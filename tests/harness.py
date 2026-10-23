"""Minimal local stand-in for the GenLayer SDK.

It lets the contract's own Python logic (validation, state machine, money
movement, band equivalence) run in plain CPython with zero installs.
It does NOT run real validators or a real LLM: web pages and LLM answers are
scripted by the tests. Live behaviour must be confirmed on Studio Next
(see docs/DEPLOYMENT.md and the evidence/ folder).
"""

import hashlib
import importlib.util
import sys
import types
from datetime import datetime as _real_datetime
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "rubrica.py"


class UserError(Exception):
    pass


class ConsensusFailure(Exception):
    """Raised when validators would disagree; real network => UNDETERMINED."""


class Return:
    def __init__(self, calldata):
        self.calldata = calldata


class Address:
    def __init__(self, value):
        if isinstance(value, Address):
            raw = value.raw
        elif isinstance(value, (bytes, bytearray)):
            raw = bytes(value)
        else:
            text = str(value)
            if text.lower().startswith("0x"):
                text = text[2:]
            raw = bytes.fromhex(text)
        if len(raw) != 20:
            raise ValueError("address must be 20 bytes")
        self.raw = raw

    @property
    def as_hex(self):
        return "0x" + self.raw.hex()

    def __eq__(self, other):
        return isinstance(other, Address) and self.raw == other.raw

    def __hash__(self):
        return hash(self.raw)

    def __repr__(self):
        return f"Address({self.as_hex})"


class TreeMap(dict):
    def __class_getitem__(cls, item):
        return cls


class _ContractBase:
    """Materialises annotated storage fields with zero values, like GenVM does."""

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        for klass in reversed(cls.__mro__):
            for name, ann in getattr(klass, "__annotations__", {}).items():
                if ann is TreeMap:
                    setattr(obj, name, TreeMap())
                elif ann is int:
                    setattr(obj, name, 0)
                elif ann is str:
                    setattr(obj, name, "")
        return obj


class Env:
    """Mutable world state shared between the stub SDK and the tests."""

    def __init__(self):
        self.now = 1_800_000_000
        self.sender = None
        self.value = 0
        self.pages = {}            # url -> text (or Exception instance)
        self.llm_calls = []        # every prompt sent to the "LLM"
        self.llm_queue = []        # scripted answers, consumed per call
        self.llm_default = None
        self.transfers = []        # (Address, amount)
        self.consensus_runs = 0

    def next_llm(self, prompt):
        self.llm_calls.append(prompt)
        item = self.llm_queue.pop(0) if self.llm_queue else self.llm_default
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(prompt)
        return item


ENV = Env()


class _Public:
    @staticmethod
    def view(fn):
        fn.__gl_kind__ = "view"
        return fn

    class _Write:
        def __call__(self, fn):
            fn.__gl_kind__ = "write"
            return fn

        @staticmethod
        def payable(fn):
            fn.__gl_kind__ = "write_payable"
            return fn

    write = _Write()


class _Message:
    @property
    def sender_address(self):
        return ENV.sender

    @property
    def value(self):
        return ENV.value


def _run_nondet_unsafe(leader_fn, validator_fn):
    ENV.consensus_runs += 1
    leader_result = leader_fn()
    if not validator_fn(Return(leader_result)):
        raise ConsensusFailure("validators disagreed")
    return leader_result


def _render(url, mode="text"):
    page = ENV.pages.get(url)
    if page is None:
        raise RuntimeError("no such page")
    if isinstance(page, Exception):
        raise page
    return page


def _exec_prompt(prompt, **kwargs):
    return ENV.next_llm(prompt)


def _contract_interface(cls):
    class _Bound:
        def __init__(self, address):
            self.address = address

        def emit_transfer(self, value=0):
            ENV.transfers.append((self.address, int(value)))

    return _Bound


def _build_modules():
    gl = types.ModuleType("genlayer")
    gl.contract = types.SimpleNamespace(Contract=_ContractBase)
    gl.public = _Public()
    gl.message = _Message()
    gl.vm = types.SimpleNamespace(
        UserError=UserError, Return=Return, run_nondet_unsafe=_run_nondet_unsafe
    )
    gl.nondet = types.SimpleNamespace(
        web=types.SimpleNamespace(render=_render),
        exec_prompt=_exec_prompt,
    )
    gl.evm = types.SimpleNamespace(contract_interface=_contract_interface)
    gl.storage = types.SimpleNamespace(allow=lambda cls: cls, TreeMap=TreeMap)

    types_mod = types.ModuleType("genlayer.types")
    types_mod.Address = Address
    types_mod.u256 = int
    types_mod.u32 = int
    types_mod.__all__ = ["Address", "u256", "u32"]
    gl.types = types_mod
    return gl, types_mod


class _FakeDatetime:
    @staticmethod
    def now(tz=None):
        return _real_datetime.fromtimestamp(ENV.now, tz or timezone.utc)


def load_contract():
    """Import contracts/rubrica.py against the stub SDK and return the module."""
    gl, types_mod = _build_modules()
    saved = {k: sys.modules.get(k) for k in ("genlayer", "genlayer.types")}
    sys.modules["genlayer"] = gl
    sys.modules["genlayer.types"] = types_mod
    try:
        spec = importlib.util.spec_from_file_location("rubrica_under_test", CONTRACT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for key, old in saved.items():
            if old is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = old
    module.datetime = _FakeDatetime
    return module


def reset_env():
    global ENV
    ENV.__init__()
    return ENV


def addr(n: int) -> Address:
    return Address(bytes([n]) * 20)


def canonical_hash(text: str) -> str:
    canon = " ".join(text.replace("\x00", " ").split())
    return "0x" + hashlib.sha256(canon.encode("utf-8")).hexdigest()

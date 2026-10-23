"""Write (or check) artifacts/rubrica.abi.json from the contract's public methods.

Usage:
    python scripts/export_abi.py            # rewrite the artifact
    python scripts/export_abi.py --check    # fail if the artifact is out of date
"""
import inspect
import json
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import harness  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "rubrica.abi.json"


def _name(annotation):
    if annotation is inspect.Signature.empty:
        return "unannotated"
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def build():
    module = harness.load_contract()
    methods = []
    for name, fn in vars(module.Rubrica).items():
        kind = getattr(fn, "__gl_kind__", None)
        if kind is None and name == "__init__":
            kind = "constructor"
        if kind is None:
            continue
        sig = inspect.signature(fn)
        params = [
            {"name": p.name, "type": _name(p.annotation)}
            for p in sig.parameters.values() if p.name != "self"
        ]
        methods.append({
            "name": name, "kind": kind, "params": params,
            "returns": _name(sig.return_annotation) if name != "__init__" else "None",
        })
    methods.sort(key=lambda m: (m["kind"] != "constructor", m["name"]))
    return {"contract": "Rubrica", "version": "0.1.0", "methods": methods}


def main():
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != text:
            raise SystemExit("artifacts/rubrica.abi.json is out of date; run scripts/export_abi.py")
        print("abi_matches_committed_artifact=PASS")
        return
    ARTIFACT.write_text(text)
    print(f"wrote {ARTIFACT.relative_to(ROOT)} ({len(text)} bytes)")


if __name__ == "__main__":
    main()

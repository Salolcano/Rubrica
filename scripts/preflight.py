"""Release gate: header, structure, ABI artifact and tests must all pass."""
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADER = [
    "# v0.3.0",
    '# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }',
]

sources = sorted((ROOT / "contracts").glob("*.py"))
if [p.name for p in sources] != ["rubrica.py"]:
    raise SystemExit(f"expected exactly contracts/rubrica.py, found {[p.name for p in sources]}")
raw = sources[0].read_bytes()
text = raw.decode("utf-8")
tree = ast.parse(text)

lines = text.splitlines()
if lines[:2] != REQUIRED_HEADER:
    raise SystemExit("the first two lines must be the v0.3.0 header with the pinned py-genlayer hash")
if ":latest" in text or ":test" in text:
    raise SystemExit("py-genlayer dependency must be pinned by hash")

classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
           and any(ast.unparse(b) == "gl.contract.Contract" for b in n.bases)]
if len(classes) != 1:
    raise SystemExit("exactly one class must extend gl.contract.Contract")

for node in classes[0].body:
    if isinstance(node, ast.FunctionDef) and any("gl.public" in ast.unparse(d) for d in node.decorator_list):
        args = [a for a in node.args.args if a.arg != "self"]
        if any(a.annotation is None for a in args) or node.returns is None:
            raise SystemExit(f"public method {node.name} needs full type annotations")

if re.search(r"\bfloat\(|:\s*float\b", text):
    raise SystemExit("floats are not allowed in contract state or arguments")

subprocess.run([sys.executable, "-m", "compileall", "-q", "contracts", "tests", "scripts"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "scripts/export_abi.py", "--check"], cwd=ROOT, check=True)

result = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests/direct", "-p", "test_*.py"],
    cwd=ROOT, capture_output=True, text=True,
)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
match = re.search(r"Ran (\d+) tests?", result.stderr)
if not match:
    raise SystemExit("could not read the unittest summary")

print("contract_sha256=0x" + hashlib.sha256(raw).hexdigest())
print("contract_source_bytes=" + str(len(raw)))
print("direct_tests=" + match.group(1))
print("preflight=PASS")

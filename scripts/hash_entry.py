"""Print the SHA-256 an entrant must submit for a text file.

Usage:  python scripts/hash_entry.py my_entry.txt

Rubrica hashes the page text after collapsing all whitespace runs to single
spaces, so line endings and trailing newlines never change the result.
"""
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python scripts/hash_entry.py <file.txt>")
text = open(sys.argv[1], "r", encoding="utf-8").read()
canonical = " ".join(text.replace("\x00", " ").split())
if not canonical:
    raise SystemExit("file is empty")
if len(canonical.encode("utf-8")) > 12_000:
    raise SystemExit("file is larger than 12,000 bytes; Rubrica will reject it")
print("0x" + hashlib.sha256(canonical.encode("utf-8")).hexdigest())

#!/usr/bin/env python3

import ast
import hashlib
import json
import subprocess
import sys
import tokenize
import io
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "RUNTIME_EVIDENCE"
EVIDENCE.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "GOODBAY220_SPECIFICATION.py",
    "KHALED27_WORKFLOW.py",
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def validate(path):
    result = {
        "file": path.name,
        "exists": path.exists(),
        "compile": False,
        "ast": False,
        "tokenize": False,
        "sha256": None,
        "error": None
    }

    if not path.exists():
        result["error"] = "missing"
        return result

    result["sha256"] = sha256_file(path)

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        compile(text, path.name, "exec")
        result["compile"] = True

        ast.parse(text, filename=path.name)
        result["ast"] = True

        list(
            tokenize.generate_tokens(
                io.StringIO(text).readline
            )
        )
        result["tokenize"] = True

    except Exception as e:
        result["error"] = str(e)

    return result

report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "targets": [],
    "overall": False
}

for name in TARGETS:
    result = validate(ROOT / name)
    report["targets"].append(result)

report["overall"] = all(
    x["exists"]
    and x["compile"]
    and x["ast"]
    and x["tokenize"]
    for x in report["targets"]
)

out = EVIDENCE / "RUNTIME_VALIDATION.json"
out.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["overall"]:
    print("RUNTIME STATUS: FAIL")
else:
    print("RUNTIME STATUS: PASS")

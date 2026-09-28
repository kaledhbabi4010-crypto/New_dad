
import ast
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "GOODDAYGOODBAY220_FINAL" / "LOCAL_RUNTIME_EVIDENCE"
OUT.mkdir(parents=True, exist_ok=True)

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()

results = []

for p in ROOT.rglob("*.py"):

    if ".git" in p.parts:
        continue

    rel = p.relative_to(ROOT).as_posix()

    item = {
        "file": rel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:

        source = p.read_text(
            encoding="utf-8",
            errors="replace"
        )

        compile(source, str(p), "exec")

        item["compile"] = True
        item["sha256"] = sha256(p)

        try:

            tree = ast.parse(source)

            item["ast"] = True

            item["functions"] = sum(
                isinstance(
                    n,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                for n in ast.walk(tree)
            )

            item["classes"] = sum(
                isinstance(n, ast.ClassDef)
                for n in ast.walk(tree)
            )

        except Exception as e:

            item["ast"] = False
            item["ast_error"] = repr(e)

    except Exception as e:

        item["compile"] = False
        item["error"] = repr(e)

    results.append(item)

payload = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "files": len(results),
    "compile_pass": sum(
        x.get("compile") is True
        for x in results
    ),
    "compile_fail": sum(
        x.get("compile") is False
        for x in results
    ),
    "results": results,
}

(OUT / "LOCAL_CODE_AUDIT.json").write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print(
    json.dumps(
        {
            "files": payload["files"],
            "compile_pass": payload["compile_pass"],
            "compile_fail": payload["compile_fail"],
        },
        indent=2
    )
)


import pathlib, zipfile, hashlib, json, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

checks = []

def check(cid, condition, detail):
    checks.append({
        "id": cid,
        "pass": bool(condition),
        "detail": str(detail)
    })

exe = ROOT / "app" / "GooddayGoodbay220.exe"

check(
    "APP_EXE_EXISTS",
    exe.exists(),
    exe
)

if exe.exists():
    check(
        "APP_EXE_SHA256",
        sha256(exe) == "2d59428f34a9e613c51b0b770e6839e85abb5ecd9efbf3d9a6cf2e8edc28c350",
        sha256(exe)
    )

for rel in [
    "install.ps1",
    "uninstall.ps1",
    "verify.ps1",
    "package.json",
    "VERSION",
    "SHA256_MANIFEST.json",
    "tools/windows_runtime_test.ps1",
    ".github/workflows/gooddaygoodbay221-windows.yml",
    ".vscode/settings.json",
    ".devcontainer/devcontainer.json"
]:
    check(
        "FILE_" + rel.replace("/", "_"),
        (ROOT / rel).exists(),
        rel
    )

z = ROOT / "SHA256_MANIFEST.json"

if z.exists():
    try:
        manifest = json.loads(z.read_text())
        for rel, expected in manifest.items():
            p = ROOT / rel
            check(
                "MANIFEST_" + rel.replace("/", "_"),
                p.exists() and sha256(p) == expected,
                sha256(p) if p.exists() else "MISSING"
            )
    except Exception as e:
        check("MANIFEST_JSON_VALID", False, e)

result = {
    "total": len(checks),
    "pass": sum(x["pass"] for x in checks),
    "fail": sum(not x["pass"] for x in checks),
    "checks": checks
}

print(json.dumps(result, indent=2))

if result["fail"]:
    sys.exit(1)

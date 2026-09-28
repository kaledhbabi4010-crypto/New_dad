
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path.cwd()
PROD = ROOT / "GOODDAYGOOBUY220_FINAL"

OUT = ROOT / "WINDOWS_RELEASE"
DIST = OUT / "dist"
WORK = OUT / "build"
PACKAGE = OUT / "package"

OUT.mkdir(exist_ok=True)
DIST.mkdir(exist_ok=True)
PACKAGE.mkdir(exist_ok=True)


def fail(message):
    print("HARD BLOCK:", message)
    raise SystemExit(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, timeout=600):
    print("$", " ".join(map(str, cmd)))

    p = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )

    print(p.stdout[-12000:])

    if p.returncode != 0:
        fail(
            "Command failed: " +
            " ".join(map(str, cmd))
        )

    return p


# -------------------------------------------------------------------------
# Production compile
# -------------------------------------------------------------------------

for source in PROD.rglob("*.py"):

    if "WINDOWS_PRODUCTION_BUILDER.py" in str(source):
        continue

    run([
        sys.executable,
        "-m",
        "py_compile",
        str(source)
    ])


# -------------------------------------------------------------------------
# Runtime import
# -------------------------------------------------------------------------

env = os.environ.copy()
env["PYTHONPATH"] = str(PROD)

run([
    sys.executable,
    "-c",
    "import KHALED27_WORKFLOW; print('REAL_IMPORT_PASS:KHALED27_WORKFLOW')"
])

run([
    sys.executable,
    "-c",
    "import RUN_GOODDAYGOOBUY220; print('REAL_IMPORT_PASS:RUN_GOODDAYGOOBUY220')"
])


# -------------------------------------------------------------------------
# Determine whether runner has a safe CLI help interface.
# -------------------------------------------------------------------------

runner = PROD / "RUN_GOODDAYGOOBUY220.py"

source = runner.read_text(
    encoding="utf-8",
    errors="replace"
)

tree = ast.parse(source)

has_argparse = False
has_click = False
has_typer = False

for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        if isinstance(node.func, ast.Attribute):

            if node.func.attr == "ArgumentParser":
                has_argparse = True

            if node.func.attr in (
                "command",
                "group",
                "option"
            ):
                has_click = True

        if isinstance(node.func, ast.Name):

            if node.func.id == "Typer":
                has_typer = True


help_supported = (
    has_argparse
    or has_click
    or has_typer
)


# -------------------------------------------------------------------------
# Install builder
# -------------------------------------------------------------------------

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip",
], timeout=600)

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "pyinstaller",
], timeout=600)


# -------------------------------------------------------------------------
# Clean build
# -------------------------------------------------------------------------

for path in (DIST, WORK):

    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------------
# PyInstaller
# -------------------------------------------------------------------------

exe_name = "GooddayGoodbay220"

run([
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name",
    exe_name,
    str(runner),
], timeout=1200)


exe = DIST / f"{exe_name}.exe"

if not exe.exists():
    fail("Windows EXE was not produced.")


# -------------------------------------------------------------------------
# PE verification
# -------------------------------------------------------------------------

with open(exe, "rb") as f:
    magic = f.read(2)

if magic != b"MZ":
    fail("Produced file does not contain Windows PE MZ header.")


exe_hash = sha256(exe)

print("EXE_SHA256:", exe_hash)
print("EXE_SIZE:", exe.stat().st_size)


# -------------------------------------------------------------------------
# Runtime smoke test
#
# Only execute --help when source evidence indicates a CLI framework.
# This avoids inventing an unsupported runtime command.
# -------------------------------------------------------------------------

runtime_result = {
    "help_supported_by_source": help_supported,
    "executed": False,
    "returncode": None,
    "output": "",
}


if help_supported:

    p = subprocess.run(
        [str(exe), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )

    runtime_result["executed"] = True
    runtime_result["returncode"] = p.returncode
    runtime_result["output"] = p.stdout[-10000:]

    print(p.stdout[-10000:])

    if p.returncode != 0:
        fail(
            "EXE --help smoke test failed."
        )

else:

    print(
        "INFO: No CLI framework was detected. "
        "No invented runtime command will be executed."
    )


# -------------------------------------------------------------------------
# Package
# -------------------------------------------------------------------------

package_root = PACKAGE / "GooddayGoodbay220"

if package_root.exists():
    shutil.rmtree(package_root)

package_root.mkdir(parents=True)


# EXE
shutil.copy2(
    exe,
    package_root / exe.name
)


# Evidence
evidence = {
    "product": "GooddayGoodbay220",
    "entrypoint": "GOODDAYGOOBUY220_FINAL/RUN_GOODDAYGOOBUY220.py",
    "windows": True,
    "pe_magic": "MZ",
    "exe_sha256": exe_hash,
    "exe_size": exe.stat().st_size,
    "runtime_smoke_test": runtime_result,
}


(package_root / "BUILD_EVIDENCE.json").write_text(
    json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# -------------------------------------------------------------------------
# ZIP
# -------------------------------------------------------------------------

zip_path = OUT / "GooddayGoodbay220.zip"

if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(
    zip_path,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as z:

    for file in package_root.rglob("*"):

        if file.is_file():

            z.write(
                file,
                file.relative_to(PACKAGE)
            )


# -------------------------------------------------------------------------
# ZIP integrity
# -------------------------------------------------------------------------

with zipfile.ZipFile(zip_path, "r") as z:

    bad = z.testzip()

    if bad is not None:
        fail(
            "ZIP integrity test failed: " + bad
        )

    names = z.namelist()

    expected = (
        "GooddayGoodbay220/GooddayGoodbay220.exe"
    )

    if expected not in names:
        fail(
            "ZIP does not contain expected executable."
        )


zip_hash = sha256(zip_path)

evidence["zip_sha256"] = zip_hash
evidence["zip_size"] = zip_path.stat().st_size

(package_root / "BUILD_EVIDENCE.json").write_text(
    json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# Recreate ZIP after final evidence update.
zip_path.unlink()

with zipfile.ZipFile(
    zip_path,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as z:

    for file in package_root.rglob("*"):

        if file.is_file():

            z.write(
                file,
                file.relative_to(PACKAGE)
            )


zip_hash = sha256(zip_path)

print("=" * 80)
print("WINDOWS PRODUCTION BUILD PASS")
print("=" * 80)
print("EXE:", exe)
print("EXE SHA256:", exe_hash)
print("ZIP:", zip_path)
print("ZIP SHA256:", zip_hash)
print("ZIP SIZE:", zip_path.stat().st_size)
print("=" * 80)

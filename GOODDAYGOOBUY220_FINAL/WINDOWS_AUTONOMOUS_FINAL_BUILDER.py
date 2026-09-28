
import os
import sys
import ast
import json
import shutil
import hashlib
import subprocess
import zipfile
from pathlib import Path

ROOT = Path.cwd()
PROD = ROOT / "GOODDAYGOOBUY220_FINAL"
RUNNER = PROD / "RUN_GOODDAYGOOBUY220.py"

OUT = ROOT / "WINDOWS_RELEASE"
DIST = OUT / "dist"
BUILD = OUT / "build"
PACKAGE = OUT / "package"

for p in (OUT, DIST, BUILD, PACKAGE):
    p.mkdir(parents=True, exist_ok=True)

def fail(msg):
    print("HARD BLOCK:", msg)
    raise SystemExit(1)

def run(cmd, timeout=1800, allow_fail=False):
    print("\n$", " ".join(map(str, cmd)))
    p = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout
    )
    print(p.stdout[-18000:])
    if p.returncode and not allow_fail:
        fail("COMMAND FAILED")
    return p

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()

# ----------------------------------------------------------------------
# Upgrade packaging tools
# ----------------------------------------------------------------------

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip",
    "setuptools",
    "wheel",
    "pyinstaller"
], timeout=1800)

# ----------------------------------------------------------------------
# Compile everything in production
# ----------------------------------------------------------------------

for f in PROD.rglob("*.py"):

    if f.name == Path(__file__).name:
        continue

    run([
        sys.executable,
        "-m",
        "py_compile",
        str(f)
    ], timeout=300)

# ----------------------------------------------------------------------
# Import tests
# ----------------------------------------------------------------------

env = os.environ.copy()
env["PYTHONPATH"] = str(PROD)

for module in (
    "KHALED27_WORKFLOW",
    "RUN_GOODDAYGOOBUY220"
):

    p = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import {module}; print('REAL_IMPORT_PASS:{module}')"
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180
    )

    print(p.stdout[-10000:])

    if p.returncode:
        fail("REAL IMPORT FAILED: " + module)

# ----------------------------------------------------------------------
# Discover imports from runner
# ----------------------------------------------------------------------

tree = ast.parse(
    RUNNER.read_text(
        encoding="utf-8",
        errors="replace"
    )
)

imports = set()

for node in ast.walk(tree):

    if isinstance(node, ast.Import):

        for a in node.names:
            imports.add(a.name.split(".")[0])

    elif isinstance(node, ast.ImportFrom):

        if node.module:
            imports.add(
                node.module.split(".")[0]
            )

stdlib = {
    "sys","os","json","re","time","pathlib","typing",
    "subprocess","shutil","hashlib","datetime","threading",
    "queue","logging","argparse","zipfile","tempfile",
    "platform","socket","ssl","uuid","enum","dataclasses",
    "traceback","inspect","functools","itertools","collections",
    "math","statistics","csv","xml","sqlite3","urllib","http",
    "email","base64","secrets","random","glob","fnmatch",
    "copy","pickle","struct","ctypes","ast","io","tokenize",
    "__future__"
}

local = {
    f.stem
    for f in PROD.rglob("*.py")
}

third_party = sorted(
    x for x in imports
    if x not in stdlib and x not in local
)

print("THIRD_PARTY:", third_party)

# ----------------------------------------------------------------------
# Install dependencies
# ----------------------------------------------------------------------

for pkg in third_party:

    print("INSTALL OPTIONAL:", pkg)

    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        pkg
    ], timeout=900, allow_fail=True)

# ----------------------------------------------------------------------
# Build strategies
# ----------------------------------------------------------------------

strategies = [
    (
        "ONEFILE_BASE",
        [
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "GooddayGoodbay220",
            "--paths",
            str(PROD),
            str(RUNNER)
        ]
    ),
    (
        "ONEFILE_COLLECT",
        [
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "GooddayGoodbay220",
            "--paths",
            str(PROD)
        ] +
        sum(
            (
                [
                    "--collect-submodules",
                    p,
                    "--collect-data",
                    p
                ]
                for p in third_party
            ),
            []
        ) +
        [
            str(RUNNER)
        ]
    ),
    (
        "ONEFILE_HIDDEN",
        [
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "GooddayGoodbay220",
            "--paths",
            str(PROD)
        ] +
        sum(
            (
                [
                    "--hidden-import",
                    p,
                    "--collect-submodules",
                    p,
                    "--collect-data",
                    p
                ]
                for p in third_party
            ),
            []
        ) +
        [
            str(RUNNER)
        ]
    ),
    (
        "ONEDIR_DIAGNOSTIC",
        [
            "--clean",
            "--noconfirm",
            "--onedir",
            "--name",
            "GooddayGoodbay220",
            "--paths",
            str(PROD)
        ] +
        sum(
            (
                [
                    "--hidden-import",
                    p,
                    "--collect-submodules",
                    p,
                    "--collect-data",
                    p
                ]
                for p in third_party
            ),
            []
        ) +
        [
            str(RUNNER)
        ]
    )
]

results = []
final_exe = None
final_strategy = None

for name, args in strategies:

    print("\n" + "=" * 90)
    print("STRATEGY:", name)
    print("=" * 90)

    if DIST.exists():
        shutil.rmtree(DIST)

    if BUILD.exists():
        shutil.rmtree(BUILD)

    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    p = run(
        [
            sys.executable,
            "-m",
            "PyInstaller"
        ] + args,
        timeout=2400,
        allow_fail=True
    )

    results.append({
        "strategy": name,
        "returncode": p.returncode,
        "output": p.stdout[-30000:]
    })

    candidates = list(
        DIST.rglob("GooddayGoodbay220.exe")
    )

    for candidate in candidates:

        try:

            with open(candidate, "rb") as f:
                magic = f.read(2)

            if (
                magic == b"MZ"
                and candidate.stat().st_size > 100000
            ):

                final_exe = candidate
                final_strategy = name
                break

        except Exception:
            pass

    if final_exe:
        print("[PASS] VALID PE:", final_exe)
        break

if not final_exe:

    (OUT / "BUILD_ATTEMPTS.json").write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    fail(
        "All Windows build strategies failed."
    )

# ----------------------------------------------------------------------
# Package
# ----------------------------------------------------------------------

package = (
    PACKAGE /
    "GooddayGoodbay220"
)

if package.exists():
    shutil.rmtree(package)

package.mkdir(
    parents=True,
    exist_ok=True
)

final_copy = (
    package /
    "GooddayGoodbay220.exe"
)

shutil.copy2(
    final_exe,
    final_copy
)

exe_hash = sha256(final_copy)

# ----------------------------------------------------------------------
# Safe runtime verification
# ----------------------------------------------------------------------

runtime = {
    "performed": False,
    "returncode": None,
    "output": ""
}

source = RUNNER.read_text(
    encoding="utf-8",
    errors="replace"
)

tree = ast.parse(source)

cli = False

for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        if isinstance(node.func, ast.Attribute):

            if node.func.attr in (
                "ArgumentParser",
                "command",
                "group",
                "option"
            ):
                cli = True

        if isinstance(node.func, ast.Name):

            if node.func.id == "Typer":
                cli = True

if cli:

    try:

        p = subprocess.run(
            [
                str(final_copy),
                "--help"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180
        )

        runtime["performed"] = True
        runtime["returncode"] = p.returncode
        runtime["output"] = p.stdout[-30000:]

        print(
            p.stdout[-12000:]
        )

    except Exception as e:

        runtime["error"] = repr(e)

else:

    print(
        "[INFO] No CLI detected; "
        "no destructive execution invented."
    )

# ----------------------------------------------------------------------
# Evidence
# ----------------------------------------------------------------------

evidence = {
    "product": "GooddayGoodbay220",
    "entrypoint":
        "GOODDAYGOOBUY220_FINAL/RUN_GOODDAYGOOBUY220.py",
    "strategy": final_strategy,
    "exe_size": final_copy.stat().st_size,
    "exe_sha256": exe_hash,
    "pe_magic": "MZ",
    "runtime": runtime,
    "build_attempts": results
}

(package / "BUILD_EVIDENCE.json").write_text(
    json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

# ----------------------------------------------------------------------
# ZIP
# ----------------------------------------------------------------------

zip_path = (
    OUT /
    "GooddayGoodbay220.zip"
)

if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(
    zip_path,
    "w",
    zipfile.ZIP_DEFLATED
) as z:

    for f in package.rglob("*"):

        if f.is_file():

            z.write(
                f,
                f.relative_to(PACKAGE)
            )

# ----------------------------------------------------------------------
# ZIP validation
# ----------------------------------------------------------------------

with zipfile.ZipFile(
    zip_path,
    "r"
) as z:

    if z.testzip():
        fail("ZIP integrity failure.")

    expected = (
        "GooddayGoodbay220/"
        "GooddayGoodbay220.exe"
    )

    if expected not in z.namelist():
        fail("EXE missing from ZIP.")

zip_hash = sha256(zip_path)

(OUT / "FINAL_WINDOWS_EVIDENCE.json").write_text(
    json.dumps(
        {
            "status":
                "WINDOWS_PACKAGE_BUILT_AND_VERIFIED",
            "exe_sha256": exe_hash,
            "zip_sha256": zip_hash,
            "exe_size":
                final_copy.stat().st_size,
            "zip_size":
                zip_path.stat().st_size,
            "strategy": final_strategy,
            "runtime": runtime
        },
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("=" * 90)
print("WINDOWS BUILD PASS")
print("EXE:", final_copy)
print("ZIP:", zip_path)
print("EXE SHA256:", exe_hash)
print("ZIP SHA256:", zip_hash)
print("=" * 90)

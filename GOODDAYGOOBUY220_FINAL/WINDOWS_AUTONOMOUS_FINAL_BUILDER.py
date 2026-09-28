
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
BUILD = OUT / "build"
PACKAGE = OUT / "package"

OUT.mkdir(exist_ok=True)
DIST.mkdir(exist_ok=True)
BUILD.mkdir(exist_ok=True)
PACKAGE.mkdir(exist_ok=True)


RUNNER = PROD / "RUN_GOODDAYGOOBUY220.py"


def fail(msg):
    print("HARD BLOCK:", msg)
    raise SystemExit(1)


def run(cmd, timeout=1200, allow_fail=False):

    print()
    print("$", " ".join(map(str, cmd)))

    p = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout
    )

    print(p.stdout[-16000:])

    if p.returncode != 0 and not allow_fail:

        fail(
            "COMMAND_FAILED\n" +
            " ".join(map(str, cmd))
        )

    return p


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


# -------------------------------------------------------------------------
# Install PyInstaller
# -------------------------------------------------------------------------

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip"
], timeout=600)

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pyinstaller"
], timeout=1200)


# -------------------------------------------------------------------------
# Source compilation
# -------------------------------------------------------------------------

for source in PROD.rglob("*.py"):

    if source.name == Path(__file__).name:
        continue

    run([
        sys.executable,
        "-m",
        "py_compile",
        str(source)
    ], timeout=300)


# -------------------------------------------------------------------------
# Real imports
# -------------------------------------------------------------------------

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

    if p.returncode != 0:
        fail(f"Import failed: {module}")


# -------------------------------------------------------------------------
# AST dependency discovery
# -------------------------------------------------------------------------

source = RUNNER.read_text(
    encoding="utf-8",
    errors="replace"
)

tree = ast.parse(source)

imports = set()

for node in ast.walk(tree):

    if isinstance(node, ast.Import):

        for alias in node.names:
            imports.add(alias.name.split(".")[0])

    elif isinstance(node, ast.ImportFrom):

        if node.module:
            imports.add(
                node.module.split(".")[0]
            )


stdlib = {
    "sys", "os", "json", "re", "time", "pathlib",
    "typing", "subprocess", "shutil", "hashlib",
    "datetime", "threading", "queue", "logging",
    "argparse", "zipfile", "tempfile", "platform",
    "socket", "ssl", "uuid", "enum", "dataclasses",
    "traceback", "inspect", "functools", "itertools",
    "collections", "math", "statistics", "csv",
    "xml", "sqlite3", "urllib", "http", "email",
    "base64", "secrets", "random", "glob", "fnmatch",
    "copy", "pickle", "struct", "ctypes"
}

local_modules = {
    p.stem
    for p in PROD.rglob("*.py")
}

third_party = sorted(
    x for x in imports
    if x not in stdlib
    and x not in local_modules
)


# -------------------------------------------------------------------------
# Install discovered third-party modules.
#
# Failure is tolerated because some imports can be optional.
# -------------------------------------------------------------------------

for package in third_party:

    print(
        "OPTIONAL DEPENDENCY:",
        package
    )

    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        package
    ], timeout=600, allow_fail=True)


# -------------------------------------------------------------------------
# Find package metadata.
# -------------------------------------------------------------------------

package_candidates = []

for package in third_party:

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib.util,sys;"
                    "name=sys.argv[1];"
                    "print(importlib.util.find_spec(name))"
                ),
                package
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if result.returncode == 0:
            package_candidates.append(package)

    except Exception:
        pass


# -------------------------------------------------------------------------
# DATA collection
# -------------------------------------------------------------------------

datas = []

extensions = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".csv",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".pem",
    ".crt",
    ".cer"
}

for f in PROD.rglob("*"):

    if f.is_file() and f.suffix.lower() in extensions:

        datas.append(
            (
                str(f),
                str(
                    f.parent.relative_to(PROD)
                )
            )
        )


# -------------------------------------------------------------------------
# Strategy 1
#
# Normal PyInstaller.
# -------------------------------------------------------------------------

strategies = []


strategies.append({
    "name": "normal",
    "args": [
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "GooddayGoodbay220",
        "--paths",
        str(PROD),
        str(RUNNER)
    ]
})


# -------------------------------------------------------------------------
# Strategy 2
#
# Add recursive collection for discovered third-party packages.
# -------------------------------------------------------------------------

collect_args = []

for package in package_candidates:

    collect_args += [
        "--collect-submodules",
        package
    ]

    collect_args += [
        "--collect-data",
        package
    ]


strategies.append({
    "name": "recursive_dependencies",
    "args": [
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "GooddayGoodbay220",
        "--paths",
        str(PROD)
    ] + collect_args + [
        str(RUNNER)
    ]
})


# -------------------------------------------------------------------------
# Strategy 3
#
# Explicit hidden imports.
# -------------------------------------------------------------------------

hidden_args = []

for package in package_candidates:

    hidden_args += [
        "--hidden-import",
        package
    ]

strategies.append({
    "name": "hidden_imports",
    "args": [
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        "GooddayGoodbay220",
        "--paths",
        str(PROD)
    ] + hidden_args + collect_args + [
        str(RUNNER)
    ]
})


# -------------------------------------------------------------------------
# Strategy 4
#
# Build ONEDIR first.
# This is a diagnostic fallback and gives PyInstaller a more transparent
# collection layout.
# -------------------------------------------------------------------------

strategies.append({
    "name": "onedir_diagnostic",
    "args": [
        "--clean",
        "--noconfirm",
        "--onedir",
        "--name",
        "GooddayGoodbay220",
        "--paths",
        str(PROD)
    ] + hidden_args + collect_args + [
        str(RUNNER)
    ]
})


# -------------------------------------------------------------------------
# Build loop
# -------------------------------------------------------------------------

build_results = []

successful_exe = None
successful_strategy = None

for strategy in strategies:

    name = strategy["name"]

    print()
    print("=" * 90)
    print("BUILD STRATEGY:", name)
    print("=" * 90)

    if DIST.exists():
        shutil.rmtree(DIST)

    if BUILD.exists():
        shutil.rmtree(BUILD)

    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller"
    ] + strategy["args"]

    result = run(
        command,
        timeout=1800,
        allow_fail=True
    )

    result_record = {
        "strategy": name,
        "returncode": result.returncode,
        "output_tail": result.stdout[-20000:]
    }

    build_results.append(result_record)

    # ---------------------------------------------------------------------
    # Search every possible EXE generated by the strategy.
    # ---------------------------------------------------------------------

    candidates = list(DIST.rglob("GooddayGoodbay220.exe"))

    valid = []

    for candidate in candidates:

        try:

            with open(candidate, "rb") as f:
                magic = f.read(2)

            if magic == b"MZ" and candidate.stat().st_size > 100000:

                valid.append(candidate)

        except Exception:
            pass


    if valid:

        successful_exe = valid[0]
        successful_strategy = name

        print(
            "[PASS] VALID WINDOWS PE FOUND:",
            successful_exe
        )

        break

    print(
        "[WARN] Strategy did not produce a valid EXE:",
        name
    )


if successful_exe is None:

    Path(
        OUT / "BUILD_ATTEMPTS.json"
    ).write_text(
        json.dumps(
            build_results,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    fail(
        "All PyInstaller production strategies failed."
    )


# -------------------------------------------------------------------------
# EXE verification
# -------------------------------------------------------------------------

exe_sha256 = sha256(successful_exe)

exe_size = successful_exe.stat().st_size

print(
    "SUCCESSFUL STRATEGY:",
    successful_strategy
)

print(
    "EXE SHA256:",
    exe_sha256
)

print(
    "EXE SIZE:",
    exe_size
)


# -------------------------------------------------------------------------
# Runtime interface discovery
# -------------------------------------------------------------------------

runner_tree = ast.parse(source)

has_argparse = False
has_click = False
has_typer = False

for node in ast.walk(runner_tree):

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


runtime = {
    "cli_detected": (
        has_argparse
        or has_click
        or has_typer
    ),
    "executed": False,
    "returncode": None,
    "output": ""
}


# -------------------------------------------------------------------------
# Safe smoke test
#
# Only --help is used when a CLI framework was detected.
# -------------------------------------------------------------------------

if runtime["cli_detected"]:

    try:

        p = subprocess.run(
            [
                str(successful_exe),
                "--help"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180
        )

        runtime["executed"] = True
        runtime["returncode"] = p.returncode
        runtime["output"] = p.stdout[-20000:]

        print(
            p.stdout[-12000:]
        )

        if p.returncode != 0:

            print(
                "WARNING: EXE --help returned:",
                p.returncode
            )

    except Exception as e:

        runtime["error"] = repr(e)

else:

    print(
        "No CLI framework detected. "
        "No destructive/no-argument execution will be invented."
    )


# -------------------------------------------------------------------------
# PACKAGE
# -------------------------------------------------------------------------

package_root = (
    PACKAGE /
    "GooddayGoodbay220"
)

if package_root.exists():
    shutil.rmtree(package_root)

package_root.mkdir(
    parents=True,
    exist_ok=True
)

final_exe = (
    package_root /
    "GooddayGoodbay220.exe"
)

shutil.copy2(
    successful_exe,
    final_exe
)


# -------------------------------------------------------------------------
# Evidence
# -------------------------------------------------------------------------

evidence = {
    "product": "GooddayGoodbay220",
    "entrypoint":
        "GOODDAYGOOBUY220_FINAL/RUN_GOODDAYGOOBUY220.py",
    "successful_strategy": successful_strategy,
    "exe_sha256": exe_sha256,
    "exe_size": exe_size,
    "pe_magic": "MZ",
    "runtime": runtime,
    "third_party_candidates": third_party,
    "package_candidates": package_candidates,
    "build_attempts": build_results,
    "timestamp_utc": time.time()
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

    for file in package_root.rglob("*"):

        if file.is_file():

            z.write(
                file,
                file.relative_to(PACKAGE)
            )


# -------------------------------------------------------------------------
# ZIP verification
# -------------------------------------------------------------------------

with zipfile.ZipFile(
    zip_path,
    "r"
) as z:

    bad = z.testzip()

    if bad:
        fail(
            "ZIP integrity failed: " + bad
        )

    expected = (
        "GooddayGoodbay220/"
        "GooddayGoodbay220.exe"
    )

    if expected not in z.namelist():

        fail(
            "Expected executable missing from ZIP."
        )


zip_sha256 = sha256(zip_path)


# -------------------------------------------------------------------------
# Extract ZIP and compare EXE hash
# -------------------------------------------------------------------------

verify_dir = OUT / "ZIP_VERIFY"

if verify_dir.exists():
    shutil.rmtree(verify_dir)

verify_dir.mkdir()

with zipfile.ZipFile(
    zip_path,
    "r"
) as z:
    z.extractall(verify_dir)

inside_exe = (
    verify_dir /
    "GooddayGoodbay220" /
    "GooddayGoodbay220.exe"
)

if not inside_exe.exists():
    fail(
        "EXE not found after ZIP extraction."
    )

inside_hash = sha256(inside_exe)

if inside_hash != exe_sha256:
    fail(
        "EXE SHA256 changed after ZIP packaging."
    )


# -------------------------------------------------------------------------
# Final evidence
# -------------------------------------------------------------------------

final_evidence = {
    **evidence,
    "zip_sha256": zip_sha256,
    "zip_size": zip_path.stat().st_size,
    "zip_integrity": "PASS",
    "zip_exe_hash_preservation": "PASS",
    "status": "WINDOWS_PACKAGE_BUILT_AND_VERIFIED"
}

(OUT / "FINAL_WINDOWS_EVIDENCE.json").write_text(
    json.dumps(
        final_evidence,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print()
print("=" * 100)
print("WINDOWS PRODUCTION PACKAGE PASS")
print("=" * 100)
print("EXE:", final_exe)
print("EXE SHA256:", exe_sha256)
print("ZIP:", zip_path)
print("ZIP SHA256:", zip_sha256)
print("STRATEGY:", successful_strategy)
print("=" * 100)

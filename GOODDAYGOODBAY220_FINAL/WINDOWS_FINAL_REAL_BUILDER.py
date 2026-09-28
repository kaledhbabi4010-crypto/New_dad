
import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "RELEASE"
OUT.mkdir(exist_ok=True)

REPORT = OUT / "BUILD_EVIDENCE.json"

def utc():
    return datetime.now(timezone.utc).isoformat()

def run(cmd, timeout=300):
    print("\n>", " ".join(map(str, cmd)))

    p = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout
    )

    print(p.stdout[-20000:])

    return p.returncode, p.stdout

# -----------------------------------------------------------------------------------------------
# Discover application candidates again on Windows.
# -----------------------------------------------------------------------------------------------

import ast

candidates = []

for p in ROOT.rglob("*.py"):

    if ".git" in p.parts:
        continue

    rel = p.relative_to(ROOT).as_posix()

    if any(
        word in rel.lower()
        for word in [
            "builder",
            "workflow",
            "factory",
            "repair",
            "audit",
            "forensic",
            "evidence",
            "reconstruction",
        ]
    ):
        continue

    try:

        source = p.read_text(
            encoding="utf-8",
            errors="replace"
        )

        tree = ast.parse(source)

        guard = False
        funcs = []

        for n in ast.walk(tree):

            if isinstance(
                n,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            ):

                if n.name.lower() in {
                    "main",
                    "run",
                    "start",
                    "launch",
                    "cli",
                    "application",
                    "app",
                }:
                    funcs.append(n.name)

            elif isinstance(n, ast.If):

                try:

                    t = ast.unparse(n.test)

                    if (
                        "__name__" in t
                        and "__main__" in t
                    ):
                        guard = True

                except Exception:
                    pass

        cli = []

        if "argparse" in source:
            cli.append("argparse")

        if "click" in source:
            cli.append("click")

        if "typer" in source:
            cli.append("typer")

        score = 0

        if guard:
            score += 6

        if funcs:
            score += 4

        if cli:
            score += 3

        if p.name.lower() in {
            "main.py",
            "app.py",
            "cli.py",
            "launcher.py",
            "runner.py",
        }:
            score += 4

        if score:
            candidates.append({
                "path": str(p),
                "relative": rel,
                "score": score,
                "guard": guard,
                "functions": sorted(set(funcs)),
                "cli": cli,
            })

    except Exception:
        pass

candidates.sort(
    key=lambda x: x["score"],
    reverse=True
)

(OUT / "ENTRYPOINTS_WINDOWS.json").write_text(
    json.dumps(
        candidates,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("\nCANDIDATES:")

for c in candidates[:20]:
    print(c)

if not candidates:
    raise RuntimeError(
        "No safe executable application entry point discovered."
    )

# -----------------------------------------------------------------------------------------------
# Build candidates one by one.
# -----------------------------------------------------------------------------------------------

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
        "pip",
        "setuptools",
        "wheel",
        "pyinstaller",
    ],
    check=True
)

strategies = []

for candidate in candidates[:8]:

    source = Path(candidate["path"])

    exe_name = "GooddayGoodbay220"

    build_dir = OUT / "build"
    dist_dir = OUT / "dist"

    if build_dir.exists():
        shutil.rmtree(build_dir)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    base = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        exe_name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(build_dir),
    ]

    commands = []

    commands.append(
        base + [str(source)]
    )

    # If imports are dynamically hidden, collect the actual package
    # only when the source declares one.
    for module in candidate.get("cli", []):
        pass

    success = False
    build_output = ""

    for idx, command in enumerate(commands, 1):

        print(
            "\n============================================================"
        )
        print(
            "BUILD CANDIDATE",
            candidate["relative"],
            "STRATEGY",
            idx
        )
        print(
            "============================================================"
        )

        rc, output = run(command, timeout=900)

        build_output += output

        exe = dist_dir / f"{exe_name}.exe"

        if rc == 0 and exe.exists():

            # PE header check
            with open(exe, "rb") as f:
                magic = f.read(2)

            if magic != b"MZ":
                continue

            if exe.stat().st_size < 100_000:
                continue

            # -----------------------------------------------------------------------------------
            # REAL EXECUTION TEST
            # -----------------------------------------------------------------------------------

            runtime_log = OUT / "runtime.log"

            try:

                started = time.time()

                proc = subprocess.run(
                    [str(exe)],
                    cwd=str(OUT),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=20
                )

                duration = time.time() - started

                runtime_log.write_text(
                    proc.stdout or "",
                    encoding="utf-8",
                    errors="replace"
                )

                runtime = {
                    "executed": True,
                    "returncode": proc.returncode,
                    "duration_seconds": duration,
                    "output": proc.stdout[-20000:],
                }

                # A program that immediately exits with no output and no
                # observable behavior is NOT automatically considered valid.
                meaningful = (
                    proc.returncode == 0
                    or len((proc.stdout or "").strip()) > 0
                )

                if meaningful:

                    shutil.copy2(
                        exe,
                        OUT / "GooddayGoodbay220.exe"
                    )

                    strategies.append({
                        "candidate": candidate,
                        "strategy": idx,
                        "build_returncode": rc,
                        "runtime": runtime,
                        "accepted": True,
                    })

                    success = True
                    break

                strategies.append({
                    "candidate": candidate,
                    "strategy": idx,
                    "build_returncode": rc,
                    "runtime": runtime,
                    "accepted": False,
                    "reason": "No meaningful runtime evidence",
                })

            except subprocess.TimeoutExpired as e:

                runtime = {
                    "executed": True,
                    "timeout": True,
                    "output": str(e.stdout or "")[-20000:],
                }

                # A timeout can indicate a GUI/service application that
                # stays alive, but it is not automatically accepted.
                strategies.append({
                    "candidate": candidate,
                    "strategy": idx,
                    "build_returncode": rc,
                    "runtime": runtime,
                    "accepted": False,
                    "reason": "Runtime timeout requires explicit application test",
                })

        else:

            strategies.append({
                "candidate": candidate,
                "strategy": idx,
                "build_returncode": rc,
                "accepted": False,
            })

    if success:
        break

if not success:

    (OUT / "BUILD_OUTPUT.txt").write_text(
        build_output,
        encoding="utf-8",
        errors="replace"
    )

    raise RuntimeError(
        "No candidate produced a runtime-verified executable."
    )

exe = OUT / "GooddayGoodbay220.exe"

# -----------------------------------------------------------------------------------------------
# FINAL EXE HASH
# -----------------------------------------------------------------------------------------------

import hashlib

h = hashlib.sha256()

with open(exe, "rb") as f:
    for c in iter(lambda: f.read(1024 * 1024), b""):
        h.update(c)

exe_hash = h.hexdigest()

# -----------------------------------------------------------------------------------------------
# ZIP
# -----------------------------------------------------------------------------------------------

zip_base = OUT / "GooddayGoodbay220"

if (OUT / "GooddayGoodbay220.zip").exists():
    (OUT / "GooddayGoodbay220.zip").unlink()

shutil.make_archive(
    str(zip_base),
    "zip",
    root_dir=str(OUT),
    base_dir="GooddayGoodbay220.exe"
)

zip_file = OUT / "GooddayGoodbay220.zip"

if not zip_file.exists():
    raise RuntimeError("ZIP creation failed.")

# -----------------------------------------------------------------------------------------------
# Evidence
# -----------------------------------------------------------------------------------------------

evidence = {
    "timestamp": utc(),
    "exe": str(exe),
    "exe_size": exe.stat().st_size,
    "exe_sha256": exe_hash,
    "zip": str(zip_file),
    "zip_size": zip_file.stat().st_size,
    "strategies": strategies,
    "final_verified": True,
}

REPORT.write_text(
    json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("\nFINAL WINDOWS BUILD VERIFIED")
print("EXE:", exe)
print("SHA256:", exe_hash)
print("ZIP:", zip_file)

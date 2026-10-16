#!/usr/bin/env python3
"""
AutoTest Engine - tools/autotest_engine.py
Simple Python "one-button" engine that can run smoke, e2e (Playwright), load (k6 via Docker) and security (OWASP ZAP via Docker) checks.
All new files live under Gooddaygoobuy221/ and this script does NOT modify existing repo files.

Usage examples:
  python3 Gooddaygoobuy221/tools/autotest_engine.py init
  python3 Gooddaygoobuy221/tools/autotest_engine.py run --target https://staging.example.com
  python3 Gooddaygoobuy221/tools/autotest_engine.py e2e --target https://staging.example.com

Environment variables:
  AUTOTEST_USER, AUTOTEST_PASS (optional) - credentials for tests
  AUTOTEST_TARGETS - comma-separated list of urls
  DOCKER_HOST (optional) - if running Docker remotely

This script prefers running locally. For CI, see Gooddaygoobuy221/tools/README.md
"""

import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import requests

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
TOOLS = ROOT / "tools"
TESTS = ROOT.parent / "tests_playwright"

def ensure_artifacts():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd, cwd=None, env=None, check=True):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, env=env or os.environ, check=check)


def init(args):
    # create venv and install minimal deps
    venv_dir = TOOLS / ".venv"
    if not venv_dir.exists():
        print("Creating virtualenv...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])
    pip = str(venv_dir / "bin" / "pip")
    python = str(venv_dir / "bin" / "python")
    print("Installing Python dependencies into venv...")
    run_cmd([pip, "install", "--upgrade", "pip"]) 
    run_cmd([pip, "install", "playwright", "requests"]) 
    print("Installing Playwright browsers (this may take a while)...")
    run_cmd([python, "-m", "playwright", "install"]) 
    print("Init complete. To use the venv: source tools/.venv/bin/activate")


def smoke(args):
    ensure_artifacts()
    targets = _get_targets(args)
    results = []
    for url in targets:
        try:
            print(f"[smoke] GET {url}")
            r = requests.get(url, timeout=15)
            ok = r.status_code < 400
            results.append((url, r.status_code, ok))
            print(f" -> {r.status_code}")
        except Exception as e:
            print(f" -> ERROR {e}")
            results.append((url, None, False))
    # write simple report
    now = datetime.utcnow().isoformat()
    rpt = ARTIFACTS / f"smoke_report_{now}.txt"
    with rpt.open("w") as fh:
        for url, code, ok in results:
            fh.write(f"{url}\t{code}\t{ok}\n")
    print("Smoke finished. Report:", rpt)


def e2e(args):
    """Simple Playwright scenario using the sync API - navigates to target and captures screenshot."""
    ensure_artifacts()
    targets = _get_targets(args)
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("Playwright not installed or browsers not available. Run: python3 Gooddaygoobuy221/tools/autotest_engine.py init")
        raise

    for url in targets:
        print(f"[e2e] Running basic scenario against {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(1000)
                screenshot = ARTIFACTS / f"screenshot_{_safe_name(url)}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                print(f"Screenshot saved to {screenshot}")
            except Exception as e:
                print("E2E step failed:", e)
            finally:
                browser.close()


def load(args):
    ensure_artifacts()
    # attempt to run k6 in docker
    script = TOOLS / "k6_script.js"
    if not script.exists():
        print("k6 script not found at", script)
        return
    if shutil.which("docker") is None:
        print("Docker not found. Install Docker to run k6 in container or run k6 locally.")
        return
    targets = _get_targets(args)
    target = targets[0]
    out = ARTIFACTS / "k6_report.txt"
    cmd = [
        "docker", "run", "--rm",
        "-i",
        "loadimpact/k6:latest",
        "run", "-e", f"TARGET={target}", "-"
    ]
    print("Running k6 (container). This will stream output to console and save to report")
    with script.open("rb") as js:
        p = subprocess.Popen(cmd, stdin=js, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = p.communicate()
        out.write_bytes(stdout or b"")
    print("k6 finished. Report:", out)


def security(args):
    ensure_artifacts()
    # run OWASP ZAP baseline with Docker
    if shutil.which("docker") is None:
        print("Docker not found. Install Docker to run OWASP ZAP container.")
        return
    targets = _get_targets(args)
    target = targets[0]
    report = ARTIFACTS / "zap_report.html"
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{str(ARTIFACTS)}:/zap/wrk",
        "owasp/zap2docker-stable",
        "zap-baseline.py", "-t", target, "-r", f"/zap/wrk/{report.name}", "-q"
    ]
    print("Running OWASP ZAP baseline scan (this may take several minutes)...")
    run_cmd(cmd)
    print("ZAP report:", report)


def run_all(args):
    # convenience: smoke -> e2e -> load -> security (skippable)
    smoke(args)
    e2e(args)
    if args.do_load:
        load(args)
    if args.do_security:
        security(args)


def _get_targets(args):
    if args.target:
        return [args.target]
    env = os.environ.get("AUTOTEST_TARGETS")
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    # fallback example target
    return ["https://example.com"]


def _safe_name(url):
    return url.replace("https://", "").replace("http://", "").replace("/", "_")


def main():
    parser = argparse.ArgumentParser(description="AutoTest Engine CLI")
    parser.add_argument("command", choices=["init","smoke","e2e","load","security","run"], help="command to run")
    parser.add_argument("--target", help="single target URL to test")
    parser.add_argument("--do-load", action="store_true", help="run load tests as part of run")
    parser.add_argument("--do-security", action="store_true", help="run security scan as part of run")
    args = parser.parse_args()

    try:
        if args.command == "init":
            init(args)
        elif args.command == "smoke":
            smoke(args)
        elif args.command == "e2e":
            e2e(args)
        elif args.command == "load":
            load(args)
        elif args.command == "security":
            security(args)
        elif args.command == "run":
            run_all(args)
    except subprocess.CalledProcessError as e:
        print("Command failed:", e)
        sys.exit(2)

if __name__ == "__main__":
    main()

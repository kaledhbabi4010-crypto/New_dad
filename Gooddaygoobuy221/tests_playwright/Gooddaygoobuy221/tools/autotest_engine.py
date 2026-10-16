#!/usr/bin/env python3
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

def ensure_artifacts():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd, cwd=None, env=None, check=True):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, env=env or os.environ, check=check)

def init(args):
    venv_dir = TOOLS / ".venv"
    if not venv_dir.exists():
        print("Creating virtualenv...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])
    pip = str(venv_dir / "bin" / "pip")
    python = str(venv_dir / "bin" / "python")
    print("Installing Python dependencies...")
    run_cmd([pip, "install", "--upgrade", "pip"])
    run_cmd([pip, "install", "playwright", "requests"])
    print("Installing Playwright browsers...")
    run_cmd([python, "-m", "playwright", "install"])
    print("Init complete.")

def smoke(args):
    ensure_artifacts()
    targets = _get_targets(args)
    results = []
    for url in targets:
        try:
            r = requests.get(url, timeout=15)
            ok = r.status_code < 400
            results.append((url, r.status_code, ok))
            print(f"[smoke] {url} -> {r.status_code}")
        except Exception as e:
            print(f"[smoke] {url} -> ERROR {e}")
            results.append((url, None, False))
    now = datetime.utcnow().isoformat()
    rpt = ARTIFACTS / f"smoke_report_{now}.txt"
    with rpt.open("w") as fh:
        for url, code, ok in results:
            fh.write(f"{url}\t{code}\t{ok}\n")
    print("Smoke finished. Report:", rpt)

def e2e(args):
    ensure_artifacts()
    targets = _get_targets(args)
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright not installed. Run: python3 Gooddaygoobuy221/tools/autotest_engine.py init")
        return
    for url in targets:
        print(f"[e2e] Running against {url}")
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
    if shutil.which("docker") is None:
        print("Docker not found. Install Docker to run k6 in container.")
        return
    script = TOOLS / "k6_script.js"
    if not script.exists():
        print("Missing k6 script at", script)
        return
    target = _get_targets(args)[0]
    out = ARTIFACTS / "k6_report.txt"
    cmd = ["docker", "run", "--rm", "-i", "grafana/k6:latest", "run", "-e", f"TARGET={target}", "-"]
    print("Running k6 in Docker...")
    with script.open("rb") as js:
        p = subprocess.Popen(cmd, stdin=js, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = p.communicate()
        out.write_bytes(stdout or b"")
    print("k6 finished. Report:", out)

def security(args):
    ensure_artifacts()
    if shutil.which("docker") is None:
        print("Docker not found. Install Docker to run OWASP ZAP.")
        return
    target = _get_targets(args)[0]
    report = ARTIFACTS / "zap_report.html"
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{str(ARTIFACTS)}:/zap/wrk",
        "owasp/zap2docker-stable",
        "zap-baseline.py", "-t", target, "-r", f"/zap/wrk/{report.name}", "-q"
    ]
    print("Running OWASP ZAP baseline scan...")
    run_cmd(cmd)
    print("ZAP report:", report)

def run_all(args):
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
    return ["https://example.com"]

def _safe_name(url):
    return url.replace("https://", "").replace("http://", "").replace("/", "_")

def main():
    parser = argparse.ArgumentParser(description="AutoTest Engine CLI")
    parser.add_argument("command", choices=["init","smoke","e2e","load","security","run"])
    parser.add_argument("--target", help="single target URL to test")
    parser.add_argument("--do-load", action="store_true")
    parser.add_argument("--do-security", action="store_true")
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

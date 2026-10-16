AutoTest Engine
================

Location: Gooddaygoobuy221/tools/

What this adds
- A Python "engine" (autotest_engine.py) that can run:
  - init: creates a venv and installs Playwright + dependencies
  - smoke: simple HTTP GET checks
  - e2e: basic Playwright scenario that captures a screenshot
  - load: runs k6 in Docker using tools/k6_script.js
  - security: runs OWASP ZAP baseline scan in Docker

- A helper shell script tools/run_engine.sh that runs the whole pipeline with one command.
- Example Playwright test in tests_playwright/test_login.py
- k6 script at tools/k6_script.js and zap_scan helper scripts.

Quickstart (local)
1) Run locally (example):
   ./Gooddaygoobuy221/tools/run_engine.sh https://staging.example.com

2) Or run steps manually:
   python3 Gooddaygoobuy221/tools/autotest_engine.py init
   python3 Gooddaygoobuy221/tools/autotest_engine.py smoke --target https://staging.example.com
   python3 Gooddaygoobuy221/tools/autotest_engine.py e2e --target https://staging.example.com

Notes & safety
- Do not run these tests against third-party production systems without explicit permission.
- Provide credentials via environment variables (AUTOTEST_USER / AUTOTEST_PASS) if needed; do not put secrets in the repo.

CI / GitHub Actions
- You can wire tools/run_engine.sh into a workflow_dispatch GitHub Actions workflow to get a "Run workflow" button.

Artifacts
- Test outputs (screenshots, reports) are written to Gooddaygoobuy221/artifacts/


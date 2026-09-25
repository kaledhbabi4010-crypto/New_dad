#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "KHALED_WORKFLOW_FINAL.py"

result = subprocess.run(
    [sys.executable, str(ENGINE)],
    cwd=str(ROOT),
    text=True
)

print("ENGINE_RETURN_CODE:", result.returncode)

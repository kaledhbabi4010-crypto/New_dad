#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KHALED-27 — GOODBAY220 AUTOMATED SOFTWARE FACTORY WORKFLOW
===========================================================

PURPOSE
-------
This file is the orchestration layer for the GOODBAY220 specification.

It is designed to automate:

1. Repository discovery
2. Specification discovery and validation
3. Requirement / RTM validation
4. Environment detection
5. Source/build validation
6. Unit/integration/security testing
7. MCP testing through explicitly configured external runners
8. Real Revit host testing on Windows
9. Real AutoCAD host testing on Windows
10. Install / verify / repair / upgrade / rollback / uninstall testing
11. Persistence audit
12. Evidence collection
13. Failure diagnosis
14. Controlled repair cycles
15. Rebuild/retest cycles
16. Release qualification

TRUTH RULE
----------
No PASS is inferred from:
- source existence
- build invocation alone
- test discovery alone
- process existence alone
- AI output
- MCP protocol success alone
- Revit/AutoCAD executable detection alone

REAL HOST PASS requires actual execution + verification evidence.

RELEASE RULE
------------
The workflow releases only when required evidence is present.

If a required external environment is unavailable:
    BLOCKED / UNVERIFIED

It never converts BLOCKED into PASS.

AI RULE
-------
AI is advisory only.
AI proposals must pass validation and execution gates.
AI output is never directly executed as shell code.

NO PERSISTENCE
--------------
This workflow itself does not create:
- Windows services
- startup persistence
- tray agents
- watchdogs
- hidden scheduled tasks
- permanent sockets
- self-relaunch loops

EXTERNAL REAL HOST TESTING
--------------------------
Real Revit / AutoCAD testing requires a Windows machine with the
actual Autodesk application installed.

The workflow can invoke an explicitly configured test adapter/command.
It does not pretend that a generic cloud runner is equivalent to
real Autodesk desktop execution.

IMPORTANT
---------
This file is an orchestrator. It does not magically manufacture
Autodesk licenses, Revit installations, AutoCAD installations,
GitHub runners, or missing source code.

All results are evidence based.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import enum
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ============================================================================
# 001 — IDENTITY
# ============================================================================

WORKFLOW_NAME = "KHALED-27"
PRODUCT_NAME = "GOODBAY220"
AUTODESK_RUNTIME = "REVO AI"

WORKFLOW_VERSION = "27.0.0"
SCHEMA_VERSION = "27.0"

TRUTH_HIERARCHY = (
    "REAL_EXECUTION",
    "EVIDENCE",
    "REPRODUCIBLE_TEST",
    "SOURCE",
    "AI_REASONING",
)

MAX_REPAIR_ATTEMPTS = 5
COMMAND_TIMEOUT_SECONDS = 1800

EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_INVALID_ARGUMENT = 2
EXIT_POLICY_DENIED = 3
EXIT_NOT_AUTHORIZED = 4
EXIT_UNSUPPORTED = 5
EXIT_VERIFICATION_FAILED = 6
EXIT_RECOVERY_REQUIRED = 7
EXIT_PARTIAL = 8
EXIT_BLOCKED = 9
EXIT_CANCELLED = 10


# ============================================================================
# 002 — ENUMERATIONS
# ============================================================================

class TruthState(str, enum.Enum):
    PROVEN = "PROVEN"
    VERIFIED = "VERIFIED"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    UNVERIFIED = "UNVERIFIED"


class TestStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SKIPPED = "SKIPPED"
    INVALID = "INVALID"


class CompatibilityState(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class OperationState(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"


class CommandType(str, enum.Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    VALIDATE = "VALIDATE"
    PLAN = "PLAN"
    SIMULATE = "SIMULATE"
    MUTATE = "MUTATE"
    VERIFY = "VERIFY"
    RECOVER = "RECOVER"


class Ownership(str, enum.Enum):
    OWNED = "OWNED"
    SHARED = "SHARED"
    UNKNOWN = "UNKNOWN"


class ClaimRelation(str, enum.Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"


# ============================================================================
# 003 — DATA CONTRACTS
# ============================================================================

@dataclasses.dataclass
class Evidence:
    evidence_id: str
    evidence_type: str
    source: str
    scope: str
    timestamp: str
    truth_state: TruthState
    integrity_hash: str
    data: Dict[str, Any]
    references: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Requirement:
    requirement_id: str
    axis_number: int
    title: str
    requirement: str
    component: str
    status: str = "UNVERIFIED"
    truth_state: TruthState = TruthState.UNVERIFIED
    test_ids: List[str] = dataclasses.field(default_factory=list)
    evidence_ids: List[str] = dataclasses.field(default_factory=list)
    acceptance_criteria: str = ""


@dataclasses.dataclass
class Command:
    command_id: str
    command_type: CommandType
    target: str
    parameters: Dict[str, Any]
    preconditions: List[str]
    required_capabilities: List[str]
    risk: str
    approval_requirement: str
    timeout: int
    expected_result: Dict[str, Any]


@dataclasses.dataclass
class TestRecord:
    test_id: str
    name: str
    category: str
    status: TestStatus
    truth_state: TruthState
    started_at: str
    finished_at: str
    command: Optional[str] = None
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    evidence_ids: List[str] = dataclasses.field(default_factory=list)
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class RepairRecord:
    repair_id: str
    attempt: int
    diagnosis: str
    action: str
    status: TestStatus
    evidence_ids: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ReleaseGateResult:
    qualified: bool
    status: str
    blockers: List[str]
    warnings: List[str]
    evidence_count: int
    tests_total: int
    tests_passed: int
    tests_failed: int
    tests_blocked: int


# ============================================================================
# 004 — AXIS REGISTER
# ============================================================================

AXIS_GROUPS = {
    (1, 100): "Identity and Architecture",
    (101, 200): "Data and Contracts",
    (201, 300): "Security and Privilege",
    (301, 400): "Lifecycle and Installation",
    (401, 500): "Runtime and Autodesk",
    (501, 600): "Healing and Recovery",
    (601, 700): "AI and Network",
    (701, 800): "Evidence Truth Audit",
    (801, 900): "Testing Reliability",
    (901, 1000): "Release Operations Maintainability",
}


def axis_group(number: int) -> str:
    for (low, high), name in AXIS_GROUPS.items():
        if low <= number <= high:
            return name
    return "UNKNOWN"


def create_axis_register() -> List[Requirement]:
    """
    Creates the structural 1000-axis register.

    IMPORTANT:
    This does NOT invent implementation proof.
    A generated axis remains UNVERIFIED until linked to actual
    specification text, implementation, tests and evidence.
    """
    result: List[Requirement] = []

    for number in range(1, 1001):
        rid = f"K27-AXIS-{number:04d}"
        group = axis_group(number)

        result.append(
            Requirement(
                requirement_id=rid,
                axis_number=number,
                title=f"{group} — Axis {number:04d}",
                requirement="PENDING_SPECIFICATION_TRACEABILITY",
                component=group,
                status="UNVERIFIED",
                truth_state=TruthState.UNVERIFIED,
                acceptance_criteria="Requirement must be linked to specification, implementation, test and evidence.",
            )
        )

    return result


def validate_axis_register(register: Sequence[Requirement]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if len(register) != 1000:
        errors.append(f"Expected 1000 axes, found {len(register)}")

    ids = set()

    for item in register:
        if item.requirement_id in ids:
            errors.append(f"Duplicate RequirementId: {item.requirement_id}")

        ids.add(item.requirement_id)

        if item.axis_number < 1 or item.axis_number > 1000:
            errors.append(f"Invalid axis number: {item.axis_number}")

        expected = f"K27-AXIS-{item.axis_number:04d}"

        if item.requirement_id != expected:
            errors.append(
                f"Invalid RequirementId {item.requirement_id}; expected {expected}"
            )

    return len(errors) == 0, errors


# ============================================================================
# 005 — UTILITIES
# ============================================================================

def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def json_hash(data: Any) -> str:
    raw = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return sha256_bytes(raw)


def safe_text(value: Any, limit: int = 100_000) -> str:
    text = str(value)

    if len(text) > limit:
        return text[:limit] + "\n...[TRUNCATED]..."

    return text


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def executable_exists(name: str) -> bool:
    return shutil.which(name) is not None


def find_first(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        try:
            if p.exists():
                return p
        except OSError:
            continue

    return None


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )


# ============================================================================
# 006 — REPOSITORY
# ============================================================================

class Repository:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.evidence_dir = self.root / ".khaled27" / "evidence"
        self.logs_dir = self.root / ".khaled27" / "logs"
        self.reports_dir = self.root / ".khaled27" / "reports"
        self.backups_dir = self.root / ".khaled27" / "backups"
        self.artifacts_dir = self.root / ".khaled27" / "artifacts"

    def bootstrap(self) -> None:
        for p in (
            self.evidence_dir,
            self.logs_dir,
            self.reports_dir,
            self.backups_dir,
            self.artifacts_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)

    def find_files(self, patterns: Sequence[str]) -> List[Path]:
        result = []

        for pattern in patterns:
            result.extend(self.root.rglob(pattern))

        return sorted(set(result))

    def find_specification(self) -> Optional[Path]:
        candidates = self.find_files(
            (
                "*GOODBAY220*.md",
                "*GOODBAY220*.txt",
                "*GOODBAY220*.py",
                "*goodbay220*.md",
                "*goodbay220*.txt",
                "*goodbay220*.py",
                "GOODBAY220*",
            )
        )

        candidates = [
            p
            for p in candidates
            if ".git" not in p.parts
            and ".khaled27" not in p.parts
        ]

        return candidates[0] if candidates else None


# ============================================================================
# 007 — EVIDENCE STORE
# ============================================================================

class EvidenceStore:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.items: List[Evidence] = []

    def add(
        self,
        evidence_type: str,
        source: str,
        scope: str,
        truth_state: TruthState,
        data: Dict[str, Any],
        references: Optional[List[str]] = None,
    ) -> Evidence:

        timestamp = now_utc()

        evidence_id = new_id("EVIDENCE")

        payload = {
            "evidence_id": evidence_id,
            "type": evidence_type,
            "source": source,
            "scope": scope,
            "timestamp": timestamp,
            "truth_state": truth_state.value,
            "data": data,
            "references": references or [],
        }

        integrity = json_hash(payload)

        item = Evidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            source=source,
            scope=scope,
            timestamp=timestamp,
            truth_state=truth_state,
            integrity_hash=integrity,
            data=data,
            references=references or [],
        )

        self.items.append(item)

        self.flush(item)

        return item

    def flush(self, evidence: Evidence) -> None:
        filename = (
            self.repository.evidence_dir
            / f"{evidence.evidence_id}.json"
        )

        write_json(
            filename,
            dataclasses.asdict(evidence),
        )

    def export_bundle(self) -> Path:
        bundle = {
            "workflow": WORKFLOW_NAME,
            "version": WORKFLOW_VERSION,
            "generated_at": now_utc(),
            "evidence": [
                dataclasses.asdict(x)
                for x in self.items
            ],
        }

        path = (
            self.repository.artifacts_dir
            / "evidence_bundle.json"
        )

        write_json(path, bundle)

        return path


# ============================================================================
# 008 — AUDIT LOGGER
# ============================================================================

class AuditLogger:
    def __init__(self, repository: Repository):
        self.path = (
            repository.logs_dir
            / "khaled27_audit.jsonl"
        )

    def log(
        self,
        event: str,
        **data: Any,
    ) -> None:

        record = {
            "timestamp": now_utc(),
            "event": event,
            "workflow": WORKFLOW_NAME,
            "version": WORKFLOW_VERSION,
            "data": data,
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )


# ============================================================================
# 009 — SECURITY POLICY
# ============================================================================

class SecurityPolicy:
    """
    Policy layer.

    It intentionally does NOT permit arbitrary AI-generated shell commands.

    External commands may only be invoked when explicitly configured by
    the repository/environment owner.
    """

    ALLOWED_PROGRAMS = {
        "python",
        "python3",
        "git",
        "dotnet",
        "pytest",
        "msbuild",
        "nuget",
        "powershell",
        "pwsh",
        "where",
        "which",
        "cmd",
    }

    FORBIDDEN_PERSISTENCE = (
        "schtasks /create",
        "new-service",
        "sc create",
        "reg add hkcu\\software\\microsoft\\windows\\currentversion\\run",
        "reg add hklm\\software\\microsoft\\windows\\currentversion\\run",
    )

    def validate_program(self, program: str) -> Tuple[bool, str]:
        name = Path(program).name.lower()

        if name not in self.ALLOWED_PROGRAMS:
            return False, f"Program not allowlisted: {name}"

        return True, "ALLOWLISTED"

    def validate_text(self, command: str) -> Tuple[bool, str]:
        lowered = command.lower()

        for forbidden in self.FORBIDDEN_PERSISTENCE:
            if forbidden in lowered:
                return False, f"Forbidden persistence command: {forbidden}"

        return True, "POLICY_OK"


# ============================================================================
# 010 — EXECUTION GATE
# ============================================================================

class ExecutionGate:
    def __init__(self, policy: SecurityPolicy):
        self.policy = policy

    def authorize(
        self,
        command: Sequence[str],
        mutation: bool = False,
    ) -> Tuple[bool, str]:

        if not command:
            return False, "EMPTY_COMMAND"

        ok, reason = self.policy.validate_program(command[0])

        if not ok:
            return False, reason

        rendered = " ".join(map(str, command))

        ok, reason = self.policy.validate_text(rendered)

        if not ok:
            return False, reason

        if mutation and os.environ.get(
            "KHALED27_ALLOW_MUTATION",
            "",
        ).lower() not in ("1", "true", "yes"):

            return False, (
                "MUTATION_NOT_AUTHORIZED: "
                "set KHALED27_ALLOW_MUTATION=true "
                "in the controlled execution environment"
            )

        return True, "AUTHORIZED"


# ============================================================================
# 011 — DETERMINISTIC EXECUTOR
# ============================================================================

class DeterministicExecutor:
    def __init__(
        self,
        gate: ExecutionGate,
        logger: AuditLogger,
    ):
        self.gate = gate
        self.logger = logger

    def run(
        self,
        command: Sequence[str],
        cwd: Path,
        timeout: int = COMMAND_TIMEOUT_SECONDS,
        mutation: bool = False,
    ) -> Tuple[int, str, str]:

        authorized, reason = self.gate.authorize(
            command,
            mutation=mutation,
        )

        self.logger.log(
            "EXECUTION_REQUEST",
            command=list(command),
            cwd=str(cwd),
            authorized=authorized,
            reason=reason,
        )

        if not authorized:
            raise PermissionError(reason)

        started = time.time()

        process = subprocess.run(
            list(command),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

        elapsed = time.time() - started

        stdout = safe_text(process.stdout)
        stderr = safe_text(process.stderr)

        self.logger.log(
            "EXECUTION_RESULT",
            command=list(command),
            return_code=process.returncode,
            elapsed_seconds=elapsed,
            stdout=stdout,
            stderr=stderr,
        )

        return process.returncode, stdout, stderr


# ============================================================================
# 012 — ENVIRONMENT DETECTOR
# ============================================================================

class EnvironmentDetector:
    def detect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "timestamp": now_utc(),
            "os": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": sys.version,
            "cwd": os.getcwd(),
            "hostname": socket.gethostname(),
            "executables": {},
            "autodesk": {},
        }

        for program in (
            "python",
            "git",
            "dotnet",
            "pytest",
            "msbuild",
            "powershell",
            "pwsh",
        ):
            result["executables"][program] = shutil.which(program)

        result["autodesk"] = self.detect_autodesk()

        return result

    def detect_autodesk(self) -> Dict[str, Any]:
        if not is_windows():
            return {
                "windows": False,
                "revit": [],
                "autocad": [],
            }

        roots = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(
                os.environ.get(
                    "ProgramW6432",
                    r"C:\Program Files",
                )
            ),
            Path(
                os.environ.get(
                    "ProgramFiles(x86)",
                    r"C:\Program Files (x86)",
                )
            ),
        ]

        revit: List[str] = []
        autocad: List[str] = []

        for root in roots:
            try:
                if not root.exists():
                    continue

                for p in root.glob(
                    "Autodesk/Revit */Revit.exe"
                ):
                    revit.append(str(p))

                for p in root.glob(
                    "Autodesk/AutoCAD */acad.exe"
                ):
                    autocad.append(str(p))

            except OSError:
                continue

        return {
            "windows": True,
            "revit": sorted(set(revit)),
            "autocad": sorted(set(autocad)),
        }


# ============================================================================
# 013 — SPECIFICATION ENGINE
# ============================================================================

class SpecificationEngine:
    def __init__(
        self,
        repository: Repository,
        evidence: EvidenceStore,
        logger: AuditLogger,
    ):
        self.repository = repository
        self.evidence = evidence
        self.logger = logger

    def inspect(self) -> Dict[str, Any]:
        path = self.repository.find_specification()

        if not path:
            self.evidence.add(
                "SPECIFICATION",
                "SpecificationEngine",
                "GOODBAY220",
                TruthState.UNKNOWN,
                {
                    "found": False,
                    "message": "GOODBAY220 specification not found",
                },
            )

            return {
                "found": False,
                "path": None,
            }

        content = read_text_file(path)

        checks = {
            "contains_goodbay220": "GOODBAY220" in content.upper(),
            "contains_truth_rule": (
                "TRUTH" in content.upper()
                or "EVIDENCE" in content.upper()
            ),
            "contains_revit": "REVIT" in content.upper(),
            "contains_autocad": "AUTOCAD" in content.upper(),
            "contains_security": "SECURITY" in content.upper(),
            "contains_recovery": "RECOVERY" in content.upper(),
            "contains_testing": "TEST" in content.upper(),
        }

        result = {
            "found": True,
            "path": str(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "checks": checks,
        }

        self.evidence.add(
            "SPECIFICATION",
            str(path),
            "GOODBAY220",
            TruthState.OBSERVED,
            result,
        )

        return result


# ============================================================================
# 014 — BUILD ENGINE
# ============================================================================

class BuildEngine:
    def __init__(
        self,
        repository: Repository,
        executor: DeterministicExecutor,
        evidence: EvidenceStore,
        logger: AuditLogger,
    ):
        self.repository = repository
        self.executor = executor
        self.evidence = evidence
        self.logger = logger

    def locate_solution(self) -> Optional[Path]:
        candidates = [
            p
            for p in self.repository.root.rglob("*.sln")
            if ".git" not in p.parts
            and ".khaled27" not in p.parts
        ]

        return sorted(candidates)[0] if candidates else None

    def locate_project(self) -> Optional[Path]:
        candidates = [
            p
            for p in self.repository.root.rglob("*.csproj")
            if ".git" not in p.parts
            and ".khaled27" not in p.parts
        ]

        return sorted(candidates)[0] if candidates else None

    def run(self) -> TestRecord:
        started = now_utc()

        solution = self.locate_solution()
        project = self.locate_project()

        target = solution or project

        if not target:
            return TestRecord(
                test_id=new_id("TEST"),
                name="DOTNET_BUILD",
                category="BUILD",
                status=TestStatus.BLOCKED,
                truth_state=TruthState.UNVERIFIED,
                started_at=started,
                finished_at=now_utc(),
                details={
                    "reason": "No .sln or .csproj found",
                },
            )

        command = [
            "dotnet",
            "build",
            str(target),
            "--nologo",
        ]

        try:
            code, stdout, stderr = self.executor.run(
                command,
                self.repository.root,
            )

            status = (
                TestStatus.PASS
                if code == 0
                else TestStatus.FAIL
            )

            evidence = self.evidence.add(
                "BUILD_RESULT",
                "dotnet",
                str(target),
                TruthState.VERIFIED
                if code == 0
                else TruthState.OBSERVED,
                {
                    "target": str(target),
                    "return_code": code,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )

            return TestRecord(
                test_id=new_id("TEST"),
                name="DOTNET_BUILD",
                category="BUILD",
                status=status,
                truth_state=(
                    TruthState.VERIFIED
                    if code == 0
                    else TruthState.OBSERVED
                ),
                started_at=started,
                finished_at=now_utc(),
                command=" ".join(command),
                return_code=code,
                stdout=stdout,
                stderr=stderr,
                evidence_ids=[evidence.evidence_id],
            )

        except Exception as exc:
            return TestRecord(
                test_id=new_id("TEST"),
                name="DOTNET_BUILD",
                category="BUILD",
                status=TestStatus.FAIL,
                truth_state=TruthState.UNKNOWN,
                started_at=started,
                finished_at=now_utc(),
                details={
                    "exception": repr(exc),
                },
            )


# ============================================================================
# 015 — PYTHON TEST ENGINE
# ============================================================================

class PythonTestEngine:
    def __init__(
        self,
        repository: Repository,
        executor: DeterministicExecutor,
        evidence: EvidenceStore,
    ):
        self.repository = repository
        self.executor = executor
        self.evidence = evidence

    def discover_tests(self) -> List[Path]:
        return sorted(
            p
            for p in self.repository.root.rglob("test*.py")
            if ".git" not in p.parts
            and ".khaled27" not in p.parts
        )

    def run(self) -> TestRecord:
        started = now_utc()
        tests = self.discover_tests()

        if not tests:
            return TestRecord(
                test_id=new_id("TEST"),
                name="PYTHON_TEST_DISCOVERY",
                category="UNIT",
                status=TestStatus.BLOCKED,
                truth_state=TruthState.UNVERIFIED,
                started_at=started,
                finished_at=now_utc(),
                details={
                    "reason": "No Python tests discovered",
                },
            )

        if not executable_exists("pytest"):
            return TestRecord(
                test_id=new_id("TEST"),
                name="PYTHON_TESTS",
                category="UNIT",
                status=TestStatus.BLOCKED,
                truth_state=TruthState.UNVERIFIED,
                started_at=started,
                finished_at=now_utc(),
                details={
                    "reason": "pytest not installed",
                },
            )

        command = [
            "pytest",
            "-q",
        ]

        try:
            code, stdout, stderr = self.executor.run(
                command,
                self.repository.root,
            )

            status = (
                TestStatus.PASS
                if code == 0
                else TestStatus.FAIL
            )

            ev = self.evidence.add(
                "PYTHON_TEST_RESULT",
                "pytest",
                str(self.repository.root),
                TruthState.VERIFIED
                if code == 0
                else TruthState.OBSERVED,
                {
                    "return_code": code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "discovered_tests": [
                        str(x)
                        for x in tests
                    ],
                },
            )

            return TestRecord(
                test_id=new_id("TEST"),
                name="PYTHON_TESTS",
                category="UNIT",
                status=status,
                truth_state=(
                    TruthState.VERIFIED
                    if code == 0
                    else TruthState.OBSERVED
                ),
                started_at=started,
                finished_at=now_utc(),
                command="pytest -q",
                return_code=code,
                stdout=stdout,
                stderr=stderr,
                evidence_ids=[ev.evidence_id],
            )

        except Exception as exc:
            return TestRecord(
                test_id=new_id("TEST"),
                name="PYTHON_TESTS",
                category="UNIT",
                status=TestStatus.FAIL,
                truth_state=TruthState.UNKNOWN,
                started_at=started,
                finished_at=now_utc(),
                details={
                    "exception": repr(exc),
                },
            )


# ============================================================================
# 016 — STATIC SECURITY
# ============================================================================

class StaticSecurityScanner:
    """
    Conservative source scanner.

    It excludes:
    - .git
    - .khaled27
    - binary/build output

    It does not claim a complete security audit.
    """

    EXTENSIONS = {
        ".py",
        ".cs",
        ".csproj",
        ".json",
        ".xml",
        ".yml",
        ".yaml",
        ".ps1",
        ".cmd",
        ".bat",
        ".md",
        ".txt",
    }

    DANGEROUS_PATTERNS = ()

    CLOUD_AI = None

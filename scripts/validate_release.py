#!/usr/bin/env python3
"""Validate the curated release without the private simulation baseline."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_body_v2() -> dict:
    """The frozen decision is public; the trial data is archived pre-publication."""
    folder = CASES / "body-v2"
    readme = (folder / "README.md").read_text(encoding="utf-8")
    require("gate: false" in readme, "body-v2 archived decision line missing")
    require(not any(folder.glob("*.csv")), "body-v2 trial data must stay archived")
    require(not any(folder.glob("*.json")), "body-v2 result data must stay archived")
    return {"gate_pass": False, "archived": True, "success_gain": None}

def check_latency() -> dict:
    """Archived case: only the decision summary stays public."""
    folder = CASES / "latency"
    readme = (folder / "README.md").read_text(encoding="utf-8")
    require('"not evaluated"' in readme, "latency GTSAM boundary line missing")
    require(not any(folder.glob("*.csv")), "latency tables must stay archived")
    require(not any(folder.glob("*.json")), "latency results must stay archived")
    return {
        "filterpy_gate_pass": False,
        "gtsam_behavior_gate": "not_evaluated",
        "archived": True,
    }

def check_posture() -> dict:
    """Archived case: descriptive diagnostic, data held back pre-publication."""
    folder = CASES / "posture"
    readme = (folder / "README.md").read_text(encoding="utf-8")
    require("descriptive" in readme, "posture descriptive boundary line missing")
    require(not any(folder.glob("*.csv")), "posture table must stay archived")
    require(not any(folder.glob("*.json")), "posture results must stay archived")
    return {"rows": None, "interpretation": "descriptive_only", "archived": True}

def check_execution_evidence() -> dict:
    folder = CASES / "execution-evidence"
    with tempfile.TemporaryDirectory(prefix="research-gates-") as temp:
        output = Path(temp) / "replay-output"
        completed = subprocess.run(
            [sys.executable, str(folder / "replay_bus.py"), "--out", str(output)],
            cwd=folder,
            check=False,
            capture_output=True,
            text=True,
        )
        require(completed.returncode == 0, completed.stderr or completed.stdout)
        summary = load_json(output / "replay-summary.json")
        require(summary["gate"]["status"] == "pass", "execution-evidence gate failed")
        require(summary["adapted_events"] == 24, "unexpected adapted-event count")
        require(summary["episodes"] == 8, "unexpected episode count")
        require(all(summary["gate"]["checks"].values()), "execution-evidence check changed")
        return {"events": 24, "episodes": 8, "gate": "pass"}


def check_readiness(execution: dict, body: dict, latency: dict) -> dict:
    historical = load_json(CASES / "readiness" / "historical-gate-status.json")
    gates = {
        "execution_evidence_mechanism": execution["gate"] == "pass",
        "body_v2_behavior": body["gate_pass"] is True,
        "latency_estimator_behavior": latency["filterpy_gate_pass"] is True,
        "anchored_feedback_implementation": False,
    }
    blockers = [name for name, passed in gates.items() if not passed]
    require(blockers == historical["blockers"], "readiness blockers changed")
    require(not historical["experiment"]["formal_run_ready"], "formal experiment unexpectedly ready")
    return {"formal_run_ready": False, "blockers": blockers}


def check_release_hygiene() -> dict:
    text_suffixes = {".md", ".txt", ".json", ".jsonl", ".csv", ".py", ".yml", ".yaml", ".toml", ".cff"}
    patterns = {
        "absolute_windows_path": re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]"),
        "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I),
        "cloud_instance": re.compile(r"\bdsw-[a-z0-9]+\b", re.I),
        "credential_assignment": re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]+"),
    }
    failures: list[str] = []
    files = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in text_suffixes:
            continue
        files += 1
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for name, pattern in patterns.items():
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: {name}")
    require(not failures, "release hygiene failures: " + "; ".join(failures))
    return {"text_files_scanned": files, "failures": 0}


def validate() -> dict:
    body = check_body_v2()
    latency = check_latency()
    posture = check_posture()
    execution = check_execution_evidence()
    readiness = check_readiness(execution, body, latency)
    hygiene = check_release_hygiene()
    return {
        "status": "pass",
        "body_v2": body,
        "latency": latency,
        "posture": posture,
        "execution_evidence": execution,
        "readiness": readiness,
        "hygiene": hygiene,
    }


def main() -> int:
    try:
        report = validate()
    except Exception as exc:  # fail closed for a release check
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

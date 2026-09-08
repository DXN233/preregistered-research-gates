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
    folder = CASES / "body-v2"
    result = load_json(folder / "body-v2-results.json")
    trials = folder / "body-v2-trials.csv"
    require(sha256(trials) == result["design"]["trials_sha256"], "body-v2 trial hash mismatch")
    require(csv_rows(trials) == result["design"]["trials"], "body-v2 row count mismatch")
    gain = result["metrics"]["v2_full"]["success"] - result["metrics"]["v1"]["success"]
    require(abs(gain - result["full_vs_v1"]["success_gain"]) < 1e-12, "body-v2 gain mismatch")
    require(gain < 0.02, "body-v2 unexpectedly clears the frozen 2pp gate")
    require(result["representation_probe"]["gate_pass"] is True, "representation mechanism gate changed")
    require(result["gate_pass"] is False, "body-v2 final gate changed")
    return {"rows": csv_rows(trials), "success_gain": gain, "gate_pass": False}


def check_latency() -> dict:
    folder = CASES / "latency"
    result = load_json(folder / "filterpy-oosm-results.json")
    development = folder / "filterpy-oosm-development.csv"
    holdout = folder / "filterpy-oosm-holdout.csv"
    require(sha256(development) == result["development_trials_sha256"], "latency development hash mismatch")
    require(sha256(holdout) == result["holdout_trials_sha256"], "latency holdout hash mismatch")
    require(result["gate_pass"] is False, "FilterPy behavior gate changed")
    require(result["verdict"] == "filterpy_oosm_fail", "FilterPy verdict changed")
    stop = load_json(folder / "gtsam-throughput-stop.json")
    require(stop["status"] == "engineering_throughput_stop", "GTSAM stop status changed")
    require(stop["behaviorGate"] == "not_evaluated", "GTSAM behavior must remain unknown")
    require("dswInstance" not in stop.get("cloudCleanup", {}), "cloud instance identifier leaked")
    return {
        "development_rows": csv_rows(development),
        "holdout_rows": csv_rows(holdout),
        "filterpy_gate_pass": False,
        "gtsam_behavior_gate": "not_evaluated",
    }


def check_posture() -> dict:
    folder = CASES / "posture"
    result = load_json(folder / "severe-state-2x2-results.json")
    trials = folder / "severe-state-2x2-trials.csv"
    require(sha256(trials) == result["trials_sha256"], "posture trial hash mismatch")
    require(csv_rows(trials) == 4 * result["design"]["episodes_per_cell"], "posture row count mismatch")
    summaries = result["summaries"]
    require(summaries["delay_6_noise_0"]["success_rate"] == 0.0, "delay-only cell changed")
    require(summaries["delay_6_noise_0.0035"]["success_rate"] == 0.0, "delay-plus-noise cell changed")
    require(result["decision"]["interaction_is_not_identified"], "descriptive boundary missing")
    return {"rows": csv_rows(trials), "interpretation": "descriptive_only"}


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

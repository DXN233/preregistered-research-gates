from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_release", ROOT / "scripts" / "validate_release.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ReleaseCandidateTests(unittest.TestCase):
    def test_body_v2_gate(self):
        result = VALIDATOR.check_body_v2()
        self.assertFalse(result["gate_pass"])
        self.assertLess(result["success_gain"], 0.02)

    def test_latency_gate_and_throughput_boundary(self):
        result = VALIDATOR.check_latency()
        self.assertFalse(result["filterpy_gate_pass"])
        self.assertEqual(result["gtsam_behavior_gate"], "not_evaluated")

    def test_posture_is_descriptive(self):
        result = VALIDATOR.check_posture()
        self.assertEqual(result["interpretation"], "descriptive_only")

    def test_execution_evidence_replay(self):
        result = VALIDATOR.check_execution_evidence()
        self.assertEqual(result["gate"], "pass")

    def test_formal_experiment_stays_blocked(self):
        readiness = VALIDATOR.check_readiness(
            VALIDATOR.check_execution_evidence(),
            VALIDATOR.check_body_v2(),
            VALIDATOR.check_latency(),
        )
        self.assertFalse(readiness["formal_run_ready"])
        self.assertEqual(len(readiness["blockers"]), 3)

    def test_release_hygiene(self):
        self.assertEqual(VALIDATOR.check_release_hygiene()["failures"], 0)


if __name__ == "__main__":
    unittest.main()

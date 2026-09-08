import tempfile
import unittest
from pathlib import Path

from replay_bus import DEFAULT_SOURCE, ReplayBus, adapt_stage_events, evidence_payload_hash, gates, inject, run_scenario, validate_event


class ExecutionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events, cls.contexts = adapt_stage_events(DEFAULT_SOURCE, limit_episodes=8)

    def test_adapter_preserves_unknowns(self):
        event = self.events[0]
        self.assertEqual([], validate_event(event))
        self.assertIsNone(event["measurements"]["slip"])
        self.assertIsNone(event["measurements"]["torque_margin"])
        self.assertIn("measurements.slip", event["quality"]["unknown_fields"])

    def test_source_events_are_not_mutated_by_pollution(self):
        original = self.events[0]["body"]["body_id"]
        packets, _ = inject(self.events, "cross_body")
        self.assertEqual(original, self.events[0]["body"]["body_id"])
        self.assertEqual("foreign_body", packets[0]["event"]["body"]["body_id"])

    def test_payload_tampering_is_detected(self):
        event = dict(self.events[0])
        event["measurements"] = dict(event["measurements"])
        event["measurements"]["relation_error"] = 999.0
        self.assertIn("integrity.payload_sha256", validate_event(event))

    def test_cross_context_is_quarantined(self):
        report = run_scenario(self.events, self.contexts, "cross_task")
        self.assertEqual(0, report["pollution_accepted"])
        self.assertEqual(len(self.events), report["pollution_packets"])
        self.assertNotIn("integrity.payload_sha256", report["reason_counts"])

    def test_missing_permission_is_quarantined(self):
        packets, _ = inject(self.events[:1], "clean")
        event = packets[0]["event"]
        event["authority"]["permissions"].remove("propose_knowledge_patch")
        event["integrity"]["payload_sha256"] = evidence_payload_hash(event)
        bus = ReplayBus(self.contexts)
        bus.decide(packets[0])
        self.assertEqual("quarantine", bus.ledger[0]["decision"])
        self.assertTrue(any(code.startswith("permission_missing:") for code in bus.ledger[0]["reason_codes"]))

    def test_duplicate_is_idempotent(self):
        report = run_scenario(self.events, self.contexts, "duplicate")
        self.assertEqual(0, report["duplicate_second_writes"])
        self.assertEqual(len(self.events), report["knowledge_candidates"])
        self.assertEqual(len(self.events), report["decision_counts"]["duplicate"])

    def test_reorder_defers_then_flushes(self):
        report = run_scenario(self.events, self.contexts, "reorder")
        self.assertGreater(report["decision_counts"].get("defer", 0), 0)
        self.assertEqual(len(self.events), report["accepted_unique_events"])
        self.assertEqual(0, report["pending_after_replay"])

    def test_drop_does_not_skip_missing_phase(self):
        report = run_scenario(self.events, self.contexts, "drop")
        self.assertGreater(report["pending_after_replay"], 0)
        delivered = report["transport"]["delivered_packets"]
        self.assertLess(report["accepted_unique_events"], delivered)

    def test_latency_is_quarantined(self):
        report = run_scenario(self.events, self.contexts, "latency")
        self.assertEqual(len(self.events), report["decision_counts"]["quarantine"])
        self.assertIn("delivery_window_expired", report["reason_counts"])

    def test_all_frozen_gates(self):
        names = ["clean", "latency", "reorder", "drop", "duplicate", "cross_body", "cross_task", "mixed"]
        reports = {name: run_scenario(self.events, self.contexts, name) for name in names}
        result = gates(reports, len(self.events))
        self.assertEqual("pass", result["status"], result["checks"])


if __name__ == "__main__":
    unittest.main()

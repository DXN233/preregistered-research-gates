#!/usr/bin/env python3
"""ExecutionEvidence v0.1 offline adapter, fault injector and absorption bus."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "0.1.0"
POLICY_VERSION = "absorb-policy-0.1.0"
ADAPTER_VERSION = "stage-events-adapter-0.1.0"
UTC = timezone.utc
DEFAULT_SOURCE = Path(__file__).resolve().parent / "fixtures" / "stage-observer-events.recovered.csv"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any, length: int | None = None) -> str:
    result = hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()
    return result if length is None else result[:length]


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def as_float(value: str) -> float | None:
    if value in ("", "None", None):
        return None
    return float(value)


def as_bool(value: str) -> bool:
    return str(value).lower() == "true"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: Iterable[Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(canonical(value) + "\n")


def evidence_payload_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "integrity"}
    return digest(payload)


def episode_key(row: dict[str, str]) -> tuple[str, ...]:
    return (row["body"], row["task"], row["disturbance"], row["seed"], row["controller"])


def adapt_stage_events(source: Path, limit_episodes: int = 24) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Adapt legacy rows without pretending absent measurements were observed."""
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[episode_key(row)].append(row)

    # Deterministically round-robin complete traces across body/disturbance/controller strata.
    strata: dict[tuple[str, str, str], list[tuple[tuple[str, ...], list[dict[str, str]]]]] = defaultdict(list)
    for key, episode_rows in groups.items():
        indices = sorted(int(row["stage_index"]) for row in episode_rows)
        if indices == [0, 1, 2]:
            body, _task, disturbance, _seed, controller = key
            strata[(body, disturbance, controller)].append((key, episode_rows))
    for items in strata.values():
        items.sort(key=lambda pair: pair[0])
    ordered: list[tuple[tuple[str, ...], list[dict[str, str]]]] = []
    while len(ordered) < limit_episodes:
        progressed = False
        for stratum in sorted(strata):
            if strata[stratum] and len(ordered) < limit_episodes:
                ordered.append(strata[stratum].pop(0))
                progressed = True
        if not progressed:
            break
    base = datetime(2026, 9, 4, tzinfo=UTC)
    events: list[dict[str, Any]] = []
    contexts: dict[str, dict[str, Any]] = {}

    for episode_number, (key, episode_rows) in enumerate(ordered):
        body, task, disturbance, seed, controller = key
        episode_id = f"ep_{digest(key, 20)}"
        body_spec_version = "legacy-mujoco-spec-2026-09-03"
        knowledge_revision = "kr_stage-observer-frozen-2026-09-04"
        primitive = task.upper()
        principal = f"executor:{controller}"
        contexts[episode_id] = {
            "episode_id": episode_id,
            "task_id": task,
            "body_id": body,
            "body_spec_version": body_spec_version,
            "knowledge_revision": knowledge_revision,
            "allowed_primitives": [primitive],
            "allowed_principal": principal,
            "required_permissions": ["submit_evidence", "propose_transition", "propose_knowledge_patch"],
            "max_delivery_latency_ms": 5000,
            "min_confidence": 0.80,
        }
        episode_rows.sort(key=lambda row: int(row["stage_index"]))
        elapsed_total = 0
        for row_number, row in enumerate(episode_rows):
            elapsed_total += int(row["elapsed_steps"])
            executed = base + timedelta(seconds=episode_number * 20 + elapsed_total * 0.01)
            observed = executed - timedelta(milliseconds=20)
            feedback = executed + timedelta(milliseconds=100)
            passed = as_bool(row["passed"])
            source_record = {name: row[name] for name in sorted(row)}
            source_sha = digest(source_record)
            anchor = {
                "episode_id": episode_id,
                "task_id": task,
                "body_id": body,
                "body_spec_version": body_spec_version,
                "primitive": primitive,
                "phase_index": int(row["stage_index"]),
                "executed_at": iso(executed),
                "source_sha256": source_sha,
            }
            event = {
                "schema_version": SCHEMA_VERSION,
                "event_id": f"eev_{digest(anchor, 24)}",
                "idempotency_key": f"idem_{digest(anchor, 32)}",
                "episode_id": episode_id,
                "task_id": task,
                "body": {"body_id": body, "body_spec_version": body_spec_version, "representation_version": "v1"},
                "execution": {
                    "primitive": primitive,
                    "phase": row["stage_name"],
                    "phase_index": int(row["stage_index"]),
                    "observed_at": iso(observed),
                    "executed_at": iso(executed),
                    "feedback_at": iso(feedback),
                    "causal_window": {"start": iso(observed - timedelta(milliseconds=250)), "end": iso(feedback + timedelta(milliseconds=250))},
                },
                "measurements": {
                    "relation_error": as_float(row["relation_error"]),
                    "object_error": as_float(row["object_error"]),
                    "ee_speed": as_float(row["ee_speed"]),
                    "contact_state": "contact" if as_bool(row["contact"]) else "no_contact",
                    "slip": None,
                    "torque_margin": None,
                },
                "transition": {
                    "proposal": "advance" if passed else "recover",
                    "outcome": "accepted" if passed else "rejected",
                    "reason": row["transition_reason"],
                },
                "recovery": {"recoverable": disturbance != "severe", "requested_replan_scope": "none" if passed else "phase"},
                "confidence": {"value": 0.95, "method": "deterministic_legacy_adapter"},
                "provenance": {
                    "source_type": "simulation_log",
                    "source_uri": str(source),
                    "source_record_id": f"{episode_id}:stage:{row['stage_index']}:row:{row_number}",
                    "adapter_version": ADAPTER_VERSION,
                    "source_sha256": source_sha,
                },
                "safety_flags": ["legacy_time_derived"],
                "knowledge": {"base_revision": knowledge_revision, "write_intent": "propose_only"},
                "authority": {
                    "principal": principal,
                    "permissions": ["submit_evidence", "propose_transition", "propose_knowledge_patch"],
                    "scope": {"task_id": task, "body_id": body, "body_spec_version": body_spec_version, "primitive": primitive},
                },
                "experiment": {
                    "controller": controller,
                    "disturbance": disturbance,
                    "seed": int(seed),
                    "factors": {"body_representation": "v1", "feedback": "raw"},
                },
                "quality": {
                    "derived_fields": ["event_id", "idempotency_key", "episode_id", "execution.observed_at", "execution.executed_at", "execution.feedback_at", "execution.causal_window", "confidence"],
                    "unknown_fields": ["measurements.slip", "measurements.torque_margin"],
                },
            }
            event["integrity"] = {"algorithm": "sha256-canonical-json-v1", "payload_sha256": evidence_payload_hash(event)}
            events.append(event)
    return events, contexts


def validate_event(event: dict[str, Any]) -> list[str]:
    """Small runtime validator; the JSON Schema remains the normative contract."""
    errors: list[str] = []
    required = ["schema_version", "event_id", "idempotency_key", "episode_id", "task_id", "body", "execution", "measurements", "transition", "recovery", "confidence", "provenance", "safety_flags", "knowledge", "authority", "experiment", "quality", "integrity"]
    errors.extend(f"missing:{field}" for field in required if field not in event)
    if errors:
        return errors
    if event["schema_version"] != SCHEMA_VERSION:
        errors.append("schema_version")
    if not event["event_id"].startswith("eev_") or len(event["event_id"]) != 28:
        errors.append("event_id")
    if not event["idempotency_key"].startswith("idem_") or len(event["idempotency_key"]) != 37:
        errors.append("idempotency_key")
    confidence = event["confidence"].get("value")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("confidence.value")
    phase_index = event["execution"].get("phase_index")
    if not isinstance(phase_index, int) or phase_index < 0:
        errors.append("execution.phase_index")
    try:
        observed = parse_time(event["execution"]["observed_at"])
        executed = parse_time(event["execution"]["executed_at"])
        feedback = parse_time(event["execution"]["feedback_at"])
        start = parse_time(event["execution"]["causal_window"]["start"])
        end = parse_time(event["execution"]["causal_window"]["end"])
        if not start <= observed <= executed <= feedback <= end:
            errors.append("time_order")
    except (KeyError, TypeError, ValueError):
        errors.append("time_parse")
    if event["knowledge"].get("write_intent") != "propose_only":
        errors.append("knowledge.write_intent")
    if event["integrity"].get("algorithm") != "sha256-canonical-json-v1" or event["integrity"].get("payload_sha256") != evidence_payload_hash(event):
        errors.append("integrity.payload_sha256")
    return errors


def packet(event: dict[str, Any], delivered_at: datetime, scenario: str, packet_index: int) -> dict[str, Any]:
    return {
        "packet_id": f"pkt_{digest([scenario, packet_index, event['event_id']], 20)}",
        "scenario": scenario,
        "delivered_at": iso(delivered_at),
        "event": event,
    }


def inject(events: list[dict[str, Any]], scenario: str, seed: int = 20260904) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Transport faults never mutate the caller's source event list."""
    rng = random.Random(seed)
    base_packets = [packet(copy.deepcopy(event), parse_time(event["execution"]["feedback_at"]) + timedelta(milliseconds=200), scenario, index) for index, event in enumerate(events)]
    dropped = 0
    if scenario == "clean":
        result = base_packets
    elif scenario == "latency":
        result = base_packets
        for item in result:
            item["delivered_at"] = iso(parse_time(item["delivered_at"]) + timedelta(seconds=12))
    elif scenario == "reorder":
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in base_packets:
            groups[item["event"]["episode_id"]].append(item)
        result = []
        for episode_id in sorted(groups):
            result.extend(sorted(groups[episode_id], key=lambda item: item["event"]["execution"]["phase_index"], reverse=True))
    elif scenario == "drop":
        result = []
        for item in base_packets:
            if item["event"]["execution"]["phase_index"] == 1:
                dropped += 1
            else:
                result.append(item)
    elif scenario == "duplicate":
        result = []
        for index, item in enumerate(base_packets):
            result.append(item)
            duplicate = copy.deepcopy(item)
            duplicate["packet_id"] = f"pkt_dup_{digest([item['packet_id'], index], 16)}"
            duplicate["delivered_at"] = iso(parse_time(item["delivered_at"]) + timedelta(milliseconds=1))
            result.append(duplicate)
    elif scenario in {"cross_body", "cross_task"}:
        result = []
        for index, item in enumerate(base_packets):
            polluted = copy.deepcopy(item)
            polluted["packet_id"] = f"pkt_polluted_{digest([scenario, index], 16)}"
            if scenario == "cross_body":
                polluted["event"]["body"]["body_id"] = "foreign_body"
                polluted["event"]["authority"]["scope"]["body_id"] = "foreign_body"
            else:
                polluted["event"]["task_id"] = "foreign_task"
                polluted["event"]["authority"]["scope"]["task_id"] = "foreign_task"
            # Model a well-formed event routed to the wrong episode context, not an in-flight bit flip.
            polluted["event"]["integrity"]["payload_sha256"] = evidence_payload_hash(polluted["event"])
            result.append(polluted)
    elif scenario == "mixed":
        result = base_packets
        rng.shuffle(result)
        result = [item for index, item in enumerate(result) if index % 11 != 0]
        dropped = len(base_packets) - len(result)
        extras = []
        for index, item in enumerate(result[: max(1, len(result) // 8)]):
            duplicate = copy.deepcopy(item)
            duplicate["packet_id"] = f"pkt_mixed_dup_{digest([index, item['packet_id']], 16)}"
            extras.append(duplicate)
        result.extend(extras)
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return result, {"source_events": len(events), "delivered_packets": len(result), "dropped_packets": dropped}


@dataclass
class EpisodeState:
    next_phase: int = 0


class ReplayBus:
    def __init__(self, contexts: dict[str, dict[str, Any]]) -> None:
        self.contexts = contexts
        self.states: dict[str, EpisodeState] = defaultdict(EpisodeState)
        self.seen: set[str] = set()
        self.pending: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self.ledger: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []

    def decide(self, item: dict[str, Any], from_pending: bool = False) -> str:
        event = item["event"]
        reasons = validate_event(event)
        context = self.contexts.get(event.get("episode_id", ""))
        if context is None:
            reasons.append("unknown_episode")
        if context is not None:
            comparisons = {
                "task_mismatch": (event["task_id"], context["task_id"]),
                "body_mismatch": (event["body"]["body_id"], context["body_id"]),
                "body_spec_version_mismatch": (event["body"]["body_spec_version"], context["body_spec_version"]),
                "knowledge_revision_mismatch": (event["knowledge"]["base_revision"], context["knowledge_revision"]),
                "principal_mismatch": (event["authority"]["principal"], context["allowed_principal"]),
            }
            reasons.extend(code for code, pair in comparisons.items() if pair[0] != pair[1])
            if event["execution"]["primitive"] not in context["allowed_primitives"]:
                reasons.append("primitive_not_allowed")
            missing_permissions = sorted(set(context["required_permissions"]) - set(event["authority"]["permissions"]))
            if missing_permissions:
                reasons.append("permission_missing:" + ",".join(missing_permissions))
            scope = event["authority"]["scope"]
            expected_scope = {"task_id": context["task_id"], "body_id": context["body_id"], "body_spec_version": context["body_spec_version"], "primitive": event["execution"]["primitive"]}
            if scope != expected_scope:
                reasons.append("authority_scope_mismatch")
            if event["confidence"]["value"] < context["min_confidence"]:
                reasons.append("confidence_below_minimum")
            latency = (parse_time(item["delivered_at"]) - parse_time(event["execution"]["feedback_at"])).total_seconds() * 1000
            if latency > context["max_delivery_latency_ms"]:
                reasons.append("delivery_window_expired")
        if reasons:
            return self._record(item, "quarantine", sorted(set(reasons)), from_pending)
        if event["idempotency_key"] in self.seen:
            return self._record(item, "duplicate", ["idempotency_key_seen"], from_pending)

        episode_id = event["episode_id"]
        phase = event["execution"]["phase_index"]
        expected = self.states[episode_id].next_phase
        if phase > expected:
            if not from_pending:
                self.pending[episode_id][phase].append(item)
            return self._record(item, "defer", [f"phase_gap:expected={expected}:received={phase}"], from_pending)
        if phase < expected:
            return self._record(item, "quarantine", [f"stale_phase:expected={expected}:received={phase}"], from_pending)

        self.seen.add(event["idempotency_key"])
        self.states[episode_id].next_phase += 1
        decision = self._record(item, "accept", ["all_gates_passed"], from_pending)
        self.candidates.append(self._candidate(event))
        self._flush(episode_id)
        return decision

    def _flush(self, episode_id: str) -> None:
        while True:
            expected = self.states[episode_id].next_phase
            waiting = self.pending[episode_id].pop(expected, [])
            if not waiting:
                break
            for item in waiting:
                self.decide(item, from_pending=True)

    def _record(self, item: dict[str, Any], decision: str, reasons: list[str], from_pending: bool) -> str:
        event = item["event"]
        entry = {
            "decision_id": f"dec_{digest([len(self.ledger), item['packet_id'], decision], 20)}",
            "policy_version": POLICY_VERSION,
            "packet_id": item["packet_id"],
            "scenario": item["scenario"],
            "event_id": event.get("event_id"),
            "idempotency_key": event.get("idempotency_key"),
            "episode_id": event.get("episode_id"),
            "phase_index": event.get("execution", {}).get("phase_index"),
            "decision": decision,
            "reason_codes": reasons,
            "from_pending": from_pending,
            "event_sha256": digest(event),
            "context_sha256": digest(self.contexts.get(event.get("episode_id", ""), {})),
        }
        self.ledger.append(entry)
        return decision

    @staticmethod
    def _candidate(event: dict[str, Any]) -> dict[str, Any]:
        value = {
            "transition_outcome": event["transition"]["outcome"],
            "relation_error": event["measurements"]["relation_error"],
            "contact_state": event["measurements"]["contact_state"],
            "requested_replan_scope": event["recovery"]["requested_replan_scope"],
            "confidence": event["confidence"]["value"],
        }
        return {
            "candidate_id": f"kpc_{digest([event['event_id'], value], 20)}",
            "status": "proposed_not_committed",
            "source_event_id": event["event_id"],
            "base_revision": event["knowledge"]["base_revision"],
            "operation": "upsert_observation",
            "target": f"/execution_observations/{event['task_id']}/{event['body']['body_id']}/{event['execution']['primitive']}/{event['execution']['phase']}",
            "value": value,
            "required_next_authority": "knowledge_bus:commit_patch",
        }


def run_scenario(events: list[dict[str, Any]], contexts: dict[str, dict[str, Any]], scenario: str) -> dict[str, Any]:
    packets, transport = inject(events, scenario)
    bus = ReplayBus(contexts)
    for item in packets:
        bus.decide(item)
    decisions = Counter(item["decision"] for item in bus.ledger)
    reasons = Counter(reason for item in bus.ledger for reason in item["reason_codes"])
    accepted_ids = {item["event_id"] for item in bus.ledger if item["decision"] == "accept"}
    duplicate_second_writes = max(0, len(bus.candidates) - len(accepted_ids))
    pollution_packets = sum(1 for item in bus.ledger if any(reason in {"body_mismatch", "task_mismatch"} for reason in item["reason_codes"]))
    pollution_accepted = sum(1 for item in bus.ledger if item["decision"] == "accept" and any(reason in {"body_mismatch", "task_mismatch"} for reason in item["reason_codes"]))
    return {
        "scenario": scenario,
        "transport": transport,
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "accepted_unique_events": len(accepted_ids),
        "knowledge_candidates": len(bus.candidates),
        "duplicate_second_writes": duplicate_second_writes,
        "pollution_packets": pollution_packets,
        "pollution_accepted": pollution_accepted,
        "pending_after_replay": sum(len(items) for phases in bus.pending.values() for items in phases.values()),
        "ledger": bus.ledger,
        "candidates": bus.candidates,
    }


def gates(reports: dict[str, dict[str, Any]], total_events: int) -> dict[str, Any]:
    checks = {
        "clean_absorption_100pct": reports["clean"]["accepted_unique_events"] == total_events,
        "duplicate_zero_second_write": reports["duplicate"]["duplicate_second_writes"] == 0 and reports["duplicate"]["knowledge_candidates"] == total_events,
        "cross_body_isolation_100pct": reports["cross_body"]["pollution_packets"] == total_events and reports["cross_body"]["pollution_accepted"] == 0,
        "cross_task_isolation_100pct": reports["cross_task"]["pollution_packets"] == total_events and reports["cross_task"]["pollution_accepted"] == 0,
        "latency_quarantined_100pct": reports["latency"]["decision_counts"].get("quarantine", 0) == total_events,
        "reorder_eventual_absorption_100pct": reports["reorder"]["accepted_unique_events"] == total_events and reports["reorder"]["pending_after_replay"] == 0,
        "drop_never_skips_gap": reports["drop"]["pending_after_replay"] > 0 and reports["drop"]["accepted_unique_events"] < total_events - reports["drop"]["transport"]["dropped_packets"],
        "accepted_equals_candidate_count": all(report["accepted_unique_events"] == report["knowledge_candidates"] for report in reports.values()),
    }
    return {"status": "pass" if all(checks.values()) else "fail", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=Path("replay-output"))
    parser.add_argument("--limit-episodes", type=int, default=24)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    events, contexts = adapt_stage_events(args.source, args.limit_episodes)
    scenarios = ["clean", "latency", "reorder", "drop", "duplicate", "cross_body", "cross_task", "mixed"]
    reports = {name: run_scenario(events, contexts, name) for name in scenarios}
    gate_result = gates(reports, len(events))
    sample_distribution = Counter(
        (event["body"]["body_id"], event["experiment"]["disturbance"], event["experiment"]["controller"])
        for event in events if event["execution"]["phase_index"] == 0
    )
    summary = {
        "contract_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "source": str(args.source),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "adapted_events": len(events),
        "episodes": len(contexts),
        "episode_sample_distribution": {" | ".join(key): value for key, value in sorted(sample_distribution.items())},
        "scenarios": {name: {key: value for key, value in report.items() if key not in {"ledger", "candidates"}} for name, report in reports.items()},
        "gate": gate_result,
        "claim_boundary": "A pass validates deterministic offline transport isolation and absorption mechanics only; it does not establish policy improvement, physical feasibility, real-sensor validity, or robot safety.",
    }
    write_jsonl(args.out / "adapted-events.jsonl", events)
    write_json(args.out / "contexts.json", contexts)
    write_json(args.out / "replay-summary.json", summary)
    for name, report in reports.items():
        write_jsonl(args.out / f"decision-ledger-{name}.jsonl", report["ledger"])
        write_jsonl(args.out / f"knowledge-candidates-{name}.jsonl", report["candidates"])
    print(json.dumps({"status": gate_result["status"], "events": len(events), "episodes": len(contexts), "output": str(args.out)}, ensure_ascii=False))
    return 0 if gate_result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

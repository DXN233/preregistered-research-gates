# ExecutionEvidence v0.1

The replay bus separates immutable source evidence from delivery faults and
from knowledge-write authority. It tests clean delivery, latency, reorder,
drop, duplicate, cross-body, cross-task and mixed conditions.

The included reconstructed fixture contains 24 events from eight complete
three-stage episodes. All frozen transport checks pass on it. The historical
experiment used a larger 72-event/24-episode sample; that original source table
was lost and is not represented as recovered here.

Run:

```bash
python replay_bus.py --out validation-output
python -m unittest -v test_replay_bus.py
```

Accepted events generate only `proposed_not_committed` candidates. They do not
grant permission to mutate knowledge.

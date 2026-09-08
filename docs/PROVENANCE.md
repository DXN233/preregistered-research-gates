# Provenance and recovery notes

This candidate was assembled on 2026-09-08 from preserved local research
artifacts. It does not depend on the lost source drive.

| Package | Preserved material | Recovery boundary |
|---|---|---|
| body-v2 | 1,920-row trial table and frozen result JSON | The underlying simulator/controller source is not included |
| latency | FilterPy development/holdout tables and result JSON; sanitized GTSAM throughput-stop record | The GTSAM batch returned no completed result package |
| posture | 384-row severe delay x noise table and frozen descriptive result | The table supports only the stated frozen-condition contrast |
| execution-evidence | Standalone replay bus, schema and 24-event/8-episode minimal fixture | The fixture was reconstructed; it is not the original full source CSV or the historical 72-event/24-episode sample |
| readiness | Historical machine-readable gate status | Recomputed against the preserved case results; no formal 2x2 is run |

The release validator checks all preserved CSV hashes that are declared in the
result records. It also checks that no local absolute path, public-account
identity, email address, cloud instance identifier, or credential-like key is
present in the release tree.

The source artifacts used to assemble this candidate remain outside the
candidate repository. Their system-governance status is frozen evidence or
advisory; this package does not promote them to current effectiveness claims.

# Preregistered Research Gates

A small collection of reproducible examples showing that a test pass, a
mechanism pass, a behavior pass, a throughput pass, and permission to run a
larger experiment are different claims.

本仓库收录五个经过裁剪的研究门禁案例。重点不是展示“所有实验都成功”，
而是让失败阈值、停止决定和证据边界可以被复算。

## Included cases

| Case | Preserved decision (public) | Trial data | What it does not establish |
|---|---|---|---|
| Body representation v2 | Mechanism passed; the preregistered behavior gate stayed **closed** | archived pre-publication | General robot improvement or real-robot validity |
| FilterPy delayed-state estimator | The frozen behavior gate **failed** | archived pre-publication | A deployable latency estimator |
| GTSAM/Pinocchio development run | Stopped on engineering throughput; behavior gate **never evaluated** | archived pre-publication | A behavioral failure or benefit |
| ExecutionEvidence v0.1 | Deterministic isolation, ordering and idempotency gates pass on a reconstructed minimal fixture | included, rerunnable | Policy improvement, physical feasibility, or recovery of the original dataset |
| Formal 2x2 readiness | The larger experiment remains blocked by three explicit prerequisites | n/a | Evidence about the final algorithm |

Three gated cases keep their preregistered decisions public while their frozen
trial tables are held in a private archive until the corresponding paper is
submitted. The decisions are binding either way; the archive exists so that
publication review can re-derive them from the full data.

The posture delay-by-noise result is included as a descriptive diagnostic. It
is not presented as a general causal mediation result.

## Quick start

Python 3.11 or newer is sufficient; the release checks use only the standard
library.

```bash
python scripts/validate_release.py
python -m unittest discover -s tests -v
```

The first command verifies artifact hashes, recomputes decision gates from the
published CSV/JSON files, reruns the offline execution-evidence stress cases,
and rejects private absolute paths or credential-like strings.

## Repository structure

```text
cases/
  body-v2/             frozen trial table and decision record
  latency/             FilterPy trials/result and sanitized throughput stop
  posture/             descriptive delay x noise 2x2
  execution-evidence/  standalone replay bus and reconstructed fixture
  readiness/           historical fail-closed readiness record
docs/
  CLAIMS.md             allowed and disallowed interpretations
  NEGATIVE_RESULTS_AS_RESEARCH_ASSETS.md
                        note on when failed gates remain useful research
  PROVENANCE.md         source and recovery boundaries
scripts/
  validate_release.py  clean-room release validator
tests/
  test_release.py      regression tests for all published gates
```

## Reproducibility boundary

The public artifacts reproduce the published **decisions and gates**, not the
underlying MuJoCo simulations. The original control baseline is intentionally
not included, and three case datasets are archived pre-publication; the
release validator enforces both boundaries (it fails if archived data files
reappear). This keeps the package useful for research-audit practice without
releasing the highest-value control mechanism or pre-empting paper review.

ExecutionEvidence is the exception: its replay bus and minimal recovered
fixture are included and can be rerun end to end. The fixture was reconstructed
from preserved adapted events after the original source drive was lost; it is
not the full historical source dataset.

## Status

Public research-audit release: <https://github.com/DXN233/preregistered-research-gates>.
It is licensed under MIT, and GitHub Actions reruns the release validator and
regression tests on every push and pull request. The reproducibility and claim
boundaries above remain part of the release contract.

# Validation record

Local candidate validation date: 2026-09-08.

## Recomputed artifacts

| Check | Result |
|---|---|
| body-v2 trial hash and row count | pass, 1,920 rows |
| body-v2 success gain | 0.0182292; below frozen 0.02 gate |
| FilterPy development hash and row count | pass, 96 rows |
| FilterPy holdout hash and row count | pass, 768 rows |
| FilterPy behavior gate | fail, as preserved |
| GTSAM behavior gate | not evaluated, as preserved |
| posture trial hash and row count | pass, 384 rows |
| posture interpretation | descriptive only |
| reconstructed ExecutionEvidence replay | pass, 24 events and 8 episodes |
| formal 2x2 readiness | false, with three blockers |
| text hygiene scan | pass, 25 text files and zero matches |

## Tests

- Six release-level regression tests passed.
- Ten focused ExecutionEvidence tests passed.
- The validator and both suites also passed from a clean local clone.
- Git object integrity passed for the one-commit local history.
- The sole commit author uses the public no-reply identity configured for the
  intended hosting account.

## Deliberately preserved mismatch

The historical ExecutionEvidence report described 72 events from 24 episodes.
The surviving reconstructed fixture contains 24 events from eight episodes.
The smaller fixture passes the same transport checks, but this candidate does
not claim that it recreates the larger historical sample.

## Remaining external checks

CI has not run on a public host because no remote repository exists. The owner
must still confirm ownership, MIT licensing, the repository name and the exact
public target before any repository is created or pushed.

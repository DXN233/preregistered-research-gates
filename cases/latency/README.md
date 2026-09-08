# Latency-estimator gates

The FilterPy case preserves its development and holdout trial tables. Its
safety checks passed, but severe push reach and non-severe regression gates did
not, so the frozen behavior verdict is failure.

The GTSAM/Pinocchio record has a different status. Protocol work had passed,
but the development batch was stopped after roughly 136 minutes because the
implementation was too slow. No completed result package was returned, so its
behavior is explicitly `not_evaluated` rather than failed.

The cloud instance identifier was removed from the public candidate; cleanup
status and the scientific interpretation were retained.

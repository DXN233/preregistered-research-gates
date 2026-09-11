# When a Negative Result Is Still a Research Asset

Research value is not the same thing as positive performance gain.

A result can miss its target and still improve the state of a project when it
makes a decision reproducible: another person can see what was tested, which
threshold governed the decision, why the result stopped, and which claims
remain unsupported.

That requires more than publishing a failed chart after the fact. A useful
negative result needs four things.

## 1. A decision rule that existed before the verdict

The threshold or stop condition must not be invented to fit the observed
outcome. A preregistered rule turns “this did not look good enough” into a
checkable decision. It also blocks the common escape route of adding trials or
changing metrics until a borderline result becomes positive.

## 2. Evidence that lets another reader recompute the decision

The smallest useful release is not necessarily the whole private system. It is
the bounded set of data, code, hashes, and validation logic needed to reproduce
the published verdict. This makes the result auditable without requiring the
highest-value implementation or private operating state to be disclosed.

## 3. A typed verdict

Different gates answer different questions:

- a test pass says the checked implementation behaved as specified;
- a mechanism pass says an internal property was observed;
- a behavior pass says the frozen outcome threshold was met;
- a throughput pass says the method is practical enough to evaluate or use;
- a readiness pass says the prerequisites for the next experiment are present.

Passing one does not silently grant the others. A throughput stop, for example,
is not evidence that the behavior would have failed. A mechanism pass is not a
deployment claim.

## 4. An explicit claim boundary

A negative result is reusable only if readers can tell what it rules out and
what it leaves open. The release should state the tested conditions, missing
baselines, unavailable data, reconstruction limits, and interpretations that
the evidence does not support.

## Examples in this repository

The cases here preserve several different kinds of non-positive outcomes:

- Body representation v2 passed mechanism checks, but its 1.8229 percentage
  point behavior gain stayed below the preregistered 2-point gate.
- The FilterPy delayed-state estimator passed safety checks but failed its
  frozen behavior gate.
- The GTSAM/Pinocchio run stopped on impractical throughput before producing a
  behavior verdict.
- The formal 2x2 experiment remains blocked because three prerequisites have
  not passed.

These records do not prove that the underlying ideas can never work. They do
something narrower and more useful: prevent failed gates from being narrated
as successes, preserve the cost already paid for the experiments, and make the
next redesign start from a visible boundary instead of a vague memory.

## Practical rule

Publish a negative result when the release lets another reader recompute a
decision and avoid a known mistake. Do not publish it merely because an
experiment happened, and do not turn a bounded failure into a universal claim.

The goal is not to maximize the number of public artifacts. It is to release
enough evidence that an honest “no,” “not yet,” or “not evaluated” becomes a
durable research contribution.

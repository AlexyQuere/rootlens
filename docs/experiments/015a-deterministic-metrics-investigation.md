# Experiment 015A — Deterministic Metrics Investigation

**Project:** RootLens — Autonomous AI Incident Investigator  
**Status:** Completed with one validated positive fault scenario and one unresolved diagnostic scenario  
**Stage:** 15A — Deterministic observability tools  
**Primary source:** Prometheus native application metrics  
**Diagnostic source:** `traces_span_metrics_*` (trace-derived aggregate metrics; not treated as an independent native-metrics source)  
**Core principle:** observation ≠ interpretation ≠ hypothesis ≠ conclusion

---

## 1. Objective

Experiment 015A introduces deterministic metrics investigation before any agentic reasoning.

The objective is to give RootLens a stable metrics API that:

1. queries Prometheus deterministically,
2. preserves exact PromQL and time-window provenance,
3. exposes request rate, request count, error rate, and latency quantiles,
4. compares healthy and incident windows,
5. separates measurement from interpretation,
6. avoids arbitrary LLM-generated PromQL in the default path,
7. records benchmark control-plane state without leaking it into the investigator.

The architecture is deliberately layered:

```text
Prometheus HTTP API
        ↓
PrometheusClient
        ↓
MetricsTool
        ↓
MetricEvidence
        ↓
MetricComparisonEvidence
        ↓
later: agent / investigator
```

The agent is not implemented yet.

---

## 2. Implemented deterministic metrics primitives

RootLens currently supports three metric families:

```text
http_server
rpc_server
rpc_client
```

The deterministic investigation primitives include:

```text
request_count(...)
request_rate(...)
error_rate(...)
latency_quantile(...)
latency_quantiles(...)
```

Every `MetricEvidence` preserves:

```text
name
statistic
value
unit
service
time window
PromQL
source
labels
```

Derived comparisons are computed from baseline and incident evidence rather than supplied manually.

---

## 3. Experimental protocol

The final v2 runner was strengthened after earlier exploratory runs exposed confounding.

For each final run:

```text
target faults OFF
        ↓
Flagd Scheduler confirmed stopped
        ↓
manual healthy checkout confirmed
        ↓
300 s baseline washout
        ↓
feature-flag state re-read from /feature/api/read
        ↓
baseline collected
        ↓
baseline rejected unless Checkout and Checkout→Payment error rates are zero
        ↓
exactly one target fault enabled
        ↓
feature-flag state verified programmatically
        ↓
manual incident effect confirmed
        ↓
300 s incident window
        ↓
feature-flag state checked again
        ↓
incident collected
        ↓
artifact frozen
```

Feature-flag state is benchmark metadata only:

```text
ground-truth / control plane
             │
             X
       not provided to
             │
             ▼
      RootLens analysis
```

The RootLens analysis input for 015A is Prometheus only.

---

# 4. Final scenario A — `paymentFailure = 100%`

Frozen artifact:

```text
data/evaluation/metrics_payment_failure_100_v2.json
```

## 4.1 Healthy baseline

Measured native RPC metrics:

```text
checkout_request_count             13.749714
checkout_request_rate               0.045832 req/s
checkout_error_rate                 0.000000

checkout_payment_request_count     13.749656
checkout_payment_request_rate       0.045832 req/s
checkout_payment_error_rate         0.000000
```

Latency:

```text
p50 = 0.153571 s
p95 = 0.362500 s
p99 = 0.472500 s
```

## 4.2 Incident

With `paymentFailure = 100%`:

```text
checkout_request_count              7.500500
checkout_request_rate               0.025002 req/s
checkout_error_rate                 1.000000

checkout_payment_request_count      7.500438
checkout_payment_request_rate       0.025001 req/s
checkout_payment_error_rate         1.000000
```

Latency:

```text
p50 = 0.050000 s
p95 = 0.205000 s
p99 = 0.241000 s
```

## 4.3 Native-metrics interpretation

The strongest deterministic observation is:

```text
Checkout PlaceOrder error rate:
0% → 100%

Checkout → Payment Charge error rate:
0% → 100%
```

The defensible metrics-only conclusion is:

> During the controlled incident window, all observed Checkout `PlaceOrder` RPCs and all observed Checkout→Payment `Charge` RPCs were reported as non-OK.

A stronger statement such as “Payment's internal application logic is the root cause” is not justified by metrics alone.

## 4.4 Latency caveat

Latency decreases while the system is failing:

```text
p50: 153.6 ms → 50.0 ms
p95: 362.5 ms → 205.0 ms
p99: 472.5 ms → 241.0 ms
```

This demonstrates an important observability lesson:

```text
lower latency ≠ healthier system
```

A fast failure can be faster than a successful request that completes all downstream work.

Because the event count is small, p95 and p99 are descriptive only.

---

# 5. Trace-derived funnel diagnostic — `paymentFailure = 100%`

The trace-derived span metrics are used only as a diagnostic bridge to the next stage.

Healthy:

```text
frontend_to_checkout       13.750, ERROR 0
checkout_server            13.750, ERROR 0
checkout_to_payment        13.750, ERROR 0
payment_server             13.750, ERROR 0
```

Incident:

```text
frontend_to_checkout        7.500, ERROR 7.500
checkout_server             7.500, ERROR 7.500
checkout_to_payment         7.500, ERROR 7.500
payment_server              7.500, ERROR 7.500
```

Flow diagnostic:

```text
Checkout → Payment client attempts: 7.500
Payment server observations:        7.500
Client - server difference:        +0.000

Checkout → Payment client errors:   7.500
Payment server errors:              7.500
```

This pattern is consistent with requests reaching the Payment service and the error being visible both at Payment server level and upstream.

It does not by itself identify the internal software defect.

---

# 6. Final scenario B — `paymentUnreachable`

Frozen artifact:

```text
data/evaluation/metrics_payment_unreachable_v2.json
```

## 6.1 Healthy baseline

Measured native RPC metrics:

```text
checkout_request_count             18.752266
checkout_request_rate               0.062508 req/s
checkout_error_rate                 0.000000

checkout_payment_request_count     18.752188
checkout_payment_request_rate       0.062507 req/s
checkout_payment_error_rate         0.000000
```

## 6.2 Incident

During the controlled flag-on incident window:

```text
checkout_request_count             12.499271
checkout_request_rate               0.041664 req/s
checkout_error_rate                 0.000000

checkout_payment_request_count     12.499375
checkout_payment_request_rate       0.041665 req/s
checkout_payment_error_rate         0.000000
```

Latency:

```text
p50 = 0.100000 s
p95 = 0.235000 s
p99 = 0.247000 s
```

## 6.3 Native-metrics interpretation

The target feature flag was programmatically verified and its manual effect was confirmed before the measured incident window.

However, the current native RPC observables do not expose an error-rate increase:

```text
Checkout error rate:           0% → 0%
Checkout → Payment error rate: 0% → 0%
```

Therefore the correct conclusion is not that the system was healthy.

The correct conclusion is:

> The currently selected native RPC metrics did not expose a distinct error signature for this controlled `paymentUnreachable` run.

This is a measured coverage limitation of the current observables for this run.

---

# 7. Trace-derived funnel diagnostic — `paymentUnreachable`

Healthy:

```text
frontend_to_checkout       20.000
checkout_server            18.750
checkout_to_payment        18.750
payment_server             18.750
```

Incident:

```text
frontend_to_checkout       12.500, ERROR 0
checkout_server            12.500, ERROR 0
checkout_to_payment        12.500, ERROR 0
payment_server             12.500, ERROR 0
```

Flow diagnostic:

```text
Checkout → Payment client attempts: 12.500
Payment server observations:        12.500
Client - server difference:        +0.000

Checkout → Payment client errors:   0.000
Payment server errors:              0.000
```

The expected aggregate client/server rupture was not observed.

This result must not be forced into an unsupported root-cause interpretation.

Possible explanations require request-level evidence and belong to the trace investigation stage.

---

# 8. Important experimental limitation

The manipulation check used a manual checkout immediately before the measured incident window, while the measured five-minute window was dominated by load-generator traffic.

Therefore:

```text
manual fault effect confirmed
```

does not prove that every measured load-generator request exercised exactly the same failing path.

The control-plane state was stable, but the discrepancy between the confirmed manual failure and the aggregate measured flow remains unresolved.

`paymentUnreachable` is therefore retained as a controlled diagnostic run, but not as proof that metrics can or cannot universally detect this fault.

This unresolved discrepancy is an explicit input to Experiment 015B.

---

# 9. Request-count semantics

Prometheus `increase()` can return fractional values such as:

```text
13.749714
7.500500
18.752266
```

These are not literal fractional requests.

`increase()` extrapolates counter growth to the exact query-window boundaries.

At this traffic volume, counts and high quantiles should therefore be interpreted cautiously.

---

# 10. Frontend HTTP metric limitation

Across these runs:

```text
frontend_http_error_rate = 0
```

even when downstream Checkout and Payment RPCs fail.

The currently selected `http_server` family does not provide a useful user-facing checkout failure observable for this experiment.

The metric remains supported by `MetricsTool`, but it should not be treated as a valid checkout health signal without validating the exact route/cardinality semantics.

---

# 11. Main result

Experiment 015A demonstrates both the value and the limitation of deterministic metrics investigation.

For `paymentFailure = 100%`:

```text
native RPC metrics
        ↓
clear 100% error signal
        ↓
Checkout → Payment dependency implicated
```

For `paymentUnreachable`:

```text
controlled incident
        ↓
current native RPC metrics show no error signal
        ↓
aggregate trace-derived funnel also does not resolve discrepancy
        ↓
request-level trace evidence required
```

The architecture decision is therefore:

```text
MetricsTool remains deterministic and narrow.
Do not add increasingly complex heuristic PromQL
just to force every incident into a metrics-only explanation.
```

Instead:

```text
metrics
   ↓
detect / scope degradation
   ↓
when evidence is insufficient or contradictory
   ↓
request-level traces
   ↓
logs / other evidence
```

---

# 12. Decision

**Keep:**

```text
PrometheusClient
MetricEvidence
MetricComparisonEvidence
MetricsTool
request_count
request_rate
error_rate
latency_quantile(s)
controlled experiment harness
control-plane metadata isolation
```

**Do not add yet:**

```text
LLM-generated arbitrary PromQL
heuristic root-cause inference inside MetricsTool
confidence probabilities
complex flow rules inferred from aggregate metrics
```

**Next:**

```text
Experiment 015B — Deterministic Trace Investigation Tool
```

---

# 13. What 015B must answer

The next stage should inspect individual traces rather than aggregate span metrics.

Required capabilities:

```text
retrieve trace(s) for an incident window
inspect span tree / parent-child relationships
preserve trace_id and span_id provenance
extract service, operation, status, duration
identify client spans without corresponding server spans
surface span errors and error descriptions
compare healthy and degraded request paths
```

For `paymentUnreachable`, 015B should determine whether individual affected requests exhibit a pattern such as:

```text
Checkout → Payment client span
            ERROR
              │
              X
no matching Payment server span
```

or whether the measured load-generator requests followed a different path.

The tool must report observations first and leave root-cause reasoning to later layers.

---

# 14. Engineering lessons

## Measurement is not interpretation

A query returning a number does not prove the semantic meaning of that number.

## Correct PromQL is not enough

The observable itself must correspond to the system behavior being investigated.

## Absence of an error series is not proof of health

A confirmed incident can remain invisible to a selected aggregate metric.

## Aggregate telemetry can hide request-level structure

A funnel over five minutes cannot establish which client span corresponds to which server span.

## Fail-fast can improve latency while reliability collapses

Outcome metrics and latency must be interpreted jointly.

## Complexity must earn its place

When aggregate metrics become ambiguous, the correct response is not necessarily more PromQL. It may be a different evidence source.

---

# 15. Interview explanation

> “I built the observability layer before the agent. I separated the Prometheus transport client from a deterministic domain-level MetricsTool and made every result carry its exact query and time-window provenance. Then I evaluated it on controlled faults. A 100% Payment application failure produced a clean 0-to-100% error-rate transition on both Checkout and Checkout→Payment RPC metrics, while an unreachable-Payment scenario did not produce a corresponding signal in the selected native metrics. I deliberately did not patch that ambiguity with heuristic PromQL. Instead, I treated it as evidence that aggregate metrics have coverage limits and moved to request-level traces. That keeps measurement deterministic and pushes interpretation to the appropriate evidence layer.”

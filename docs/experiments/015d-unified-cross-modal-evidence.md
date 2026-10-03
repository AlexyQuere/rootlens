# Experiment 015D - Unified Cross-Modal Incident Evidence

## Status

**Complete / frozen**

Experiment 015D unifies deterministic metrics, traces, and logs into a typed incident-evidence layer before introducing any investigation agent.

The goal is not to infer root cause automatically. The goal is to preserve evidence structure, provenance, correlation semantics, acquisition state, and failure-specific differences so a later investigation loop can reason over reliable tools.

## Research question

Can RootLens combine Prometheus metrics, Jaeger / OTLP traces, and OpenSearch logs into one typed incident representation while preserving modality-specific semantics and avoiding unsupported causal conclusions?

The experiment specifically tests whether the unified representation can distinguish two failure modes that share similar high-level metric symptoms but differ materially at request level:

1. `paymentFailure=100%`: the request reaches Payment and fails server-side;
2. `paymentUnreachable` with runtime-confirmed `True/on`: Checkout fails before any Payment server span or Payment log is observed.

## Epistemic rules

Experiment 015D freezes the following rules:

```text
missing log != service did not execute
missing server span != server definitely did not execute
metric anomaly != root cause
ERROR log != root cause
control-plane state != runtime request state
correlation != causation
same scenario != same incident run
no series != zero
missing context != present-but-unmatched context
```

No scalar root-cause score and no uncalibrated confidence value are introduced.

## Unified evidence model

The core representation is:

```text
IncidentEvidenceBundle
  incident_id
  start / end
  metrics
  traces
  logs
  acquisitions
```

Metrics are stored as baseline-vs-incident `MetricComparisonEvidence` objects. Traces remain request-level `TraceEvidence`. Logs remain exact `LogEvidence` documents.

Acquisition state is modeled separately from service-local evidence presence. For example, `log acquisition = observed` with `Payment log_count = 0` means OpenSearch was successfully acquired for the incident but no Payment log was observed in the captured request set.

## Explicit metric / service bindings

Metric identity is not inferred post hoc from arbitrary labels.

Each validated metric receives an explicit `MetricServiceBinding`.

For an RPC client edge such as:

```text
Checkout -> Payment
```

the metric remains a Checkout-emitted client metric but is represented in service views as:

```text
checkout  role=primary
payment   role=peer
```

This allows the same edge evidence to be relevant to both services without relabeling it as an internal Payment metric.

## Exact cross-modal correlation

The unified index uses exact identifiers:

```text
trace identity = trace_id
span identity  = (trace_id, span_id)
service join   = exact service_name
```

Logs are distinguished between:

```text
no trace context
trace context present but unmatched
no span context
span context present but unmatched
```

Synthetic unit tests verify that these states are not conflated.

## Synchronization guard

An early attempt to merge previously frozen artifacts failed a temporal-alignment check.

The old metric, trace, and log artifacts represented the same scenario but different incident runs.

This produced the key rule:

> **same scenario != same incident run**

RootLens therefore rejects non-overlapping artifact windows and uses synchronized capture for 015D.

## Synchronized capture protocol

For each phase:

```text
manual scenario configuration
        |
        v
washout
        |
        v
freeze analytical t0 / t1
        |
        v
wait through measured window
        |
        v
short telemetry-ingestion wait
        |
        +--> Prometheus queries pinned to t1
        +--> Jaeger traces for [t0, t1]
        +--> OpenSearch logs by exact captured trace IDs
```

OpenSearch discovery uses `observedTimestamp` with a margin around the analytical interval while original event timestamps remain preserved.

The runner writes phase checkpoints immediately so a later serialization or transport failure does not erase an already measured phase.

## Engineering findings during capture

### Prometheus query window

A 60-second `increase(...)` query returned no series even while the underlying counter existed. The validated 300-second analytical window produced usable evidence.

RootLens therefore treats missing query results as unavailable evidence rather than silently coercing them to zero.

### Metric identity is modality-specific

A trace operation name was initially reused as an HTTP metric operation filter. The live Prometheus schema showed that the corresponding frontend HTTP metric did not expose that operation identity.

The validated frontend error-rate metric therefore remains service-wide rather than pretending to be checkout-route-specific.

### Immutable serialization

`LogQueryEvidence` contains immutable mappings. `dataclasses.asdict()` attempted a recursive `deepcopy()` and failed on `mappingproxy` objects.

The serializer was replaced by field-by-field recursive JSON conversion, preserving immutable runtime objects while producing ordinary dictionaries only at the artifact boundary.

## Positive control - synchronized `paymentFailure`

Artifact:

```text
data/evaluation/cross_modal_payment_failure_100_synced_v1.json
```

The incident phase contains:

```text
10 metric comparisons
11 incident traces
425 incident logs
10 explicit metric bindings
```

Cross-modal integrity:

```text
425 / 425 logs have trace context
425 / 425 logs match a captured trace
425 / 425 logs have span context
425 / 425 logs match a captured span
```

The synchronized baseline was historically reacquired after the original live run failed during serialization. Its analytical window is exact and its provenance is explicitly recorded as historical recovery rather than being presented as a live acquisition.

### Metric evidence

```text
checkout_error_rate          0.000000 -> 1.000000
checkout_payment_error_rate  0.000000 -> 1.000000
frontend_http_error_rate     0.000000 -> 0.000000
```

### Trace evidence

Across all 11 incident traces:

```text
Checkout -> Payment CLIENT observed  11 / 11
Checkout -> Payment CLIENT error     11 / 11
Payment SERVER observed              11 / 11
Payment SERVER error                 11 / 11
```

### Log evidence

Across all 11 incident traces, Payment emitted:

```text
"Charge request received."
"Payment request failed. Invalid token. demo.user_context.loyalty_level=gold"
```

The invalid-token failure log was present in 11 / 11 incident traces.

### Request-level join

For every incident trace:

```text
Checkout -> Payment CLIENT ERROR
        +
Payment SERVER ERROR
        +
Payment invalid-token log
```

The three evidence elements joined on all 11 / 11 incident trace IDs.

### Interpretation

```text
metrics -> detect degraded Checkout / Payment RPC behavior
traces  -> show the request reached Payment and failed server-side
logs    -> add the systematic invalid-token mechanism
```

This is descriptive evidence, not an automatic RCA rule.

## Controlled real-ON `paymentUnreachable`

Artifact:

```text
data/evaluation/cross_modal_payment_unreachable_real_on_synced_v1.json
```

The artifact passed structural validation with:

```text
baseline: 10 metrics, 11 traces, 453 logs
incident: 10 metrics, 13 traces, 425 logs
```

### Runtime manipulation validation

The control plane is not accepted as proof of runtime state.

The measured incident traces themselves were inspected for feature-flag evaluation events.

All 13 / 13 incident requests contained:

```text
feature_flag.key            = paymentUnreachable
feature_flag.result.value   = True
feature_flag.result.variant = on
feature_flag.result.reason  = cached
feature_flag.provider.name  = flagd
```

Therefore this measured window is a genuine runtime-ON case.

### Metric evidence

```text
checkout_error_rate          0.000000 -> 1.000000
checkout_payment_error_rate  0.000000 -> 1.000000
frontend_http_error_rate     0.000000 -> 0.003205
```

The frontend metric is service-wide, so `0.003205` must not be interpreted as a checkout failure fraction.

### Trace evidence

Across all 13 incident traces:

```text
Checkout -> Payment CLIENT observed  13 / 13
Checkout -> Payment CLIENT error     13 / 13
Payment SERVER observed               0 / 13
Payment SERVER error                  0 / 13
```

Every Checkout-to-Payment client error carried:

```text
"name resolver error: produced zero addresses"
```

### Log evidence

Across the same measured traces:

```text
Payment logs observed = 0
```

Frontend logs contained:

```text
13 / 13 traces  "Checkout failed to place order"
```

### Service-oriented view

The Payment service still receives three peer-role metric bindings:

```text
checkout_payment_request_count
checkout_payment_request_rate
checkout_payment_error_rate
```

but in this incident its service view contains:

```text
traces: 0
spans:  0
logs:   0
```

This means Payment-related server/log evidence was not observed in the captured incident requests. It is not converted into a stronger claim that Payment could never have executed.

### Interpretation

```text
runtime request flag = ON
        |
        v
Checkout attempts Payment RPC
        |
        v
client resolver fails
        |
        v
no Payment SERVER span observed
no Payment log observed
```

The trace carries the mechanism evidence here. Logs mainly expose the upstream symptom.

## Cross-case comparison

The two synchronized failures share similar high-level RPC metric degradation:

```text
                         paymentFailure   paymentUnreachable
checkout error rate          1.0                 1.0
checkout->payment error      1.0                 1.0
```

But request-level evidence separates them:

```text
paymentFailure
  Checkout CLIENT ERROR
  Payment SERVER ERROR
  Payment invalid-token log

paymentUnreachable
  Checkout CLIENT ERROR
  resolver / zero-address message
  Payment SERVER not observed
  Payment log not observed
```

This is the central result of 015D:

> **similar metric symptoms can correspond to materially different failure mechanisms, and the distinction emerges only when the modalities remain typed and exactly correlated.**

## What 015D does not claim

Experiment 015D does not establish that:

- one telemetry modality is universally superior;
- missing Payment spans or logs prove that Payment never executed;
- a metric error identifies the root cause;
- a log error identifies the root cause;
- the feature-flag provider refresh mechanism is fully understood;
- the controlled OpenTelemetry Demo results generalize quantitatively to arbitrary production systems.

The conclusions are scoped to the controlled experiments and implemented evidence contracts.

## Decision

**Freeze Experiment 015D.**

The unified evidence layer has demonstrated:

```text
typed modality-specific evidence
exact trace / span correlation
explicit edge metric bindings
acquisition-state semantics
missing-vs-unmatched integrity semantics
synchronized multi-modal capture
request-level mechanism separation
```

No agent framework is needed to improve this layer further before the next research question.

## Next experiment

Build the first **single custom investigation loop** on top of the frozen deterministic tools.

The next system should learn to decide which evidence operation to execute next while preserving:

```text
observation != interpretation != hypothesis != conclusion
claim -> evidence -> source
```

The single-agent baseline must be evaluated before any multi-agent architecture is introduced.

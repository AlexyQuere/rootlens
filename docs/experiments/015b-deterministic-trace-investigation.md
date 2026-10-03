# Experiment 015B - Deterministic Trace Investigation

## Status

**Complete**

Experiment 015B builds and evaluates RootLens's deterministic trace-investigation layer on top of the OpenTelemetry Demo and the Jaeger v3 query API.

The goal is not to infer root cause automatically. The trace layer exposes request-level observations with explicit provenance so that later investigation logic can keep this separation:

```text
observation != interpretation != hypothesis != conclusion
```

No agent framework is used in this stage.

## Objective

Experiment 015A showed that aggregate metrics were sufficient to detect and scope a controlled `paymentFailure` incident, but `paymentUnreachable` remained ambiguous. The control plane reported the flag as enabled, while selected native RPC metrics and trace-derived aggregate metrics showed no Checkout-to-Payment error signal.

Experiment 015B asks whether deterministic request-level tracing can localize these failures while also preserving telemetry-integrity limitations.

Required capabilities:

- query traces by service, operation, and time window;
- fetch a complete trace by trace ID;
- parse Jaeger v3 OTLP payloads into typed evidence;
- reconstruct parent/child topology;
- expose error and slow spans;
- pair CLIENT and SERVER spans through parent/child identity;
- report unmatched client spans without treating them as failures;
- compare trace paths structurally;
- preserve raw OTLP evidence during controlled experiments;
- expose trace-integrity problems instead of silently correcting them.

## Jaeger transport

RootLens uses the Jaeger v3 query API exposed by the OpenTelemetry Demo through the frontend proxy.

Default local endpoint:

```text
http://localhost:8080/jaeger/ui/api/v3
```

The deterministic client supports:

```text
list_services()
find_traces(...)
get_trace(trace_id)
```

Jaeger v3 returns OTLP JSON under `result.resourceSpans`.

For trace search, the current Jaeger API returns HTTP 404 with `No traces found` when the search result is empty. RootLens normalizes this specific search outcome into an empty trace payload. `get_trace(trace_id)` remains strict because asking for a specific missing trace is different from a search with zero matches.

## Structured OTLP evidence

The parser converts raw OTLP JSON into immutable evidence objects.

Core types:

```text
SpanEventEvidence
SpanEvidence
TraceEvidence
ParentChildTemporalViolation
TraceIntegrityEvidence
```

A span preserves:

```text
trace_id
span_id
parent_span_id
service_name
operation_name
span kind
start/end nanoseconds
duration
status code
status message
span attributes
resource attributes
events
instrumentation scope
source
```

Timestamps remain raw integer nanoseconds. RootLens does not silently repair telemetry.

## Trace integrity finding

Real smoke tests exposed a data-quality issue. A normal checkout root span lasted only a few hundred milliseconds, but the trace-wide temporal envelope was around 67,013,800 ms, or roughly 18.6 hours.

The topology itself was usually coherent:

```text
roots:   1
orphans: 0
services: 12
```

Inspection showed that spans from the `quote` service were timestamped roughly 18.6 hours before the rest of the same trace. The Quote container and PHP runtime clocks were correct when inspected.

RootLens therefore distinguishes:

```text
span duration
root/request duration
trace temporal envelope
parent/child temporal violations
root-interval violations
orphans
```

The old ambiguous trace-wide `duration_ms` concept is treated as `envelope_duration_ms` because:

```text
max(span end) - min(span start)
```

is not necessarily request latency.

For request latency, RootLens uses a known entry/root span or a task-specific span such as `CheckoutService/PlaceOrder`.

The evidence model exposes:

```text
root_count
orphan_count
temporal_violation_count
max_temporal_skew_ms
root_interval_violation_count
max_root_interval_skew_ms
```

without an arbitrary good/bad threshold at this layer.

## Deterministic investigation primitives

`TraceInvestigationTool` provides observations rather than RCA heuristics:

```text
summarize(trace)
find_spans(...)
find_error_spans(...)
find_slow_spans(...)
find_parent_child_edges(...)
find_client_server_pairs(...)
find_unmatched_client_spans(...)
edge_signatures(...)
compare_trace_paths(...)
```

### CLIENT -> SERVER pairing

Where distributed parentage is preserved, pairing uses:

```text
server.parent_span_id == client.span_id
```

This is stronger than matching only on operation names.

### Unmatched clients

Healthy traces already contained expected unmatched CLIENT spans for dependencies such as `astronomy-db`, Valkey, and some flagd calls.

Therefore:

```text
unmatched client != failed dependency
```

A stronger request-level observation is a combination such as:

```text
CLIENT status = ERROR
+
no matching SERVER span
+
healthy traces normally contain the SERVER span
```

Even then, the deterministic layer reports evidence rather than an automatic root-cause label.

## Structural path comparison

Absolute timestamp order cannot be trusted when a trace contains severe clock inconsistencies. RootLens therefore compares parent/child edge signatures:

```text
parent service
parent operation
parent kind
        ->
child service
child operation
child kind
```

This makes path comparison topology-driven rather than chronology-driven.

## Evidence retention lesson

The first attempt to reuse the exact frozen windows from Experiment 015A failed because Jaeger no longer retained those individual traces.

Observed behavior:

```text
old 015A window -> HTTP 404 No traces found
recent window   -> HTTP 200
```

This established a new protocol rule:

```text
time-window metadata != preserved request-level evidence
```

Controlled trace experiments now freeze both:

```text
derived relation observations
+
raw OTLP resourceSpans
```

immediately after each measurement window.

The runner also writes the baseline artifact before the incident begins so baseline evidence survives if a later step fails.

## Controlled experiment design

Two fault scenarios were evaluated:

```text
paymentFailure = 100%
paymentUnreachable = on
```

Each experiment used:

```text
feature-flag control-plane validation
baseline washout
300 s baseline window
5 s ingestion grace
immediate Jaeger capture
manual fault activation
control-plane validation
300 s incident window
5 s ingestion grace
immediate Jaeger capture
```

The runner does not modify feature flags automatically. Control-plane state is recorded for experimental validation but is not treated as the request-level analysis input.

The main relation is:

```text
Checkout
CLIENT oteldemo.PaymentService/Charge
        |
        v
Payment
SERVER oteldemo.PaymentService/Charge
```

Each trace is classified descriptively, for example:

```text
client_non_error_server_non_error
client_error_server_error
client_error_no_server
client_non_error_no_server
```

`UNSET` is interpreted only as not marked ERROR, not as formal proof of success.

## Positive control - paymentFailure = 100%

Artifact:

```text
data/evaluation/traces_payment_failure_100_controlled_v1.json
```

Baseline:

```text
discovered traces:       19
frozen checkout traces:  19
fetch errors:             0
excluded traces:          0

client_non_error_server_non_error: 19 / 19
client ERROR:                       0 / 19
server ERROR:                       0 / 19
```

Incident:

```text
discovered traces:       13
frozen checkout traces:  13
fetch errors:             0
excluded traces:          0

client_error_server_error: 13 / 13
client ERROR:              13 / 13
server ERROR:              13 / 13
```

Interpretation:

```text
Checkout -> Payment CLIENT ERROR
        ->
matching Payment SERVER ERROR
```

The failure reached Payment and was visible server-side. This validates the request-level transport, parser, pairing, and classification pipeline. It does not yet identify the internal Payment implementation mechanism.

## paymentUnreachable request-level result

Artifact:

```text
data/evaluation/traces_payment_unreachable_controlled_v1.json
```

Baseline:

```text
discovered traces:       18
frozen checkout traces:  18
fetch errors:             0
excluded traces:          0

client_non_error_server_non_error: 18 / 18
```

Incident:

```text
discovered traces:       12
frozen checkout traces:  12
fetch errors:             0
excluded traces:          0

client_non_error_server_non_error: 12 / 12
client ERROR:                       0 / 12
server ERROR:                       0 / 12
```

The trace layer therefore confirmed, rather than contradicted, the ambiguous metrics result. The measured load-generator requests continued to use the normal Payment path.

The missing evidence became:

> What value did the Checkout process actually evaluate for `paymentUnreachable`?

## Runtime feature-flag evidence

The frozen traces contain OpenFeature `feature_flag.evaluation` events.

All 18 baseline traces evaluated:

```text
feature_flag.result.value   = False
feature_flag.result.variant = off
feature_flag.result.reason  = cached
```

All 12 incident traces still evaluated:

```text
feature_flag.result.value   = False
feature_flag.result.variant = off
feature_flag.result.reason  = cached
```

even while the experiment's control-plane validation reported `paymentUnreachable=on`.

This explains why the measured requests showed:

```text
Checkout -> Payment non-error
Payment SERVER present
native RPC error rate = 0
trace-derived aggregate error rate = 0
```

The controlled fault was not active for those measured Checkout requests.

The defensible conclusion is a control-plane/data-plane divergence:

```text
control-plane configuration = ON
Checkout runtime evaluation = cached OFF
```

This localizes the divergence before the Payment RPC. It is not enough to label the deeper cause as a specific cache implementation bug.

## Causal intervention - restart Checkout

A targeted intervention was performed while the control-plane value remained:

```text
paymentUnreachable = on
```

Only the Checkout process was restarted.

The next trace showed:

```text
feature_flag.result.value   = True
feature_flag.result.variant = on
feature_flag.result.reason  = static
```

and:

```text
Checkout -> Payment CLIENT
status  = ERROR
message = "name resolver error: produced zero addresses"

Payment SERVER
not observed
```

The key before/after comparison is:

```text
same control-plane configuration = ON

before Checkout restart:
    runtime evaluation = OFF / cached
    Payment SERVER observed
    Checkout -> Payment non-error

after Checkout restart:
    runtime evaluation = ON / static
    Checkout -> Payment ERROR
    resolver produced zero addresses
    Payment SERVER not observed
```

Restarting only Checkout changed the runtime feature-flag evaluation and restored the expected injected fault behavior.

This strongly supports stale local/provider state in the previous Checkout process. The exact reason why the process failed to refresh or invalidate that state remains unresolved and is intentionally outside the scope of Experiment 015B.

## Main findings

1. Metrics and traces answer different questions. Metrics detect and scope population-level degradation; traces localize a failure on an individual request path.
2. Topology can remain useful when timestamps are unreliable. Parent/child structure and individual span durations remained usable despite the Quote timestamp anomaly.
3. A missing server span is not sufficient evidence of failure. Healthy traces can contain unmatched clients.
4. Aggregate ambiguity can reflect a control-plane/data-plane problem rather than an observability failure.
5. Raw traces must be frozen during experiments when the backend has ephemeral retention.
6. Causal intervention is stronger than simple correlation. Restarting only Checkout changed both the evaluated flag and the observed RPC behavior while the control-plane state stayed ON.

## Design decisions

Keep:

```text
deterministic Jaeger v3 transport
typed immutable OTLP evidence
raw nanosecond timestamps
explicit trace-integrity diagnostics
topology-first CLIENT/SERVER pairing
descriptive relation classifications
structural path comparison
experiment-time raw OTLP freezing
feature-flag evaluation events as evidence
causal interventions for ambiguous findings
```

Do not add yet:

```text
LLM-generated Jaeger queries
automatic root-cause classification inside the trace tool
arbitrary probability/confidence scores
automatic timestamp correction
unmatched-client-equals-network-failure heuristics
agent frameworks
```

## Main files

Transport and evidence:

```text
src/rootlens/observability/jaeger.py
src/rootlens/observability/trace_evidence.py
src/rootlens/observability/otlp_trace.py
src/rootlens/observability/trace_investigation.py
```

Evaluation:

```text
src/rootlens/evaluation/trace_incident.py
src/rootlens/evaluation/trace_capture.py
```

Scripts:

```text
scripts/check_jaeger.py
scripts/check_trace_parser.py
scripts/check_trace_investigation.py
scripts/evaluate_trace_incident.py
scripts/run_trace_incident_experiment.py
scripts/analyze_trace_feature_flags.py
scripts/probe_latest_payment_unreachable.py
```

Frozen artifacts:

```text
data/evaluation/traces_payment_failure_100_controlled_v1.json
data/evaluation/traces_payment_unreachable_controlled_v1.json
```

## Completion criteria

Experiment 015B is complete:

```text
[complete] Jaeger transport
[complete] OTLP parsing
[complete] structured span/trace evidence
[complete] trace-integrity diagnostics
[complete] deterministic CLIENT/SERVER pairing
[complete] unmatched-client observation
[complete] structural path comparison
[complete] real-system smoke tests
[complete] controlled positive fault evaluation
[complete] ambiguous fault investigation
[complete] raw trace freezing
[complete] causal intervention
[complete] explicit engineering decision
```

## Interview explanation

> I built the trace layer directly against Jaeger v3 and OTLP rather than using an agent framework. The parser preserves raw span provenance and reconstructs request topology, while a separate investigation tool exposes deterministic primitives such as error spans, client/server pairs, unmatched clients, and path differences. During evaluation I found a real telemetry-integrity issue: one service had an 18-hour timestamp skew, so I separated trace-envelope duration from request latency and added integrity diagnostics instead of silently fixing timestamps. For controlled payment faults, request-level traces cleanly distinguished a server-side payment failure from a client-side unreachable dependency. The more interesting result was a feature-flag control-plane/data-plane divergence: the control plane said the fault was ON, but every measured Checkout trace evaluated a cached OFF value. Restarting only Checkout changed evaluation to ON and produced the expected resolver error with no Payment server span. That reinforced the design rule that RootLens should acquire missing evidence and test hypotheses rather than force an RCA from the first anomaly.

## Decision

**Experiment 015B is frozen.**

Next:

```text
Experiment 015C
Deterministic log investigation and correlation
```

The objective is to add exact, provenance-preserving log retrieval and correlation before building any single investigation agent.

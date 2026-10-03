# Experiment 015C — Deterministic Log Investigation

**Status:** complete  
**Decision:** keep the deterministic OpenSearch log layer and freeze it before building cross-modal evidence correlation.

## Objective

Experiment 015C builds a deterministic log-investigation layer for RootLens before any agentic orchestration.

The goals are to query logs by exact time window, service, trace ID, span ID, and raw severity; preserve exact provenance and raw OpenSearch evidence; correlate logs with request-level traces; separate event time from observation time; detect telemetry-integrity problems without silently repairing them; expose possible duplicate records without silently deduplicating them; compare baseline and incident windows using per-trace prevalence rather than raw log counts; and evaluate whether logs add evidence beyond metrics and traces.

The experiment deliberately excludes LLM-generated OpenSearch/PPL queries, automatic root-cause heuristics, fuzzy body matching, severity normalization, silent timestamp repair, silent duplicate removal, and agent frameworks.

## 1. Backend and schema inspection

The OpenTelemetry Demo sends logs through the OpenTelemetry Collector into OpenSearch:

```text
application services
    -> OTLP
OpenTelemetry Collector
    -> OpenSearch
    -> otel-logs-YYYY-MM-DD
```

Observed top-level fields:

```text
@timestamp
observedTimestamp
body
severity
traceId
spanId
attributes
resource
instrumentationScope
```

Important observations:

- raw severity values are heterogeneous across runtimes (`INFO`, `info`, `Information`, and missing);
- `traceId` and `spanId` can be absent even for useful log records;
- trace-ID correlation works across multiple services;
- raw log bodies can contain highly variable fields such as timestamps, product IDs, request IDs, addresses, and ports.

## 2. Event time versus observation time

The first OpenSearch client used `@timestamp` as the discovery window. That was incorrect for this environment.

For the known post-restart `paymentUnreachable` trace:

```text
3541df651cfbedf57cb9dd68ac319682
```

a query without an event-time restriction returned 44 logs, while an `@timestamp`-bounded query returned only 38.

The six missing logs were:

```text
shipping  x2
currency  x4
```

Inspection showed:

```text
event time     = 1970-01-01T00:00:00Z
observed time  = 2026-10-03T13:29:25...
```

RootLens now uses:

```text
discovery/query window  -> observedTimestamp
event timestamp         -> @timestamp, preserved as-is
```

Both timestamps are retained in `LogEvidence`. RootLens also exposes the factual quantity `observed_minus_event_ms` rather than calling it a delay or automatically classifying it as anomalous.

No timestamp is silently repaired.

## 3. Evidence contract

`LogEvidence` preserves:

```text
event_timestamp
event_timestamp_raw
observed_timestamp
observed_timestamp_raw
service_name
severity_text
severity_number
body
trace_id
span_id
attributes
resource_attributes
instrumentation_scope
index
document_id
raw_source
source
```

Missing trace/span context remains valid evidence. Invalid or unusual timestamps are preserved rather than rewritten.

## 4. OpenSearch transport

`OpenSearchClient` provides deterministic search with exact time windows; exact service, trace ID, span ID, and raw severity filters; configurable time field; stable sorting; explicit empty results; transport/API/response error separation; and query provenance.

Default time field:

```text
observedTimestamp
```

The caller may still explicitly query by `@timestamp` when needed.

## 5. Deterministic log investigation

`LogInvestigationTool` adds deterministic operations:

```text
summarize
find_logs
order_logs
find_possible_duplicates
largest_timestamp_differences
event_signatures
compare_exact_events
```

### Exact filtering

Raw severity and body values are preserved. For example:

```text
error != ERROR != Information
```

No normalization is applied yet.

### Possible duplicates

The post-restart trace contained four possible duplicate groups from `load-generator`. RootLens reports duplicate groups but keeps all underlying OpenSearch documents.

```text
possible duplicate != safe to delete
```

### Timestamp-integrity evidence

For the known trace, the largest timestamp differences naturally surfaced the six epoch-timestamp records:

```text
currency  x4  ~1.791e12 ms
shipping  x2  ~1.791e12 ms
```

without any arbitrary anomaly threshold.

## 6. Per-trace prevalence benchmark

Raw counts are not appropriate when baseline and incident windows contain different numbers of requests.

For a log signature `s`, RootLens measures:

```text
p_B(s) = baseline traces containing s / number of baseline traces
p_I(s) = incident traces containing s / number of incident traces
delta(s) = p_I(s) - p_B(s)
```

A signature counts once per trace for prevalence even when duplicate log records exist inside that trace.

The exact signature is currently:

```text
service_name
raw severity_text
exact body
```

This is intentionally conservative and deterministic.

## 7. `paymentFailure` positive control

Frozen trace population:

```text
baseline: 19 traces
incident: 13 traces
```

Log coverage:

```text
baseline:
  traces with logs  19 / 19
  total logs        689

incident:
  traces with logs  13 / 13
  total logs        387
```

Systematic baseline-only signatures:

```text
cart       Information  "EmptyCartAsync called with userId={userId}"
checkout   INFO         "order placed"
checkout   INFO         "payment went through"
email      INFO         "Order confirmation email sent"
frontend   info         "Order placed successfully"
payment    info         "Transaction complete."
shipping   INFO         "Tracking ID Created"
```

Each had:

```text
baseline prevalence = 1.0
incident prevalence = 0.0
delta               = -1.0
```

Systematic incident-only signatures:

```text
frontend  info  "Checkout payment declined"
payment   warn  "Payment request failed. Invalid token. demo.user_context.loyalty_level=gold"
```

Each had:

```text
baseline prevalence = 0.0
incident prevalence = 1.0
delta               = +1.0
```

### Interpretation

The trace experiment had already established:

```text
Checkout -> Payment CLIENT ERROR
Payment SERVER ERROR
```

The log layer adds mechanism-level evidence inside Payment:

```text
Payment request failed. Invalid token.
```

The defensible conclusion is:

> Traces localize the failure to a request that reaches Payment and fails server-side; logs add a systematic Payment-side failure message indicating an invalid-token mechanism.

The fault label is not used as analysis evidence.

## 8. `paymentUnreachable` stale-runtime negative control

Frozen trace population:

```text
baseline: 18 traces
incident: 12 traces
```

Log coverage:

```text
baseline:
  traces with logs  18 / 18
  total logs        737

incident:
  traces with logs  12 / 12
  total logs        540
```

The largest prevalence differences were small:

```text
shipping empty body:
  baseline 2/18
  incident 0/12
  delta = -0.111

one-off frontend-proxy exact bodies:
  baseline 0/18
  incident 1/12
  delta = +0.083
```

There was no systematic Checkout/Payment incident signature comparable to the `paymentFailure` positive control.

This matches the independent trace evidence:

```text
control-plane configuration = ON
Checkout runtime evaluation = cached OFF
```

and the request-level traces remained normal.

### Interpretation

The benchmark does not invent an incident merely because the control plane reported the feature flag ON.

Across the measured stale-runtime window:

```text
metrics  -> no distinct fault signature
traces   -> normal Checkout -> Payment path
logs     -> no systematic incident signature
```

The modalities are mutually consistent.

## 9. Post-restart real `paymentUnreachable` request

After restarting only Checkout while the control-plane flag remained ON, the trace showed:

```text
feature_flag.result.value   = True
feature_flag.result.variant = on
feature_flag.result.reason  = static

Checkout -> Payment CLIENT
status  = ERROR
message = "name resolver error: produced zero addresses"

Payment SERVER
not observed
```

The correlated log artifact for the exact trace:

```text
trace_id = 3541df651cfbedf57cb9dd68ac319682
```

contains:

```text
total hits    44
returned logs 44
```

Services:

```text
cart             7
checkout         1
currency         4
frontend         8
frontend-proxy   7
load-generator   8
product-catalog  6
quote            1
shipping         2
payment          0
```

The only raw error-like log was:

```text
frontend:
  "Checkout failed to place order"
```

### Interpretation

For this failure mode:

- the logs expose the user-facing symptom;
- the logs contain no Payment record for the correlated trace;
- the precise resolver mechanism is carried by the Checkout client span, not by the inspected log bodies;
- absence of Payment logs is not, by itself, proof that Payment never executed;
- the stronger request-level evidence remains the trace topology plus the resolver error.

Therefore logs do not add the same level of mechanism evidence here as they did for `paymentFailure`.

## 10. Cross-modal result

The main 015C result is not that logs are globally better or worse than traces.

> **The evidential value of each telemetry modality is failure-dependent.**

Observed examples:

```text
paymentFailure
  metrics -> detect error behavior
  traces  -> localize failure to Payment server-side
  logs    -> add invalid-token mechanism

paymentUnreachable stale-runtime window
  metrics -> no distinct fault signal
  traces  -> runtime requests remain normal
  logs    -> no systematic incident signature

paymentUnreachable real ON request
  traces  -> expose resolver failure before Payment server
  logs    -> expose user-facing checkout failure, not resolver mechanism
```

This justifies preserving multiple deterministic modalities rather than collapsing them into one heuristic score.

## 11. Noise and current limitations

Exact body signatures create noise for access logs because bodies contain dynamic values such as timestamps, product IDs, request IDs, response sizes, IP addresses, and ports.

Decision:

> Do not add body templating, regex normalization, or semantic clustering yet.

The high-value positive-control signals were already visible at `|delta| = 1.0`, so normalization is not currently required to recover the relevant evidence.

Other limitations:

- severity remains raw and heterogeneous;
- no calibrated anomaly score is produced;
- missing logs are not interpreted as proof of missing execution;
- exact-body comparison is conservative;
- log retention still requires timely freezing of evidence.

## 12. Files introduced in 015C

Core implementation:

```text
src/rootlens/observability/log_evidence.py
src/rootlens/observability/opensearch.py
src/rootlens/observability/log_investigation.py
src/rootlens/evaluation/log_incident.py
```

Validation and experiment scripts:

```text
scripts/check_opensearch.py
scripts/check_log_investigation.py
scripts/run_log_incident_evaluation.py
scripts/capture_trace_logs.py
```

Tests:

```text
tests/observability/test_log_evidence.py
tests/observability/test_opensearch.py
tests/observability/test_log_investigation.py
tests/evaluation/test_log_incident.py
```

Frozen evaluation artifacts:

```text
data/evaluation/logs_payment_failure_100_controlled_v1.json
data/evaluation/logs_payment_unreachable_controlled_v1.json
data/evaluation/logs_payment_unreachable_post_restart_trace_v1.json
```

## 13. Decision

Experiment 015C is frozen.

Keep:

```text
OpenSearch transport
typed LogEvidence
observedTimestamp discovery
raw event-time preservation
exact query provenance
exact filtering
possible-duplicate reporting
timestamp-integrity evidence
trace-ID correlation
per-trace signature prevalence
raw frozen log artifacts
```

Do not add yet:

```text
LLM-generated log queries
automatic root-cause rules
severity normalization
silent deduplication
silent timestamp correction
body templating
semantic log clustering
agent frameworks
```

## 14. Next experiment

**Experiment 015D — Unified Cross-Modal Evidence**

The next layer will combine metrics, traces, and logs into a single deterministic evidence contract before the first investigation agent.

The design goal is not to produce a root cause automatically. It is to make evidence from different modalities comparable and correlatable while preserving:

```text
source
time window
service
trace/span identity
query provenance
raw evidence
integrity diagnostics
what was observed
what remains unknown
```

This is the final deterministic layer before the first custom investigation loop.

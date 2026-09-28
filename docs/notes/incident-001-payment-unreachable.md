# Incident 001 — Payment Service Unreachable

## Status

**Resolved**

## Type

**Calibration incident — manual root-cause analysis**

This incident is intentionally used to understand and document the investigation workflow that RootLens will later automate.

It is **not** considered a blind evaluation incident because the injected fault was known beforehand.

---

# 1. Objective

The objective of this experiment is to manually investigate a failure affecting the checkout workflow using observability signals only:

- metrics;
- distributed traces;
- structured logs;
- browser/network observations.

The investigation should clearly distinguish:

- user-visible symptoms;
- observations;
- interpretations;
- hypotheses;
- supporting evidence;
- contradicting evidence;
- rejected hypotheses;
- failure mechanism;
- root cause.

This manual investigation will later serve as a reference trajectory for evaluating RootLens.

The goal is not only to identify the correct root cause, but also to document **how an investigator progressively reduces the search space using different observability signals**.

---

# 2. System

The experiment runs on the OpenTelemetry Demo deployed locally with Docker.

The checkout workflow involves several downstream services, including:

- Cart;
- Product Catalog;
- Currency;
- Shipping;
- Payment.

A simplified healthy request path is:

```text
User
 ↓
Frontend
 ↓
CheckoutService.PlaceOrder
 ├── Cart
 ├── Product Catalog
 ├── Currency
 ├── Shipping
 └── Payment
```

The observability stack provides three main types of telemetry:

```text
Metrics → Prometheus
Traces  → Jaeger
Logs    → OpenSearch
```

These signals are collected through OpenTelemetry.

The objective of RootLens will eventually be to correlate these signals automatically rather than analyze each system independently.

---

# 3. Healthy Baseline

Before injecting the fault, the normal behaviour of the Checkout service was measured.

The following operation was used as the baseline:

```text
Service:
checkout

Operation:
oteldemo.CheckoutService/PlaceOrder

Observation window:
5 minutes
```

The measured baseline was:

| Signal | Healthy baseline |
|---|---:|
| Traffic | ~0.046 req/s |
| Traffic | ~2.75 req/min |
| p50 latency | ~84 ms |
| p95 latency | ~350 ms |
| p99 latency | ~468 ms |
| Error rate | 0% |
| RPC status | `OK` |

A healthy distributed trace showed Checkout successfully calling its downstream dependencies.

Example healthy execution:

```text
Frontend
 ↓
CheckoutService.PlaceOrder
 ├── CartService
 ├── ProductCatalogService
 ├── CurrencyService
 ├── ShippingService
 └── PaymentService.Charge
```

No error was observed during the healthy baseline.

The baseline is important because an incident cannot be identified only from an absolute value.

For example:

```text
p95 = 350 ms
```

has little meaning without knowing whether the normal value is:

```text
100 ms
```

or:

```text
340 ms
```

RootLens will therefore eventually require some notion of historical or reference behaviour.

---

# 4. Fault Injection

The following fault was activated:

```text
paymentUnreachable
```

Approximate incident start:

```text
T0 ≈ 2026-09-28 22:50 CEST
```

The load generator remained active so that the system continued receiving traffic during the incident.

The objective was to observe how the fault propagates from the underlying system to the final user-visible symptom.

---

# 5. User-Visible Symptom

After fault injection, clicking `Place Order` did not complete successfully.

Initially, this could have suggested several possibilities:

- the frontend button was broken;
- the frontend failed to send the request;
- the request never reached Checkout;
- Checkout failed;
- a downstream dependency failed;
- the request timed out.

Browser DevTools were therefore used to verify what actually happened.

The browser generated:

```text
POST http://localhost:8080/api/checkout?currencyCode=USD
```

The server returned:

```text
HTTP 500 Internal Server Error
```

The frontend then reported:

```text
Failed to place order.
```

## Observation O1 — The frontend successfully sends the request

The `Place Order` action correctly generated the expected HTTP request.

The request reached the backend and returned HTTP 500.

Therefore, the failure was not caused by a simple frontend click-handler problem.

---

# 6. Metrics Investigation

The next step was to determine whether the issue represented:

- a traffic problem;
- a latency problem;
- an availability problem;
- an error-rate problem.

Metrics were inspected for:

```text
service_name = checkout

rpc_method =
oteldemo.CheckoutService/PlaceOrder
```

A five-minute observation window was used.

---

## 6.1 Traffic

During the incident:

```text
~0.051 req/s
```

Healthy baseline:

```text
~0.046 req/s
```

Traffic therefore remained approximately stable.

## Observation O2 — No significant traffic increase

There was no evidence of a large traffic increase during the incident.

This made a sudden load spike significantly less likely as an explanation.

The observed degradation therefore could not simply be explained by:

```text
more traffic
    ↓
service saturation
    ↓
failures
```

---

# 7. Latency Investigation

The measured latency distributions were:

| Percentile | Healthy | Incident |
|---|---:|---:|
| p50 | ~84 ms | ~199 ms |
| p95 | ~350 ms | ~471 ms |
| p99 | ~468 ms | ~494 ms |

Median latency increased substantially.

p95 also increased.

However, p99 remained relatively close to its healthy value.

## Observation O3 — Moderate latency degradation

Latency degraded during the incident, particularly at p50 and p95.

However, latency degradation was modest compared with the increase in failed requests observed later.

This suggested that the incident was primarily an **availability or correctness failure**, rather than a pure performance degradation.

An important lesson is:

```text
failure ≠ necessarily high latency
```

A request can fail almost immediately.

---

# 8. Error Rate Investigation

Healthy baseline:

```text
0%
```

During the incident:

```text
~63.7%
```

The Checkout RPC metrics now exposed two response statuses:

```text
OK
INTERNAL
```

Approximate request rates observed during one measurement window were:

```text
OK       ≈ 0.0208 req/s
INTERNAL ≈ 0.0391 req/s
```

## Observation O4 — Checkout failures increased sharply

`CheckoutService.PlaceOrder` continued receiving requests.

However, a large fraction terminated with:

```text
rpc_response_status_code = INTERNAL
```

Therefore:

```text
requests are reaching Checkout
```

but:

```text
many requests fail during processing
```

The strongest anomaly was therefore the error rate.

---

# 9. Initial Hypotheses

At this point only:

- user behaviour;
- browser networking;
- metrics

had been inspected.

Distributed traces had not yet been analyzed.

Several possible explanations remained plausible.

---

## H1 — Frontend Failure

Possible explanation:

The frontend button or frontend application may have failed to send the checkout request.

### Evidence against

Browser DevTools showed:

```text
POST /api/checkout
→ HTTP 500
```

The request successfully reached the backend.

### Status

**Rejected**

---

## H2 — Traffic Overload or Resource Saturation

Possible explanation:

Checkout or one of its dependencies might be overloaded because of increased request volume.

### Evidence for

Latency increased during the incident.

### Evidence against

Traffic remained approximately stable:

```text
Healthy  ≈ 0.046 req/s

Incident ≈ 0.051 req/s
```

The error rate changed much more dramatically than request volume.

### Status

**Unlikely**

---

## H3 — Internal Checkout Application Failure

Possible explanation:

Checkout itself may fail internally while processing the order.

### Supporting evidence

`CheckoutService.PlaceOrder` returned:

```text
INTERNAL
```

### Missing evidence

The precise location of the failure inside the Checkout workflow was unknown.

### Status

**Open**

---

## H4 — Downstream Dependency Failure

Possible explanation:

One of the services called by Checkout may be unavailable or failing.

### Supporting evidence

Checkout orchestrates several downstream calls.

A failure in one of these services could propagate upward and eventually appear as:

```text
CheckoutService.PlaceOrder → INTERNAL
```

### Status

**Open**

---

# 10. Distributed Trace Investigation

A failing `CheckoutService.PlaceOrder` trace was inspected in Jaeger.

The trace approximately showed:

```text
Frontend                    ERROR / HTTP 500
 ↓
CheckoutService.PlaceOrder  ERROR
 │
 ├── Cart                    OK
 ├── Product Catalog         OK
 ├── Currency                OK
 ├── Shipping                OK
 └── PaymentService.Charge   ERROR
```

The earlier order-preparation operations completed successfully.

Successful operations included:

- retrieving the shopping cart;
- retrieving product information;
- currency operations;
- calculating shipping information.

The failure appeared specifically when Checkout attempted to call PaymentService.

---

# 11. Observation O5 — Failure Localized to Checkout → Payment

Several Checkout dependencies successfully completed their operations.

The failing branch was:

```text
Checkout
 ↓
PaymentService.Charge
```

This significantly reduced the investigation search space.

Before inspecting the trace, the problem could have originated from many services.

After inspecting the trace, the investigation could focus specifically on the interaction between:

```text
Checkout
```

and:

```text
PaymentService
```

This illustrates one of the main benefits of distributed tracing:

```text
large distributed system
        ↓
specific failing execution path
```

---

# 12. Payment RPC Investigation

The failing span was:

```text
oteldemo.PaymentService/Charge
```

The span was emitted by:

```text
service = checkout
```

It represented a client-side gRPC request.

Relevant span attributes were:

```text
error = true

otel.status_code = ERROR

otel.status_description =
"name resolver error: produced zero addresses"

rpc.method =
oteldemo.PaymentService/Charge

rpc.response.status_code =
UNAVAILABLE

rpc.system.name =
grpc

span.kind =
client
```

The failing span lasted approximately:

```text
551 µs
```

No corresponding successful PaymentService server span appeared after the failing client request.

---

# 13. Observation O6 — Payment RPC Fails Before Reaching PaymentService

The error occurred on the Checkout client side.

The RPC failed before PaymentService successfully received and processed the `Charge` request.

The key error was:

```text
name resolver error: produced zero addresses
```

and the RPC status was:

```text
UNAVAILABLE
```

The absence of a Payment server span was particularly informative.

The execution looked like:

```text
Checkout
   │
   │ attempt PaymentService.Charge
   ▼
gRPC name resolution
   │
   └── no usable address
          ↓
       UNAVAILABLE
```

rather than:

```text
Checkout
   ↓
Payment
   ↓
Payment application crashes
```

---

# 14. Interpretation

The failing Payment call lasted only approximately:

```text
551 µs
```

This was inconsistent with:

- a long-running Payment computation;
- a multi-second timeout;
- a slow Payment business operation.

Instead, the trace explicitly reported:

```text
name resolver error: produced zero addresses
```

This indicated that the gRPC client could not obtain a usable network destination for PaymentService.

## Interpretation I1

Checkout was unable to resolve a valid PaymentService destination.

---

# 15. Updated Hypotheses

## H3 — Internal Checkout Application Failure

### Evidence against

Checkout successfully performed the earlier order preparation steps.

Several other downstream dependencies completed successfully.

The failure was localized specifically to the Payment RPC call.

### Status

**Very unlikely**

---

## H4 — PaymentService Application Failure

Possible explanation:

PaymentService may have received the request and crashed while processing the payment.

### Evidence against

No PaymentService server span appeared for the failing `Charge` request.

The failure happened on the Checkout client side during destination resolution.

### Status

**Rejected**

---

## H5 — Checkout Cannot Resolve the PaymentService Endpoint

### Supporting evidence

- `PaymentService/Charge` client span is in error.
- RPC status is `UNAVAILABLE`.
- The span reports `name resolver error: produced zero addresses`.
- No Payment server span follows the failing client span.
- Other Checkout dependencies remain healthy.
- Traffic remains approximately stable.

### Status

**Strongly supported**

---

# 16. Log Correlation

The failing distributed trace was correlated with structured logs in OpenSearch using its full `traceId`.

The trace ID retrieved logs produced by multiple services participating in the same distributed request.

Observed logs included:

```text
currency          conversion successful
shipping          Requesting quote
shipping          Sending Quote
checkout          [PlaceOrder]
cart              GetCartAsync...
product-catalog   Product Found
quote             Calculated quote
frontend          Checkout failed to place order
frontend          API request completed
```

These logs confirmed that several operations completed normally before the final Checkout failure.

This was consistent with the distributed trace.

---

# 17. Trace and Log Correlation

Logs sharing the same `traceId` belong to the same distributed execution.

For example:

```text
Trace ID
   │
   ├── Checkout log
   ├── Cart log
   ├── Shipping log
   ├── Product Catalog log
   └── Frontend log
```

The `spanId` provides an even more precise link between a log record and a particular operation within that trace.

This demonstrated that telemetry from multiple services can be joined without relying only on timestamps.

---

# 18. Telemetry Quality Observation

Some logs displayed timestamps around:

```text
1970-01-01
```

These were clearly inconsistent with the real incident time.

This likely reflects missing or incorrectly mapped timestamps in some log records.

## Observation O7 — Telemetry itself can be imperfect

RootLens must not assume that every telemetry field is always reliable.

Future investigation logic should be able to tolerate:

- missing timestamps;
- malformed timestamps;
- missing trace IDs;
- incomplete spans;
- noisy telemetry;
- unrelated errors.

---

# 19. Unrelated / Noisy Evidence

During the investigation, another error was observed involving:

```text
payment
 ↓
flagd
```

for:

```text
flagd.evaluation.v2.Service/EventStream
```

with:

```text
DEADLINE_EXCEEDED
```

However, this error was not selected as the root cause.

The failing Checkout execution already showed:

```text
Checkout
 ↓
PaymentService.Charge
 ↓
name resolver error
```

before PaymentService successfully received the request.

Therefore, the `payment → flagd` error did not provide a better causal explanation for the observed Checkout failure.

This demonstrates an important investigation principle:

> Not every error observed during an incident is causally related to the user-visible failure.

---

# 20. Root Cause

Checkout was unable to resolve a valid network destination for PaymentService.

The `oteldemo.PaymentService/Charge` gRPC client call failed with:

```text
rpc.response.status_code = UNAVAILABLE
```

and:

```text
name resolver error: produced zero addresses
```

Because Checkout could not resolve a valid PaymentService destination:

```text
PaymentService.Charge failed
        ↓
CheckoutService.PlaceOrder returned INTERNAL
        ↓
Frontend /api/checkout returned HTTP 500
        ↓
User could not place the order
```

The injected ground truth confirmed this diagnosis:

```text
paymentUnreachable
```

intentionally configured Checkout to use an invalid or unreachable PaymentService destination.

---

# 21. Causal Chain

The final causal chain was:

```text
Invalid / unresolvable PaymentService destination
                  ↓
Checkout gRPC resolver finds zero addresses
                  ↓
PaymentService/Charge returns UNAVAILABLE
                  ↓
CheckoutService.PlaceOrder returns INTERNAL
                  ↓
Frontend /api/checkout returns HTTP 500
                  ↓
"Failed to place order"
```

---

# 22. Rejected Hypotheses

| Hypothesis | Decision | Main evidence |
|---|---|---|
| Frontend button failure | Rejected | POST request reached backend |
| Traffic overload | Unlikely | Traffic remained approximately stable |
| Generic Checkout failure | Very unlikely | Earlier Checkout operations succeeded |
| Payment application crash | Rejected | Payment server never received failing RPC |
| Payment endpoint resolution failure | Supported | `UNAVAILABLE` + `produced zero addresses` |

---

# 23. Human Investigation Trajectory

The complete manual investigation followed this sequence:

```text
1. Observe user-visible checkout failure
             ↓
2. Inspect Checkout metrics
             ↓
3. Detect large increase in INTERNAL errors
             ↓
4. Verify POST /api/checkout → HTTP 500
             ↓
5. Form initial hypotheses
             ↓
6. Inspect failing PlaceOrder trace
             ↓
7. Verify Cart / Product / Currency / Shipping succeed
             ↓
8. Localize failure to PaymentService/Charge
             ↓
9. Inspect Payment client span
             ↓
10. Find UNAVAILABLE + name resolver error
             ↓
11. Correlate trace with structured logs
             ↓
12. Reject unrelated errors
             ↓
13. Compare diagnosis with injected ground truth
```

This trajectory is important because it provides a human reference for the future RootLens investigation engine.

---

# 24. Role of Each Observability Signal

## Metrics

Metrics answered:

```text
Is the system behaving abnormally?
```

They showed:

- traffic remained stable;
- error rate increased dramatically;
- latency increased moderately.

Metrics confirmed and quantified the incident.

They did not identify the root cause.

---

## Traces

Distributed traces answered:

```text
Where does the failing request break?
```

They showed:

```text
Checkout
 ├── Cart              OK
 ├── Product Catalog   OK
 ├── Currency          OK
 ├── Shipping          OK
 └── Payment           ERROR
```

Tracing provided the strongest evidence in this investigation.

The Payment client span then exposed the exact failure mechanism:

```text
name resolver error: produced zero addresses
```

---

## Logs

Logs answered:

```text
What events occurred during this distributed request?
```

Using the trace ID allowed logs from multiple services to be correlated.

Logs showed successful activity from several services followed by:

```text
Checkout failed to place order
```

However, the precise resolver failure was represented more clearly in the trace than in application logs.

Therefore:

> The most useful observability signal depends on the incident.

---

# 25. Main Lessons Learned

## 25.1 Symptom is not root cause

The initial symptom was:

```text
Place Order does not work.
```

The final root cause was:

```text
Checkout cannot resolve a valid PaymentService destination.
```

Several investigation steps were necessary to bridge the gap between these two statements.

---

## 25.2 Error status alone is insufficient

The Checkout metric reported:

```text
INTERNAL
```

but this did not imply that Checkout itself was the root cause.

The failure actually originated from its interaction with another service.

---

## 25.3 Failure does not necessarily mean high latency

The failing Payment RPC lasted only approximately:

```text
551 µs
```

The request failed very quickly.

Therefore:

```text
failure ≠ necessarily high latency
```

An investigation system must analyze error rates as well as latency.

---

## 25.4 Not every error is causal

The unrelated `flagd` error demonstrated that an investigator cannot simply find the first error and declare it to be the root cause.

Evidence must be connected to the failing request and explain the causal chain.

A useful future RootLens check may therefore ask:

```text
Is this error on the failing request path?

Does it share the relevant trace?

Does it occur before the user-visible failure?

Does it explain the observed symptom?

Is there stronger contradictory evidence?
```

---

## 25.5 Trace IDs are essential for correlation

A `traceId` can connect telemetry produced by several services during the same distributed request.

A `spanId` provides a more precise link to an individual operation.

This enables:

```text
failing trace
     ↓
failing span
     ↓
relevant logs only
```

rather than searching through all application logs.

---

## 25.6 Telemetry can be noisy or incomplete

Some log timestamps were inconsistent.

Some errors were unrelated to the incident.

Some signals provided better information than others.

RootLens must therefore treat telemetry as evidence that may contain noise rather than as perfect ground truth.

---

## 25.7 Observation, interpretation and hypothesis must remain separate

A useful investigation model is:

```text
Observation
    ↓
Interpretation
    ↓
Hypothesis
    ↓
Evidence gathering
    ↓
Hypothesis evaluation
    ↓
Root cause
```

For example:

```text
Observation:
Checkout error rate increased.

Interpretation:
The service is experiencing a correctness or availability problem.

Hypothesis:
A downstream dependency may be unavailable.

Evidence:
PaymentService/Charge returns UNAVAILABLE.

Conclusion:
Checkout cannot resolve PaymentService.
```

RootLens should preserve this distinction explicitly.

---

# 26. Investigation Model for RootLens

This incident suggests that RootLens should explicitly maintain:

```text
observations
hypotheses
supporting evidence
contradicting evidence
rejected hypotheses
open questions
tool calls
```

rather than relying only on a free-form conversation history.

A possible future investigation state could be:

```json
{
  "incident": {},
  "observations": [],
  "hypotheses": [],
  "supporting_evidence": [],
  "contradicting_evidence": [],
  "rejected_hypotheses": [],
  "open_questions": [],
  "tool_calls": []
}
```

A hypothesis could eventually look like:

```json
{
  "id": "H5",
  "claim": "Checkout cannot resolve PaymentService",
  "supporting_evidence": [
    "Payment RPC returns UNAVAILABLE",
    "name resolver produced zero addresses"
  ],
  "contradicting_evidence": [],
  "status": "supported"
}
```

The system should avoid assigning arbitrary LLM-generated probabilities unless confidence values are rigorously defined.

---

# 27. Potential Deterministic Tools

The manual investigation naturally identified several tools that a future RootLens investigator may require.

## Metrics tools

```text
get_service_health()
get_request_rate()
get_error_rate()
get_latency_percentile()
```

## Trace tools

```text
find_failing_traces()
get_trace()
find_error_spans()
get_service_dependencies()
```

## Log tools

```text
get_logs_by_trace_id()
get_logs_by_span_id()
search_service_logs()
```

These tools should expose stable structured outputs rather than forcing the LLM to generate raw PromQL or OpenSearch queries for every operation.

This should improve:

- reliability;
- reproducibility;
- testability;
- tool-selection evaluation.

---

# 28. Example Future Automated Investigation

A future RootLens investigation could reproduce the manual process:

```text
User:
"Checkout is failing."
        ↓
get_service_health("checkout")
        ↓
Observation:
error rate increased
        ↓
find_failing_traces("checkout")
        ↓
Trace:
PaymentService/Charge ERROR
        ↓
find_error_spans(...)
        ↓
Evidence:
UNAVAILABLE
name resolver produced zero addresses
        ↓
get_logs_by_trace_id(...)
        ↓
Corroborating evidence
        ↓
Hypothesis evaluation
        ↓
Root cause report
```

This workflow should initially be implemented deterministically before being made increasingly agentic.

---

# 29. Ground-Truth Note

Because the `paymentUnreachable` fault was known before the investigation, this incident must not be used as an unbiased evaluation sample for RootLens.

It is a **calibration incident**.

Future benchmark incidents should separate:

```text
information available to RootLens
```

from:

```text
hidden evaluation ground truth
```

The injected fault should not be visible to the AI during evaluation.

This separation will be necessary to prevent label leakage.

---

# 30. Final Incident Summary

## Symptom

```text
Place Order fails.
```

## User-facing error

```text
HTTP 500 Internal Server Error
```

## Checkout RPC status

```text
INTERNAL
```

## Failing dependency

```text
PaymentService.Charge
```

## Payment RPC status

```text
UNAVAILABLE
```

## Failure mechanism

```text
name resolver error: produced zero addresses
```

## Root cause

```text
Checkout is configured with an invalid or unresolvable
PaymentService destination.
```

## Ground truth

```text
paymentUnreachable
```

## Result

```text
Manual RCA: successful
```

---

# 31. Conclusion

This first calibration incident demonstrated that a useful root-cause investigation requires more than finding an error message.

The investigation progressively reduced the search space:

```text
User symptom
    ↓
HTTP failure
    ↓
Metrics anomaly
    ↓
Checkout failure
    ↓
Distributed trace
    ↓
Payment dependency
    ↓
Failing client span
    ↓
Name-resolution failure
    ↓
Root cause
```

Each observability signal contributed differently:

```text
Metrics
→ quantify the incident

Traces
→ localize the failure

Logs
→ reconstruct and corroborate events

Ground truth
→ validate the final diagnosis
```

The incident also demonstrated several principles that should guide RootLens:

1. observations must remain separate from hypotheses;
2. errors must be evaluated for causal relevance;
3. multiple telemetry sources should be correlated rather than searched independently;
4. live telemetry should primarily be accessed through deterministic tools;
5. investigation state should explicitly preserve evidence and rejected hypotheses;
6. automated RCA must be evaluated against hidden ground truth;
7. the simplest reliable workflow should be established before introducing agentic behaviour.

This incident therefore provides both:

- the first successful manual RCA;
- the initial specification of the capabilities that RootLens will later automate.

# Observability Guide

Observability combines multiple telemetry signals to understand the internal behavior of a distributed system from its external outputs.

The three primary signals used by RootLens are metrics, traces, and logs.

Metrics answer questions such as:

- Is error rate increasing?
- Is latency degrading?
- How much traffic is affected?
- Is a resource saturated?

Distributed traces reconstruct the path of an individual request across service boundaries. They are particularly useful for locating the dependency or operation where a failing request diverges from a healthy one.

Logs provide detailed events emitted during execution. Structured logs can include service names, error fields, trace IDs, span IDs, and application-specific context.

A typical investigation may proceed from aggregate symptoms to request-level evidence:

```text
metrics
→ detect and quantify degradation

traces
→ localize the failing path

logs
→ identify the detailed mechanism
```

This order is useful but not mandatory.

Observability evidence should be interpreted causally. An error in telemetry is not necessarily the root cause simply because it is visible.

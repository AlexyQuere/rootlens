# Telemetry Correlation

Root-cause analysis often requires linking metrics, traces, and logs that describe the same incident from different perspectives.

Metrics are aggregated, so they rarely identify a single request. Traces and logs provide request-level evidence.

A common correlation workflow is:

1. Use metrics to identify the affected service, time window, and symptom.
2. Select a failing trace from that interval.
3. Use the trace ID to find logs emitted by services on that request path.
4. Compare failing and healthy traces when possible.
5. Check whether the detailed log message is consistent with the failing span.

`TraceId` and `SpanId` serve different purposes. A trace ID groups the entire distributed request, while a span ID identifies one operation within that trace.

Searching logs with a span ID when the logging backend expects the trace ID may return incomplete or misleading results.

Correlation does not establish causality by itself. A log can share the correct trace ID and still describe a non-causal warning. Evidence should also explain the observed failure and occur on the relevant causal path.

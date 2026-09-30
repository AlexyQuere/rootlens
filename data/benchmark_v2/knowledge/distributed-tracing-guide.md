# Distributed Tracing Guide

A distributed trace represents the execution path of one request across multiple services.

A trace contains spans. Each span represents an operation such as an HTTP request, gRPC call, database query, or internal computation.

Important identifiers include:

- `TraceId`: identifies the complete distributed request;
- `SpanId`: identifies one operation inside the trace;
- parent span ID: links a child operation to its caller.

Trace IDs are typically longer than span IDs and should not be confused when correlating telemetry.

Span kinds commonly include:

- SERVER;
- CLIENT;
- INTERNAL;
- PRODUCER;
- CONSUMER.

When diagnosing a failed RPC, compare the client span with the corresponding server span. A client error with no downstream server span suggests that the request may have failed before reaching the service.

Do not sum span durations to estimate total request time. Parent spans include child time, and parallel spans can overlap.

The critical path is more informative for latency analysis than simply selecting the longest visible span.

Tracing is especially useful for distinguishing healthy upstream dependencies from the first failing dependency on a specific request path.

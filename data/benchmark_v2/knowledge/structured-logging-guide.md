# Structured Logging Guide

Structured logs represent events using fields rather than relying only on free-form text.

A structured log entry may contain:

- timestamp;
- severity;
- message body;
- `resource.service.name`;
- trace ID;
- span ID;
- error code;
- request or user context.

Trace and span identifiers allow logs to be correlated with a distributed trace when the application emits them correctly.

Not every log entry has trace context. Background tasks, startup messages, health checks, and infrastructure logs may not belong to a user request.

Investigators should avoid searching only for the word "error" and assuming every match is causal. A relevant log should ideally satisfy several conditions:

- it occurs in the incident time window;
- it belongs to a service on the failing request path;
- it shares the relevant trace ID when available;
- its message explains or supports the observed failure.

Telemetry can contain malformed or surprising timestamps. Such data-quality problems should be recorded rather than silently treated as trustworthy evidence.

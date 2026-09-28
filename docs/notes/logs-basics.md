# Logs Basics

## What is a log?

A log represents an event emitted by an application at a particular
point in time.

Unlike metrics, logs describe individual events rather than aggregated
system behaviour.

Unlike traces, a log does not necessarily represent the complete
execution path of a request.

## Structured logs

The Checkout Service emits structured logs containing business
attributes such as:

- `demo.order.id`
- `demo.order.amount`
- `demo.order.items.count`
- `demo.shipping.amount`

Structured attributes make logs easier to filter and process
automatically than free-form text alone.

## Log record fields

An OpenTelemetry log can contain:

- timestamp;
- body;
- severity;
- trace ID;
- span ID;
- resource information;
- attributes.

Trace and span IDs are particularly useful because they allow a log
to be correlated with the distributed trace that generated it.

## Logs and trace correlation

If a log and a trace share the same Trace ID, they belong to the same
distributed execution.

The Span ID can provide an even more precise link to the operation that
emitted the log.

Conceptually:

Metrics
→ detect degradation

Trace
→ identify suspicious request path

Span
→ identify suspicious operation

Logs associated with trace/span
→ inspect detailed events and errors

## Why logs matter for RootLens

Logs can provide detailed information about failures that is not
visible in aggregate metrics.

However, a log message is still evidence rather than necessarily the
root cause.

For example:

"connection refused"

describes a failure mechanism, but additional investigation may still
be required to determine why the connection was refused.
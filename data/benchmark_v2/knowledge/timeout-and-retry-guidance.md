# Timeout and Retry Guidance

Timeouts and retries protect distributed systems from waiting indefinitely on dependencies, but poor retry policy can amplify incidents.

A request that exceeds its configured deadline may surface as `DEADLINE_EXCEEDED`. Investigators should determine where the time was actually spent instead of assuming the slowest-looking span is the root cause.

Retries can help with transient failures such as temporary connection errors, but retries may also:

- increase downstream load;
- extend end-to-end latency;
- create retry storms;
- duplicate non-idempotent operations;
- hide the original failure pattern.

Retry policies should consider idempotency, backoff, jitter, maximum attempts, and total time budget.

For diagnosis, inspect:

- caller deadline;
- number of attempts;
- per-attempt latency;
- downstream server spans;
- total parent-span duration;
- whether retry attempts overlap or occur sequentially.

A `DEADLINE_EXCEEDED` error does not automatically imply a network failure. It means the deadline expired; traces and metrics are needed to identify why.

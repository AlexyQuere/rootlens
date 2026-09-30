# Metrics Guide

Metrics summarize system behavior over time.

Common metric types include counters, gauges, and histograms.

A counter increases cumulatively. Request counters are usually converted into rates using a function such as `rate(counter[5m])`.

A gauge can move up or down and is useful for quantities such as queue depth, memory usage, or active connections.

Histograms aggregate observations into buckets and can be used to estimate latency percentiles such as p50, p95, and p99.

For service health, useful signals include:

- traffic;
- error rate;
- latency;
- saturation.

These are closely related to the SRE "golden signals".

When evaluating checkout behavior, metrics can show that `oteldemo.CheckoutService/PlaceOrder` has an elevated error rate or latency. Metrics alone normally cannot identify the exact downstream call that failed for an individual request.

Always distinguish zero from missing data. An absent series may mean that no metric exists or no samples were emitted, not that the measured value is zero.

Metrics are strongest for detection and quantification; traces and logs are usually needed for request-level root-cause evidence.

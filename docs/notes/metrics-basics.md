# Metrics Basics

## What is a metric?

A metric represents a numerical measurement of a system over time.

Unlike a distributed trace, which describes one particular request,
metrics provide an aggregated view of the behaviour of many requests.

A metric can be viewed conceptually as a time series:

value = f(time)

with additional labels describing what is being measured.

For example, the Checkout Service exposes metrics with labels such as:

- `service_name="checkout"`
- `rpc_method="oteldemo.CheckoutService/PlaceOrder"`
- `rpc_response_status_code="OK"`
- `rpc_system_name="grpc"`
- `service_version="3.1.0"`

These labels allow metrics to be filtered and aggregated.

---

## Counters

A counter represents a cumulative quantity.

For example:

`rpc_server_call_duration_seconds_count`

contains the number of RPC calls observed.

The raw counter value is not the current request rate.

To estimate requests per second, Prometheus uses the `rate()` function:

For the `CheckoutService/PlaceOrder` operation, a healthy baseline gave
approximately:

- p50: 84 ms
- p95: 350 ms
- p99: 468 ms

| Metric | Value |
|---|---:|
| Traffic | ~0.046 req/s |
| p50 latency | ~84 ms |
| p95 latency | ~350 ms |
| p99 latency | ~468 ms |
| Error rate | 0% |
```promql
rate(counter[5m])
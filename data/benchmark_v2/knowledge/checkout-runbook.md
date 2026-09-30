# Checkout Runbook

Use this runbook when users cannot complete checkout or `/api/checkout` returns errors.

## 1. Confirm impact

Check:

- `oteldemo.CheckoutService/PlaceOrder` request rate;
- error rate;
- p50, p95, and p99 latency;
- whether the failure is global or intermittent.

## 2. Select a failing request

Open a failing distributed trace and inspect Checkout and its downstream calls.

Expected dependencies can include:

- Cart;
- Product Catalog;
- Currency;
- Shipping;
- Payment.

## 3. Identify the first failing dependency

Do not assume the final Checkout error is the root cause.

For each failing client span, check:

- gRPC status;
- status description;
- whether a matching server span exists;
- whether earlier dependencies completed successfully.

## 4. Correlate logs

Search logs using the full trace ID. Look for application errors in services on the failing path.

## 5. Compare with healthy behavior

A healthy trace provides a useful reference for normal dependency ordering and approximate latency.

## 6. Check configuration only after localization

If the trace indicates connection or resolution failure, inspect endpoint and service-discovery configuration.

If the request reached the downstream server, investigate that service's application logs.

Record the final conclusion with explicit evidence and rejected alternatives.

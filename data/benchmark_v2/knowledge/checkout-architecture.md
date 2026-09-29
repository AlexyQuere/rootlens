# Checkout Architecture

The Checkout service coordinates the order-placement workflow. Its main operation is `oteldemo.CheckoutService/PlaceOrder`.

A typical checkout request retrieves the customer's cart, resolves product information, converts prices when needed, obtains a shipping quote, charges the customer, and creates the final order response. Checkout is therefore an orchestration service: a failure in one downstream dependency can make `PlaceOrder` fail even when the Checkout process itself is healthy.

The most important downstream calls are:

- Cart service for the current basket;
- Product Catalog for product metadata;
- Currency service for price conversion;
- Shipping service for delivery cost;
- Payment service for the final charge.

Most service-to-service calls use gRPC. A distributed trace is the best source for determining which dependency was reached and which call failed for a specific request.

A failed child span should not automatically be interpreted as a downstream application failure. For example, a client span may fail before a corresponding server span exists. That pattern can indicate service discovery, DNS, connection, or transport problems.

Useful evidence during investigation includes:

- the `oteldemo.CheckoutService/PlaceOrder` server span;
- child spans for downstream RPC calls;
- `rpc.response.status_code`;
- trace-correlated Checkout logs;
- the error rate and latency of `PlaceOrder`.

Checkout owns orchestration logic, but it does not own payment authorization, product catalog data, or shipping calculation logic.

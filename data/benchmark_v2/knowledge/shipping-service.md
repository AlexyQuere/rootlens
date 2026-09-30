# Shipping Service

The Shipping service calculates delivery quotes and participates in the checkout workflow before payment is completed.

Checkout asks Shipping for the cost of delivering the current cart. A shipping failure may cause order placement to fail even when Cart, Currency, Product Catalog, and Payment are healthy.

When investigating a Shipping problem, determine whether the request reached the Shipping service. A client-side gRPC error without a corresponding Shipping server span can indicate a transport, resolution, or connectivity problem rather than faulty shipping business logic.

Relevant evidence includes:

- Shipping client and server spans;
- the gRPC method name for the quote request;
- `rpc.response.status_code`;
- Shipping logs correlated by trace ID;
- request latency and error rate;
- upstream Checkout behavior.

Do not confuse shipping latency with end-to-end checkout latency. The parent Checkout span includes time spent in multiple dependencies and orchestration work.

If the Shipping call completes successfully before a later Payment failure, Shipping should usually be treated as evidence of a healthy earlier dependency rather than as the root cause.

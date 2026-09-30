# Cart Service

The Cart service stores and retrieves the products currently selected by a user. Checkout depends on Cart early in the order-placement workflow.

A cart failure can prevent checkout before payment or shipping is attempted. For this reason, the position of the Cart call in a distributed trace matters when diagnosing a failed order.

Typical Cart operations include retrieving a cart, adding an item, and emptying the cart after a successful order. If Checkout cannot retrieve the cart, later dependencies may never be called.

Investigators should distinguish:

- an empty but valid cart;
- a Cart RPC error;
- a slow Cart response;
- a connectivity problem before the Cart server receives the request.

Useful evidence includes Cart client/server spans, gRPC status codes, Cart logs correlated by trace ID, and Cart latency metrics.

A healthy PaymentService cannot compensate for a Cart failure that happens earlier in the checkout path. Conversely, an error elsewhere in the same trace does not make Cart causal unless it explains the failed request path.

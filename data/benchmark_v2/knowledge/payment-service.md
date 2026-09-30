# Payment Service

PaymentService is responsible for charging a customer as part of checkout. The main RPC used by Checkout is `oteldemo.PaymentService/Charge`.

A successful payment request reaches the Payment service, executes the charge logic, and returns a successful gRPC status to the caller. A payment-related checkout failure can occur at several different layers, so investigators should distinguish them carefully.

Examples include:

1. The Checkout client cannot resolve or connect to PaymentService.
2. The RPC reaches PaymentService but fails before charge processing completes.
3. PaymentService executes normally but rejects or cannot process the charge.
4. PaymentService is healthy, but Checkout mishandles the returned result.

The presence of a failing Checkout → Payment client span does not prove that PaymentService processed the request. If the client span reports a connectivity-oriented status such as `UNAVAILABLE` and no matching Payment server span exists, the failure may have happened before the request arrived at PaymentService.

When the server span exists, inspect Payment logs and span attributes for the application-level mechanism.

Useful evidence includes:

- `oteldemo.PaymentService/Charge`;
- client and server span pairing;
- `rpc.response.status_code`;
- trace IDs shared between Checkout and Payment logs;
- Payment request rate, error rate, and latency.

PaymentService should not be blamed solely because a failing trace contains the word "payment"; the causal path must be verified.

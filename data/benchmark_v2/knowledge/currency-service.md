# Currency Service

The Currency service converts monetary values between currencies used by the storefront and downstream checkout operations.

Checkout or the frontend may request currency conversion during an order. Currency failures can affect displayed prices or prevent an order from completing, depending on where the failure occurs.

Useful investigation evidence includes:

- Currency client/server spans;
- requested source and destination currencies;
- gRPC status codes;
- Currency service logs;
- request latency and error-rate metrics.

A successful Currency span on a failing checkout trace is useful negative evidence: it helps rule out currency conversion as the causal step for that request.

Currency issues should be separated from Payment issues. Currency transforms values; Payment performs the charge. Similar monetary vocabulary in logs does not imply the same service responsibility.

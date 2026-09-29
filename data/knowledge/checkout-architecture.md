# Checkout Architecture

The Checkout service exposes the `PlaceOrder` operation.

A checkout request coordinates several downstream services.

Checkout retrieves the customer's cart, obtains product information,
performs currency conversion when necessary, requests a shipping quote,
and finally calls PaymentService to charge the customer.

Most downstream communication uses gRPC.

A failure in a downstream dependency may cause the Checkout operation
to fail even if the Checkout service itself remains available.

Distributed traces can be used to determine which downstream call
failed during a particular checkout request.
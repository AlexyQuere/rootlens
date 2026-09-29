# Checkout Payment Flow

This document describes the normal business sequence between Checkout and Payment.

A simplified successful order flow is:

```text
Frontend
→ Checkout
→ Cart
→ Product Catalog
→ Currency
→ Shipping
→ Payment
→ Checkout response
→ Frontend response
```

Checkout invokes `oteldemo.PaymentService/Charge` after it has enough information to calculate the final amount.

On a successful request:

1. Checkout receives the order request.
2. Earlier dependencies complete successfully.
3. Checkout calls PaymentService.
4. PaymentService processes the charge.
5. Checkout completes the order and returns success.

This document is useful for understanding expected control flow and dependency ordering.

It is not a troubleshooting guide. It does not enumerate network-resolution failure modes, retry policy, or detailed gRPC error interpretation.

Because it contains terms such as Checkout, PaymentService, `Charge`, frontend, shipping, and order, it can act as a hard negative for questions that require a specific troubleshooting or observability explanation rather than a description of the normal business workflow.

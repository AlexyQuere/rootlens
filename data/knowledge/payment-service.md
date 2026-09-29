# Payment Service

PaymentService is responsible for charging customers during checkout.

Checkout calls the `PaymentService/Charge` gRPC operation after the
order information and shipping cost have been prepared.

Payment failures can prevent an order from being completed.

When diagnosing payment problems, investigators should distinguish
between a request that reaches PaymentService and fails during payment
processing, and a request that fails before the Payment service
receives it.
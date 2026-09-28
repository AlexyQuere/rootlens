# Observability Basics

## Trace

A trace represents the complete execution path of one request across a distributed system.

In the trace observed in Jaeger, a `POST` request enters the system through `frontend-web` and then propagates through several services involved in the checkout workflow.

The trace shown has:

- a total duration of about **142 ms**;
- **12 services** involved;
- **55 spans**;
- a maximum depth of **15**.

The request starts in the frontend and eventually triggers operations in services such as:

- `checkout`;
- `cart`;
- `product-catalog`;
- `currency`;
- `shipping`;
- `payment`;
- `flagd`.

The trace therefore gives a global view of how a single user request propagates through the application.

A trace is especially useful in a distributed system because the visible symptom may occur in one service while the actual problem originates in another service further downstream.

---

## Span

A span represents one individual operation performed during a trace.

A trace is therefore composed of multiple spans connected together.

For example, in the checkout trace, different spans correspond to operations such as:

- receiving the HTTP `POST` request in the frontend;
- calling `CheckoutService.PlaceOrder`;
- retrieving the shopping cart;
- retrieving product information;
- converting currencies;
- requesting a shipping quote;
- calling the payment service;
- charging the payment.

Each span has its own duration.

For example, in this trace, some operations take only a few microseconds or milliseconds, while the `payment` operation takes significantly longer than many of the other child operations.

This does not automatically mean that `payment` is a problem: the duration must be compared with normal behaviour and interpreted in the context of the complete trace.

---

## Trace ID vs Span ID

Every trace has a unique **Trace ID**.

All spans belonging to the same distributed request share this Trace ID.

Each individual span also has its own unique **Span ID**.

Conceptually:

```text
Trace ID: ABC123

Frontend span
    Span ID: 1

Checkout span
    Span ID: 2

Payment span
    Span ID: 3
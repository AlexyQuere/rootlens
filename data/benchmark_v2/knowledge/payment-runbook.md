# Payment Runbook

Use this runbook when a checkout investigation points toward the Payment dependency.

First determine whether the request actually reached PaymentService.

## Client span exists, server span missing

This pattern suggests failure before PaymentService handled the request.

Investigate:

- service name and endpoint configuration;
- name resolution;
- service discovery;
- network connectivity;
- gRPC status and status description.

`UNAVAILABLE` with resolver-oriented diagnostics is especially relevant to this branch.

## Payment server span exists

If the server span exists, inspect PaymentService itself.

Check:

- Payment application logs;
- gRPC server status;
- charge-processing errors;
- latency;
- downstream calls made by PaymentService.

## Distinguish symptom from cause

A frontend HTTP 500 or Checkout `INTERNAL` status may be a propagated symptom rather than the original payment failure.

Likewise, a Payment-related error elsewhere in telemetry is not causal unless it belongs to the failing request path.

A useful final report should state whether the failure occurred:

```text
before PaymentService
inside PaymentService
after PaymentService returned
```

and cite the trace and logs supporting that conclusion.

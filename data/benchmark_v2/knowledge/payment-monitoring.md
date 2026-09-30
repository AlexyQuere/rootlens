# Payment Monitoring

Payment monitoring focuses on the operational health of PaymentService over time.

Recommended dashboards include:

- request rate for `PaymentService/Charge`;
- error rate by gRPC status;
- p50, p95, and p99 latency;
- process CPU and memory;
- restart count;
- availability over the selected interval.

Alerts should distinguish sustained degradation from isolated failures. A short burst of `UNAVAILABLE` responses may require different handling from a prolonged error-rate increase.

Payment monitoring is useful for answering questions such as:

- Is PaymentService broadly unhealthy?
- Did latency change during the incident window?
- Are failures concentrated in one status code?
- Is the service receiving traffic at all?

Monitoring does not by itself determine whether an individual Checkout request reached PaymentService. For request-level diagnosis, inspect the distributed trace and look for corresponding Payment server spans.

This document intentionally contains vocabulary such as Payment, Checkout, `Charge`, latency, and error rate. It is therefore lexically similar to payment troubleshooting material, but its purpose is dashboard and alert design rather than diagnosing a specific request path.

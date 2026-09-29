# Frontend Service

The Frontend service exposes the user-facing application and translates browser interactions into backend requests.

During checkout, the browser may call an endpoint such as `/api/checkout`. The Frontend then invokes backend services, including Checkout.

A browser-visible HTTP 500 establishes that the user request failed, but it does not identify the backend root cause. Investigators should correlate the failing frontend request with the distributed trace and downstream service spans.

Useful frontend evidence includes:

- HTTP route and status code;
- frontend logs such as checkout failure messages;
- the trace ID associated with the request;
- timing of the request;
- the downstream Checkout span.

A Frontend error can be a symptom of a deeper backend failure. For example, a Checkout RPC may return an error to Frontend after a dependency failure. In that case, the frontend HTTP 500 is evidence of impact, not necessarily the underlying cause.

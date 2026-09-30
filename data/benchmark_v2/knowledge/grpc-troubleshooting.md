# gRPC Troubleshooting

gRPC status codes describe the outcome observed by an RPC caller. They should be interpreted together with traces, logs, and service topology.

`UNAVAILABLE` usually indicates that the service is currently unavailable at the transport or connectivity level. Possible causes include:

- unreachable endpoint;
- connection failure;
- name-resolution failure;
- unavailable service instance;
- transient network failure.

`DEADLINE_EXCEEDED` means that the operation did not complete before the caller's deadline. The underlying cause may be a slow downstream service, network delay, queueing, retries, or an unrealistically short timeout.

`INTERNAL` is broader. It can represent an internal application failure or an upstream service translating a lower-level dependency failure into a generic error.

When a client span fails, check whether a corresponding server span exists. If no server span exists, the failure may have occurred before the downstream application processed the request.

Useful span fields include:

- RPC service and method;
- `rpc.response.status_code`;
- span status;
- status description;
- client/server span relationship;
- trace ID.

Do not diagnose root cause from the status code alone. The same code can result from several mechanisms.

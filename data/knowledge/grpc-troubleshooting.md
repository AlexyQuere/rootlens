# gRPC Troubleshooting

The gRPC status `UNAVAILABLE` indicates that a service is currently
unable to process the request at the transport or connectivity level.

Possible causes include an unreachable service endpoint, connection
failure, DNS or name-resolution problems, temporary network failure,
or a service that is not running.

A client-side span with `UNAVAILABLE` does not necessarily mean that
the downstream application processed the request.

If no corresponding server span exists, the failure may have occurred
before the request reached the downstream service.
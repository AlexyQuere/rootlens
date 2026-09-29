# Service Discovery

Distributed applications need a mechanism for locating service
instances.

A client usually starts from a service name or endpoint configuration
and resolves it into one or more usable network addresses.

Failures during service discovery or name resolution can prevent a
client from establishing a connection to a downstream service.

Typical causes include invalid service names, incorrect endpoint
configuration, DNS failures, or unavailable service instances.
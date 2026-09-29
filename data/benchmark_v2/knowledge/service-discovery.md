# Service Discovery

Distributed applications need a mechanism for locating service instances.

A client often begins with a logical service name or configured endpoint and resolves it into one or more usable network addresses. The resulting addresses are then used to establish a connection to the downstream service.

Service discovery failures can occur because of:

- an invalid service name;
- incorrect endpoint configuration;
- failed DNS or name resolution;
- no available service instances;
- stale or incomplete discovery data.

A discovery failure can prevent an RPC from reaching the downstream application at all. In traces, this may appear as a failing client span with no corresponding server span.

Messages such as "name resolver error", "produced zero addresses", or equivalent resolver diagnostics strongly suggest that the client could not obtain a usable destination.

Service discovery is related to, but distinct from, DNS. DNS can be one mechanism used during resolution, while service discovery is the broader process of finding a reachable service instance.

For incident investigation, compare the client-side error with service endpoint configuration, DNS behavior, and the presence or absence of a downstream server span.

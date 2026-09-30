# Product Catalog Service

The Product Catalog service provides product metadata used by the frontend, Cart, and checkout-related workflows.

Typical information includes product identifiers, names, descriptions, and prices. A checkout request may query Product Catalog before later calls such as Shipping and Payment.

Product Catalog failures can appear as missing product data, RPC errors, or increased latency. Investigators should inspect the relevant client/server spans and determine whether the failure happens before or after the catalog lookup.

Useful evidence includes:

- product identifiers in span attributes or logs;
- Product Catalog server spans;
- gRPC status;
- Product Catalog error and latency metrics;
- the ordering of catalog calls within the distributed trace.

Product Catalog is a common hard negative for broad checkout queries because it appears in many checkout traces. Its presence on the request path does not make it causal.

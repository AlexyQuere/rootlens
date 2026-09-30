# DNS Troubleshooting

DNS translates host names into network addresses and may participate in service discovery for distributed applications.

Common DNS-related failure modes include:

- nonexistent or misspelled host names;
- temporary resolver failures;
- stale cached records;
- incorrect search domains;
- network access problems to the resolver;
- records that resolve to unreachable addresses.

DNS evidence should be separated from generic service-discovery evidence. A name-resolution error can originate in DNS, but some service discovery mechanisms do not use DNS directly.

During investigation, compare:

- the configured service name;
- resolver error messages;
- actual DNS lookup results;
- container or host search-domain configuration;
- whether other clients can resolve the same name;
- whether a server span exists downstream.

If an RPC client reports that resolution produced no addresses, DNS is one hypothesis, not an automatic conclusion. Endpoint configuration or discovery state can produce a similar symptom.

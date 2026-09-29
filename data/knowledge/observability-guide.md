# Observability Guide

Metrics, traces and logs provide complementary views of a distributed
system.

Metrics are useful for detecting and quantifying changes in system
behaviour such as error-rate increases, traffic changes and latency
degradation.

Distributed traces reconstruct the path followed by an individual
request and help localize failures across service boundaries.

Structured logs provide detailed events produced during execution.

Trace IDs allow logs emitted by different services to be correlated
with the same distributed request.
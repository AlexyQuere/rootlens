# Latency Troubleshooting

High end-to-end latency can result from a slow service, retries, queueing, network delay, resource saturation, or several moderate delays on the critical path.

Start with latency metrics such as p50, p95, and p99. A percentile increase shows that the latency distribution changed but does not identify the responsible operation.

Then inspect representative traces.

Important rules:

- parent span duration includes child execution time;
- parallel spans can overlap;
- summing all span durations overestimates request latency;
- the longest span is not automatically the root cause;
- retries can create repeated spans and extend total latency.

Compare failing or slow traces against a healthy baseline.

Check whether latency is concentrated in:

- one downstream RPC;
- repeated retry attempts;
- a gap between operations;
- internal processing;
- several dependencies on the critical path.

`DEADLINE_EXCEEDED` indicates that the request exceeded a deadline, not why. The underlying latency mechanism still requires evidence.

For RootLens, latency conclusions should identify the operation contributing to the critical path and cite the relevant spans and metrics.

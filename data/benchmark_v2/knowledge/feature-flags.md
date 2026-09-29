# Feature Flags

Feature flags allow behavior to be enabled, disabled, or modified without rebuilding the entire application.

In an observability demo or test environment, feature flags may intentionally inject faults such as latency, service failures, or unreachable dependencies. In production systems, flags can also control product behavior, rollout percentage, and experiments.

Feature flag evidence is highly informative only when the investigator is allowed to inspect flag state. A benchmark intended to test blind root-cause analysis should avoid exposing the injected fault name directly to the investigator.

Useful evidence includes:

- flag evaluation results;
- service and environment targeted by the flag;
- activation time;
- rollout scope;
- configuration changes.

A flag-related error appearing elsewhere in telemetry is not automatically causal for the user-facing incident. It must be connected to the failing request path and observed symptom.

For RootLens evaluation, ground-truth fault configuration should be kept separate from the operational knowledge available to the retriever.

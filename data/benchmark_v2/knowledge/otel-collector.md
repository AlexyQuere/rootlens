# OpenTelemetry Collector

The OpenTelemetry Collector receives, processes, and exports telemetry.

Applications can emit traces, metrics, and logs using OpenTelemetry protocols. The Collector can then route those signals to backends such as tracing, metrics, and logging systems.

A typical flow is:

```text
application services
→ OpenTelemetry Collector
→ telemetry backends
```

The Collector can use receivers, processors, exporters, and pipelines.

In some environments, Prometheus may receive metrics through an OTLP ingestion path rather than by scraping application targets directly. In that configuration, an empty Prometheus Targets page does not necessarily mean that no metrics are being collected.

Collector failures can affect observability without directly causing the user-facing business incident. For example, missing traces may be a telemetry problem while checkout itself remains healthy.

Investigators should therefore distinguish:

- application failure;
- telemetry collection failure;
- backend visualization failure.

Useful evidence includes Collector logs, pipeline configuration, exporter status, and whether telemetry from multiple services disappears at the same time.

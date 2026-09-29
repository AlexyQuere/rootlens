# RootLens Retrieval Benchmark v2 — Knowledge Corpus Manifest

## Purpose

This corpus is designed for retrieval evaluation before RAG generation.

It contains 24 operational documents with deliberate vocabulary overlap, semantic paraphrases, document-length variation, and hard negatives.

## Design Goals

- Preserve exact technical identifiers for lexical retrieval tests.
- Include semantic paraphrases for dense retrieval tests.
- Include multi-document evidence paths.
- Include hard negatives that share vocabulary but answer a different intent.
- Separate knowledge from future evaluation qrels.
- Avoid embedding benchmark ground-truth labels inside the corpus.

## Documents

### Application architecture
- checkout-architecture.md
- payment-service.md
- cart-service.md
- shipping-service.md
- currency-service.md
- product-catalog-service.md
- frontend-service.md

### Distributed systems / infrastructure
- service-discovery.md
- grpc-troubleshooting.md
- timeout-and-retry-guidance.md
- dns-troubleshooting.md
- feature-flags.md

### Observability
- observability-guide.md
- metrics-guide.md
- distributed-tracing-guide.md
- structured-logging-guide.md
- telemetry-correlation.md
- otel-collector.md

### Incident response and runbooks
- incident-response-guide.md
- checkout-runbook.md
- payment-runbook.md
- latency-troubleshooting.md

### Hard negatives
- payment-monitoring.md
- checkout-payment-flow.md

## Intended Next Step

Create:
- 24 DEV queries
- 16 TEST queries
- graded relevance judgments: 0 / 1 / 2

The TEST set should be frozen and not used for architecture tuning.

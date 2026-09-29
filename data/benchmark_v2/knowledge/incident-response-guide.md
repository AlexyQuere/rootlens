# Incident Response Guide

Root-cause analysis should separate observations, interpretations, hypotheses, and conclusions.

An observation is directly supported by evidence:

```text
Checkout error rate increased from the healthy baseline.
```

An interpretation summarizes what the observation means:

```text
The incident affects order placement.
```

A hypothesis proposes a possible mechanism:

```text
A downstream dependency may be unavailable.
```

A conclusion should be supported by multiple consistent pieces of evidence.

A practical investigation workflow is:

1. Define the user-visible symptom.
2. Quantify the incident with metrics.
3. Identify representative failing traces.
4. Locate the first meaningful failure on the request path.
5. Correlate logs and configuration.
6. Generate competing hypotheses.
7. Reject hypotheses contradicted by evidence.
8. State the best-supported root cause or abstain if evidence is insufficient.

An error should not automatically be considered the root cause. Investigators should verify that it lies on the failing request path and explains the symptom.

RootLens should follow the discipline:

```text
claim → evidence → source
```

Unsupported certainty is worse than an explicit abstention.

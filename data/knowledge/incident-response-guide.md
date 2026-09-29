# Incident Response Guide

Root-cause analysis should separate observations, interpretations,
hypotheses and conclusions.

An investigation can begin by measuring the affected service and
identifying the dominant symptom.

Failing distributed traces can then be used to narrow the investigation
to a specific service or dependency.

Logs and configuration data can provide additional evidence.

An error should not automatically be considered the root cause.
Investigators should verify that the error lies on the failing request
path and explains the observed symptom.

Hypotheses should be supported or rejected using explicit evidence.s
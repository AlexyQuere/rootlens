# ADR 001 — Use OpenTelemetry Demo as the Initial Experimental Environment

- **Status:** Accepted
- **Date:** 2026-09-29
- **Decision owners:** RootLens project
- **Related milestone:** Milestone 0 — Observable incident investigation environment

---

## 1. Context

RootLens aims to investigate incidents in distributed systems by combining operational evidence such as:

- metrics;
- distributed traces;
- structured logs;
- service dependencies;
- technical documentation;
- runbooks;
- historical incidents;
- source code and configuration.

Before building any retrieval, RAG, agentic, or multi-agent capability, the project needs a realistic environment in which incidents can be observed and investigated manually.

The environment must allow us to study the actual workflow that RootLens will later automate:

```text
User-visible symptom
        ↓
Metrics anomaly
        ↓
Failing request / trace
        ↓
Failing span or dependency
        ↓
Relevant logs and configuration
        ↓
Hypothesis evaluation
        ↓
Root cause
```

The first experimental environment therefore needs to provide:

1. a distributed microservice architecture;
2. metrics, traces, and logs;
3. reproducible incidents;
4. known ground truth for evaluation;
5. local execution;
6. low or zero infrastructure cost;
7. enough realism to expose non-trivial investigation paths;
8. an environment that does not itself become the main engineering project.

---

## 2. Decision

RootLens will use the **OpenTelemetry Demo** as its initial distributed-system experimental environment.

The demo will be run locally with Docker.

RootLens will initially interact with the observability stack through:

```text
Application        → http://localhost:8080
Feature flags      → http://localhost:8080/feature
Jaeger             → http://localhost:16686
Prometheus         → http://localhost:9090
Grafana            → http://localhost:3000
```

The OpenTelemetry Demo is kept **outside the RootLens repository**.

The RootLens repository contains only the investigation logic, tools, evaluation assets, documentation, and AI components developed specifically for this project.

The demo is therefore treated as an external experimental system rather than as part of RootLens itself.

---

## 3. Why This Decision Was Made

### 3.1 It provides a realistic distributed architecture

The OpenTelemetry Demo contains multiple services and realistic cross-service dependencies.

A single checkout request can involve services such as:

- frontend;
- checkout;
- cart;
- product catalog;
- currency;
- shipping;
- payment.

This is significantly more useful for root-cause analysis than a single-process toy application.

It allows RootLens to reason about questions such as:

```text
Which service is failing?

Is the observed error local or downstream?

Did the request reach the downstream service?

Which dependency lies on the failing execution path?

Are unrelated errors present elsewhere in the system?
```

---

### 3.2 It exposes the three core observability signals

The demo provides:

```text
Metrics
Traces
Logs
```

This is essential because RootLens is intended to correlate multiple evidence sources rather than operate on a single telemetry stream.

The first manual investigation already demonstrated the complementary role of each signal:

```text
Metrics
→ detected and quantified degradation

Traces
→ localized the failure

Logs
→ reconstructed and corroborated events
```

---

### 3.3 It supports reproducible fault injection

The demo exposes feature flags that can intentionally introduce failures.

For example, the first calibration incident used:

```text
paymentUnreachable
```

This produced a reproducible checkout failure.

Reproducible incidents are essential because RootLens must eventually be evaluated against known ground truth rather than only judged qualitatively.

---

### 3.4 It provides known ground truth

For injected incidents, the real fault is known independently of RootLens.

This allows us to separate:

```text
information available to the investigator
```

from:

```text
hidden evaluation ground truth
```

This is necessary for future benchmark design.

Without known ground truth, a plausible-looking AI explanation could be mistaken for a correct root-cause analysis.

---

### 3.5 It can run locally

The environment runs locally through Docker.

This provides several advantages:

- no mandatory cloud account;
- no cloud infrastructure cost;
- reproducible setup;
- fast experimentation;
- full access to telemetry;
- easier debugging;
- no dependency on proprietary observability platforms.

This aligns with the RootLens principle of being **local-first and provider-agnostic** where practical.

---

### 3.6 It prevents premature infrastructure work

An alternative would be to build a custom microservice platform specifically for RootLens.

That would require substantial work on:

- service design;
- networking;
- deployment;
- telemetry instrumentation;
- synthetic traffic;
- failure injection;
- observability configuration.

Most of this work would not directly improve the core research and engineering questions of RootLens:

- retrieval;
- evidence gathering;
- tool use;
- hypothesis generation;
- hypothesis testing;
- causal reasoning;
- investigation orchestration;
- evaluation.

Using an existing observable distributed system allows the project to focus on the Applied AI problem.

---

## 4. Experimental Architecture

The initial environment can be represented as:

```text
                    OpenTelemetry Demo
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
       Metrics            Traces             Logs
          │                 │                 │
          ▼                 ▼                 ▼
     Prometheus           Jaeger          OpenSearch
                                                 │
                                                 ▼
                                              Grafana
```

RootLens will later interact with these systems through deterministic tools such as:

```text
get_request_rate()
get_error_rate()
get_latency_percentile()

find_failing_traces()
get_trace()
find_error_spans()

get_logs_by_trace_id()
get_logs_by_span_id()

get_service_dependencies()
```

The LLM or investigation engine should not initially need to construct raw observability queries for every action.

---

## 5. Current Validation

The environment has already been validated through a first manual incident investigation.

### Calibration incident

Injected fault:

```text
paymentUnreachable
```

Observed user symptom:

```text
POST /api/checkout
→ HTTP 500
```

Metrics showed:

```text
Traffic:
~0.046 req/s healthy
~0.051 req/s during incident

Error rate:
0% healthy
~63.7% during incident
```

Distributed tracing localized the failure to:

```text
Checkout
 ↓
PaymentService.Charge
```

The failing client span reported:

```text
rpc.response.status_code = UNAVAILABLE

otel.status_description =
"name resolver error: produced zero addresses"
```

Correlated logs confirmed that earlier services in the checkout path were still functioning.

The investigation therefore reconstructed the causal chain:

```text
Invalid / unresolvable PaymentService destination
                  ↓
Checkout gRPC resolver finds zero addresses
                  ↓
PaymentService.Charge returns UNAVAILABLE
                  ↓
CheckoutService.PlaceOrder returns INTERNAL
                  ↓
Frontend /api/checkout returns HTTP 500
                  ↓
User cannot place the order
```

This successful investigation demonstrates that the environment is suitable for RootLens development.

---

## 6. Alternatives Considered

### Alternative A — Build a custom microservice system

#### Description

Create a purpose-built distributed application for RootLens with custom services, telemetry, traffic generation, and fault injection.

#### Advantages

- complete control over the architecture;
- faults can be designed specifically for evaluation;
- easier to create highly targeted benchmark cases;
- no dependency on an external demo project.

#### Disadvantages

- high initial engineering cost;
- substantial work unrelated to the core Applied AI objective;
- risk of spending more time building infrastructure than RootLens;
- custom faults may initially be less realistic than faults in a mature demo.

#### Decision

**Rejected for the initial phase.**

A custom environment may be introduced later if the OpenTelemetry Demo becomes too limiting.

---

### Alternative B — Use static incident datasets only

#### Description

Use pre-recorded logs, metrics, traces, or public incident datasets without running a live distributed system.

#### Advantages

- simple setup;
- deterministic data;
- easy experiment reproducibility;
- potentially easier benchmark automation.

#### Disadvantages

- no interactive investigation;
- no active tool use;
- difficult to test dynamic evidence acquisition;
- limited ability to test agent decisions about what data to request next;
- less representative of a forward-deployed investigation workflow.

#### Decision

**Rejected as the primary environment.**

Static datasets may later complement the live environment for benchmark coverage.

---

### Alternative C — Use a commercial observability platform

Examples could include hosted observability products exposing logs, traces, metrics, and incident workflows.

#### Advantages

- realistic production-style interfaces;
- mature telemetry capabilities;
- potentially realistic integrations and APIs.

#### Disadvantages

- possible cost;
- external account dependency;
- vendor lock-in;
- reduced reproducibility;
- unnecessary complexity at the beginning of the project;
- harder to guarantee that all future contributors can reproduce experiments.

#### Decision

**Rejected for the initial phase.**

RootLens should remain observability-backend agnostic wherever possible.

---

### Alternative D — Use only one telemetry source

For example:

```text
logs only
```

or:

```text
traces only
```

#### Advantages

- simpler system;
- fewer integrations;
- easier implementation.

#### Disadvantages

The first incident already demonstrated that different signals answer different questions:

```text
Metrics → Is something abnormal?

Traces → Where is the request failing?

Logs → What happened during the execution?
```

Reducing the environment to a single signal would remove a central RootLens research problem: multi-source evidence correlation.

#### Decision

**Rejected.**

---

## 7. Consequences

### Positive consequences

Using the OpenTelemetry Demo provides:

- a realistic microservice topology;
- real distributed traces;
- structured logs;
- time-series metrics;
- fault injection;
- reproducible incidents;
- known ground truth;
- local execution;
- zero mandatory cloud cost;
- fast iteration.

It also allows the project to start with manual reasoning before introducing AI.

This supports the development philosophy:

```text
understand
    ↓
build baseline
    ↓
measure
    ↓
add complexity only when justified
```

---

### Negative consequences

The OpenTelemetry Demo is still a synthetic environment.

Its incidents may be:

- simpler than real production incidents;
- more isolated;
- more deterministic;
- easier to diagnose;
- less noisy than incidents in large production systems.

Feature-flag faults may also expose patterns that become too easy to learn if benchmark design is careless.

Therefore, success on the demo alone will not demonstrate production-level RCA capability.

---

## 8. Risks

### Risk 1 — Benchmark leakage

If RootLens can access documentation describing the injected feature flag, it may retrieve the answer rather than investigate the incident.

For example, exposing a document containing:

```text
paymentUnreachable makes Checkout use an invalid Payment address
```

would make an evaluation of the same incident invalid.

### Mitigation

Strictly separate:

```text
data/knowledge/
```

from:

```text
data/evaluation/
```

Ground truth must not be included in the knowledge accessible to RootLens during blind evaluation.

---

### Risk 2 — Overfitting to OpenTelemetry Demo

RootLens could learn assumptions specific to:

- service names;
- telemetry schemas;
- feature flags;
- demo topology;
- known fault patterns.

### Mitigation

Tool APIs should expose generic concepts such as:

```text
service
operation
dependency
error
latency
trace
log
```

rather than hard-coding demo-specific behaviour.

Later milestones should introduce:

- additional fault types;
- custom incidents;
- alternative datasets;
- possibly a second distributed environment.

---

### Risk 3 — Treating injected incidents as representative of production

Feature-flag failures may be cleaner than real incidents involving:

- multiple simultaneous failures;
- partial degradation;
- noisy telemetry;
- configuration drift;
- slow resource exhaustion;
- cascading failures;
- incomplete instrumentation.

### Mitigation

The demo will be considered the **initial training and calibration environment**, not the final validation environment.

---

## 9. Design Constraints Derived from This Decision

The following constraints apply to RootLens development.

### 9.1 RootLens must remain environment-agnostic

The internal investigation logic should not depend directly on the OpenTelemetry Demo implementation.

The demo is one data source, not the RootLens architecture.

---

### 9.2 Telemetry access should be wrapped in deterministic tools

Instead of relying on an LLM to repeatedly generate raw queries, RootLens should progressively expose stable functions such as:

```text
get_error_rate(service, operation, window)

get_latency_percentile(service, operation, percentile, window)

find_failing_traces(service, operation, window)

get_trace(trace_id)

get_logs_by_trace_id(trace_id)
```

This makes behaviour easier to:

- test;
- evaluate;
- reproduce;
- compare;
- debug.

---

### 9.3 Ground truth must remain outside the investigator context

The fault selected for an evaluation must be stored separately from the information available to RootLens.

This is required for credible evaluation.

---

### 9.4 Manual investigations should precede automation

Before RootLens automates a new investigation pattern, at least one manual example should be understood well enough to specify:

- useful observations;
- relevant tools;
- plausible hypotheses;
- causal evidence;
- stopping conditions.

The first `paymentUnreachable` incident serves as the initial example.

---

## 10. What This ADR Does Not Decide

This ADR does **not** yet decide:

- which LLM provider RootLens will use;
- whether the final system will be single-agent or multi-agent;
- which vector database will be used;
- which embedding model will be used;
- whether LangGraph will be used;
- how hypotheses will be scored;
- how confidence will be represented;
- how code and Git history will be integrated;
- which production observability systems will eventually be supported.

Those decisions will be made later and should each be justified independently.

---

## 11. Revisit Criteria

This decision should be revisited if one or more of the following becomes true:

1. the OpenTelemetry Demo no longer provides incidents complex enough to differentiate RootLens approaches;
2. RootLens begins overfitting to demo-specific service names or fault patterns;
3. evaluation requires failure modes that cannot be represented through the demo;
4. a second environment is required to demonstrate generalization;
5. realistic multi-fault or long-running incidents become necessary;
6. production-style telemetry schemas need to be tested;
7. the demo becomes an obstacle to reproducible automated benchmarking.

At that point, likely options include:

- extending the OpenTelemetry Demo;
- creating custom faults;
- adding static benchmark datasets;
- introducing a second distributed application;
- building a dedicated RootLens benchmark environment.

---

## 12. Final Decision Summary

RootLens will use the OpenTelemetry Demo as its **initial experimental distributed system** because it provides:

```text
distributed architecture
        +
metrics
        +
traces
        +
logs
        +
fault injection
        +
known ground truth
        +
local reproducibility
```

while allowing the project to focus engineering effort on the core RootLens problem:

> acquiring evidence, forming and testing hypotheses, and producing evidence-grounded root-cause analyses.

The OpenTelemetry Demo is therefore accepted as the environment for the first RootLens milestones, with the explicit understanding that future evaluation must expand beyond it.

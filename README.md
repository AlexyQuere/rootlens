# RootLens

**Autonomous AI Incident Investigator for distributed systems**

RootLens is an applied AI / systems project that explores how to build an evidence-grounded incident investigator for distributed systems. The long-term goal is an AI system that can investigate failures by combining live observability data, technical knowledge, historical incidents, code, Git history, service topology, and explicit hypothesis testing.

The project is deliberately built from first principles. Instead of starting with an agent framework, RootLens first establishes reliable retrieval, evidence contracts, evaluation methodology, and deterministic components. The core rule is simple:

> **claim -> evidence -> source**

The system should eventually be able to observe an incident, decide what evidence is missing, call the appropriate tools, retrieve technical knowledge, generate competing hypotheses, reject unsupported alternatives, identify the best-supported root cause, explain its reasoning with evidence, and abstain when the available information is insufficient.

## Current status

**Stages 1-14 and deterministic observability Experiments 015A-015D are complete.**

The current default knowledge pipeline remains:

```text
question
   |
   v
BGE dense retrieval
whole-document indexing
   |
   v
top-5 evidence documents
   |
   v
BasicGroundedRAG
   |
   v
structured claims + explicit sources
```

The live incident path now has deterministic metrics, trace, log, and unified cross-modal evidence:

```text
incident
   |
   +--> Prometheus metrics evidence
   |
   +--> Jaeger / OTLP request-level trace evidence
   |
   +--> OpenSearch request-correlated log evidence
   |
   v
unified typed incident evidence
   |
   v
next: first single custom investigation loop
```

No agent framework has been introduced yet. Agentic orchestration will only be added after the deterministic evidence layer has stable contracts, provenance, controlled evaluations, and explicit failure semantics.

## Why RootLens is not just another RAG chatbot

Most RAG demos optimize retrieval or answer quality in isolation. RootLens treats incident investigation as a systems problem with several distinct failure modes:

- retrieval can miss useful evidence;
- retrieved evidence can be ignored;
- cited evidence can fail to support the claim;
- the answer can be technically incomplete despite good retrieval;
- a model can overclaim when information is missing;
- more complex retrieval can improve candidate recall without improving the final answer;
- LLM-as-a-judge evaluations can themselves be noisy;
- observability data can be incomplete, duplicated, delayed, timestamp-corrupted, or inconsistent across modalities;
- control-plane configuration can diverge from runtime behavior.

The project therefore evaluates each layer separately and then checks whether a subsystem improvement actually produces a task-level gain.

## Project principles

1. **Mechanisms before frameworks.** Core retrieval, evaluation, grounding, and orchestration logic is implemented directly before considering LangChain/LangGraph-style abstractions.
2. **Evidence over eloquence.** A fluent answer is not sufficient. Factual claims need explicit source support.
3. **Abstention is a feature.** The system must distinguish answerable, partially answerable, and unanswerable questions.
4. **DEV and TEST are separated.** Architecture decisions are made on DEV; frozen TEST is reserved for explicit checkpoints.
5. **No ground-truth leakage.** Hidden qrels, benchmark answers, and injected-fault labels are not exposed to the generation model.
6. **Complexity must earn its place.** New retrieval or agentic components stay only if experiments show a meaningful task-level benefit.
7. **Evaluation is multi-layered.** Retrieval metrics, citation metrics, claim-level grounding, abstention, intervention tests, telemetry integrity, per-request evidence, and pairwise answer evaluation are treated as different measurements.
8. **Raw evidence is preserved.** RootLens does not silently repair timestamps, deduplicate records, normalize severity, or convert missing evidence into a causal conclusion.

## Current repository structure

```text
rootlens/
├── data/
│   ├── benchmark_v2/
│   │   ├── knowledge/              # RAG-visible technical corpus
│   │   ├── dev_queries.json        # architecture / tuning queries
│   │   ├── dev_rewrites_v1.json    # frozen semantic rewrites
│   │   └── ...
│   └── evaluation/                 # hidden or derived frozen artifacts
├── docs/
│   └── experiments/                # experiment reports and decisions
├── scripts/                        # smoke tests and reproducible runners
├── src/rootlens/
│   ├── retrieval/                  # sparse, dense, fusion, multi-query
│   ├── rag/                        # evidence-grounded generation pipeline
│   ├── llm/                        # provider abstraction
│   ├── observability/              # Prometheus, Jaeger, OpenSearch evidence/tools
│   └── evaluation/                 # retrieval, RAG, telemetry evaluation
└── tests/                           # deterministic unit tests
```

## Development environment

RootLens is developed locally on macOS / Apple Silicon with Python and a provider-agnostic OpenAI-compatible LLM interface.

Provider configuration is kept outside Git:

```bash
ROOTLENS_LLM_API_KEY=...
ROOTLENS_LLM_BASE_URL=https://<provider>/v1
ROOTLENS_LLM_MODEL=<model>
```

The current experiments use an OpenAI-compatible endpoint and keep `.env` files out of version control. The code depends on the provider interface rather than on one vendor-specific SDK.

Typical test command:

```bash
PYTHONPATH=src python -m pytest tests -q
```

## Observability foundation

The project uses the OpenTelemetry Demo as the distributed-system laboratory. The environment exposes realistic service-to-service traffic, traces, logs, metrics, feature-flag faults, and downstream failure propagation.

The investigation discipline is:

```text
Observation != Interpretation != Hypothesis != Conclusion
```

The current modality split is intentionally empirical rather than absolute:

```text
metrics -> detect and scope system-level changes
traces  -> localize request paths and RPC behavior
logs    -> sometimes expose application-internal mechanism or symptoms
docs    -> provide technical knowledge
code    -> verify implementation behavior
```

A user-visible symptom is not automatically the root cause, a missing downstream span is not automatically proof that a server never executed, and a control-plane configuration value is not automatically proof that the same value was evaluated by the runtime handling a request.

## Retrieval experiments: Stages 2-13

The retrieval stack was built incrementally rather than jumping directly to embeddings.

### Stage 2 - TF-IDF from first principles

Implemented tokenization, term frequency, document frequency, inverse document frequency, vector construction, cosine similarity, deterministic ranking, and a basic retrieval benchmark.

Initial small-corpus result:

| Metric | TF-IDF |
|---|---:|
| Precision@1 | 0.7500 |
| Recall@1 | 0.4375 |
| Recall@3 | 0.8750 |
| MRR@3 | 0.8542 |

### Stage 3 - BM25

Added term-frequency saturation and document-length normalization using the standard BM25 scoring structure (`k1=1.5`, `b=0.75`). BM25 did not materially outperform TF-IDF on the first small corpus, but it provided a stronger sparse baseline and clarified why exact identifiers remain valuable.

### Stage 4 - Dense retrieval

Implemented exact dense retrieval with `BAAI/bge-small-en-v1.5` embeddings, normalized vectors, query instructions, and dot-product / cosine ranking.

On the first benchmark:

| Metric | Dense BGE |
|---|---:|
| Precision@1 | 1.0000 |
| Recall@1 | 0.6875 |
| Recall@3 | 0.9375 |
| MRR@3 | 1.0000 |

### Stage 5 - Benchmark v2 and baseline selection

The benchmark was expanded to **24 documents** and **40 queries**: 24 DEV queries and 16 frozen TEST queries. Queries cover exact identifiers, semantic paraphrases, architecture, troubleshooting, observability, multi-document reasoning, and hard negatives. Relevance uses graded qrels: direct/primary, supporting, or absent.

Metrics include Precision@1, Recall@k, MRR, and nDCG.

DEV comparison:

| Retriever | P@1 | R@3 | R@5 | MRR@3 | nDCG@3 |
|---|---:|---:|---:|---:|---:|
| TF-IDF | 0.6667 | 0.5972 | 0.6840 | 0.7917 | 0.6649 |
| BM25 | 0.7083 | 0.5938 | 0.6979 | 0.8403 | 0.6521 |
| Dense BGE | 0.9167 | **0.7500** | **0.8299** | 0.9583 | **0.8317** |
| Hybrid RRF | **0.9583** | 0.7222 | 0.7604 | **0.9792** | 0.8182 |

Dense BGE was selected because it gave the best evidence coverage and graded ranking quality for the downstream RAG task.

### Stage 6 - Chunking

Compared whole-document retrieval with 64-token / 16-overlap and 128-token / 32-overlap chunking. The corpus documents are short and focused, so chunking fragmented useful context and reduced retrieval quality.

| Unit | R@3 | R@5 | nDCG@3 |
|---|---:|---:|---:|
| Whole document | **0.7500** | **0.8299** | **0.8317** |
| 64 / 16 | 0.6076 | 0.6806 | 0.7314 |
| 128 / 32 | 0.6146 | 0.7431 | 0.7228 |

Decision: keep whole documents.

### Stage 7 - Candidate-depth analysis

Measured how much relevant evidence is available before reranking:

```text
Recall@1  = 0.3507
Recall@3  = 0.7500
Recall@5  = 0.8299
Recall@10 = 0.9236
Recall@20 = 0.9896
```

Top-10 became the standard candidate depth for reranking experiments. This separates **candidate generation** from **final ranking** and establishes an oracle upper bound.

### Stage 8 - MiniLM cross-encoder reranking

Tested a lightweight cross-encoder over dense top-10 candidates. The reranker reduced ranking quality relative to the dense baseline.

| System | R@3 | R@5 | nDCG@3 |
|---|---:|---:|---:|
| Dense | **0.7500** | **0.8299** | **0.8317** |
| MiniLM reranked | 0.6562 | 0.7674 | 0.7725 |

Decision: reject MiniLM reranking.

### Stage 9 - BGE reranker

Tested a stronger BGE cross-encoder reranker. It also regressed the task metrics and added latency.

```text
P@1      0.7500
R@3      0.6840
R@5      0.8021
MRR@3    0.8681
nDCG@3   0.7388
```

Decision: stop reranker tuning until there is evidence that reranking is the bottleneck.

### Stage 10 - Semantic multi-query candidate generation

Generated three frozen semantic rewrites per question. Rewrites are generated without documents, qrels, expected answers, or incident ground truth.

The candidate union improved coverage substantially:

```text
Dense Recall@10                  0.9236
Semantic multi-query union       0.9896
RRF final Recall@10              0.9340
```

Five of six known candidate failures were recovered in the union, but only one of those recovered documents survived the final RRF ranking. This exposed a new bottleneck: evidence was present in the candidate set but not selected into the final context.

### Stage 11 - Multi-query fusion

Compared RRF, MaxSim, and MeanSim fusion. The recovered evidence still failed to consistently survive final ranking.

Lesson: the problem was not a particular RRF constant. Scalar document scores could not reliably represent complementary evidence needs.

### Stage 12 - Set-aware evidence selection

Tested Maximal Marginal Relevance and a greedy query-coverage objective. Neither improved task metrics. Dense retrieval already achieved nearly saturated semantic query coverage at top-5, so semantic diversity was not the missing mechanism.

Decision: stop selector tuning and test whether the query itself needed decomposition into distinct information needs.

### Stage 13 - Query decomposition

Implemented adaptive 1-3 subquery decomposition and compared it with a matched-budget semantic-rewrite control.

Key result: decomposition did not improve candidate recall or final ranking enough to justify its complexity. The generated subqueries were actually **less diverse in embedding space** than semantic rewrites.

Final Dense remained the default baseline.

## Stage 14 - Evidence-grounded RAG

Stage 14 moved the project from retrieval metrics to an end-to-end answer pipeline.

### 14A - BasicGroundedRAG

Pipeline:

```text
question
  -> Dense top-5
  -> evidence context with explicit source IDs
  -> LLM
  -> strict JSON answer
  -> schema and citation validation
```

Answer contract:

```text
status = answered | partial | abstained
claims = [{ text, sources[] }]
limitation = string | null
```

Important design choices:

- strict source IDs;
- no automatic citation repair;
- one schema retry for malformed output;
- no retry for fabricated citations;
- no uncalibrated confidence score;
- every factual claim must cite retrieved evidence.

### 14B - Offline evidence-flow metrics

On 24 DEV answers:

```text
Retrieval qrel recall          0.8299
Citation qrel precision        0.9375
Citation qrel recall           0.6736
Relevant evidence retention    0.8403
Source utilization             0.4167
```

Citation relevance is deliberately not treated as proof of claim support.

### 14C - Claim-level grounding

Grounding was evaluated at the claim level with two independent LLM judges and a targeted human audit.

- 116 claims evaluated;
- both judges labeled 115/116 as fully supported;
- exact cross-judge agreement: 114/116 = 98.28%;
- targeted human audit of disagreements plus high-risk agreements found 10/10 fully supported.

This is reported as a validation exercise, not as a universal grounding-accuracy estimate.

### 14D - Abstention benchmark

Built 18 matched queries in six triplets:

```text
answerable -> partial -> unanswerable
```

Generation was performed without loading hidden gold labels.

Result on this controlled benchmark:

```text
status accuracy           1.0000
balanced accuracy         1.0000
macro-F1                  1.0000
failure-to-abstain rate   0.0000
triplet consistency       1.0000
```

The conclusion is intentionally narrow: the pipeline can distinguish sufficient from insufficient evidence on this controlled benchmark.

### 14E - Retrieval failure attribution

Six known retrieval-gap queries were re-run with qrel-enriched top-5 contexts. Missing qrel evidence was inserted while keeping the context budget fixed.

The intervention increased citation coverage and recovered evidence was usually used, but pairwise inspection showed that all six original Dense answers were already sufficient.

Key lesson:

> **retrieval gap != answer-limiting failure**

### 14F - Dense vs Semantic Multi-Query at answer level

The final retrieval decision compared the simple Dense pipeline against Semantic Multi-Query RRF using the same model, prompt, and top-5 evidence budget.

Deterministic results:

| Metric | Dense | Semantic |
|---|---:|---:|
| Retrieval qrel Recall@5 | **0.8299** | 0.8194 |
| Citation precision | **0.9375** | 0.8785 |
| Citation recall | 0.6736 | **0.6806** |
| Evidence retention | 0.8403 | **0.8472** |
| Retrieval queries/question | **1** | 4 |
| Mean RAG latency | **2087.6 ms** | 2265.6 ms |

Two blinded LLM judges evaluated all 24 answer pairs with reversed A/B ordering. Exact cross-judge agreement was 18/24 (75%), Cohen's kappa was 0.623.

A targeted blind human audit then adjudicated judge disagreements, changed-context consensus wins, and identical-context non-ties.

Final combined adjudication:

```text
All 24:                 Dense 6 | Semantic 6 | Tie 12
Changed context (15):   Dense 4 | Semantic 5 | Tie 6
Same context (9):       Dense 2 | Semantic 1 | Tie 6
```

The identical-context control is important: preferences still appeared when retrieval evidence was identical, showing that generation/evaluation variance is large enough that the one-answer Semantic edge cannot be confidently attributed to retrieval.

**Decision:** keep Dense BGE whole-document top-5 as the default. Retain Semantic Multi-Query as an experimental strategy, not a systematic production path.

## Experiment 015A - Deterministic metrics investigation

RootLens added a direct Prometheus client and typed metric evidence before introducing any agentic behavior.

Core capabilities:

```text
instant query
range query
request rate
error-rate ratio
request count
server latency quantiles
baseline-vs-incident comparison
exact PromQL provenance
```

Selected native metric families are `http_server`, `rpc_server`, and `rpc_client`.

The metrics layer deliberately avoids LLM-generated arbitrary PromQL and root-cause heuristics.

### paymentFailure positive control

During `paymentFailure=100%`, observed Checkout PlaceOrder and Checkout-to-Payment Charge RPCs both reported an error rate of 1.0, while the selected frontend HTTP error-rate metric remained 0. Latency also fell because the failing path returned faster.

Lesson:

> lower latency does not necessarily mean healthier behavior.

### paymentUnreachable ambiguity

During the controlled `paymentUnreachable` run, selected native RPC metrics showed no error signal. This was not interpreted as proof of health or proof that metrics cannot detect the fault. The unresolved question was handed to the trace layer.

## Experiment 015B - Deterministic trace investigation

RootLens now has a direct Jaeger v3 / OTLP trace layer.

Core capabilities:

```text
find traces by service / operation / time
fetch a complete trace
parse immutable span evidence
reconstruct parent/child topology
find error and long spans
pair CLIENT -> SERVER spans
report unmatched clients
compare structural trace paths
diagnose trace integrity
freeze raw OTLP during experiments
```

### Telemetry-integrity finding

Real traces exposed an approximately 18.6-hour timestamp offset in Quote spans inside otherwise short Checkout traces. RootLens does not repair those timestamps. It separates individual span duration, request/root duration, trace temporal envelope, parent/child temporal violations, and root-interval violations.

### paymentFailure request-level result

Frozen controlled result:

```text
baseline:
  client_non_error_server_non_error  19 / 19

incident:
  client_error_server_error          13 / 13
```

The incident reached Payment and was visible as an error on both the Checkout client span and matching Payment server span.

### paymentUnreachable request-level result

Frozen controlled result:

```text
baseline:
  client_non_error_server_non_error  18 / 18

incident:
  client_non_error_server_non_error  12 / 12
```

The trace layer therefore confirmed, rather than contradicted, the metrics ambiguity.

### Missing evidence acquired: runtime feature-flag evaluation

Every measured incident trace contained:

```text
feature_flag.key            = paymentUnreachable
feature_flag.result.value   = False
feature_flag.result.variant = off
feature_flag.result.reason  = cached
```

even while experiment control-plane validation reported the flag as `on`.

This localized the divergence before the Payment RPC:

```text
control-plane configuration = ON
Checkout runtime evaluation = cached OFF
```

### Causal intervention

With the control-plane value still ON, only Checkout was restarted. The next trace showed:

```text
feature_flag.result.value   = True
feature_flag.result.variant = on
feature_flag.result.reason  = static

Checkout -> Payment CLIENT
status  = ERROR
message = "name resolver error: produced zero addresses"

Payment SERVER
not observed
```

This intervention strongly supports stale runtime/provider state in the previous Checkout process while leaving the deeper refresh/invalidation mechanism unresolved.

### Evidence preservation lesson

An earlier attempt to reuse old metrics windows failed because Jaeger no longer retained the individual traces. Controlled trace experiments now freeze both structured observations and raw OTLP `resourceSpans` while the evidence still exists.

Key lesson:

> RootLens should acquire missing evidence and test hypotheses instead of forcing an RCA from the first anomaly.

## Experiment 015C - Deterministic log investigation

RootLens now has a direct OpenSearch log layer with typed evidence, trace correlation, telemetry-integrity diagnostics, and controlled baseline-vs-incident evaluation.

Core capabilities:

```text
search by observation-time window
filter by exact service / trace ID / span ID / raw severity
preserve event and observation timestamps
preserve exact query provenance
report possible duplicate groups
rank event-vs-observation timestamp differences
compare exact log signatures
compare baseline/incident signature prevalence per trace
freeze raw log evidence
```

### Why discovery uses `observedTimestamp`

The first implementation used `@timestamp` for the query window.

For a known post-restart `paymentUnreachable` trace, this returned 38 logs instead of the 44 found without the event-time restriction.

The six missing records were:

```text
shipping  x2
currency  x4
```

and all six had:

```text
@timestamp        = 1970-01-01T00:00:00Z
observedTimestamp = 2026-10-03T13:29:25...
```

RootLens therefore uses `observedTimestamp` as the default discovery field while preserving the original `@timestamp` exactly.

No timestamp is silently repaired.

### Raw severity and duplicate evidence

Real logs exposed heterogeneous raw severities:

```text
INFO
info
Information
<missing>
```

The known post-restart trace also contained four possible duplicate groups in `load-generator`.

RootLens reports these groups but does not silently deduplicate them.

### Per-trace prevalence instead of raw counts

Baseline and incident windows contain different numbers of requests, so raw log counts are not directly comparable.

For each exact signature `s`:

```text
p_B(s) = baseline traces containing s / baseline trace count
p_I(s) = incident traces containing s / incident trace count
delta(s) = p_I(s) - p_B(s)
```

A duplicate signature inside one trace counts once for prevalence while all underlying documents remain preserved.

### paymentFailure positive control

Log coverage:

```text
baseline:
  19 / 19 traces with logs
  689 logs

incident:
  13 / 13 traces with logs
  387 logs
```

Healthy-path signatures present in 19/19 baseline traces and 0/13 incident traces included:

```text
checkout  "payment went through"
checkout  "order placed"
payment   "Transaction complete."
frontend  "Order placed successfully"
email     "Order confirmation email sent"
shipping  "Tracking ID Created"
```

Incident-only signatures present in 13/13 incident traces and 0/19 baseline traces included:

```text
frontend  "Checkout payment declined"
payment   "Payment request failed. Invalid token. demo.user_context.loyalty_level=gold"
```

The trace layer had localized the failure to a request that reached Payment and failed server-side. The logs add a systematic Payment-side failure message indicating an invalid-token mechanism.

### paymentUnreachable stale-runtime negative control

Log coverage:

```text
baseline:
  18 / 18 traces with logs
  737 logs

incident:
  12 / 12 traces with logs
  540 logs
```

No strong systematic Checkout/Payment signature changed between the two windows.

The largest differences were small:

```text
shipping empty-body log:
  2/18 -> 0/12
  delta = -0.111

one-off exact frontend-proxy bodies:
  0/18 -> 1/12
  delta = +0.083
```

This matches the independent feature-flag and trace evidence: the control plane was ON, but the measured Checkout runtime still evaluated the flag as cached OFF and the request path remained normal.

### Post-restart real paymentUnreachable request

For trace:

```text
3541df651cfbedf57cb9dd68ac319682
```

the log artifact contains:

```text
44 / 44 correlated logs
9 services
0 Payment logs
```

and the only raw error-like log is:

```text
frontend:
  "Checkout failed to place order"
```

The trace layer, however, contains the precise mechanism:

```text
Checkout -> Payment CLIENT ERROR
"name resolver error: produced zero addresses"
Payment SERVER not observed
```

Therefore the logs expose the user-facing symptom here, while the trace carries the stronger mechanism evidence.

### 015C conclusion

The key result is:

> **The evidential value of each telemetry modality is failure-dependent.**

Observed examples:

```text
paymentFailure
  metrics -> detect error behavior
  traces  -> localize failure to Payment server-side
  logs    -> add invalid-token mechanism

paymentUnreachable stale-runtime window
  metrics -> no distinct fault signal
  traces  -> runtime requests remain normal
  logs    -> no systematic incident signature

paymentUnreachable real ON request
  traces  -> expose resolver failure before Payment server
  logs    -> expose checkout failure symptom, not resolver mechanism
```

This is why RootLens keeps modality-specific raw evidence rather than collapsing metrics, traces, and logs into one opaque score.

## Experiment 015D - Unified cross-modal incident evidence

Experiment 015D unified metrics, traces, and logs into a typed incident-evidence layer before introducing any investigation agent.

Core capabilities:

```text
typed incident bundle
explicit modality acquisition state
exact trace-ID and span-ID correlation
explicit service / peer metric bindings
service-oriented evidence views
missing-context vs unmatched-context integrity semantics
synchronized metric / trace / log capture
checkpoint / resume for long experiments
controlled cross-modal content validation
```

### Why synchronization mattered

An initial attempt to combine previously frozen metric, trace, and log artifacts was rejected because the artifacts represented different incident runs. RootLens now requires temporal compatibility and uses a synchronized capture protocol instead of treating `same scenario` as `same incident`.

For each phase, Prometheus metrics are evaluated at the analytical window end, Jaeger traces are collected for the same analytical window, and OpenSearch logs are recovered by exact captured trace IDs using `observedTimestamp` for discovery while preserving original event timestamps.

### Typed evidence model

The incident representation preserves modality-specific semantics rather than flattening all evidence into one score.

```text
IncidentEvidenceBundle
  metrics      -> baseline / incident MetricComparisonEvidence
  traces       -> request-level TraceEvidence
  logs         -> exact LogEvidence documents
  acquisitions -> observed / empty / unavailable modality state
```

RPC client metrics use explicit service bindings. A Checkout-to-Payment metric remains a Checkout-emitted client metric while also becoming edge evidence for Payment with a `peer` role. This avoids relabeling edge evidence as an internal Payment metric.

### Cross-modal integrity

The synchronized `paymentFailure` incident produced:

```text
10 metric comparisons
11 incident traces
425 incident logs
10 / 10 metric bindings
425 / 425 logs with matching trace context
425 / 425 logs with matching span context
```

Synthetic tests also verify that these cases remain distinct:

```text
missing trace/span context
!=
trace/span context present but unmatched
```

RootLens therefore does not infer that missing context is equivalent to a failed correlation.

### Synchronized `paymentFailure` positive control

The synchronized positive control showed:

```text
checkout_error_rate          0.0 -> 1.0
checkout_payment_error_rate  0.0 -> 1.0
frontend_http_error_rate     0.0 -> 0.0

11 / 11 Checkout -> Payment CLIENT spans in error
11 / 11 matching Payment SERVER spans in error
11 / 11 traces with Payment invalid-token failure log
```

Request-level correlation joined all three evidence elements on all 11 incident traces. The interpretation remains layered:

```text
metrics -> detect degraded Checkout / Payment RPC behavior
traces  -> show the request reached Payment and failed server-side
logs    -> add the systematic invalid-token mechanism
```

The baseline for this specific synchronized artifact was historically reacquired after a serialization failure. Its exact analytical window was preserved, and the artifact records this provenance explicitly rather than pretending the acquisition happened live.

### Synchronized real-ON `paymentUnreachable`

The controlled real-runtime-ON experiment produced a different evidence shape:

```text
checkout_error_rate          0.0 -> 1.0
checkout_payment_error_rate  0.0 -> 1.0
frontend_http_error_rate     0.0 -> 0.003205

13 / 13 measured traces:
  paymentUnreachable = True / on
  Checkout -> Payment CLIENT observed
  Checkout -> Payment CLIENT ERROR
  error message = "name resolver error: produced zero addresses"

0 / 13 Payment SERVER spans observed
0 Payment logs observed
13 / 13 frontend traces contain "Checkout failed to place order"
```

The runtime manipulation check is evaluated on the measured incident traces themselves, not only on the control plane. All 13 incident requests evaluated `paymentUnreachable=True/on`.

The service-oriented view still binds Checkout-to-Payment RPC metrics to Payment as peer evidence, but Payment has no observed trace span and no observed log in this incident. This is intentionally represented as absence of observed Payment evidence, not as proof that Payment could never have executed.

### 015D conclusion

The two synchronized failure modes demonstrate why cross-modal evidence must preserve structure:

```text
paymentFailure
  metrics -> degraded Checkout / Payment RPC
  traces  -> Payment SERVER observed and in error
  logs    -> Payment invalid-token mechanism

paymentUnreachable real ON
  metrics -> degraded Checkout / Payment RPC
  traces  -> resolver failure on Checkout client before Payment server evidence
  logs    -> frontend symptom; no Payment log observed
```

The same high-level metric symptom can therefore correspond to materially different request-level mechanisms. RootLens keeps the modalities typed and correlated rather than collapsing them into an opaque root-cause score.

**Decision:** freeze Experiment 015D and move to the first single custom investigation loop. No LangChain/LangGraph-style orchestration is justified yet.

## Current architecture decision

```text
Knowledge path
--------------
Question
  -> BGE dense retrieval
  -> whole-document ranking
  -> top-5 context
  -> BasicGroundedRAG
  -> structured claim/source answer
  -> strict validation

Live incident path
------------------
Incident
  -> deterministic Prometheus metrics
  -> deterministic Jaeger / OTLP traces
  -> deterministic OpenSearch logs
  -> unified typed cross-modal evidence
  -> knowledge retrieval when needed
  -> single custom investigation loop   [next]
  -> explicit hypothesis / evidence engine
  -> agentic orchestration
```

No LangChain/LangGraph-style orchestration is justified yet.

## What comes next

The retrieval phase is frozen. Metrics, traces, and logs are now deterministic evidence sources.

Planned sequence:

1. **first single custom investigation loop**;
2. agentic RAG and deterministic tool selection;
3. explicit hypothesis / evidence / contradiction engine;
4. multi-agent architecture only if it beats the single-agent baseline;
5. code, Git, topology, and time-series investigation;
6. productization, UI, final benchmark, and incident replay.

## Interview-level project summary

> I am building an AI incident investigator from first principles rather than starting from an agent framework. I first benchmarked sparse retrieval, dense embeddings, chunking, rerankers, multi-query, fusion, set-aware selection, and decomposition, then built an evidence-grounded RAG contract where every factual claim cites evidence and the model can abstain. After freezing Dense top-5 as the default retrieval path, I built deterministic observability layers for metrics, traces, and logs, then unified them into typed cross-modal incident evidence with explicit provenance, metric/service bindings, exact trace/span correlation, integrity semantics, and synchronized experiments. In a server-side Payment failure, the same requests show Checkout-to-Payment metric errors, matching Payment server errors, and a systematic invalid-token log. In a real runtime `paymentUnreachable` failure, the Checkout-to-Payment metric also reaches a 100% error rate, but all measured requests fail at the client resolver, no Payment server span is observed, and no Payment log is observed. The next step is a single custom investigation loop that learns to choose among these deterministic evidence tools before any multi-agent orchestration is introduced.

## Status

```text
Observability foundations          complete
IR / retrieval foundations         complete
Advanced retrieval experiments     complete
Evidence-grounded RAG              complete
RAG evaluation / abstention        complete
Failure attribution                complete
Answer-level retriever decision    complete
Deterministic metrics (015A)       complete
Deterministic traces (015B)        complete
Deterministic logs (015C)          complete
Unified evidence (015D)            complete
Single investigation agent         next
Agentic RAG                        planned
Hypothesis / evidence engine       planned
Multi-agent evaluation             planned
Productization / final benchmark   planned
```

RootLens now has a frozen deterministic cross-modal evidence layer and is moving to the **first single investigation agent**.

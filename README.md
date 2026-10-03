# RootLens

**Autonomous AI Incident Investigator for distributed systems**

RootLens is an applied AI / systems project that explores how to build an evidence-grounded incident investigator for distributed systems. The long-term goal is an AI system that can investigate failures by combining live observability data, technical knowledge, historical incidents, code, Git history, service topology, and explicit hypothesis testing.

The project is deliberately built from first principles. Instead of starting with an agent framework, RootLens first establishes reliable retrieval, evidence contracts, evaluation methodology, and deterministic components. The core rule is simple:

> **claim -> evidence -> source**

The system should eventually be able to observe an incident, decide what evidence is missing, call the appropriate tools, retrieve technical knowledge, generate competing hypotheses, reject unsupported alternatives, identify the best-supported root cause, explain its reasoning with evidence, and abstain when the available information is insufficient.

## Current status

**Stages 1-14 and deterministic observability Experiments 015A-015B are complete.**

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

The live incident path now has deterministic metrics and trace evidence:

```text
incident
   |
   +--> Prometheus metrics evidence
   |
   +--> Jaeger / OTLP request-level trace evidence
   |
   v
next: deterministic log evidence
```

No agent framework has been introduced yet. Agentic orchestration will only be added after metrics, traces, and logs have stable contracts, tests, provenance, and controlled evaluations.

## Why RootLens is not just another RAG chatbot

Most RAG demos optimize retrieval or answer quality in isolation. RootLens treats incident investigation as a systems problem with several distinct failure modes:

- retrieval can miss useful evidence;
- retrieved evidence can be ignored;
- cited evidence can fail to support the claim;
- the answer can be technically incomplete despite good retrieval;
- a model can overclaim when information is missing;
- more complex retrieval can improve candidate recall without improving the final answer;
- LLM-as-a-judge evaluations can themselves be noisy.

The project therefore evaluates each layer separately and then checks whether a subsystem improvement actually produces a task-level gain.

## Project principles

1. **Mechanisms before frameworks.** Core retrieval, evaluation, grounding, and orchestration logic is implemented directly before considering LangChain/LangGraph-style abstractions.
2. **Evidence over eloquence.** A fluent answer is not sufficient. Factual claims need explicit source support.
3. **Abstention is a feature.** The system must distinguish answerable, partially answerable, and unanswerable questions.
4. **DEV and TEST are separated.** Architecture decisions are made on DEV; frozen TEST is reserved for explicit checkpoints.
5. **No ground-truth leakage.** Hidden qrels, benchmark answers, and injected-fault labels are not exposed to the generation model.
6. **Complexity must earn its place.** New retrieval or agentic components stay only if experiments show a meaningful task-level benefit.
7. **Evaluation is multi-layered.** Retrieval metrics, citation metrics, claim-level grounding, abstention, intervention tests, and pairwise answer evaluation are treated as different measurements.

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
│   ├── observability/              # Prometheus, Jaeger, trace evidence/tools
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

The intended modality split is:

```text
metrics -> detect and scope
traces  -> localize request path
logs    -> explain mechanism
docs    -> provide technical knowledge
code    -> verify implementation behavior
```

A user-visible symptom is not automatically the root cause, and a control-plane configuration value is not automatically proof that the same value was evaluated by the runtime handling a request.

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
find error and slow spans
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

An earlier attempt to reuse old 015A windows failed because Jaeger no longer retained the individual traces. Controlled trace experiments now freeze both structured observations and raw OTLP `resourceSpans` while the evidence still exists.

Key lesson:

> RootLens should acquire missing evidence and test hypotheses instead of forcing an RCA from the first anomaly.

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
  -> deterministic logs                 [next]
  -> unified evidence / correlation
  -> knowledge retrieval when needed
  -> single investigation loop
  -> explicit hypothesis / evidence engine
  -> agentic orchestration
```

No LangChain/LangGraph-style orchestration is justified yet.

## What comes next

The retrieval phase is frozen. Metrics and traces are now deterministic evidence sources.

Planned sequence:

1. **015C - deterministic log search and correlation**;
2. **015D - unified metrics / traces / logs evidence correlation**;
3. first single custom investigation loop;
4. agentic RAG and tool selection;
5. explicit hypothesis / evidence / contradiction engine;
6. multi-agent architecture only if it beats the single-agent baseline;
7. code, Git, topology, and time-series investigation;
8. productization, UI, final benchmark, and incident replay.

## Interview-level project summary

> I am building an AI incident investigator from first principles rather than starting from an agent framework. I first benchmarked sparse retrieval, dense embeddings, chunking, rerankers, multi-query, fusion, set-aware selection, and decomposition, then built an evidence-grounded RAG contract where every factual claim cites evidence and the model can abstain. After freezing Dense top-5 as the default retrieval path, I moved to deterministic observability tools. The metrics layer captures exact PromQL and baseline-vs-incident evidence; the trace layer works directly with Jaeger v3 and OTLP, reconstructs request topology, diagnoses telemetry-integrity problems, and preserves raw traces during controlled experiments. One trace experiment exposed a control-plane/data-plane feature-flag divergence: the control plane reported a fault ON while every Checkout request evaluated a cached OFF value. Restarting only Checkout changed the evaluated flag to ON and produced the expected client-side resolver failure with no Payment server span. The next step is deterministic log correlation before any agentic orchestration.

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
Deterministic logs (015C)          next
Unified evidence (015D)            planned
Single investigation agent         planned
Agentic RAG                        planned
Hypothesis / evidence engine       planned
Multi-agent evaluation             planned
Productization / final benchmark   planned
```

RootLens is now moving from **deterministic request-level observability** to **cross-modal evidence correlation**.

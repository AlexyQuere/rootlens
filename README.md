# RootLens

**Autonomous AI Incident Investigator for distributed systems**

RootLens is an applied AI / systems project that explores how to build an evidence-grounded incident investigator for distributed systems. The long-term goal is an AI system that can investigate failures by combining live observability data, technical knowledge, historical incidents, code, Git history, service topology, and explicit hypothesis testing.

The project is deliberately built from first principles. Instead of starting with an agent framework, RootLens first establishes reliable retrieval, evidence contracts, evaluation methodology, and deterministic components. The core rule is simple:

> **claim -> evidence -> source**

The system should eventually be able to observe an incident, decide what evidence is missing, call the appropriate tools, retrieve technical knowledge, generate competing hypotheses, reject unsupported alternatives, identify the best-supported root cause, explain its reasoning with evidence, and abstain when the available information is insufficient.

## Current status

**Stage 14 is complete.** The retrieval and evidence-grounded RAG phase is now frozen.

The current default knowledge pipeline is:

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

The next phase is **deterministic observability tooling**: metrics, traces, and logs. Agentic orchestration will only be added after these tools have stable contracts and tests.

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
│   └── evaluation/                 # hidden or derived evaluation artifacts
├── scripts/                        # reproducible experiment runners
├── src/rootlens/
│   ├── retrieval/                  # sparse, dense, fusion, multi-query
│   ├── rag/                        # evidence-grounded generation pipeline
│   ├── evaluation/                 # retrieval, grounding, abstention, pairwise metrics
│   └── llm/                        # provider abstraction
└── tests/                          # deterministic unit tests
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

The first manual RCA exercise established the investigation discipline used throughout RootLens:

```text
Observation != Interpretation != Hypothesis != Conclusion
```

Example causal chain from an injected payment failure:

```text
invalid / unresolved Payment destination
        -> resolver produced zero addresses
        -> Checkout -> Payment Charge returned gRPC UNAVAILABLE
        -> Checkout translated failure to INTERNAL
        -> browser observed HTTP 500
```

The important lesson is that a user-visible symptom is not automatically the root cause. Metrics detect and quantify; traces localize the failing request path; logs and configuration evidence explain the mechanism.

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

Next investigation path
-----------------------
Incident
  -> deterministic metrics tool
  -> deterministic trace tool
  -> deterministic log tool
  -> knowledge retrieval when needed
  -> hypothesis / evidence engine
  -> agentic orchestration
```

## What comes next

The retrieval phase is intentionally frozen. The next work is not more RAG tuning.

Planned sequence:

1. deterministic Prometheus metrics tool;
2. deterministic trace investigation tool;
3. deterministic log search / correlation tool;
4. baseline comparison and change detection;
5. single custom investigation loop;
6. agentic RAG and tool selection;
7. explicit hypothesis / evidence / contradiction engine;
8. multi-agent architecture only if it beats the single-agent baseline;
9. code, Git, topology, and time-series investigation;
10. productization, UI, final benchmark, and incident replay.

## Interview-level project summary

A concise way to describe RootLens:

> I am building an AI incident investigator from first principles rather than starting from an agent framework. I first built and benchmarked the retrieval stack - sparse retrieval, dense embeddings, chunking, rerankers, multi-query, fusion, set-aware selection, and decomposition - then moved to an evidence-grounded RAG contract where every factual claim cites retrieved evidence and the model can abstain. I evaluate retrieval, citations, claim support, abstention, and answer quality separately. One of the main findings was that higher candidate recall did not reliably improve final answers, so I kept the simpler Dense top-5 retriever. The next phase is deterministic metrics, traces, and logs tooling before introducing a single investigation agent and, only if justified experimentally, a multi-agent system.

## Status

```text
Observability foundations        complete
IR / retrieval foundations       complete
Advanced retrieval experiments   complete
Evidence-grounded RAG            complete
RAG evaluation / abstention      complete
Failure attribution              complete
Answer-level retriever decision  complete
Deterministic observability      next
Single investigation agent       planned
Agentic RAG                      planned
Hypothesis / evidence engine      planned
Multi-agent evaluation           planned
Productization / final benchmark planned
```

RootLens is currently at the transition from **retrieval-grounded QA** to **tool-driven incident investigation**.

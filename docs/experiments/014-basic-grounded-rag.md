# Experiment 014 — Evidence-Grounded RAG

**Project:** RootLens — Autonomous AI Incident Investigator  
**Status:** Completed  
**Default retrieval decision after 014F:** Dense BGE whole-document top-5  
**Generator used in frozen DEV experiments:** `qwen-3.6-35b-instruct`  
**Dense encoder:** `BAAI/bge-small-en-v1.5`  
**Evaluation split:** DEV only, 24 queries  
**Core principle:** **claim → evidence → source**

---

## 1. Objective

Experiment 014 is the transition from retrieval-only evaluation to an end-to-end evidence-grounded RAG system.

Before this experiment, RootLens could rank documents. A useful incident investigator must also:

1. generate an answer from retrieved evidence,
2. expose which evidence supports each factual claim,
3. reject malformed or unsupported model outputs,
4. abstain when evidence is insufficient,
5. distinguish retrieval defects from answer-level defects,
6. justify retrieval complexity using downstream answer quality.

The architecture is deliberately simple:

```text
question
   ↓
Dense BGE retrieval
   ↓
top-5 whole documents
   ↓
evidence-only prompt
   ↓
LLM
   ↓
strict structured output
   ↓
schema + citation validation
   ↓
GroundedAnswer
```

No agent framework, vector database, LangChain, or LangGraph is required at this stage.

---

# 014A — Basic Evidence-Grounded RAG

## 2. Why retrieval metrics were not enough

A retriever can return relevant documents while the generator ignores them, invents unsupported facts, cites the wrong source, or answers when it should abstain.

Conversely, a qrel-positive document can be missing while the remaining context is still sufficient.

Therefore:

\[
\text{retrieval quality} \neq \text{answer quality}
\]

and

\[
\text{citation presence} \neq \text{grounding}
\]

A citation proves only that a source identifier was emitted. It does not prove entailment.

## 3. Output contract

RootLens uses three answer states:

```text
answered
partial
abstained
```

Conceptual schema:

```json
{
  "status": "answered | partial | abstained",
  "claims": [
    {
      "text": "A factual claim.",
      "sources": ["source-id.md"]
    }
  ],
  "limitation": null
}
```

### Status semantics

**answered**
- at least one claim,
- each claim has at least one valid source,
- no missing-evidence limitation is required.

**partial**
- at least one supported claim,
- a non-empty limitation states what evidence is missing.

**abstained**
- no factual claims,
- a non-empty limitation explains why the evidence is insufficient.

Abstention is therefore a first-class system behavior.

## 4. Evidence isolation

The generator sees only retrieved evidence, for example:

```text
[SOURCE: payment-service.md]
...
[/SOURCE]
```

It does not see qrels, expected answers, benchmark labels, or injected-fault ground truth.

## 5. Strict validation

The parser validates:

- JSON structure,
- status value,
- claim structure,
- non-empty claim text,
- non-empty source list,
- citations restricted to retrieved documents,
- consistency between status, claims, and limitation.

Harmless syntax such as `SOURCE: payment-service.md` or `[SOURCE: payment-service.md]` is normalized, but the final source identifier must still exactly match an allowed retrieved source.

Principle:

\[
\boxed{\text{robust syntax, strict semantics}}
\]

RootLens never guesses which document a hallucinated citation was intended to reference.

## 6. Schema retry

A malformed schema is different from a provenance failure.

For a schema error, RootLens allows one constrained retry using the same question and same evidence plus the validation error and previous output.

Retrieval is not repeated.

Citation hallucinations are not automatically repaired.

```text
LLM
 ↓
Validator
 ├── valid → accept
 ├── schema error → one constrained retry
 └── invalid citation → reject
```

---

# 014B — Offline RAG Evaluation

## 7. Evidence-flow metrics

Let:
- \(R\): retrieved documents,
- \(C\): cited documents,
- \(Q\): positive qrel documents.

Retrieval qrel recall:

\[
\mathrm{Recall}_{retrieval} = \frac{|R \cap Q|}{|Q|}
\]

Citation qrel precision:

\[
\mathrm{Precision}_{citation} = \frac{|C \cap Q|}{|C|}
\]

Citation qrel recall:

\[
\mathrm{Recall}_{citation} = \frac{|C \cap Q|}{|Q|}
\]

Relevant evidence retention:

\[
\mathrm{Retention} = \frac{|C \cap R \cap Q|}{|R \cap Q|}
\]

Source utilization:

\[
\mathrm{Utilization} = \frac{|C \cap R|}{|R|}
\]

These are qrel diagnostics, not claim-entailment metrics.

## 8. Frozen DEV results

Dense top-5 RAG produced:

- 24 / 24 `answered`,
- 116 claims,
- 4.83 claims / answer,
- mean generation latency ≈ 2087.6 ms.

| Metric | Result |
|---|---:|
| Retrieval qrel recall | **0.8299** |
| Citation qrel precision | **0.9375** |
| Citation qrel recall | **0.6736** |
| Relevant evidence retention | **0.8403** |
| Source utilization | **0.4167** |

The low source utilization showed the model was not blindly citing all five retrieved documents.

The 24 DEV questions were all answerable, so a separate abstention benchmark was required.

---

# 014C — Claim-Level Groundedness

## 9. Why qrels cannot measure grounding

A document can be relevant to a query without supporting every generated sentence.

Grounding is a claim-level entailment question:

\[
\text{claim} \stackrel{?}{\Longleftarrow} \text{cited evidence}
\]

Each of the 116 claims was judged using only:

- the question,
- the exact claim,
- the texts of the cited sources.

The grounding judges did not see qrels or expected answers.

## 10. Grounding labels

```text
full
partial
none
```

- **full** — the cited evidence supports the full logical strength of the claim,
- **partial** — the source supports only part of the claim or a weaker formulation,
- **none** — the claim is unsupported.

Logical strength matters. `may indicate` does not entail `proves`.

## 11. Cross-judge results

Judges:
- `gemma-4-31b`,
- `qwen-3.6-35b-instruct-reasoning-high`.

| Result | Gemma | Qwen reasoning |
|---|---:|---:|
| Full | 115 | 115 |
| Partial | 1 | 1 |
| None | 0 | 0 |

Exact cross-judge agreement:

\[
\frac{114}{116} = 98.28\%
\]

A targeted human audit covered both judge disagreements plus eight high-risk agreement cases.

Human result:

```text
10 full
0 partial
0 none
```

Defensible conclusion:

> Both judges classified 115/116 claims as fully supported and agreed on 114/116. A targeted human audit of both disagreements plus eight high-risk agreement cases found all ten audited claims fully supported.

This is not the same as claiming a human-verified 99.14% grounding accuracy.

---

# 014D — Abstention and Insufficient Evidence

## 12. Matched-triplet benchmark

A relevant-looking context is not necessarily sufficient evidence.

Six topics were converted into matched triplets:

1. answerable,
2. partial,
3. unanswerable.

Total:

\[
6 \times 3 = 18
\]

queries.

Intentionally absent fields included:

- production PostgreSQL version,
- production cloud region,
- current on-call engineer,
- Kubernetes replica count,
- TLS certificate expiry,
- production CPU limit.

The unanswerable queries still retrieved topically relevant documents, which makes the benchmark stronger than using unrelated questions.

## 13. Abstention results

```text
answered   6
partial    6
abstained  6
```

| Metric | Result |
|---|---:|
| Accuracy | **1.0000** |
| Balanced accuracy | **1.0000** |
| Macro-F1 | **1.0000** |
| Failure-to-abstain rate | **0.0000** |
| Partial overclaim rate | **0.0000** |
| Partial over-abstain rate | **0.0000** |
| Triplet consistency | **1.0000** |

One schema retry occurred in 18 generations.

Correct interpretation:

> Perfect status classification on a small controlled 18-query matched-triplet benchmark.

It does not establish perfect open-world abstention.

---

# 014E — Failure Attribution with Evidence Interventions

## 14. Retrieval gap versus answer failure

Six earlier retrieval misses were tested using evidence interventions.

For each query:

```text
Frozen Dense top-5
      vs
Qrel-enriched top-5
```

with the same question, generator, prompt, decoding, and context budget.

Qrels were used only to construct the experimental intervention; they were never visible to the LLM.

## 15. Failure taxonomy

1. **retrieval-limited** — missing evidence is inserted, used, and repairs the answer;
2. **evidence-utilization-limited** — needed evidence is present but ignored;
3. **generation/reasoning-limited** — evidence is cited but the answer remains deficient;
4. **retrieval gap but not answer-limiting** — the missing qrel was not necessary for a sufficient answer;
5. **inconclusive**.

This turns RAG debugging into a controlled intervention:

\[
\text{intervene on evidence} \rightarrow \text{observe answer}
\]

## 16. 014E result

Across six targeted queries:

- qrel citation recall: **0.5278 → 0.8611**,
- 9 missing qrel documents inserted,
- 8 / 9 inserted documents cited.

Yet the original Dense answers were already sufficient in all six cases.

```text
retrieval_limited                         0 / 6
evidence_utilization_limited             0 / 6
generation_reasoning_limited             0 / 6
retrieval_gap_not_answer_limiting        6 / 6
inconclusive                              0 / 6
```

Key result:

\[
\boxed{\text{retrieval recall improvement} \not\Rightarrow \text{answer quality improvement}}
\]

---

# 014F — Dense versus Semantic Multi-Query at Answer Level

## 17. Experimental design

The production question was not whether Multi-Query could increase candidate recall, but whether it improved final answers under the same top-5 context budget.

```text
Dense
  1 retrieval query
  ↓
top-5
  ↓
same RAG pipeline

vs

Semantic Multi-Query
  original + 3 frozen rewrites
  ↓
Dense top-10 per query
  ↓
RRF
  ↓
top-5
  ↓
same RAG pipeline
```

Only the retrieval strategy changed.

## 18. Reciprocal Rank Fusion

For document \(d\):

\[
\mathrm{RRF}(d) = \sum_{q \in Q} \frac{1}{K + \mathrm{rank}_q(d)}
\]

with \(K=60\).

RRF combines ranks instead of assuming raw cosine scores are perfectly calibrated across rewritten queries.

## 19. Deterministic comparison

| Metric | Dense | Semantic | Delta |
|---|---:|---:|---:|
| Retrieval qrel Recall@5 | **0.8299** | 0.8194 | -0.0104 |
| Citation qrel precision | **0.9375** | 0.8785 | -0.0590 |
| Citation qrel recall | 0.6736 | **0.6806** | +0.0069 |
| Relevant evidence retention | 0.8403 | **0.8472** | +0.0069 |
| Source utilization | 0.4167 | **0.4583** | +0.0417 |
| Mean claims | 4.8333 | 4.6250 | -0.2083 |

Evidence composition:

- changed top-5 set on **15 / 24** queries,
- Semantic added **1** relevant document,
- Semantic lost **2** relevant documents,
- mean evidence-set Jaccard: **0.7445**.

Cost:

- Dense retrieval calls / question: **1**,
- Semantic retrieval calls / question: **4**,
- Semantic retrieval latency mean: **64.5 ms**,
- Dense mean RAG latency: **2087.6 ms**,
- Semantic mean RAG latency: **2265.6 ms**,
- delta: **+178 ms**,
- Semantic schema retries: **5 / 24**.

## 20. Blind pairwise evaluation

Two judges compared Dense and Semantic answers without seeing system identity:

- Gemma 4 31B,
- Qwen 3.6 reasoning-high.

Answer order was reversed between judges to reduce positional bias.

Cross-judge results:

- exact agreement: **18 / 24 = 75%**,
- Cohen's kappa: **0.623**.

## 21. Identical-context negative control

For **9 / 24** questions, both retrievers produced the same top-5 evidence set.

Those queries form a natural negative control: any answer preference cannot be caused by retrieval.

Yet judge non-tie rates were:

- Gemma: **33.3%**,
- Qwen: **55.6%**.

Therefore:

\[
\boxed{\text{different answer} \not\Rightarrow \text{retrieval effect}}
\]

Generation variance and judge variance are real confounders.

## 22. Targeted blind human audit

The human audit covered all decision-relevant cases:

- judge disagreements,
- identical-context non-ties,
- changed-context consensus wins.

Total audited: **15**.

```text
Dense         6
Semantic      6
Tie           3
Inconclusive  0
```

Human agreement with judges:

- Gemma: **10 / 15 = 66.7%**,
- Qwen reasoning: **9 / 15 = 60.0%**.

LLM-as-a-judge is therefore treated as an evaluation instrument, not ground truth.

## 23. Final combined adjudication

All 24 DEV questions:

```text
Dense         6
Semantic      6
Tie          12
Inconclusive  0
```

15 changed-context queries:

```text
Dense         4
Semantic      5
Tie           6
```

9 identical-context controls:

```text
Dense         2
Semantic      1
Tie           6
```

The one-answer Semantic edge on changed contexts is of the same order as preferences observed when retrieval did not change, so it cannot be robustly attributed to Multi-Query retrieval.

---

# 24. Final architecture decision

RootLens keeps the following default knowledge path:

```text
BAAI/bge-small-en-v1.5
        ↓
whole-document embeddings
        ↓
exact dense search
        ↓
top-5
        ↓
BasicGroundedRAG
        ↓
claim → evidence → source
```

Semantic Multi-Query RRF remains an experimental strategy but is not enabled systematically.

The conclusion is not “Dense is universally better”. The defensible statement is:

> **Semantic Multi-Query did not demonstrate a material answer-level improvement over the simpler Dense baseline sufficient to justify its additional retrieval complexity.**

---

# 25. Main engineering lessons

## Retrieval metrics are necessary but insufficient

\[
\text{candidate recall}
\neq
\text{final context quality}
\neq
\text{answer quality}
\]

## Qrels are not entailment labels

Query-level relevance is not claim-level support.

## Abstention must be evaluated explicitly

The system must distinguish “I found related material” from “I have enough evidence to answer this exact request.”

## Validation belongs outside the LLM

The model proposes. Deterministic code validates schema, citations, source membership, and state consistency.

## Complexity must earn its place

Multi-Query added four retrieval calls, fusion logic, latency, and debugging surface without demonstrating a robust downstream benefit.

## LLM judges require controls

The identical-context negative control exposed preference noise that would otherwise have been misattributed to retrieval.

---

# 26. Main files

Core RAG:

```text
src/rootlens/rag/basic_rag.py
src/rootlens/llm/provider.py
```

Evaluation:

```text
src/rootlens/evaluation/rag_metrics.py
src/rootlens/evaluation/grounding_judge.py
src/rootlens/evaluation/abstention_metrics.py
src/rootlens/evaluation/failure_attribution.py
src/rootlens/evaluation/pairwise_answer_judge.py
src/rootlens/evaluation/pairwise_metrics.py
```

Experimental retrieval:

```text
src/rootlens/retrieval/frozen_multi_query_rrf.py
```

Important artifacts:

```text
data/benchmark_v2/dev_rag_outputs_v1.json
data/benchmark_v2/dev_rag_outputs_semantic_v1.json
data/evaluation/abstention_eval_v1.json
data/evaluation/rag_failure_attribution_final_v1.json
data/evaluation/rag_dense_vs_semantic_v1.json
data/evaluation/rag_pairwise_gemma_v1.json
data/evaluation/rag_pairwise_qwen_reasoning_v1.json
data/evaluation/rag_pairwise_judge_agreement_v1.json
data/evaluation/rag_pairwise_human_audit_eval_v1.json
```

---

# 27. Interview explanation

A concise senior-level explanation:

> “Once I had a strong dense retriever, I stopped optimizing retrieval metrics in isolation and built an evidence-grounded RAG layer. Every generated factual claim must cite retrieved evidence, and deterministic validation rejects invalid schemas or citations. I evaluated the system at several levels: qrel evidence flow, claim-level grounding with two independent judges and targeted human audit, abstention with matched answerable/partial/unanswerable triplets, and causal evidence interventions to separate retrieval gaps from actual answer-limiting failures. Finally, I compared Dense retrieval against semantic Multi-Query at the final-answer level using blind pairwise judges, reversed answer ordering, identical-context negative controls, and human adjudication. Multi-Query added complexity but did not demonstrate a robust downstream benefit, so I kept Dense top-5 as the default.”

Likely senior questions:

### Why no confidence score?

Because an arbitrary LLM scalar is not a calibrated probability. RootLens exposes explicit states (`answered`, `partial`, `abstained`) and evidence provenance instead.

### Why one schema retry but not one citation retry?

A malformed JSON object is an interface-format failure. An invented citation is a provenance failure. Automatically repairing the latter can hide unsafe behavior.

### Why not use qrels as grounding labels?

Qrels are query-level relevance judgments; grounding is claim-level entailment.

### Why keep Dense rather than Multi-Query?

Because candidate-recall gains did not translate into better final top-5 retrieval or a robust answer-level advantage, while operational complexity increased.

### Why was the negative control important?

Because repeated LLM generation can create different answers even with identical evidence. Without a negative control, generation noise can be falsely attributed to retrieval changes.

---

# 28. Decision and next phase

**Experiment 014 is closed.**

Default RootLens RAG:

```text
Dense BGE
+ whole documents
+ top-5
+ evidence-grounded generation
+ deterministic schema/citation validation
+ explicit abstention
```

No further retrieval tuning will be performed unless future tool-driven incident investigations reveal a measurable downstream retrieval failure.

Next phase:

```text
metrics
→ traces
→ logs
→ structured evidence objects
→ single-agent investigation loop
```

from __future__ import annotations

import hashlib
import json
import os
import time

from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.failure_attribution import (
    build_qrel_enriched_context,
)
from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)
from rootlens.rag.basic_rag import (
    BasicGroundedRAG,
)


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

KNOWLEDGE_DIR = (
    BENCHMARK_DIR
    / "knowledge"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)

BASELINE_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_oracle_outputs_v1.json"
)


TARGET_QUERY_IDS = (
    "dev-008",
    "dev-015",
    "dev-020",
    "dev-021",
    "dev-022",
    "dev-023",
)

TOP_K = 5


class StaticEvidenceRetriever:

    def __init__(
        self,
        ranking_by_query:
            dict[str, list[str]],
    ) -> None:

        self.ranking_by_query = (
            ranking_by_query
        )

    def search(
        self,
        query: str,
        k: int,
    ) -> list[
        tuple[str, float]
    ]:

        if query not in (
            self.ranking_by_query
        ):
            raise KeyError(
                "No static evidence "
                f"ranking for: {query}"
            )

        source_ids = (
            self.ranking_by_query[
                query
            ][
                :k
            ]
        )

        #
        # Synthetic scores.
        #
        # They are NOT Dense similarity
        # scores and are never shown to
        # the LLM.
        #
        return [
            (
                source_id,
                float(
                    len(source_ids)
                    - index
                ),
            )
            for index, source_id
            in enumerate(
                source_ids
            )
        ]


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_documents() -> dict[
    str,
    str,
]:

    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):

        documents[
            path.name
        ] = (
            path.read_text(
                encoding="utf-8"
            )
            .strip()
        )

    if not documents:
        raise RuntimeError(
            "No knowledge documents found."
        )

    return documents


def file_sha256(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def require_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:
        raise RuntimeError(
            "Missing environment "
            f"variable: {name}"
        )

    return value


def save_checkpoint(
    metadata: dict,
    items: list[dict],
) -> None:

    data = {
        "metadata":
            metadata,

        "items":
            items,
    }

    temporary = (
        OUTPUT_FILE.with_suffix(
            ".json.tmp"
        )
    )

    temporary.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary.replace(
        OUTPUT_FILE
    )


def main() -> None:

    documents = (
        load_documents()
    )

    queries = load_json(
        DEV_FILE
    )

    baseline_data = load_json(
        BASELINE_FILE
    )

    baseline_items = {
        item[
            "query_id"
        ]:
            item
        for item
        in baseline_data.get(
            "items",
            []
        )
    }

    query_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in queries
    }

    for query_id in (
        TARGET_QUERY_IDS
    ):

        if query_id not in query_by_id:
            raise RuntimeError(
                "Missing DEV query: "
                f"{query_id}"
            )

        if query_id not in baseline_items:
            raise RuntimeError(
                "Missing frozen baseline "
                f"output: {query_id}"
            )

    rankings = {}

    interventions = {}

    for query_id in (
        TARGET_QUERY_IDS
    ):

        example = (
            query_by_id[
                query_id
            ]
        )

        baseline_item = (
            baseline_items[
                query_id
            ]
        )

        baseline_ids = [
            evidence[
                "source_id"
            ]
            for evidence
            in baseline_item[
                "evidence"
            ]
        ]

        intervention = (
            build_qrel_enriched_context(
                baseline_ids=(
                    baseline_ids
                ),
                relevance=(
                    example[
                        "relevance"
                    ]
                ),
                k=TOP_K,
            )
        )

        for source_id in (
            intervention
            .enriched_ids
        ):

            if source_id not in (
                documents
            ):
                raise RuntimeError(
                    "Intervention references "
                    "unknown document: "
                    f"{source_id}"
                )

        rankings[
            example[
                "query"
            ]
        ] = list(
            intervention
            .enriched_ids
        )

        interventions[
            query_id
        ] = intervention

    retriever = (
        StaticEvidenceRetriever(
            rankings
        )
    )

    model = require_env(
        "ROOTLENS_LLM_MODEL"
    )

    base_url = require_env(
        "ROOTLENS_LLM_BASE_URL"
    )

    api_key = require_env(
        "ROOTLENS_LLM_API_KEY"
    )

    provider = (
        OpenAICompatibleLLM(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
    )

    rag = BasicGroundedRAG(
        documents=documents,
        retriever=retriever,
        provider=provider,
        top_k=TOP_K,
        max_schema_retries=1,
    )

    metadata = {
        "experiment":
            "014E",

        "version":
            "v1",

        "condition":
            "qrel_enriched_top5",

        "target_query_ids":
            list(
                TARGET_QUERY_IDS
            ),

        "top_k":
            TOP_K,

        "context_budget_matched":
            True,

        "qrels_visible_to_llm":
            False,

        "qrels_used_by_orchestrator":
            True,

        "intervention_policy":
            (
                "qrel-positive documents "
                "ordered by grade, then "
                "original Dense top-5 used "
                "to fill remaining slots"
            ),

        "dev_file_sha256":
            file_sha256(
                DEV_FILE
            ),

        "baseline_file_sha256":
            file_sha256(
                BASELINE_FILE
            ),

        "llm_model":
            model,

        "rag_prompt_version":
            BasicGroundedRAG
            .PROMPT_VERSION,
    }

    items = []
    completed_ids = set()

    if OUTPUT_FILE.exists():

        existing = load_json(
            OUTPUT_FILE
        )

        existing_metadata = (
            existing.get(
                "metadata",
                {}
            )
        )

        for field in (
            "experiment",
            "version",
            "condition",
            "top_k",
            "dev_file_sha256",
            "baseline_file_sha256",
            "llm_model",
            "rag_prompt_version",
        ):

            if (
                existing_metadata.get(
                    field
                )
                != metadata.get(
                    field
                )
            ):
                raise RuntimeError(
                    "Existing checkpoint "
                    "metadata mismatch: "
                    f"{field}"
                )

        items = existing.get(
            "items",
            []
        )

        completed_ids = {
            item[
                "query_id"
            ]
            for item in items
        }

        print(
            "Resuming with "
            f"{len(completed_ids)} "
            "queries already completed."
        )

        print()

    print(
        "Experiment 014E — "
        "Qrel-Enriched Evidence Intervention"
    )

    print(
        f"Queries: "
        f"{len(TARGET_QUERY_IDS)}"
    )

    print(
        f"Context budget: "
        f"top-{TOP_K}"
    )

    print(
        "Qrels visible to LLM: False"
    )

    print(
        f"LLM: {model}"
    )

    print()

    for index, query_id in enumerate(
        TARGET_QUERY_IDS,
        start=1,
    ):

        if query_id in completed_ids:

            print(
                f"[{index}/"
                f"{len(TARGET_QUERY_IDS)}] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        example = (
            query_by_id[
                query_id
            ]
        )

        intervention = (
            interventions[
                query_id
            ]
        )

        query = (
            example[
                "query"
            ]
        )

        print(
            f"[{index}/"
            f"{len(TARGET_QUERY_IDS)}] "
            f"{query_id}"
        )

        print(
            f"  question: "
            f"{query}"
        )

        print(
            "  baseline: "
            + ", ".join(
                intervention
                .baseline_ids
            )
        )

        print(
            "  enriched: "
            + ", ".join(
                intervention
                .enriched_ids
            )
        )

        print(
            "  recovered qrel: "
            + (
                ", ".join(
                    intervention
                    .recovered_qrel_ids
                )
                if (
                    intervention
                    .recovered_qrel_ids
                )
                else "[]"
            )
        )

        print(
            "  dropped baseline: "
            + (
                ", ".join(
                    intervention
                    .dropped_baseline_ids
                )
                if (
                    intervention
                    .dropped_baseline_ids
                )
                else "[]"
            )
        )

        if (
            intervention
            .omitted_positive_qrel_ids
        ):

            print(
                "  WARNING omitted "
                "positive qrel: "
                + ", ".join(
                    intervention
                    .omitted_positive_qrel_ids
                )
            )

        start = (
            time.perf_counter()
        )

        result = rag.answer(
            query
        )

        latency_ms = (
            (
                time.perf_counter()
                - start
            )
            * 1000.0
        )

        print(
            f"  status: "
            f"{result.answer.status}"
        )

        print(
            f"  claims: "
            f"{len(result.answer.claims)}"
        )

        for claim_index, claim in enumerate(
            result.answer.claims,
            start=1,
        ):

            print(
                f"    {claim_index}. "
                f"{claim.text}"
            )

            print(
                "       sources: "
                + ", ".join(
                    claim.sources
                )
            )

        if (
            result.answer.limitation
            is not None
        ):

            print(
                "  limitation: "
                f"{result.answer.limitation}"
            )

        print(
            "  generation_attempts: "
            f"{result.generation_attempts}"
        )

        print(
            f"  latency_ms: "
            f"{latency_ms:.1f}"
        )

        print()

        item = {
            "query_id":
                query_id,

            "query":
                query,

            "category":
                example[
                    "category"
                ],

            "intervention": {
                "baseline_ids":
                    list(
                        intervention
                        .baseline_ids
                    ),

                "enriched_ids":
                    list(
                        intervention
                        .enriched_ids
                    ),

                "positive_qrel_ids":
                    list(
                        intervention
                        .positive_qrel_ids
                    ),

                "recovered_qrel_ids":
                    list(
                        intervention
                        .recovered_qrel_ids
                    ),

                "dropped_baseline_ids":
                    list(
                        intervention
                        .dropped_baseline_ids
                    ),

                "omitted_positive_qrel_ids":
                    list(
                        intervention
                        .omitted_positive_qrel_ids
                    ),
            },

            "evidence": [
                {
                    "source_id":
                        evidence.source_id,

                    "rank":
                        evidence.rank,

                    "selection_score":
                        evidence
                        .retrieval_score,
                }
                for evidence
                in result.evidence
            ],

            "answer": {
                "status":
                    result.answer.status,

                "claims": [
                    {
                        "text":
                            claim.text,

                        "sources":
                            list(
                                claim.sources
                            ),
                    }
                    for claim
                    in result.answer.claims
                ],

                "limitation":
                    result.answer.limitation,
            },

            "generation_attempts":
                result.generation_attempts,

            "latency_ms":
                latency_ms,

            "raw_model_output":
                result.raw_model_output,
        }

        items.append(
            item
        )

        completed_ids.add(
            query_id
        )

        save_checkpoint(
            metadata=metadata,
            items=items,
        )

    save_checkpoint(
        metadata=metadata,
        items=items,
    )

    print(
        "Saved qrel-enriched "
        "outputs to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

import hashlib
import json
import os
import time

from pathlib import Path

from dotenv import load_dotenv

from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)
from rootlens.rag.basic_rag import (
    BasicGroundedRAG,
)
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)
from rootlens.retrieval.frozen_multi_query_rrf import (
    FrozenMultiQueryRRFRetriever,
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

KNOWLEDGE_DIR = (
    BENCHMARK_DIR
    / "knowledge"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)

REWRITES_FILE = (
    BENCHMARK_DIR
    / "dev_rewrites_v1.json"
)

OUTPUT_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_semantic_v1.json"
)


DENSE_MODEL = (
    "BAAI/bge-small-en-v1.5"
)

TOP_K = 5

CANDIDATES_PER_QUERY = 10

RRF_K = 60

EXPECTED_REWRITES = 3


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256(
    path: Path,
) -> str:

    digest = (
        hashlib.sha256()
    )

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = (
                handle.read(
                    1024 * 1024
                )
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return (
        digest.hexdigest()
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


def load_visible_queries() -> list[
    dict
]:

    raw = load_json(
        DEV_FILE
    )

    if not isinstance(
        raw,
        list,
    ):

        raise RuntimeError(
            "DEV benchmark must "
            "be a JSON list."
        )

    visible = []

    for item in raw:

        visible.append(
            {
                "query_id":
                    item[
                        "query_id"
                    ],

                "category":
                    item[
                        "category"
                    ],

                "query":
                    item[
                        "query"
                    ],
            }
        )

    return visible


def load_rewrite_mapping() -> dict[
    str,
    list[str],
]:

    raw = load_json(
        REWRITES_FILE
    )

    entries = None

    if isinstance(
        raw,
        list,
    ):

        entries = raw

    elif isinstance(
        raw,
        dict,
    ):

        #
        # Accept the benchmark artifact
        # formats used during the previous
        # retrieval experiments.
        #
        for key in (
            "queries",
            "items",
            "rewrites",
        ):

            value = raw.get(
                key
            )

            if (
                isinstance(
                    value,
                    list,
                )
                and all(
                    isinstance(
                        item,
                        dict,
                    )
                    for item
                    in value
                )
            ):

                entries = value
                break

        if entries is None:

            candidate_mapping = {
                key:
                    value
                for key, value
                in raw.items()
                if isinstance(
                    value,
                    list,
                )
            }

            if (
                candidate_mapping
                and all(
                    all(
                        isinstance(
                            rewrite,
                            str,
                        )
                        for rewrite
                        in value
                    )
                    for value
                    in candidate_mapping.values()
                )
            ):

                mapping = (
                    candidate_mapping
                )

            else:

                mapping = None

        else:

            mapping = None

    else:

        mapping = None

    if entries is not None:

        mapping = {}

        for entry in entries:

            query = entry.get(
                "query"
            )

            rewrites = entry.get(
                "rewrites"
            )

            if not isinstance(
                query,
                str,
            ):

                raise RuntimeError(
                    "Rewrite entry has "
                    "invalid query."
                )

            if (
                not isinstance(
                    rewrites,
                    list,
                )
                or not all(
                    isinstance(
                        rewrite,
                        str,
                    )
                    for rewrite
                    in rewrites
                )
            ):

                raise RuntimeError(
                    "Rewrite entry has "
                    "invalid rewrites."
                )

            mapping[
                query
            ] = rewrites

    if not mapping:

        raise RuntimeError(
            "Could not parse frozen "
            "rewrite artifact."
        )

    return mapping


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

    queries = (
        load_visible_queries()
    )

    rewrites = (
        load_rewrite_mapping()
    )

    if len(
        queries
    ) != 24:

        raise RuntimeError(
            "Expected 24 DEV queries."
        )

    for item in queries:

        query = item[
            "query"
        ]

        if query not in rewrites:

            raise RuntimeError(
                "Missing frozen rewrites "
                f"for {item['query_id']}."
            )

        if len(
            rewrites[
                query
            ]
        ) != EXPECTED_REWRITES:

            raise RuntimeError(
                f"{item['query_id']} has "
                f"{len(rewrites[query])} "
                "rewrites; expected "
                f"{EXPECTED_REWRITES}."
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

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    semantic = (
        FrozenMultiQueryRRFRetriever(
            base_retriever=dense,
            rewrites=rewrites,
            candidates_per_query=(
                CANDIDATES_PER_QUERY
            ),
            rrf_k=RRF_K,
        )
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
        retriever=semantic,
        provider=provider,
        top_k=TOP_K,
        max_schema_retries=1,
    )

    metadata = {
        "experiment":
            "014F",

        "version":
            "v1",

        "condition":
            "semantic_multi_query_rrf",

        "query_file":
            DEV_FILE.name,

        "query_file_sha256":
            sha256(
                DEV_FILE
            ),

        "rewrite_file":
            REWRITES_FILE.name,

        "rewrite_file_sha256":
            sha256(
                REWRITES_FILE
            ),

        "rewrites_per_query":
            EXPECTED_REWRITES,

        "retrieval_queries_per_question":
            1
            + EXPECTED_REWRITES,

        "dense_model":
            DENSE_MODEL,

        "candidates_per_query":
            CANDIDATES_PER_QUERY,

        "rrf_k":
            RRF_K,

        "final_top_k":
            TOP_K,

        "retrieval_unit":
            "whole_document",

        "llm_model":
            model,

        "base_url":
            base_url,

        "rag_prompt_version":
            BasicGroundedRAG
            .PROMPT_VERSION,

        "qrels_used_for_retrieval":
            False,

        "qrels_visible_to_llm":
            False,

        "baseline_regenerated":
            False,
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

        for key in (
            "experiment",
            "version",
            "condition",
            "query_file_sha256",
            "rewrite_file_sha256",
            "dense_model",
            "candidates_per_query",
            "rrf_k",
            "final_top_k",
            "llm_model",
            "rag_prompt_version",
        ):

            if (
                existing_metadata.get(
                    key
                )
                != metadata.get(
                    key
                )
            ):

                raise RuntimeError(
                    "Existing checkpoint "
                    "metadata mismatch for "
                    f"{key!r}."
                )

        items = (
            existing.get(
                "items",
                []
            )
        )

        completed_ids = {
            item[
                "query_id"
            ]
            for item
            in items
        }

        print(
            "Resuming with "
            f"{len(completed_ids)} "
            "completed queries."
        )

        print()

    print(
        "Experiment 014F — "
        "Semantic Multi-Query RAG"
    )

    print(
        f"Documents: "
        f"{len(documents)}"
    )

    print(
        f"DEV queries: "
        f"{len(queries)}"
    )

    print(
        "Retrieval queries / question: "
        f"{1 + EXPECTED_REWRITES}"
    )

    print(
        "Candidate depth / retrieval: "
        f"{CANDIDATES_PER_QUERY}"
    )

    print(
        f"RRF k: {RRF_K}"
    )

    print(
        f"Final evidence budget: "
        f"top-{TOP_K}"
    )

    print(
        f"LLM: {model}"
    )

    print(
        "Qrels visible to LLM: False"
    )

    print()

    for index, item in enumerate(
        queries,
        start=1,
    ):

        query_id = (
            item[
                "query_id"
            ]
        )

        if query_id in completed_ids:

            print(
                f"[{index}/24] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        query = (
            item[
                "query"
            ]
        )

        expanded = (
            semantic.expanded_queries(
                query
            )
        )

        print(
            f"[{index}/24] "
            f"{query_id}"
        )

        print(
            f"  category: "
            f"{item['category']}"
        )

        print(
            f"  query: {query}"
        )

        print(
            f"  expanded queries: "
            f"{len(expanded)}"
        )

        retrieval_start = (
            time.perf_counter()
        )

        preview_ranking = (
            semantic.search(
                query,
                k=TOP_K,
            )
        )

        retrieval_latency_ms = (
            (
                time.perf_counter()
                - retrieval_start
            )
            * 1000.0
        )

        print(
            "  semantic top-5: "
            + ", ".join(
                document_id
                for document_id, _
                in preview_ranking
            )
        )

        generation_start = (
            time.perf_counter()
        )

        result = rag.answer(
            query
        )

        generation_latency_ms = (
            (
                time.perf_counter()
                - generation_start
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

        print(
            "  cited sources: "
            + ", ".join(
                sorted(
                    {
                        source
                        for claim
                        in result.answer.claims
                        for source
                        in claim.sources
                    }
                )
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
            "  generation attempts: "
            f"{result.generation_attempts}"
        )

        print(
            "  retrieval latency_ms: "
            f"{retrieval_latency_ms:.1f}"
        )

        print(
            "  RAG latency_ms: "
            f"{generation_latency_ms:.1f}"
        )

        print()

        frozen_item = {
            "query_id":
                query_id,

            "category":
                item[
                    "category"
                ],

            "query":
                query,

            "expanded_queries":
                expanded,

            "evidence": [
                {
                    "source_id":
                        evidence.source_id,

                    "rank":
                        evidence.rank,

                    "rrf_score":
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

            "retrieval_latency_ms":
                retrieval_latency_ms,

            "rag_latency_ms":
                generation_latency_ms,

            "raw_model_output":
                result.raw_model_output,
        }

        items.append(
            frozen_item
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
        "Saved frozen Semantic RAG "
        "outputs to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
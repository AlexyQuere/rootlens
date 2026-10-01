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

QUERIES_FILE = (
    BENCHMARK_DIR
    / "abstention_queries_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "abstention_outputs_v1.json"
)


TOP_K = 5

DENSE_MODEL = (
    "BAAI/bge-small-en-v1.5"
)


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
            f"Missing environment variable: "
            f"{name}"
        )

    return value


def save_checkpoint(
    metadata: dict,
    items: list[dict],
) -> None:

    output = {
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
            output,
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

    query_data = load_json(
        QUERIES_FILE
    )

    queries = query_data.get(
        "queries",
        []
    )

    if len(queries) != 18:
        raise RuntimeError(
            "Expected 18 abstention queries."
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

    metadata = {
        "experiment":
            "014D",

        "version":
            "v1",

        "query_file":
            QUERIES_FILE.name,

        "query_sha256":
            file_sha256(
                QUERIES_FILE
            ),

        "gold_loaded_during_generation":
            False,

        "llm_model":
            model,

        "base_url":
            base_url,

        "rag_prompt_version":
            BasicGroundedRAG
            .PROMPT_VERSION,

        "retriever":
            "dense",

        "dense_model":
            DENSE_MODEL,

        "retrieval_unit":
            "whole_document",

        "top_k":
            TOP_K,
    }

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
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
        retriever=dense,
        provider=provider,
        top_k=TOP_K,
        max_schema_retries=1,
    )

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
            "query_sha256",
            "llm_model",
            "rag_prompt_version",
            "top_k",
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
        "Experiment 014D — "
        "Abstention Benchmark"
    )

    print(
        f"documents={len(documents)} "
        f"| queries={len(queries)} "
        f"| top_k={TOP_K}"
    )

    print(
        f"LLM: {model}"
    )

    print(
        "Gold loaded during generation: "
        "False"
    )

    print()

    for index, example in enumerate(
        queries,
        start=1,
    ):

        query_id = (
            example[
                "query_id"
            ]
        )

        if query_id in completed_ids:

            print(
                f"[{index}/18] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        query = (
            example[
                "query"
            ]
        )

        print(
            f"[{index}/18] "
            f"{query_id}"
        )

        print(
            f"  pair: "
            f"{example['pair_id']}"
        )

        print(
            f"  variant: "
            f"{example['variant']}"
        )

        print(
            f"  question: {query}"
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
            "  evidence: "
            + ", ".join(
                evidence.source_id
                for evidence
                in result.evidence
            )
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

            "pair_id":
                example[
                    "pair_id"
                ],

            "variant":
                example[
                    "variant"
                ],

            "query":
                query,

            "evidence": [
                {
                    "source_id":
                        evidence.source_id,

                    "rank":
                        evidence.rank,

                    "retrieval_score":
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
        "Saved frozen abstention "
        "outputs to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
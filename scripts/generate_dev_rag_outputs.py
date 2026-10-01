import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.benchmark import (
    validate_benchmark,
)
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

KNOWLEDGE_DIR = (
    BENCHMARK_DIR
    / "knowledge"
)

DEV_FILE = (
    BENCHMARK_DIR
    / "dev_queries.json"
)

OUTPUT_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)


TOP_K = 5

DENSE_MODEL = (
    "BAAI/bge-small-en-v1.5"
)


def require_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:
        raise RuntimeError(
            f"Missing environment "
            f"variable: {name}"
        )

    return value


def load_documents():

    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):

        content = (
            path.read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if not content:
            raise ValueError(
                f"Empty document: "
                f"{path.name}"
            )

        documents[
            path.name
        ] = content

    return documents


def load_queries():

    return json.loads(
        DEV_FILE.read_text(
            encoding="utf-8"
        )
    )


def build_metadata(
    llm_model: str,
    base_url: str,
) -> dict:

    return {
        "rag_prompt_version":
            BasicGroundedRAG
            .PROMPT_VERSION,

        "llm_model":
            llm_model,

        "base_url":
            base_url,

        "retriever":
            "dense",

        "dense_model":
            DENSE_MODEL,

        "retrieval_unit":
            "whole_document",

        "top_k":
            TOP_K,
    }


def validate_existing_file(
    existing: dict,
    llm_model: str,
    base_url: str,
) -> None:

    metadata = existing.get(
        "metadata",
        {}
    )

    expected = build_metadata(
        llm_model=llm_model,
        base_url=base_url,
    )

    for key, expected_value in (
        expected.items()
    ):

        actual_value = (
            metadata.get(
                key
            )
        )

        if (
            actual_value
            != expected_value
        ):
            raise RuntimeError(
                "Existing RAG output file "
                "is incompatible with the "
                "current experiment.\n"
                f"Field: {key}\n"
                f"Existing: "
                f"{actual_value!r}\n"
                f"Expected: "
                f"{expected_value!r}"
            )


def save_checkpoint(
    items: list[dict],
    llm_model: str,
    base_url: str,
) -> None:

    output = {
        "metadata":
            build_metadata(
                llm_model=llm_model,
                base_url=base_url,
            ),

        "items":
            items,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def serialize_result(
    query_id: str,
    category: str,
    result,
    latency_ms: float,
) -> dict:

    return {
        "query_id":
            query_id,

        "query":
            result.question,

        "category":
            category,

        "evidence": [
            {
                "source_id":
                    evidence.source_id,

                "rank":
                    evidence.rank,

                "retrieval_score":
                    evidence.retrieval_score,
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

        "raw_model_output":
            result.raw_model_output,

        "generation_attempts":
            result.generation_attempts,

        "latency_ms":
            latency_ms,
    }


def main() -> None:

    documents = (
        load_documents()
    )

    queries = (
        load_queries()
    )

    validate_benchmark(
        documents,
        queries,
    )

    base_url = require_env(
        "ROOTLENS_LLM_BASE_URL"
    )

    api_key = require_env(
        "ROOTLENS_LLM_API_KEY"
    )

    llm_model = require_env(
        "ROOTLENS_LLM_MODEL"
    )

    provider = (
        OpenAICompatibleLLM(
            base_url=base_url,
            api_key=api_key,
            model=llm_model,
        )
    )

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    rag = BasicGroundedRAG(
        documents=documents,
        retriever=dense,
        provider=provider,
        top_k=TOP_K,
    )

    #
    # Resume only when the existing
    # artifact was generated with exactly
    # the same experiment configuration.
    #
    if OUTPUT_FILE.exists():

        existing = json.loads(
            OUTPUT_FILE.read_text(
                encoding="utf-8"
            )
        )

        validate_existing_file(
            existing=existing,
            llm_model=llm_model,
            base_url=base_url,
        )

        items = existing.get(
            "items",
            []
        )

        completed_ids = {
            item[
                "query_id"
            ]
            for item
            in items
        }

        print(
            f"Resuming with "
            f"{len(completed_ids)} "
            "queries already completed."
        )

    else:

        items = []
        completed_ids = set()

    print()
    print(
        "Experiment 014 — "
        "Basic Evidence-Grounded RAG"
    )

    print(
        f"DEV only | "
        f"documents={len(documents)} "
        f"| queries={len(queries)} "
        f"| top_k={TOP_K}"
    )

    print(
        "RAG prompt version: "
        f"{BasicGroundedRAG.PROMPT_VERSION}"
    )

    print(
        f"LLM: {llm_model}"
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

        query = (
            example[
                "query"
            ]
        )

        category = (
            example[
                "category"
            ]
        )

        if (
            query_id
            in completed_ids
        ):

            print(
                f"[{index}/{len(queries)}] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        print(
            f"[{index}/{len(queries)}] "
            f"{query_id}"
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
            time.perf_counter()
            - start
        ) * 1000.0

        print(
            "  evidence: "
            + ", ".join(
                evidence.source_id
                for evidence
                in result.evidence
            )
        )

        print(
            "  status: "
            f"{result.answer.status}"
        )

        print(
            "  claims: "
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
                f"{', '.join(claim.sources)}"
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
            "  latency="
            f"{latency_ms:.1f} ms"
        )

        item = (
            serialize_result(
                query_id=query_id,
                category=category,
                result=result,
                latency_ms=latency_ms,
            )
        )

        items.append(
            item
        )

        completed_ids.add(
            query_id
        )

        #
        # Checkpoint after every LLM call.
        #
        save_checkpoint(
            items=items,
            llm_model=llm_model,
            base_url=base_url,
        )

        print()

    #
    # Final save.
    #
    save_checkpoint(
        items=items,
        llm_model=llm_model,
        base_url=base_url,
    )

    status_counts = {
        "answered": 0,
        "partial": 0,
        "abstained": 0,
    }

    total_claims = 0
    total_latency = 0.0

    for item in items:

        status = (
            item[
                "answer"
            ][
                "status"
            ]
        )

        status_counts[
            status
        ] += 1

        total_claims += len(
            item[
                "answer"
            ][
                "claims"
            ]
        )

        total_latency += (
            item[
                "latency_ms"
            ]
        )

    print(
        "Saved frozen RAG outputs to:"
    )

    print(
        OUTPUT_FILE
    )

    print()

    print(
        "Generation summary:"
    )

    print(
        f"  queries="
        f"{len(items)}"
    )

    print(
        "  answered="
        f"{status_counts['answered']}"
    )

    print(
        "  partial="
        f"{status_counts['partial']}"
    )

    print(
        "  abstained="
        f"{status_counts['abstained']}"
    )

    print(
        f"  total_claims="
        f"{total_claims}"
    )

    if items:

        print(
            "  mean_claims/query="
            f"{total_claims / len(items):.2f}"
        )

        print(
            "  mean_latency_ms="
            f"{total_latency / len(items):.1f}"
        )


if __name__ == "__main__":
    main()
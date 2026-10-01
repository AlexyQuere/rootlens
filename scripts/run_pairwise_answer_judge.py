from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.pairwise_answer_judge import (
    PairwiseAnswerJudge,
)
from rootlens.llm.provider import (
    OpenAICompatibleLLM,
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

DENSE_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

SEMANTIC_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_semantic_v1.json"
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_documents():

    result = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):

        result[
            path.name
        ] = (
            path.read_text(
                encoding="utf-8"
            )
            .strip()
        )

    return result


def primary_dense_is_a(
    query_id: str,
) -> bool:

    digest = hashlib.sha256(
        query_id.encode(
            "utf-8"
        )
    ).digest()

    return (
        digest[
            0
        ]
        % 2
        == 0
    )


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--order",
        required=True,
        choices=[
            "primary",
            "reversed",
        ],
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args()


def main():

    args = parse_args()

    output_file = Path(
        args.output
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    documents = (
        load_documents()
    )

    queries = load_json(
        DEV_FILE
    )

    dense_data = load_json(
        DENSE_FILE
    )

    semantic_data = load_json(
        SEMANTIC_FILE
    )

    dense = {
        item[
            "query_id"
        ]:
            item
        for item
        in dense_data[
            "items"
        ]
    }

    semantic = {
        item[
            "query_id"
        ]:
            item
        for item
        in semantic_data[
            "items"
        ]
    }

    model = (
        os.getenv(
            "ROOTLENS_JUDGE_MODEL"
        )
        or os.getenv(
            "ROOTLENS_LLM_MODEL"
        )
    )

    base_url = (
        os.getenv(
            "ROOTLENS_JUDGE_BASE_URL"
        )
        or os.getenv(
            "ROOTLENS_LLM_BASE_URL"
        )
    )

    api_key = (
        os.getenv(
            "ROOTLENS_JUDGE_API_KEY"
        )
        or os.getenv(
            "ROOTLENS_LLM_API_KEY"
        )
    )

    if not all(
        [
            model,
            base_url,
            api_key,
        ]
    ):

        raise RuntimeError(
            "Missing judge provider "
            "configuration."
        )

    provider = (
        OpenAICompatibleLLM(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
    )

    judge = PairwiseAnswerJudge(
        provider,
        max_schema_retries=1,
    )

    existing_items = []

    if output_file.exists():

        existing = load_json(
            output_file
        )

        metadata = existing.get(
            "metadata",
            {}
        )

        if (
            metadata.get(
                "judge_model"
            )
            != model
            or metadata.get(
                "order"
            )
            != args.order
        ):

            raise RuntimeError(
                "Existing output metadata "
                "does not match this run."
            )

        existing_items = (
            existing.get(
                "items",
                []
            )
        )

    completed = {
        item[
            "query_id"
        ]
        for item
        in existing_items
    }

    items = list(
        existing_items
    )

    print(
        "Experiment 014F — "
        "Blind Pairwise Answer Judge"
    )

    print(
        f"Judge: {model}"
    )

    print(
        f"Order: {args.order}"
    )

    print(
        f"Queries: {len(queries)}"
    )

    print()

    for index, query in enumerate(
        queries,
        start=1,
    ):

        query_id = (
            query[
                "query_id"
            ]
        )

        if query_id in completed:

            print(
                f"[{index}/24] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        dense_item = (
            dense[
                query_id
            ]
        )

        semantic_item = (
            semantic[
                query_id
            ]
        )

        dense_is_a = (
            primary_dense_is_a(
                query_id
            )
        )

        if args.order == "reversed":

            dense_is_a = (
                not dense_is_a
            )

        if dense_is_a:

            answer_a_system = (
                "dense"
            )

            answer_b_system = (
                "semantic"
            )

            answer_a = dense_item[
                "answer"
            ]

            answer_b = semantic_item[
                "answer"
            ]

        else:

            answer_a_system = (
                "semantic"
            )

            answer_b_system = (
                "dense"
            )

            answer_a = semantic_item[
                "answer"
            ]

            answer_b = dense_item[
                "answer"
            ]

        dense_evidence = {
            evidence[
                "source_id"
            ]
            for evidence
            in dense_item[
                "evidence"
            ]
        }

        semantic_evidence = {
            evidence[
                "source_id"
            ]
            for evidence
            in semantic_item[
                "evidence"
            ]
        }

        reference_ids = sorted(
            dense_evidence
            | semantic_evidence
        )

        evidence = {
            source_id:
                documents[
                    source_id
                ]
            for source_id
            in reference_ids
        }

        context_changed = (
            dense_evidence
            != semantic_evidence
        )

        start = (
            time.perf_counter()
        )

        judgment = judge.judge(
            question=query[
                "query"
            ],
            answer_a=answer_a,
            answer_b=answer_b,
            evidence=evidence,
        )

        latency_ms = (
            (
                time.perf_counter()
                - start
            )
            * 1000.0
        )

        if (
            judgment.winner
            == "tie"
        ):

            preferred_system = (
                "tie"
            )

        elif (
            judgment.winner
            == "A"
        ):

            preferred_system = (
                answer_a_system
            )

        else:

            preferred_system = (
                answer_b_system
            )

        print(
            f"[{index}/24] "
            f"{query_id}"
        )

        print(
            f"  context_changed: "
            f"{context_changed}"
        )

        print(
            f"  winner: "
            f"{judgment.winner}"
        )

        print(
            f"  preferred system: "
            f"{preferred_system}"
        )

        print(
            f"  rationale: "
            f"{judgment.rationale}"
        )

        print()

        items.append(
            {
                "query_id":
                    query_id,

                "category":
                    query[
                        "category"
                    ],

                "context_changed":
                    context_changed,

                "answer_a_system":
                    answer_a_system,

                "answer_b_system":
                    answer_b_system,

                "winner":
                    judgment.winner,

                "preferred_system":
                    preferred_system,

                "material_difference":
                    (
                        judgment
                        .material_difference
                    ),

                "rationale":
                    judgment.rationale,

                "generation_attempts":
                    (
                        judgment
                        .generation_attempts
                    ),

                "latency_ms":
                    latency_ms,

                "raw_model_output":
                    (
                        judgment
                        .raw_model_output
                    ),
            }
        )

        artifact = {
            "metadata": {
                "experiment":
                    "014F",

                "evaluation":
                    "blind_pairwise",

                "judge_model":
                    model,

                "order":
                    args.order,

                "qrels_visible_to_judge":
                    False,

                "system_identity_visible_to_judge":
                    False,

                "reference_evidence":
                    (
                        "union of Dense and "
                        "Semantic top-5 evidence"
                    ),
            },

            "items":
                items,
        }

        output_file.write_text(
            json.dumps(
                artifact,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    print(
        "Saved to:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

import hashlib
import json

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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

DENSE_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

SEMANTIC_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_semantic_v1.json"
)

AGREEMENT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_judge_agreement_v1.json"
)

AUDIT_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_human_audit_v1.json"
)

KEY_FILE = (
    EVALUATION_DIR
    / "rag_pairwise_human_audit_key_v1.json"
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

    return documents


def dense_is_a(
    query_id: str,
) -> bool:

    value = (
        query_id
        + ":human-audit-v1"
    )

    digest = hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).digest()

    return (
        digest[0]
        % 2
        == 0
    )


def main() -> None:

    queries = load_json(
        DEV_FILE
    )

    dense_data = load_json(
        DENSE_FILE
    )

    semantic_data = load_json(
        SEMANTIC_FILE
    )

    agreement = load_json(
        AGREEMENT_FILE
    )

    documents = (
        load_documents()
    )

    query_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in queries
    }

    dense_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in dense_data[
            "items"
        ]
    }

    semantic_by_id = {
        item[
            "query_id"
        ]:
            item
        for item
        in semantic_data[
            "items"
        ]
    }

    candidates = (
        agreement[
            "audit_candidates"
        ]
    )

    candidate_ids = sorted(
        candidates
    )

    print(
        "Experiment 014F — "
        "Human Pairwise Audit"
    )

    print(
        f"Candidates: "
        f"{len(candidate_ids)}"
    )

    audit_items = []

    key_items = []

    for query_id in candidate_ids:

        query = (
            query_by_id[
                query_id
            ]
        )

        dense = (
            dense_by_id[
                query_id
            ]
        )

        semantic = (
            semantic_by_id[
                query_id
            ]
        )

        evidence_ids = sorted(
            {
                evidence[
                    "source_id"
                ]
                for evidence
                in dense[
                    "evidence"
                ]
            }
            |
            {
                evidence[
                    "source_id"
                ]
                for evidence
                in semantic[
                    "evidence"
                ]
            }
        )

        evidence = [
            {
                "source_id":
                    source_id,

                "content":
                    documents[
                        source_id
                    ],
            }
            for source_id
            in evidence_ids
        ]

        if dense_is_a(
            query_id
        ):

            answer_a = (
                dense[
                    "answer"
                ]
            )

            answer_b = (
                semantic[
                    "answer"
                ]
            )

            a_system = "dense"
            b_system = "semantic"

        else:

            answer_a = (
                semantic[
                    "answer"
                ]
            )

            answer_b = (
                dense[
                    "answer"
                ]
            )

            a_system = "semantic"
            b_system = "dense"

        audit_items.append(
            {
                "query_id":
                    query_id,

                "question":
                    query[
                        "query"
                    ],

                "evidence":
                    evidence,

                "answer_a":
                    answer_a,

                "answer_b":
                    answer_b,

                "human_label":
                    None,

                "human_rationale":
                    None,
            }
        )

        key_items.append(
            {
                "query_id":
                    query_id,

                "answer_a_system":
                    a_system,

                "answer_b_system":
                    b_system,

                "audit_reasons":
                    candidates[
                        query_id
                    ],
            }
        )

    audit_artifact = {
        "metadata": {
            "experiment":
                "014F",

            "evaluation":
                "targeted_blind_human_audit",

            "version":
                "v1",

            "candidate_count":
                len(
                    audit_items
                ),

            "system_identity_visible":
                False,

            "judge_outputs_visible":
                False,

            "reference_evidence":
                (
                    "union of Dense and "
                    "Semantic top-5 evidence"
                ),
        },

        "items":
            audit_items,
    }

    key_artifact = {
        "metadata": {
            "experiment":
                "014F",

            "evaluation":
                "human_audit_blind_key",

            "version":
                "v1",
        },

        "items":
            key_items,
    }

    AUDIT_FILE.write_text(
        json.dumps(
            audit_artifact,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    KEY_FILE.write_text(
        json.dumps(
            key_artifact,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Audit artifact:"
    )

    print(
        AUDIT_FILE
    )

    print()

    print(
        "Blind key:"
    )

    print(
        KEY_FILE
    )

    print()

    print(
        "Do not inspect the key "
        "before completing annotations."
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

import hashlib
import json
import random

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)


GROUNDING_FILE = (
    EVALUATION_DIR
    / "rag_grounding_dev_v1.json"
)

GEMMA_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_gemma_dev_v1.json"
)

QWEN_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_qwen_reasoning_dev_v1.json"
)

RAG_EVAL_FILE = (
    BENCHMARK_DIR
    / "dev_rag_eval_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_grounding_human_spotcheck_v1.json"
)


TARGET_SIZE = 10
SEED = 1402

DIFFICULT_CATEGORIES = {
    "multi_document",
    "troubleshooting",
}

LOGICAL_STRENGTH_MARKERS = (
    " must ",
    " always ",
    " only ",
    " proves ",
    " means ",
    " indicates ",
    " is caused by ",
    " root cause",
    " best ",
)


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


def annotation_id(
    annotation: dict,
) -> str:

    return (
        f"{annotation['query_id']}"
        f":claim-"
        f"{annotation['claim_index']:02d}"
    )


def items_by_id(
    data: dict,
) -> dict:

    result = {}

    for item in data.get(
        "items",
        []
    ):

        item_id = (
            item[
                "annotation_id"
            ]
        )

        if item_id in result:
            raise RuntimeError(
                "Duplicate annotation ID: "
                f"{item_id}"
            )

        result[
            item_id
        ] = item

    return result


def judge_label(
    item: dict,
) -> str:

    return (
        item[
            "judgment"
        ][
            "label"
        ]
    )


def supporting_sources(
    item: dict,
) -> set[str]:

    return set(
        item[
            "judgment"
        ].get(
            "supporting_sources",
            [],
        )
    )


def jaccard(
    left: set[str],
    right: set[str],
) -> float:

    union = (
        left
        | right
    )

    if not union:
        return 1.0

    return (
        len(
            left
            & right
        )
        / len(union)
    )


def logical_strength_score(
    claim: str,
) -> int:

    normalized = (
        " "
        + claim.lower()
        + " "
    )

    return sum(
        marker
        in normalized
        for marker
        in LOGICAL_STRENGTH_MARKERS
    )


def main() -> None:

    rng = random.Random(
        SEED
    )

    grounding = load_json(
        GROUNDING_FILE
    )

    gemma = items_by_id(
        load_json(
            GEMMA_FILE
        )
    )

    qwen = items_by_id(
        load_json(
            QWEN_FILE
        )
    )

    rag_eval = load_json(
        RAG_EVAL_FILE
    )

    if set(gemma) != set(qwen):
        raise RuntimeError(
            "Gemma and Qwen judge files "
            "do not contain the same claims."
        )

    qrel_risk_queries = {
        item[
            "query_id"
        ]
        for item
        in rag_eval.get(
            "queries",
            []
        )
        if item.get(
            "cited_qrel_irrelevant"
        )
    }

    annotations = {}

    for annotation in (
        grounding.get(
            "annotations",
            []
        )
    ):

        item_id = (
            annotation_id(
                annotation
            )
        )

        annotations[
            item_id
        ] = annotation

    if (
        set(annotations)
        != set(gemma)
    ):
        raise RuntimeError(
            "Grounding annotations and "
            "judge artifacts do not match."
        )

    #
    # First include ALL cross-judge
    # disagreements.
    #
    disagreement_ids = [
        item_id
        for item_id
        in sorted(
            annotations
        )
        if (
            judge_label(
                gemma[
                    item_id
                ]
            )
            != judge_label(
                qwen[
                    item_id
                ]
            )
        )
    ]

    if len(
        disagreement_ids
    ) > TARGET_SIZE:
        raise RuntimeError(
            "More disagreements than "
            "the spot-check target."
        )

    #
    # Score judge-agreement claims by
    # how useful they are for a
    # high-risk human audit.
    #
    candidates = []

    for item_id, annotation in (
        annotations.items()
    ):

        if item_id in (
            disagreement_ids
        ):
            continue

        gemma_item = (
            gemma[
                item_id
            ]
        )

        qwen_item = (
            qwen[
                item_id
            ]
        )

        if (
            judge_label(
                gemma_item
            )
            != judge_label(
                qwen_item
            )
        ):
            continue

        score = 0
        reasons = []

        category = (
            annotation[
                "category"
            ]
        )

        if category in (
            DIFFICULT_CATEGORIES
        ):

            score += 3

            reasons.append(
                "difficult_category"
            )

        if (
            annotation[
                "query_id"
            ]
            in qrel_risk_queries
        ):

            score += 2

            reasons.append(
                "qrel_citation_diagnostic"
            )

        citation_count = len(
            annotation[
                "citations"
            ]
        )

        if citation_count > 1:

            score += 1

            reasons.append(
                "multiple_citations"
            )

        source_jaccard = (
            jaccard(
                supporting_sources(
                    gemma_item
                ),
                supporting_sources(
                    qwen_item
                ),
            )
        )

        if source_jaccard < 1.0:

            score += 2

            reasons.append(
                "supporting_source_disagreement"
            )

        strength_score = (
            logical_strength_score(
                annotation[
                    "claim"
                ]
            )
        )

        if strength_score > 0:

            score += 2

            reasons.append(
                "strong_logical_language"
            )

        word_count = len(
            annotation[
                "claim"
            ].split()
        )

        if word_count >= 30:

            score += 1

            reasons.append(
                "long_or_compound_claim"
            )

        candidates.append(
            {
                "annotation_id":
                    item_id,

                "score":
                    score,

                "reasons":
                    reasons,

                "query_id":
                    annotation[
                        "query_id"
                    ],
            }
        )

    #
    # Randomize ties deterministically,
    # then sort by decreasing risk.
    #
    rng.shuffle(
        candidates
    )

    candidates.sort(
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    )

    selected_ids = list(
        disagreement_ids
    )

    selected_queries = {
        annotations[
            item_id
        ][
            "query_id"
        ]
        for item_id
        in selected_ids
    }

    #
    # Prefer one audited agreement
    # per query for diversity.
    #
    for candidate in candidates:

        if len(
            selected_ids
        ) >= TARGET_SIZE:
            break

        if (
            candidate[
                "query_id"
            ]
            in selected_queries
        ):
            continue

        selected_ids.append(
            candidate[
                "annotation_id"
            ]
        )

        selected_queries.add(
            candidate[
                "query_id"
            ]
        )

    #
    # Fallback if query diversity
    # prevented reaching 10.
    #
    if len(
        selected_ids
    ) < TARGET_SIZE:

        for candidate in candidates:

            if len(
                selected_ids
            ) >= TARGET_SIZE:
                break

            item_id = (
                candidate[
                    "annotation_id"
                ]
            )

            if item_id in selected_ids:
                continue

            selected_ids.append(
                item_id
            )

    if len(
        selected_ids
    ) != TARGET_SIZE:
        raise RuntimeError(
            "Could not construct "
            f"{TARGET_SIZE} spot checks."
        )

    #
    # Important:
    # randomize the human presentation
    # order so disagreement cases are
    # not identifiable from position.
    #
    rng.shuffle(
        selected_ids
    )

    human_items = []

    for item_id in selected_ids:

        annotation = (
            annotations[
                item_id
            ]
        )

        human_items.append(
            {
                "annotation_id":
                    item_id,

                "query_id":
                    annotation[
                        "query_id"
                    ],

                "claim_index":
                    annotation[
                        "claim_index"
                    ],

                "category":
                    annotation[
                        "category"
                    ],

                "query":
                    annotation[
                        "query"
                    ],

                "claim":
                    annotation[
                        "claim"
                    ],

                "citations":
                    annotation[
                        "citations"
                    ],

                #
                # No judge information is
                # exposed here.
                #
                "human_label":
                    None,

                "human_note":
                    "",
            }
        )

    output = {
        "metadata": {
            "version":
                "v1",

            "target_size":
                TARGET_SIZE,

            "seed":
                SEED,

            "selection":
                (
                    "All cross-judge "
                    "disagreements plus "
                    "high-risk judge-agreement "
                    "claims."
                ),

            "judge_labels_visible":
                False,

            "grounding_file":
                GROUNDING_FILE.name,

            "grounding_sha256":
                sha256(
                    GROUNDING_FILE
                ),

            "gemma_file":
                GEMMA_FILE.name,

            "gemma_sha256":
                sha256(
                    GEMMA_FILE
                ),

            "qwen_file":
                QWEN_FILE.name,

            "qwen_sha256":
                sha256(
                    QWEN_FILE
                ),

            "number_of_cross_judge_disagreements":
                len(
                    disagreement_ids
                ),
        },

        "items":
            human_items,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Experiment 014C — "
        "Human Spot-Check Sample"
    )

    print(
        f"Total spot checks: "
        f"{len(human_items)}"
    )

    print(
        "Cross-judge disagreements "
        "included: "
        f"{len(disagreement_ids)}"
    )

    print(
        "High-risk judge agreements "
        "included: "
        f"{TARGET_SIZE - len(disagreement_ids)}"
    )

    print(
        "Judge labels hidden: True"
    )

    print()

    print(
        "Saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
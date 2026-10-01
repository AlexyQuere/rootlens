from __future__ import annotations

import json

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AUDIT_FILE = (
    ROOT
    / "data"
    / "evaluation"
    / "rag_pairwise_human_audit_v1.json"
)


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def save_json(
    data: dict,
) -> None:

    temporary = (
        AUDIT_FILE.with_suffix(
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
        AUDIT_FILE
    )


def print_answer(
    title: str,
    answer: dict,
) -> None:

    print()
    print(
        title
    )

    print(
        "-" * len(
            title
        )
    )

    print(
        "status: "
        f"{answer['status']}"
    )

    for index, claim in enumerate(
        answer.get(
            "claims",
            []
        ),
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"{claim['text']}"
        )

        print(
            "   sources: "
            + ", ".join(
                claim[
                    "sources"
                ]
            )
        )

    limitation = (
        answer.get(
            "limitation"
        )
    )

    if limitation:

        print()

        print(
            "limitation: "
            f"{limitation}"
        )


def main() -> None:

    data = load_json(
        AUDIT_FILE
    )

    items = data[
        "items"
    ]

    remaining = [
        item
        for item
        in items
        if (
            item.get(
                "human_label"
            )
            is None
        )
    ]

    print(
        "RootLens 014F — "
        "Blind Human Pairwise Audit"
    )

    print()

    print(
        "Allowed labels:"
    )

    print(
        "  A = Answer A materially better"
    )

    print(
        "  B = Answer B materially better"
    )

    print(
        "  T = technically equivalent / tie"
    )

    print(
        "  I = genuinely inconclusive"
    )

    print()

    print(
        "Use A/B only for a meaningful "
        "technical advantage."
    )

    print(
        "Do not prefer an answer merely "
        "because it is longer."
    )

    print()

    print(
        f"Remaining: "
        f"{len(remaining)}"
        f"/{len(items)}"
    )

    for item in items:

        if (
            item.get(
                "human_label"
            )
            is not None
        ):
            continue

        print()
        print(
            "=" * 100
        )

        print(
            item[
                "query_id"
            ]
        )

        print()

        print(
            "QUESTION"
        )

        print(
            item[
                "question"
            ]
        )

        print()

        print(
            "REFERENCE EVIDENCE"
        )

        print(
            "-" * 100
        )

        for evidence in (
            item[
                "evidence"
            ]
        ):

            print()

            print(
                "[SOURCE: "
                f"{evidence['source_id']}"
                "]"
            )

            print(
                evidence[
                    "content"
                ]
            )

        print_answer(
            "ANSWER A",
            item[
                "answer_a"
            ],
        )

        print_answer(
            "ANSWER B",
            item[
                "answer_b"
            ],
        )

        print()

        while True:

            raw = input(
                "Your judgment "
                "[A/B/T/I/Q]: "
            ).strip().upper()

            if raw in {
                "A",
                "B",
                "T",
                "I",
                "Q",
            }:
                break

            print(
                "Invalid label."
            )

        if raw == "Q":

            print(
                "Stopping. Progress "
                "has been preserved."
            )

            break

        mapping = {
            "A":
                "A",

            "B":
                "B",

            "T":
                "tie",

            "I":
                "inconclusive",
        }

        rationale = input(
            "Short rationale: "
        ).strip()

        item[
            "human_label"
        ] = mapping[
            raw
        ]

        item[
            "human_rationale"
        ] = rationale

        save_json(
            data
        )

        print(
            "Saved."
        )

    remaining_after = sum(
        item.get(
            "human_label"
        )
        is None
        for item
        in items
    )

    print()

    print(
        f"Remaining: "
        f"{remaining_after}"
    )

    if remaining_after == 0:

        print(
            "Human audit complete."
        )


if __name__ == "__main__":
    main()
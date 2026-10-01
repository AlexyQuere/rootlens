from __future__ import annotations

import json

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SPOTCHECK_FILE = (
    ROOT
    / "data"
    / "evaluation"
    / "rag_grounding_human_spotcheck_v1.json"
)


LABELS = {
    "f": "full",
    "p": "partial",
    "n": "none",
}

VALID_LABELS = set(
    LABELS.values()
)


def load_data() -> dict:

    return json.loads(
        SPOTCHECK_FILE.read_text(
            encoding="utf-8"
        )
    )


def save_data(
    data: dict,
) -> None:

    temporary = (
        SPOTCHECK_FILE
        .with_suffix(
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
        SPOTCHECK_FILE
    )


def completed(
    items: list[dict],
) -> int:

    return sum(
        item.get(
            "human_label"
        )
        in VALID_LABELS
        for item
        in items
    )


def main() -> None:

    data = load_data()

    items = data.get(
        "items",
        []
    )

    if not items:
        raise RuntimeError(
            "No spot-check items found."
        )

    print()
    print(
        "RootLens — Human "
        "Grounding Spot Checks"
    )

    print(
        "Judge predictions are hidden."
    )

    print()

    print(
        "Question to answer:"
    )

    print(
        "Do the cited sources, taken "
        "together, support the ENTIRE claim?"
    )

    print()

    print(
        "f = full"
    )

    print(
        "p = partial"
    )

    print(
        "n = none"
    )

    print(
        "q = save and quit"
    )

    print()

    for index, item in enumerate(
        items,
        start=1,
    ):

        if (
            item.get(
                "human_label"
            )
            in VALID_LABELS
        ):
            continue

        print(
            "=" * 90
        )

        print(
            f"[{index}/{len(items)}]"
        )

        print(
            f"Category: "
            f"{item['category']}"
        )

        print()

        print(
            "QUESTION"
        )

        print(
            "-" * 90
        )

        print(
            item[
                "query"
            ]
        )

        print()

        print(
            "CLAIM"
        )

        print(
            "-" * 90
        )

        print(
            item[
                "claim"
            ]
        )

        print()

        print(
            "CITED EVIDENCE"
        )

        for citation_index, citation in enumerate(
            item[
                "citations"
            ],
            start=1,
        ):

            print()
            print(
                f"[{citation_index}] "
                f"{citation['source_id']}"
            )

            print(
                "-" * 90
            )

            print(
                citation[
                    "source_text"
                ]
            )

        while True:

            print()

            print(
                "Support for ENTIRE claim?"
            )

            print(
                "f=full  p=partial  "
                "n=none  q=quit"
            )

            value = (
                input(
                    "> "
                )
                .strip()
                .lower()
            )

            if value == "q":

                save_data(
                    data
                )

                print()

                print(
                    "Progress saved: "
                    f"{completed(items)}"
                    f"/{len(items)}"
                )

                return

            if value not in LABELS:

                print(
                    "Invalid choice."
                )

                continue

            item[
                "human_label"
            ] = (
                LABELS[
                    value
                ]
            )

            break

        if (
            item[
                "human_label"
            ]
            != "full"
        ):

            print()

            print(
                "Brief reason "
                "(optional, Enter to skip):"
            )

            item[
                "human_note"
            ] = (
                input(
                    "> "
                )
                .strip()
            )

        save_data(
            data
        )

        print()

        print(
            "Progress: "
            f"{completed(items)}"
            f"/{len(items)}"
        )

    print()
    print(
        "=" * 90
    )

    print(
        "Human spot-check complete."
    )

    print(
        f"{completed(items)}"
        f"/{len(items)} labelled."
    )


if __name__ == "__main__":
    main()
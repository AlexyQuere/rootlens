import json

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

KNOWLEDGE_DIR = (
    BENCHMARK_DIR
    / "knowledge"
)

RAG_OUTPUTS_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_grounding_dev_v1.json"
)


VALID_CLAIM_LABELS = {
    "full",
    "partial",
    "none",
}


VALID_CITATION_LABELS = {
    "full",
    "partial",
    "none",
}


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_documents():

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


def main() -> None:

    documents = (
        load_documents()
    )

    frozen = load_json(
        RAG_OUTPUTS_FILE
    )

    items = frozen.get(
        "items",
        []
    )

    annotations = []

    total_claims = 0
    total_citations = 0

    for item in items:

        query_id = (
            item[
                "query_id"
            ]
        )

        query = (
            item[
                "query"
            ]
        )

        category = (
            item[
                "category"
            ]
        )

        claims = (
            item[
                "answer"
            ][
                "claims"
            ]
        )

        for claim_index, claim in enumerate(
            claims,
            start=1,
        ):

            citations = []

            for source_id in (
                claim[
                    "sources"
                ]
            ):

                if (
                    source_id
                    not in documents
                ):
                    raise RuntimeError(
                        "Unknown cited source: "
                        f"{source_id}"
                    )

                citations.append(
                    {
                        "source_id":
                            source_id,

                        "source_text":
                            documents[
                                source_id
                            ],

                        "support":
                            None,

                        "note":
                            "",
                    }
                )

                total_citations += 1

            annotations.append(
                {
                    "query_id":
                        query_id,

                    "query":
                        query,

                    "category":
                        category,

                    "claim_index":
                        claim_index,

                    "claim":
                        claim[
                            "text"
                        ],

                    "claim_support":
                        None,

                    "claim_note":
                        "",

                    "citations":
                        citations,
                }
            )

            total_claims += 1

    output = {
        "metadata": {
            "version":
                "v1",

            "source_outputs":
                RAG_OUTPUTS_FILE.name,

            "claim_labels": [
                "full",
                "partial",
                "none",
            ],

            "citation_labels": [
                "full",
                "partial",
                "none",
            ],

            "instructions": {
                "claim_support":
                    (
                        "Judge whether the cited "
                        "sources collectively support "
                        "the entire claim."
                    ),

                "citation_support":
                    (
                        "Judge whether this individual "
                        "source supports the claim."
                    ),
            },
        },

        "annotations":
            annotations,
    }

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Grounding annotation template"
    )

    print(
        f"Claims: {total_claims}"
    )

    print(
        f"Citation links: "
        f"{total_citations}"
    )

    print(
        "Saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
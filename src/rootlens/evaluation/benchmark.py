from pathlib import Path


VALID_RELEVANCE_GRADES = {
    1,
    2,
}


def validate_benchmark(
    documents: dict[str, str],
    queries: list[dict],
) -> None:
    """Validate retrieval benchmark integrity."""

    if not documents:
        raise ValueError(
            "Benchmark corpus is empty."
        )

    for document_id, content in documents.items():
        if not content.strip():
            raise ValueError(
                f"Knowledge document is empty: "
                f"{document_id}"
            )

    query_ids = [
        example["query_id"]
        for example in queries
    ]

    if len(query_ids) != len(set(query_ids)):
        raise ValueError(
            "Duplicate query IDs detected."
        )

    for example in queries:
        query_id = example["query_id"]

        query = example.get(
            "query",
            "",
        ).strip()

        if not query:
            raise ValueError(
                f"Empty query: {query_id}"
            )

        relevance = example.get(
            "relevance",
            {},
        )

        if not relevance:
            raise ValueError(
                f"No relevance judgments: "
                f"{query_id}"
            )

        for document_id, grade in relevance.items():
            if document_id not in documents:
                raise ValueError(
                    f"{query_id} references missing "
                    f"document: {document_id}"
                )

            if grade not in VALID_RELEVANCE_GRADES:
                raise ValueError(
                    f"{query_id} has invalid "
                    f"relevance grade {grade} "
                    f"for {document_id}"
                )

def validate_query_split(
    dev_queries: list[dict],
    test_queries: list[dict],
) -> None:
    """Ensure that development and test queries do not overlap."""

    dev_ids = {
        query["query_id"]
        for query in dev_queries
    }

    test_ids = {
        query["query_id"]
        for query in test_queries
    }

    duplicate_ids = (
        dev_ids
        & test_ids
    )

    if duplicate_ids:
        raise ValueError(
            "Query IDs appear in both "
            "DEV and TEST: "
            + ", ".join(
                sorted(duplicate_ids)
            )
        )

    dev_texts = {
        query["query"].strip().lower()
        for query in dev_queries
    }

    test_texts = {
        query["query"].strip().lower()
        for query in test_queries
    }

    duplicate_queries = (
        dev_texts
        & test_texts
    )

    if duplicate_queries:
        raise ValueError(
            "Identical query text appears "
            "in both DEV and TEST."
        )
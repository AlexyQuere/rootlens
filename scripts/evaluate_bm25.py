import json
from pathlib import Path

from rootlens.evaluation.retrieval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rootlens.retrieval.bm25_retriever import (
    BM25Retriever,
)


ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = ROOT / "data" / "knowledge"

EVALUATION_FILE = (
    ROOT
    / "data"
    / "evaluation"
    / "retrieval_queries.json"
)


def load_documents() -> dict[str, str]:
    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob("*.md")
    ):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                f"Knowledge document is empty: "
                f"{path.name}"
            )

        documents[path.name] = content

    return documents


def load_queries() -> list[dict]:
    return json.loads(
        EVALUATION_FILE.read_text(
            encoding="utf-8"
        )
    )


def validate_evaluation(
    documents: dict[str, str],
    queries: list[dict],
) -> None:
    missing = {
        document_id
        for example in queries
        for document_id
        in example["relevant_documents"]
        if document_id not in documents
    }

    if missing:
        raise ValueError(
            "Missing relevant documents: "
            + ", ".join(sorted(missing))
        )


def main() -> None:
    documents = load_documents()
    queries = load_queries()

    validate_evaluation(
        documents,
        queries,
    )

    retriever = BM25Retriever(documents)

    precision_1_scores = []
    recall_1_scores = []
    recall_3_scores = []
    reciprocal_ranks = []

    for example in queries:
        relevant = set(
            example["relevant_documents"]
        )

        results = retriever.search(
            example["query"],
            k=3,
        )

        retrieved = [
            document_id
            for document_id, _ in results
        ]

        precision_1_scores.append(
            precision_at_k(
                retrieved,
                relevant,
                k=1,
            )
        )

        recall_1_scores.append(
            recall_at_k(
                retrieved,
                relevant,
                k=1,
            )
        )

        recall_3_scores.append(
            recall_at_k(
                retrieved,
                relevant,
                k=3,
            )
        )

        reciprocal_ranks.append(
            reciprocal_rank(
                retrieved,
                relevant,
            )
        )

        print()
        print(
            f'{example["query_id"]}: '
            f'{example["query"]}'
        )

        print(
            f'Relevant: {sorted(relevant)}'
        )

        print("Retrieved:")

        for rank, (
            document_id,
            score,
        ) in enumerate(results, start=1):
            print(
                f"  {rank}. "
                f"{document_id} "
                f"({score:.4f})"
            )

    n = len(queries)

    print()
    print("=== BM25 baseline ===")

    print(
        "Precision@1:",
        sum(precision_1_scores) / n,
    )

    print(
        "Recall@1:",
        sum(recall_1_scores) / n,
    )

    print(
        "Recall@3:",
        sum(recall_3_scores) / n,
    )

    print(
        "MRR@3:",
        sum(reciprocal_ranks) / n,
    )


if __name__ == "__main__":
    main()
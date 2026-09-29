import json
from pathlib import Path

from rootlens.evaluation.retrieval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rootlens.retrieval.tfidf_retriever import TfidfRetriever


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

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            raise ValueError(
                f"Knowledge document is empty: {path.name}"
            )

        documents[path.name] = content

    return documents


def load_queries() -> list[dict]:
    return json.loads(
        EVALUATION_FILE.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:
    documents = load_documents()
    queries = load_queries()
    missing_relevant_documents = {
        document_id
        for example in queries
        for document_id in example["relevant_documents"]
        if document_id not in documents
    }

    if missing_relevant_documents:
        missing = ", ".join(
            sorted(missing_relevant_documents)
        )

        raise ValueError(
            "Evaluation references documents that are "
            f"missing from the knowledge corpus: {missing}"
        )

    retriever = TfidfRetriever(documents)

    precision_1_scores = []
    recall_1_scores = []
    recall_3_scores = []
    reciprocal_ranks = []

    for example in queries:
        query = example["query"]

        relevant = set(
            example["relevant_documents"]
        )

        results = retriever.search(
            query,
            k=3,
        )

        retrieved = [
            document_id
            for document_id, _ in results
        ]

        p1 = precision_at_k(
            retrieved,
            relevant,
            k=1,
        )

        r1 = recall_at_k(
            retrieved,
            relevant,
            k=1,
        )

        r3 = recall_at_k(
            retrieved,
            relevant,
            k=3,
        )

        rr = reciprocal_rank(
            retrieved,
            relevant,
        )

        precision_1_scores.append(p1)
        recall_1_scores.append(r1)
        recall_3_scores.append(r3)
        reciprocal_ranks.append(rr)

        print()
        print(
            f'{example["query_id"]}: {query}'
        )

        print(
            f'Relevant: '
            f'{sorted(relevant)}'
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

    number_of_queries = len(queries)

    print()
    print("=== TF-IDF baseline ===")

    print(
        "Precision@1:",
        sum(precision_1_scores)
        / number_of_queries,
    )

    print(
        "Recall@1:",
        sum(recall_1_scores)
        / number_of_queries,
    )

    print(
        "Recall@3:",
        sum(recall_3_scores)
        / number_of_queries,
    )

    print(
        "MRR@3:",
        sum(reciprocal_ranks)
        / number_of_queries,
    )



if __name__ == "__main__":
    main()
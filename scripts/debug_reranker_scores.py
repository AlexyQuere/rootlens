import json
import statistics
from pathlib import Path

from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)
from rootlens.retrieval.reranker import (
    CrossEncoderReranker,
)


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data" / "benchmark_v2"
KNOWLEDGE_DIR = BENCHMARK_DIR / "knowledge"
DEV_FILE = BENCHMARK_DIR / "dev_queries.json"


def load_documents() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8").strip()
        for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
    }


def load_queries() -> list[dict]:
    return json.loads(
        DEV_FILE.read_text(encoding="utf-8")
    )


def rerank_one(
    query: str,
    dense_results: list[tuple[str, float]],
    documents: dict[str, str],
    reranker: CrossEncoderReranker,
):
    candidate_ids = [
        document_id
        for document_id, _ in dense_results
    ]

    texts = [
        documents[document_id]
        for document_id in candidate_ids
    ]

    ce_scores = reranker.score(
        query,
        texts,
    )

    rows = [
        (
            dense_rank,
            document_id,
            dense_score,
            ce_score,
        )
        for dense_rank, (
            (document_id, dense_score),
            ce_score,
        ) in enumerate(
            zip(
                dense_results,
                ce_scores,
            ),
            start=1,
        )
    ]

    reranked = sorted(
        rows,
        key=lambda row: (
            -row[3],
            row[1],
        ),
    )

    return rows, reranked


def main() -> None:
    documents = load_documents()
    queries = load_queries()

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    reranker = CrossEncoderReranker()

    changed_top3 = 0
    changed_top5 = 0
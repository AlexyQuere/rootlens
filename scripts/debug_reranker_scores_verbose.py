import json
import statistics
import sys
from pathlib import Path


def log(message: str) -> None:
    print(message, flush=True)


log("[1/7] Script started")

try:
    from rootlens.retrieval.dense_retriever import (
        BGEEncoder,
        DenseRetriever,
    )
    from rootlens.retrieval.reranker import (
        CrossEncoderReranker,
    )
except Exception as exc:
    log(f"[ERROR] Import failed: {exc!r}")
    raise


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data" / "benchmark_v2"
KNOWLEDGE_DIR = BENCHMARK_DIR / "knowledge"
DEV_FILE = BENCHMARK_DIR / "dev_queries.json"


def load_documents() -> dict[str, str]:
    documents = {
        path.name: path.read_text(encoding="utf-8").strip()
        for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
    }

    if not documents:
        raise RuntimeError(
            f"No Markdown documents found in {KNOWLEDGE_DIR}"
        )

    return documents


def load_queries() -> list[dict]:
    if not DEV_FILE.exists():
        raise RuntimeError(
            f"DEV query file not found: {DEV_FILE}"
        )

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
    log(f"[2/7] Repository root: {ROOT}")

    documents = load_documents()
    queries = load_queries()

    log(
        f"[3/7] Loaded {len(documents)} documents "
        f"and {len(queries)} DEV queries"
    )

    log("[4/7] Loading BGE encoder...")
    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )
    log("[4/7] BGE encoder ready")

    log("[5/7] Loading cross-encoder...")
    reranker = CrossEncoderReranker()
    log(
        "[5/7] Cross-encoder ready: "
        f"{reranker.model_name}"
    )

    changed_top3 = 0
    changed_top5 = 0
    changed_top10 = 0

    diagnostic_ids = {
        "dev-011",
        "dev-021",
    }

    log("[6/7] Scoring DEV queries...")

    for index, example in enumerate(
        queries,
        start=1,
    ):
        if index == 1 or index % 5 == 0:
            log(
                f"  processing query "
                f"{index}/{len(queries)} "
                f"({example['query_id']})"
            )

        dense_results = dense.search(
            example["query"],
            k=10,
        )

        rows, reranked = rerank_one(
            example["query"],
            dense_results,
            documents,
            reranker,
        )

        dense_order = [
            document_id
            for document_id, _
            in dense_results
        ]

        reranked_order = [
            row[1]
            for row in reranked
        ]

        if dense_order[:3] != reranked_order[:3]:
            changed_top3 += 1

        if dense_order[:5] != reranked_order[:5]:
            changed_top5 += 1

        if dense_order != reranked_order:
            changed_top10 += 1

        if example["query_id"] not in diagnostic_ids:
            continue

        print()
        log(
            f"{example['query_id']}: "
            f"{example['query']}"
        )

        print(
            f"{'dense':>5} "
            f"{'document':<34} "
            f"{'dense_score':>12} "
            f"{'ce_score':>12}",
            flush=True,
        )

        print("-" * 70, flush=True)

        for (
            dense_rank,
            document_id,
            dense_score,
            ce_score,
        ) in rows:
            print(
                f"{dense_rank:>5} "
                f"{document_id:<34} "
                f"{dense_score:>12.6f} "
                f"{ce_score:>12.6f}",
                flush=True,
            )

        ce_scores = [
            row[3]
            for row in rows
        ]

        print()
        log("Dense order:")
        for rank, document_id in enumerate(
            dense_order,
            start=1,
        ):
            log(
                f"  {rank:>2}. {document_id}"
            )

        print()
        log("Cross-encoder order:")
        for rank, row in enumerate(
            reranked,
            start=1,
        ):
            log(
                f"  {rank:>2}. "
                f"{row[1]} "
                f"(score={row[3]:.6f})"
            )

        print()
        log(
            "Cross-encoder score range: "
            f"{min(ce_scores):.6f} "
            f"to {max(ce_scores):.6f}"
        )
        log(
            "Cross-encoder score std: "
            f"{statistics.pstdev(ce_scores):.6f}"
        )

    print()
    log("[7/7] Ranking-change summary")
    log(
        f"Top-3 changed:  "
        f"{changed_top3}/{len(queries)}"
    )
    log(
        f"Top-5 changed:  "
        f"{changed_top5}/{len(queries)}"
    )
    log(
        f"Top-10 changed: "
        f"{changed_top10}/{len(queries)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"\n[FATAL] {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise

import math

def precision_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int,
) -> float:
    """Compute Precision@k."""

    if k <= 0:
        raise ValueError("k must be strictly positive.")

    top_k = retrieved[:k]

    relevant_retrieved = sum(
        document_id in relevant
        for document_id in top_k
    )

    return relevant_retrieved / k


def recall_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int,
) -> float:
    """Compute Recall@k."""

    if k <= 0:
        raise ValueError("k must be strictly positive.")

    if not relevant:
        return 0.0

    top_k = retrieved[:k]

    relevant_retrieved = sum(
        document_id in relevant
        for document_id in top_k
    )

    return relevant_retrieved / len(relevant)


def reciprocal_rank(
    retrieved: list[str],
    relevant: set[str],
) -> float:
    """Compute reciprocal rank for one query."""

    for rank, document_id in enumerate(
        retrieved,
        start=1,
    ):
        if document_id in relevant:
            return 1.0 / rank

    return 0.0

def dcg_at_k(
    retrieved: list[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    """Compute Discounted Cumulative Gain at k."""

    if k <= 0:
        raise ValueError(
            "k must be strictly positive."
        )

    score = 0.0

    for rank, document_id in enumerate(
        retrieved[:k],
        start=1,
    ):
        grade = relevance.get(
            document_id,
            0,
        )

        gain = (2 ** grade) - 1

        discount = math.log2(
            rank + 1
        )

        score += gain / discount

    return score


def ndcg_at_k(
    retrieved: list[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    """Compute normalized DCG at k."""

    if k <= 0:
        raise ValueError(
            "k must be strictly positive."
        )

    actual_dcg = dcg_at_k(
        retrieved,
        relevance,
        k,
    )

    ideal_grades = sorted(
        relevance.values(),
        reverse=True,
    )[:k]

    ideal_dcg = 0.0

    for rank, grade in enumerate(
        ideal_grades,
        start=1,
    ):
        gain = (2 ** grade) - 1

        discount = math.log2(
            rank + 1
        )

        ideal_dcg += gain / discount

    if ideal_dcg == 0.0:
        return 0.0

    return actual_dcg / ideal_dcg
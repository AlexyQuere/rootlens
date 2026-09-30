import math

import torch

from rootlens.retrieval.reranker import (
    BGEReranker,
)


def choose_device() -> str:
    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


def main() -> None:
    device = choose_device()

    print(
        f"Selected device: {device}"
    )

    reranker = BGEReranker(
        device=device,
        batch_size=2,
    )

    query = (
        "Which service calculates delivery "
        "cost before the customer is charged?"
    )

    documents = [
        (
            "ShippingService calculates "
            "delivery quotes and shipping cost "
            "during checkout."
        ),
        (
            "PaymentService charges the customer "
            "after checkout computes the total."
        ),
        (
            "The frontend renders the checkout "
            "page for the customer."
        ),
    ]

    scores = reranker.score(
        query,
        documents,
    )

    print()
    print("Scores:")

    for document, score in zip(
        documents,
        scores,
    ):
        print(
            f"{score:.6f} | {document}"
        )

        assert math.isfinite(
            score
        )

    ranking = sorted(
        zip(
            documents,
            scores,
        ),
        key=lambda item: -item[1],
    )

    print()
    print("Ranking:")

    for rank, (
        document,
        score,
    ) in enumerate(
        ranking,
        start=1,
    ):
        print(
            f"{rank}. "
            f"score={score:.6f} "
            f"| {document}"
        )


if __name__ == "__main__":
    main()
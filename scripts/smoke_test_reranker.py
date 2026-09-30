import torch

from rootlens.retrieval.reranker import (
    CrossEncoderReranker,
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
        f"Selected device: {device}",
        flush=True,
    )

    reranker = CrossEncoderReranker(
        device=device,
    )

    query = (
        "Which service calculates delivery "
        "cost before the customer is charged?"
    )

    documents = [
        (
            "The Shipping service calculates "
            "delivery quotes and delivery cost."
        ),
        (
            "PaymentService charges the customer "
            "after checkout computes the total."
        ),
        (
            "The frontend renders the checkout page."
        ),
    ]

    scores = reranker.score(
        query,
        documents,
    )

    print(
        "Scores:",
        scores,
        flush=True,
    )

    ranking = sorted(
        zip(
            documents,
            scores,
        ),
        key=lambda item: -item[1],
    )

    print(
        "Ranking:",
        flush=True,
    )

    for rank, (
        document,
        score,
    ) in enumerate(
        ranking,
        start=1,
    ):
        print(
            f"{rank}. score={score:.6f} "
            f"| {document}",
            flush=True,
        )


if __name__ == "__main__":
    main()

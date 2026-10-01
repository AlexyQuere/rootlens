import argparse
import os

from pathlib import Path

from dotenv import load_dotenv

from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)
from rootlens.rag.basic_rag import (
    BasicGroundedRAG,
)
from rootlens.retrieval.dense_retriever import (
    BGEEncoder,
    DenseRetriever,
)


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


KNOWLEDGE_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
    / "knowledge"
)


TOP_K = 5


def require_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:
        raise RuntimeError(
            f"Missing environment "
            f"variable: {name}"
        )

    return value


def load_documents():

    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):

        content = (
            path.read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if not content:
            raise ValueError(
                f"Empty document: "
                f"{path.name}"
            )

        documents[
            path.name
        ] = content

    return documents


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "question",
        type=str,
    )

    args = (
        parser.parse_args()
    )

    documents = (
        load_documents()
    )

    dense = DenseRetriever(
        documents,
        encoder=BGEEncoder(),
    )

    provider = (
        OpenAICompatibleLLM(
            base_url=require_env(
                "ROOTLENS_LLM_BASE_URL"
            ),
            api_key=require_env(
                "ROOTLENS_LLM_API_KEY"
            ),
            model=require_env(
                "ROOTLENS_LLM_MODEL"
            ),
        )
    )

    rag = BasicGroundedRAG(
        documents=documents,
        retriever=dense,
        provider=provider,
        top_k=TOP_K,
    )

    result = rag.answer(
        args.question
    )

    print()
    print(
        "=== Retrieved Evidence ==="
    )

    for item in (
        result.evidence
    ):

        print(
            f"{item.rank}. "
            f"{item.source_id} "
            f"(score="
            f"{item.retrieval_score:.4f})"
        )

    print()
    print(
        "=== Answer ==="
    )

    print(
        f"status: "
        f"{result.answer.status}"
    )

    for index, claim in enumerate(
        result.answer.claims,
        start=1,
    ):

        print()
        print(
            f"{index}. "
            f"{claim.text}"
        )

        print(
            "   sources: "
            f"{', '.join(claim.sources)}"
        )

    if (
        result.answer.limitation
        is not None
    ):

        print()
        print(
            "limitation: "
            f"{result.answer.limitation}"
        )


if __name__ == "__main__":
    main()
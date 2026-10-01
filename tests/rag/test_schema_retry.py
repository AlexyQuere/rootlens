import pytest

from rootlens.rag.basic_rag import (
    BasicGroundedRAG,
    RAGCitationError,
    RAGSchemaError,
)


DOCUMENTS = {
    "payment-service.md":
        (
            "PaymentService handles "
            "payment charging."
        ),

    "grpc-troubleshooting.md":
        (
            "A client span with no "
            "corresponding server span "
            "can indicate the request "
            "did not reach the downstream "
            "service."
        ),
}


class CountingRetriever:

    def __init__(
        self,
        ranking,
    ):

        self.ranking = ranking
        self.calls = 0

    def search(
        self,
        query,
        k,
    ):

        self.calls += 1

        return (
            self.ranking[
                :k
            ]
        )


class SequenceProvider:

    def __init__(
        self,
        responses,
    ):

        self.responses = list(
            responses
        )

        self.calls = 0

        self.prompts = []

    def generate(
        self,
        system_prompt,
        user_prompt,
        *,
        max_tokens,
        temperature,
    ):

        self.calls += 1

        self.prompts.append(
            (
                system_prompt,
                user_prompt,
            )
        )

        if (
            self.calls
            > len(
                self.responses
            )
        ):
            raise AssertionError(
                "Provider called more "
                "times than expected."
            )

        return (
            self.responses[
                self.calls - 1
            ]
        )


def build_rag(
    responses,
):

    retriever = (
        CountingRetriever(
            [
                (
                    "payment-service.md",
                    0.91,
                ),
                (
                    "grpc-troubleshooting.md",
                    0.84,
                ),
            ]
        )
    )

    provider = (
        SequenceProvider(
            responses
        )
    )

    rag = BasicGroundedRAG(
        documents=DOCUMENTS,
        retriever=retriever,
        provider=provider,
        top_k=2,
        max_schema_retries=1,
    )

    return (
        rag,
        retriever,
        provider,
    )


def test_schema_failure_is_retried_once():

    invalid_response = """
    {
      "status": "answered",
      "claims": [
        "PaymentService handles payment charging."
      ],
      "limitation": null
    }
    """

    repaired_response = """
    {
      "status": "answered",
      "claims": [
        {
          "text": "PaymentService handles payment charging.",
          "sources": [
            "payment-service.md"
          ]
        }
      ],
      "limitation": null
    }
    """

    (
        rag,
        retriever,
        provider,
    ) = build_rag(
        [
            invalid_response,
            repaired_response,
        ]
    )

    result = rag.answer(
        "Who handles payment charging?"
    )

    assert (
        result.answer.status
        == "answered"
    )

    assert (
        result.generation_attempts
        == 2
    )

    assert (
        provider.calls
        == 2
    )

    #
    # Retrieval must not be repeated.
    #
    assert (
        retriever.calls
        == 1
    )

    assert (
        result.answer.claims[
            0
        ].sources
        == (
            "payment-service.md",
        )
    )


def test_unknown_source_is_not_retried():

    invented_source_response = """
    {
      "status": "answered",
      "claims": [
        {
          "text": "A database stores payments.",
          "sources": [
            "database.md"
          ]
        }
      ],
      "limitation": null
    }
    """

    (
        rag,
        retriever,
        provider,
    ) = build_rag(
        [
            invented_source_response,
        ]
    )

    with pytest.raises(
        RAGCitationError,
        match="not retrieved",
    ):

        rag.answer(
            "Where are payments stored?"
        )

    assert (
        provider.calls
        == 1
    )

    assert (
        retriever.calls
        == 1
    )


def test_second_schema_failure_is_raised():

    invalid_response_1 = """
    {
      "status": "answered",
      "claims": [
        "PaymentService handles payment charging."
      ],
      "limitation": null
    }
    """

    invalid_response_2 = """
    {
      "status": "answered",
      "claims": [
        "PaymentService handles payment charging."
      ],
      "limitation": null
    }
    """

    (
        rag,
        retriever,
        provider,
    ) = build_rag(
        [
            invalid_response_1,
            invalid_response_2,
        ]
    )

    with pytest.raises(
        RAGSchemaError,
        match="must be a JSON object",
    ):

        rag.answer(
            "Who handles payments?"
        )

    assert (
        provider.calls
        == 2
    )

    assert (
        retriever.calls
        == 1
    )


def test_retry_prompt_contains_validation_error():

    invalid_response = """
    {
      "status": "answered",
      "claims": [
        "PaymentService handles payment charging."
      ],
      "limitation": null
    }
    """

    repaired_response = """
    {
      "status": "answered",
      "claims": [
        {
          "text": "PaymentService handles payment charging.",
          "sources": [
            "payment-service.md"
          ]
        }
      ],
      "limitation": null
    }
    """

    (
        rag,
        _,
        provider,
    ) = build_rag(
        [
            invalid_response,
            repaired_response,
        ]
    )

    rag.answer(
        "Who handles payments?"
    )

    assert (
        provider.calls
        == 2
    )

    retry_system_prompt = (
        provider.prompts[
            1
        ][
            0
        ]
    )

    retry_user_prompt = (
        provider.prompts[
            1
        ][
            1
        ]
    )

    assert (
        "repairing a structured"
        in retry_system_prompt
    )

    assert (
        "VALIDATION ERROR"
        in retry_user_prompt
    )

    assert (
        "Each claim must be "
        "a JSON object"
        in retry_user_prompt
    )
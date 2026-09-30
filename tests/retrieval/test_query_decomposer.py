import pytest

from rootlens.retrieval.query_decomposer import (
    LLMQueryDecomposer,
    StaticQueryDecomposer,
)


class FakeProvider:

    def __init__(
        self,
        response: str,
    ) -> None:
        self.response = response

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 384,
        temperature: float = 0.0,
    ) -> str:
        return self.response


def test_decomposer_parses_subqueries():

    provider = FakeProvider(
        """
        [
          "Which metric detects checkout errors?",
          "Which traces localize the failing dependency?",
          "Which logs provide request-level evidence?"
        ]
        """
    )

    decomposer = (
        LLMQueryDecomposer(
            provider
        )
    )

    result = decomposer.decompose(
        (
            "How should I investigate "
            "checkout errors?"
        ),
        n=3,
    )

    assert len(result) == 3


def test_decomposition_preserves_identifier_somewhere():

    provider = FakeProvider(
        """
        [
          "What does rpc.response.status_code UNAVAILABLE indicate?",
          "Which trace evidence shows whether the server received the request?",
          "Which network evidence distinguishes transport failure?"
        ]
        """
    )

    decomposer = (
        LLMQueryDecomposer(
            provider
        )
    )

    result = decomposer.decompose(
        (
            "How should I investigate "
            "rpc.response.status_code "
            "UNAVAILABLE?"
        ),
        n=3,
    )

    combined = " ".join(result)

    assert (
        "rpc.response.status_code"
        in combined
    )

    assert (
        "UNAVAILABLE"
        in combined
    )


def test_missing_identifier_is_rejected():

    provider = FakeProvider(
        """
        [
          "Which trace evidence should be inspected?",
          "Which logs explain the failure?",
          "Which network symptoms matter?"
        ]
        """
    )

    decomposer = (
        LLMQueryDecomposer(
            provider,
            max_attempts=1,
        )
    )

    with pytest.raises(
        ValueError
    ):
        decomposer.decompose(
            (
                "Why is "
                "rpc.response.status_code "
                "UNAVAILABLE?"
            ),
            n=3,
        )


def test_static_decomposer_is_deterministic():

    mapping = {
        "query": [
            "subquery one",
            "subquery two",
            "subquery three",
        ]
    }

    decomposer = (
        StaticQueryDecomposer(
            mapping
        )
    )

    first = decomposer.decompose(
        "query"
    )

    second = decomposer.decompose(
        "query"
    )

    assert first == second

def test_atomic_query_can_return_one_subquery():

    provider = FakeProvider(
        """
        [
          "Which service owns oteldemo.PaymentService/Charge?"
        ]
        """
    )

    decomposer = (
        LLMQueryDecomposer(
            provider
        )
    )

    result = decomposer.decompose(
        (
            "Which service is responsible "
            "for the "
            "oteldemo.PaymentService/Charge "
            "operation?"
        ),
        n=3,
    )

    assert len(result) == 1

    assert (
        "oteldemo.PaymentService/Charge"
        in result[0]
    )

def test_static_decomposer_accepts_fewer_than_maximum():

    decomposer = (
        StaticQueryDecomposer(
            {
                "atomic query": [
                    "atomic subquery"
                ]
            }
        )
    )

    result = decomposer.decompose(
        "atomic query",
        n=3,
    )

    assert result == [
        "atomic subquery"
    ]
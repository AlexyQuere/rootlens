import pytest

from rootlens.retrieval.query_rewriter import (
    LLMQueryRewriter,
    StaticQueryRewriter,
    extract_identifiers,
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
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> str:
        return self.response


def test_extract_identifiers():

    query = (
        "rpc.response.status_code is "
        "UNAVAILABLE for "
        "PaymentService/Charge"
    )

    identifiers = (
        extract_identifiers(
            query
        )
    )

    assert (
        "rpc.response.status_code"
        in identifiers
    )

    assert (
        "UNAVAILABLE"
        in identifiers
    )

    assert (
        "PaymentService/Charge"
        in identifiers
    )


def test_llm_query_rewriter_parses_json():

    provider = FakeProvider(
        """
        [
          "How do services correlate logs?",
          "How are logs linked across services?",
          "How can distributed logs be associated?"
        ]
        """
    )

    rewriter = LLMQueryRewriter(
        provider
    )

    rewrites = rewriter.rewrite(
        "How do I correlate logs?",
        n=3,
    )

    assert len(rewrites) == 3


def test_rewriter_rejects_lost_identifier():

    provider = FakeProvider(
        """
        [
          "Why did the RPC fail?",
          "What caused the RPC problem?",
          "Why was the request unavailable?"
        ]
        """
    )

    rewriter = LLMQueryRewriter(
        provider
    )

    with pytest.raises(
        ValueError,
        match="identifiers",
    ):
        rewriter.rewrite(
            (
                "Why is "
                "rpc.response.status_code "
                "UNAVAILABLE?"
            ),
            n=3,
        )


def test_static_rewriter_is_deterministic():

    mapping = {
        "query": [
            "rewrite one",
            "rewrite two",
            "rewrite three",
        ]
    }

    rewriter = StaticQueryRewriter(
        mapping
    )

    assert rewriter.rewrite(
        "query",
        n=2,
    ) == [
        "rewrite one",
        "rewrite two",
    ]

class SequentialFakeProvider:

    def __init__(
        self,
        responses: list[str],
    ) -> None:
        self.responses = responses
        self.index = 0

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> str:

        response = self.responses[
            self.index
        ]

        self.index += 1

        return response


def test_rewriter_retries_duplicates():

    provider = SequentialFakeProvider(
        [
            """
            [
              "What is the purpose of oteldemo.CheckoutService/PlaceOrder?",
              "What is the purpose of oteldemo.CheckoutService/PlaceOrder?",
              "What does oteldemo.CheckoutService/PlaceOrder do?"
            ]
            """,
            """
            [
              "What role does oteldemo.CheckoutService/PlaceOrder perform?",
              "What functionality is provided by oteldemo.CheckoutService/PlaceOrder?",
              "What does oteldemo.CheckoutService/PlaceOrder do?"
            ]
            """,
        ]
    )

    rewriter = LLMQueryRewriter(
        provider=provider,
        max_attempts=3,
    )

    rewrites = rewriter.rewrite(
        (
            "What is the purpose of "
            "oteldemo.CheckoutService/PlaceOrder?"
        ),
        n=3,
    )

    assert len(rewrites) == 3

    assert len(
        set(rewrites)
    ) == 3
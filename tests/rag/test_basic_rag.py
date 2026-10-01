import pytest

from rootlens.rag.basic_rag import (
    BasicGroundedRAG,
)


class FakeRetriever:

    def __init__(
        self,
        ranking,
    ):
        self.ranking = ranking

    def search(
        self,
        query,
        k,
    ):
        return self.ranking[:k]


class FakeProvider:

    def __init__(
        self,
        response,
    ):
        self.response = response
        self.system_prompt = None
        self.user_prompt = None

    def generate(
        self,
        system_prompt,
        user_prompt,
        *,
        max_tokens,
        temperature,
    ):

        self.system_prompt = (
            system_prompt
        )

        self.user_prompt = (
            user_prompt
        )

        return self.response


DOCUMENTS = {
    "payment-service.md":
        (
            "PaymentService handles "
            "payment charging."
        ),

    "checkout-service.md":
        (
            "CheckoutService coordinates "
            "the checkout workflow."
        ),
}


def build_rag(
    response,
    ranking=None,
):

    if ranking is None:
        ranking = [
            (
                "payment-service.md",
                0.91,
            ),
            (
                "checkout-service.md",
                0.82,
            ),
        ]

    provider = (
        FakeProvider(
            response
        )
    )

    rag = BasicGroundedRAG(
        documents=DOCUMENTS,
        retriever=FakeRetriever(
            ranking
        ),
        provider=provider,
        top_k=2,
    )

    return rag, provider


def test_answered_response():

    rag, _ = build_rag(
        """
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
    )

    result = rag.answer(
        "Which service handles payment?"
    )

    assert (
        result.answer.status
        == "answered"
    )

    assert (
        len(
            result.answer.claims
        )
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


def test_partial_response():

    rag, _ = build_rag(
        """
        {
          "status": "partial",
          "claims": [
            {
              "text": "PaymentService handles payment charging.",
              "sources": [
                "payment-service.md"
              ]
            }
          ],
          "limitation": "The evidence does not describe retry behavior."
        }
        """
    )

    result = rag.answer(
        "Who charges payments and how are retries handled?"
    )

    assert (
        result.answer.status
        == "partial"
    )

    assert (
        result.answer.limitation
        is not None
    )


def test_abstention_response():

    rag, _ = build_rag(
        """
        {
          "status": "abstained",
          "claims": [],
          "limitation": "The provided evidence does not answer the question."
        }
        """
    )

    result = rag.answer(
        "Which database stores payments?"
    )

    assert (
        result.answer.status
        == "abstained"
    )

    assert (
        result.answer.claims
        == ()
    )


def test_unknown_citation_is_rejected():

    rag, _ = build_rag(
        """
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
    )

    with pytest.raises(
        ValueError,
        match="not retrieved",
    ):
        rag.answer(
            "Where are payments stored?"
        )


def test_claim_without_source_is_rejected():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [
            {
              "text": "PaymentService handles payments.",
              "sources": []
            }
          ],
          "limitation": null
        }
        """
    )

    with pytest.raises(
        ValueError,
        match="at least one source",
    ):
        rag.answer(
            "Who handles payments?"
        )


def test_answered_requires_claim():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [],
          "limitation": null
        }
        """
    )

    with pytest.raises(
        ValueError,
        match="at least one claim",
    ):
        rag.answer(
            "Who handles payments?"
        )


def test_partial_requires_limitation():

    rag, _ = build_rag(
        """
        {
          "status": "partial",
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
    )

    with pytest.raises(
        ValueError,
        match="missing evidence",
    ):
        rag.answer(
            "Who handles payments?"
        )


def test_abstention_cannot_contain_claims():

    rag, _ = build_rag(
        """
        {
          "status": "abstained",
          "claims": [
            {
              "text": "PaymentService handles payment charging.",
              "sources": [
                "payment-service.md"
              ]
            }
          ],
          "limitation": "Insufficient evidence."
        }
        """
    )

    with pytest.raises(
        ValueError,
        match="must not contain claims",
    ):
        rag.answer(
            "Who handles payments?"
        )


def test_unknown_retrieved_document_is_rejected():

    rag, _ = build_rag(
        """
        {
          "status": "abstained",
          "claims": [],
          "limitation": "Insufficient evidence."
        }
        """,
        ranking=[
            (
                "unknown.md",
                0.91,
            )
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="unknown source",
    ):
        rag.answer(
            "Question"
        )


def test_duplicate_retrieved_document_is_rejected():

    rag, _ = build_rag(
        """
        {
          "status": "abstained",
          "claims": [],
          "limitation": "Insufficient evidence."
        }
        """,
        ranking=[
            (
                "payment-service.md",
                0.91,
            ),
            (
                "payment-service.md",
                0.88,
            ),
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="duplicate source",
    ):
        rag.answer(
            "Question"
        )


def test_context_contains_only_retrieved_documents():

    rag, provider = build_rag(
        """
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
        """,
        ranking=[
            (
                "payment-service.md",
                0.91,
            )
        ],
    )

    rag.answer(
        "Who handles payment?"
    )

    assert (
        "[SOURCE: payment-service.md]"
        in provider.user_prompt
    )

    assert (
        "PaymentService handles "
        "payment charging."
        in provider.user_prompt
    )

    assert (
        "checkout-service.md"
        not in provider.user_prompt
    )


def test_markdown_fenced_json_is_accepted():

    rag, _ = build_rag(
        """
        ```json
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
        ```
        """
    )

    result = rag.answer(
        "Who handles payments?"
    )

    assert (
        result.answer.status
        == "answered"
    )


def test_duplicate_citations_are_normalized():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [
            {
              "text": "PaymentService handles payment charging.",
              "sources": [
                "payment-service.md",
                "payment-service.md"
              ]
            }
          ],
          "limitation": null
        }
        """
    )

    result = rag.answer(
        "Who handles payments?"
    )

    assert (
        result.answer.claims[
            0
        ].sources
        == (
            "payment-service.md",
        )
    )

def test_source_prefix_is_normalized():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [
            {
              "text": "PaymentService handles payment charging.",
              "sources": [
                "SOURCE: payment-service.md"
              ]
            }
          ],
          "limitation": null
        }
        """
    )

    result = rag.answer(
        "Who handles payments?"
    )

    assert (
        result.answer.claims[
            0
        ].sources
        == (
            "payment-service.md",
        )
    )

def test_bracketed_source_marker_is_normalized():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [
            {
              "text": "PaymentService handles payment charging.",
              "sources": [
                "[SOURCE: payment-service.md]"
              ]
            }
          ],
          "limitation": null
        }
        """
    )

    result = rag.answer(
        "Who handles payments?"
    )

    assert (
        result.answer.claims[
            0
        ].sources
        == (
            "payment-service.md",
        )
    )

def test_non_object_claim_is_rejected():

    rag, _ = build_rag(
        """
        {
          "status": "answered",
          "claims": [
            "PaymentService handles payments."
          ],
          "limitation": null
        }
        """
    )

    with pytest.raises(
        ValueError,
        match="must be a JSON object",
    ):
        rag.answer(
            "Who handles payments?"
        )
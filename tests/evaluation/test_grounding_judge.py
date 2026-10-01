import pytest

from rootlens.evaluation.grounding_judge import (
    GroundingJudge,
    GroundingJudgeSchemaError,
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


QUESTION = (
    "Which service handles payment?"
)

CLAIM = (
    "PaymentService handles "
    "payment charging."
)

EVIDENCE = [
    (
        "payment-service.md",
        (
            "PaymentService handles "
            "payment charging."
        ),
    ),
]


def test_full_judgment():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "payment-service.md"
              ],
              "unsupported_part": null,
              "rationale": "The source explicitly states the claim."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider
    )

    result = judge.judge(
        question=QUESTION,
        claim=CLAIM,
        cited_evidence=EVIDENCE,
    )

    assert (
        result.label
        == "full"
    )

    assert (
        result.supporting_sources
        == (
            "payment-service.md",
        )
    )

    assert (
        result.unsupported_part
        is None
    )

    assert (
        result.generation_attempts
        == 1
    )


def test_partial_judgment():

    provider = SequenceProvider(
        [
            """
            {
              "label": "partial",
              "supporting_sources": [
                "payment-service.md"
              ],
              "unsupported_part": "The source does not establish that this is the only payment responsibility.",
              "rationale": "The core responsibility is supported, but the exclusivity is not."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider
    )

    result = judge.judge(
        question=QUESTION,
        claim=(
            "PaymentService exclusively "
            "handles every payment task."
        ),
        cited_evidence=EVIDENCE,
    )

    assert (
        result.label
        == "partial"
    )

    assert (
        result.unsupported_part
        is not None
    )


def test_none_judgment():

    provider = SequenceProvider(
        [
            """
            {
              "label": "none",
              "supporting_sources": [],
              "unsupported_part": "The cited source does not mention PostgreSQL.",
              "rationale": "The source describes payment charging, not database technology."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider
    )

    result = judge.judge(
        question=(
            "Which PostgreSQL version "
            "is used?"
        ),
        claim=(
            "PaymentService uses "
            "PostgreSQL 18."
        ),
        cited_evidence=EVIDENCE,
    )

    assert (
        result.label
        == "none"
    )

    assert (
        result.supporting_sources
        == ()
    )


def test_unknown_supporting_source_is_rejected():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "database.md"
              ],
              "unsupported_part": null,
              "rationale": "Supported."
            }
            """,
            """
            {
              "label": "full",
              "supporting_sources": [
                "database.md"
              ],
              "unsupported_part": null,
              "rationale": "Supported."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider,
        max_schema_retries=1,
    )

    with pytest.raises(
        GroundingJudgeSchemaError,
        match="outside the cited evidence",
    ):

        judge.judge(
            question=QUESTION,
            claim=CLAIM,
            cited_evidence=EVIDENCE,
        )

    assert (
        provider.calls
        == 2
    )


def test_schema_failure_is_retried_once():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "payment-service.md"
              ]
            }
            """,
            """
            {
              "label": "full",
              "supporting_sources": [
                "payment-service.md"
              ],
              "unsupported_part": null,
              "rationale": "The source directly supports the claim."
            }
            """,
        ]
    )

    judge = GroundingJudge(
        provider=provider,
        max_schema_retries=1,
    )

    result = judge.judge(
        question=QUESTION,
        claim=CLAIM,
        cited_evidence=EVIDENCE,
    )

    assert (
        result.label
        == "full"
    )

    assert (
        result.generation_attempts
        == 2
    )

    assert (
        provider.calls
        == 2
    )


def test_full_cannot_have_unsupported_part():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "payment-service.md"
              ],
              "unsupported_part": "Something is missing.",
              "rationale": "Mixed output."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider,
        max_schema_retries=0,
    )

    with pytest.raises(
        GroundingJudgeSchemaError,
        match="unsupported_part=null",
    ):

        judge.judge(
            question=QUESTION,
            claim=CLAIM,
            cited_evidence=EVIDENCE,
        )


def test_none_cannot_have_supporting_sources():

    provider = SequenceProvider(
        [
            """
            {
              "label": "none",
              "supporting_sources": [
                "payment-service.md"
              ],
              "unsupported_part": "The claim is unsupported.",
              "rationale": "Contradictory structured judgment."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider,
        max_schema_retries=0,
    )

    with pytest.raises(
        GroundingJudgeSchemaError,
        match="no supporting sources",
    ):

        judge.judge(
            question=QUESTION,
            claim=CLAIM,
            cited_evidence=EVIDENCE,
        )


def test_duplicate_evidence_is_rejected():

    provider = SequenceProvider(
        []
    )

    judge = GroundingJudge(
        provider=provider
    )

    with pytest.raises(
        ValueError,
        match="Duplicate evidence source",
    ):

        judge.judge(
            question=QUESTION,
            claim=CLAIM,
            cited_evidence=[
                (
                    "payment-service.md",
                    "First copy.",
                ),
                (
                    "payment-service.md",
                    "Second copy.",
                ),
            ],
        )

def test_source_prefix_is_normalized():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "SOURCE: payment-service.md"
              ],
              "unsupported_part": null,
              "rationale": "The source directly supports the claim."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider
    )

    result = judge.judge(
        question=QUESTION,
        claim=CLAIM,
        cited_evidence=EVIDENCE,
    )

    assert (
        result.supporting_sources
        == (
            "payment-service.md",
        )
    )


def test_bracketed_source_marker_is_normalized():

    provider = SequenceProvider(
        [
            """
            {
              "label": "full",
              "supporting_sources": [
                "[SOURCE: payment-service.md]"
              ],
              "unsupported_part": null,
              "rationale": "The source directly supports the claim."
            }
            """
        ]
    )

    judge = GroundingJudge(
        provider=provider
    )

    result = judge.judge(
        question=QUESTION,
        claim=CLAIM,
        cited_evidence=EVIDENCE,
    )

    assert (
        result.supporting_sources
        == (
            "payment-service.md",
        )
    )
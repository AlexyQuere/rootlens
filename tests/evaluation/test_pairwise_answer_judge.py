import pytest

from rootlens.evaluation.pairwise_answer_judge import (
    PairwiseAnswerJudge,
    PairwiseJudgeSchemaError,
)


class FakeProvider:

    def __init__(
        self,
        outputs,
    ):

        self.outputs = list(
            outputs
        )

        self.prompts = []

    def generate(
        self,
        system_prompt,
        user_prompt,
        temperature=0.0,
        max_tokens=512,
    ):

        self.prompts.append(
            {
                "system_prompt":
                    system_prompt,

                "user_prompt":
                    user_prompt,
            }
        )

        return self.outputs.pop(
            0
        )


def build_answer(
    text="Payment handles charging.",
):

    return {
        "status": "answered",

        "claims": [
            {
                "text":
                    text,

                "sources": [
                    "payment.md",
                ],
            }
        ],

        "limitation": None,
    }


def test_a_can_win():

    provider = FakeProvider(
        [
            """
            {
              "winner": "A",
              "material_difference": true,
              "rationale": "A is better supported."
            }
            """
        ]
    )

    judge = PairwiseAnswerJudge(
        provider
    )

    result = judge.judge(
        question="Who handles payment?",
        answer_a=build_answer(),
        answer_b=build_answer(
            "Unknown."
        ),
        evidence={
            "payment.md":
                "Payment handles charging."
        },
    )

    assert result.winner == "A"

    assert (
        result.material_difference
        is True
    )


def test_tie_is_supported():

    provider = FakeProvider(
        [
            """
            {
              "winner": "tie",
              "material_difference": false,
              "rationale": "Equivalent answers."
            }
            """
        ]
    )

    judge = PairwiseAnswerJudge(
        provider
    )

    result = judge.judge(
        question="Who handles payment?",
        answer_a=build_answer(),
        answer_b=build_answer(),
        evidence={
            "payment.md":
                "Payment handles charging."
        },
    )

    assert result.winner == "tie"

    assert (
        result.material_difference
        is False
    )


def test_invalid_tie_contract():

    provider = FakeProvider(
        [
            """
            {
              "winner": "tie",
              "material_difference": true,
              "rationale": "Equivalent."
            }
            """
        ]
    )

    judge = PairwiseAnswerJudge(
        provider,
        max_schema_retries=0,
    )

    with pytest.raises(
        PairwiseJudgeSchemaError
    ):

        judge.judge(
            question="Question",
            answer_a=build_answer(),
            answer_b=build_answer(),
            evidence={
                "payment.md":
                    "Payment handles charging."
            },
        )


def test_schema_retry():

    provider = FakeProvider(
        [
            """
            {
              "winner": "A"
            }
            """,

            """
            {
              "winner": "A",
              "material_difference": true,
              "rationale": "A is more complete."
            }
            """,
        ]
    )

    judge = PairwiseAnswerJudge(
        provider,
        max_schema_retries=1,
    )

    result = judge.judge(
        question="Question",
        answer_a=build_answer(),
        answer_b=build_answer(),
        evidence={
            "payment.md":
                "Payment handles charging."
        },
    )

    assert (
        result.generation_attempts
        == 2
    )

    assert len(
        provider.prompts
    ) == 2


def test_markdown_json_is_accepted():

    provider = FakeProvider(
        [
            """
            ```json
            {
              "winner": "B",
              "material_difference": true,
              "rationale": "B is more complete."
            }
            ```
            """
        ]
    )

    judge = PairwiseAnswerJudge(
        provider
    )

    result = judge.judge(
        question="Question",
        answer_a=build_answer(),
        answer_b=build_answer(),
        evidence={
            "payment.md":
                "Payment handles charging."
        },
    )

    assert result.winner == "B"
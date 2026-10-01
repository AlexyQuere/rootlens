from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Literal
from typing import Protocol


PairwiseWinner = Literal[
    "A",
    "B",
    "tie",
]


class LLMProvider(Protocol):

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        ...


class PairwiseJudgeError(
    ValueError
):
    pass


class PairwiseJudgeSchemaError(
    PairwiseJudgeError
):
    pass


@dataclass(frozen=True)
class PairwiseJudgment:

    winner: PairwiseWinner

    material_difference: bool

    rationale: str

    generation_attempts: int

    raw_model_output: str


class PairwiseAnswerJudge:

    PROMPT_VERSION = "v1"
    SYSTEM_PROMPT = (
        "You are a strict and neutral evaluator "
        "of technical answers. "
        "Follow the evaluation rubric exactly, "
        "use only the supplied evidence, and "
        "return only valid JSON."
    )

    SCHEMA_RETRY_VERSION = "v1"

    def __init__(
        self,
        provider: LLMProvider,
        max_schema_retries: int = 1,
    ) -> None:

        if max_schema_retries < 0:
            raise ValueError(
                "max_schema_retries "
                "must be non-negative."
            )

        self.provider = provider

        self.max_schema_retries = (
            max_schema_retries
        )

    def judge(
        self,
        question: str,
        answer_a: dict,
        answer_b: dict,
        evidence: dict[
            str,
            str,
        ],
    ) -> PairwiseJudgment:

        prompt = self._build_prompt(
            question=question,
            answer_a=answer_a,
            answer_b=answer_b,
            evidence=evidence,
        )

        attempts = 0

        previous_output = None

        previous_error = None

        while (
            attempts
            <= self.max_schema_retries
        ):

            attempts += 1

            if attempts == 1:

                current_prompt = prompt

            else:

                current_prompt = (
                    self._build_retry_prompt(
                        original_prompt=prompt,
                        previous_output=(
                            previous_output
                            or ""
                        ),
                        validation_error=(
                            previous_error
                            or "Unknown error"
                        ),
                    )
                )

            raw = self.provider.generate(
                self.SYSTEM_PROMPT,
                current_prompt,
                temperature=0.0,
                max_tokens=512,
            )

            previous_output = raw

            try:

                parsed = (
                    self._parse_judgment(
                        raw
                    )
                )

            except PairwiseJudgeSchemaError as exc:

                previous_error = str(
                    exc
                )

                if (
                    attempts
                    > self.max_schema_retries
                ):
                    raise

                continue

            return PairwiseJudgment(
                winner=parsed[
                    "winner"
                ],
                material_difference=(
                    parsed[
                        "material_difference"
                    ]
                ),
                rationale=parsed[
                    "rationale"
                ],
                generation_attempts=attempts,
                raw_model_output=raw,
            )

        raise RuntimeError(
            "Unreachable judge state."
        )

    @classmethod
    def _build_prompt(
        cls,
        question: str,
        answer_a: dict,
        answer_b: dict,
        evidence: dict[
            str,
            str,
        ],
    ) -> str:

        answer_a_text = (
            cls._format_answer(
                answer_a
            )
        )

        answer_b_text = (
            cls._format_answer(
                answer_b
            )
        )

        evidence_blocks = []

        for source_id in sorted(
            evidence
        ):

            evidence_blocks.append(
                "\n".join(
                    [
                        (
                            "[SOURCE: "
                            f"{source_id}]"
                        ),
                        evidence[
                            source_id
                        ],
                        "[/SOURCE]",
                    ]
                )
            )

        evidence_text = (
            "\n\n".join(
                evidence_blocks
            )
        )

        return f"""
You are evaluating two candidate answers
to the same technical question.

You do NOT know which retrieval system
produced either answer.

Evaluate only using the supplied evidence.
Do not use external knowledge.

QUESTION
--------
{question}


REFERENCE EVIDENCE
------------------
{evidence_text}


ANSWER A
--------
{answer_a_text}


ANSWER B
--------
{answer_b_text}


EVALUATION CRITERIA
-------------------

Evaluate in this priority order:

1. Factual support / grounding
   Every factual claim should be supported
   by the supplied evidence.

2. Completeness
   The answer should address the important
   aspects of the question.

3. Relevance and directness
   Prefer answers that directly answer the
   question without unnecessary detours.

4. Investigation usefulness
   Prefer the answer that would materially
   help an engineer make the better next
   diagnostic decision.

5. Concision
   Prefer concise answers only when factual
   support and completeness are otherwise
   equivalent.

IMPORTANT:

- A longer answer is not automatically better.
- More citations are not automatically better.
- Different wording alone is NOT a material
  difference.
- Minor stylistic differences must result
  in "tie".
- Choose A or B only if one answer has a
  meaningful technical advantage.
- Unsupported or overstated claims are a
  meaningful disadvantage.

Return EXACTLY one JSON object:

{{
  "winner": "A" | "B" | "tie",
  "material_difference": true | false,
  "rationale": "short explanation"
}}

Contract:

- winner = "tie"
  => material_difference must be false

- winner = "A" or "B"
  => material_difference must be true
""".strip()

    @classmethod
    def _format_answer(
        cls,
        answer: dict,
    ) -> str:

        lines = [
            (
                "status: "
                f"{answer['status']}"
            )
        ]

        claims = answer.get(
            "claims",
            [],
        )

        for index, claim in enumerate(
            claims,
            start=1,
        ):

            sources = ", ".join(
                claim[
                    "sources"
                ]
            )

            lines.append(
                (
                    f"{index}. "
                    f"{claim['text']}"
                )
            )

            lines.append(
                (
                    "   sources: "
                    f"{sources}"
                )
            )

        limitation = answer.get(
            "limitation"
        )

        if limitation:

            lines.append(
                "limitation: "
                f"{limitation}"
            )

        return "\n".join(
            lines
        )

    @classmethod
    def _build_retry_prompt(
        cls,
        original_prompt: str,
        previous_output: str,
        validation_error: str,
    ) -> str:

        return f"""
{original_prompt}

Your previous response violated the output
schema.

VALIDATION ERROR
----------------
{validation_error}

PREVIOUS RESPONSE
-----------------
{previous_output}

Return ONLY a corrected JSON object.
""".strip()

    @classmethod
    def _parse_json(
        cls,
        raw: str,
    ) -> dict:

        cleaned = raw.strip()

        if cleaned.startswith(
            "```"
        ):

            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

        try:

            data = json.loads(
                cleaned
            )

        except json.JSONDecodeError as exc:

            raise PairwiseJudgeSchemaError(
                "Judge did not return "
                "valid JSON."
            ) from exc

        if not isinstance(
            data,
            dict,
        ):

            raise PairwiseJudgeSchemaError(
                "Judge output must be "
                "a JSON object."
            )

        return data

    @classmethod
    def _parse_judgment(
        cls,
        raw: str,
    ) -> dict:

        data = cls._parse_json(
            raw
        )

        expected_keys = {
            "winner",
            "material_difference",
            "rationale",
        }

        if set(
            data
        ) != expected_keys:

            raise PairwiseJudgeSchemaError(
                "Judge output must contain "
                "exactly winner, "
                "material_difference and "
                "rationale."
            )

        winner = data[
            "winner"
        ]

        if winner not in (
            "A",
            "B",
            "tie",
        ):

            raise PairwiseJudgeSchemaError(
                "winner must be A, B or tie."
            )

        material = data[
            "material_difference"
        ]

        if not isinstance(
            material,
            bool,
        ):

            raise PairwiseJudgeSchemaError(
                "material_difference must "
                "be boolean."
            )

        rationale = data[
            "rationale"
        ]

        if (
            not isinstance(
                rationale,
                str,
            )
            or not rationale.strip()
        ):

            raise PairwiseJudgeSchemaError(
                "rationale must be a "
                "non-empty string."
            )

        if (
            winner == "tie"
            and material
        ):

            raise PairwiseJudgeSchemaError(
                "tie requires "
                "material_difference=false."
            )

        if (
            winner != "tie"
            and not material
        ):

            raise PairwiseJudgeSchemaError(
                "A/B winner requires "
                "material_difference=true."
            )

        return {
            "winner":
                winner,

            "material_difference":
                material,

            "rationale":
                rationale.strip(),
        }
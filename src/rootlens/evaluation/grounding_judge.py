from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Literal
from typing import Sequence

from rootlens.llm.provider import (
    LLMProvider,
)


GroundingLabel = Literal[
    "full",
    "partial",
    "none",
]


class GroundingJudgeError(
    ValueError
):
    """Base error for grounding evaluation."""


class GroundingJudgeSchemaError(
    GroundingJudgeError
):
    """
    The judge output violates the
    expected structured contract.
    """


@dataclass(frozen=True)
class GroundingJudgment:

    label: GroundingLabel

    supporting_sources: tuple[
        str,
        ...
    ]

    unsupported_part: str | None

    rationale: str

    generation_attempts: int

    raw_model_output: str


class GroundingJudge:

    PROMPT_VERSION = "v1"

    VALID_LABELS = {
        "full",
        "partial",
        "none",
    }

    def __init__(
        self,
        provider: LLMProvider,
        max_schema_retries: int = 1,
    ) -> None:

        if max_schema_retries < 0:
            raise ValueError(
                "max_schema_retries "
                "cannot be negative."
            )

        self.provider = provider

        self.max_schema_retries = (
            max_schema_retries
        )

    def judge(
        self,
        question: str,
        claim: str,
        cited_evidence: Sequence[
            tuple[str, str]
        ],
    ) -> GroundingJudgment:

        question = question.strip()
        claim = claim.strip()

        if not question:
            raise ValueError(
                "question cannot be empty."
            )

        if not claim:
            raise ValueError(
                "claim cannot be empty."
            )

        evidence = (
            self._validate_evidence(
                cited_evidence
            )
        )

        allowed_sources = {
            source_id
            for source_id, _
            in evidence
        }

        context = (
            self._format_evidence(
                evidence
            )
        )

        previous_output = None
        previous_error = None

        total_attempts = (
            1
            + self.max_schema_retries
        )

        for attempt_index in range(
            total_attempts
        ):

            if attempt_index == 0:

                system_prompt = (
                    self._system_prompt()
                )

                user_prompt = (
                    self._user_prompt(
                        question=question,
                        claim=claim,
                        context=context,
                    )
                )

            else:

                if (
                    previous_output is None
                    or previous_error is None
                ):
                    raise RuntimeError(
                        "Retry requested without "
                        "a previous judge failure."
                    )

                system_prompt = (
                    self._retry_system_prompt()
                )

                user_prompt = (
                    self._retry_user_prompt(
                        question=question,
                        claim=claim,
                        context=context,
                        previous_output=(
                            previous_output
                        ),
                        validation_error=(
                            str(
                                previous_error
                            )
                        ),
                    )
                )

            raw_output = (
                self.provider.generate(
                    system_prompt,
                    user_prompt,
                    max_tokens=512,
                    temperature=0.0,
                )
            )

            try:

                parsed = (
                    self._parse_judgment(
                        raw_output=(
                            raw_output
                        ),
                        allowed_sources=(
                            allowed_sources
                        ),
                    )
                )

            except GroundingJudgeSchemaError as exc:

                previous_output = (
                    raw_output
                )

                previous_error = exc

                if (
                    attempt_index
                    >= self.max_schema_retries
                ):
                    raise

                continue

            return GroundingJudgment(
                label=(
                    parsed[
                        "label"
                    ]
                ),
                supporting_sources=(
                    parsed[
                        "supporting_sources"
                    ]
                ),
                unsupported_part=(
                    parsed[
                        "unsupported_part"
                    ]
                ),
                rationale=(
                    parsed[
                        "rationale"
                    ]
                ),
                generation_attempts=(
                    attempt_index + 1
                ),
                raw_model_output=(
                    raw_output
                ),
            )

        raise RuntimeError(
            "Grounding judge loop "
            "terminated unexpectedly."
        )

    @staticmethod
    def _validate_evidence(
        cited_evidence: Sequence[
            tuple[str, str]
        ],
    ) -> list[
        tuple[str, str]
    ]:

        if not cited_evidence:
            raise ValueError(
                "cited_evidence cannot "
                "be empty."
            )

        result = []
        seen = set()

        for source_id, text in (
            cited_evidence
        ):

            if (
                not isinstance(
                    source_id,
                    str,
                )
                or not source_id.strip()
            ):
                raise ValueError(
                    "Every source identifier "
                    "must be a non-empty string."
                )

            if (
                not isinstance(
                    text,
                    str,
                )
                or not text.strip()
            ):
                raise ValueError(
                    "Every evidence source "
                    "must contain text."
                )

            source_id = (
                source_id.strip()
            )

            if source_id in seen:
                raise ValueError(
                    "Duplicate evidence source: "
                    f"{source_id}"
                )

            seen.add(
                source_id
            )

            result.append(
                (
                    source_id,
                    text.strip(),
                )
            )

        return result

    @staticmethod
    def _format_evidence(
        evidence: Sequence[
            tuple[str, str]
        ],
    ) -> str:

        blocks = []

        for source_id, text in (
            evidence
        ):

            blocks.append(
                (
                    f"[SOURCE: {source_id}]\n"
                    f"{text}\n"
                    "[/SOURCE]"
                )
            )

        return "\n\n".join(
            blocks
        )

    @staticmethod
    def _system_prompt() -> str:

        return (
            "You are evaluating whether a "
            "generated technical claim is "
            "supported by its cited evidence.\n\n"

            "Judge ONLY evidence support.\n"
            "Do NOT judge whether the claim "
            "is true according to your prior "
            "knowledge.\n"
            "Do NOT use external knowledge.\n"
            "Do NOT use assumptions that are "
            "not explicitly supported by the "
            "provided evidence.\n\n"

            "Use exactly one label:\n\n"

            "full:\n"
            "The cited evidence collectively "
            "supports the entire claim. "
            "No material part of the claim "
            "requires unsupported inference, "
            "stronger wording, or external "
            "knowledge.\n\n"

            "partial:\n"
            "The evidence supports a meaningful "
            "part of the claim, but at least one "
            "material element is unsupported, "
            "overstated, generalized, or stronger "
            "than the evidence.\n\n"

            "none:\n"
            "The cited evidence does not support "
            "the central claim. The evidence may "
            "be topically related, but it does "
            "not establish the claim.\n\n"

            "Be especially strict about changes "
            "in logical strength. For example, "
            "'may indicate' does not support "
            "'proves', and one possible cause "
            "does not support an assertion that "
            "it is the cause.\n\n"

            "supporting_sources must contain "
            "only identifiers from the supplied "
            "evidence that materially support "
            "the claim.\n\n"

            "For label 'full', unsupported_part "
            "must be null.\n\n"

            "For label 'partial', identify the "
            "unsupported or overstated part.\n\n"

            "For label 'none', "
            "supporting_sources must be empty "
            "and unsupported_part must explain "
            "what is unsupported.\n\n"

            "Return ONLY valid JSON using "
            "exactly this schema:\n\n"

            "{\n"
            '  "label": '
            '"full | partial | none",\n'
            '  "supporting_sources": '
            '["source-id"],\n'
            '  "unsupported_part": '
            '"string or null",\n'
            '  "rationale": '
            '"brief evidence-based explanation"\n'
            "}\n"
        )

    @staticmethod
    def _user_prompt(
        question: str,
        claim: str,
        context: str,
    ) -> str:

        return (
            "QUESTION\n"
            "--------\n"
            f"{question}\n\n"

            "CLAIM TO EVALUATE\n"
            "-----------------\n"
            f"{claim}\n\n"

            "CITED EVIDENCE\n"
            "--------------\n"
            f"{context}\n\n"

            "Determine whether the cited "
            "evidence supports the claim."
        )

    @staticmethod
    def _retry_system_prompt() -> str:

        return (
            "You are repairing an invalid "
            "structured grounding judgment.\n\n"

            "Do not change the evaluation task.\n"
            "Use only the supplied evidence.\n"
            "Do not use external knowledge.\n\n"

            "Return ONLY valid JSON with "
            "exactly these fields:\n"
            "label, supporting_sources, "
            "unsupported_part, rationale."
        )

    @staticmethod
    def _retry_user_prompt(
        question: str,
        claim: str,
        context: str,
        previous_output: str,
        validation_error: str,
    ) -> str:

        return (
            "The previous grounding judgment "
            "failed validation.\n\n"

            "VALIDATION ERROR\n"
            "----------------\n"
            f"{validation_error}\n\n"

            "QUESTION\n"
            "--------\n"
            f"{question}\n\n"

            "CLAIM\n"
            "-----\n"
            f"{claim}\n\n"

            "CITED EVIDENCE\n"
            "--------------\n"
            f"{context}\n\n"

            "PREVIOUS INVALID OUTPUT\n"
            "-----------------------\n"
            f"{previous_output}\n\n"

            "Return a corrected judgment "
            "using the required schema."
        )

    @staticmethod
    def _normalize_source_id(
        source: str,
        allowed_sources: set[str],
    ) -> str:

        candidate = source.strip()

        #
        # Preferred canonical form.
        #
        if candidate in allowed_sources:
            return candidate

        #
        # Accept harmless formatting that
        # mirrors the evidence markers:
        #
        # SOURCE: payment-service.md
        # [SOURCE: payment-service.md]
        #
        match = re.fullmatch(
            (
                r"\[?\s*SOURCE\s*:\s*"
                r"([^\]]+?)\s*\]?"
            ),
            candidate,
            flags=re.IGNORECASE,
        )

        if match is not None:

            normalized = (
                match.group(1)
                .strip()
            )

            if normalized in allowed_sources:
                return normalized

        raise GroundingJudgeSchemaError(
            "Judge referenced source "
            "outside the cited evidence: "
            f"{source!r}"
        )

    @classmethod
    def _parse_judgment(
        cls,
        raw_output: str,
        allowed_sources: set[str],
    ) -> dict:

        data = (
            cls._parse_json(
                raw_output
            )
        )

        if not isinstance(
            data,
            dict,
        ):
            raise GroundingJudgeSchemaError(
                "Judge output must be "
                "a JSON object."
            )

        expected_keys = {
            "label",
            "supporting_sources",
            "unsupported_part",
            "rationale",
        }

        if set(data) != expected_keys:
            raise GroundingJudgeSchemaError(
                "Judge output must contain "
                "exactly label, "
                "supporting_sources, "
                "unsupported_part, rationale."
            )

        label = data[
            "label"
        ]

        if label not in (
            cls.VALID_LABELS
        ):
            raise GroundingJudgeSchemaError(
                "Invalid grounding label: "
                f"{label!r}"
            )

        sources = data[
            "supporting_sources"
        ]

        if not isinstance(
            sources,
            list,
        ):
            raise GroundingJudgeSchemaError(
                "supporting_sources must "
                "be a list."
            )

        if not all(
            isinstance(
                source,
                str,
            )
            and source.strip()
            for source in sources
        ):
            raise GroundingJudgeSchemaError(
                "supporting_sources must "
                "contain non-empty strings."
            )

        normalized_sources_list = []

        for source in sources:

            normalized_source = (
                cls._normalize_source_id(
                    source=source,
                    allowed_sources=(
                        allowed_sources
                    ),
                )
            )

            normalized_sources_list.append(
                normalized_source
            )

        normalized_sources = tuple(
            dict.fromkeys(
                normalized_sources_list
            )
        )

        unsupported_part = data[
            "unsupported_part"
        ]

        if (
            unsupported_part is not None
            and not isinstance(
                unsupported_part,
                str,
            )
        ):
            raise GroundingJudgeSchemaError(
                "unsupported_part must be "
                "a string or null."
            )

        if isinstance(
            unsupported_part,
            str,
        ):

            unsupported_part = (
                unsupported_part.strip()
            )

            if not unsupported_part:
                unsupported_part = None

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
            raise GroundingJudgeSchemaError(
                "rationale must be a "
                "non-empty string."
            )

        rationale = (
            rationale.strip()
        )

        if label == "full":

            if not normalized_sources:
                raise GroundingJudgeSchemaError(
                    "A full judgment must "
                    "identify at least one "
                    "supporting source."
                )

            if unsupported_part is not None:
                raise GroundingJudgeSchemaError(
                    "A full judgment must "
                    "have unsupported_part=null."
                )

        elif label == "partial":

            if not normalized_sources:
                raise GroundingJudgeSchemaError(
                    "A partial judgment must "
                    "identify at least one "
                    "supporting source."
                )

            if unsupported_part is None:
                raise GroundingJudgeSchemaError(
                    "A partial judgment must "
                    "describe the unsupported "
                    "part."
                )

        elif label == "none":

            if normalized_sources:
                raise GroundingJudgeSchemaError(
                    "A none judgment must "
                    "have no supporting "
                    "sources."
                )

            if unsupported_part is None:
                raise GroundingJudgeSchemaError(
                    "A none judgment must "
                    "describe what is "
                    "unsupported."
                )

        return {
            "label":
                label,

            "supporting_sources":
                normalized_sources,

            "unsupported_part":
                unsupported_part,

            "rationale":
                rationale,
        }

    @staticmethod
    def _parse_json(
        raw_output: str,
    ):

        cleaned = (
            raw_output.strip()
        )

        if not cleaned:
            raise GroundingJudgeSchemaError(
                "Judge returned an "
                "empty response."
            )

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

        start = cleaned.find(
            "{"
        )

        if start == -1:
            raise GroundingJudgeSchemaError(
                "Judge response does "
                "not contain JSON."
            )

        decoder = (
            json.JSONDecoder()
        )

        try:

            data, _ = (
                decoder.raw_decode(
                    cleaned[
                        start:
                    ]
                )
            )

        except json.JSONDecodeError as exc:

            raise GroundingJudgeSchemaError(
                "Invalid JSON returned "
                "by grounding judge."
            ) from exc

        return data
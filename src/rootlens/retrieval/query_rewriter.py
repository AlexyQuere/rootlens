from __future__ import annotations

import json
import re
from typing import Protocol

from rootlens.llm.provider import (
    LLMProvider,
)


class QueryRewriter(Protocol):

    def rewrite(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:
        ...


def extract_identifiers(
    query: str,
) -> set[str]:

    patterns = [
        # dotted/slashed technical names
        r"\b[A-Za-z][A-Za-z0-9_]*"
        r"(?:[./][A-Za-z0-9_.-]+)+\b",

        # uppercase codes
        r"\b[A-Z][A-Z0-9_]{2,}\b",

        # CamelCase technical names
        r"\b[A-Z][a-z]+"
        r"(?:[A-Z][A-Za-z0-9]*)+\b",

        # HTTP-style status codes
        r"\b[45][0-9]{2}\b",
    ]

    identifiers: set[str] = set()

    for pattern in patterns:
        identifiers.update(
            re.findall(
                pattern,
                query,
            )
        )

    return identifiers


class LLMQueryRewriter:
    """Generate semantically equivalent retrieval queries."""

    PROMPT_VERSION = "v2"

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError(
                "max_attempts must be strictly positive."
            )

        self.provider = provider
        self.max_attempts = max_attempts

    def rewrite(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:

        if n <= 0:
            raise ValueError(
                "n must be strictly positive."
            )

        collected: list[str] = []

        for attempt in range(
            1,
            self.max_attempts + 1,
        ):
            missing = n - len(collected)

            if missing <= 0:
                break

            raw_candidates = (
                self._generate_candidates(
                    query=query,
                    n=max(
                        missing,
                        n,
                    ),
                    previous=collected,
                    attempt=attempt,
                )
            )

            valid_candidates = (
                self._filter_valid_candidates(
                    original=query,
                    candidates=raw_candidates,
                    existing=collected,
                )
            )

            collected.extend(
                valid_candidates
            )

            collected = collected[:n]

        if len(collected) != n:
            raise ValueError(
                "Could not generate exactly "
                f"{n} valid unique rewrites "
                f"after {self.max_attempts} attempts. "
                f"Generated {len(collected)}: "
                f"{collected}. "
                "Candidates may have been rejected because "
                "they were duplicates, equivalent to the original query, "
                "or because they did not preserve required technical identifiers."
            )

        return collected

    def _generate_candidates(
        self,
        query: str,
        n: int,
        previous: list[str],
        attempt: int,
    ) -> list[str]:

        system_prompt = (
            "You rewrite search queries for "
            "technical incident investigation. "
            "Generate semantically equivalent "
            "search queries for information retrieval. "
            "Do not answer the query. "
            "Do not decompose it into subquestions. "
            "Each rewrite must preserve the complete "
            "information need of the original query. "
            "Preserve technical identifiers, "
            "service names, method names, error codes, "
            "status codes, and literal technical tokens "
            "exactly. "
            "Do not add facts that are not present "
            "in the original query. "
            "Each rewrite must be meaningfully different "
            "from the original query and from every other "
            "rewrite. "
            "Changing only punctuation, capitalization, "
            "or word order is not sufficient. "
            "Use different lexical phrasing while "
            "preserving the same retrieval intent. "
            "Return only a JSON array of strings."
        )

        previous_text = ""

        if previous:
            previous_text = (
                "\n\nDo not repeat any of these "
                "already accepted rewrites:\n"
                + "\n".join(
                    f"- {rewrite}"
                    for rewrite in previous
                )
            )

        user_prompt = (
            f"Original query:\n"
            f"{query}\n\n"
            f"Generate exactly {n} new "
            f"semantic rewrites."
            f"{previous_text}\n\n"
            f"This is generation attempt {attempt}."
        )

        raw = self.provider.generate(
            system_prompt,
            user_prompt,
            max_tokens=256,
            temperature=0.0,
        )

        return self._parse_response(
            raw
        )

    def _filter_valid_candidates(
        self,
        original: str,
        candidates: list[str],
        existing: list[str],
    ) -> list[str]:

        identifiers = extract_identifiers(
            original
        )

        normalized_original = (
            self._normalize(
                original
            )
        )

        seen = {
            normalized_original
        }

        seen.update(
            self._normalize(
                rewrite
            )
            for rewrite in existing
        )

        valid: list[str] = []

        for candidate in candidates:

            candidate = candidate.strip()

            if not candidate:
                continue

            normalized = (
                self._normalize(
                    candidate
                )
            )

            if normalized in seen:
                continue

            missing_identifiers = [
                identifier
                for identifier in identifiers
                if identifier
                not in candidate
            ]

            if missing_identifiers:
                continue

            seen.add(
                normalized
            )

            valid.append(
                candidate
            )

        return valid

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        return " ".join(
            text.lower().split()
        )

    @staticmethod
    def _parse_response(
        raw: str,
    ) -> list[str]:

        cleaned = raw.strip()

        if cleaned.startswith(
            "```"
        ):
            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

        start = cleaned.find("[")
        end = cleaned.rfind("]")

        if (
            start == -1
            or end == -1
        ):
            raise ValueError(
                "LLM did not return "
                "a JSON array."
            )

        parsed = json.loads(
            cleaned[
                start:
                end + 1
            ]
        )

        if not isinstance(
            parsed,
            list,
        ):
            raise ValueError(
                "Expected a JSON list."
            )

        if not all(
            isinstance(item, str)
            for item in parsed
        ):
            raise ValueError(
                "Every rewrite must "
                "be a string."
            )

        return [
            item.strip()
            for item in parsed
            if item.strip()
        ]

class StaticQueryRewriter:
    """Deterministic rewriter backed by frozen generated rewrites."""

    def __init__(
        self,
        rewrites_by_query:
            dict[str, list[str]],
    ) -> None:
        self.rewrites_by_query = (
            rewrites_by_query
        )

    def rewrite(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:

        if query not in (
            self.rewrites_by_query
        ):
            raise KeyError(
                "No frozen rewrites for "
                f"query: {query}"
            )

        rewrites = (
            self.rewrites_by_query[
                query
            ]
        )

        if len(rewrites) < n:
            raise ValueError(
                "Not enough frozen rewrites."
            )

        return rewrites[:n]
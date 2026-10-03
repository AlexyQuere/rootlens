from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Literal, Mapping


_TRACE_ID_RE = re.compile(
    r"^[0-9a-fA-F]{32}$"
)

_SPAN_ID_RE = re.compile(
    r"^[0-9a-fA-F]{16}$"
)


LogTimeField = Literal[
    "@timestamp",
    "observedTimestamp",
]


def _freeze_value(
    value: Any,
) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze_value(item)
                for key, item in value.items()
            }
        )

    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_value(item)
            for item in value
        )

    return value


def parse_iso_timestamp(
    value: str,
) -> datetime:
    if not isinstance(value, str):
        raise TypeError(
            "Timestamp must be a string."
        )

    cleaned = value.strip()

    if not cleaned:
        raise ValueError(
            "Timestamp cannot be empty."
        )

    parsed = datetime.fromisoformat(
        cleaned.replace(
            "Z",
            "+00:00",
        )
    )

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise ValueError(
            "Timestamp must be timezone-aware."
        )

    return parsed


@dataclass(frozen=True)
class LogEvidence:
    event_timestamp: datetime | None
    event_timestamp_raw: str | None

    observed_timestamp: datetime | None
    observed_timestamp_raw: str | None

    service_name: str | None

    severity_text: str | None
    severity_number: int | None

    body: Any

    trace_id: str | None
    span_id: str | None

    attributes: Mapping[str, Any]
    resource_attributes: Mapping[str, Any]
    instrumentation_scope: Mapping[str, Any]

    index: str
    document_id: str

    raw_source: Mapping[str, Any]

    source: str = "opensearch"

    def __post_init__(
        self,
    ) -> None:
        if (
            self.event_timestamp is None
            and self.observed_timestamp is None
        ):
            raise ValueError(
                "At least one timestamp must be present."
            )

        if (
            self.event_timestamp is not None
            and (
                self.event_timestamp.tzinfo is None
                or self.event_timestamp.utcoffset()
                is None
            )
        ):
            raise ValueError(
                "event_timestamp must be "
                "timezone-aware."
            )

        if (
            self.observed_timestamp is not None
            and (
                self.observed_timestamp.tzinfo is None
                or self.observed_timestamp.utcoffset()
                is None
            )
        ):
            raise ValueError(
                "observed_timestamp must be "
                "timezone-aware."
            )

        object.__setattr__(
            self,
            "attributes",
            _freeze_value(
                self.attributes
            ),
        )

        object.__setattr__(
            self,
            "resource_attributes",
            _freeze_value(
                self.resource_attributes
            ),
        )

        object.__setattr__(
            self,
            "instrumentation_scope",
            _freeze_value(
                self.instrumentation_scope
            ),
        )

        object.__setattr__(
            self,
            "body",
            _freeze_value(
                self.body
            ),
        )

        object.__setattr__(
            self,
            "raw_source",
            _freeze_value(
                self.raw_source
            ),
        )

    @property
    def trace_id_valid(
        self,
    ) -> bool:
        if self.trace_id is None:
            return False

        return bool(
            _TRACE_ID_RE.fullmatch(
                self.trace_id
            )
        )

    @property
    def span_id_valid(
        self,
    ) -> bool:
        if self.span_id is None:
            return False

        return bool(
            _SPAN_ID_RE.fullmatch(
                self.span_id
            )
        )

    @property
    def severity_casefold(
        self,
    ) -> str | None:
        if self.severity_text is None:
            return None

        return self.severity_text.casefold()

    @property
    def body_text(
        self,
    ) -> str | None:
        if isinstance(
            self.body,
            str,
        ):
            return self.body

        return None

    @property
    def observed_minus_event_ms(
        self,
    ) -> float | None:
        if (
            self.event_timestamp is None
            or self.observed_timestamp is None
        ):
            return None

        delta = (
            self.observed_timestamp
            - self.event_timestamp
        )

        return (
            delta.total_seconds()
            * 1000.0
        )


@dataclass(frozen=True)
class LogQueryEvidence:
    index_pattern: str

    start: datetime
    end: datetime

    service_name: str | None
    trace_id: str | None
    span_id: str | None
    severity_text: str | None

    limit: int

    time_field: LogTimeField

    request_body: Mapping[str, Any]

    source: str = "opensearch"

    def __post_init__(
        self,
    ) -> None:
        if (
            self.start.tzinfo is None
            or self.start.utcoffset() is None
        ):
            raise ValueError(
                "start must be timezone-aware."
            )

        if (
            self.end.tzinfo is None
            or self.end.utcoffset() is None
        ):
            raise ValueError(
                "end must be timezone-aware."
            )

        if self.end <= self.start:
            raise ValueError(
                "end must be after start."
            )

        if self.limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        if self.time_field not in (
            "@timestamp",
            "observedTimestamp",
        ):
            raise ValueError(
                "Unsupported time field."
            )

        object.__setattr__(
            self,
            "request_body",
            _freeze_value(
                self.request_body
            ),
        )


@dataclass(frozen=True)
class LogSearchResult:
    query: LogQueryEvidence
    logs: tuple[LogEvidence, ...]
    total_hits: int
    took_ms: int | None
    timed_out: bool
from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from types import MappingProxyType
from typing import Any, Mapping


class SpanKind(IntEnum):

    UNSPECIFIED = 0
    INTERNAL = 1
    SERVER = 2
    CLIENT = 3
    PRODUCER = 4
    CONSUMER = 5


class SpanStatusCode(IntEnum):

    UNSET = 0
    OK = 1
    ERROR = 2


def _freeze_mapping(
    value: Mapping[str, Any],
) -> Mapping[str, Any]:

    return MappingProxyType(
        dict(value)
    )


@dataclass(frozen=True)
class SpanEventEvidence:

    name: str
    time_unix_nano: int
    attributes: Mapping[str, Any]

    def __post_init__(
        self,
    ) -> None:

        if not self.name:
            raise ValueError(
                "event name must not be empty."
            )

        if self.time_unix_nano < 0:
            raise ValueError(
                "event time must be non-negative."
            )

        object.__setattr__(
            self,
            "attributes",
            _freeze_mapping(
                self.attributes
            ),
        )

    @property
    def time(
        self,
    ) -> datetime:

        return datetime.fromtimestamp(
            self.time_unix_nano
            / 1_000_000_000,
            tz=timezone.utc,
        )


@dataclass(frozen=True)
class SpanEvidence:

    trace_id: str
    span_id: str
    parent_span_id: str | None

    service_name: str | None
    operation_name: str

    kind: SpanKind

    start_time_unix_nano: int
    end_time_unix_nano: int

    status_code: SpanStatusCode
    status_message: str | None

    attributes: Mapping[str, Any]
    resource_attributes: Mapping[str, Any]

    events: tuple[
        SpanEventEvidence,
        ...
    ] = ()

    scope_name: str | None = None
    scope_version: str | None = None

    source: str = "jaeger"

    def __post_init__(
        self,
    ) -> None:

        if not re.fullmatch(
            r"[0-9a-f]{32}",
            self.trace_id,
        ):
            raise ValueError(
                "trace_id must contain "
                "32 lowercase hex characters."
            )

        if not re.fullmatch(
            r"[0-9a-f]{16}",
            self.span_id,
        ):
            raise ValueError(
                "span_id must contain "
                "16 lowercase hex characters."
            )

        if (
            self.parent_span_id is not None
            and not re.fullmatch(
                r"[0-9a-f]{16}",
                self.parent_span_id,
            )
        ):
            raise ValueError(
                "parent_span_id must be "
                "None or 16 lowercase "
                "hex characters."
            )

        if not self.operation_name:
            raise ValueError(
                "operation_name must "
                "not be empty."
            )

        if (
            self.end_time_unix_nano
            < self.start_time_unix_nano
        ):
            raise ValueError(
                "span end time must not "
                "precede start time."
            )

        object.__setattr__(
            self,
            "attributes",
            _freeze_mapping(
                self.attributes
            ),
        )

        object.__setattr__(
            self,
            "resource_attributes",
            _freeze_mapping(
                self.resource_attributes
            ),
        )

    @property
    def duration_ms(
        self,
    ) -> float:

        return (
            self.end_time_unix_nano
            - self.start_time_unix_nano
        ) / 1_000_000

    @property
    def start_time(
        self,
    ) -> datetime:

        return datetime.fromtimestamp(
            self.start_time_unix_nano
            / 1_000_000_000,
            tz=timezone.utc,
        )

    @property
    def end_time(
        self,
    ) -> datetime:

        return datetime.fromtimestamp(
            self.end_time_unix_nano
            / 1_000_000_000,
            tz=timezone.utc,
        )

    @property
    def is_error(
        self,
    ) -> bool:

        return (
            self.status_code
            == SpanStatusCode.ERROR
        )


@dataclass(frozen=True)
class ParentChildTemporalViolation:

    parent_span_id: str
    child_span_id: str

    parent_service: str | None
    child_service: str | None

    parent_operation: str
    child_operation: str

    starts_before_parent_ms: float
    ends_after_parent_ms: float

    def __post_init__(
        self,
    ) -> None:

        if (
            self.starts_before_parent_ms < 0
            or self.ends_after_parent_ms < 0
        ):
            raise ValueError(
                "Temporal violation values "
                "must be non-negative."
            )

        if (
            self.starts_before_parent_ms == 0
            and self.ends_after_parent_ms == 0
        ):
            raise ValueError(
                "Temporal violation must "
                "contain a positive skew."
            )

    @property
    def max_skew_ms(
        self,
    ) -> float:

        return max(
            self.starts_before_parent_ms,
            self.ends_after_parent_ms,
        )


@dataclass(frozen=True)
class TraceIntegrityEvidence:

    root_count: int
    orphan_count: int

    temporal_violations: tuple[
        ParentChildTemporalViolation,
        ...
    ]

    @property
    def temporal_violation_count(
        self,
    ) -> int:

        return len(
            self.temporal_violations
        )

    @property
    def max_temporal_skew_ms(
        self,
    ) -> float:

        if not self.temporal_violations:
            return 0.0

        return max(
            violation.max_skew_ms
            for violation
            in self.temporal_violations
        )


@dataclass(frozen=True)
class TraceEvidence:

    trace_id: str

    spans: tuple[
        SpanEvidence,
        ...
    ]

    source: str = "jaeger"

    def __post_init__(
        self,
    ) -> None:

        if not self.spans:
            raise ValueError(
                "TraceEvidence must contain "
                "at least one span."
            )

        span_ids: set[str] = set()

        for span in self.spans:

            if span.trace_id != self.trace_id:
                raise ValueError(
                    "All spans must belong "
                    "to trace_id."
                )

            if span.span_id in span_ids:
                raise ValueError(
                    "Duplicate span_id in trace: "
                    f"{span.span_id}"
                )

            span_ids.add(
                span.span_id
            )

    @property
    def start_time_unix_nano(
        self,
    ) -> int:

        return min(
            span.start_time_unix_nano
            for span in self.spans
        )

    @property
    def end_time_unix_nano(
        self,
    ) -> int:

        return max(
            span.end_time_unix_nano
            for span in self.spans
        )

    @property
    def envelope_duration_ms(
        self,
    ) -> float:

        return (
            self.end_time_unix_nano
            - self.start_time_unix_nano
        ) / 1_000_000

    @property
    def services(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            sorted(
                {
                    span.service_name
                    for span in self.spans
                    if span.service_name
                    is not None
                }
            )
        )

    @property
    def error_spans(
        self,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        return tuple(
            span
            for span in self.spans
            if span.is_error
        )

    @property
    def root_spans(
        self,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        return tuple(
            span
            for span in self.spans
            if span.parent_span_id
            is None
        )

    @property
    def orphan_spans(
        self,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        span_ids = {
            span.span_id
            for span in self.spans
        }

        return tuple(
            span
            for span in self.spans
            if (
                span.parent_span_id
                is not None
                and span.parent_span_id
                not in span_ids
            )
        )

    def children_of(
        self,
        span_id: str,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        return tuple(
            sorted(
                (
                    span
                    for span in self.spans
                    if (
                        span.parent_span_id
                        == span_id
                    )
                ),
                key=lambda span: (
                    span.start_time_unix_nano,
                    span.span_id,
                ),
            )
        )

    @property
    def temporal_violations(
        self,
    ) -> tuple[
        ParentChildTemporalViolation,
        ...
    ]:

        by_id = {
            span.span_id: span
            for span in self.spans
        }

        violations = []

        for child in self.spans:

            if child.parent_span_id is None:
                continue

            parent = by_id.get(
                child.parent_span_id
            )

            if parent is None:
                continue

            starts_before_parent_ns = max(
                0,
                (
                    parent.start_time_unix_nano
                    - child.start_time_unix_nano
                ),
            )

            ends_after_parent_ns = max(
                0,
                (
                    child.end_time_unix_nano
                    - parent.end_time_unix_nano
                ),
            )

            if (
                starts_before_parent_ns == 0
                and ends_after_parent_ns == 0
            ):
                continue

            violations.append(
                ParentChildTemporalViolation(
                    parent_span_id=(
                        parent.span_id
                    ),
                    child_span_id=(
                        child.span_id
                    ),
                    parent_service=(
                        parent.service_name
                    ),
                    child_service=(
                        child.service_name
                    ),
                    parent_operation=(
                        parent.operation_name
                    ),
                    child_operation=(
                        child.operation_name
                    ),
                    starts_before_parent_ms=(
                        starts_before_parent_ns
                        / 1_000_000
                    ),
                    ends_after_parent_ms=(
                        ends_after_parent_ns
                        / 1_000_000
                    ),
                )
            )

        return tuple(
            sorted(
                violations,
                key=lambda violation: (
                    -violation.max_skew_ms,
                    violation.parent_span_id,
                    violation.child_span_id,
                ),
            )
        )

    @property
    def integrity(
        self,
    ) -> TraceIntegrityEvidence:

        return TraceIntegrityEvidence(
            root_count=len(
                self.root_spans
            ),
            orphan_count=len(
                self.orphan_spans
            ),
            temporal_violations=(
                self.temporal_violations
            ),
        )
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from rootlens.observability.log_evidence import (
    LogEvidence,
)


LogOrdering = Literal[
    "event",
    "observed",
]


def _stable_value(
    value: Any,
) -> Any:
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    str(key),
                    _stable_value(item),
                )
                for key, item
                in value.items()
            )
        )

    if isinstance(
        value,
        (list, tuple),
    ):
        return tuple(
            _stable_value(item)
            for item in value
        )

    return value


def _body_key(
    body: Any,
) -> str:
    return repr(
        _stable_value(
            body
        )
    )


@dataclass(frozen=True)
class LogSummary:
    log_count: int

    service_counts: tuple[
        tuple[str, int],
        ...
    ]

    severity_counts: tuple[
        tuple[str, int],
        ...
    ]

    logs_with_trace_id: int
    logs_without_trace_id: int

    logs_with_span_id: int
    logs_without_span_id: int

    logs_with_event_timestamp: int
    logs_without_event_timestamp: int

    logs_with_observed_timestamp: int
    logs_without_observed_timestamp: int


@dataclass(frozen=True)
class LogDuplicateSignature:
    service_name: str | None
    trace_id: str | None
    span_id: str | None

    event_timestamp_raw: str | None

    severity_text: str | None

    body_key: str


@dataclass(frozen=True)
class PossibleDuplicateGroup:
    signature: LogDuplicateSignature

    logs: tuple[
        LogEvidence,
        ...
    ]

    @property
    def count(
        self,
    ) -> int:
        return len(
            self.logs
        )


@dataclass(frozen=True)
class TimestampDifferenceEvidence:
    service_name: str | None

    trace_id: str | None
    span_id: str | None

    event_timestamp: datetime
    observed_timestamp: datetime

    observed_minus_event_ms: float

    index: str
    document_id: str


@dataclass(frozen=True)
class LogEventSignature:
    service_name: str | None

    severity_text: str | None

    body_key: str


@dataclass(frozen=True)
class LogEventDifference:
    signature: LogEventSignature

    baseline_count: int
    incident_count: int

    @property
    def delta(
        self,
    ) -> int:
        return (
            self.incident_count
            - self.baseline_count
        )


@dataclass(frozen=True)
class LogEventComparison:
    baseline_log_count: int
    incident_log_count: int

    differences: tuple[
        LogEventDifference,
        ...
    ]

    @property
    def identical(
        self,
    ) -> bool:
        return (
            len(
                self.differences
            )
            == 0
        )


class LogInvestigationTool:

    def summarize(
        self,
        logs: Iterable[
            LogEvidence
        ],
    ) -> LogSummary:

        items = tuple(
            logs
        )

        service_counter = Counter(
            (
                log.service_name
                or "<missing>"
            )
            for log in items
        )

        severity_counter = Counter(
            (
                log.severity_text
                or "<missing>"
            )
            for log in items
        )

        with_trace = sum(
            log.trace_id is not None
            for log in items
        )

        with_span = sum(
            log.span_id is not None
            for log in items
        )

        with_event_time = sum(
            log.event_timestamp
            is not None
            for log in items
        )

        with_observed_time = sum(
            log.observed_timestamp
            is not None
            for log in items
        )

        return LogSummary(
            log_count=len(
                items
            ),

            service_counts=tuple(
                sorted(
                    service_counter.items()
                )
            ),

            severity_counts=tuple(
                sorted(
                    severity_counter.items()
                )
            ),

            logs_with_trace_id=(
                with_trace
            ),

            logs_without_trace_id=(
                len(items)
                - with_trace
            ),

            logs_with_span_id=(
                with_span
            ),

            logs_without_span_id=(
                len(items)
                - with_span
            ),

            logs_with_event_timestamp=(
                with_event_time
            ),

            logs_without_event_timestamp=(
                len(items)
                - with_event_time
            ),

            logs_with_observed_timestamp=(
                with_observed_time
            ),

            logs_without_observed_timestamp=(
                len(items)
                - with_observed_time
            ),
        )

    def find_logs(
        self,
        logs: Iterable[
            LogEvidence
        ],
        *,
        service_name:
            str | None = None,
        trace_id:
            str | None = None,
        span_id:
            str | None = None,
        severity_text:
            str | None = None,
    ) -> tuple[
        LogEvidence,
        ...
    ]:

        result = []

        for log in logs:

            if (
                service_name
                is not None
                and log.service_name
                != service_name
            ):
                continue

            if (
                trace_id
                is not None
                and log.trace_id
                != trace_id
            ):
                continue

            if (
                span_id
                is not None
                and log.span_id
                != span_id
            ):
                continue

            if (
                severity_text
                is not None
                and log.severity_text
                != severity_text
            ):
                continue

            result.append(
                log
            )

        return tuple(
            result
        )

    def order_logs(
        self,
        logs: Iterable[
            LogEvidence
        ],
        *,
        by: LogOrdering = "observed",
    ) -> tuple[
        LogEvidence,
        ...
    ]:

        if by not in (
            "event",
            "observed",
        ):
            raise ValueError(
                "by must be "
                "'event' or "
                "'observed'."
            )

        return tuple(
            sorted(
                logs,
                key=lambda log:
                    self._ordering_key(
                        log,
                        by,
                    ),
            )
        )

    def find_possible_duplicates(
        self,
        logs: Iterable[
            LogEvidence
        ],
    ) -> tuple[
        PossibleDuplicateGroup,
        ...
    ]:

        groups: dict[
            LogDuplicateSignature,
            list[LogEvidence],
        ] = defaultdict(
            list
        )

        for log in logs:

            signature = (
                LogDuplicateSignature(
                    service_name=(
                        log.service_name
                    ),

                    trace_id=(
                        log.trace_id
                    ),

                    span_id=(
                        log.span_id
                    ),

                    event_timestamp_raw=(
                        log
                        .event_timestamp_raw
                    ),

                    severity_text=(
                        log.severity_text
                    ),

                    body_key=(
                        _body_key(
                            log.body
                        )
                    ),
                )
            )

            groups[
                signature
            ].append(
                log
            )

        duplicates = []

        for (
            signature,
            grouped_logs,
        ) in groups.items():

            if (
                len(
                    grouped_logs
                )
                <= 1
            ):
                continue

            duplicates.append(
                PossibleDuplicateGroup(
                    signature=(
                        signature
                    ),

                    logs=tuple(
                        self.order_logs(
                            grouped_logs,
                            by="observed",
                        )
                    ),
                )
            )

        return tuple(
            sorted(
                duplicates,
                key=lambda group: (
                    -group.count,
                    (
                        group.signature
                        .service_name
                        or ""
                    ),
                    (
                        group.signature
                        .trace_id
                        or ""
                    ),
                    (
                        group.signature
                        .span_id
                        or ""
                    ),
                    (
                        group.signature
                        .body_key
                    ),
                ),
            )
        )

    def largest_timestamp_differences(
        self,
        logs: Iterable[
            LogEvidence
        ],
        *,
        limit: int = 10,
    ) -> tuple[
        TimestampDifferenceEvidence,
        ...
    ]:

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        evidence = []

        for log in logs:

            if (
                log.event_timestamp
                is None
                or log.observed_timestamp
                is None
            ):
                continue

            difference = (
                log
                .observed_minus_event_ms
            )

            if difference is None:
                continue

            evidence.append(
                TimestampDifferenceEvidence(
                    service_name=(
                        log.service_name
                    ),

                    trace_id=(
                        log.trace_id
                    ),

                    span_id=(
                        log.span_id
                    ),

                    event_timestamp=(
                        log.event_timestamp
                    ),

                    observed_timestamp=(
                        log
                        .observed_timestamp
                    ),

                    observed_minus_event_ms=(
                        difference
                    ),

                    index=(
                        log.index
                    ),

                    document_id=(
                        log.document_id
                    ),
                )
            )

        evidence.sort(
            key=lambda item: (
                -abs(
                    item
                    .observed_minus_event_ms
                ),
                (
                    item.service_name
                    or ""
                ),
                (
                    item.trace_id
                    or ""
                ),
                (
                    item.span_id
                    or ""
                ),
                item.index,
                item.document_id,
            )
        )

        return tuple(
            evidence[
                :limit
            ]
        )

    def event_signatures(
        self,
        logs: Iterable[
            LogEvidence
        ],
    ) -> Counter[
        LogEventSignature
    ]:

        counter: Counter[
            LogEventSignature
        ] = Counter()

        for log in logs:

            signature = (
                LogEventSignature(
                    service_name=(
                        log.service_name
                    ),

                    severity_text=(
                        log.severity_text
                    ),

                    body_key=(
                        _body_key(
                            log.body
                        )
                    ),
                )
            )

            counter[
                signature
            ] += 1

        return counter

    def compare_exact_events(
        self,
        baseline_logs: Iterable[
            LogEvidence
        ],
        incident_logs: Iterable[
            LogEvidence
        ],
    ) -> LogEventComparison:

        baseline = tuple(
            baseline_logs
        )

        incident = tuple(
            incident_logs
        )

        baseline_counter = (
            self.event_signatures(
                baseline
            )
        )

        incident_counter = (
            self.event_signatures(
                incident
            )
        )

        signatures = (
            set(
                baseline_counter
            )
            | set(
                incident_counter
            )
        )

        differences = []

        for signature in signatures:

            baseline_count = (
                baseline_counter[
                    signature
                ]
            )

            incident_count = (
                incident_counter[
                    signature
                ]
            )

            if (
                baseline_count
                == incident_count
            ):
                continue

            differences.append(
                LogEventDifference(
                    signature=(
                        signature
                    ),

                    baseline_count=(
                        baseline_count
                    ),

                    incident_count=(
                        incident_count
                    ),
                )
            )

        differences.sort(
            key=lambda item: (
                -abs(
                    item.delta
                ),
                (
                    item.signature
                    .service_name
                    or ""
                ),
                (
                    item.signature
                    .severity_text
                    or ""
                ),
                (
                    item.signature
                    .body_key
                ),
            )
        )

        return LogEventComparison(
            baseline_log_count=(
                len(
                    baseline
                )
            ),

            incident_log_count=(
                len(
                    incident
                )
            ),

            differences=tuple(
                differences
            ),
        )

    @staticmethod
    def _ordering_key(
        log: LogEvidence,
        by: LogOrdering,
    ) -> tuple:

        if by == "observed":

            primary = (
                log.observed_timestamp
                or log.event_timestamp
            )

            secondary = (
                log.event_timestamp
                or primary
            )

        else:

            primary = (
                log.event_timestamp
                or log.observed_timestamp
            )

            secondary = (
                log.observed_timestamp
                or primary
            )

        if primary is None:
            raise ValueError(
                "Log has no timestamp."
            )

        return (
            primary,
            secondary,
            (
                log.service_name
                or ""
            ),
            (
                log.trace_id
                or ""
            ),
            (
                log.span_id
                or ""
            ),
            log.index,
            log.document_id,
        )
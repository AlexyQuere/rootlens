from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.log_investigation import (
    LogEventSignature,
    LogInvestigationTool,
)


@dataclass(frozen=True)
class TraceLogObservation:
    trace_id: str

    log_count: int

    service_counts: tuple[
        tuple[str, int],
        ...
    ]

    severity_counts: tuple[
        tuple[str, int],
        ...
    ]

    unique_signature_count: int

    possible_duplicate_group_count: int

    max_abs_observed_minus_event_ms: float | None

    signatures: tuple[
        LogEventSignature,
        ...
    ]


@dataclass(frozen=True)
class LogWindowSummary:
    trace_count: int

    traces_with_logs: int
    traces_without_logs: int

    total_logs: int

    total_unique_trace_signatures: int


@dataclass(frozen=True)
class LogSignaturePrevalence:
    signature: LogEventSignature

    baseline_trace_count: int
    incident_trace_count: int

    baseline_prevalence: float
    incident_prevalence: float

    @property
    def delta(
        self,
    ) -> float:
        return (
            self.incident_prevalence
            - self.baseline_prevalence
        )


@dataclass(frozen=True)
class LogWindowComparison:
    baseline: LogWindowSummary
    incident: LogWindowSummary

    differences: tuple[
        LogSignaturePrevalence,
        ...
    ]

    @property
    def changed_signature_count(
        self,
    ) -> int:
        return len(
            self.differences
        )


def observe_trace_logs(
    trace_id: str,
    logs: Iterable[
        LogEvidence
    ],
    *,
    tool:
        LogInvestigationTool
        | None = None,
) -> TraceLogObservation:
    if not trace_id:
        raise ValueError(
            "trace_id cannot be empty."
        )

    items = tuple(
        logs
    )

    for log in items:
        if log.trace_id != trace_id:
            raise ValueError(
                "All logs must have "
                "the requested trace_id."
            )

    investigation = (
        tool
        or LogInvestigationTool()
    )

    summary = (
        investigation.summarize(
            items
        )
    )

    signature_counter = (
        investigation.event_signatures(
            items
        )
    )

    signatures = tuple(
        sorted(
            signature_counter.keys(),
            key=_signature_key,
        )
    )

    duplicate_groups = (
        investigation
        .find_possible_duplicates(
            items
        )
    )

    timestamp_differences = (
        investigation
        .largest_timestamp_differences(
            items,
            limit=1,
        )
    )

    max_abs_difference = None

    if timestamp_differences:
        max_abs_difference = abs(
            timestamp_differences[
                0
            ]
            .observed_minus_event_ms
        )

    return TraceLogObservation(
        trace_id=trace_id,

        log_count=(
            summary.log_count
        ),

        service_counts=(
            summary.service_counts
        ),

        severity_counts=(
            summary.severity_counts
        ),

        unique_signature_count=(
            len(
                signatures
            )
        ),

        possible_duplicate_group_count=(
            len(
                duplicate_groups
            )
        ),

        max_abs_observed_minus_event_ms=(
            max_abs_difference
        ),

        signatures=signatures,
    )


def summarize_log_window(
    observations: Iterable[
        TraceLogObservation
    ],
) -> LogWindowSummary:
    items = tuple(
        observations
    )

    traces_with_logs = sum(
        observation.log_count > 0
        for observation in items
    )

    global_signatures = set()

    for observation in items:
        global_signatures.update(
            observation.signatures
        )

    return LogWindowSummary(
        trace_count=(
            len(
                items
            )
        ),

        traces_with_logs=(
            traces_with_logs
        ),

        traces_without_logs=(
            len(items)
            - traces_with_logs
        ),

        total_logs=sum(
            observation.log_count
            for observation in items
        ),

        total_unique_trace_signatures=(
            len(
                global_signatures
            )
        ),
    )


def compare_log_windows(
    baseline: Iterable[
        TraceLogObservation
    ],
    incident: Iterable[
        TraceLogObservation
    ],
) -> LogWindowComparison:
    baseline_items = tuple(
        baseline
    )

    incident_items = tuple(
        incident
    )

    if not baseline_items:
        raise ValueError(
            "baseline cannot be empty."
        )

    if not incident_items:
        raise ValueError(
            "incident cannot be empty."
        )

    baseline_counter: Counter[
        LogEventSignature
    ] = Counter()

    incident_counter: Counter[
        LogEventSignature
    ] = Counter()

    for observation in baseline_items:
        baseline_counter.update(
            set(
                observation.signatures
            )
        )

    for observation in incident_items:
        incident_counter.update(
            set(
                observation.signatures
            )
        )

    all_signatures = (
        set(
            baseline_counter
        )
        | set(
            incident_counter
        )
    )

    differences = []

    baseline_n = len(
        baseline_items
    )

    incident_n = len(
        incident_items
    )

    for signature in all_signatures:
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

        baseline_prevalence = (
            baseline_count
            / baseline_n
        )

        incident_prevalence = (
            incident_count
            / incident_n
        )

        if (
            baseline_prevalence
            == incident_prevalence
        ):
            continue

        differences.append(
            LogSignaturePrevalence(
                signature=(
                    signature
                ),

                baseline_trace_count=(
                    baseline_count
                ),

                incident_trace_count=(
                    incident_count
                ),

                baseline_prevalence=(
                    baseline_prevalence
                ),

                incident_prevalence=(
                    incident_prevalence
                ),
            )
        )

    differences.sort(
        key=lambda item: (
            -abs(
                item.delta
            ),
            -max(
                item.baseline_prevalence,
                item.incident_prevalence,
            ),
            _signature_key(
                item.signature
            ),
        )
    )

    return LogWindowComparison(
        baseline=(
            summarize_log_window(
                baseline_items
            )
        ),

        incident=(
            summarize_log_window(
                incident_items
            )
        ),

        differences=tuple(
            differences
        ),
    )


def _signature_key(
    signature: LogEventSignature,
) -> tuple[str, str, str]:
    return (
        signature.service_name
        or "",

        signature.severity_text
        or "",

        signature.body_key,
    )
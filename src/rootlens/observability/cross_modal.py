from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.metric_identity import (
    MetricServiceBinding,
    MetricServiceRole,
)
from rootlens.observability.trace_evidence import (
    TraceEvidence,
)
from rootlens.observability.unified_evidence import (
    IncidentEvidenceBundle,
    MetricEvidenceItem,
)


class SpanLike(
    Protocol,
):
    span_id: str
    service_name: str | None


@dataclass(frozen=True)
class ServiceMetricEvidence:
    evidence: MetricEvidenceItem

    binding: MetricServiceBinding

    role: MetricServiceRole


@dataclass(frozen=True)
class TraceCorrelation:
    trace_id: str

    trace: TraceEvidence | None

    logs: tuple[
        LogEvidence,
        ...
    ]

    service_names: tuple[
        str,
        ...
    ]

    logs_with_matching_span: tuple[
        LogEvidence,
        ...
    ]

    logs_without_matching_span: tuple[
        LogEvidence,
        ...
    ]

    @property
    def trace_observed(
        self,
    ) -> bool:
        return (
            self.trace is not None
        )

    @property
    def log_count(
        self,
    ) -> int:
        return len(
            self.logs
        )


@dataclass(frozen=True)
class SpanCorrelation:
    trace_id: str
    span_id: str

    span: SpanLike | None

    logs: tuple[
        LogEvidence,
        ...
    ]

    @property
    def span_observed(
        self,
    ) -> bool:
        return (
            self.span is not None
        )

    @property
    def log_count(
        self,
    ) -> int:
        return len(
            self.logs
        )


@dataclass(frozen=True)
class ServiceCorrelation:
    service_name: str

    metrics: tuple[
        ServiceMetricEvidence,
        ...
    ]

    trace_ids: tuple[
        str,
        ...
    ]

    spans: tuple[
        SpanLike,
        ...
    ]

    logs: tuple[
        LogEvidence,
        ...
    ]

    @property
    def metric_count(
        self,
    ) -> int:
        return len(
            self.metrics
        )

    @property
    def span_count(
        self,
    ) -> int:
        return len(
            self.spans
        )

    @property
    def log_count(
        self,
    ) -> int:
        return len(
            self.logs
        )


@dataclass(frozen=True)
class CrossModalCoverage:
    metric_count: int
    bound_metric_count: int
    unbound_metric_count: int

    trace_count: int
    span_count: int
    log_count: int

    service_count: int

    logs_with_trace_id: int
    logs_without_trace_id: int

    logs_with_span_id: int
    logs_without_span_id: int

    logs_with_matching_trace: int
    logs_without_matching_trace: int

    logs_with_matching_span: int
    logs_without_matching_span: int


class CrossModalIndex:
    def __init__(
        self,
        bundle: IncidentEvidenceBundle,
        *,
        metric_bindings: tuple[
            MetricServiceBinding,
            ...
        ] = (),
    ) -> None:
        self.bundle = bundle

        self.metric_bindings = (
            metric_bindings
        )

        self._traces_by_id: dict[
            str,
            TraceEvidence,
        ] = {}

        self._spans_by_key: dict[
            tuple[str, str],
            SpanLike,
        ] = {}

        self._logs_by_trace: dict[
            str,
            list[LogEvidence],
        ] = defaultdict(
            list
        )

        self._logs_by_span: dict[
            tuple[str, str],
            list[LogEvidence],
        ] = defaultdict(
            list
        )

        self._logs_by_service: dict[
            str,
            list[LogEvidence],
        ] = defaultdict(
            list
        )

        self._spans_by_service: dict[
            str,
            list[
                tuple[
                    str,
                    SpanLike,
                ]
            ],
        ] = defaultdict(
            list
        )

        self._metrics_by_service: dict[
            str,
            list[
                ServiceMetricEvidence
            ],
        ] = defaultdict(
            list
        )

        self._bound_metric_indices: set[int] = set()

        self._validate_metric_bindings()

        self._build()

    def _validate_metric_bindings(
        self,
    ) -> None:
        metric_count = len(
            self.bundle.metrics
        )

        seen_indices = set()

        for binding in (
            self.metric_bindings
        ):
            if (
                binding.metric_index
                >= metric_count
            ):
                raise ValueError(
                    "Metric binding index "
                    "is outside bundle.metrics: "
                    f"index="
                    f"{binding.metric_index}, "
                    f"metric_count="
                    f"{metric_count}."
                )

            if (
                binding.metric_index
                in seen_indices
            ):
                raise ValueError(
                    "Only one binding is "
                    "allowed per metric index: "
                    f"{binding.metric_index}."
                )

            seen_indices.add(
                binding.metric_index
            )

        self._bound_metric_indices = (
            seen_indices
        )

    def _build(
        self,
    ) -> None:
        self._build_metrics()
        self._build_traces()
        self._build_logs()

    def _build_metrics(
        self,
    ) -> None:
        for binding in (
            self.metric_bindings
        ):
            evidence = (
                self.bundle.metrics[
                    binding.metric_index
                ]
            )

            primary = (
                ServiceMetricEvidence(
                    evidence=evidence,

                    binding=binding,

                    role=(
                        MetricServiceRole
                        .PRIMARY
                    ),
                )
            )

            self._metrics_by_service[
                binding.service_name
            ].append(
                primary
            )

            if (
                binding.peer_service_name
                is not None
            ):
                peer = (
                    ServiceMetricEvidence(
                        evidence=evidence,

                        binding=binding,

                        role=(
                            MetricServiceRole
                            .PEER
                        ),
                    )
                )

                self._metrics_by_service[
                    binding
                    .peer_service_name
                ].append(
                    peer
                )

    def _build_traces(
        self,
    ) -> None:
        for trace in (
            self.bundle.traces
        ):
            trace_id = (
                trace.trace_id
            )

            if (
                trace_id
                in self._traces_by_id
            ):
                raise ValueError(
                    "Duplicate trace evidence "
                    f"for trace_id="
                    f"{trace_id}."
                )

            self._traces_by_id[
                trace_id
            ] = trace

            for span in trace.spans:
                key = (
                    trace_id,
                    span.span_id,
                )

                if (
                    key
                    in self._spans_by_key
                ):
                    raise ValueError(
                        "Duplicate span evidence "
                        f"for trace_id="
                        f"{trace_id}, "
                        f"span_id="
                        f"{span.span_id}."
                    )

                self._spans_by_key[
                    key
                ] = span

                if span.service_name:
                    self._spans_by_service[
                        span.service_name
                    ].append(
                        (
                            trace_id,
                            span,
                        )
                    )

    def _build_logs(
        self,
    ) -> None:
        for log in (
            self.bundle.logs
        ):
            if log.trace_id:
                self._logs_by_trace[
                    log.trace_id
                ].append(
                    log
                )

            if (
                log.trace_id
                and log.span_id
            ):
                self._logs_by_span[
                    (
                        log.trace_id,
                        log.span_id,
                    )
                ].append(
                    log
                )

            if log.service_name:
                self._logs_by_service[
                    log.service_name
                ].append(
                    log
                )

    def trace_correlation(
        self,
        trace_id: str,
    ) -> TraceCorrelation | None:
        trace = (
            self._traces_by_id.get(
                trace_id
            )
        )

        logs = tuple(
            self._logs_by_trace.get(
                trace_id,
                (),
            )
        )

        if (
            trace is None
            and not logs
        ):
            return None

        matching_logs = []
        unmatched_logs = []

        services = {
            log.service_name
            for log in logs
            if log.service_name
        }

        if trace is not None:
            services.update(
                span.service_name
                for span in trace.spans
                if span.service_name
            )

        for log in logs:
            if log.span_id is None:
                unmatched_logs.append(
                    log
                )
                continue

            key = (
                trace_id,
                log.span_id,
            )

            if (
                key
                in self._spans_by_key
            ):
                matching_logs.append(
                    log
                )
            else:
                unmatched_logs.append(
                    log
                )

        return TraceCorrelation(
            trace_id=trace_id,

            trace=trace,

            logs=logs,

            service_names=tuple(
                sorted(
                    services
                )
            ),

            logs_with_matching_span=(
                tuple(
                    matching_logs
                )
            ),

            logs_without_matching_span=(
                tuple(
                    unmatched_logs
                )
            ),
        )

    def span_correlation(
        self,
        trace_id: str,
        span_id: str,
    ) -> SpanCorrelation | None:
        key = (
            trace_id,
            span_id,
        )

        span = (
            self._spans_by_key.get(
                key
            )
        )

        logs = tuple(
            self._logs_by_span.get(
                key,
                (),
            )
        )

        if (
            span is None
            and not logs
        ):
            return None

        return SpanCorrelation(
            trace_id=trace_id,

            span_id=span_id,

            span=span,

            logs=logs,
        )

    def service_correlation(
        self,
        service_name: str,
    ) -> ServiceCorrelation | None:
        metric_evidence = tuple(
            self._metrics_by_service.get(
                service_name,
                (),
            )
        )

        span_entries = tuple(
            self._spans_by_service.get(
                service_name,
                (),
            )
        )

        logs = tuple(
            self._logs_by_service.get(
                service_name,
                (),
            )
        )

        if (
            not metric_evidence
            and not span_entries
            and not logs
        ):
            return None

        trace_ids = {
            trace_id
            for (
                trace_id,
                _,
            )
            in span_entries
        }

        trace_ids.update(
            log.trace_id
            for log in logs
            if log.trace_id
        )

        spans = tuple(
            span
            for (
                _,
                span,
            )
            in span_entries
        )

        return ServiceCorrelation(
            service_name=(
                service_name
            ),

            metrics=(
                metric_evidence
            ),

            trace_ids=tuple(
                sorted(
                    trace_ids
                )
            ),

            spans=spans,

            logs=logs,
        )

    def unbound_metrics(
        self,
    ) -> tuple[
        MetricEvidenceItem,
        ...
    ]:
        return tuple(
            metric
            for index, metric
            in enumerate(
                self.bundle.metrics
            )
            if (
                index
                not in
                self._bound_metric_indices
            )
        )

    def logs_without_matching_trace(
        self,
    ) -> tuple[
        LogEvidence,
        ...
    ]:
        return tuple(
            log
            for log in self.bundle.logs
            if (
                log.trace_id is not None
                and log.trace_id
                not in self._traces_by_id
            )
        )

    def logs_without_matching_span(
        self,
    ) -> tuple[
        LogEvidence,
        ...
    ]:
        result = []

        for log in (
            self.bundle.logs
        ):
            if (
                log.trace_id is None
                or log.span_id is None
            ):
                continue

            key = (
                log.trace_id,
                log.span_id,
            )

            if (
                key
                not in self._spans_by_key
            ):
                result.append(
                    log
                )

        return tuple(
            result
        )

    def coverage(
        self,
    ) -> CrossModalCoverage:
        logs = (
            self.bundle.logs
        )

        logs_with_trace_id = sum(
            log.trace_id is not None
            for log in logs
        )

        logs_with_span_id = sum(
            log.span_id is not None
            for log in logs
        )

        logs_with_matching_trace = sum(
            (
                log.trace_id is not None
                and log.trace_id
                in self._traces_by_id
            )
            for log in logs
        )

        logs_with_matching_span = sum(
            (
                log.trace_id is not None
                and log.span_id is not None
                and (
                    log.trace_id,
                    log.span_id,
                )
                in self._spans_by_key
            )
            for log in logs
        )

        logs_with_full_context = sum(
            (
                log.trace_id is not None
                and log.span_id is not None
            )
            for log in logs
        )

        services = (
            self.service_names
        )

        return CrossModalCoverage(
            metric_count=len(
                self.bundle.metrics
            ),

            bound_metric_count=len(
                self._bound_metric_indices
            ),

            unbound_metric_count=(
                len(
                    self.bundle.metrics
                )
                - len(
                    self._bound_metric_indices
                )
            ),

            trace_count=len(
                self._traces_by_id
            ),

            span_count=len(
                self._spans_by_key
            ),

            log_count=len(
                logs
            ),

            service_count=len(
                services
            ),

            logs_with_trace_id=(
                logs_with_trace_id
            ),

            logs_without_trace_id=(
                len(logs)
                - logs_with_trace_id
            ),

            logs_with_span_id=(
                logs_with_span_id
            ),

            logs_without_span_id=(
                len(logs)
                - logs_with_span_id
            ),

            logs_with_matching_trace=(
                logs_with_matching_trace
            ),

            logs_without_matching_trace=(
                logs_with_trace_id
                - logs_with_matching_trace
            ),

            logs_with_matching_span=(
                logs_with_matching_span
            ),

            logs_without_matching_span=(
                logs_with_full_context
                - logs_with_matching_span
            ),
        )

    @property
    def service_names(
        self,
    ) -> tuple[str, ...]:
        services = set(
            self._metrics_by_service
        )

        services.update(
            self._spans_by_service
        )

        services.update(
            self._logs_by_service
        )

        return tuple(
            sorted(
                services
            )
        )
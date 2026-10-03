from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rootlens.observability.cross_modal import (
    CrossModalCoverage,
    CrossModalIndex,
    ServiceMetricEvidence,
    SpanLike,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.metric_identity import (
    MetricServiceBinding,
)
from rootlens.observability.unified_evidence import (
    EvidenceModality,
    IncidentEvidenceBundle,
    MetricEvidenceItem,
    ModalityAcquisition,
)


@dataclass(frozen=True)
class ServiceIntegrityView:
    log_count: int

    logs_without_trace_id: int
    logs_without_span_id: int

    logs_with_unmatched_trace: int
    logs_with_unmatched_span: int


@dataclass(frozen=True)
class ServiceEvidenceView:
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

    metric_acquisition: ModalityAcquisition | None

    trace_acquisition: ModalityAcquisition | None

    log_acquisition: ModalityAcquisition | None

    integrity: ServiceIntegrityView

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

    @property
    def modalities_with_evidence(
        self,
    ) -> tuple[
        EvidenceModality,
        ...
    ]:
        result = []

        if self.metrics:
            result.append(
                EvidenceModality.METRIC
            )

        if self.spans:
            result.append(
                EvidenceModality.TRACE
            )

        if self.logs:
            result.append(
                EvidenceModality.LOG
            )

        return tuple(
            result
        )


@dataclass(frozen=True)
class IncidentEvidenceView:
    incident_id: str

    start: datetime
    end: datetime

    services: tuple[
        ServiceEvidenceView,
        ...
    ]

    acquisitions: tuple[
        ModalityAcquisition,
        ...
    ]

    coverage: CrossModalCoverage

    unbound_metrics: tuple[
        MetricEvidenceItem,
        ...
    ]

    def service(
        self,
        service_name: str,
    ) -> ServiceEvidenceView | None:
        for service in (
            self.services
        ):
            if (
                service.service_name
                == service_name
            ):
                return service

        return None


def build_incident_evidence_view(
    bundle: IncidentEvidenceBundle,
    *,
    metric_bindings: tuple[
        MetricServiceBinding,
        ...
    ] = (),
) -> IncidentEvidenceView:
    index = CrossModalIndex(
        bundle,

        metric_bindings=(
            metric_bindings
        ),
    )

    services = []

    for service_name in (
        index.service_names
    ):
        correlation = (
            index.service_correlation(
                service_name
            )
        )

        if correlation is None:
            continue

        integrity = (
            _service_integrity(
                service_name=(
                    service_name
                ),

                correlation_logs=(
                    correlation.logs
                ),

                index=index,
            )
        )

        services.append(
            ServiceEvidenceView(
                service_name=(
                    service_name
                ),

                metrics=(
                    correlation.metrics
                ),

                trace_ids=(
                    correlation.trace_ids
                ),

                spans=(
                    correlation.spans
                ),

                logs=(
                    correlation.logs
                ),

                metric_acquisition=(
                    bundle.acquisition_for(
                        EvidenceModality
                        .METRIC
                    )
                ),

                trace_acquisition=(
                    bundle.acquisition_for(
                        EvidenceModality
                        .TRACE
                    )
                ),

                log_acquisition=(
                    bundle.acquisition_for(
                        EvidenceModality
                        .LOG
                    )
                ),

                integrity=(
                    integrity
                ),
            )
        )

    return IncidentEvidenceView(
        incident_id=(
            bundle.incident_id
        ),

        start=bundle.start,
        end=bundle.end,

        services=tuple(
            services
        ),

        acquisitions=(
            bundle.acquisitions
        ),

        coverage=(
            index.coverage()
        ),

        unbound_metrics=(
            index.unbound_metrics()
        ),
    )


def _service_integrity(
    *,
    service_name: str,

    correlation_logs: tuple[
        LogEvidence,
        ...
    ],

    index: CrossModalIndex,
) -> ServiceIntegrityView:
    unmatched_traces = set(
        id(log)
        for log
        in index
        .logs_without_matching_trace()
    )

    unmatched_spans = set(
        id(log)
        for log
        in index
        .logs_without_matching_span()
    )

    service_logs = tuple(
        log
        for log
        in correlation_logs
        if (
            log.service_name
            == service_name
        )
    )

    return ServiceIntegrityView(
        log_count=len(
            service_logs
        ),

        logs_without_trace_id=sum(
            log.trace_id is None
            for log in service_logs
        ),

        logs_without_span_id=sum(
            log.span_id is None
            for log in service_logs
        ),

        logs_with_unmatched_trace=sum(
            id(log)
            in unmatched_traces
            for log in service_logs
        ),

        logs_with_unmatched_span=sum(
            id(log)
            in unmatched_spans
            for log in service_logs
        ),
    )
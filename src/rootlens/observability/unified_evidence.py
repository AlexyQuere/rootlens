from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
    MetricEvidence,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.trace_evidence import (
    TraceEvidence,
)


MetricEvidenceItem = (
    MetricEvidence
    | MetricComparisonEvidence
)


class EvidenceModality(
    str,
    Enum,
):
    METRIC = "metric"
    TRACE = "trace"
    LOG = "log"


class AcquisitionState(
    str,
    Enum,
):
    OBSERVED = "observed"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ModalityAcquisition:
    modality: EvidenceModality
    state: AcquisitionState

    source_system: str

    evidence_count: int

    detail: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.source_system:
            raise ValueError(
                "source_system cannot be empty."
            )

        if self.evidence_count < 0:
            raise ValueError(
                "evidence_count cannot be negative."
            )

        if (
            self.state
            == AcquisitionState.OBSERVED
            and self.evidence_count == 0
        ):
            raise ValueError(
                "OBSERVED requires at least "
                "one evidence item."
            )

        if (
            self.state
            == AcquisitionState.EMPTY
            and self.evidence_count != 0
        ):
            raise ValueError(
                "EMPTY requires evidence_count=0."
            )

        if (
            self.state
            == AcquisitionState.UNAVAILABLE
            and self.evidence_count != 0
        ):
            raise ValueError(
                "UNAVAILABLE requires "
                "evidence_count=0."
            )


@dataclass(frozen=True)
class IncidentEvidenceBundle:
    incident_id: str

    start: datetime
    end: datetime

    metrics: tuple[
        MetricEvidenceItem,
        ...
    ] = ()

    traces: tuple[
        TraceEvidence,
        ...
    ] = ()

    logs: tuple[
        LogEvidence,
        ...
    ] = ()

    acquisitions: tuple[
        ModalityAcquisition,
        ...
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.incident_id:
            raise ValueError(
                "incident_id cannot be empty."
            )

        for name, value in (
            ("start", self.start),
            ("end", self.end),
        ):
            if (
                value.tzinfo is None
                or value.utcoffset()
                is None
            ):
                raise ValueError(
                    f"{name} must be "
                    "timezone-aware."
                )

        if self.end <= self.start:
            raise ValueError(
                "end must be after start."
            )

        modalities = [
            acquisition.modality
            for acquisition
            in self.acquisitions
        ]

        if (
            len(modalities)
            != len(
                set(modalities)
            )
        ):
            raise ValueError(
                "Only one acquisition record "
                "per modality is allowed."
            )

        self._validate_acquisition_count(
            modality=(
                EvidenceModality.METRIC
            ),
            actual_count=len(
                self.metrics
            ),
        )

        self._validate_acquisition_count(
            modality=(
                EvidenceModality.TRACE
            ),
            actual_count=len(
                self.traces
            ),
        )

        self._validate_acquisition_count(
            modality=(
                EvidenceModality.LOG
            ),
            actual_count=len(
                self.logs
            ),
        )

    def acquisition_for(
        self,
        modality: EvidenceModality,
    ) -> ModalityAcquisition | None:
        for acquisition in (
            self.acquisitions
        ):
            if (
                acquisition.modality
                == modality
            ):
                return acquisition

        return None

    @property
    def trace_ids(
        self,
    ) -> tuple[str, ...]:
        trace_ids = {
            trace.trace_id
            for trace in self.traces
        }

        trace_ids.update(
            log.trace_id
            for log in self.logs
            if log.trace_id is not None
        )

        return tuple(
            sorted(
                trace_ids
            )
        )

    @property
    def span_keys(
        self,
    ) -> tuple[
        tuple[str, str],
        ...
    ]:
        keys = {
            (
                trace.trace_id,
                span.span_id,
            )
            for trace in self.traces
            for span in trace.spans
        }

        keys.update(
            (
                log.trace_id,
                log.span_id,
            )
            for log in self.logs
            if (
                log.trace_id is not None
                and log.span_id is not None
            )
        )

        return tuple(
            sorted(
                keys
            )
        )

    @property
    def service_names(
        self,
    ) -> tuple[str, ...]:
        services = {
            span.service_name
            for trace in self.traces
            for span in trace.spans
            if span.service_name
        }

        services.update(
            log.service_name
            for log in self.logs
            if log.service_name
        )

        return tuple(
            sorted(
                services
            )
        )

    def logs_for_trace(
        self,
        trace_id: str,
    ) -> tuple[
        LogEvidence,
        ...
    ]:
        return tuple(
            log
            for log in self.logs
            if log.trace_id
            == trace_id
        )

    def logs_for_span(
        self,
        trace_id: str,
        span_id: str,
    ) -> tuple[
        LogEvidence,
        ...
    ]:
        return tuple(
            log
            for log in self.logs
            if (
                log.trace_id
                == trace_id
                and log.span_id
                == span_id
            )
        )

    def trace_by_id(
        self,
        trace_id: str,
    ) -> TraceEvidence | None:
        matches = [
            trace
            for trace in self.traces
            if trace.trace_id
            == trace_id
        ]

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                "Duplicate TraceEvidence "
                f"for trace_id={trace_id}."
            )

        return matches[0]

    def _validate_acquisition_count(
        self,
        *,
        modality: EvidenceModality,
        actual_count: int,
    ) -> None:
        acquisition = (
            self.acquisition_for(
                modality
            )
        )

        if acquisition is None:
            return

        if (
            acquisition.evidence_count
            != actual_count
        ):
            raise ValueError(
                "Acquisition evidence_count "
                "does not match the bundle "
                f"for modality="
                f"{modality.value}: "
                f"declared="
                f"{acquisition.evidence_count}, "
                f"actual={actual_count}."
            )
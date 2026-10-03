from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
    MetricEvidence,
    TimeWindow,
)
from rootlens.observability.jaeger import (
    JaegerTracePayload,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.metric_identity import (
    MetricFamily,
    MetricServiceBinding,
)
from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)
from rootlens.observability.trace_evidence import (
    TraceEvidence,
)
from rootlens.observability.unified_evidence import (
    AcquisitionState,
    EvidenceModality,
    IncidentEvidenceBundle,
    ModalityAcquisition,
)


RPC_CLIENT_PEER_BY_OPERATION = {
    "oteldemo.PaymentService/Charge":
        "payment",
}


@dataclass(frozen=True)
class LoadedMetrics:
    scenario: str

    start: datetime
    end: datetime

    comparisons: tuple[
        MetricComparisonEvidence,
        ...
    ]

    bindings: tuple[
        MetricServiceBinding,
        ...
    ]

    metric_keys: tuple[
        str,
        ...
    ]

    source_path: str


@dataclass(frozen=True)
class LoadedTraces:
    scenario: str

    start: datetime
    end: datetime

    traces: tuple[
        TraceEvidence,
        ...
    ]

    source_path: str


@dataclass(frozen=True)
class LoadedLogs:
    scenario: str

    start: datetime
    end: datetime

    logs: tuple[
        LogEvidence,
        ...
    ]

    source_path: str


@dataclass(frozen=True)
class CommonTimeWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class LoadedIncidentBundle:
    bundle: IncidentEvidenceBundle

    metric_bindings: tuple[
        MetricServiceBinding,
        ...
    ]

    metric_source: str
    trace_source: str
    log_source: str


def load_metric_artifact(
    path: str | Path,
) -> LoadedMetrics:
    artifact_path = Path(
        path
    )

    data = _read_json(
        artifact_path
    )

    scenario = _require_string(
        data,
        "scenario",
    )

    baseline = _require_mapping(
        data,
        "baseline",
    )

    incident = _require_mapping(
        data,
        "incident",
    )

    baseline_keys = tuple(
        baseline.keys()
    )

    incident_keys = tuple(
        incident.keys()
    )

    if (
        set(baseline_keys)
        != set(incident_keys)
    ):
        raise ValueError(
            "Baseline and incident metric "
            "keys differ."
        )

    comparisons = []
    bindings = []

    incident_starts = []
    incident_ends = []

    for metric_index, metric_key in enumerate(
        baseline_keys
    ):
        baseline_raw = (
            _expect_mapping(
                baseline[
                    metric_key
                ],
                (
                    "baseline."
                    f"{metric_key}"
                ),
            )
        )

        incident_raw = (
            _expect_mapping(
                incident[
                    metric_key
                ],
                (
                    "incident."
                    f"{metric_key}"
                ),
            )
        )

        baseline_evidence = (
            _metric_from_json(
                baseline_raw
            )
        )

        incident_evidence = (
            _metric_from_json(
                incident_raw
            )
        )

        comparison = (
            MetricComparisonEvidence(
                baseline=(
                    baseline_evidence
                ),

                incident=(
                    incident_evidence
                ),
            )
        )

        comparisons.append(
            comparison
        )

        incident_starts.append(
            incident_evidence
            .window.start
        )

        incident_ends.append(
            incident_evidence
            .window.end
        )

        binding = (
            _metric_binding(
                metric_index=(
                    metric_index
                ),

                metric_key=(
                    metric_key
                ),

                evidence=(
                    incident_evidence
                ),
            )
        )

        if binding is not None:
            bindings.append(
                binding
            )

    if not comparisons:
        raise ValueError(
            "Metric artifact contains "
            "no metrics."
        )

    return LoadedMetrics(
        scenario=scenario,

        start=min(
            incident_starts
        ),

        end=max(
            incident_ends
        ),

        comparisons=tuple(
            comparisons
        ),

        bindings=tuple(
            bindings
        ),

        metric_keys=(
            baseline_keys
        ),

        source_path=str(
            artifact_path
        ),
    )


def load_trace_artifact(
    path: str | Path,
    *,
    phase: str = "incident",
) -> LoadedTraces:
    if phase not in (
        "baseline",
        "incident",
    ):
        raise ValueError(
            "phase must be "
            "'baseline' or 'incident'."
        )

    artifact_path = Path(
        path
    )

    data = _read_json(
        artifact_path
    )

    scenario = _require_string(
        data,
        "scenario",
    )

    window = _require_mapping(
        data,
        phase,
    )

    start = _parse_datetime(
        _require_string(
            window,
            "start",
        )
    )

    end = _parse_datetime(
        _require_string(
            window,
            "end",
        )
    )

    raw_traces = window.get(
        "raw_traces"
    )

    if not isinstance(
        raw_traces,
        list,
    ):
        raise ValueError(
            f"{phase}.raw_traces "
            "must be a list."
        )

    traces = []

    for index, raw_trace in enumerate(
        raw_traces
    ):
        raw_trace = (
            _expect_mapping(
                raw_trace,
                (
                    f"{phase}."
                    f"raw_traces[{index}]"
                ),
            )
        )

        expected_trace_id = (
            _require_string(
                raw_trace,
                "trace_id",
            )
        )

        resource_spans = (
            raw_trace.get(
                "resource_spans"
            )
        )

        if not isinstance(
            resource_spans,
            list,
        ):
            raise ValueError(
                "resource_spans must "
                "be a list."
            )

        payload = (
            JaegerTracePayload(
                resource_spans=tuple(
                    _expect_mapping(
                        item,
                        (
                            "resource_spans"
                            f"[{item_index}]"
                        ),
                    )
                    for item_index, item
                    in enumerate(
                        resource_spans
                    )
                )
            )
        )

        parsed = (
            parse_otlp_traces(
                payload
            )
        )

        matching = [
            trace
            for trace in parsed
            if trace.trace_id
            == expected_trace_id
        ]

        if len(
            matching
        ) != 1:
            raise ValueError(
                "Expected exactly one "
                "parsed TraceEvidence for "
                f"trace_id="
                f"{expected_trace_id}, "
                f"found={len(matching)}."
            )

        traces.append(
            matching[0]
        )

    return LoadedTraces(
        scenario=scenario,

        start=start,
        end=end,

        traces=tuple(
            traces
        ),

        source_path=str(
            artifact_path
        ),
    )


def load_log_artifact(
    path: str | Path,
    *,
    phase: str = "incident",
) -> LoadedLogs:
    if phase not in (
        "baseline",
        "incident",
    ):
        raise ValueError(
            "phase must be "
            "'baseline' or 'incident'."
        )

    artifact_path = Path(
        path
    )

    data = _read_json(
        artifact_path
    )

    scenario = _require_string(
        data,
        "scenario",
    )

    window = _require_mapping(
        data,
        phase,
    )

    start = _parse_datetime(
        _require_string(
            window,
            "original_start",
        )
    )

    end = _parse_datetime(
        _require_string(
            window,
            "original_end",
        )
    )

    trace_records = window.get(
        "traces"
    )

    if not isinstance(
        trace_records,
        list,
    ):
        raise ValueError(
            f"{phase}.traces must "
            "be a list."
        )

    logs = []

    for trace_index, trace_record in enumerate(
        trace_records
    ):
        trace_record = (
            _expect_mapping(
                trace_record,
                (
                    f"{phase}.traces"
                    f"[{trace_index}]"
                ),
            )
        )

        trace_logs = (
            trace_record.get(
                "logs"
            )
        )

        if not isinstance(
            trace_logs,
            list,
        ):
            raise ValueError(
                "trace logs must "
                "be a list."
            )

        for log_index, raw_log in enumerate(
            trace_logs
        ):
            logs.append(
                _log_from_json(
                    _expect_mapping(
                        raw_log,
                        (
                            "logs"
                            f"[{log_index}]"
                        ),
                    )
                )
            )

    return LoadedLogs(
        scenario=scenario,

        start=start,
        end=end,

        logs=tuple(
            logs
        ),

        source_path=str(
            artifact_path
        ),
    )


def load_single_trace_log_artifact(
    path: str | Path,
) -> LoadedLogs:
    artifact_path = Path(
        path
    )

    data = _read_json(
        artifact_path
    )

    scenario = str(
        data.get(
            "case",
            "unknown",
        )
    )

    query = _require_mapping(
        data,
        "query",
    )

    start = _parse_datetime(
        _require_string(
            query,
            "start",
        )
    )

    end = _parse_datetime(
        _require_string(
            query,
            "end",
        )
    )

    raw_logs = data.get(
        "logs"
    )

    if not isinstance(
        raw_logs,
        list,
    ):
        raise ValueError(
            "logs must be a list."
        )

    logs = tuple(
        _log_from_json(
            _expect_mapping(
                raw_log,
                f"logs[{index}]",
            )
        )
        for index, raw_log
        in enumerate(
            raw_logs
        )
    )

    return LoadedLogs(
        scenario=scenario,

        start=start,
        end=end,

        logs=logs,

        source_path=str(
            artifact_path
        ),
    )


def common_time_window(
    *slices: (
        LoadedMetrics
        | LoadedTraces
        | LoadedLogs
    ),
) -> CommonTimeWindow | None:
    if not slices:
        raise ValueError(
            "At least one evidence "
            "slice is required."
        )

    start = max(
        evidence.start
        for evidence
        in slices
    )

    end = min(
        evidence.end
        for evidence
        in slices
    )

    if end <= start:
        return None

    return CommonTimeWindow(
        start=start,
        end=end,
    )


def build_incident_bundle(
    *,
    incident_id: str,

    metrics: LoadedMetrics,
    traces: LoadedTraces,
    logs: LoadedLogs,
) -> LoadedIncidentBundle:
    scenarios = {
        metrics.scenario,
        traces.scenario,
        logs.scenario,
    }

    if len(
        scenarios
    ) != 1:
        raise ValueError(
            "Artifacts do not describe "
            "the same scenario: "
            f"{sorted(scenarios)}"
        )

    common = common_time_window(
        metrics,
        traces,
        logs,
    )

    if common is None:
        raise ValueError(
            "Artifacts are not "
            "temporally compatible. "
            "Do not merge evidence from "
            "different experiment runs."
        )

    bundle = (
        IncidentEvidenceBundle(
            incident_id=(
                incident_id
            ),

            start=common.start,
            end=common.end,

            metrics=(
                metrics.comparisons
            ),

            traces=(
                traces.traces
            ),

            logs=(
                logs.logs
            ),

            acquisitions=(
                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .METRIC
                    ),

                    state=(
                        _acquisition_state(
                            len(
                                metrics
                                .comparisons
                            )
                        )
                    ),

                    source_system=(
                        "prometheus"
                    ),

                    evidence_count=len(
                        metrics.comparisons
                    ),
                ),

                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .TRACE
                    ),

                    state=(
                        _acquisition_state(
                            len(
                                traces.traces
                            )
                        )
                    ),

                    source_system=(
                        "jaeger"
                    ),

                    evidence_count=len(
                        traces.traces
                    ),
                ),

                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .LOG
                    ),

                    state=(
                        _acquisition_state(
                            len(
                                logs.logs
                            )
                        )
                    ),

                    source_system=(
                        "opensearch"
                    ),

                    evidence_count=len(
                        logs.logs
                    ),
                ),
            ),
        )
    )

    return LoadedIncidentBundle(
        bundle=bundle,

        metric_bindings=(
            metrics.bindings
        ),

        metric_source=(
            metrics.source_path
        ),

        trace_source=(
            traces.source_path
        ),

        log_source=(
            logs.source_path
        ),
    )


def _metric_from_json(
    raw: Mapping[str, Any],
) -> MetricEvidence:
    window_raw = _require_mapping(
        raw,
        "window",
    )

    labels_raw = raw.get(
        "labels"
    )

    labels = None

    if labels_raw is not None:
        labels_mapping = (
            _expect_mapping(
                labels_raw,
                "labels",
            )
        )

        labels = {}

        for key, value in (
            labels_mapping.items()
        ):
            if (
                not isinstance(
                    key,
                    str,
                )
                or not isinstance(
                    value,
                    str,
                )
            ):
                raise ValueError(
                    "Metric labels must "
                    "be string-to-string."
                )

            labels[
                key
            ] = value

    service = raw.get(
        "service"
    )

    if (
        service is not None
        and not isinstance(
            service,
            str,
        )
    ):
        raise ValueError(
            "Metric service must "
            "be a string or null."
        )

    value = raw.get(
        "value"
    )

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        raise ValueError(
            "Metric value must "
            "be numeric."
        )

    return MetricEvidence(
        name=_require_string(
            raw,
            "name",
        ),

        statistic=(
            _require_string(
                raw,
                "statistic",
            )
        ),

        value=float(
            value
        ),

        unit=_require_string(
            raw,
            "unit",
        ),

        service=service,

        window=TimeWindow(
            start=_parse_datetime(
                _require_string(
                    window_raw,
                    "start",
                )
            ),

            end=_parse_datetime(
                _require_string(
                    window_raw,
                    "end",
                )
            ),
        ),

        promql=_require_string(
            raw,
            "promql",
        ),

        source=str(
            raw.get(
                "source",
                "prometheus",
            )
        ),

        labels=labels,
    )


def _metric_binding(
    *,
    metric_index: int,
    metric_key: str,
    evidence: MetricEvidence,
) -> MetricServiceBinding | None:
    if evidence.service is None:
        return None

    labels = evidence.labels

    if labels is None:
        return None

    family_raw = labels.get(
        "metric_family"
    )

    if family_raw is None:
        return None

    try:
        family = MetricFamily(
            family_raw
        )

    except ValueError:
        return None

    if (
        family
        != MetricFamily.RPC_CLIENT
    ):
        return MetricServiceBinding(
            metric_index=(
                metric_index
            ),

            metric_key=(
                metric_key
            ),

            family=family,

            service_name=(
                evidence.service
            ),
        )

    operation = labels.get(
        "operation"
    )

    if operation is None:
        return None

    peer = (
        RPC_CLIENT_PEER_BY_OPERATION
        .get(
            operation
        )
    )

    if peer is None:
        return None

    return MetricServiceBinding(
        metric_index=(
            metric_index
        ),

        metric_key=metric_key,

        family=family,

        service_name=(
            evidence.service
        ),

        peer_service_name=peer,
    )


def _log_from_json(
    raw: Mapping[str, Any],
) -> LogEvidence:
    event_raw = raw.get(
        "event_timestamp"
    )

    observed_raw = raw.get(
        "observed_timestamp"
    )

    event_timestamp = (
        _parse_optional_datetime(
            event_raw
        )
    )

    observed_timestamp = (
        _parse_optional_datetime(
            observed_raw
        )
    )

    service_name = raw.get(
        "service_name"
    )

    severity_text = raw.get(
        "severity_text"
    )

    trace_id = raw.get(
        "trace_id"
    )

    span_id = raw.get(
        "span_id"
    )

    return LogEvidence(
        event_timestamp=(
            event_timestamp
        ),

        event_timestamp_raw=(
            event_raw
            if isinstance(
                event_raw,
                str,
            )
            else None
        ),

        observed_timestamp=(
            observed_timestamp
        ),

        observed_timestamp_raw=(
            observed_raw
            if isinstance(
                observed_raw,
                str,
            )
            else None
        ),

        service_name=(
            service_name
            if isinstance(
                service_name,
                str,
            )
            else None
        ),

        severity_text=(
            severity_text
            if isinstance(
                severity_text,
                str,
            )
            else None
        ),

        severity_number=(
            raw.get(
                "severity_number"
            )
        ),

        body=raw.get(
            "body"
        ),

        trace_id=(
            trace_id
            if isinstance(
                trace_id,
                str,
            )
            else None
        ),

        span_id=(
            span_id
            if isinstance(
                span_id,
                str,
            )
            else None
        ),

        attributes=dict(
            _expect_mapping(
                raw.get(
                    "attributes",
                    {},
                ),
                "attributes",
            )
        ),

        resource_attributes=dict(
            _expect_mapping(
                raw.get(
                    "resource",
                    {},
                ),
                "resource",
            )
        ),

        instrumentation_scope=dict(
            _expect_mapping(
                raw.get(
                    "instrumentation_scope",
                    {},
                ),
                (
                    "instrumentation_scope"
                ),
            )
        ),

        index=_require_string(
            raw,
            "index",
        ),

        document_id=(
            _require_string(
                raw,
                "document_id",
            )
        ),

        raw_source=dict(
            _expect_mapping(
                raw.get(
                    "raw_source",
                    {},
                ),
                "raw_source",
            )
        ),
    )


def _acquisition_state(
    count: int,
) -> AcquisitionState:
    if count > 0:
        return (
            AcquisitionState
            .OBSERVED
        )

    return AcquisitionState.EMPTY


def _parse_optional_datetime(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Timestamp must be "
            "a string or null."
        )

    return _parse_datetime(
        value
    )


def _parse_datetime(
    value: str,
) -> datetime:
    result = (
        datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    )

    if (
        result.tzinfo is None
        or result.utcoffset()
        is None
    ):
        raise ValueError(
            "Timestamp must be "
            "timezone-aware."
        )

    return result


def _read_json(
    path: Path,
) -> Mapping[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return _expect_mapping(
        value,
        str(path),
    )


def _require_string(
    mapping: Mapping[str, Any],
    key: str,
) -> str:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"{key} must be "
            "a string."
        )

    return value


def _require_mapping(
    mapping: Mapping[str, Any],
    key: str,
) -> Mapping[str, Any]:
    if key not in mapping:
        raise ValueError(
            f"Missing key: {key}"
        )

    return _expect_mapping(
        mapping[
            key
        ],
        key,
    )


def _expect_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise ValueError(
            f"{name} must be "
            "a mapping."
        )

    return value
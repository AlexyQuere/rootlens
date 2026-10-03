from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, TypeVar

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
    MetricEvidence,
    TimeWindow,
)
from rootlens.observability.incident_view import (
    IncidentEvidenceView,
    build_incident_evidence_view,
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
from rootlens.observability.unified_evidence import (
    AcquisitionState,
    EvidenceModality,
    IncidentEvidenceBundle,
    ModalityAcquisition,
)


E = TypeVar("E")


RPC_CLIENT_PEERS = {
    "oteldemo.PaymentService/Charge":
        "payment",
}


@dataclass(frozen=True)
class SyncedIncidentEvidence:
    scenario: str
    bundle: IncidentEvidenceBundle
    metric_bindings: tuple[
        MetricServiceBinding,
        ...
    ]
    view: IncidentEvidenceView


def load_synced_incident_evidence(
    path: str | Path,
) -> SyncedIncidentEvidence:
    artifact_path = Path(
        path
    )

    artifact = _read_json(
        artifact_path
    )

    if (
        artifact.get(
            "experiment"
        )
        != "015D"
    ):
        raise ValueError(
            "Expected an Experiment "
            "015D artifact."
        )

    scenario = _require_string(
        artifact,
        "scenario",
    )

    baseline = _require_mapping(
        artifact,
        "baseline",
    )

    incident = _require_mapping(
        artifact,
        "incident",
    )

    incident_window_raw = (
        _require_mapping(
            incident,
            "window",
        )
    )

    incident_start = (
        _parse_datetime(
            _require_string(
                incident_window_raw,
                "start",
            )
        )
    )

    incident_end = (
        _parse_datetime(
            _require_string(
                incident_window_raw,
                "end",
            )
        )
    )

    (
        metric_comparisons,
        metric_bindings,
    ) = _load_metric_comparisons(
        baseline=baseline,
        incident=incident,
    )

    traces = _load_incident_traces(
        incident
    )

    logs = _load_incident_logs(
        incident
    )

    acquisitions = (
        ModalityAcquisition(
            modality=_enum_member(
                EvidenceModality,
                "metric",
                "metrics",
            ),
            state=_acquisition_state(
                len(
                    metric_comparisons
                )
            ),
            source_system=(
                "prometheus"
            ),
            evidence_count=len(
                metric_comparisons
            ),
        ),
        ModalityAcquisition(
            modality=_enum_member(
                EvidenceModality,
                "trace",
                "traces",
            ),
            state=_acquisition_state(
                len(
                    traces
                )
            ),
            source_system=(
                "jaeger"
            ),
            evidence_count=len(
                traces
            ),
        ),
        ModalityAcquisition(
            modality=_enum_member(
                EvidenceModality,
                "log",
                "logs",
            ),
            state=_acquisition_state(
                len(
                    logs
                )
            ),
            source_system=(
                "opensearch"
            ),
            evidence_count=len(
                logs
            ),
        ),
    )

    bundle = IncidentEvidenceBundle(
        incident_id=(
            f"015D:"
            f"{scenario}:"
            f"{incident_start.isoformat()}"
        ),
        start=incident_start,
        end=incident_end,
        metrics=metric_comparisons,
        traces=traces,
        logs=logs,
        acquisitions=(
            acquisitions
        ),
    )

    view = (
        build_incident_evidence_view(
            bundle,
            metric_bindings=(
                metric_bindings
            ),
        )
    )

    return SyncedIncidentEvidence(
        scenario=scenario,
        bundle=bundle,
        metric_bindings=(
            metric_bindings
        ),
        view=view,
    )


def _load_metric_comparisons(
    *,
    baseline: Mapping[str, Any],
    incident: Mapping[str, Any],
) -> tuple[
    tuple[
        MetricComparisonEvidence,
        ...
    ],
    tuple[
        MetricServiceBinding,
        ...
    ],
]:
    baseline_raw = (
        _require_mapping(
            baseline,
            "metrics",
        )
    )

    incident_raw = (
        _require_mapping(
            incident,
            "metrics",
        )
    )

    baseline_keys = tuple(
        baseline_raw.keys()
    )

    incident_keys = tuple(
        incident_raw.keys()
    )

    if set(
        baseline_keys
    ) != set(
        incident_keys
    ):
        raise ValueError(
            "Baseline and incident "
            "metric keys differ."
        )

    comparisons = []
    bindings = []

    for index, key in enumerate(
        baseline_keys
    ):
        baseline_metric = (
            _metric_from_json(
                _expect_mapping(
                    baseline_raw[
                        key
                    ],
                    (
                        "baseline."
                        f"metrics.{key}"
                    ),
                )
            )
        )

        incident_metric = (
            _metric_from_json(
                _expect_mapping(
                    incident_raw[
                        key
                    ],
                    (
                        "incident."
                        f"metrics.{key}"
                    ),
                )
            )
        )

        _validate_same_metric_identity(
            key=key,
            baseline=baseline_metric,
            incident=incident_metric,
        )

        comparison = (
            MetricComparisonEvidence(
                baseline=(
                    baseline_metric
                ),
                incident=(
                    incident_metric
                ),
            )
        )

        comparisons.append(
            comparison
        )

        binding = (
            _metric_binding(
                metric_index=index,
                metric_key=key,
                evidence=(
                    incident_metric
                ),
            )
        )

        if binding is not None:
            bindings.append(
                binding
            )

    return (
        tuple(
            comparisons
        ),
        tuple(
            bindings
        ),
    )


def _load_incident_traces(
    incident: Mapping[str, Any],
):
    traces_raw = _require_mapping(
        incident,
        "traces",
    )

    expected_ids_raw = (
        traces_raw.get(
            "trace_ids"
        )
    )

    if not isinstance(
        expected_ids_raw,
        list,
    ):
        raise ValueError(
            "incident.traces."
            "trace_ids must be "
            "a list."
        )

    expected_ids = tuple(
        _expect_string(
            value,
            "trace_id",
        )
        for value in (
            expected_ids_raw
        )
    )

    resource_spans_raw = (
        traces_raw.get(
            "resource_spans"
        )
    )

    if not isinstance(
        resource_spans_raw,
        list,
    ):
        raise ValueError(
            "incident.traces."
            "resource_spans must "
            "be a list."
        )

    payload = JaegerTracePayload(
        resource_spans=tuple(
            _expect_mapping(
                value,
                (
                    "incident.traces."
                    f"resource_spans[{index}]"
                ),
            )
            for index, value
            in enumerate(
                resource_spans_raw
            )
        )
    )

    traces = (
        parse_otlp_traces(
            payload
        )
    )

    parsed_ids = tuple(
        trace.trace_id
        for trace in traces
    )

    if set(
        parsed_ids
    ) != set(
        expected_ids
    ):
        missing = sorted(
            set(
                expected_ids
            )
            - set(
                parsed_ids
            )
        )

        extra = sorted(
            set(
                parsed_ids
            )
            - set(
                expected_ids
            )
        )

        raise ValueError(
            "Parsed trace IDs differ "
            "from captured trace IDs. "
            f"missing={missing}, "
            f"extra={extra}"
        )

    if len(
        parsed_ids
    ) != len(
        expected_ids
    ):
        raise ValueError(
            "Parsed trace count differs "
            "from captured trace count."
        )

    return traces


def _load_incident_logs(
    incident: Mapping[str, Any],
) -> tuple[
    LogEvidence,
    ...
]:
    logs_raw = _require_mapping(
        incident,
        "logs",
    )

    trace_results = logs_raw.get(
        "traces"
    )

    if not isinstance(
        trace_results,
        list,
    ):
        raise ValueError(
            "incident.logs.traces "
            "must be a list."
        )

    logs = []

    for trace_index, trace_value in (
        enumerate(
            trace_results
        )
    ):
        trace_result = (
            _expect_mapping(
                trace_value,
                (
                    "incident.logs."
                    f"traces[{trace_index}]"
                ),
            )
        )

        expected_trace_id = (
            _require_string(
                trace_result,
                "trace_id",
            )
        )

        raw_logs = trace_result.get(
            "logs"
        )

        if not isinstance(
            raw_logs,
            list,
        ):
            raise ValueError(
                "Per-trace logs must "
                "be a list."
            )

        for log_index, raw_log_value in (
            enumerate(
                raw_logs
            )
        ):
            raw_log = (
                _expect_mapping(
                    raw_log_value,
                    (
                        "incident.logs."
                        f"traces[{trace_index}]."
                        f"logs[{log_index}]"
                    ),
                )
            )

            log = _log_from_json(
                raw_log
            )

            if (
                log.trace_id
                != expected_trace_id
            ):
                raise ValueError(
                    "Log trace ID differs "
                    "from its exact "
                    "trace query."
                )

            logs.append(
                log
            )

    expected_total = (
        logs_raw.get(
            "total_logs"
        )
    )

    if (
        not isinstance(
            expected_total,
            int,
        )
    ):
        raise ValueError(
            "incident.logs.total_logs "
            "must be an integer."
        )

    if len(
        logs
    ) != expected_total:
        raise ValueError(
            "Parsed log count differs "
            "from artifact total_logs: "
            f"{len(logs)} != "
            f"{expected_total}"
        )

    return tuple(
        logs
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
                "metric.labels",
            )
        )

        labels = {
            _expect_string(
                key,
                "metric label key",
            ):
            _expect_string(
                value,
                "metric label value",
            )
            for key, value
            in labels_mapping.items()
        }

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
            "be string or null."
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
        statistic=_require_string(
            raw,
            "statistic",
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


def _log_from_json(
    raw: Mapping[str, Any],
) -> LogEvidence:
    event_value = raw.get(
        "event_timestamp"
    )

    observed_value = raw.get(
        "observed_timestamp"
    )

    event_raw = raw.get(
        "event_timestamp_raw"
    )

    observed_raw = raw.get(
        "observed_timestamp_raw"
    )

    return LogEvidence(
        event_timestamp=(
            _parse_optional_datetime(
                event_value
            )
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
            _parse_optional_datetime(
                observed_value
            )
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
            raw.get(
                "service_name"
            )
            if isinstance(
                raw.get(
                    "service_name"
                ),
                str,
            )
            else None
        ),
        severity_text=(
            raw.get(
                "severity_text"
            )
            if isinstance(
                raw.get(
                    "severity_text"
                ),
                str,
            )
            else None
        ),
        severity_number=(
            raw.get(
                "severity_number"
            )
            if isinstance(
                raw.get(
                    "severity_number"
                ),
                int,
            )
            else None
        ),
        body=raw.get(
            "body"
        ),
        trace_id=(
            raw.get(
                "trace_id"
            )
            if isinstance(
                raw.get(
                    "trace_id"
                ),
                str,
            )
            else None
        ),
        span_id=(
            raw.get(
                "span_id"
            )
            if isinstance(
                raw.get(
                    "span_id"
                ),
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
                "log.attributes",
            )
        ),
        resource_attributes=dict(
            _expect_mapping(
                raw.get(
                    "resource",
                    {},
                ),
                "log.resource",
            )
        ),
        instrumentation_scope=dict(
            _expect_mapping(
                raw.get(
                    "instrumentation_scope",
                    {},
                ),
                (
                    "log."
                    "instrumentation_scope"
                ),
            )
        ),
        index=_require_string(
            raw,
            "index",
        ),
        document_id=_require_string(
            raw,
            "document_id",
        ),
        raw_source=dict(
            _expect_mapping(
                raw.get(
                    "raw_source",
                    {},
                ),
                "log.raw_source",
            )
        ),
    )


def _validate_same_metric_identity(
    *,
    key: str,
    baseline: MetricEvidence,
    incident: MetricEvidence,
) -> None:
    baseline_identity = (
        baseline.name,
        baseline.statistic,
        baseline.unit,
        baseline.service,
        dict(
            baseline.labels
            or {}
        ),
    )

    incident_identity = (
        incident.name,
        incident.statistic,
        incident.unit,
        incident.service,
        dict(
            incident.labels
            or {}
        ),
    )

    if (
        baseline_identity
        != incident_identity
    ):
        raise ValueError(
            "Baseline/incident metric "
            "identity differs for "
            f"{key}."
        )


def _metric_binding(
    *,
    metric_index: int,
    metric_key: str,
    evidence: MetricEvidence,
) -> MetricServiceBinding | None:
    if evidence.service is None:
        return None

    labels = dict(
        evidence.labels
        or {}
    )

    family_raw = labels.get(
        "metric_family"
    )

    if family_raw is None:
        return None

    family = _enum_member(
        MetricFamily,
        family_raw,
    )

    if (
        _normalized_enum(
            family
        )
        != "rpcclient"
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

    peer = (
        RPC_CLIENT_PEERS.get(
            operation
        )
    )

    if peer is None:
        raise ValueError(
            "RPC client metric has "
            "no explicit peer binding: "
            f"key={metric_key}, "
            f"operation={operation}"
        )

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
        peer_service_name=peer,
    )


def _acquisition_state(
    count: int,
) -> AcquisitionState:
    if count > 0:
        return _enum_member(
            AcquisitionState,
            "observed",
        )

    return _enum_member(
        AcquisitionState,
        "empty",
    )


def _enum_member(
    enum_type,
    *candidates: str,
):
    normalized_candidates = {
        _normalize(
            candidate
        )
        for candidate in candidates
    }

    for member in enum_type:
        member_names = {
            _normalize(
                member.name
            ),
            _normalize(
                str(
                    member.value
                )
            ),
        }

        if (
            member_names
            & normalized_candidates
        ):
            return member

    available = [
        (
            member.name,
            member.value,
        )
        for member in enum_type
    ]

    raise ValueError(
        "Could not resolve enum "
        f"{enum_type.__name__} "
        f"for {candidates}. "
        f"Available: {available}"
    )


def _normalized_enum(
    member,
) -> str:
    return _normalize(
        str(
            member.value
        )
    )


def _normalize(
    value: str,
) -> str:
    return "".join(
        character
        for character in value.lower()
        if character.isalnum()
    )


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
            "string or null."
        )

    return _parse_datetime(
        value
    )


def _parse_datetime(
    value: str,
) -> datetime:
    result = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
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
        str(
            path
        ),
    )


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


def _require_string(
    mapping: Mapping[str, Any],
    key: str,
) -> str:
    if key not in mapping:
        raise ValueError(
            f"Missing key: {key}"
        )

    return _expect_string(
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


def _expect_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"{name} must be "
            "a string."
        )

    return value
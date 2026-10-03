from __future__ import annotations

import copy

from dataclasses import asdict
from datetime import (
    datetime,
    timezone,
)

from rootlens.evaluation.trace_incident import (
    ClientServerRelationSpec,
    observe_relation,
    summarize_observations,
)

from rootlens.observability.jaeger import (
    JaegerClient,
    JaegerError,
)

from rootlens.observability.otlp_trace import (
    OTLPTraceParseError,
    parse_otlp_traces,
)

from rootlens.observability.trace_evidence import (
    SpanKind,
    TraceEvidence,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


def capture_relation_window(
    *,
    client: JaegerClient,
    tool: TraceInvestigationTool,
    relation_spec: ClientServerRelationSpec,
    start: datetime,
    end: datetime,
    search_service: str,
    search_operation: str,
    max_traces: int = 200,
) -> dict:

    _validate_window(
        start=start,
        end=end,
    )

    if max_traces <= 0:
        raise ValueError(
            "max_traces must be positive."
        )

    search_payload = client.find_traces(
        service_name=search_service,
        operation_name=search_operation,
        start=start,
        end=end,
        num_traces=max_traces,
    )

    search_traces = parse_otlp_traces(
        search_payload
    )

    discovered_trace_ids = tuple(
        sorted(
            {
                trace.trace_id
                for trace
                in search_traces
            }
        )
    )

    observations = []

    frozen_raw_traces = []

    fetch_errors = []

    excluded_no_target_span = []

    for trace_id in discovered_trace_ids:

        try:
            payload = client.get_trace(
                trace_id
            )

            traces = parse_otlp_traces(
                payload
            )

        except (
            JaegerError,
            OTLPTraceParseError,
        ) as exc:

            fetch_errors.append(
                {
                    "trace_id":
                        trace_id,
                    "error":
                        str(exc),
                }
            )

            continue

        matching = [
            trace
            for trace in traces
            if trace.trace_id == trace_id
        ]

        if len(matching) != 1:

            fetch_errors.append(
                {
                    "trace_id":
                        trace_id,
                    "error":
                        (
                            "Expected exactly "
                            "one fetched trace; "
                            f"got {len(matching)}."
                        ),
                }
            )

            continue

        trace = matching[0]

        if not trace_has_span_in_window(
            trace,
            start=start,
            end=end,
            service_name=search_service,
            operation_name=(
                search_operation
            ),
            kind=SpanKind.SERVER,
        ):

            excluded_no_target_span.append(
                trace_id
            )

            continue

        observation = observe_relation(
            trace,
            spec=relation_spec,
            tool=tool,
        )

        observations.append(
            observation
        )

        frozen_raw_traces.append(
            {
                "trace_id":
                    trace_id,

                "resource_spans":
                    copy.deepcopy(
                        list(
                            payload
                            .resource_spans
                        )
                    ),
            }
        )

    observations_tuple = tuple(
        observations
    )

    summary = summarize_observations(
        observations_tuple
    )

    return {
        "start":
            start.isoformat(),

        "end":
            end.isoformat(),

        "captured_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "search": {
            "service_name":
                search_service,

            "operation_name":
                search_operation,

            "max_traces":
                max_traces,

            "discovered_trace_ids":
                list(
                    discovered_trace_ids
                ),

            "discovered_trace_count":
                len(
                    discovered_trace_ids
                ),
        },

        "fetched_trace_count":
            len(
                observations_tuple
            ),

        "fetch_errors":
            fetch_errors,

        "excluded_no_target_span":
            excluded_no_target_span,

        "summary":
            asdict(
                summary
            ),

        "observations": [
            asdict(
                observation
            )
            for observation
            in observations_tuple
        ],

        "raw_traces":
            frozen_raw_traces,
    }


def trace_has_span_in_window(
    trace: TraceEvidence,
    *,
    start: datetime,
    end: datetime,
    service_name: str,
    operation_name: str,
    kind: SpanKind,
) -> bool:

    _validate_window(
        start=start,
        end=end,
    )

    for span in trace.spans:

        if (
            span.service_name
            != service_name
        ):
            continue

        if (
            span.operation_name
            != operation_name
        ):
            continue

        if span.kind != kind:
            continue

        if (
            start
            <= span.start_time
            <= end
        ):
            return True

    return False


def _validate_window(
    *,
    start: datetime,
    end: datetime,
) -> None:

    if (
        start.tzinfo is None
        or start.utcoffset()
        is None
    ):
        raise ValueError(
            "start must be timezone-aware."
        )

    if (
        end.tzinfo is None
        or end.utcoffset()
        is None
    ):
        raise ValueError(
            "end must be timezone-aware."
        )

    if end <= start:
        raise ValueError(
            "end must be after start."
        )
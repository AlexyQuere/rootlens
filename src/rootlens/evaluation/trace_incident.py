from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from rootlens.observability.trace_evidence import (
    SpanEvidence,
    SpanKind,
    TraceEvidence,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


RelationClass = Literal[
    "no_client",
    "multiple_clients",
    "client_error_no_server",
    "client_non_error_no_server",
    "client_error_server_error",
    "client_error_server_non_error",
    "client_non_error_server_error",
    "client_non_error_server_non_error",
    "multiple_server_children",
]


@dataclass(frozen=True)
class ClientServerRelationSpec:

    client_service: str
    client_operation: str

    server_service: str
    server_operation: str


@dataclass(frozen=True)
class RelationObservation:

    trace_id: str

    classification: RelationClass

    client_span_count: int
    server_span_count: int

    client_span_ids: tuple[str, ...]
    server_span_ids: tuple[str, ...]

    client_status_codes: tuple[str, ...]
    server_status_codes: tuple[str, ...]

    client_status_messages: tuple[
        str | None,
        ...
    ]

    server_status_messages: tuple[
        str | None,
        ...
    ]

    root_count: int
    orphan_count: int

    temporal_violation_count: int
    max_temporal_skew_ms: float

    root_interval_violation_count: int
    max_root_interval_skew_ms: float


@dataclass(frozen=True)
class RelationWindowSummary:

    trace_count: int

    class_counts: tuple[
        tuple[str, int],
        ...
    ]

    client_observed_count: int
    client_error_count: int

    server_observed_count: int
    server_error_count: int

    client_error_no_server_count: int
    client_non_error_no_server_count: int


def observe_relation(
    trace: TraceEvidence,
    *,
    spec: ClientServerRelationSpec,
    tool: TraceInvestigationTool,
) -> RelationObservation:

    clients = tool.find_spans(
        trace,
        service_name=(
            spec.client_service
        ),
        operation_name=(
            spec.client_operation
        ),
        kind=SpanKind.CLIENT,
    )

    pairs = (
        tool.find_client_server_pairs(
            trace
        )
    )

    matching_servers: list[
        SpanEvidence
    ] = []

    for pair in pairs:

        if (
            pair.client.service_name
            != spec.client_service
        ):
            continue

        if (
            pair.client.operation_name
            != spec.client_operation
        ):
            continue

        if (
            pair.server.service_name
            != spec.server_service
        ):
            continue

        if (
            pair.server.operation_name
            != spec.server_operation
        ):
            continue

        matching_servers.append(
            pair.server
        )

    classification = (
        _classify(
            clients=clients,
            servers=tuple(
                matching_servers
            ),
        )
    )

    integrity = trace.integrity

    return RelationObservation(
        trace_id=trace.trace_id,

        classification=(
            classification
        ),

        client_span_count=len(
            clients
        ),

        server_span_count=len(
            matching_servers
        ),

        client_span_ids=tuple(
            span.span_id
            for span in clients
        ),

        server_span_ids=tuple(
            span.span_id
            for span
            in matching_servers
        ),

        client_status_codes=tuple(
            span.status_code.name
            for span in clients
        ),

        server_status_codes=tuple(
            span.status_code.name
            for span
            in matching_servers
        ),

        client_status_messages=tuple(
            span.status_message
            for span in clients
        ),

        server_status_messages=tuple(
            span.status_message
            for span
            in matching_servers
        ),

        root_count=(
            integrity.root_count
        ),

        orphan_count=(
            integrity.orphan_count
        ),

        temporal_violation_count=(
            integrity
            .temporal_violation_count
        ),

        max_temporal_skew_ms=(
            integrity
            .max_temporal_skew_ms
        ),

        root_interval_violation_count=(
            integrity
            .root_interval_violation_count
        ),

        max_root_interval_skew_ms=(
            integrity
            .max_root_interval_skew_ms
        ),
    )


def summarize_observations(
    observations: tuple[
        RelationObservation,
        ...
    ],
) -> RelationWindowSummary:

    classes = Counter(
        observation.classification
        for observation in observations
    )

    return RelationWindowSummary(
        trace_count=len(
            observations
        ),

        class_counts=tuple(
            sorted(
                classes.items()
            )
        ),

        client_observed_count=sum(
            observation.client_span_count
            > 0
            for observation
            in observations
        ),

        client_error_count=sum(
            "ERROR"
            in observation
            .client_status_codes
            for observation
            in observations
        ),

        server_observed_count=sum(
            observation.server_span_count
            > 0
            for observation
            in observations
        ),

        server_error_count=sum(
            "ERROR"
            in observation
            .server_status_codes
            for observation
            in observations
        ),

        client_error_no_server_count=sum(
            observation.classification
            == "client_error_no_server"
            for observation
            in observations
        ),

        client_non_error_no_server_count=sum(
            observation.classification
            == (
                "client_non_error_no_server"
            )
            for observation
            in observations
        ),
    )


def _classify(
    *,
    clients: tuple[
        SpanEvidence,
        ...
    ],
    servers: tuple[
        SpanEvidence,
        ...
    ],
) -> RelationClass:

    if not clients:
        return "no_client"

    if len(clients) > 1:
        return "multiple_clients"

    client = clients[0]

    if len(servers) > 1:
        return "multiple_server_children"

    if not servers:

        if client.is_error:
            return (
                "client_error_no_server"
            )

        return (
            "client_non_error_no_server"
        )

    server = servers[0]

    if (
        client.is_error
        and server.is_error
    ):
        return (
            "client_error_server_error"
        )

    if (
        client.is_error
        and not server.is_error
    ):
        return (
            "client_error_server_non_error"
        )

    if (
        not client.is_error
        and server.is_error
    ):
        return (
            "client_non_error_server_error"
        )

    return (
        "client_non_error_server_non_error"
    )
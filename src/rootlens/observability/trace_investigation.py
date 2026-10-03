from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from rootlens.observability.trace_evidence import (
    SpanEvidence,
    SpanKind,
    SpanStatusCode,
    TraceEvidence,
)


@dataclass(frozen=True)
class TraceSummary:

    trace_id: str

    span_count: int
    services: tuple[str, ...]

    root_count: int
    orphan_count: int
    error_span_count: int

    envelope_duration_ms: float

    single_root_service: str | None
    single_root_operation: str | None
    single_root_duration_ms: float | None

    temporal_violation_count: int
    max_temporal_skew_ms: float


@dataclass(frozen=True)
class SpanEdge:

    parent: SpanEvidence
    child: SpanEvidence


@dataclass(frozen=True)
class ClientServerPair:

    client: SpanEvidence
    server: SpanEvidence

    @property
    def crosses_service_boundary(
        self,
    ) -> bool:

        return (
            self.client.service_name
            != self.server.service_name
        )


@dataclass(frozen=True)
class SpanEdgeSignature:

    parent_service: str | None
    parent_operation: str
    parent_kind: SpanKind

    child_service: str | None
    child_operation: str
    child_kind: SpanKind


@dataclass(frozen=True)
class TracePathDifference:

    edge: SpanEdgeSignature

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
class TracePathComparison:

    baseline_trace_id: str
    incident_trace_id: str

    differences: tuple[
        TracePathDifference,
        ...
    ]

    @property
    def identical(
        self,
    ) -> bool:

        return not self.differences


class TraceInvestigationTool:

    def summarize(
        self,
        trace: TraceEvidence,
    ) -> TraceSummary:

        roots = trace.root_spans

        if len(roots) == 1:

            root = roots[0]

            root_service = (
                root.service_name
            )

            root_operation = (
                root.operation_name
            )

            root_duration_ms = (
                root.duration_ms
            )

        else:

            root_service = None
            root_operation = None
            root_duration_ms = None

        integrity = trace.integrity

        return TraceSummary(
            trace_id=trace.trace_id,

            span_count=len(
                trace.spans
            ),

            services=trace.services,

            root_count=(
                integrity.root_count
            ),

            orphan_count=(
                integrity.orphan_count
            ),

            error_span_count=len(
                trace.error_spans
            ),

            envelope_duration_ms=(
                trace.envelope_duration_ms
            ),

            single_root_service=(
                root_service
            ),

            single_root_operation=(
                root_operation
            ),

            single_root_duration_ms=(
                root_duration_ms
            ),

            temporal_violation_count=(
                integrity
                .temporal_violation_count
            ),

            max_temporal_skew_ms=(
                integrity
                .max_temporal_skew_ms
            ),
        )

    def find_spans(
        self,
        trace: TraceEvidence,
        *,
        service_name: str | None = None,
        operation_name: str | None = None,
        kind: SpanKind | None = None,
        status_code:
            SpanStatusCode | None = None,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        result = []

        for span in trace.spans:

            if (
                service_name is not None
                and span.service_name
                != service_name
            ):
                continue

            if (
                operation_name is not None
                and span.operation_name
                != operation_name
            ):
                continue

            if (
                kind is not None
                and span.kind != kind
            ):
                continue

            if (
                status_code is not None
                and span.status_code
                != status_code
            ):
                continue

            result.append(
                span
            )

        return tuple(
            sorted(
                result,
                key=lambda span: (
                    span.start_time_unix_nano,
                    span.span_id,
                ),
            )
        )

    def find_error_spans(
        self,
        trace: TraceEvidence,
        *,
        service_name: str | None = None,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        return self.find_spans(
            trace,
            service_name=service_name,
            status_code=(
                SpanStatusCode.ERROR
            ),
        )

    def find_slow_spans(
        self,
        trace: TraceEvidence,
        *,
        limit: int = 10,
        min_duration_ms:
            float | None = None,
        service_name:
            str | None = None,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        if (
            min_duration_ms is not None
            and min_duration_ms < 0
        ):
            raise ValueError(
                "min_duration_ms must "
                "be non-negative."
            )

        candidates = []

        for span in trace.spans:

            if (
                service_name is not None
                and span.service_name
                != service_name
            ):
                continue

            if (
                min_duration_ms is not None
                and span.duration_ms
                < min_duration_ms
            ):
                continue

            candidates.append(
                span
            )

        return tuple(
            sorted(
                candidates,
                key=lambda span: (
                    -span.duration_ms,
                    span.start_time_unix_nano,
                    span.span_id,
                ),
            )[:limit]
        )

    def find_parent_child_edges(
        self,
        trace: TraceEvidence,
    ) -> tuple[
        SpanEdge,
        ...
    ]:

        by_id = {
            span.span_id:
                span
            for span in trace.spans
        }

        edges = []

        for child in trace.spans:

            if child.parent_span_id is None:
                continue

            parent = by_id.get(
                child.parent_span_id
            )

            if parent is None:
                continue

            edges.append(
                SpanEdge(
                    parent=parent,
                    child=child,
                )
            )

        return tuple(
            sorted(
                edges,
                key=lambda edge: (
                    edge.parent.start_time_unix_nano,
                    edge.parent.span_id,
                    edge.child.start_time_unix_nano,
                    edge.child.span_id,
                ),
            )
        )

    def find_client_server_pairs(
        self,
        trace: TraceEvidence,
    ) -> tuple[
        ClientServerPair,
        ...
    ]:

        pairs = []

        for edge in (
            self.find_parent_child_edges(
                trace
            )
        ):

            if (
                edge.parent.kind
                == SpanKind.CLIENT
                and edge.child.kind
                == SpanKind.SERVER
            ):

                pairs.append(
                    ClientServerPair(
                        client=edge.parent,
                        server=edge.child,
                    )
                )

        return tuple(
            pairs
        )

    def find_unmatched_client_spans(
        self,
        trace: TraceEvidence,
    ) -> tuple[
        SpanEvidence,
        ...
    ]:

        matched_client_ids = {
            pair.client.span_id
            for pair in (
                self.find_client_server_pairs(
                    trace
                )
            )
        }

        clients = (
            self.find_spans(
                trace,
                kind=SpanKind.CLIENT,
            )
        )

        return tuple(
            span
            for span in clients
            if (
                span.span_id
                not in matched_client_ids
            )
        )

    def edge_signatures(
        self,
        trace: TraceEvidence,
    ) -> tuple[
        SpanEdgeSignature,
        ...
    ]:

        signatures = []

        for edge in (
            self.find_parent_child_edges(
                trace
            )
        ):

            signatures.append(
                SpanEdgeSignature(
                    parent_service=(
                        edge.parent
                        .service_name
                    ),

                    parent_operation=(
                        edge.parent
                        .operation_name
                    ),

                    parent_kind=(
                        edge.parent.kind
                    ),

                    child_service=(
                        edge.child
                        .service_name
                    ),

                    child_operation=(
                        edge.child
                        .operation_name
                    ),

                    child_kind=(
                        edge.child.kind
                    ),
                )
            )

        return tuple(
            signatures
        )

    def compare_trace_paths(
        self,
        baseline: TraceEvidence,
        incident: TraceEvidence,
    ) -> TracePathComparison:

        baseline_counts = Counter(
            self.edge_signatures(
                baseline
            )
        )

        incident_counts = Counter(
            self.edge_signatures(
                incident
            )
        )

        all_edges = (
            set(
                baseline_counts
            )
            | set(
                incident_counts
            )
        )

        differences = []

        for edge in all_edges:

            baseline_count = (
                baseline_counts[
                    edge
                ]
            )

            incident_count = (
                incident_counts[
                    edge
                ]
            )

            if (
                baseline_count
                == incident_count
            ):
                continue

            differences.append(
                TracePathDifference(
                    edge=edge,
                    baseline_count=(
                        baseline_count
                    ),
                    incident_count=(
                        incident_count
                    ),
                )
            )

        return TracePathComparison(
            baseline_trace_id=(
                baseline.trace_id
            ),

            incident_trace_id=(
                incident.trace_id
            ),

            differences=tuple(
                sorted(
                    differences,
                    key=lambda difference:
                        self._edge_sort_key(
                            difference.edge
                        ),
                )
            ),
        )

    @staticmethod
    def _edge_sort_key(
        edge: SpanEdgeSignature,
    ) -> tuple:

        return (
            edge.parent_service
            or "",

            edge.parent_operation,

            int(
                edge.parent_kind
            ),

            edge.child_service
            or "",

            edge.child_operation,

            int(
                edge.child_kind
            ),
        )
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)
from rootlens.observability.unified_evidence import (
    IncidentEvidenceBundle,
)


@dataclass(frozen=True)
class MetricChange:
    metric_key: str
    baseline: float
    incident: float
    absolute_delta: float


@dataclass(frozen=True)
class TracePaymentObservation:
    trace_id: str

    checkout_payment_client_observed: bool
    checkout_payment_client_error: bool

    payment_server_observed: bool
    payment_server_error: bool


@dataclass(frozen=True)
class ExactLogBodyPrevalence:
    service_name: str
    body: str

    trace_count: int
    total_trace_count: int

    log_count: int

    @property
    def prevalence(
        self,
    ) -> float:
        if (
            self.total_trace_count
            == 0
        ):
            return 0.0

        return (
            self.trace_count
            / self.total_trace_count
        )


@dataclass(frozen=True)
class RequestEvidenceRow:
    trace_id: str

    checkout_payment_client_error: bool
    payment_server_error: bool

    payment_log_bodies: tuple[
        str,
        ...
    ]


def metric_changes(
    *,
    bundle: IncidentEvidenceBundle,
    metric_keys: tuple[
        str,
        ...
    ],
    metric_bindings,
) -> tuple[
    MetricChange,
    ...
]:
    index_by_key = {
        binding.metric_key:
            binding.metric_index
        for binding
        in metric_bindings
    }

    changes = []

    for metric_key in metric_keys:
        if (
            metric_key
            not in index_by_key
        ):
            raise ValueError(
                "No metric binding for "
                f"{metric_key}."
            )

        metric_index = (
            index_by_key[
                metric_key
            ]
        )

        evidence = (
            bundle.metrics[
                metric_index
            ]
        )

        if not isinstance(
            evidence,
            MetricComparisonEvidence,
        ):
            raise TypeError(
                "Expected "
                "MetricComparisonEvidence "
                f"for {metric_key}."
            )

        baseline = float(
            evidence.baseline.value
        )

        incident = float(
            evidence.incident.value
        )

        changes.append(
            MetricChange(
                metric_key=(
                    metric_key
                ),

                baseline=baseline,

                incident=incident,

                absolute_delta=(
                    incident
                    - baseline
                ),
            )
        )

    return tuple(
        changes
    )


def trace_payment_observations(
    bundle: IncidentEvidenceBundle,
    *,
    checkout_service: str = "checkout",
    payment_service: str = "payment",
    payment_operation: str = (
        "oteldemo.PaymentService/Charge"
    ),
) -> tuple[
    TracePaymentObservation,
    ...
]:
    tool = (
        TraceInvestigationTool()
    )

    observations = []

    for trace in bundle.traces:
        error_keys = {
            (
                span.trace_id,
                span.span_id,
            )
            for span
            in tool.find_error_spans(
                trace
            )
        }

        pairs = (
            tool.find_client_server_pairs(
                trace
            )
        )

        payment_pairs = [
            pair
            for pair in pairs
            if (
                pair.client.service_name
                == checkout_service
                and
                pair.client.operation_name
                == payment_operation
                and
                pair.server.service_name
                == payment_service
            )
        ]

        payment_client_spans = [
            span
            for span
            in trace.spans
            if (
                span.service_name
                == checkout_service
                and
                span.operation_name
                == payment_operation
            )
        ]

        payment_server_spans = [
            pair.server
            for pair
            in payment_pairs
        ]

        client_error = any(
            (
                span.trace_id,
                span.span_id,
            )
            in error_keys
            for span
            in payment_client_spans
        )

        server_error = any(
            (
                span.trace_id,
                span.span_id,
            )
            in error_keys
            for span
            in payment_server_spans
        )

        observations.append(
            TracePaymentObservation(
                trace_id=(
                    trace.trace_id
                ),

                checkout_payment_client_observed=bool(
                    payment_client_spans
                ),

                checkout_payment_client_error=(
                    client_error
                ),

                payment_server_observed=bool(
                    payment_server_spans
                ),

                payment_server_error=(
                    server_error
                ),
            )
        )

    return tuple(
        observations
    )


def exact_log_body_prevalence(
    logs: tuple[
        LogEvidence,
        ...
    ],
    *,
    service_name: str,
    trace_ids: tuple[
        str,
        ...
    ],
) -> tuple[
    ExactLogBodyPrevalence,
    ...
]:
    allowed_trace_ids = set(
        trace_ids
    )

    traces_by_body = (
        defaultdict(
            set
        )
    )

    count_by_body = Counter()

    for log in logs:
        if (
            log.service_name
            != service_name
        ):
            continue

        if (
            log.trace_id
            not in allowed_trace_ids
        ):
            continue

        body = log.body_text

        count_by_body[
            body
        ] += 1

        traces_by_body[
            body
        ].add(
            log.trace_id
        )

    rows = [
        ExactLogBodyPrevalence(
            service_name=(
                service_name
            ),

            body=body,

            trace_count=len(
                traces_by_body[
                    body
                ]
            ),

            total_trace_count=len(
                allowed_trace_ids
            ),

            log_count=count,
        )
        for body, count
        in count_by_body.items()
    ]

    rows.sort(
        key=lambda row: (
            -row.trace_count,
            -row.log_count,
            row.body,
        )
    )

    return tuple(
        rows
    )


def request_evidence_rows(
    bundle: IncidentEvidenceBundle,
    *,
    payment_service: str = "payment",
) -> tuple[
    RequestEvidenceRow,
    ...
]:
    trace_observations = {
        observation.trace_id:
            observation
        for observation
        in trace_payment_observations(
            bundle
        )
    }

    payment_bodies = (
        defaultdict(
            list
        )
    )

    for log in bundle.logs:
        if (
            log.service_name
            != payment_service
        ):
            continue

        if log.trace_id is None:
            continue

        payment_bodies[
            log.trace_id
        ].append(
            log.body_text
        )

    rows = []

    for trace_id in sorted(
        trace_observations
    ):
        observation = (
            trace_observations[
                trace_id
            ]
        )

        rows.append(
            RequestEvidenceRow(
                trace_id=trace_id,

                checkout_payment_client_error=(
                    observation
                    .checkout_payment_client_error
                ),

                payment_server_error=(
                    observation
                    .payment_server_error
                ),

                payment_log_bodies=tuple(
                    payment_bodies.get(
                        trace_id,
                        ()
                    )
                ),
            )
        )

    return tuple(
        rows
    )
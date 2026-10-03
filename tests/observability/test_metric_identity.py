from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

import pytest

from rootlens.observability.cross_modal import (
    CrossModalIndex,
)
from rootlens.observability.metric_identity import (
    MetricFamily,
    MetricServiceBinding,
    MetricServiceRole,
)
from rootlens.observability.unified_evidence import (
    IncidentEvidenceBundle,
)


def make_bundle(
    metrics,
):
    return IncidentEvidenceBundle(
        incident_id="incident",

        start=datetime(
            2026,
            10,
            3,
            13,
            0,
            tzinfo=timezone.utc,
        ),

        end=datetime(
            2026,
            10,
            3,
            13,
            5,
            tzinfo=timezone.utc,
        ),

        metrics=tuple(
            metrics
        ),
    )


def test_rpc_client_requires_peer():
    with pytest.raises(
        ValueError
    ):
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "checkout_payment_error_rate"
            ),

            family=(
                MetricFamily.RPC_CLIENT
            ),

            service_name="checkout",
        )


def test_rpc_client_services_must_differ():
    with pytest.raises(
        ValueError
    ):
        MetricServiceBinding(
            metric_index=0,

            metric_key="metric",

            family=(
                MetricFamily.RPC_CLIENT
            ),

            service_name="checkout",

            peer_service_name=(
                "checkout"
            ),
        )


def test_server_metric_rejects_peer():
    with pytest.raises(
        ValueError
    ):
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "payment_error_rate"
            ),

            family=(
                MetricFamily.RPC_SERVER
            ),

            service_name="payment",

            peer_service_name=(
                "checkout"
            ),
        )


def test_rpc_client_metric_links_both_services():
    metric = object()

    bundle = make_bundle(
        (
            metric,
        )
    )

    binding = (
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "checkout_payment_error_rate"
            ),

            family=(
                MetricFamily.RPC_CLIENT
            ),

            service_name="checkout",

            peer_service_name=(
                "payment"
            ),
        )
    )

    index = CrossModalIndex(
        bundle,

        metric_bindings=(
            binding,
        ),
    )

    checkout = (
        index.service_correlation(
            "checkout"
        )
    )

    payment = (
        index.service_correlation(
            "payment"
        )
    )

    assert checkout is not None
    assert payment is not None

    assert (
        checkout.metric_count
        == 1
    )

    assert (
        payment.metric_count
        == 1
    )

    assert (
        checkout.metrics[0].evidence
        is metric
    )

    assert (
        checkout.metrics[0].role
        == MetricServiceRole.PRIMARY
    )

    assert (
        payment.metrics[0].role
        == MetricServiceRole.PEER
    )


def test_rpc_server_metric_is_primary_only():
    metric = object()

    binding = (
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "payment_error_rate"
            ),

            family=(
                MetricFamily.RPC_SERVER
            ),

            service_name="payment",
        )
    )

    index = CrossModalIndex(
        make_bundle(
            (
                metric,
            )
        ),

        metric_bindings=(
            binding,
        ),
    )

    payment = (
        index.service_correlation(
            "payment"
        )
    )

    checkout = (
        index.service_correlation(
            "checkout"
        )
    )

    assert payment is not None

    assert (
        payment.metrics[0].role
        == MetricServiceRole.PRIMARY
    )

    assert checkout is None


def test_unbound_metrics_are_preserved():
    first = object()
    second = object()

    binding = (
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "checkout_error_rate"
            ),

            family=(
                MetricFamily.RPC_SERVER
            ),

            service_name="checkout",
        )
    )

    index = CrossModalIndex(
        make_bundle(
            (
                first,
                second,
            )
        ),

        metric_bindings=(
            binding,
        ),
    )

    assert (
        index.unbound_metrics()
        == (second,)
    )

    coverage = (
        index.coverage()
    )

    assert (
        coverage.metric_count
        == 2
    )

    assert (
        coverage.bound_metric_count
        == 1
    )

    assert (
        coverage.unbound_metric_count
        == 1
    )


def test_binding_index_must_exist():
    metric = object()

    binding = (
        MetricServiceBinding(
            metric_index=1,

            metric_key="metric",

            family=(
                MetricFamily.HTTP_SERVER
            ),

            service_name="frontend",
        )
    )

    with pytest.raises(
        ValueError
    ):
        CrossModalIndex(
            make_bundle(
                (
                    metric,
                )
            ),

            metric_bindings=(
                binding,
            ),
        )


def test_metric_index_can_only_be_bound_once():
    metric = object()

    first = (
        MetricServiceBinding(
            metric_index=0,

            metric_key="metric-a",

            family=(
                MetricFamily.RPC_SERVER
            ),

            service_name="checkout",
        )
    )

    second = (
        MetricServiceBinding(
            metric_index=0,

            metric_key="metric-b",

            family=(
                MetricFamily.HTTP_SERVER
            ),

            service_name="frontend",
        )
    )

    with pytest.raises(
        ValueError
    ):
        CrossModalIndex(
            make_bundle(
                (
                    metric,
                )
            ),

            metric_bindings=(
                first,
                second,
            ),
        )
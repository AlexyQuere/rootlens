from dataclasses import dataclass
from datetime import datetime, timezone

from rootlens.evaluation.runtime_feature_flag import (
    extract_feature_flag_observations,
    runtime_state_matches,
)


@dataclass(frozen=True)
class FakeEvent:
    timestamp: datetime
    attributes: dict


@dataclass(frozen=True)
class FakeSpan:
    span_id: str
    service_name: str
    operation_name: str
    events: tuple[
        FakeEvent,
        ...
    ]


@dataclass(frozen=True)
class FakeTrace:
    trace_id: str
    spans: tuple[
        FakeSpan,
        ...
    ]


def make_trace(
    *,
    value,
    variant,
    reason,
):
    event = FakeEvent(
        timestamp=datetime(
            2026,
            10,
            3,
            tzinfo=timezone.utc,
        ),
        attributes={
            "feature_flag.key":
                "paymentUnreachable",
            "feature_flag.provider.name":
                "flagd",
            "feature_flag.result.value":
                value,
            "feature_flag.result.variant":
                variant,
            "feature_flag.result.reason":
                reason,
        },
    )

    span = FakeSpan(
        span_id="abc",
        service_name="checkout",
        operation_name=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        events=(
            event,
        ),
    )

    return FakeTrace(
        trace_id="trace-1",
        spans=(
            span,
        ),
    )


def test_extract_runtime_flag_on():
    observations = (
        extract_feature_flag_observations(
            (
                make_trace(
                    value=True,
                    variant="on",
                    reason="static",
                ),
            ),
            flag_key=(
                "paymentUnreachable"
            ),
        )
    )

    assert len(
        observations
    ) == 1

    observation = (
        observations[0]
    )

    assert (
        observation.value
        is True
    )

    assert (
        observation.variant
        == "on"
    )

    assert runtime_state_matches(
        observation,
        expected_value=True,
        expected_variant="on",
    )


def test_runtime_flag_cached_off_fails():
    observations = (
        extract_feature_flag_observations(
            (
                make_trace(
                    value=False,
                    variant="off",
                    reason="cached",
                ),
            ),
            flag_key=(
                "paymentUnreachable"
            ),
        )
    )

    assert len(
        observations
    ) == 1

    assert not runtime_state_matches(
        observations[0],
        expected_value=True,
        expected_variant="on",
    )
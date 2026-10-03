from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class FeatureFlagRuntimeObservation:
    trace_id: str
    span_id: str
    service_name: str
    operation_name: str

    flag_key: str
    value: Any
    variant: str | None
    reason: str | None
    provider: str | None

    event_time: str | None


def extract_feature_flag_observations(
    traces,
    *,
    flag_key: str,
    service_name: str = "checkout",
    operation_name: str = (
        "oteldemo.CheckoutService/PlaceOrder"
    ),
) -> tuple[
    FeatureFlagRuntimeObservation,
    ...
]:
    observations = []

    for trace in traces:
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

            events = getattr(
                span,
                "events",
                (),
            )

            for event in events:
                attributes = (
                    _event_attributes(
                        event
                    )
                )

                if (
                    attributes.get(
                        "feature_flag.key"
                    )
                    != flag_key
                ):
                    continue

                observations.append(
                    FeatureFlagRuntimeObservation(
                        trace_id=(
                            trace.trace_id
                        ),
                        span_id=(
                            span.span_id
                        ),
                        service_name=(
                            span.service_name
                        ),
                        operation_name=(
                            span.operation_name
                        ),
                        flag_key=(
                            flag_key
                        ),
                        value=(
                            attributes.get(
                                "feature_flag."
                                "result.value"
                            )
                        ),
                        variant=(
                            _optional_string(
                                attributes.get(
                                    "feature_flag."
                                    "result.variant"
                                )
                            )
                        ),
                        reason=(
                            _optional_string(
                                attributes.get(
                                    "feature_flag."
                                    "result.reason"
                                )
                            )
                        ),
                        provider=(
                            _optional_string(
                                attributes.get(
                                    "feature_flag."
                                    "provider.name"
                                )
                            )
                        ),
                        event_time=(
                            _event_time(
                                event
                            )
                        ),
                    )
                )

    observations.sort(
        key=lambda observation: (
            observation.trace_id,
            observation.span_id,
            observation.event_time
            or "",
        )
    )

    return tuple(
        observations
    )


def runtime_state_matches(
    observation:
        FeatureFlagRuntimeObservation,
    *,
    expected_value: bool,
    expected_variant: str,
) -> bool:
    return (
        observation.value
        is expected_value
        and
        (
            observation.variant
            or ""
        ).casefold()
        == expected_variant.casefold()
    )


def _event_attributes(
    event,
) -> Mapping[str, Any]:
    if isinstance(
        event,
        Mapping,
    ):
        attributes = event.get(
            "attributes",
            {},
        )
    else:
        attributes = getattr(
            event,
            "attributes",
            {},
        )

    if isinstance(
        attributes,
        Mapping,
    ):
        return attributes

    return {}


def _event_time(
    event,
) -> str | None:
    candidates = (
        "timestamp",
        "time",
        "event_time",
    )

    for name in candidates:
        if isinstance(
            event,
            Mapping,
        ):
            value = event.get(
                name
            )
        else:
            value = getattr(
                event,
                name,
                None,
            )

        if value is None:
            continue

        isoformat = getattr(
            value,
            "isoformat",
            None,
        )

        if callable(
            isoformat
        ):
            return isoformat()

        return str(
            value
        )

    return None


def _optional_string(
    value,
) -> str | None:
    if value is None:
        return None

    return str(
        value
    )
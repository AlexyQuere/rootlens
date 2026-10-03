from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from rootlens.evaluation.cross_modal_capture import (
    PinnedPrometheusClient,
)

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from rootlens.evaluation.cross_modal_capture import (
    PinnedPrometheusClient,
    _jsonable,
)


class FakePrometheusClient:
    def __init__(
        self,
    ):
        self.calls = []

    def query(
        self,
        promql,
        *,
        time=None,
    ):
        self.calls.append(
            (
                promql,
                time,
            )
        )

        return ()


def test_pinned_client_uses_fixed_time():
    client = (
        FakePrometheusClient()
    )

    pinned_time = datetime(
        2026,
        10,
        3,
        15,
        0,
        tzinfo=timezone.utc,
    )

    pinned = (
        PinnedPrometheusClient(
            client,
            evaluation_time=(
                pinned_time
            ),
        )
    )

    pinned.query(
        "up"
    )

    assert client.calls == [
        (
            "up",
            pinned_time,
        )
    ]


def test_explicit_time_overrides_pin():
    client = (
        FakePrometheusClient()
    )

    pinned_time = datetime(
        2026,
        10,
        3,
        15,
        0,
        tzinfo=timezone.utc,
    )

    explicit_time = datetime(
        2026,
        10,
        3,
        14,
        0,
        tzinfo=timezone.utc,
    )

    pinned = (
        PinnedPrometheusClient(
            client,
            evaluation_time=(
                pinned_time
            ),
        )
    )

    pinned.query(
        "up",
        time=explicit_time,
    )

    assert client.calls == [
        (
            "up",
            explicit_time,
        )
    ]

@dataclass(frozen=True)
class FrozenPayload:
    data: Mapping[
        str,
        object,
    ]


def test_jsonable_handles_mappingproxy_inside_dataclass():
    value = FrozenPayload(
        data=MappingProxyType(
            {
                "outer": (
                    MappingProxyType(
                        {
                            "inner": 42,
                        }
                    )
                )
            }
        )
    )

    result = _jsonable(
        value
    )

    assert result == {
        "data": {
            "outer": {
                "inner": 42,
            }
        }
    }
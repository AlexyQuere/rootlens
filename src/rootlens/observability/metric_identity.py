from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MetricFamily(
    str,
    Enum,
):
    HTTP_SERVER = "http_server"
    RPC_SERVER = "rpc_server"
    RPC_CLIENT = "rpc_client"


class MetricServiceRole(
    str,
    Enum,
):
    PRIMARY = "primary"
    PEER = "peer"


@dataclass(frozen=True)
class MetricServiceBinding:
    metric_index: int

    metric_key: str

    family: MetricFamily

    service_name: str

    peer_service_name: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.metric_index < 0:
            raise ValueError(
                "metric_index cannot "
                "be negative."
            )

        if not self.metric_key:
            raise ValueError(
                "metric_key cannot "
                "be empty."
            )

        if not self.service_name:
            raise ValueError(
                "service_name cannot "
                "be empty."
            )

        if (
            self.family
            == MetricFamily.RPC_CLIENT
        ):
            if not self.peer_service_name:
                raise ValueError(
                    "rpc_client metrics "
                    "require "
                    "peer_service_name."
                )

            if (
                self.peer_service_name
                == self.service_name
            ):
                raise ValueError(
                    "rpc_client primary "
                    "and peer services "
                    "must differ."
                )

        else:
            if (
                self.peer_service_name
                is not None
            ):
                raise ValueError(
                    "peer_service_name is "
                    "only valid for "
                    "rpc_client metrics."
                )

    @property
    def service_names(
        self,
    ) -> tuple[str, ...]:
        if (
            self.peer_service_name
            is None
        ):
            return (
                self.service_name,
            )

        return (
            self.service_name,
            self.peer_service_name,
        )

    def role_for(
        self,
        service_name: str,
    ) -> MetricServiceRole | None:
        if (
            service_name
            == self.service_name
        ):
            return (
                MetricServiceRole.PRIMARY
            )

        if (
            service_name
            == self.peer_service_name
        ):
            return (
                MetricServiceRole.PEER
            )

        return None
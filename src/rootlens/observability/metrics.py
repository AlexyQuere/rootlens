from __future__ import annotations

import math

from dataclasses import dataclass
from typing import (
    Literal,
    Protocol,
)

from rootlens.observability.evidence import (
    MetricEvidence,
    TimeWindow,
)

from rootlens.observability.prometheus import (
    InstantSample,
)


MetricFamilyName = Literal[
    "http_server",
    "rpc_server",
    "rpc_client",
]


class MetricsToolError(
    RuntimeError
):
    """
    Base error raised by the metrics tool.
    """


class MetricUnavailableError(
    MetricsToolError
):
    """
    No usable metric observation was returned.
    """


class MetricCardinalityError(
    MetricsToolError
):
    """
    A supposedly scalar PromQL query returned
    multiple samples.
    """


class UnsupportedMetricOperationError(
    MetricsToolError
):
    """
    The requested semantic operation has not been
    validated for the selected metric family.
    """


class PrometheusQueryClient(
    Protocol
):
    def query(
        self,
        promql: str,
        *,
        time=None,
    ) -> tuple[
        InstantSample,
        ...,
    ]:
        ...


@dataclass(
    frozen=True
)
class MetricFamilySpec:
    name: MetricFamilyName

    count_metric: str

    operation_label: str

    status_label: str

    bucket_metric: str | None

    protocol_label: str | None = None
    protocol_value: str | None = None


HTTP_SERVER = MetricFamilySpec(
    name="http_server",

    count_metric=(
        "http_server_request_"
        "duration_seconds_count"
    ),

    bucket_metric=(
        "http_server_request_"
        "duration_seconds_bucket"
    ),

    operation_label=(
        "http_route"
    ),

    status_label=(
        "http_response_status_code"
    ),
)


RPC_SERVER = MetricFamilySpec(
    name="rpc_server",

    count_metric=(
        "rpc_server_call_"
        "duration_seconds_count"
    ),

    bucket_metric=(
        "rpc_server_call_"
        "duration_seconds_bucket"
    ),

    operation_label=(
        "rpc_method"
    ),

    status_label=(
        "rpc_response_status_code"
    ),

    protocol_label=(
        "rpc_system_name"
    ),

    protocol_value="grpc",
)


RPC_CLIENT = MetricFamilySpec(
    name="rpc_client",

    count_metric=(
        "rpc_client_call_"
        "duration_seconds_count"
    ),

    # The metric exists in Prometheus, but its
    # bucket schema has not yet been explicitly
    # validated in this experiment.
    bucket_metric=None,

    operation_label=(
        "rpc_method"
    ),

    status_label=(
        "rpc_response_status_code"
    ),

    protocol_label=(
        "rpc_system_name"
    ),

    protocol_value="grpc",
)


FAMILIES: dict[
    MetricFamilyName,
    MetricFamilySpec,
] = {
    "http_server":
        HTTP_SERVER,

    "rpc_server":
        RPC_SERVER,

    "rpc_client":
        RPC_CLIENT,
}


class MetricsTool:
    """
    Deterministic semantic metrics interface.

    The tool converts high-level observability
    requests into fixed PromQL templates.

    It does not perform incident reasoning.
    """

    def __init__(
        self,
        client: PrometheusQueryClient,
    ) -> None:

        self.client = client

    def request_rate(
        self,
        *,
        family: MetricFamilyName,
        service: str,
        window: TimeWindow,
        operation: str | None = None,
    ) -> MetricEvidence:

        spec = self._get_family(
            family
        )

        selector = self._selector(
            spec=spec,
            service=service,
            operation=operation,
        )

        duration = self._promql_duration(
            window
        )

        promql = (
            "sum("
            "rate("
            f"{spec.count_metric}"
            f"{selector}"
            f"[{duration}]"
            ")"
            ")"
        )

        value = self._query_scalar(
            promql=promql,
            window=window,
        )

        labels = self._evidence_labels(
            family=family,
            operation=operation,
        )

        return MetricEvidence(
            name=spec.count_metric,
            statistic="request_rate",
            value=value,
            unit="requests_per_second",
            service=service,
            window=window,
            promql=promql,
            labels=labels,
        )

    def request_count(
        self,
        *,
        family: MetricFamilyName,
        service: str,
        window: TimeWindow,
        operation: str | None = None,
    ) -> MetricEvidence:

        spec = self._get_family(
            family
        )

        selector = self._selector(
            spec=spec,
            service=service,
            operation=operation,
        )

        duration = self._promql_duration(
            window
        )

        promql = (
            "sum("
            "increase("
            f"{spec.count_metric}"
            f"{selector}"
            f"[{duration}]"
            ")"
            ")"
        )

        value = self._query_scalar(
            promql=promql,
            window=window,
        )

        labels = self._evidence_labels(
            family=family,
            operation=operation,
        )

        return MetricEvidence(
            name=spec.count_metric,
            statistic="request_count",
            value=value,
            unit="requests",
            service=service,
            window=window,
            promql=promql,
            labels=labels,
        )

    def error_rate(
        self,
        *,
        family: MetricFamilyName,
        service: str,
        window: TimeWindow,
        operation: str | None = None,
    ) -> MetricEvidence:

        spec = self._get_family(
            family
        )

        base_matchers = (
            self._matchers(
                spec=spec,
                service=service,
                operation=operation,
            )
        )

        error_matcher = (
            self._error_matcher(
                spec
            )
        )

        all_selector = (
            self._render_selector(
                base_matchers
            )
        )

        error_selector = (
            self._render_selector(
                [
                    *base_matchers,
                    error_matcher,
                ]
            )
        )

        duration = (
            self._promql_duration(
                window
            )
        )

        numerator = (
            "("
            "sum("
            "rate("
            f"{spec.count_metric}"
            f"{error_selector}"
            f"[{duration}]"
            ")"
            ") "
            "or vector(0)"
            ")"
        )

        denominator = (
            "sum("
            "rate("
            f"{spec.count_metric}"
            f"{all_selector}"
            f"[{duration}]"
            ")"
            ")"
        )

        promql = (
            f"{numerator}"
            " / "
            f"{denominator}"
        )

        value = self._query_scalar(
            promql=promql,
            window=window,
        )

        if (
            value < 0
            or value > 1
        ):
            raise MetricUnavailableError(
                "Prometheus returned an "
                "invalid error-rate ratio: "
                f"{value}."
            )

        labels = self._evidence_labels(
            family=family,
            operation=operation,
        )

        return MetricEvidence(
            name=spec.count_metric,
            statistic="error_rate",
            value=value,
            unit="ratio",
            service=service,
            window=window,
            promql=promql,
            labels=labels,
        )

    def latency_quantile(
        self,
        *,
        family: MetricFamilyName,
        service: str,
        window: TimeWindow,
        quantile: float,
        operation: str | None = None,
    ) -> MetricEvidence:

        if not (
            0 < quantile < 1
        ):
            raise ValueError(
                "quantile must be "
                "strictly between 0 and 1."
            )

        spec = self._get_family(
            family
        )

        if spec.bucket_metric is None:
            raise UnsupportedMetricOperationError(
                "Latency quantiles have not "
                f"yet been validated for "
                f"{family!r}."
            )

        selector = self._selector(
            spec=spec,
            service=service,
            operation=operation,
        )

        duration = (
            self._promql_duration(
                window
            )
        )

        promql = (
            "histogram_quantile("
            f"{quantile}, "
            "sum by (le) ("
            "rate("
            f"{spec.bucket_metric}"
            f"{selector}"
            f"[{duration}]"
            ")"
            ")"
            ")"
        )

        value = self._query_scalar(
            promql=promql,
            window=window,
        )

        percentile = round(
            quantile
            * 100
        )

        labels = self._evidence_labels(
            family=family,
            operation=operation,
        )

        return MetricEvidence(
            name=spec.bucket_metric,
            statistic=(
                f"p{percentile}"
            ),
            value=value,
            unit="seconds",
            service=service,
            window=window,
            promql=promql,
            labels=labels,
        )

    def latency_quantiles(
        self,
        *,
        family: MetricFamilyName,
        service: str,
        window: TimeWindow,
        operation: str | None = None,
        quantiles: tuple[
            float,
            ...,
        ] = (
            0.50,
            0.95,
            0.99,
        ),
    ) -> tuple[
        MetricEvidence,
        ...,
    ]:

        return tuple(
            self.latency_quantile(
                family=family,
                service=service,
                window=window,
                quantile=quantile,
                operation=operation,
            )
            for quantile
            in quantiles
        )

    def _query_scalar(
        self,
        *,
        promql: str,
        window: TimeWindow,
    ) -> float:

        result = self.client.query(
            promql,
            time=window.end,
        )

        if not result:
            raise MetricUnavailableError(
                "Prometheus returned no "
                "series for the metric query."
            )

        if len(
            result
        ) != 1:
            raise MetricCardinalityError(
                "Expected one scalar metric "
                "sample, got "
                f"{len(result)}."
            )

        value = result[0].value

        if not math.isfinite(
            value
        ):
            raise MetricUnavailableError(
                "Prometheus returned a "
                "non-finite metric value."
            )

        return value

    @staticmethod
    def _get_family(
        family: MetricFamilyName,
    ) -> MetricFamilySpec:

        try:
            return FAMILIES[
                family
            ]

        except KeyError as exc:
            raise ValueError(
                "Unknown metric family: "
                f"{family!r}."
            ) from exc

    @classmethod
    def _selector(
        cls,
        *,
        spec: MetricFamilySpec,
        service: str,
        operation: str | None,
    ) -> str:

        matchers = cls._matchers(
            spec=spec,
            service=service,
            operation=operation,
        )

        return cls._render_selector(
            matchers
        )

    @classmethod
    def _matchers(
        cls,
        *,
        spec: MetricFamilySpec,
        service: str,
        operation: str | None,
    ) -> list[str]:

        if not service.strip():
            raise ValueError(
                "service must not be empty."
            )

        matchers = [
            (
                "service_name="
                f"\"{cls._escape_label(service)}\""
            )
        ]

        if (
            spec.protocol_label
            is not None
            and spec.protocol_value
            is not None
        ):
            matchers.append(
                (
                    f"{spec.protocol_label}="
                    "\""
                    f"{cls._escape_label(spec.protocol_value)}"
                    "\""
                )
            )

        if operation is not None:

            if not operation.strip():
                raise ValueError(
                    "operation must either "
                    "be None or non-empty."
                )

            matchers.append(
                (
                    f"{spec.operation_label}="
                    "\""
                    f"{cls._escape_label(operation)}"
                    "\""
                )
            )

        return matchers

    @staticmethod
    def _render_selector(
        matchers: list[str],
    ) -> str:

        return (
            "{"
            + ",".join(
                matchers
            )
            + "}"
        )

    @staticmethod
    def _error_matcher(
        spec: MetricFamilySpec,
    ) -> str:

        if spec.name == "http_server":
            return (
                f"{spec.status_label}"
                '=~"5.."'
            )

        return (
            f"{spec.status_label}"
            '!="OK"'
        )

    @staticmethod
    def _promql_duration(
        window: TimeWindow,
    ) -> str:

        duration = (
            window.duration_seconds
        )

        if duration <= 0:
            raise ValueError(
                "window duration "
                "must be positive."
            )

        milliseconds = round(
            duration
            * 1000
        )

        if (
            milliseconds
            % 1000
            == 0
        ):
            return (
                f"{milliseconds // 1000}s"
            )

        return (
            f"{milliseconds}ms"
        )

    @staticmethod
    def _escape_label(
        value: str,
    ) -> str:

        return (
            value
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                "\n",
                "\\n",
            )
            .replace(
                '"',
                '\\"',
            )
        )

    @staticmethod
    def _evidence_labels(
        *,
        family: MetricFamilyName,
        operation: str | None,
    ) -> dict[
        str,
        str,
    ]:

        labels = {
            "metric_family":
                family,
        }

        if operation is not None:
            labels[
                "operation"
            ] = operation

        return labels
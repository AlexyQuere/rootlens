from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PrometheusTime = (
    str
    | int
    | float
    | datetime
)


class PrometheusError(
    RuntimeError
):
    """
    Base error raised by the Prometheus client.
    """


class PrometheusTransportError(
    PrometheusError
):
    """
    HTTP/network communication failure.
    """


class PrometheusAPIError(
    PrometheusError
):
    """
    Prometheus returned a valid error response.
    """


class PrometheusResponseError(
    PrometheusError
):
    """
    Prometheus returned an unexpected or malformed
    success response.
    """


@dataclass(
    frozen=True
)
class InstantSample:
    """
    One sample returned by an instant Prometheus query.
    """

    metric: Mapping[str, str]
    timestamp: float
    value: float


@dataclass(
    frozen=True
)
class RangeSample:
    """
    One timestamp/value pair from a range query.
    """

    timestamp: float
    value: float


@dataclass(
    frozen=True
)
class RangeSeries:
    """
    One labelled time series returned by Prometheus.
    """

    metric: Mapping[str, str]
    samples: tuple[
        RangeSample,
        ...,
    ]


class PrometheusClient:
    """
    Minimal deterministic Prometheus HTTP API client.

    This class is responsible only for:

    - HTTP communication,
    - Prometheus API validation,
    - conversion from JSON to typed Python objects.

    It deliberately contains no incident-analysis logic.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: Mapping[
            str,
            str,
        ] | None = None,
    ) -> None:

        if not base_url.strip():

            raise ValueError(
                "base_url must not be empty."
            )

        if timeout_seconds <= 0:

            raise ValueError(
                "timeout_seconds must be positive."
            )

        self.base_url = (
            base_url.rstrip(
                "/"
            )
        )

        self.timeout_seconds = (
            timeout_seconds
        )

        self.headers = dict(
            headers
            or {}
        )

    def query(
        self,
        promql: str,
        *,
        time: PrometheusTime | None = None,
    ) -> tuple[
        InstantSample,
        ...,
    ]:
        """
        Execute an instant PromQL query.

        Returns one InstantSample per labelled series.
        """

        self._validate_promql(
            promql
        )

        params: dict[
            str,
            str,
        ] = {
            "query":
                promql,
        }

        if time is not None:

            params[
                "time"
            ] = (
                self._format_time(
                    time
                )
            )

        payload = self._request(
            endpoint=(
                "/api/v1/query"
            ),
            params=params,
        )

        data = self._extract_data(
            payload
        )

        result_type = (
            data.get(
                "resultType"
            )
        )

        if result_type != "vector":

            raise PrometheusResponseError(
                "Expected instant query "
                "resultType='vector', "
                f"got {result_type!r}."
            )

        result = data.get(
            "result"
        )

        if not isinstance(
            result,
            list,
        ):

            raise PrometheusResponseError(
                "Prometheus vector result "
                "must be a list."
            )

        return tuple(
            self._parse_instant_sample(
                item
            )
            for item
            in result
        )

    def query_range(
        self,
        promql: str,
        *,
        start: PrometheusTime,
        end: PrometheusTime,
        step: str | int | float,
    ) -> tuple[
        RangeSeries,
        ...,
    ]:
        """
        Execute a range PromQL query.

        Returns one RangeSeries per labelled series.
        """

        self._validate_promql(
            promql
        )

        step_value = (
            self._format_step(
                step
            )
        )

        params = {
            "query":
                promql,

            "start":
                self._format_time(
                    start
                ),

            "end":
                self._format_time(
                    end
                ),

            "step":
                step_value,
        }

        payload = self._request(
            endpoint=(
                "/api/v1/query_range"
            ),
            params=params,
        )

        data = self._extract_data(
            payload
        )

        result_type = (
            data.get(
                "resultType"
            )
        )

        if result_type != "matrix":

            raise PrometheusResponseError(
                "Expected range query "
                "resultType='matrix', "
                f"got {result_type!r}."
            )

        result = data.get(
            "result"
        )

        if not isinstance(
            result,
            list,
        ):

            raise PrometheusResponseError(
                "Prometheus matrix result "
                "must be a list."
            )

        return tuple(
            self._parse_range_series(
                item
            )
            for item
            in result
        )

    def _request(
        self,
        *,
        endpoint: str,
        params: Mapping[
            str,
            str,
        ],
    ) -> dict:

        query_string = urlencode(
            params
        )

        url = (
            f"{self.base_url}"
            f"{endpoint}"
            f"?{query_string}"
        )

        request = Request(
            url=url,
            headers=self.headers,
            method="GET",
        )

        try:

            with urlopen(
                request,
                timeout=(
                    self.timeout_seconds
                ),
            ) as response:

                raw = response.read()

        except HTTPError as exc:

            try:

                body = (
                    exc.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            except Exception:

                body = ""

            message = (
                f"Prometheus HTTP error "
                f"{exc.code}"
            )

            if body:

                message += (
                    f": {body}"
                )

            raise PrometheusTransportError(
                message
            ) from exc

        except URLError as exc:

            raise PrometheusTransportError(
                "Could not reach Prometheus: "
                f"{exc.reason}"
            ) from exc

        except OSError as exc:

            raise PrometheusTransportError(
                "Prometheus transport failure: "
                f"{exc}"
            ) from exc

        try:

            decoded = raw.decode(
                "utf-8"
            )

            payload = json.loads(
                decoded
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:

            raise PrometheusResponseError(
                "Prometheus returned invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):

            raise PrometheusResponseError(
                "Prometheus response must "
                "be a JSON object."
            )

        return payload

    @staticmethod
    def _extract_data(
        payload: dict,
    ) -> dict:

        status = payload.get(
            "status"
        )

        if status == "error":

            error_type = (
                payload.get(
                    "errorType",
                    "unknown",
                )
            )

            error = (
                payload.get(
                    "error",
                    "unknown Prometheus error",
                )
            )

            raise PrometheusAPIError(
                f"{error_type}: {error}"
            )

        if status != "success":

            raise PrometheusResponseError(
                "Unexpected Prometheus "
                f"status: {status!r}."
            )

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):

            raise PrometheusResponseError(
                "Prometheus response "
                "contains no valid data object."
            )

        return data

    @classmethod
    def _parse_instant_sample(
        cls,
        item: object,
    ) -> InstantSample:

        if not isinstance(
            item,
            dict,
        ):

            raise PrometheusResponseError(
                "Prometheus vector entry "
                "must be an object."
            )

        metric = cls._parse_metric(
            item.get(
                "metric"
            )
        )

        value = item.get(
            "value"
        )

        timestamp, number = (
            cls._parse_sample(
                value
            )
        )

        return InstantSample(
            metric=metric,
            timestamp=timestamp,
            value=number,
        )

    @classmethod
    def _parse_range_series(
        cls,
        item: object,
    ) -> RangeSeries:

        if not isinstance(
            item,
            dict,
        ):

            raise PrometheusResponseError(
                "Prometheus matrix entry "
                "must be an object."
            )

        metric = cls._parse_metric(
            item.get(
                "metric"
            )
        )

        values = item.get(
            "values"
        )

        if not isinstance(
            values,
            list,
        ):

            raise PrometheusResponseError(
                "Prometheus matrix entry "
                "must contain a values list."
            )

        samples = tuple(
            RangeSample(
                timestamp=timestamp,
                value=value,
            )
            for timestamp, value
            in (
                cls._parse_sample(
                    raw_sample
                )
                for raw_sample
                in values
            )
        )

        return RangeSeries(
            metric=metric,
            samples=samples,
        )

    @staticmethod
    def _parse_metric(
        raw_metric: object,
    ) -> dict[
        str,
        str,
    ]:

        if not isinstance(
            raw_metric,
            dict,
        ):

            raise PrometheusResponseError(
                "Prometheus metric labels "
                "must be an object."
            )

        metric: dict[
            str,
            str,
        ] = {}

        for key, value in (
            raw_metric.items()
        ):

            if (
                not isinstance(
                    key,
                    str,
                )
                or not isinstance(
                    value,
                    str,
                )
            ):

                raise PrometheusResponseError(
                    "Prometheus metric labels "
                    "must be strings."
                )

            metric[
                key
            ] = value

        return metric

    @staticmethod
    def _parse_sample(
        raw_sample: object,
    ) -> tuple[
        float,
        float,
    ]:

        if (
            not isinstance(
                raw_sample,
                list,
            )
            or len(
                raw_sample
            ) != 2
        ):

            raise PrometheusResponseError(
                "A Prometheus sample must "
                "contain [timestamp, value]."
            )

        raw_timestamp = (
            raw_sample[0]
        )

        raw_value = (
            raw_sample[1]
        )

        try:

            timestamp = float(
                raw_timestamp
            )

            value = float(
                raw_value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise PrometheusResponseError(
                "Prometheus sample contains "
                "a non-numeric timestamp "
                "or value."
            ) from exc

        return (
            timestamp,
            value,
        )

    @staticmethod
    def _validate_promql(
        promql: str,
    ) -> None:

        if (
            not isinstance(
                promql,
                str,
            )
            or not promql.strip()
        ):

            raise ValueError(
                "promql must be "
                "a non-empty string."
            )

    @staticmethod
    def _format_time(
        value: PrometheusTime,
    ) -> str:

        if isinstance(
            value,
            datetime,
        ):

            if (
                value.tzinfo
                is None
                or value.utcoffset()
                is None
            ):

                raise ValueError(
                    "datetime values must "
                    "be timezone-aware."
                )

            return str(
                value.timestamp()
            )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):

            return str(
                value
            )

        if isinstance(
            value,
            str,
        ):

            if not value.strip():

                raise ValueError(
                    "Prometheus time string "
                    "must not be empty."
                )

            return value

        raise TypeError(
            "Unsupported Prometheus "
            f"time type: {type(value)!r}"
        )

    @staticmethod
    def _format_step(
        step: str | int | float,
    ) -> str:

        if isinstance(
            step,
            (
                int,
                float,
            ),
        ):

            if step <= 0:

                raise ValueError(
                    "step must be positive."
                )

            return str(
                step
            )

        if isinstance(
            step,
            str,
        ):

            if not step.strip():

                raise ValueError(
                    "step must not be empty."
                )

            return step

        raise TypeError(
            "step must be a string "
            "or numeric value."
        )
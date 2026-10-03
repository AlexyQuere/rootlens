from __future__ import annotations

import json
import re

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import (
    quote,
    urlencode,
)
from urllib.request import (
    Request,
    urlopen,
)


class JaegerError(RuntimeError):
    """Base error for Jaeger access."""


class JaegerTransportError(
    JaegerError
):
    """Network-level failure."""


class JaegerAPIError(
    JaegerError
):
    """Jaeger returned a non-success response."""


class JaegerResponseError(
    JaegerError
):
    """Jaeger returned an invalid response."""


@dataclass(frozen=True)
class JaegerTracePayload:
    """
    Raw OTLP trace payload returned by Jaeger.

    Parsing ResourceSpans into domain-level
    TraceEvidence is intentionally deferred
    to a separate layer.
    """

    resource_spans: tuple[
        Mapping[str, Any],
        ...
    ]


class JaegerClient:

    def __init__(
        self,
        base_url: str,
        *,
        api_path: str = (
            "/jaeger/ui/api/v3"
        ),
        timeout_seconds: float = 10.0,
        headers: Mapping[
            str,
            str,
        ]
        | None = None,
    ) -> None:

        if not base_url.strip():
            raise ValueError(
                "base_url must not be empty."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must "
                "be positive."
            )

        self._base_url = (
            base_url.rstrip("/")
        )

        self._api_path = (
            "/"
            + api_path.strip("/")
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        self._headers = {
            "Accept":
                "application/json",
        }

        if headers:
            self._headers.update(
                headers
            )

    def list_services(
        self,
    ) -> tuple[str, ...]:

        payload = self._get(
            "/services"
        )

        services = payload.get(
            "services"
        )

        if services is None:
            return ()

        if not isinstance(
            services,
            list,
        ):
            raise JaegerResponseError(
                "Jaeger services response "
                "must contain a list."
            )

        if not all(
            isinstance(
                service,
                str,
            )
            for service
            in services
        ):
            raise JaegerResponseError(
                "Every Jaeger service name "
                "must be a string."
            )

        return tuple(
            sorted(
                services
            )
        )

    def find_traces(
        self,
        *,
        service_name: str,
        start: datetime,
        end: datetime,
        num_traces: int = 20,
        operation_name: str | None = None,
    ) -> JaegerTracePayload:

        if not service_name.strip():
            raise ValueError(
                "service_name must "
                "not be empty."
            )

        self._validate_window(
            start=start,
            end=end,
        )

        if num_traces <= 0:
            raise ValueError(
                "num_traces must "
                "be positive."
            )

        params: dict[
            str,
            str | int,
        ] = {
            "query.service_name":
                service_name,

            "query.num_traces":
                num_traces,

            "query.start_time_min":
                self._format_datetime(
                    start
                ),

            "query.start_time_max":
                self._format_datetime(
                    end
                ),
        }

        if operation_name is not None:

            if not operation_name.strip():
                raise ValueError(
                    "operation_name must "
                    "not be empty."
                )

            params[
                "query.operation_name"
            ] = operation_name

        try:
            payload = self._get(
                "/traces",
                params=params,
            )

        except JaegerAPIError as exc:

            message = str(exc)

            if (
                "HTTP 404" in message
                and "No traces found" in message
            ):
                return JaegerTracePayload(
                    resource_spans=()
                )

            raise

        return self._parse_trace_payload(
            payload
        )

    def get_trace(
        self,
        trace_id: str,
    ) -> JaegerTracePayload:

        normalized = (
            trace_id.strip()
        )

        if not re.fullmatch(
            r"(?:[0-9a-fA-F]{16}|"
            r"[0-9a-fA-F]{32})",
            normalized,
        ):
            raise ValueError(
                "trace_id must be a "
                "16- or 32-character "
                "hexadecimal identifier."
            )

        payload = self._get(
            "/traces/"
            + quote(
                normalized,
                safe="",
            )
        )

        return (
            self._parse_trace_payload(
                payload
            )
        )

    def _get(
        self,
        path: str,
        *,
        params: Mapping[
            str,
            str | int,
        ]
        | None = None,
    ) -> dict[str, Any]:

        url = (
            self._base_url
            + self._api_path
            + path
        )

        if params:
            url += (
                "?"
                + urlencode(
                    params
                )
            )

        request = Request(
            url=url,
            headers=dict(
                self._headers
            ),
            method="GET",
        )

        try:

            with urlopen(
                request,
                timeout=(
                    self._timeout_seconds
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

            raise JaegerAPIError(
                "Jaeger API request "
                f"failed with HTTP "
                f"{exc.code}: {body}"
            ) from exc

        except URLError as exc:

            raise JaegerTransportError(
                "Could not reach Jaeger: "
                f"{exc.reason}"
            ) from exc

        try:

            payload = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:

            raise JaegerResponseError(
                "Jaeger returned invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise JaegerResponseError(
                "Jaeger response must "
                "be a JSON object."
            )

        return payload

    @staticmethod
    def _parse_trace_payload(
        payload: Mapping[
            str,
            Any,
        ],
    ) -> JaegerTracePayload:

        result = payload.get(
            "result"
        )

        if result is None:
            return JaegerTracePayload(
                resource_spans=()
            )

        if not isinstance(
            result,
            dict,
        ):
            raise JaegerResponseError(
                "Jaeger trace result "
                "must be an object."
            )

        resource_spans = (
            result.get(
                "resourceSpans"
            )
        )

        if resource_spans is None:

            return JaegerTracePayload(
                resource_spans=()
            )

        if not isinstance(
            resource_spans,
            list,
        ):
            raise JaegerResponseError(
                "resourceSpans must "
                "be a list."
            )

        if not all(
            isinstance(
                item,
                dict,
            )
            for item
            in resource_spans
        ):
            raise JaegerResponseError(
                "Every resourceSpans item "
                "must be an object."
            )

        return JaegerTracePayload(
            resource_spans=tuple(
                resource_spans
            )
        )

    @staticmethod
    def _validate_window(
        *,
        start: datetime,
        end: datetime,
    ) -> None:

        if (
            start.tzinfo is None
            or start.utcoffset()
            is None
        ):
            raise ValueError(
                "start must be "
                "timezone-aware."
            )

        if (
            end.tzinfo is None
            or end.utcoffset()
            is None
        ):
            raise ValueError(
                "end must be "
                "timezone-aware."
            )

        if end <= start:
            raise ValueError(
                "end must be after start."
            )

    @staticmethod
    def _format_datetime(
        value: datetime,
    ) -> str:

        utc = value.astimezone(
            timezone.utc
        )

        return (
            utc.isoformat(
                timespec="microseconds"
            )
            .replace(
                "+00:00",
                "Z",
            )
        )
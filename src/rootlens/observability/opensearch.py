from __future__ import annotations

import json

from datetime import (
    datetime,
    timezone,
)
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import urlencode
from urllib.request import (
    Request,
    urlopen,
)

from rootlens.observability.log_evidence import (
    LogEvidence,
    LogQueryEvidence,
    LogSearchResult,
    LogTimeField,
    parse_iso_timestamp,
)


class OpenSearchError(
    RuntimeError
):
    pass


class OpenSearchTransportError(
    OpenSearchError
):
    pass


class OpenSearchAPIError(
    OpenSearchError
):
    pass


class OpenSearchResponseError(
    OpenSearchError
):
    pass


class OpenSearchClient:
    def __init__(
        self,
        base_url: str,
        *,
        index_pattern: str = "otel-logs-*",
        timeout_seconds: float = 10.0,
    ) -> None:
        cleaned = (
            base_url
            .strip()
            .rstrip("/")
        )

        if not cleaned:
            raise ValueError(
                "base_url cannot be empty."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        self.base_url = cleaned
        self.index_pattern = index_pattern
        self.timeout_seconds = timeout_seconds

    def search_logs(
        self,
        *,
        start: datetime,
        end: datetime,
        service_name: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        severity_text: str | None = None,
        limit: int = 100,
        time_field: LogTimeField = "observedTimestamp",
    ) -> LogSearchResult:
        self._validate_window(
            start=start,
            end=end,
        )

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        if limit > 1000:
            raise ValueError(
                "limit cannot exceed 1000."
            )

        if time_field not in (
            "@timestamp",
            "observedTimestamp",
        ):
            raise ValueError(
                "Unsupported time field."
            )

        filters: list[
            dict[str, Any]
        ] = [
            {
                "range": {
                    time_field: {
                        "gte":
                            self._format_time(
                                start
                            ),
                        "lte":
                            self._format_time(
                                end
                            ),
                    }
                }
            }
        ]

        if service_name:
            filters.append(
                self._exact_filter(
                    "resource.service.name",
                    service_name,
                )
            )

        if trace_id:
            filters.append(
                self._exact_filter(
                    "traceId",
                    trace_id,
                )
            )

        if span_id:
            filters.append(
                self._exact_filter(
                    "spanId",
                    span_id,
                )
            )

        if severity_text:
            filters.append(
                self._exact_filter(
                    "severity.text",
                    severity_text,
                )
            )

        request_body = {
            "size":
                limit,

            "track_total_hits":
                True,

            "query": {
                "bool": {
                    "filter":
                        filters,
                }
            },

            "sort": [
                {
                    time_field: {
                        "order":
                            "asc",
                        "unmapped_type":
                            "date",
                    }
                }
            ],
        }

        payload = self._post_json(
            (
                f"/{self.index_pattern}"
                "/_search"
            ),
            body=request_body,
            params={
                "ignore_unavailable":
                    "true",
                "allow_no_indices":
                    "true",
            },
        )

        hits_container = payload.get(
            "hits"
        )

        if not isinstance(
            hits_container,
            dict,
        ):
            raise OpenSearchResponseError(
                "OpenSearch response does not "
                "contain a hits object."
            )

        raw_hits = hits_container.get(
            "hits"
        )

        if not isinstance(
            raw_hits,
            list,
        ):
            raise OpenSearchResponseError(
                "OpenSearch response hits.hits "
                "is not a list."
            )

        logs = tuple(
            self._parse_hit(
                hit
            )
            for hit in raw_hits
        )

        logs = tuple(
            sorted(
                logs,
                key=lambda log:
                    self._log_sort_key(
                        log,
                        time_field,
                    ),
            )
        )

        query = LogQueryEvidence(
            index_pattern=(
                self.index_pattern
            ),
            start=start,
            end=end,
            service_name=service_name,
            trace_id=trace_id,
            span_id=span_id,
            severity_text=(
                severity_text
            ),
            limit=limit,
            time_field=time_field,
            request_body=request_body,
        )

        return LogSearchResult(
            query=query,
            logs=logs,
            total_hits=(
                self._parse_total_hits(
                    hits_container.get(
                        "total"
                    )
                )
            ),
            took_ms=(
                self._optional_int(
                    payload.get(
                        "took"
                    )
                )
            ),
            timed_out=bool(
                payload.get(
                    "timed_out",
                    False,
                )
            ),
        )

    def _parse_hit(
        self,
        hit: Any,
    ) -> LogEvidence:
        if not isinstance(
            hit,
            dict,
        ):
            raise OpenSearchResponseError(
                "Search hit is not an object."
            )

        source = hit.get(
            "_source"
        )

        if not isinstance(
            source,
            dict,
        ):
            raise OpenSearchResponseError(
                "Search hit does not "
                "contain _source."
            )

        event_raw = source.get(
            "@timestamp"
        )

        observed_raw = source.get(
            "observedTimestamp"
        )

        event_timestamp = None
        observed_timestamp = None

        if isinstance(
            event_raw,
            str,
        ):
            event_timestamp = (
                parse_iso_timestamp(
                    event_raw
                )
            )
        else:
            event_raw = None

        if isinstance(
            observed_raw,
            str,
        ):
            observed_timestamp = (
                parse_iso_timestamp(
                    observed_raw
                )
            )
        else:
            observed_raw = None

        if (
            event_timestamp is None
            and observed_timestamp is None
        ):
            raise OpenSearchResponseError(
                "Log has neither @timestamp "
                "nor observedTimestamp."
            )

        resource = source.get(
            "resource"
        )

        if not isinstance(
            resource,
            dict,
        ):
            resource = {}

        attributes = source.get(
            "attributes"
        )

        if not isinstance(
            attributes,
            dict,
        ):
            attributes = {}

        scope = source.get(
            "instrumentationScope"
        )

        if not isinstance(
            scope,
            dict,
        ):
            scope = {}

        severity = source.get(
            "severity"
        )

        if not isinstance(
            severity,
            dict,
        ):
            severity = {}

        return LogEvidence(
            event_timestamp=(
                event_timestamp
            ),
            event_timestamp_raw=(
                event_raw
            ),

            observed_timestamp=(
                observed_timestamp
            ),
            observed_timestamp_raw=(
                observed_raw
            ),

            service_name=(
                self._optional_string(
                    resource.get(
                        "service.name"
                    )
                )
            ),

            severity_text=(
                self._optional_string(
                    severity.get(
                        "text"
                    )
                )
            ),

            severity_number=(
                self._optional_int(
                    severity.get(
                        "number"
                    )
                )
            ),

            body=source.get(
                "body"
            ),

            trace_id=(
                self._optional_string(
                    source.get(
                        "traceId"
                    )
                )
            ),

            span_id=(
                self._optional_string(
                    source.get(
                        "spanId"
                    )
                )
            ),

            attributes=attributes,

            resource_attributes=(
                resource
            ),

            instrumentation_scope=(
                scope
            ),

            index=str(
                hit.get(
                    "_index",
                    "",
                )
            ),

            document_id=str(
                hit.get(
                    "_id",
                    "",
                )
            ),

            raw_source=source,
        )

    def _post_json(
        self,
        path: str,
        *,
        body: dict[str, Any],
        params: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        url = (
            self.base_url
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
            url,
            data=json.dumps(
                body
            ).encode(
                "utf-8"
            ),
            headers={
                "Accept":
                    "application/json",
                "Content-Type":
                    "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read()

        except HTTPError as exc:
            body_text = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise OpenSearchAPIError(
                "OpenSearch request failed "
                f"with HTTP {exc.code}: "
                f"{body_text}"
            ) from exc

        except URLError as exc:
            raise OpenSearchTransportError(
                "Could not reach OpenSearch: "
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
            raise OpenSearchResponseError(
                "OpenSearch returned "
                "invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise OpenSearchResponseError(
                "OpenSearch response is not "
                "a JSON object."
            )

        return payload

    @staticmethod
    def _exact_filter(
        field: str,
        value: str,
    ) -> dict[str, Any]:
        return {
            "bool": {
                "should": [
                    {
                        "term": {
                            (
                                field
                                + ".keyword"
                            ):
                                value
                        }
                    },
                    {
                        "term": {
                            field:
                                value
                        }
                    },
                ],
                "minimum_should_match":
                    1,
            }
        }

    @staticmethod
    def _format_time(
        value: datetime,
    ) -> str:
        return (
            value
            .astimezone(
                timezone.utc
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )

    @staticmethod
    def _validate_window(
        *,
        start: datetime,
        end: datetime,
    ) -> None:
        for name, value in (
            ("start", start),
            ("end", end),
        ):
            if (
                value.tzinfo is None
                or value.utcoffset()
                is None
            ):
                raise ValueError(
                    f"{name} must be "
                    "timezone-aware."
                )

        if end <= start:
            raise ValueError(
                "end must be after start."
            )

    @staticmethod
    def _optional_string(
        value: Any,
    ) -> str | None:
        if not isinstance(
            value,
            str,
        ):
            return None

        cleaned = value.strip()

        if not cleaned:
            return None

        return cleaned

    @staticmethod
    def _optional_int(
        value: Any,
    ) -> int | None:
        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            int,
        ):
            return value

        return None

    @staticmethod
    def _parse_total_hits(
        value: Any,
    ) -> int:
        if isinstance(
            value,
            int,
        ):
            return value

        if isinstance(
            value,
            dict,
        ):
            count = value.get(
                "value"
            )

            if isinstance(
                count,
                int,
            ):
                return count

        return 0

    @staticmethod
    def _log_sort_key(
        log: LogEvidence,
        time_field: LogTimeField,
    ) -> tuple:
        if (
            time_field
            == "observedTimestamp"
        ):
            primary = (
                log.observed_timestamp
                or log.event_timestamp
            )
        else:
            primary = (
                log.event_timestamp
                or log.observed_timestamp
            )

        if primary is None:
            raise ValueError(
                "Log has no timestamp."
            )

        return (
            primary,
            (
                log.service_name
                or ""
            ),
            (
                log.trace_id
                or ""
            ),
            (
                log.span_id
                or ""
            ),
            log.index,
            log.document_id,
        )
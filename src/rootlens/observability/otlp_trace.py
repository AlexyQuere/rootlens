from __future__ import annotations

import base64
import re

from collections import defaultdict
from types import MappingProxyType
from typing import Any, Mapping

from rootlens.observability.jaeger import (
    JaegerTracePayload,
)

from rootlens.observability.trace_evidence import (
    SpanEventEvidence,
    SpanEvidence,
    SpanKind,
    SpanStatusCode,
    TraceEvidence,
)


class OTLPTraceParseError(
    ValueError
):
    pass


_KIND_NAMES = {
    "SPAN_KIND_UNSPECIFIED":
        SpanKind.UNSPECIFIED,

    "SPAN_KIND_INTERNAL":
        SpanKind.INTERNAL,

    "SPAN_KIND_SERVER":
        SpanKind.SERVER,

    "SPAN_KIND_CLIENT":
        SpanKind.CLIENT,

    "SPAN_KIND_PRODUCER":
        SpanKind.PRODUCER,

    "SPAN_KIND_CONSUMER":
        SpanKind.CONSUMER,
}


_STATUS_NAMES = {
    "STATUS_CODE_UNSET":
        SpanStatusCode.UNSET,

    "STATUS_CODE_OK":
        SpanStatusCode.OK,

    "STATUS_CODE_ERROR":
        SpanStatusCode.ERROR,
}


def parse_otlp_traces(
    payload: JaegerTracePayload,
) -> tuple[
    TraceEvidence,
    ...
]:

    grouped: dict[
        str,
        list[SpanEvidence],
    ] = defaultdict(list)

    for resource_span in (
        payload.resource_spans
    ):

        resource = _expect_mapping(
            resource_span.get(
                "resource",
                {},
            ),
            "resource",
        )

        resource_attributes = (
            _parse_attributes(
                resource.get(
                    "attributes",
                    [],
                )
            )
        )

        service_value = (
            resource_attributes.get(
                "service.name"
            )
        )

        if (
            service_value is not None
            and not isinstance(
                service_value,
                str,
            )
        ):
            raise OTLPTraceParseError(
                "service.name must be "
                "a string when present."
            )

        service_name = (
            service_value
            if service_value
            else None
        )

        scope_spans = (
            resource_span.get(
                "scopeSpans",
                [],
            )
        )

        if not isinstance(
            scope_spans,
            list,
        ):
            raise OTLPTraceParseError(
                "scopeSpans must be a list."
            )

        for scope_span in scope_spans:

            scope_span = (
                _expect_mapping(
                    scope_span,
                    "scopeSpan",
                )
            )

            scope = _expect_mapping(
                scope_span.get(
                    "scope",
                    {},
                ),
                "scope",
            )

            scope_name = (
                scope.get(
                    "name"
                )
            )

            scope_version = (
                scope.get(
                    "version"
                )
            )

            spans = scope_span.get(
                "spans",
                [],
            )

            if not isinstance(
                spans,
                list,
            ):
                raise OTLPTraceParseError(
                    "spans must be a list."
                )

            for raw_span in spans:

                span = _parse_span(
                    raw_span,
                    service_name=(
                        service_name
                    ),
                    resource_attributes=(
                        resource_attributes
                    ),
                    scope_name=(
                        scope_name
                    ),
                    scope_version=(
                        scope_version
                    ),
                )

                grouped[
                    span.trace_id
                ].append(
                    span
                )

    traces = []

    for trace_id, spans in (
        grouped.items()
    ):

        ordered = tuple(
            sorted(
                spans,
                key=lambda span: (
                    span.start_time_unix_nano,
                    span.span_id,
                ),
            )
        )

        traces.append(
            TraceEvidence(
                trace_id=trace_id,
                spans=ordered,
            )
        )

    return tuple(
        sorted(
            traces,
            key=lambda trace: (
                trace.start_time_unix_nano,
                trace.trace_id,
            ),
        )
    )


def _parse_span(
    raw_span: Any,
    *,
    service_name: str | None,
    resource_attributes:
        Mapping[str, Any],
    scope_name: str | None,
    scope_version: str | None,
) -> SpanEvidence:

    raw_span = _expect_mapping(
        raw_span,
        "span",
    )

    trace_id = _hex_id(
        raw_span.get(
            "traceId"
        ),
        length=32,
        field="traceId",
    )

    span_id = _hex_id(
        raw_span.get(
            "spanId"
        ),
        length=16,
        field="spanId",
    )

    raw_parent = raw_span.get(
        "parentSpanId"
    )

    parent_span_id = None

    if raw_parent:

        parent_span_id = _hex_id(
            raw_parent,
            length=16,
            field="parentSpanId",
        )

    operation_name = raw_span.get(
        "name"
    )

    if not isinstance(
        operation_name,
        str,
    ) or not operation_name:

        raise OTLPTraceParseError(
            "span name must be "
            "a non-empty string."
        )

    kind = _parse_kind(
        raw_span.get(
            "kind",
            0,
        )
    )

    start = _parse_integer(
        raw_span.get(
            "startTimeUnixNano"
        ),
        "startTimeUnixNano",
    )

    end = _parse_integer(
        raw_span.get(
            "endTimeUnixNano"
        ),
        "endTimeUnixNano",
    )

    if end < start:
        raise OTLPTraceParseError(
            "endTimeUnixNano precedes "
            "startTimeUnixNano."
        )

    status = _expect_mapping(
        raw_span.get(
            "status",
            {},
        ),
        "status",
    )

    status_code = (
        _parse_status(
            status.get(
                "code",
                0,
            )
        )
    )

    status_message = status.get(
        "message"
    )

    if (
        status_message is not None
        and not isinstance(
            status_message,
            str,
        )
    ):
        raise OTLPTraceParseError(
            "status.message must "
            "be a string."
        )

    attributes = _parse_attributes(
        raw_span.get(
            "attributes",
            [],
        )
    )

    events = _parse_events(
        raw_span.get(
            "events",
            [],
        )
    )

    return SpanEvidence(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=(
            parent_span_id
        ),
        service_name=service_name,
        operation_name=(
            operation_name
        ),
        kind=kind,
        start_time_unix_nano=start,
        end_time_unix_nano=end,
        status_code=status_code,
        status_message=(
            status_message
        ),
        attributes=attributes,
        resource_attributes=(
            resource_attributes
        ),
        events=events,
        scope_name=scope_name,
        scope_version=scope_version,
    )


def _parse_events(
    raw: Any,
) -> tuple[
    SpanEventEvidence,
    ...
]:

    if raw is None:
        return ()

    if not isinstance(
        raw,
        list,
    ):
        raise OTLPTraceParseError(
            "events must be a list."
        )

    result = []

    for event in raw:

        event = _expect_mapping(
            event,
            "event",
        )

        name = event.get(
            "name"
        )

        if not isinstance(
            name,
            str,
        ) or not name:

            raise OTLPTraceParseError(
                "event name must be "
                "a non-empty string."
            )

        timestamp = _parse_integer(
            event.get(
                "timeUnixNano"
            ),
            "event.timeUnixNano",
        )

        result.append(
            SpanEventEvidence(
                name=name,
                time_unix_nano=timestamp,
                attributes=(
                    _parse_attributes(
                        event.get(
                            "attributes",
                            [],
                        )
                    )
                ),
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda event:
                event.time_unix_nano,
        )
    )


def _parse_attributes(
    raw: Any,
) -> Mapping[str, Any]:

    if raw is None:
        return MappingProxyType({})

    if not isinstance(
        raw,
        list,
    ):
        raise OTLPTraceParseError(
            "attributes must be a list."
        )

    result: dict[
        str,
        Any,
    ] = {}

    for entry in raw:

        entry = _expect_mapping(
            entry,
            "attribute",
        )

        key = entry.get(
            "key"
        )

        if not isinstance(
            key,
            str,
        ) or not key:

            raise OTLPTraceParseError(
                "attribute key must "
                "be a non-empty string."
            )

        if key in result:
            raise OTLPTraceParseError(
                "duplicate attribute key: "
                f"{key}"
            )

        if "value" not in entry:
            raise OTLPTraceParseError(
                "attribute has no value: "
                f"{key}"
            )

        result[
            key
        ] = _parse_any_value(
            entry[
                "value"
            ]
        )

    return MappingProxyType(
        result
    )


def _parse_any_value(
    raw: Any,
) -> Any:

    raw = _expect_mapping(
        raw,
        "AnyValue",
    )

    if "stringValue" in raw:
        return raw[
            "stringValue"
        ]

    if "boolValue" in raw:

        value = raw[
            "boolValue"
        ]

        if not isinstance(
            value,
            bool,
        ):
            raise OTLPTraceParseError(
                "boolValue must be boolean."
            )

        return value

    if "intValue" in raw:
        return _parse_integer(
            raw[
                "intValue"
            ],
            "intValue",
        )

    if "doubleValue" in raw:

        try:
            return float(
                raw[
                    "doubleValue"
                ]
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise OTLPTraceParseError(
                "Invalid doubleValue."
            ) from exc

    if "bytesValue" in raw:

        value = raw[
            "bytesValue"
        ]

        if not isinstance(
            value,
            str,
        ):
            raise OTLPTraceParseError(
                "bytesValue must be "
                "base64 text."
            )

        try:
            return base64.b64decode(
                value,
                validate=True,
            )

        except ValueError as exc:

            raise OTLPTraceParseError(
                "Invalid bytesValue."
            ) from exc

    if "arrayValue" in raw:

        array = _expect_mapping(
            raw[
                "arrayValue"
            ],
            "arrayValue",
        )

        values = array.get(
            "values",
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            raise OTLPTraceParseError(
                "arrayValue.values "
                "must be a list."
            )

        return tuple(
            _parse_any_value(
                value
            )
            for value in values
        )

    if "kvlistValue" in raw:

        kvlist = _expect_mapping(
            raw[
                "kvlistValue"
            ],
            "kvlistValue",
        )

        return _parse_attributes(
            kvlist.get(
                "values",
                [],
            )
        )

    raise OTLPTraceParseError(
        "Unsupported or empty AnyValue."
    )


def _parse_kind(
    raw: Any,
) -> SpanKind:

    if isinstance(
        raw,
        str,
    ) and raw in _KIND_NAMES:

        return _KIND_NAMES[
            raw
        ]

    value = _parse_integer(
        raw,
        "span.kind",
    )

    try:
        return SpanKind(
            value
        )

    except ValueError as exc:

        raise OTLPTraceParseError(
            "Unknown SpanKind: "
            f"{raw}"
        ) from exc


def _parse_status(
    raw: Any,
) -> SpanStatusCode:

    if isinstance(
        raw,
        str,
    ) and raw in _STATUS_NAMES:

        return _STATUS_NAMES[
            raw
        ]

    value = _parse_integer(
        raw,
        "status.code",
    )

    try:
        return SpanStatusCode(
            value
        )

    except ValueError as exc:

        raise OTLPTraceParseError(
            "Unknown status code: "
            f"{raw}"
        ) from exc


def _parse_integer(
    raw: Any,
    field: str,
) -> int:

    if isinstance(
        raw,
        bool,
    ):
        raise OTLPTraceParseError(
            f"{field} must be integer."
        )

    try:
        return int(
            raw
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise OTLPTraceParseError(
            f"{field} must be integer."
        ) from exc


def _hex_id(
    raw: Any,
    *,
    length: int,
    field: str,
) -> str:

    if not isinstance(
        raw,
        str,
    ):
        raise OTLPTraceParseError(
            f"{field} must be text."
        )

    normalized = (
        raw.lower()
    )

    if not re.fullmatch(
        rf"[0-9a-f]{{{length}}}",
        normalized,
    ):
        raise OTLPTraceParseError(
            f"{field} must contain "
            f"{length} hexadecimal "
            "characters."
        )

    return normalized


def _expect_mapping(
    raw: Any,
    field: str,
) -> Mapping[str, Any]:

    if not isinstance(
        raw,
        Mapping,
    ):
        raise OTLPTraceParseError(
            f"{field} must be an object."
        )

    return raw
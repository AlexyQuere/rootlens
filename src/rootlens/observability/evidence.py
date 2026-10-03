from __future__ import annotations

import math

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(
    frozen=True
)
class TimeWindow:
    """
    Closed observation window.

    All datetimes must be timezone-aware.
    """

    start: datetime
    end: datetime

    def __post_init__(
        self,
    ) -> None:

        if (
            self.start.tzinfo is None
            or self.start.utcoffset() is None
        ):
            raise ValueError(
                "start must be timezone-aware."
            )

        if (
            self.end.tzinfo is None
            or self.end.utcoffset() is None
        ):
            raise ValueError(
                "end must be timezone-aware."
            )

        if self.end <= self.start:
            raise ValueError(
                "end must be after start."
            )

    @property
    def duration_seconds(
        self,
    ) -> float:

        return (
            self.end
            - self.start
        ).total_seconds()


@dataclass(
    frozen=True
)
class MetricEvidence:
    """
    One deterministic metric observation.

    The object contains both the observation and
    the provenance required to reproduce it.
    """

    name: str
    statistic: str
    value: float
    unit: str

    service: str | None

    window: TimeWindow

    promql: str

    source: str = "prometheus"

    labels: Mapping[
        str,
        str,
    ] | None = None

    def __post_init__(
        self,
    ) -> None:

        if not self.name.strip():
            raise ValueError(
                "name must not be empty."
            )

        if not self.statistic.strip():
            raise ValueError(
                "statistic must not be empty."
            )

        if not self.unit.strip():
            raise ValueError(
                "unit must not be empty."
            )

        if not self.promql.strip():
            raise ValueError(
                "promql must not be empty."
            )

        if not self.source.strip():
            raise ValueError(
                "source must not be empty."
            )

        if (
            self.service is not None
            and not self.service.strip()
        ):
            raise ValueError(
                "service must either be None "
                "or a non-empty string."
            )

        if not math.isfinite(
            self.value
        ):
            raise ValueError(
                "metric value must be finite."
            )


@dataclass(
    frozen=True
)
class MetricComparisonEvidence:
    """
    Comparison of the same metric between
    baseline and incident windows.

    Delta values are derived from the two
    observations and cannot be supplied manually.
    """

    baseline: MetricEvidence
    incident: MetricEvidence

    zero_tolerance: float = 1e-12

    def __post_init__(
        self,
    ) -> None:

        if self.zero_tolerance < 0:
            raise ValueError(
                "zero_tolerance must be "
                "non-negative."
            )

        if (
            self.baseline.name
            != self.incident.name
        ):
            raise ValueError(
                "baseline and incident metrics "
                "must have the same name."
            )

        if (
            self.baseline.statistic
            != self.incident.statistic
        ):
            raise ValueError(
                "baseline and incident metrics "
                "must use the same statistic."
            )

        if (
            self.baseline.unit
            != self.incident.unit
        ):
            raise ValueError(
                "baseline and incident metrics "
                "must use the same unit."
            )

        if (
            self.baseline.service
            != self.incident.service
        ):
            raise ValueError(
                "baseline and incident metrics "
                "must refer to the same service."
            )

    @property
    def name(
        self,
    ) -> str:

        return self.baseline.name

    @property
    def statistic(
        self,
    ) -> str:

        return self.baseline.statistic

    @property
    def unit(
        self,
    ) -> str:

        return self.baseline.unit

    @property
    def service(
        self,
    ) -> str | None:

        return self.baseline.service

    @property
    def absolute_delta(
        self,
    ) -> float:

        return (
            self.incident.value
            - self.baseline.value
        )

    @property
    def relative_delta(
        self,
    ) -> float | None:

        baseline_value = (
            self.baseline.value
        )

        if (
            abs(
                baseline_value
            )
            <= self.zero_tolerance
        ):
            return None

        return (
            self.absolute_delta
            / abs(
                baseline_value
            )
        )
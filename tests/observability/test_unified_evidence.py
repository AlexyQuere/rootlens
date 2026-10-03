from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

import pytest

from rootlens.observability.unified_evidence import (
    AcquisitionState,
    EvidenceModality,
    IncidentEvidenceBundle,
    ModalityAcquisition,
)


def window():
    return (
        datetime(
            2026,
            10,
            3,
            13,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026,
            10,
            3,
            13,
            5,
            tzinfo=timezone.utc,
        ),
    )


def test_empty_bundle_is_valid():
    start, end = window()

    bundle = IncidentEvidenceBundle(
        incident_id="incident-001",

        start=start,
        end=end,
    )

    assert bundle.metrics == ()
    assert bundle.traces == ()
    assert bundle.logs == ()

    assert bundle.trace_ids == ()
    assert bundle.span_keys == ()
    assert bundle.service_names == ()


def test_empty_acquisition_is_not_observed():
    acquisition = (
        ModalityAcquisition(
            modality=(
                EvidenceModality.LOG
            ),

            state=(
                AcquisitionState.EMPTY
            ),

            source_system="opensearch",

            evidence_count=0,
        )
    )

    assert (
        acquisition.state
        == AcquisitionState.EMPTY
    )


def test_observed_requires_evidence():
    with pytest.raises(
        ValueError
    ):
        ModalityAcquisition(
            modality=(
                EvidenceModality.LOG
            ),

            state=(
                AcquisitionState.OBSERVED
            ),

            source_system="opensearch",

            evidence_count=0,
        )


def test_empty_requires_zero_count():
    with pytest.raises(
        ValueError
    ):
        ModalityAcquisition(
            modality=(
                EvidenceModality.TRACE
            ),

            state=(
                AcquisitionState.EMPTY
            ),

            source_system="jaeger",

            evidence_count=1,
        )


def test_unavailable_requires_zero_count():
    with pytest.raises(
        ValueError
    ):
        ModalityAcquisition(
            modality=(
                EvidenceModality.METRIC
            ),

            state=(
                AcquisitionState.UNAVAILABLE
            ),

            source_system="prometheus",

            evidence_count=2,
        )


def test_duplicate_modality_acquisition_rejected():
    start, end = window()

    acquisitions = (
        ModalityAcquisition(
            modality=(
                EvidenceModality.LOG
            ),
            state=(
                AcquisitionState.EMPTY
            ),
            source_system="opensearch",
            evidence_count=0,
        ),

        ModalityAcquisition(
            modality=(
                EvidenceModality.LOG
            ),
            state=(
                AcquisitionState.UNAVAILABLE
            ),
            source_system="opensearch",
            evidence_count=0,
        ),
    )

    with pytest.raises(
        ValueError
    ):
        IncidentEvidenceBundle(
            incident_id="incident-001",

            start=start,
            end=end,

            acquisitions=(
                acquisitions
            ),
        )


def test_declared_count_must_match_bundle():
    start, end = window()

    acquisition = (
        ModalityAcquisition(
            modality=(
                EvidenceModality.LOG
            ),

            state=(
                AcquisitionState.OBSERVED
            ),

            source_system="opensearch",

            evidence_count=1,
        )
    )

    with pytest.raises(
        ValueError
    ):
        IncidentEvidenceBundle(
            incident_id="incident-001",

            start=start,
            end=end,

            logs=(),

            acquisitions=(
                acquisition,
            ),
        )


def test_naive_datetimes_rejected():
    start = datetime(
        2026,
        10,
        3,
        13,
        0,
    )

    end = datetime(
        2026,
        10,
        3,
        13,
        5,
    )

    with pytest.raises(
        ValueError
    ):
        IncidentEvidenceBundle(
            incident_id="incident-001",

            start=start,
            end=end,
        )
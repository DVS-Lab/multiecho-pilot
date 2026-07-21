#!/usr/bin/env python3
"""Audit acquisition metadata in one or more BIDS datasets.

The audit is intentionally metadata-first.  It reads BIDS JSON/TSV files,
applies the BIDS inheritance principle, and uses nibabel only for NIfTI
headers whose image content is already available locally.  It never fetches
annexed or otherwise unavailable image content.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import nibabel as nib
except ImportError:  # Header inspection is optional when content is absent.
    nib = None


PRINCIPAL_ACQUISITIONS = (
    "mb1me1",
    "mb1me4",
    "mb3me1",
    "mb3me4",
    "mb6me1",
    "mb6me4",
)

IMAGE_SUFFIXES = {
    "bold",
    "sbref",
    "T1w",
    "magnitude1",
    "magnitude2",
    "phasediff",
    "fieldmap",
    "epi",
}

PARAMETER_FIELDS = (
    "MagneticFieldStrength",
    "Manufacturer",
    "ManufacturersModelName",
    "InstitutionName",
    "InstitutionalDepartmentName",
    "ReceiveCoilName",
    "Modality",
    "ScanningSequence",
    "SequenceVariant",
    "ScanOptions",
    "MRAcquisitionType",
    "SequenceName",
    "PulseSequenceDetails",
    "RepetitionTime",
    "EchoTime",
    "EchoTime1",
    "EchoTime2",
    "FlipAngle",
    "MultibandAccelerationFactor",
    "ParallelReductionFactorInPlane",
    "PartialFourier",
    "PhaseEncodingDirection",
    "SliceTiming",
    "SliceThickness",
    "SpacingBetweenSlices",
    "BaseResolution",
    "AcquisitionMatrixPE",
    "ReconMatrixPE",
    "ImageOrientationPatientDICOM",
    "ImageOrientationText",
    "ProtocolName",
    "SeriesDescription",
)

ACQUISITION_COLUMNS = (
    "dataset_source",
    "acquisition_label",
    "task",
    "participant_count",
    "bold_file_count",
    "nominal_echo_count",
    "observed_echo_count",
    "echo_times_s",
    "repetition_time_s",
    "multiband_acceleration_factor",
    "in_plane_acceleration",
    "flip_angle_deg",
    "scanning_sequence",
    "pulse_sequence_details",
    "phase_encoding_direction",
    "image_orientation",
    "inferred_slice_order",
    "slice_timing_summary",
    "number_of_slices",
    "nifti_matrix_dimensions",
    "nifti_voxel_dimensions_mm",
    "base_resolution",
    "acquisition_matrix_pe",
    "recon_matrix_pe",
    "slice_thickness_mm",
    "spacing_between_slices_mm",
    "partial_fourier",
    "receive_coil_name",
    "sbref_count",
    "source_files",
    "exceptions_and_notes",
)

CLAIM_COLUMNS = (
    "claim_id",
    "technical_proposition",
    "complete_dataset_status",
    "complete_dataset_observed_values",
    "complete_dataset_coverage",
    "openneuro_status",
    "openneuro_observed_values",
    "openneuro_coverage",
    "evidence_files",
    "reasoning",
    "suggested_technical_correction",
)

VALID_STATUSES = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "NOT_VERIFIABLE_FROM_METADATA",
    "NOT_REPRESENTED_IN_DATASET",
    "DATA_SOURCE_UNAVAILABLE",
}

CLAIMS = (
    ("facility_tubric", "Named acquisition facility is TUBRIC."),
    ("scanner_3t", "Scanner field strength is 3 T."),
    ("scanner_siemens", "Scanner manufacturer is Siemens."),
    ("scanner_prisma", "Scanner model is Prisma."),
    ("functional_bold", "Functional files are BOLD acquisitions."),
    ("functional_epi", "Functional BOLD uses echo-planar imaging."),
    ("functional_t2star_weighting", "Functional BOLD is T2*-weighted."),
    ("functional_axial_orientation", "Functional slices are approximately axial."),
    ("functional_descending_slice_order", "Functional slice acquisition is descending."),
    ("six_principal_acquisitions", "All six principal acquisition labels are represented."),
    ("multiband_factors_1_3_6", "Multiband factors 1, 3, and 6 are used."),
    ("echo_counts_1_and_4", "Single-echo and four-echo acquisitions are used."),
    ("functional_flip_angle_20", "Principal functional flip angle is 20 degrees."),
    ("functional_resolution_identical", "Principal functional spatial resolution is identical."),
    ("functional_voxel_dimensions_2p7", "Functional sampling is 2.7 mm isotropic."),
    ("whole_brain_coverage", "Functional images provide whole-brain coverage."),
    ("ventral_cerebellum_coverage", "Functional coverage includes ventral cerebellum."),
    ("sbref_each_acquisition", "Each principal acquisition has an associated SBRef."),
    ("t1_tr_2p4", "T1w repetition time is 2.4 s."),
    ("t1_te_2p17ms", "T1w echo time is 2.17 ms."),
    ("t1_matrix_224", "T1w image matrix is 224 by 224."),
    ("t1_voxel_dimensions_1mm", "T1w voxels are 1 mm isotropic."),
    ("t1_slices_224", "T1w image has 224 slices."),
    ("t1_flip_angle_8", "T1w flip angle is 8 degrees."),
    ("fieldmap_present", "GRE B0 field maps are present."),
    ("fieldmap_tr_645ms", "Field-map repetition time is 645 ms."),
    ("fieldmap_te1_4p92ms", "Field-map first echo time is 4.92 ms."),
    ("fieldmap_te2_7p38ms", "Field-map second echo time is 7.38 ms."),
    ("fieldmap_matrix_80", "Field-map image matrix is 80 by 80."),
    ("fieldmap_voxel_dimensions_2p7", "Field-map sampling is 2.7 mm isotropic."),
    ("fieldmap_slices_54", "Field-map image has 54 slices."),
    ("fieldmap_gap_10pct", "Field-map implied interslice gap is 10 percent."),
    ("fieldmap_flip_angle_60", "Field-map flip angle is 60 degrees."),
    ("coil_64ch_present", "A 64-channel receive-coil group is present."),
    ("coil_20ch_present", "A 20-channel receive-coil group is present."),
    ("coil_assignment_complete", "Every participant has a metadata-based coil assignment."),
    ("coil_64ch_primary_sample", "Primary analysis sample uses the 64-channel coil group."),
    ("public_release_contains_both_coils", "Public release represents both coil groups."),
    ("scan_order_reconstructable", "Participant acquisition order is reconstructable."),
    ("six_acquisition_orders_observed", "All six acquisition orders are observed in participant records."),
    ("latin_square_defined", "A six-order cyclic counterbalancing scheme is defined."),
    ("latin_square_assignments_verified", "Participant assignments follow a defined order."),
)


@dataclass(frozen=True)
class DatasetSpec:
    label: str
    root: Path


@dataclass
class ImageRecord:
    dataset: str
    root: Path
    json_path: Path
    relpath: str
    suffix: str
    entities: dict[str, str]
    metadata: dict[str, Any]
    metadata_sources: list[str]
    nifti_path: Path | None
    image_status: str
    shape: tuple[int, ...] | None = None
    zooms: tuple[float, ...] | None = None
    axis_codes: tuple[str, ...] | None = None
    header_error: str = ""

    @property
    def participant(self) -> str:
        value = self.entities.get("sub", "")
        return f"sub-{value}" if value else ""

    @property
    def acquisition(self) -> str:
        return self.entities.get("acq", "")

    @property
    def task(self) -> str:
        return self.entities.get("task", "")

    @property
    def part(self) -> str:
        return self.entities.get("part", "")

    @property
    def echo(self) -> str:
        return self.entities.get("echo", "")


@dataclass
class DatasetAudit:
    spec: DatasetSpec
    available: bool
    access_note: str
    records: list[ImageRecord] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    description: dict[str, Any] = field(default_factory=dict)
    scans_files: list[str] = field(default_factory=list)
    scan_orders: dict[str, tuple[str, ...]] = field(default_factory=dict)
    inventory_counts: Counter[str] = field(default_factory=Counter)
    json_errors: list[str] = field(default_factory=list)

    def records_for(self, *suffixes: str) -> list[ImageRecord]:
        wanted = set(suffixes)
        return [record for record in self.records if record.suffix in wanted]

    def main_bold(self) -> list[ImageRecord]:
        return [
            record
            for record in self.records_for("bold")
            if record.part.lower() != "phase"
        ]

    def main_sbref(self) -> list[ImageRecord]:
        return [
            record
            for record in self.records_for("sbref")
            if record.part.lower() != "phase"
        ]


@dataclass(frozen=True)
class Evaluation:
    status: str
    observed: str
    coverage: str
    reasoning: str
    correction: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit BIDS acquisition metadata across one or more labeled datasets. "
            "The command reads JSON/TSV metadata and available NIfTI headers; it "
            "does not download unavailable imaging data."
        )
    )
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help=(
            "Labeled BIDS root. Repeat for multiple sources, for example "
            "--dataset complete=/data/bids --dataset openneuro=/data/ds005085."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for acquisition_parameters.tsv, claim_validation.tsv, dataset_comparison.tsv, and metadata_audit.md.",
    )
    parser.add_argument(
        "--counterbalance-file",
        type=Path,
        help="Optional source file containing acquisition-order definitions.",
    )
    return parser.parse_args(argv)


def parse_dataset(value: str) -> DatasetSpec:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"Dataset must use LABEL=PATH syntax, received: {value!r}"
        )
    label, raw_path = value.split("=", 1)
    label = label.strip()
    raw_path = raw_path.strip()
    if not label or not raw_path:
        raise argparse.ArgumentTypeError(
            f"Dataset must use non-empty LABEL=PATH syntax, received: {value!r}"
        )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
        raise argparse.ArgumentTypeError(
            f"Dataset label contains unsupported characters: {label!r}"
        )
    return DatasetSpec(label=label, root=Path(raw_path).expanduser().resolve())


def strip_extension(name: str) -> str:
    if name.endswith(".nii.gz"):
        return name[:-7]
    return Path(name).stem


def parse_bids_name(path: Path) -> tuple[dict[str, str], str]:
    stem = strip_extension(path.name)
    tokens = stem.split("_")
    suffix = tokens[-1] if tokens else ""
    entities: dict[str, str] = {}
    for token in tokens[:-1]:
        if "-" not in token:
            continue
        key, value = token.split("-", 1)
        if key and value:
            entities[key] = value
    return entities, suffix


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def is_ancestor(candidate: Path, target: Path) -> bool:
    try:
        target.relative_to(candidate)
    except ValueError:
        return False
    return True


def inheritance_candidates(
    target: Path,
    target_entities: dict[str, str],
    target_suffix: str,
    json_index: list[tuple[Path, dict[str, str], str]],
) -> list[tuple[Path, dict[str, str], str]]:
    applicable = []
    for path, entities, suffix in json_index:
        if suffix != target_suffix:
            continue
        if not is_ancestor(path.parent, target.parent):
            continue
        if any(target_entities.get(key) != value for key, value in entities.items()):
            continue
        applicable.append((path, entities, suffix))
    return sorted(
        applicable,
        key=lambda item: (
            len(item[0].parts),
            len(item[1]),
            item[0].as_posix(),
        ),
    )


def image_path_for_sidecar(json_path: Path) -> Path | None:
    base = json_path.with_suffix("")
    gz_path = Path(f"{base}.nii.gz")
    nii_path = Path(f"{base}.nii")
    if gz_path.exists() or gz_path.is_symlink():
        return gz_path
    if nii_path.exists() or nii_path.is_symlink():
        return nii_path
    return None


def looks_like_pointer(path: Path) -> bool:
    if path.is_symlink() and not path.exists():
        target = str(path.readlink())
        return ".git/annex/objects/" in target or "annex/objects/" in target
    if not path.exists() or not path.is_file():
        return False
    try:
        if path.stat().st_size > 4096:
            return False
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    text = sample.decode("utf-8", errors="ignore")
    return (
        ".git/annex/objects/" in text
        or text.startswith("version https://git-lfs.github.com/spec")
        or text.startswith("/annex/objects/")
    )


def inspect_image(path: Path | None) -> tuple[
    str,
    tuple[int, ...] | None,
    tuple[float, ...] | None,
    tuple[str, ...] | None,
    str,
]:
    if path is None:
        return "not_listed", None, None, None, ""
    if looks_like_pointer(path):
        return "annex_pointer_unavailable", None, None, None, ""
    if not path.exists():
        return "unavailable", None, None, None, ""
    if nib is None:
        return (
            "available_header_not_read",
            None,
            None,
            None,
            "nibabel is not installed",
        )
    try:
        image = nib.load(str(path))
        shape = tuple(int(value) for value in image.shape)
        zooms = tuple(float(value) for value in image.header.get_zooms())
        axis_codes = tuple(str(value) for value in nib.aff2axcodes(image.affine))
        return "available", shape, zooms, axis_codes, ""
    except Exception as exc:  # A malformed image should not abort a metadata audit.
        return "header_error", None, None, None, f"{type(exc).__name__}: {exc}"


def relative_source(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def inventory_file_types(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        if not (path.is_file() or path.is_symlink()):
            continue
        name = path.name
        if name.endswith(".nii.gz") or name.endswith(".nii"):
            counts["nifti_entries"] += 1
            if looks_like_pointer(path):
                counts["nifti_unavailable_pointers"] += 1
            elif path.exists():
                counts["nifti_available"] += 1
        elif name.endswith(".json"):
            counts["json"] += 1
        elif name.endswith(".tsv"):
            counts["tsv"] += 1
        if "_sbref." in name:
            counts["sbref_entries"] += 1
    return counts


def read_participants(root: Path) -> list[str]:
    participants = {
        path.name
        for path in root.glob("sub-*")
        if path.is_dir()
    }
    participants_tsv = root / "participants.tsv"
    if participants_tsv.is_file():
        try:
            with participants_tsv.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream, delimiter="\t"):
                    participant = (row.get("participant_id") or "").strip()
                    if participant.startswith("sub-"):
                        participants.add(participant)
        except (OSError, csv.Error):
            pass
    return sorted(participants)


def acquisition_from_filename(filename: str) -> str:
    match = re.search(r"(?:^|_)acq-([^_./]+)", filename)
    return match.group(1) if match else ""


def read_scan_orders(root: Path) -> tuple[list[str], dict[str, tuple[str, ...]]]:
    scan_files: list[str] = []
    scan_orders: dict[str, tuple[str, ...]] = {}
    for path in sorted(root.rglob("*_scans.tsv")):
        participant_match = re.search(r"sub-[A-Za-z0-9]+", path.as_posix())
        participant = participant_match.group(0) if participant_match else ""
        if not participant:
            continue
        scan_files.append(relative_source(root, path))
        ordered: list[str] = []
        seen: set[str] = set()
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream, delimiter="\t"):
                    filename = (row.get("filename") or "").strip()
                    if not re.search(r"_bold\.nii(?:\.gz)?$", filename):
                        continue
                    acquisition = acquisition_from_filename(filename)
                    if acquisition and acquisition not in seen:
                        ordered.append(acquisition)
                        seen.add(acquisition)
        except (OSError, csv.Error, UnicodeError):
            continue
        scan_orders[participant] = tuple(ordered)
    return scan_files, dict(sorted(scan_orders.items()))


def audit_dataset(spec: DatasetSpec) -> DatasetAudit:
    root = spec.root
    if not root.is_dir():
        return DatasetAudit(
            spec=spec,
            available=False,
            access_note=f"BIDS root is unavailable: {root}",
        )

    description: dict[str, Any] = {}
    description_path = root / "dataset_description.json"
    if description_path.is_file():
        try:
            description = read_json(description_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            description = {}

    json_index: list[tuple[Path, dict[str, str], str]] = []
    for path in sorted(root.rglob("*.json")):
        entities, suffix = parse_bids_name(path)
        if suffix in IMAGE_SUFFIXES:
            json_index.append((path, entities, suffix))

    records: list[ImageRecord] = []
    errors: list[str] = []
    for target, entities, suffix in json_index:
        # Dataset-, modality-, or task-level sidecars are inheritance sources,
        # not participant image instances in their own right.
        if "sub" not in entities:
            continue
        inherited: dict[str, Any] = {}
        sources: list[str] = []
        candidates = inheritance_candidates(target, entities, suffix, json_index)
        for candidate, _, _ in candidates:
            try:
                inherited.update(read_json(candidate))
                sources.append(relative_source(root, candidate))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                errors.append(
                    f"{relative_source(root, candidate)}: {type(exc).__name__}: {exc}"
                )
        nifti_path = image_path_for_sidecar(target)
        image_status, shape, zooms, axis_codes, header_error = inspect_image(nifti_path)
        records.append(
            ImageRecord(
                dataset=spec.label,
                root=root,
                json_path=target,
                relpath=relative_source(root, target),
                suffix=suffix,
                entities=entities,
                metadata=inherited,
                metadata_sources=sorted(set(sources)),
                nifti_path=nifti_path,
                image_status=image_status,
                shape=shape,
                zooms=zooms,
                axis_codes=axis_codes,
                header_error=header_error,
            )
        )

    scans_files, scan_orders = read_scan_orders(root)
    return DatasetAudit(
        spec=spec,
        available=True,
        access_note="BIDS root inspected directly",
        records=sorted(records, key=lambda record: record.relpath),
        participants=read_participants(root),
        description=description,
        scans_files=scans_files,
        scan_orders=scan_orders,
        inventory_counts=inventory_file_types(root),
        json_errors=sorted(set(errors)),
    )


def stable_scalar(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.10g}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(stable_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def unique_values(records: Iterable[ImageRecord], field_name: str) -> list[Any]:
    values: dict[str, Any] = {}
    for record in records:
        value = record.metadata.get(field_name)
        if value is None or value == "":
            continue
        values[stable_scalar(value)] = value
    return [values[key] for key in sorted(values)]


def joined_values(records: Iterable[ImageRecord], field_name: str) -> str:
    return "; ".join(stable_scalar(value) for value in unique_values(records, field_name))


def shorten_sources(sources: Iterable[str], limit: int = 40) -> str:
    values = sorted(set(source for source in sources if source))
    if len(values) <= limit:
        return "; ".join(values)
    return "; ".join(values[:limit]) + f"; ... (+{len(values) - limit} more)"


def record_sources(records: Iterable[ImageRecord], limit: int = 12) -> tuple[str, ...]:
    values = []
    for record in records:
        values.append(f"{record.dataset}:{record.relpath}")
        values.extend(
            f"{record.dataset}:{source}" for source in record.metadata_sources
        )
    unique = sorted(set(values))
    return tuple(unique[:limit])


def orientation_summary(record: ImageRecord) -> str:
    if record.axis_codes:
        return "NIfTI axes " + "".join(record.axis_codes)
    text = record.metadata.get("ImageOrientationText")
    if text:
        return stable_scalar(text)
    values = record.metadata.get("ImageOrientationPatientDICOM")
    if not isinstance(values, list) or len(values) != 6:
        return ""
    try:
        r1 = tuple(float(value) for value in values[:3])
        r2 = tuple(float(value) for value in values[3:])
    except (TypeError, ValueError):
        return stable_scalar(values)
    normal = (
        r1[1] * r2[2] - r1[2] * r2[1],
        r1[2] * r2[0] - r1[0] * r2[2],
        r1[0] * r2[1] - r1[1] * r2[0],
    )
    axis = max(range(3), key=lambda index: abs(normal[index]))
    labels = ("approximately sagittal", "approximately coronal", "approximately axial")
    return f"{labels[axis]} (DICOM orientation)"


def shortest_repeated_block(values: Sequence[float]) -> int:
    for period in range(1, len(values) + 1):
        if len(values) % period:
            continue
        block = values[:period]
        if all(
            math.isclose(values[index], block[index % period], abs_tol=1e-7)
            for index in range(len(values))
        ):
            return period
    return len(values)


def monotonic_direction(values: Sequence[float]) -> str:
    if len(values) < 2:
        return "undetermined"
    nondecreasing = all(a <= b + 1e-7 for a, b in zip(values, values[1:]))
    nonincreasing = all(a + 1e-7 >= b for a, b in zip(values, values[1:]))
    if nondecreasing and not nonincreasing:
        return "ascending"
    if nonincreasing and not nondecreasing:
        return "descending"
    if nonincreasing and nondecreasing:
        return "simultaneous"
    return "interleaved or non-monotonic"


def slice_timing_details(record: ImageRecord) -> tuple[str, str]:
    raw = record.metadata.get("SliceTiming")
    if not isinstance(raw, list) or not raw:
        return "", ""
    try:
        values = [float(value) for value in raw]
    except (TypeError, ValueError):
        return f"n={len(raw)}; non-numeric values", "undetermined"
    period = shortest_repeated_block(values)
    repeats = len(values) // period
    block = values[:period]
    direction = monotonic_direction(block)
    summary = (
        f"n={len(values)}; range={min(values):.10g}..{max(values):.10g} s; "
        f"unique={len(set(values))}; {direction}"
    )
    if repeats > 1:
        summary += f" block repeated x{repeats}"
    inferred = f"{direction} slice-index timing"
    if repeats > 1:
        inferred += f" (multiband pattern x{repeats})"
    if not record.axis_codes:
        inferred += "; physical direction not verified from a NIfTI affine"
    return summary, inferred


def tuple3(values: tuple[Any, ...] | None) -> tuple[Any, ...] | None:
    if not values or len(values) < 3:
        return None
    return tuple(values[:3])


def unit_for_records(
    dataset: DatasetAudit,
    acquisition_label: str,
    task: str,
    records: list[ImageRecord],
    sbrefs: list[ImageRecord],
    kind: str,
) -> dict[str, Any]:
    participants = sorted({record.participant for record in records if record.participant})
    echo_numbers = sorted({record.echo for record in records if record.echo})
    echo_times = sorted(
        {
            float(record.metadata["EchoTime"])
            for record in records
            if isinstance(record.metadata.get("EchoTime"), (int, float))
        }
    )
    observed_echo_count = len(echo_numbers) or len(echo_times)
    nominal_match = re.search(r"me(\d+)", acquisition_label)
    nominal_echo_count = nominal_match.group(1) if nominal_match else ""
    shape_values = sorted({tuple3(record.shape) for record in records if tuple3(record.shape)})
    zoom_values = sorted(
        {
            tuple(round(value, 8) for value in tuple3(record.zooms) or ())
            for record in records
            if tuple3(record.zooms)
        }
    )
    orientations = sorted(
        {orientation_summary(record) for record in records if orientation_summary(record)}
    )
    slice_summaries: set[str] = set()
    slice_orders: set[str] = set()
    timing_counts: set[int] = set()
    for record in records:
        summary, order = slice_timing_details(record)
        if summary:
            slice_summaries.add(summary)
        if order:
            slice_orders.add(order)
        timing = record.metadata.get("SliceTiming")
        if isinstance(timing, list):
            timing_counts.add(len(timing))
    header_slice_counts = sorted(
        {record.shape[2] for record in records if record.shape and len(record.shape) >= 3}
    )
    notes: list[str] = []
    unavailable = Counter(record.image_status for record in records)
    for status, _count in sorted(unavailable.items()):
        if status != "available":
            notes.append(f"image entries include status: {status}")
    if kind == "bold":
        phase_count = sum(
            1
            for candidate in dataset.records_for("bold")
            if candidate.acquisition == acquisition_label
            and candidate.task == task
            and candidate.part.lower() == "phase"
            and candidate.participant in participants
        )
        if phase_count:
            notes.append("phase BOLD sidecars excluded from bold_file_count")
        if acquisition_label.startswith("mb1") and not unique_values(
            records, "MultibandAccelerationFactor"
        ):
            notes.append(
                "MultibandAccelerationFactor is absent; the acquisition label alone is not direct confirmation of factor 1"
            )
    if len(shape_values) > 1:
        notes.append("multiple NIfTI matrix dimensions")
    if len(zoom_values) > 1:
        notes.append("multiple NIfTI voxel-dimension sets")
    if len(timing_counts) > 1:
        notes.append("multiple SliceTiming lengths")
    if dataset.json_errors:
        notes.append(f"{len(dataset.json_errors)} JSON read errors in dataset")

    source_files = []
    for record in records + sbrefs:
        source_files.append(record.relpath)
        source_files.extend(record.metadata_sources)
        if record.nifti_path is not None:
            source_files.append(relative_source(dataset.spec.root, record.nifti_path))

    if header_slice_counts:
        slice_count_text = "; ".join(str(value) for value in header_slice_counts)
    elif timing_counts:
        slice_count_text = "; ".join(
            f"{value} (SliceTiming; header unavailable)" for value in sorted(timing_counts)
        )
    else:
        slice_count_text = ""

    return {
        "dataset_source": dataset.spec.label,
        "acquisition_label": acquisition_label,
        "task": task,
        "participant_count": len(participants),
        "bold_file_count": len(records) if kind == "bold" else 0,
        "nominal_echo_count": nominal_echo_count,
        "observed_echo_count": observed_echo_count,
        "echo_times_s": "; ".join(stable_scalar(value) for value in echo_times),
        "repetition_time_s": joined_values(records, "RepetitionTime"),
        "multiband_acceleration_factor": joined_values(
            records, "MultibandAccelerationFactor"
        ),
        "in_plane_acceleration": joined_values(
            records, "ParallelReductionFactorInPlane"
        ),
        "flip_angle_deg": joined_values(records, "FlipAngle"),
        "scanning_sequence": joined_values(records, "ScanningSequence"),
        "pulse_sequence_details": joined_values(records, "PulseSequenceDetails"),
        "phase_encoding_direction": joined_values(records, "PhaseEncodingDirection"),
        "image_orientation": "; ".join(orientations),
        "inferred_slice_order": "; ".join(sorted(slice_orders)),
        "slice_timing_summary": "; ".join(sorted(slice_summaries)),
        "number_of_slices": slice_count_text,
        "nifti_matrix_dimensions": "; ".join(stable_scalar(value) for value in shape_values),
        "nifti_voxel_dimensions_mm": "; ".join(
            stable_scalar(value) for value in zoom_values
        ),
        "base_resolution": joined_values(records, "BaseResolution"),
        "acquisition_matrix_pe": joined_values(records, "AcquisitionMatrixPE"),
        "recon_matrix_pe": joined_values(records, "ReconMatrixPE"),
        "slice_thickness_mm": joined_values(records, "SliceThickness"),
        "spacing_between_slices_mm": joined_values(records, "SpacingBetweenSlices"),
        "partial_fourier": joined_values(records, "PartialFourier"),
        "receive_coil_name": joined_values(records, "ReceiveCoilName"),
        "sbref_count": len(sbrefs),
        "source_files": shorten_sources(source_files),
        "exceptions_and_notes": "; ".join(notes),
    }


def parameter_signature(row: dict[str, Any]) -> tuple[str, ...]:
    excluded = {
        "dataset_source",
        "participant_count",
        "bold_file_count",
        "sbref_count",
        "source_files",
        "exceptions_and_notes",
    }
    return tuple(str(row[column]) for column in ACQUISITION_COLUMNS if column not in excluded)


def build_parameter_rows(dataset: DatasetAudit) -> list[dict[str, Any]]:
    if not dataset.available:
        return []
    preliminary: list[dict[str, Any]] = []

    bold_groups: dict[tuple[str, str, str], list[ImageRecord]] = defaultdict(list)
    for record in dataset.main_bold():
        key = (record.participant, record.task, record.acquisition or "unlabeled_bold")
        bold_groups[key].append(record)
    sbref_groups: dict[tuple[str, str, str], list[ImageRecord]] = defaultdict(list)
    for record in dataset.main_sbref():
        key = (record.participant, record.task, record.acquisition or "unlabeled_bold")
        sbref_groups[key].append(record)
    for key in sorted(bold_groups):
        participant, task, acquisition = key
        preliminary.append(
            unit_for_records(
                dataset,
                acquisition,
                task,
                bold_groups[key],
                sbref_groups.get((participant, task, acquisition), []),
                "bold",
            )
        )

    for suffix, label in (("T1w", "T1w"),):
        for record in dataset.records_for(suffix):
            preliminary.append(
                unit_for_records(dataset, label, "", [record], [], "structural")
            )

    fmap_groups: dict[tuple[str, str], list[ImageRecord]] = defaultdict(list)
    for record in dataset.records_for("magnitude1", "magnitude2", "phasediff", "fieldmap"):
        run = record.entities.get("run", "unlabeled")
        acquisition = record.acquisition or "unlabeled"
        fmap_groups[(record.participant, f"fmap-{acquisition}-run-{run}")].append(record)
    for (_, label), records in sorted(fmap_groups.items()):
        preliminary.append(unit_for_records(dataset, label, "", records, [], "fieldmap"))

    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in preliminary:
        grouped[parameter_signature(row)].append(row)

    combined: list[dict[str, Any]] = []
    for signature in sorted(grouped):
        rows = grouped[signature]
        base = dict(rows[0])
        base["participant_count"] = sum(int(row["participant_count"]) for row in rows)
        base["bold_file_count"] = sum(int(row["bold_file_count"]) for row in rows)
        base["sbref_count"] = sum(int(row["sbref_count"]) for row in rows)
        base["source_files"] = shorten_sources(
            source
            for row in rows
            for source in str(row["source_files"]).split("; ")
        )
        base["exceptions_and_notes"] = "; ".join(
            sorted(
                {
                    note
                    for row in rows
                    for note in str(row["exceptions_and_notes"]).split("; ")
                    if note
                }
            )
        )
        combined.append(base)
    return sorted(
        combined,
        key=lambda row: (
            str(row["dataset_source"]),
            str(row["acquisition_label"]),
            str(row["task"]),
            parameter_signature(row),
        ),
    )


def values_text(values: Iterable[Any]) -> str:
    keyed = {stable_scalar(value): value for value in values if value is not None and value != ""}
    return "; ".join(stable_scalar(keyed[key]) for key in sorted(keyed))


def coverage_text(dataset: DatasetAudit, records: Sequence[ImageRecord]) -> str:
    participants = {record.participant for record in records if record.participant}
    total = len(dataset.participants)
    return f"{len(participants)}/{total} participants; {len(records)} sidecars"


def unavailable_evaluation(dataset: DatasetAudit | None) -> Evaluation | None:
    if dataset is None:
        return Evaluation(
            "DATA_SOURCE_UNAVAILABLE",
            "",
            "0 participants audited",
            "No dataset with the requested evidence role was supplied.",
        )
    if not dataset.available:
        return Evaluation(
            "DATA_SOURCE_UNAVAILABLE",
            "",
            "0 participants audited",
            dataset.access_note,
        )
    return None


def near(value: Any, expected: float, tolerance: float = 1e-6) -> bool:
    return isinstance(value, (int, float)) and math.isclose(
        float(value), expected, rel_tol=0, abs_tol=tolerance
    )


def evaluate_numeric(
    dataset: DatasetAudit,
    suffixes: tuple[str, ...],
    field_name: str,
    expected: float,
    correction: str = "",
) -> Evaluation:
    records = dataset.records_for(*suffixes)
    if not records:
        return Evaluation(
            "NOT_REPRESENTED_IN_DATASET",
            "",
            f"0/{len(dataset.participants)} participants",
            f"No {', '.join(suffixes)} sidecars are represented.",
            correction,
        )
    present = [record for record in records if record.metadata.get(field_name) is not None]
    values = unique_values(present, field_name)
    if not present:
        return Evaluation(
            "NOT_VERIFIABLE_FROM_METADATA",
            f"{field_name} absent",
            coverage_text(dataset, records),
            f"{field_name} is absent from represented sidecars.",
            correction,
            record_sources(records),
        )
    matches = [near(record.metadata.get(field_name), expected) for record in present]
    if all(matches) and len(present) == len(records):
        status = "SUPPORTED"
        reasoning = f"All represented sidecars report the expected {field_name}."
    elif any(matches):
        status = "PARTIALLY_SUPPORTED"
        reasoning = f"The expected {field_name} is reported for only part of the represented data."
    else:
        status = "CONTRADICTED"
        reasoning = f"Represented {field_name} values do not match the expected value."
    return Evaluation(
        status,
        values_text(values),
        coverage_text(dataset, records),
        reasoning,
        correction,
        record_sources(records),
    )


def metadata_participants(records: Iterable[ImageRecord], field_name: str) -> set[str]:
    return {
        record.participant
        for record in records
        if record.participant and record.metadata.get(field_name) not in (None, "")
    }


def coil_kind(value: Any) -> str:
    text = str(value or "").lower().replace("-", "").replace("_", "")
    if "64" in text:
        return "64ch"
    if "20" in text:
        return "20ch"
    return str(value or "unknown")


def logical_bold_units(dataset: DatasetAudit) -> dict[tuple[str, str], list[ImageRecord]]:
    units: dict[tuple[str, str], list[ImageRecord]] = defaultdict(list)
    for record in dataset.main_bold():
        units[(record.participant, record.acquisition)].append(record)
    return dict(units)


def gap_values(records: Iterable[ImageRecord]) -> list[float]:
    values = []
    for record in records:
        thickness = record.metadata.get("SliceThickness")
        spacing = record.metadata.get("SpacingBetweenSlices")
        if not isinstance(thickness, (int, float)) or not isinstance(spacing, (int, float)):
            continue
        if float(thickness) == 0:
            continue
        values.append((float(spacing) - float(thickness)) / float(thickness) * 100)
    return values


def evaluate_claim(
    claim_id: str,
    dataset: DatasetAudit | None,
    counterbalance_orders: tuple[tuple[str, ...], ...],
    counterbalance_source: str,
) -> Evaluation:
    missing = unavailable_evaluation(dataset)
    if missing is not None and claim_id != "latin_square_defined":
        return missing
    if claim_id == "latin_square_defined":
        if counterbalance_orders:
            rotations = {
                tuple(counterbalance_orders[0][offset:] + counterbalance_orders[0][:offset])
                for offset in range(len(counterbalance_orders[0]))
            }
            observed = set(counterbalance_orders)
            status = "SUPPORTED" if len(observed) == 6 and observed == rotations else "PARTIALLY_SUPPORTED"
            return Evaluation(
                status,
                f"{len(observed)} distinct six-condition orders",
                "repository order-definition source",
                "Six cyclic rotations are defined." if status == "SUPPORTED" else "Order definitions were found but do not form all six cyclic rotations.",
                "",
                (counterbalance_source,) if counterbalance_source else (),
            )
        return Evaluation(
            "NOT_VERIFIABLE_FROM_METADATA",
            "no parsed order definitions",
            "no order-definition source",
            "BIDS imaging metadata does not itself define the counterbalancing scheme.",
            "Provide --counterbalance-file to audit the documented order definitions.",
        )
    assert dataset is not None

    bold = dataset.main_bold()
    t1 = dataset.records_for("T1w")
    fmap = dataset.records_for("magnitude1", "magnitude2", "phasediff", "fieldmap")
    all_imaging = dataset.records
    bold_units = logical_bold_units(dataset)

    if claim_id == "facility_tubric":
        values = unique_values(all_imaging, "InstitutionName")
        if not all_imaging:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No imaging sidecars are represented.")
        return Evaluation(
            "NOT_VERIFIABLE_FROM_METADATA",
            values_text(values),
            coverage_text(dataset, all_imaging),
            "Institution metadata names a Temple University site but does not explicitly identify TUBRIC.",
            "Use the exact site name recorded by an authoritative facility or protocol source.",
            record_sources(all_imaging),
        )
    if claim_id == "scanner_3t":
        return evaluate_numeric(dataset, tuple(IMAGE_SUFFIXES), "MagneticFieldStrength", 3)
    if claim_id in {"scanner_siemens", "scanner_prisma"}:
        field_name, expected = (
            ("Manufacturer", "siemens")
            if claim_id == "scanner_siemens"
            else ("ManufacturersModelName", "prisma")
        )
        records = all_imaging
        values = unique_values(records, field_name)
        present = [record for record in records if record.metadata.get(field_name)]
        matches = [str(record.metadata[field_name]).lower() == expected for record in present]
        if not records:
            status = "NOT_REPRESENTED_IN_DATASET"
        elif present and all(matches) and len(present) == len(records):
            status = "SUPPORTED"
        elif any(matches):
            status = "PARTIALLY_SUPPORTED"
        elif present:
            status = "CONTRADICTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(
            status,
            values_text(values),
            coverage_text(dataset, records),
            f"Evaluated {field_name} across represented imaging sidecars.",
            "",
            record_sources(records),
        )
    if claim_id == "functional_bold":
        status = "SUPPORTED" if bold else "NOT_REPRESENTED_IN_DATASET"
        return Evaluation(
            status,
            f"{len(bold_units)} participant-acquisition units; {len(bold)} magnitude/no-part BOLD sidecars",
            coverage_text(dataset, bold),
            "BIDS suffix and datatype identify the represented files as BOLD." if bold else "No BOLD sidecars are represented.",
            "",
            record_sources(bold),
        )
    if claim_id == "functional_epi":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        sequences = unique_values(bold, "ScanningSequence")
        present = [record for record in bold if record.metadata.get("ScanningSequence")]
        matches = ["EP" in str(record.metadata.get("ScanningSequence", "")).split("\\") for record in present]
        status = "SUPPORTED" if present and all(matches) and len(present) == len(bold) else "PARTIALLY_SUPPORTED" if any(matches) else "CONTRADICTED"
        return Evaluation(status, values_text(sequences), coverage_text(dataset, bold), "ScanningSequence was evaluated for the EP code.", "", record_sources(bold))
    if claim_id == "functional_t2star_weighting":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        return Evaluation(
            "PARTIALLY_SUPPORTED",
            f"BIDS bold; ScanningSequence={joined_values(bold, 'ScanningSequence')}; EchoTime={joined_values(bold, 'EchoTime')} s",
            coverage_text(dataset, bold),
            "T2* weighting is inferred from BOLD/EPI labeling and echo times; an explicit weighting field is absent.",
            "Describe T2* weighting as an inference from BOLD EPI metadata unless an authoritative sequence source states it explicitly.",
            record_sources(bold),
        )
    if claim_id == "functional_axial_orientation":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        orientations = sorted({orientation_summary(record) for record in bold if orientation_summary(record)})
        axial = [value for value in orientations if "axial" in value.lower() or "tra" in value.lower()]
        status = "SUPPORTED" if orientations and len(axial) == len(orientations) else "PARTIALLY_SUPPORTED" if axial else "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, "; ".join(orientations), coverage_text(dataset, bold), "Orientation uses NIfTI axes when available and DICOM orientation metadata otherwise.", "", record_sources(bold))
    if claim_id == "functional_descending_slice_order":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        details = [slice_timing_details(record)[1] for record in bold]
        details = [value for value in details if value]
        descending = [value for value in details if value.startswith("descending")]
        if details and len(descending) == len(details):
            status = "SUPPORTED" if all(record.axis_codes for record in bold) else "PARTIALLY_SUPPORTED"
        elif descending:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(
            status,
            "; ".join(sorted(set(details))),
            coverage_text(dataset, bold),
            "SliceTiming supports slice-index ordering; physical direction also requires a defensible index-to-space mapping.",
            "Qualify the direction when NIfTI affines are unavailable.",
            record_sources(bold),
        )
    if claim_id == "six_principal_acquisitions":
        represented = sorted({record.acquisition for record in bold if record.acquisition in PRINCIPAL_ACQUISITIONS})
        coverage = {acq: len({record.participant for record in bold if record.acquisition == acq}) for acq in PRINCIPAL_ACQUISITIONS}
        if set(represented) == set(PRINCIPAL_ACQUISITIONS):
            status = "SUPPORTED" if all(value == len(dataset.participants) for value in coverage.values()) else "PARTIALLY_SUPPORTED"
        elif represented:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_REPRESENTED_IN_DATASET"
        return Evaluation(
            status,
            "; ".join(f"{key}={coverage[key]} participants" for key in PRINCIPAL_ACQUISITIONS),
            f"{len(represented)}/6 labels; {len(dataset.participants)} total participants",
            "All six labels are present but participant coverage is evaluated separately." if len(represented) == 6 else "Not all six labels are represented.",
            "Report condition-specific participant coverage.",
            record_sources(bold),
        )
    if claim_id == "multiband_factors_1_3_6":
        values = unique_values(bold, "MultibandAccelerationFactor")
        observed = {int(value) for value in values if isinstance(value, (int, float))}
        mb1_records = [record for record in bold if record.acquisition.startswith("mb1")]
        mb1_reported = [record for record in mb1_records if record.metadata.get("MultibandAccelerationFactor") is not None]
        if {1, 3, 6}.issubset(observed):
            status = "SUPPORTED"
        elif {3, 6}.issubset(observed) and mb1_records and not mb1_reported:
            status = "PARTIALLY_SUPPORTED"
        elif observed:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA" if bold else "NOT_REPRESENTED_IN_DATASET"
        return Evaluation(
            status,
            f"reported factors={values_text(values)}; MB1-labeled sidecars with explicit factor={len(mb1_reported)}/{len(mb1_records)}",
            coverage_text(dataset, bold),
            "An MB1 label with a missing field supports only an inference, not direct confirmation.",
            "State that factors 3 and 6 are explicit and factor 1 is inferred when its field is absent.",
            record_sources(bold),
        )
    if claim_id == "echo_counts_1_and_4":
        by_unit = {}
        for key, records in bold_units.items():
            echoes = {record.echo for record in records if record.echo}
            times = {record.metadata.get("EchoTime") for record in records if record.metadata.get("EchoTime") is not None}
            by_unit[key] = len(echoes) or len(times)
        counts = sorted(set(by_unit.values()))
        status = "SUPPORTED" if 1 in counts and 4 in counts else "PARTIALLY_SUPPORTED" if counts else "NOT_REPRESENTED_IN_DATASET"
        return Evaluation(status, "observed echo counts=" + ", ".join(map(str, counts)), f"{len(by_unit)} participant-acquisition units", "Echo entities and distinct EchoTime values were grouped within participant and acquisition.", "", record_sources(bold))
    if claim_id == "functional_flip_angle_20":
        return evaluate_numeric(dataset, ("bold",), "FlipAngle", 20)
    if claim_id == "functional_resolution_identical":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        header_zooms = {tuple(round(value, 6) for value in tuple3(record.zooms) or ()) for record in bold if tuple3(record.zooms)}
        thickness = unique_values(bold, "SliceThickness")
        spacing = unique_values(bold, "SpacingBetweenSlices")
        timing_lengths = sorted({len(record.metadata["SliceTiming"]) for record in bold if isinstance(record.metadata.get("SliceTiming"), list)})
        if len(header_zooms) == 1 and len([record for record in bold if tuple3(record.zooms)]) == len(bold):
            status = "SUPPORTED"
            reason = "All available NIfTI headers report one voxel-dimension set; slice counts concern coverage, not voxel size."
        elif len(thickness) == 1 and len(spacing) == 1:
            status = "PARTIALLY_SUPPORTED"
            reason = "Sidecar thickness and spacing are consistent, but complete NIfTI voxel dimensions are unavailable."
        else:
            status = "CONTRADICTED"
            reason = "Represented spatial-sampling fields differ."
        return Evaluation(
            status,
            f"NIfTI voxel dimensions={values_text(header_zooms)}; SliceThickness={values_text(thickness)}; SpacingBetweenSlices={values_text(spacing)}; SliceTiming lengths={values_text(timing_lengths)}",
            coverage_text(dataset, bold),
            reason,
            "Distinguish voxel dimensions from matrix size, slice count, and anatomical coverage.",
            record_sources(bold),
        )
    if claim_id == "functional_voxel_dimensions_2p7":
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        header_zooms = [tuple3(record.zooms) for record in bold if tuple3(record.zooms)]
        gaps = gap_values(bold)
        header_all = len(header_zooms) == len(bold)
        iso = header_zooms and all(all(math.isclose(float(value), 2.7, abs_tol=1e-4) for value in zoom) for zoom in header_zooms)
        nonzero_gap = gaps and any(not math.isclose(value, 0, abs_tol=1e-4) for value in gaps)
        if header_all and iso and not nonzero_gap:
            status = "SUPPORTED"
        elif nonzero_gap or (header_zooms and not iso):
            status = "CONTRADICTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(
            status,
            f"NIfTI voxel dimensions={values_text(header_zooms)}; SliceThickness={joined_values(bold, 'SliceThickness')} mm; SpacingBetweenSlices={joined_values(bold, 'SpacingBetweenSlices')} mm; implied gap={values_text(round(value, 6) for value in gaps)}%",
            coverage_text(dataset, bold),
            "Nonzero through-plane spacing relative to slice thickness is incompatible with isotropic sampling as stated.",
            "Report NIfTI voxel dimensions when available; otherwise report slice thickness and spacing separately.",
            record_sources(bold),
        )
    if claim_id in {"whole_brain_coverage", "ventral_cerebellum_coverage"}:
        if not bold:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No BOLD sidecars are represented.")
        return Evaluation(
            "NOT_VERIFIABLE_FROM_METADATA",
            f"SliceTiming lengths={values_text(sorted({len(record.metadata['SliceTiming']) for record in bold if isinstance(record.metadata.get('SliceTiming'), list)}))}",
            coverage_text(dataset, bold),
            "File inventories, slice counts, and orientation do not establish anatomical coverage.",
            "Verify coverage by inspecting image geometry relative to anatomy.",
            record_sources(bold),
        )
    if claim_id == "sbref_each_acquisition":
        sbref_units = {(record.participant, record.acquisition) for record in dataset.main_sbref()}
        principal_units = {key for key in bold_units if key[1] in PRINCIPAL_ACQUISITIONS}
        missing_units = sorted(principal_units - sbref_units)
        if principal_units and not missing_units:
            status = "SUPPORTED"
        elif sbref_units:
            status = "CONTRADICTED"
        else:
            status = "CONTRADICTED" if principal_units else "NOT_REPRESENTED_IN_DATASET"
        counts = Counter(record.acquisition for record in dataset.main_sbref())
        return Evaluation(
            status,
            "; ".join(f"{acq}={counts.get(acq, 0)} magnitude/no-part SBRef sidecars" for acq in PRINCIPAL_ACQUISITIONS),
            f"{len(principal_units) - len(missing_units)}/{len(principal_units)} participant-acquisition units have SBRef metadata",
            f"SBRef metadata is absent for {len(missing_units)} represented participant-acquisition units.",
            "Report SBRef availability by acquisition rather than asserting universal availability.",
            record_sources(dataset.main_sbref()),
        )
    if claim_id == "t1_tr_2p4":
        return evaluate_numeric(dataset, ("T1w",), "RepetitionTime", 2.4)
    if claim_id == "t1_te_2p17ms":
        return evaluate_numeric(dataset, ("T1w",), "EchoTime", 0.00217)
    if claim_id == "t1_flip_angle_8":
        return evaluate_numeric(dataset, ("T1w",), "FlipAngle", 8)
    if claim_id == "t1_matrix_224":
        if not t1:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No T1w sidecars are represented.")
        shapes = [tuple3(record.shape) for record in t1 if tuple3(record.shape)]
        json_values = {field: joined_values(t1, field) for field in ("AcquisitionMatrixPE", "BaseResolution", "ReconMatrixPE")}
        if len(shapes) == len(t1):
            status = "SUPPORTED" if all(shape[0] == 224 and shape[1] == 224 for shape in shapes) else "CONTRADICTED"
            reason = "NIfTI header matrix dimensions were evaluated."
        elif all(value == "224" for value in json_values.values()):
            status = "PARTIALLY_SUPPORTED"
            reason = "Three JSON matrix fields report 224, but NIfTI headers are unavailable."
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
            reason = "NIfTI headers are unavailable and JSON matrix fields are incomplete."
        return Evaluation(status, f"NIfTI shapes={values_text(shapes)}; " + "; ".join(f"{key}={value}" for key, value in json_values.items()), coverage_text(dataset, t1), reason, "Do not equate acquisition, base, reconstruction, and NIfTI matrices.", record_sources(t1))
    if claim_id == "t1_voxel_dimensions_1mm":
        if not t1:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No T1w sidecars are represented.")
        zooms = [tuple3(record.zooms) for record in t1 if tuple3(record.zooms)]
        if len(zooms) == len(t1):
            status = "SUPPORTED" if all(all(math.isclose(float(value), 1, abs_tol=1e-4) for value in zoom) for zoom in zooms) else "CONTRADICTED"
        elif all(near(record.metadata.get("SliceThickness"), 1) for record in t1):
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"NIfTI voxel dimensions={values_text(zooms)}; SliceThickness={joined_values(t1, 'SliceThickness')} mm", coverage_text(dataset, t1), "Slice thickness alone does not establish three-dimensional isotropy.", "Use NIfTI header voxel dimensions for the isotropic-voxel statement.", record_sources(t1))
    if claim_id == "t1_slices_224":
        if not t1:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No T1w sidecars are represented.")
        slices = [record.shape[2] for record in t1 if record.shape and len(record.shape) >= 3]
        if len(slices) == len(t1):
            status = "SUPPORTED" if all(value == 224 for value in slices) else "CONTRADICTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, "NIfTI slice counts=" + values_text(slices), coverage_text(dataset, t1), "Slice count is taken from NIfTI headers; no substitute field is used.", "Verify after image content is available.", record_sources(t1))
    if claim_id == "fieldmap_present":
        if not fmap:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No field-map sidecars are represented.")
        scanning = joined_values(fmap, "ScanningSequence")
        details = joined_values(fmap, "PulseSequenceDetails")
        gre = any("GR" in str(value).split("\\") for value in unique_values(fmap, "ScanningSequence")) or "gre" in details.lower()
        return Evaluation("SUPPORTED" if gre else "PARTIALLY_SUPPORTED", f"{len(fmap)} sidecars; ScanningSequence={scanning}; PulseSequenceDetails={details}", coverage_text(dataset, fmap), "Field-map suffixes and GRE-related sequence metadata were evaluated.", "", record_sources(fmap))
    if claim_id == "fieldmap_tr_645ms":
        return evaluate_numeric(dataset, ("magnitude1", "magnitude2", "phasediff", "fieldmap"), "RepetitionTime", 0.645)
    if claim_id == "fieldmap_te1_4p92ms":
        records = dataset.records_for("magnitude1", "phasediff")
        if not records:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No first-echo field-map metadata are represented.")
        values = []
        matches = []
        for record in records:
            value = record.metadata.get("EchoTime1", record.metadata.get("EchoTime"))
            if value is not None:
                values.append(value)
                matches.append(near(value, 0.00492))
        status = "SUPPORTED" if matches and all(matches) else "PARTIALLY_SUPPORTED" if any(matches) else "CONTRADICTED" if matches else "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, values_text(values), coverage_text(dataset, records), "EchoTime1 is preferred when present; magnitude1 EchoTime is used otherwise.", "", record_sources(records))
    if claim_id == "fieldmap_te2_7p38ms":
        records = dataset.records_for("magnitude2", "phasediff")
        if not records:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No second-echo field-map metadata are represented.")
        values = []
        matches = []
        for record in records:
            value = record.metadata.get("EchoTime2", record.metadata.get("EchoTime"))
            if value is not None:
                values.append(value)
                matches.append(near(value, 0.00738))
        status = "SUPPORTED" if matches and all(matches) else "PARTIALLY_SUPPORTED" if any(matches) else "CONTRADICTED" if matches else "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, values_text(values), coverage_text(dataset, records), "EchoTime2 is preferred when present; magnitude2 EchoTime is used otherwise.", "", record_sources(records))
    if claim_id == "fieldmap_matrix_80":
        if not fmap:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No field-map sidecars are represented.")
        shapes = [tuple3(record.shape) for record in fmap if tuple3(record.shape)]
        fields = {field: joined_values(fmap, field) for field in ("AcquisitionMatrixPE", "BaseResolution", "ReconMatrixPE")}
        if len(shapes) == len(fmap):
            status = "SUPPORTED" if all(shape[0] == 80 and shape[1] == 80 for shape in shapes) else "CONTRADICTED"
        elif all(value == "80" for value in fields.values()):
            status = "PARTIALLY_SUPPORTED"
        elif all(value for value in fields.values()) and any(
            "80" in value.split("; ") for value in fields.values()
        ):
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"NIfTI shapes={values_text(shapes)}; " + "; ".join(f"{key}={value}" for key, value in fields.items()), coverage_text(dataset, fmap), "JSON matrix concepts are reported separately from NIfTI dimensions.", "State which matrix definition is intended.", record_sources(fmap))
    if claim_id == "fieldmap_voxel_dimensions_2p7":
        if not fmap:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No field-map sidecars are represented.")
        zooms = [tuple3(record.zooms) for record in fmap if tuple3(record.zooms)]
        gaps = gap_values(fmap)
        iso = zooms and all(all(math.isclose(float(value), 2.7, abs_tol=1e-4) for value in zoom) for zoom in zooms)
        nonzero_gap = gaps and any(not math.isclose(value, 0, abs_tol=1e-4) for value in gaps)
        status = "SUPPORTED" if len(zooms) == len(fmap) and iso and not nonzero_gap else "CONTRADICTED" if nonzero_gap or (zooms and not iso) else "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"NIfTI voxel dimensions={values_text(zooms)}; SliceThickness={joined_values(fmap, 'SliceThickness')} mm; SpacingBetweenSlices={joined_values(fmap, 'SpacingBetweenSlices')} mm", coverage_text(dataset, fmap), "Through-plane spacing differs from slice thickness when a nonzero gap is present.", "Report slice thickness, spacing, and NIfTI voxel dimensions separately.", record_sources(fmap))
    if claim_id == "fieldmap_slices_54":
        if not fmap:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No field-map sidecars are represented.")
        slices = [record.shape[2] for record in fmap if record.shape and len(record.shape) >= 3]
        timings = [len(record.metadata["SliceTiming"]) for record in fmap if isinstance(record.metadata.get("SliceTiming"), list)]
        if len(slices) == len(fmap):
            status = "SUPPORTED" if all(value == 54 for value in slices) else "CONTRADICTED"
        elif timings and all(value == 54 for value in timings):
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"NIfTI slice counts={values_text(slices)}; SliceTiming lengths={values_text(timings)}", coverage_text(dataset, fmap), "SliceTiming length is corroborating evidence only; NIfTI headers are primary.", "Verify the slice count from NIfTI headers when content is available.", record_sources(fmap))
    if claim_id == "fieldmap_gap_10pct":
        if not fmap:
            return Evaluation("NOT_REPRESENTED_IN_DATASET", "", f"0/{len(dataset.participants)} participants", "No field-map sidecars are represented.")
        gaps = gap_values(fmap)
        if gaps and len(gaps) == len(fmap) and all(math.isclose(value, 10, abs_tol=1e-4) for value in gaps):
            status = "SUPPORTED"
        elif any(math.isclose(value, 10, abs_tol=1e-4) for value in gaps):
            status = "PARTIALLY_SUPPORTED"
        elif gaps:
            status = "CONTRADICTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"implied gap={values_text(round(value, 6) for value in gaps)}%", coverage_text(dataset, fmap), "Calculated as (SpacingBetweenSlices - SliceThickness) / SliceThickness x 100.", "", record_sources(fmap))
    if claim_id == "fieldmap_flip_angle_60":
        return evaluate_numeric(dataset, ("magnitude1", "magnitude2", "phasediff", "fieldmap"), "FlipAngle", 60)
    if claim_id in {"coil_64ch_present", "coil_20ch_present", "public_release_contains_both_coils"}:
        values = unique_values(all_imaging, "ReceiveCoilName")
        kinds = {coil_kind(value) for value in values}
        if claim_id == "coil_64ch_present":
            status = "SUPPORTED" if "64ch" in kinds else "NOT_REPRESENTED_IN_DATASET"
        elif claim_id == "coil_20ch_present":
            status = "SUPPORTED" if "20ch" in kinds else "NOT_REPRESENTED_IN_DATASET"
        else:
            status = "SUPPORTED" if {"64ch", "20ch"}.issubset(kinds) else "CONTRADICTED" if kinds else "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, values_text(values), coverage_text(dataset, all_imaging), "ReceiveCoilName is used as participant-level primary evidence.", "Do not infer an unrepresented coil group from subject-list files.", record_sources(all_imaging))
    if claim_id == "coil_assignment_complete":
        assigned = metadata_participants(all_imaging, "ReceiveCoilName")
        total = set(dataset.participants)
        missing_participants = sorted(total - assigned)
        status = "SUPPORTED" if total and not missing_participants else "PARTIALLY_SUPPORTED" if assigned else "NOT_VERIFIABLE_FROM_METADATA"
        distribution = Counter()
        for participant in sorted(assigned):
            participant_values = unique_values([record for record in all_imaging if record.participant == participant], "ReceiveCoilName")
            for value in participant_values:
                distribution[coil_kind(value)] += 1
        return Evaluation(status, "; ".join(f"{key}={value} participants" for key, value in sorted(distribution.items())), f"{len(assigned)}/{len(total)} participants assigned", f"Participants without metadata-based assignment: {', '.join(missing_participants) if missing_participants else 'none'}.", "Report unknown assignments explicitly.", record_sources(all_imaging))
    if claim_id == "coil_64ch_primary_sample":
        values = unique_values(all_imaging, "ReceiveCoilName")
        return Evaluation(
            "NOT_VERIFIABLE_FROM_METADATA" if all_imaging else "NOT_REPRESENTED_IN_DATASET",
            values_text(values),
            coverage_text(dataset, all_imaging),
            "Receive-coil metadata assigns acquisition hardware but does not define an analysis sample as primary.",
            "Support the primary-sample designation with an analysis cohort definition and report its metadata-based coil distribution.",
            record_sources(all_imaging),
        )
    if claim_id == "scan_order_reconstructable":
        orders = {participant: order for participant, order in dataset.scan_orders.items() if order}
        full = {participant: order for participant, order in orders.items() if len(order) == 6}
        if len(full) == len(dataset.participants) and dataset.participants:
            status = "SUPPORTED"
        elif orders:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        order_counts = Counter(" > ".join(order) for order in full.values())
        return Evaluation(status, "; ".join(f"{order} ({count})" for order, count in sorted(order_counts.items())), f"{len(orders)}/{len(dataset.participants)} participants with at least one ordered BOLD condition; {len(full)} complete six-condition orders", "Row order in scans.tsv reconstructs acquisition order without reporting acquisition timestamps.", "Do not treat incomplete scan lists as verified complete assignments.", tuple(f"{dataset.spec.label}:{source}" for source in dataset.scans_files[:40]))
    if claim_id == "six_acquisition_orders_observed":
        full_orders = [order for order in dataset.scan_orders.values() if len(order) == 6]
        observed = Counter(" > ".join(order) for order in full_orders)
        if len(observed) == 6:
            status = "SUPPORTED"
        elif observed:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(
            status,
            "; ".join(f"{order} ({count})" for order, count in sorted(observed.items())),
            f"{len(observed)}/6 distinct complete orders; {len(full_orders)}/{len(dataset.participants)} participants with complete orders",
            "Only complete six-condition scans.tsv orders are counted as observed orders.",
            "Distinguish an order scheme being defined from all orders being observed in participant data.",
            tuple(f"{dataset.spec.label}:{source}" for source in dataset.scans_files[:40]),
        )
    if claim_id == "latin_square_assignments_verified":
        if not counterbalance_orders:
            return Evaluation("NOT_VERIFIABLE_FROM_METADATA", "no parsed order definitions", f"{len(dataset.scan_orders)} scans.tsv files", "Participant orders cannot be compared without documented definitions.", "Provide --counterbalance-file.", tuple(f"{dataset.spec.label}:{source}" for source in dataset.scans_files[:40]))
        full = {participant: order for participant, order in dataset.scan_orders.items() if len(order) == 6}
        matches = {participant: order for participant, order in full.items() if order in counterbalance_orders}
        if dataset.participants and len(matches) == len(dataset.participants):
            status = "SUPPORTED"
        elif full and len(matches) == len(full):
            status = "PARTIALLY_SUPPORTED"
        elif matches:
            status = "PARTIALLY_SUPPORTED"
        elif full:
            status = "CONTRADICTED"
        else:
            status = "NOT_VERIFIABLE_FROM_METADATA"
        return Evaluation(status, f"{len(matches)}/{len(full)} complete orders match a definition", f"{len(full)}/{len(dataset.participants)} participants have a complete six-condition order", "Defined mappings establish the scheme; scans.tsv order is used to test represented assignments.", "Treat participants with incomplete scan inventories as unverified.", tuple([counterbalance_source] + [f"{dataset.spec.label}:{source}" for source in dataset.scans_files[:39]]))

    raise KeyError(f"Unhandled claim: {claim_id}")


def parse_counterbalance_file(path: Path | None) -> tuple[tuple[tuple[str, ...], ...], str]:
    if path is None:
        return (), ""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        return (), resolved.as_posix()
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return (), resolved.as_posix()
    orders = []
    pattern = re.compile(r"case\s+([1-6])\s*,\s*acqs\s*=\s*\{([^}]+)\}", re.IGNORECASE)
    for match in pattern.finditer(text):
        values = tuple(re.findall(r"['\"]([A-Za-z0-9]+)['\"]", match.group(2)))
        if len(values) == 6 and all(value in PRINCIPAL_ACQUISITIONS for value in values):
            orders.append((int(match.group(1)), values))
    sorted_orders = tuple(values for _, values in sorted(set(orders)))
    return sorted_orders, resolved.as_posix()


def choose_role(audits: Sequence[DatasetAudit], role: str) -> DatasetAudit | None:
    if role == "complete":
        terms = ("complete", "linux1", "full")
    else:
        terms = ("openneuro", "public", "ds005085")
    for audit in audits:
        lowered = audit.spec.label.lower()
        if any(term in lowered for term in terms):
            return audit
    return None


def combined_evidence(complete: Evaluation, public: Evaluation) -> str:
    return shorten_sources(complete.evidence + public.evidence, limit=60)


def combined_reasoning(complete: Evaluation, public: Evaluation) -> str:
    if complete.reasoning == public.reasoning:
        return complete.reasoning
    return f"Complete: {complete.reasoning} Public: {public.reasoning}"


def combined_correction(complete: Evaluation, public: Evaluation) -> str:
    values = sorted({value for value in (complete.correction, public.correction) if value})
    return " ".join(values)


def build_claim_rows(
    complete: DatasetAudit | None,
    public: DatasetAudit | None,
    orders: tuple[tuple[str, ...], ...],
    order_source: str,
) -> list[dict[str, str]]:
    rows = []
    for claim_id, proposition in CLAIMS:
        complete_eval = evaluate_claim(claim_id, complete, orders, order_source)
        public_eval = evaluate_claim(claim_id, public, orders, order_source)
        rows.append(
            {
                "claim_id": claim_id,
                "technical_proposition": proposition,
                "complete_dataset_status": complete_eval.status,
                "complete_dataset_observed_values": complete_eval.observed,
                "complete_dataset_coverage": complete_eval.coverage,
                "openneuro_status": public_eval.status,
                "openneuro_observed_values": public_eval.observed,
                "openneuro_coverage": public_eval.coverage,
                "evidence_files": combined_evidence(complete_eval, public_eval),
                "reasoning": combined_reasoning(complete_eval, public_eval),
                "suggested_technical_correction": (
                    combined_correction(complete_eval, public_eval)
                    or "No correction suggested."
                ),
            }
        )
    return rows


def acquisition_labels(dataset: DatasetAudit | None) -> list[str]:
    if dataset is None or not dataset.available:
        return []
    labels = {
        record.acquisition
        for record in dataset.records_for("bold")
        if record.acquisition
    }
    for order in dataset.scan_orders.values():
        labels.update(order)
    return sorted(labels)


def coil_distribution(dataset: DatasetAudit | None) -> str:
    if dataset is None or not dataset.available:
        return "DATA_SOURCE_UNAVAILABLE"
    participant_coils: dict[str, set[str]] = defaultdict(set)
    for record in dataset.records:
        value = record.metadata.get("ReceiveCoilName")
        if value and record.participant:
            participant_coils[record.participant].add(coil_kind(value))
    counts = Counter(
        "/".join(sorted(values)) if values else "unknown"
        for participant, values in sorted(participant_coils.items())
    )
    unknown = len(dataset.participants) - len(participant_coils)
    if unknown:
        counts["unknown"] += unknown
    return "; ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def distribution_for_comparison(dataset: DatasetAudit, suffix: str, field_name: str) -> set[str]:
    return {stable_scalar(value) for value in unique_values(dataset.records_for(suffix), field_name)}


def build_comparison_row(
    complete: DatasetAudit | None,
    public: DatasetAudit | None,
    supplemental: Sequence[DatasetAudit],
) -> dict[str, str]:
    complete_available = complete is not None and complete.available
    public_available = public is not None and public.available
    complete_participants = set(complete.participants) if complete_available else set()
    public_participants = set(public.participants) if public_available else set()
    complete_acqs = set(acquisition_labels(complete))
    public_acqs = set(acquisition_labels(public))
    fields_that_differ: list[str] = []
    sidecar_differences: list[str] = []
    if complete_available and public_available:
        for suffix in ("bold", "T1w", "magnitude1", "phasediff"):
            for field_name in PARAMETER_FIELDS:
                complete_values = distribution_for_comparison(complete, suffix, field_name)
                public_values = distribution_for_comparison(public, suffix, field_name)
                if complete_values != public_values:
                    fields_that_differ.append(f"{suffix}.{field_name}")
                    sidecar_differences.append(
                        f"{suffix}.{field_name}: complete={';'.join(sorted(complete_values)) or '<absent>'}, public={';'.join(sorted(public_values)) or '<absent>'}"
                    )
    supplemental_note = ""
    if not complete_available and public_available:
        local_sources = [audit for audit in supplemental if audit.available and audit is not public]
        for audit in local_sources:
            local_participants = set(audit.participants)
            if public_participants and public_participants.issubset(local_participants):
                supplemental_note = (
                    f"Public participant IDs are a subset of {audit.spec.label}'s participant table, "
                    "but equivalence to the unavailable complete imaging dataset is not established."
                )
                break
    if complete_available and public_available:
        subset = str(public_participants.issubset(complete_participants) and public_acqs.issubset(complete_acqs)).lower()
        interpretation = (
            "Public identifiers and acquisition labels form a subset of the complete source; "
            "listed metadata differences require source-level review."
            if subset == "true"
            else "The public source is not a simple identifier-and-acquisition subset."
        )
    else:
        subset = "not assessable"
        interpretation = supplemental_note or "Complete-versus-public comparison requires both sources."
    evidence = []
    for dataset in (complete, public):
        if dataset is not None and dataset.available:
            if (dataset.spec.root / "participants.tsv").is_file():
                evidence.append(f"{dataset.spec.label}:participants.tsv")
            evidence.extend(f"{dataset.spec.label}:{value}" for value in dataset.scans_files[:10])
    return {
        "complete_participant_ids": "; ".join(sorted(complete_participants)) if complete_available else "DATA_SOURCE_UNAVAILABLE",
        "openneuro_participant_ids": "; ".join(sorted(public_participants)) if public_available else "DATA_SOURCE_UNAVAILABLE",
        "complete_acquisition_labels": "; ".join(sorted(complete_acqs)) if complete_available else "DATA_SOURCE_UNAVAILABLE",
        "openneuro_acquisition_labels": "; ".join(sorted(public_acqs)) if public_available else "DATA_SOURCE_UNAVAILABLE",
        "complete_coil_distribution": coil_distribution(complete),
        "openneuro_coil_distribution": coil_distribution(public),
        "complete_bold_acquisition_count": str(len(logical_bold_units(complete))) if complete_available else "DATA_SOURCE_UNAVAILABLE",
        "openneuro_bold_acquisition_count": str(len(logical_bold_units(public))) if public_available else "DATA_SOURCE_UNAVAILABLE",
        "missing_participants_in_openneuro": "; ".join(sorted(complete_participants - public_participants)) if complete_available and public_available else "not assessable",
        "missing_acquisition_conditions_in_openneuro": "; ".join(sorted(complete_acqs - public_acqs)) if complete_available and public_available else "not assessable",
        "metadata_fields_that_differ": "; ".join(sorted(fields_that_differ)) if complete_available and public_available else "not assessable",
        "sidecar_values_that_differ": shorten_sources(sidecar_differences, limit=30) if complete_available and public_available else "not assessable",
        "openneuro_appears_subset": subset,
        "difference_interpretation": interpretation,
        "evidence_files": shorten_sources(evidence),
    }


def write_tsv(path: Path, columns: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: stable_scalar(row.get(column, "")) for column in columns})


def md_escape(value: Any) -> str:
    return stable_scalar(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(columns: Sequence[str], rows: Sequence[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No represented records."]
    output = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(md_escape(row.get(column, "")) for column in columns) + " |")
    return output


def compact_parameter_rows(
    rows: Sequence[dict[str, Any]],
    key_columns: Sequence[str],
) -> list[dict[str, Any]]:
    """Collapse detailed distinct-set rows for concise Markdown display."""
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(column, "")) for column in key_columns)].append(row)
    compact: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = grouped[key]
        output: dict[str, Any] = dict(zip(key_columns, key))
        for column in ACQUISITION_COLUMNS:
            if column in key_columns:
                continue
            if column in {"participant_count", "bold_file_count", "sbref_count"}:
                output[column] = sum(int(member.get(column, 0) or 0) for member in members)
                continue
            values = sorted(
                {
                    str(member.get(column, ""))
                    for member in members
                    if member.get(column, "") not in (None, "")
                }
            )
            output[column] = " | ".join(values)
        compact.append(output)
    return compact


def claim_lookup(rows: Sequence[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["claim_id"]: row for row in rows}


def status_summary(rows: Sequence[dict[str, str]], prefix: str) -> str:
    counts = Counter(row[f"{prefix}_status"] for row in rows)
    return ", ".join(f"{status}={counts[status]}" for status in sorted(counts))


def report_dataset_scope(dataset: DatasetAudit | None, role_name: str) -> list[str]:
    if dataset is None:
        return [f"No `{role_name}` source was supplied; this evidence role is unavailable."]
    if not dataset.available:
        return [f"`{dataset.spec.label}` was unavailable at `{dataset.spec.root}`."]
    bold_units = logical_bold_units(dataset)
    labels = acquisition_labels(dataset)
    pointer_count = dataset.inventory_counts.get("nifti_unavailable_pointers", 0)
    available_count = dataset.inventory_counts.get("nifti_available", 0)
    identity_parts = [
        stable_scalar(dataset.description.get(field_name))
        for field_name in ("Name", "DatasetDOI", "BIDSVersion")
        if dataset.description.get(field_name)
    ]
    identity = "; ".join(identity_parts) or "dataset identity not reported"
    return [
        f"Source `{dataset.spec.label}` ({identity}) at `{dataset.spec.root}` contains {len(dataset.participants)} participant identifiers, {len(bold_units)} participant-acquisition BOLD units, and acquisition labels: {', '.join(labels) or 'none'}.",
        f"The inventory contains {dataset.inventory_counts.get('json', 0)} JSON files, {dataset.inventory_counts.get('tsv', 0)} TSV files, {dataset.inventory_counts.get('nifti_entries', 0)} NIfTI entries, {available_count} locally available NIfTI files, and {pointer_count} unavailable pointer entries.",
    ]


def build_markdown_report(
    audits: Sequence[DatasetAudit],
    complete: DatasetAudit | None,
    public: DatasetAudit | None,
    parameter_rows: Sequence[dict[str, Any]],
    claim_rows: Sequence[dict[str, str]],
    comparison_row: dict[str, str],
    dataset_arguments: Sequence[str],
    output_dir: Path,
    order_source: str,
) -> str:
    claims = claim_lookup(claim_rows)
    lines: list[str] = ["# Acquisition metadata audit", ""]
    lines.extend(
        [
            "## 1. Executive summary",
            "",
            "This audit separates complete-dataset evidence from the public release and uses JSON/TSV metadata as primary evidence. NIfTI geometry is used only when image content is already available.",
            "",
            f"Complete-source statuses: {status_summary(claim_rows, 'complete_dataset')}.",
            "",
            f"Public-source statuses: {status_summary(claim_rows, 'openneuro')}.",
            "",
        ]
    )

    lines.extend(["## 2. Data sources and access", ""])
    source_rows = []
    for audit in audits:
        identity = audit.description.get("DatasetDOI") or audit.description.get("Name") or ""
        source_rows.append(
            {
                "label": audit.spec.label,
                "identity": identity,
                "root": audit.spec.root,
                "access": audit.access_note,
                "participants": len(audit.participants),
                "JSON": audit.inventory_counts.get("json", 0),
                "TSV": audit.inventory_counts.get("tsv", 0),
                "NIfTI available": audit.inventory_counts.get("nifti_available", 0),
                "NIfTI pointers/unavailable": audit.inventory_counts.get("nifti_unavailable_pointers", 0),
            }
        )
    lines.extend(markdown_table(("label", "identity", "root", "access", "participants", "JSON", "TSV", "NIfTI available", "NIfTI pointers/unavailable"), source_rows))
    lines.extend(["", "No imaging content was fetched by this program.", ""])

    lines.extend(["## 3. Scope of the complete Linux1 dataset", ""])
    lines.extend(report_dataset_scope(complete, "complete"))
    lines.append("")

    lines.extend(["## 4. Scope of the public OpenNeuro release", ""])
    lines.extend(report_dataset_scope(public, "openneuro"))
    lines.append("")

    lines.extend(["## 5. Functional acquisition parameters", ""])
    functional_rows = compact_parameter_rows(
        [
            row
            for row in parameter_rows
            if row["acquisition_label"] in PRINCIPAL_ACQUISITIONS
        ],
        ("dataset_source", "acquisition_label"),
    )
    lines.extend(
        markdown_table(
            (
                "dataset_source",
                "acquisition_label",
                "participant_count",
                "bold_file_count",
                "observed_echo_count",
                "echo_times_s",
                "repetition_time_s",
                "multiband_acceleration_factor",
                "flip_angle_deg",
                "number_of_slices",
                "nifti_voxel_dimensions_mm",
            ),
            functional_rows,
        )
    )
    lines.extend(["", "`bold_file_count` counts magnitude or no-part sidecars and excludes phase sidecars. Full parameter sets and source paths are in `acquisition_parameters.tsv`.", ""])

    lines.extend(["## 6. Structural acquisition parameters", ""])
    structural_rows = [row for row in parameter_rows if row["acquisition_label"] == "T1w"]
    lines.extend(markdown_table(("dataset_source", "participant_count", "repetition_time_s", "echo_times_s", "flip_angle_deg", "nifti_matrix_dimensions", "nifti_voxel_dimensions_mm", "base_resolution", "acquisition_matrix_pe", "recon_matrix_pe", "slice_thickness_mm"), structural_rows))
    lines.append("")

    lines.extend(["## 7. Field-map parameters", ""])
    fmap_rows = compact_parameter_rows(
        [row for row in parameter_rows if str(row["acquisition_label"]).startswith("fmap-")],
        ("dataset_source", "acquisition_label"),
    )
    lines.extend(markdown_table(("dataset_source", "acquisition_label", "participant_count", "echo_times_s", "repetition_time_s", "flip_angle_deg", "number_of_slices", "nifti_matrix_dimensions", "base_resolution", "acquisition_matrix_pe", "recon_matrix_pe", "slice_thickness_mm", "spacing_between_slices_mm"), fmap_rows))
    lines.extend(["", f"Field-map gap assessment: {claims['fieldmap_gap_10pct']['openneuro_observed_values'] or claims['fieldmap_gap_10pct']['complete_dataset_observed_values'] or 'not available'}.", ""])

    lines.extend(["## 8. SBRef inventory", ""])
    sbref_rows = []
    for audit in audits:
        counts = Counter(record.acquisition for record in audit.main_sbref())
        participants = defaultdict(set)
        for record in audit.main_sbref():
            participants[record.acquisition].add(record.participant)
        for acquisition in PRINCIPAL_ACQUISITIONS:
            sbref_rows.append({"dataset": audit.spec.label, "acquisition": acquisition, "SBRef sidecars": counts.get(acquisition, 0), "participants": len(participants.get(acquisition, set()))})
    lines.extend(markdown_table(("dataset", "acquisition", "SBRef sidecars", "participants"), sbref_rows))
    lines.append("")

    lines.extend(["## 9. Head-coil distribution", ""])
    coil_rows = [{"dataset": audit.spec.label, "distribution": coil_distribution(audit)} for audit in audits]
    lines.extend(markdown_table(("dataset", "distribution"), coil_rows))
    lines.extend(["", "ReceiveCoilName is treated as primary evidence; repository subject lists are secondary context only.", ""])

    lines.extend(["## 10. Acquisition order and counterbalancing", ""])
    order_rows = []
    for audit in audits:
        full_orders = [order for order in audit.scan_orders.values() if len(order) == 6]
        matching_claim = evaluate_claim("latin_square_assignments_verified", audit, parse_counterbalance_file(Path(order_source))[0] if order_source else (), order_source)
        order_rows.append({"dataset": audit.spec.label, "scans.tsv participants": len(audit.scan_orders), "complete six-condition orders": len(full_orders), "assignment status": matching_claim.status})
    lines.extend(markdown_table(("dataset", "scans.tsv participants", "complete six-condition orders", "assignment status"), order_rows))
    lines.extend(["", "The definition source establishes the intended scheme; participant adherence is evaluated separately from scans.tsv row order. Acquisition timestamps are not reproduced.", ""])

    lines.extend(["## 11. Complete-versus-public dataset comparison", ""])
    comparison_display = [{"measure": key, "value": value} for key, value in comparison_row.items()]
    lines.extend(markdown_table(("measure", "value"), comparison_display))
    lines.append("")

    lines.extend(["## 12. Technical propositions requiring correction or qualification", ""])
    correction_rows = []
    for row in claim_rows:
        if row["complete_dataset_status"] in {"CONTRADICTED", "PARTIALLY_SUPPORTED"} or row["openneuro_status"] in {"CONTRADICTED", "PARTIALLY_SUPPORTED"}:
            correction_rows.append({"claim_id": row["claim_id"], "complete": row["complete_dataset_status"], "public": row["openneuro_status"], "correction": row["suggested_technical_correction"] or row["reasoning"]})
    lines.extend(markdown_table(("claim_id", "complete", "public", "correction"), correction_rows))
    lines.append("")

    lines.extend(["## 13. Propositions not verifiable from metadata", ""])
    unverifiable_rows = []
    for row in claim_rows:
        statuses = {row["complete_dataset_status"], row["openneuro_status"]}
        public_unverifiable = row["openneuro_status"] in {
            "NOT_VERIFIABLE_FROM_METADATA",
            "DATA_SOURCE_UNAVAILABLE",
        }
        complete_unverifiable = (
            complete is not None
            and complete.available
            and row["complete_dataset_status"] == "NOT_VERIFIABLE_FROM_METADATA"
        )
        if public_unverifiable or complete_unverifiable:
            unverifiable_rows.append({"claim_id": row["claim_id"], "complete": row["complete_dataset_status"], "public": row["openneuro_status"], "reason": row["reasoning"]})
    lines.extend(markdown_table(("claim_id", "complete", "public", "reason"), unverifiable_rows))
    lines.extend(["", "An optimal-flip-angle comparison is not treated as a dataset fact because it requires external physiological assumptions.", ""])

    lines.extend(["## 14. Reproducibility instructions", ""])
    command = ["python code/validate_acquisition_metadata.py"]
    for argument in dataset_arguments:
        command.append(f"  --dataset {argument}")
    if order_source:
        command.append(f"  --counterbalance-file {order_source}")
    command.append(f"  --output-dir {output_dir}")
    lines.extend(
        [
            "Run from the repository root with nibabel installed when NIfTI content is available:",
            "",
            "```bash",
            " \\\n".join(command),
            "```",
            "",
            "For a fresh complete-dataset audit, replace the dataset arguments with labeled paths available on that host; use labels containing `complete` and `openneuro` to populate both comparison roles.",
            "",
            "The program exits successfully when technical propositions are unsupported; malformed arguments or unrecoverable output errors still produce a nonzero exit status.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        specs = [parse_dataset(value) for value in args.dataset]
    except argparse.ArgumentTypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    labels = [spec.label for spec in specs]
    if len(labels) != len(set(labels)):
        print("error: dataset labels must be unique", file=sys.stderr)
        return 2

    audits = [audit_dataset(spec) for spec in specs]
    complete = choose_role(audits, "complete")
    public = choose_role(audits, "openneuro")
    orders, order_source = parse_counterbalance_file(args.counterbalance_file)
    parameter_rows = [row for audit in audits for row in build_parameter_rows(audit)]
    parameter_rows.sort(
        key=lambda row: (
            str(row["dataset_source"]),
            str(row["acquisition_label"]),
            str(row["task"]),
            parameter_signature(row),
        )
    )
    claim_rows = build_claim_rows(complete, public, orders, order_source)
    comparison_row = build_comparison_row(
        complete,
        public,
        [audit for audit in audits if audit not in (complete, public)],
    )

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(output_dir / "acquisition_parameters.tsv", ACQUISITION_COLUMNS, parameter_rows)
    write_tsv(output_dir / "claim_validation.tsv", CLAIM_COLUMNS, claim_rows)
    comparison_columns = tuple(comparison_row.keys())
    write_tsv(output_dir / "dataset_comparison.tsv", comparison_columns, [comparison_row])
    report = build_markdown_report(
        audits,
        complete,
        public,
        parameter_rows,
        claim_rows,
        comparison_row,
        args.dataset,
        output_dir,
        order_source,
    )
    (output_dir / "metadata_audit.md").write_text(report, encoding="utf-8")

    for audit in audits:
        print(
            f"{audit.spec.label}: participants={len(audit.participants)} "
            f"bold_acquisitions={len(logical_bold_units(audit))} "
            f"json={audit.inventory_counts.get('json', 0)} "
            f"nifti_available={audit.inventory_counts.get('nifti_available', 0)}"
        )
    print(f"Wrote audit outputs to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

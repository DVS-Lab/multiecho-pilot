#!/usr/bin/env python3
"""Create descriptive group tSNR maps and figures using a completed coverage run."""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import nibabel as nib
import numpy as np
from PIL import Image

from audit_coverage import (
    ACQUISITIONS, SPACE, align, binary, coil_groups, on_grid, roi_masks,
)
from reextract_motor_model2 import manuscript_subjects


COILS = {"20ch": 16, "64ch": 22}
VIEWS = (
    ("OFC and temporal cortex", "Orbitofrontal cortex", 2, -24),
    ("OFC", "Orbitofrontal cortex", 2, -16),
    ("OFC and ventral striatum", "Orbitofrontal cortex", 2, -8),
)


def json_digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def completed_coverage(root, requested):
    archived = json.loads((root / "first_level_feat_coverage_summary.json").read_text())
    candidates = ([requested] if requested else sorted((root / "derivatives/coverage_audit").glob("*")))
    matching = [path for path in candidates if (path / "coverage_summary.json").is_file()
                and json_digest(json.loads((path / "coverage_summary.json").read_text())) == json_digest(archived)]
    if not matching:
        raise ValueError("Pass --coverage-run with the completed November 13 coverage directory.")
    if archived["subjects"] != 38 or archived["subjects_by_coil"] != COILS:
        raise ValueError("The completed coverage summary must contain 16 and 22 participants by coil.")
    return matching[-1], archived


def raw_source(root, subject, acquisition):
    directory = root / "derivatives/fmriprep" / f"sub-{subject}" / "func"
    stem = f"sub-{subject}_task-sharedreward_acq-{acquisition}_"
    for suffix in ("desc-preproc_bold.nii.gz", "desc-optcom_bold.nii.gz"):
        paths = [path for path in directory.glob(f"{stem}*space-{SPACE}_{suffix}")
                 if "_echo-" not in path.name and "_part-phase_" not in path.name]
        if len(paths) == 1:
            if any(tag in paths[0].resolve().name for tag in ("_5mm", "_smoothed", "_denoised")):
                raise ValueError("An unsmoothed source resolves to a smoothed or denoised file.")
            return paths[0]
        if len(paths) > 1:
            raise ValueError("Multiple unsmoothed fMRIPrep inputs match one acquisition.")
    raise ValueError("An unsmoothed MNI fMRIPrep time series is missing.")


def time_moments(image, batch_size=8):
    """Stable sample SD with bounded memory and forward reads through compressed data."""
    if len(image.shape) != 4 or image.shape[3] < 2:
        raise ValueError("Expected a time series with at least two volumes.")
    count = 0
    mean = np.zeros(image.shape[:3], dtype=np.float64)
    m2 = np.zeros_like(mean)
    finite = np.ones(mean.shape, dtype=bool)
    for start in range(0, image.shape[3], batch_size):
        data = np.asarray(image.dataobj[..., start:start + batch_size], dtype=np.float64)
        finite &= np.isfinite(data).all(axis=3)
        data = np.where(np.isfinite(data), data, 0)
        batch_count = data.shape[3]
        batch_mean = data.mean(axis=3)
        delta = batch_mean - mean
        total = count + batch_count
        m2 += np.square(data - batch_mean[..., None]).sum(axis=3) + delta**2 * count * batch_count / total
        mean += delta * batch_count / total
        count = total
    sd = np.sqrt(np.maximum(m2, 0) / (count - 1))
    mean[~finite] = np.nan
    sd[~finite] = np.nan
    return mean, sd


def participant_tsnr(raw, intersection, reference):
    source = nib.load(raw, keep_file_open=True)
    mean, sd = time_moments(source)
    valid = np.isfinite(mean) & np.isfinite(sd) & (sd > 0) & (mean >= 0)
    values = np.divide(mean, sd, out=np.zeros_like(mean), where=valid).astype(np.float32)
    mapped = align(nib.Nifti1Image(values, source.affine), reference, 0)
    group_valid = binary(nib.Nifti1Image(valid.astype(np.uint8), source.affine), reference)
    group_valid &= intersection & np.isfinite(mapped)
    return mapped, group_valid, source.shape[3]


def write_map(path, values, reference):
    data = np.asarray(values, dtype=np.int16 if values.dtype.kind in "biu" else np.float32)
    nib.save(nib.Nifti1Image(data, reference.affine), path)


def roi_stats(mean, count, intersection, regions):
    result = {}
    for name, region in regions.items():
        values = mean[region & np.isfinite(mean)]
        result[name] = {
            "mean_group_tsnr_over_available_voxels": round(float(values.mean()), 4) if values.size else None,
            "mean_tsnr_contributors": round(float(count[region].mean()), 4),
            "sequence_intersection_fraction": round(float(intersection[region].mean()), 5),
            "atlas_voxels": int(region.sum()),
        }
    return result


def make_views(reference):
    steps = np.diag(reference.affine)[:3]
    if np.any(steps <= 0) or not np.allclose(reference.affine[:3, :3], np.diag(steps), atol=.001):
        raise ValueError("Expected the canonical axis-aligned MNI152 template.")
    xyz = [reference.affine[d, 3] + steps[d] * np.arange(reference.shape[d]) for d in range(3)]
    for title, region, axis, requested in VIEWS:
        index = int(np.abs(xyz[axis] - requested).argmin())
        horizontal, vertical = [d for d in range(3) if d != axis]
        xx, yy = xyz[horizontal], xyz[vertical]
        extent = [xx[0] - steps[horizontal]/2, xx[-1] + steps[horizontal]/2,
                  yy[0] - steps[vertical]/2, yy[-1] + steps[vertical]/2]
        yield title, region, axis, index, xyz[axis][index], xx, yy, extent


def montage(columns, reference, regions, mode, vmax, output):
    views = list(make_views(reference))
    coils = tuple(COILS) if mode == "tsnr" else ("all",)
    fig, axes = plt.subplots(len(views) * len(coils), len(columns), squeeze=False,
                             figsize=(13.3, 2.0 * len(views) * len(coils) + .8), layout="constrained")
    background = reference.get_fdata(dtype=np.float32)
    brain = background > 0
    anatomy_vmax = np.percentile(background[brain], 99)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#c5c5c5")
    if mode == "intersection":
        cmap = ListedColormap(["#303a61", "#f2d44d"])
    for group, coil in enumerate(coils):
        for v, (title, region, axis, index, actual, xx, yy, extent) in enumerate(views):
            row = group * len(views) + v
            for col, (acq, maps) in enumerate(columns):
                ax = axes[row, col]
                data = np.take(maps[coil], index, axis=axis).T
                template = np.take(background, index, axis=axis).T
                ax.imshow(template, origin="lower", extent=extent, cmap="gray", vmin=0, vmax=anatomy_vmax)
                in_brain = np.take(brain, index, axis=axis).T
                if mode == "tsnr":
                    display = np.ma.masked_where(~np.isfinite(data), data)
                    # Outside template tissue, show the anatomical background.
                    rgba = cmap(plt.Normalize(0, vmax)(display))
                    rgba[..., 3] = in_brain
                    layer = ax.imshow(rgba, origin="lower", extent=extent, interpolation="nearest")
                else:
                    layer = ax.imshow(np.ma.masked_where(~in_brain, data), origin="lower", extent=extent,
                                      cmap=cmap, vmin=0, vmax=vmax, interpolation="nearest")
                boundary = np.take(regions[region], index, axis=axis).T
                if boundary.any():
                    ax.contour(xx, yy, boundary, levels=[.5], colors=["#ff8e43"], linewidths=.65)
                ax.set(xticks=[], yticks=[], xlim=extent[:2], ylim=extent[2:])
                if row == 0:
                    ax.set_title(acq.upper(), fontsize=10, fontweight="bold")
                if col == 0:
                    axis_label = "xyz"[axis]
                    sample = f"{coil.removesuffix('ch')}-channel · N = {COILS[coil]}\n" if coil != "all" else ""
                    ax.set_ylabel(f"{sample}{title}\n{axis_label} = {actual:g} mm", fontsize=9,
                                  rotation=0, ha="right", va="center", labelpad=12)
                if row == len(views) * len(coils) - 1:
                    ax.set_xlabel("P ← → A" if axis == 0 else "L ← → R", fontsize=8)
    norm = plt.Normalize(0, vmax)
    colorbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, shrink=.57, pad=.015)
    colorbar.set_label({"tsnr": "Mean participant tSNR",
                       "intersection": "Coverage in all 38 participants"}[mode], fontsize=10)
    if mode == "intersection":
        colorbar.set_ticks([0, 1])
        colorbar.set_ticklabels(["Incomplete", "Complete"])
    title = {"tsnr": "Temporal signal-to-noise ratio within each sequence intersection",
             "intersection": "Intersection coverage across acquisitions · N = 38"}[mode]
    fig.suptitle(title, fontsize=16, fontweight="bold")
    if mode == "tsnr":
        fig.legend(handles=[Patch(facecolor="#c5c5c5", label="Outside intersection or undefined tSNR"),
                            Patch(facecolor="none", edgecolor="#ff8e43", label="Anatomical ROI")],
                   loc="outside lower center", ncol=2, frameon=False, fontsize=10)
    fig.savefig(output.with_suffix(".png"), dpi=300)
    fig.savefig(output.with_suffix(".pdf"), dpi=300, metadata={"Creator": "Sequence pilot descriptive maps"})
    with BytesIO() as buffer:
        fig.savefig(buffer, format="png", dpi=160)
        with Image.open(buffer) as raster:
            raster.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE).save(
                output.with_name(output.name + "_preview.png"), optimize=True)
    plt.close(fig)


def run(args):
    root = args.root.resolve()
    coverage, archived = completed_coverage(root, args.coverage_run)
    subjects = manuscript_subjects(root)
    coils = coil_groups(root, subjects)
    if len(subjects) != 38:
        raise ValueError("Expected the 38 primary-analysis participants.")
    template = nib.as_closest_canonical(nib.load(args.fsldir / "data/standard/MNI152_T1_2mm_brain.nii.gz"))
    regions, _ = roi_masks(args.fsldir, template)
    selections = {}
    # Check every input before starting the temporal reductions.
    for acquisition in ACQUISITIONS:
        for subject in subjects:
            raw = raw_source(root, subject, acquisition)
            raw_image = nib.load(raw)
            if len(raw_image.shape) != 4 or raw_image.shape[3] < 2:
                raise ValueError("An unsmoothed input is not a time series.")
            selections[subject, acquisition] = raw
    saved_masks = {}
    for acquisition in ACQUISITIONS:
        for coil, size in {"all": 38}.items():
            row = archived["primary_by_protocol"][acquisition][coil]
            count = on_grid(coverage / f"{acquisition}_{coil}_mask_participant_count.nii.gz", template)
            intersection = on_grid(coverage / f"{acquisition}_{coil}_intersection.nii.gz", template)
            if (row["participants"] != size or not np.all(np.isin(count, np.arange(size + 1)))
                    or not np.array_equal(count == size, intersection > .5)):
                raise ValueError("Saved coverage counts or intersections are inconsistent.")
            saved_masks[acquisition, coil] = count.astype(np.int16), intersection.astype(np.int16)
    common = on_grid(coverage / "all_acquisitions_all_38_intersection.nii.gz", template)
    if not np.array_equal(common > .5, np.logical_and.reduce([
            saved_masks[a, "all"][1] > .5 for a in ACQUISITIONS])):
        raise ValueError("The saved common intersection disagrees with the acquisition maps.")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Choose a new output directory to preserve earlier maps and figures.")
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "participants": 38, "participants_by_coil": COILS,
        "coverage_summary_sha256": json_digest(archived),
        "source": "unsmoothed fMRIPrep MNI152NLin6Asym magnitude or optimally combined series",
        "computed_tsnr": "temporal mean divided by sample temporal SD (N-1 divisor), all input volumes",
        "group_mean": "unweighted participant tSNR mean within the sequence's saved all-38 intersection, requiring all coil-group values finite",
        "resampling": "nearest-neighbor scalar and mask sampling onto the completed MNI152 2-mm audit lattice",
        "missing_values": "NaN outside the sequence intersection or where any coil-group tSNR is undefined, with masks and contributor counts saved separately",
        "cells": {},
    }
    with tempfile.TemporaryDirectory(prefix=".tsnr-pending-", dir=output.parent) as pending:
        stage = Path(pending)
        columns = []
        for acquisition in ACQUISITIONS:
            group_maps = {}
            coverage_count, intersection = saved_masks[acquisition, "all"]
            intersection = intersection > .5
            write_map(stage / f"{acquisition}_all38_intersection.nii.gz", intersection, template)
            write_map(stage / f"{acquisition}_all38_mask_count.nii.gz", coverage_count, template)
            for coil, size in COILS.items():
                total = np.zeros(template.shape, dtype=np.float64)
                counts = np.zeros(template.shape, dtype=np.int16)
                volumes = []
                for subject in [s for s in subjects if coils[s] == coil]:
                    values, valid, nvolumes = participant_tsnr(selections[subject, acquisition], intersection, template)
                    total += np.where(valid, values, 0)
                    counts += valid
                    volumes.append(nvolumes)
                complete = intersection & (counts == size)
                mean = np.divide(total, size, out=np.full(total.shape, np.nan, dtype=np.float32), where=complete)
                fraction = counts.astype(np.float32) / size
                images = {"mean_tsnr": mean, "tsnr_contributor_count": counts,
                          "tsnr_contributor_fraction": fraction,
                          "undefined_tsnr_count": np.where(intersection, size - counts, 0)}
                for name, data in images.items():
                    write_map(stage / f"{acquisition}_{coil}_{name}.nii.gz", data, template)
                report["cells"][f"{acquisition}_{coil}"] = {
                    "participants": size, "computed_unsmoothed_tsnr_maps": size,
                    "input_volumes_min": min(volumes), "input_volumes_max": max(volumes),
                    "voxels_with_any_tsnr": int((counts > 0).sum()),
                    "voxels_with_complete_tsnr": int((counts == size).sum()),
                    "rois": roi_stats(mean, counts, intersection, regions),
                }
                group_maps[coil] = mean
                print(f"Prepared {acquisition.upper()} {coil} (N = {size})", flush=True)
            columns.append((acquisition, group_maps))

        brain = template.get_fdata(dtype=np.float32) > 0
        pooled = np.concatenate([data[coil][brain & np.isfinite(data[coil])] for _, data in columns for coil in COILS])
        vmax = args.vmax or max(10., 10 * math.ceil(np.percentile(pooled, 99) / 10))
        report["tsnr_display_range"] = [0, vmax]
        report["fraction_of_group_mean_voxels_above_display_maximum"] = round(float((pooled > vmax).mean()), 6)
        montage(columns, template, regions, "tsnr", vmax, stage / "tsnr_montage")
        intersections = [(acq, {"all": saved_masks[acq, "all"][1]}) for acq in ACQUISITIONS]
        intersections.append(("All six", {"all": common}))
        write_map(stage / "all_six_all38_intersection.nii.gz", common, template)
        montage(intersections, template, regions, "intersection", 1, stage / "intersection_coverage_supplement")
        report["figure_slices_mni_mm"] = [{"region": title, "axis": "xyz"[axis], "coordinate": coordinate}
                                          for title, _, axis, coordinate in VIEWS]
        (stage / "group_tsnr_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        (stage / "figure_captions.txt").write_text(
            "Temporal signal-to-noise ratio across six acquisitions. Each map is the voxelwise mean of "
            "participant tSNR maps for the 20-channel (N = 16) or 64-channel (N = 22) coil. Participant "
            "tSNR is temporal mean divided by sample temporal SD of the unsmoothed series. Each "
            "sequence is displayed within its saved first-level FEAT mask intersection across all "
            "38 participants, using the same intersection for both coils and requiring all coil-group "
            f"tSNR values to be defined. All maps use the same 0–{vmax:g} color scale. Gray marks voxels "
            "outside the sequence intersection or with undefined tSNR. Companion masks and counts "
            "identify these locations. Orange contours mark atlas-defined orbitofrontal cortex.\n\n"
            "Intersection coverage across six acquisitions (N = 38 per acquisition). Yellow marks "
            "voxels included in every participant's first-level FEAT mask, and blue marks incomplete "
            "coverage. The final column requires coverage in all 228 participant–acquisition runs. "
            "These maps reuse the completed coverage audit.\n\n"
            "Both figures use matched MNI axial slices at z = −24, −16, and −8 mm on the public "
            "MNI152 template.\n")
        stage.rename(output)
    print(f"Saved group maps and figures to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--coverage-run", type=Path, help="Completed November 13 coverage directory")
    parser.add_argument("--fsldir", type=Path, default=Path(os.environ.get("FSLDIR", "/usr/local/fsl")))
    parser.add_argument("--output", type=Path, required=True, help="New directory for aggregate maps and figures")
    parser.add_argument("--vmax", type=float, help="Common display maximum, otherwise pooled 99th percentile rounded up")
    arguments = parser.parse_args()
    if arguments.vmax is not None and (not math.isfinite(arguments.vmax) or arguments.vmax <= 0):
        parser.error("--vmax must be finite and positive")
    run(arguments)

#!/usr/bin/env python3
"""Correlate fixed-reference percent signal change with the manuscript ROI estimates."""
from collections import Counter
import json
import math
from pathlib import Path
import shutil
from statistics import correlation, mean
import sys

from audit_motor_repair import ACQUISITIONS, fsl, same_grid, settings
from reextract_motor_model2 import manuscript_subjects

# Mumford, perchange_guide.pdf, Table 1. Use the same reference event at every TR.
REFERENCE_PEAK = 0.2088  # Isolated 1-s unit-height event, FSL double-gamma HRF.
ROIS = {
    "VSconstrained": (1, 13, {5: -1, 7: 1, 8: -1, 10: 1}, (("VSconstrained", 1),)),
    "rFFA": (3, 3, {8: 1, 9: -1}, (("rFFA", 1),)),
    "bilateralMotor": (2, 3, {1: 1, 2: -1}, (("leftMotor", -1), ("rightMotor", 1))),
    "bilateralCerebellum": (2, 3, {1: 1, 2: -1}, (("rightCerebellum", -1), ("leftCerebellum", 1))),
}


class ExcludedRun(Exception):
    """A predefined reason for excluding an ROI/run pair."""


def check_contrast(feat, index, expected):
    con = feat / "design.con"
    if not con.is_file():
        raise ExcludedRun("missing_contrast")
    rows = con.read_text().partition("/Matrix")[2].splitlines()
    rows = [row for row in rows if row.strip()]
    if len(rows) < index:
        raise ExcludedRun("missing_contrast")
    try:
        weights = {i: float(w) for i, w in enumerate(rows[index - 1].split(), 1) if float(w)}
    except ValueError as error:
        raise ExcludedRun("invalid_contrast") from error
    config = settings(feat)
    if weights != expected or any(
        config.get(f"fmri(convolve{i})") not in {"3", "3.0"}
        or config.get(f"fmri(convolve_phase{i})") not in {"0", "0.0"}
        for i in expected
    ):
        raise ExcludedRun("contrast_or_hrf_mismatch")


def voxel_values(image, mask):
    result = fsl("fslmeants", "-i", image, "-m", mask, "--showall", "--transpose")
    try:
        rows = [tuple(map(float, line.split())) for line in result.splitlines() if line.strip()]
    except ValueError as error:
        raise ExcludedRun("invalid_fslmeants_output") from error
    if not rows or any(len(row) != 4 or not all(map(math.isfinite, row)) for row in rows):
        raise ExcludedRun("invalid_fslmeants_output")
    return {tuple(row[:3]): row[3] for row in rows}


def roi_values(feat, index, masks, scale):
    maps = (
        feat / "mask.nii.gz",
        feat / "mean_func.nii.gz",
        feat / "stats" / f"cope{index}.nii.gz",
        feat / "stats" / f"zstat{index}.nii.gz",
    )
    values = []
    for mask, sign in masks:
        if not all(path.is_file() for path in (mask, *maps)):
            raise ExcludedRun("missing_image_or_mask")
        if not all(same_grid(path, mask) for path in maps):
            raise ExcludedRun("grid_mismatch")
        coverage, baseline, cope, zstat = (voxel_values(path, mask) for path in maps)
        if not coverage.keys() == baseline.keys() == cope.keys() == zstat.keys():
            raise ExcludedRun("voxel_alignment_mismatch")
        if any(value <= 0 for value in coverage.values()):
            raise ExcludedRun("incomplete_feat_mask_coverage")
        if any(value <= 0 for value in baseline.values()):
            raise ExcludedRun("nonpositive_baseline")
        values.append((sign * mean(cope.values()), sign * mean(zstat.values()),
                       sign * scale * mean(cope[voxel] / baseline[voxel] for voxel in cope)))
    return tuple(mean(column) for column in zip(*values))


def check_saved_values(root, subject, acq, roi, model, values):
    directory = "extractions_model2_motor" if model == 2 else "extractions"
    for stat, calculated in zip(("beta", "zstat"), values):
        name = f"ts_sub-{subject}_acq_{acq}_type-act_img-{stat}_mask-{roi}_denoise_base.txt"
        try:
            saved = float((root / "derivatives" / directory / name).read_text())
        except (OSError, ValueError) as error:
            raise ExcludedRun("missing_or_invalid_saved_estimate") from error
        if not math.isclose(saved, calculated, rel_tol=5e-6, abs_tol=1e-3):
            raise ExcludedRun("saved_estimate_mismatch")


def correlations(rows):
    if not rows:
        return {"cope_vs_psc": None, "zstat_vs_psc": None}
    cope, zstat, psc = zip(*rows)
    return {
        f"{name}_vs_psc": round(correlation(values, psc), 4)
        if len(set(values)) > 1 and len(set(psc)) > 1 else None
        for name, values in (("cope", cope), ("zstat", zstat))
    }


def summarize(root, subjects, roi, model, index, weights, hemispheres):
    masks = [(root / "masks" / f"mask_{name}.nii.gz", sign) for name, sign in hemispheres]
    scale = 100 * REFERENCE_PEAK / sum(weight for weight in weights.values() if weight > 0)
    complete = []
    exclusions = Counter()
    for subject in subjects:
        runs = []
        for acq in ACQUISITIONS:
            feat = (root / "derivatives" / "fsl" / f"sub-{subject}" /
                    f"L1_task-sharedreward_model-{model}_type-act_acq-{acq}_sm-0_denoising-base.feat")
            try:
                check_contrast(feat, index, weights)
                values = roi_values(feat, index, masks, scale)
                check_saved_values(root, subject, acq, roi, model, values[:2])
            except ExcludedRun as error:
                exclusions[str(error)] += 1
            else:
                runs.append(values)
        if len(runs) == len(ACQUISITIONS):
            complete.append(runs)

    pooled = [run for runs in complete for run in runs]
    centered = []
    for runs in complete:
        averages = [mean(column) for column in zip(*runs)]
        centered.extend(tuple(value - average for value, average in zip(run, averages))
                        for run in runs)
    return {
        "model": model,
        "contrast": index,
        "cope_to_psc_scale_before_baseline_division": round(scale, 4),
        "complete_subjects": len(complete),
        "runs_used": len(pooled),
        "run_exclusions": dict(exclusions),
        "pooled_pearson_r": correlations(pooled) if len(complete) >= 5 else correlations([]),
        "within_participant_pearson_r": correlations(centered) if len(complete) >= 5 else correlations([]),
    }


def main(root):
    if any(shutil.which(tool) is None for tool in ("fslhd", "fslmeants")):
        raise SystemExit("Load the existing FSL environment before running this audit.")
    subjects = manuscript_subjects(root)
    if len(subjects) != 38:
        raise SystemExit(f"Expected 38 manuscript participants, found {len(subjects)}.")
    report = {
        "reference_event_seconds": 1,
        "reference_double_gamma_peak": REFERENCE_PEAK,
        "expected_subjects": len(subjects),
        "expected_runs_per_roi": len(subjects) * len(ACQUISITIONS),
        "rois": {roi: summarize(root, subjects, roi, *config) for roi, config in ROIS.items()},
    }
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())

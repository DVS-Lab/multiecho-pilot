#!/usr/bin/env python3
"""Prepare corrected motor extractions and print an aggregate coverage report."""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory

from audit_motor_repair import (
    ACQUISITIONS, STAT_FILES, direction, extraction, fsl, number, read,
    resolve, same_grid, settings, timing, voxels,
)

# Each model-2 COPE 3 is left hand > right hand. The first ROI in each
# pair needs right > left. The other ROI already uses model 2 and COPE 3.
BILATERAL_PAIRS = {
    "bilateralMotor": ("leftMotor", "rightMotor"),
    "bilateralCerebellum": ("rightCerebellum", "leftCerebellum"),
}
TARGET_ROIS = tuple(pair[0] for pair in BILATERAL_PAIRS.values())
CORRECTED_FILE = re.compile(
    rf"ts_sub-\d+_acq_(?:{'|'.join(ACQUISITIONS)})_type-act_"
    rf"img-(?:{'|'.join(STAT_FILES)})_mask-(?:{'|'.join((*TARGET_ROIS, *BILATERAL_PAIRS))})"
    r"_denoise_base\.txt"
)
OUTPUT_NAME = "extractions_model2_motor"


def manuscript_subjects(root):
    import pandas as pd

    # Match the publication notebook's main-cohort, six-run, and motion-QC filters.
    demographics = pd.read_excel(
        root / "code/multiecho-pilot_Demographics.xlsx",
        usecols=["Subject", "spSubs", "SixRuns"],
    )
    quality = pd.read_csv(
        root / "derivatives/Task-sharedreward_Level-Acq_Outlier-info_mriqc-0.16.1.tsv",
        sep="\t", usecols=["Sub", "outlier_acq_Custom1"],
    )
    excluded = {s[4:] for s in quality.loc[quality["outlier_acq_Custom1"] == True, "Sub"]
                if isinstance(s, str) and s.startswith("sub-")}
    main = demographics.loc[(demographics["spSubs"] == 0) & (demographics["SixRuns"] != 0), "Subject"]
    subjects = sorted(set(main.astype(str)) - excluded)
    if not subjects or any(not subject.isascii() or not subject.isdigit() for subject in subjects):
        raise ValueError("The publication filters did not produce a valid numeric subject list.")
    return subjects


def mask_coverage(roi_mask, count, feat_mask):
    if not count:
        return "roi_mask_missing_or_empty"
    if not feat_mask.is_file():
        return "feat_mask_missing"
    if not same_grid(roi_mask, feat_mask):
        return "grid_mismatch"
    covered = voxels(roi_mask, "-k", feat_mask)
    if covered is None:
        return "unreadable"
    return "full" if covered == count else "incomplete"


def inspect_run(root, subject, acq, roi_masks, roi_sizes, counts):
    feat = (root / "derivatives/fsl" / f"sub-{subject}" /
            f"L1_task-sharedreward_model-2_type-act_acq-{acq}_sm-0_denoising-base.feat")
    fsf = settings(feat)
    issues = set()
    estimates = {}

    if timing(fsf, resolve(root, feat, fsf.get("feat_files(1)"))) != "tr_matches":
        issues.add("model2_tr_unverified")
    if direction(feat, fsf, 3) != "left_gt_right":
        issues.add("model2_cope3_unverified")

    feat_mask = feat / "mask.nii.gz"
    for roi in TARGET_ROIS:
        status = mask_coverage(roi_masks[roi], roi_sizes[roi], feat_mask)
        counts["coverage"][roi][status] += 1
        if status != "full":
            issues.add(f"{roi}_coverage")

    maps = {stat: feat / "stats" / f"{stem}.nii.gz" for stat, stem in STAT_FILES.items()}
    for stat, image in maps.items():
        if not image.is_file():
            issues.add(f"{stat}_map_missing")

    if issues:
        return estimates, issues

    for bilateral, (target, original) in BILATERAL_PAIRS.items():
        for stat, image in maps.items():
            mask = roi_masks[target]
            if not same_grid(image, mask):
                issues.add(f"{target}_{stat}_grid_mismatch")
                continue
            value = number(fsl("fslmeants", "-i", image, "-m", mask).strip())
            counterpart = number(read(extraction(root, subject, acq, original, stat)).strip())
            if not math.isfinite(value) or (stat == "varcope" and value <= 0):
                issues.add(f"{target}_{stat}_invalid_value")
                continue
            if not math.isfinite(counterpart) or (stat == "varcope" and counterpart <= 0):
                issues.add(f"{original}_{stat}_invalid_original")
                continue
            corrected = value if stat == "varcope" else -value
            estimates[extraction(root, subject, acq, target, stat).name] = corrected
            estimates[extraction(root, subject, acq, bilateral, stat).name] = (corrected + counterpart) / 2
    return estimates, issues


def stage_extractions(root, values):
    destination = root / "derivatives" / OUTPUT_NAME
    original = root / "derivatives/extractions"
    with TemporaryDirectory(prefix=".model2_motor_", dir=destination.parent) as temporary:
        staging = Path(temporary) / "extractions"
        staging.mkdir()
        for path in original.glob("*.txt"):
            if path.is_file() and not CORRECTED_FILE.fullmatch(path.name):
                shutil.copyfile(path, staging / path.name)
        for name, value in values.items():
            (staging / name).write_text(f"{value:.12g}\n")
        try:
            os.rename(staging, destination)
        except OSError:
            if not destination.is_dir():
                raise
            staged_names = {p.name for p in staging.iterdir()}
            if staged_names == {p.name for p in destination.iterdir()} and all(
                (destination / name).is_file()
                and (destination / name).read_bytes() == (staging / name).read_bytes()
                for name in staged_names
            ):
                return "already_ready"
            return "destination_conflict"
    return "ready"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/ZPOOL/data/projects/multiecho-pilot"))
    args = parser.parse_args()
    root = args.root.resolve()
    for tool in ("fslhd", "fslstats", "fslmeants"):
        if shutil.which(tool) is None:
            parser.error(f"Load the FSL environment. Missing {tool}.")
    try:
        subjects = manuscript_subjects(root)
    except ImportError:
        parser.error("Use the manuscript notebook's Python environment with pandas and openpyxl.")

    summary = {
        "manuscript_subjects_selected": len(subjects),
        "manuscript_runs_expected": len(subjects) * len(ACQUISITIONS),
        "runs_ready": 0,
        "repaired_files_staged": 0,
        "extraction_status": "blocked",
        "by_protocol": {},
    }
    masks = {roi: root / "masks" / f"mask_{roi}.nii.gz" for roi in TARGET_ROIS}
    sizes = {roi: voxels(mask) if mask.is_file() else None for roi, mask in masks.items()}
    values = {}
    for acq in ACQUISITIONS:
        counts = {"runs_expected": len(subjects), "runs_ready": 0,
                  "coverage": {roi: Counter() for roi in TARGET_ROIS}, "issues": Counter()}
        for subject in subjects:
            estimates, issues = inspect_run(root, subject, acq, masks, sizes, counts)
            if issues:
                counts["issues"].update(issues)
                print(f"sub-{subject} {acq}: {', '.join(sorted(issues))}", file=sys.stderr)
            else:
                counts["runs_ready"] += 1
                values.update(estimates)
        summary["by_protocol"][acq] = counts
        summary["runs_ready"] += counts["runs_ready"]

    if summary["runs_ready"] == summary["manuscript_runs_expected"]:
        status = stage_extractions(root, values)
        summary["extraction_status"] = status
        if status in {"ready", "already_ready"}:
            summary["repaired_files_staged"] = len(values)
            summary["extraction_directory"] = f"derivatives/{OUTPUT_NAME}"
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

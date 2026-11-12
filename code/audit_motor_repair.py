#!/usr/bin/env python3
"""Inspect existing motor FEAT fits and group masks. Emit aggregate JSON only."""
import argparse
from collections import Counter
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

ACQUISITIONS = ("mb1me1", "mb1me4", "mb3me1", "mb3me4", "mb6me1", "mb6me4")
ROIS = {"rightMotor": 2, "leftCerebellum": 2, "leftMotor": 4, "rightCerebellum": 4}
MASK_ROIS = ("leftMotor", "rightMotor", "bilateralMotor")
STAT_FILES = {"beta": "cope3", "zstat": "zstat3", "varcope": "varcope3"}
MODEL = re.compile(r"(?:^|[/_])(?:L[123]_task-sharedreward_)?model-([1-4])(?:[/_.]|$)")
FEAT_INPUT = re.compile(r"^set feat_files\(\d+\)\s+[\"{]?([^\n\"}]+)", re.M)
EV_SETTING = re.compile(r"fmri\((?:evs_(?:orig|real|vox)|(?:shape|convolve|convolve_phase|deriv_yn|tempfilt_yn|ortho)\d+(?:\.\d+)?)\)")
BOLD_SETTINGS = ("inputtype", "analysis", "ndelete", "npts", "mc", "st", "bet_yn",
                 "regunwarp_yn", "smooth", "norm_yn", "perfsub_yn", "temphp_yn",
                 "paradigm_hp", "templp_yn", "motionevs", "confoundevs", "prewhiten_yn")


def read(path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def settings(feat):
    return {key: value.strip().strip('"{}') for key, value in
            re.findall(r"^set (\S+)\s+(.+)$", read(feat / "design.fsf"), re.M)}


def resolve(root, directory, value):
    if not value:
        return None
    path = Path(value)
    candidates = [path] if path.is_absolute() else [directory / path, directory.parent / path]
    if "/multiecho-pilot/" in value:
        candidates.append(root / value.split("/multiecho-pilot/", 1)[1])
    return next((candidate for candidate in candidates if candidate.exists()), None)


def fsl(tool, *args):
    process = subprocess.run([tool, *map(str, args)], capture_output=True, text=True, check=False)
    return process.stdout if process.returncode == 0 else ""


@lru_cache(maxsize=None)
def header(path):
    return dict(line.split(maxsplit=1) for line in fsl("fslhd", path).splitlines()
                if len(line.split(maxsplit=1)) == 2)


def grid(path):
    h = header(path)
    prefix = "sto" if h.get("sform_code", "0") != "0" else "qto"
    dims = tuple(h.get(f"dim{i}") for i in range(1, 4))
    affine = tuple(float(v) for i in range(1, 5) for v in h.get(f"{prefix}_xyz:{i}", "").split())
    return dims, affine


def same_grid(a, b):
    shape_a, affine_a = grid(a)
    shape_b, affine_b = grid(b)
    return (None not in shape_a and shape_a == shape_b and len(affine_a) == len(affine_b) == 16
            and all(abs(x-y) <= 0.001 for x, y in zip(affine_a, affine_b)))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-6)


def timing(fsf, image):
    if image is None:
        return "input_unavailable"
    h = header(image)
    tr = number(h.get("pixdim4"))
    if h.get("time_units") == "ms":
        tr /= 1000
    design_tr = number(fsf.get("fmri(tr)"))
    if not (math.isfinite(tr) and math.isfinite(design_tr)):
        return "tr_unavailable"
    return "tr_matches" if math.isclose(tr, design_tr, abs_tol=1e-5) else "tr_differs"


def direction(feat, fsf, index):
    if [Path(fsf.get(f"fmri(custom{i})", "")).name for i in (1, 2)] != [
        "_guess_allLeftButton.txt", "_guess_allRightButton.txt"
    ]:
        return "unverified_ev_order"
    rows = read(feat / "design.con").partition("/Matrix")[2].strip().splitlines()
    if len(rows) < index:
        return "row_unavailable"
    weights = list(map(number, rows[index-1].split()))
    if len(weights) < 2 or any(w != 0 for w in weights[2:]):
        return "other"
    return {(1, -1): "left_gt_right", (-1, 1): "right_gt_left"}.get(tuple(weights[:2]), "other")


def extraction(root, sub, acq, roi, stat="beta"):
    return (root / "derivatives/extractions" /
            f"ts_sub-{sub}_acq_{acq}_type-act_img-{stat}_mask-{roi}_denoise_base.txt")


def same_small_input(root, dir2, dir4, model2, model4, key):
    a, b = (resolve(root, d, m.get(key)) for d, m in ((dir2, model2), (dir4, model4)))
    return bool(a and b and a.is_file() and b.is_file() and
                (a.samefile(b) or a.read_bytes() == b.read_bytes()))


def inspect_pair(root, sub, acq, metrics, use_sample):
    feat_root = root / "derivatives/fsl" / f"sub-{sub}"
    paths = {i: feat_root / f"L1_task-sharedreward_model-{i}_type-act_acq-{acq}_sm-0_denoising-base.feat"
             for i in (2, 4)}
    configs = {i: settings(p) for i, p in paths.items()}
    if not all(configs.values()):
        metrics["reuse"]["missing_design_pair"] += 1
        return
    fsf2, fsf4 = configs[2], configs[4]
    bold = {i: resolve(root, paths[i], cfg.get("feat_files(1)")) for i, cfg in configs.items()}
    for i, fsf in configs.items():
        row = direction(paths[i], fsf, 3)
        metrics[f"model_{i}"][row] += 1
        metrics[f"model_{i}"][timing(fsf, bold[i])] += 1
    if direction(paths[4], fsf4, 4) == "right_gt_left" and all(
        (paths[4] / "stats" / f"{stem}4.nii.gz").is_file() for stem in ("cope", "zstat", "varcope")
    ):
        metrics["reuse"]["model_4_reverse_contrast_maps_present"] += 1
    if timing(fsf2, bold[2]) == "tr_matches" and direction(paths[2], fsf2, 3) == "left_gt_right" and all(
        (paths[2] / "stats" / f"{stem}.nii.gz").is_file() for stem in STAT_FILES.values()
    ):
        metrics["reuse"]["model_2_correct_tr_and_motor_maps_present"] += 1
    if bold[2] and bold[4] and bold[2].samefile(bold[4]):
        metrics["reuse"]["same_input_nifti"] += 1
    if all(fsf2.get(f"fmri({k})") == fsf4.get(f"fmri({k})") for k in BOLD_SETTINGS):
        metrics["reuse"]["same_preprocessing_settings"] += 1
    if same_small_input(root, paths[2], paths[4], fsf2, fsf4, "confoundev_files(1)"):
        metrics["reuse"]["same_confound_file_content"] += 1
    ev2, ev4 = ({k: v for k, v in fsf.items() if EV_SETTING.fullmatch(k)} for fsf in (fsf2, fsf4))
    ev_keys = {k for k in fsf2.keys() | fsf4.keys() if re.fullmatch(r"fmri\(custom\d+\)", k)
               and any(fsf.get(k) for fsf in (fsf2, fsf4))}
    # Missing-EV placeholders may retain a path for a file that was never used.
    if ev2 == ev4 and all(fsf2.get(k) == fsf4.get(k) or
                          same_small_input(root, paths[2], paths[4], fsf2, fsf4, k) for k in ev_keys):
        metrics["reuse"]["same_task_ev_specification"] += 1
    if not use_sample:
        return
    model2_mask = paths[2] / "mask.nii.gz"
    for roi in ("leftMotor", "rightCerebellum"):
        mask = root / "masks" / f"mask_{roi}.nii.gz"
        if mask.is_file() and model2_mask.is_file() and same_grid(mask, model2_mask):
            total = voxels(mask)
            if total and voxels(mask, "-k", model2_mask) == total:
                metrics["reuse"][f"sampled_model_2_covers_{roi}"] += 1
    for roi, model in ROIS.items():
        mask = root / "masks" / f"mask_{roi}.nii.gz"
        for stat, stem in STAT_FILES.items():
            counts = metrics["sampled_extraction_checks"][roi][stat]
            stored = number(read(extraction(root, sub, acq, roi, stat)).strip())
            image = paths[model] / "stats" / f"{stem}.nii.gz"
            if not (mask.is_file() and image.is_file() and math.isfinite(stored)):
                counts["unavailable"] += 1
            elif not same_grid(image, mask):
                counts["grid_differs"] += 1
            else:
                observed = number(fsl("fslmeants", "-i", image, "-m", mask).strip())
                counts["matches" if close(stored, observed) else "differs"] += 1
    for region, hemispheres in (("bilateralMotor", ("leftMotor", "rightMotor")),
                                ("bilateralCerebellum", ("leftCerebellum", "rightCerebellum"))):
        for stat, counts in metrics["sampled_bilateral_averages"][region].items():
            bilateral, left, right = (number(read(extraction(root, sub, acq, roi, stat)).strip())
                                      for roi in (region, *hemispheres))
            if all(math.isfinite(value) for value in (bilateral, left, right)):
                label = "matches" if math.isclose(bilateral, (left + right) / 2,
                                                  rel_tol=5e-6, abs_tol=1e-6) else "differs"
                counts[label] += 1
            else:
                counts["unavailable"] += 1


def voxels(image, *args):
    result = fsl("fslstats", image, *args, "-V").split()
    return int(result[0]) if result and result[0].isdigit() else None


@lru_cache(maxsize=None)
def group_model(root, directory):
    """Return a model category from actual FEAT input references when available."""
    referenced = set()
    for ancestor in (directory, *directory.parents):
        if ancestor == root:
            break
        for source in FEAT_INPUT.findall(read(ancestor / "design.fsf")):
            referenced.update(MODEL.findall(source))
        if referenced:
            return "input_model_" + "_and_".join(sorted(referenced))
    named = MODEL.findall(str(directory.relative_to(root)))
    return "directory_model_" + "_and_".join(sorted(set(named))) if named else "unknown_model"


def mask_lineage(root):
    masks = {roi: root / "masks" / f"mask_{roi}.nii.gz" for roi in MASK_ROIS}
    counts = {roi: voxels(mask) if mask.is_file() else None for roi, mask in masks.items()}
    results = {roi: {"mask_present": path.is_file(), "exact_matches": Counter(), "same_grid_candidates": 0}
               for roi, path in masks.items()}
    scanned = 0
    for group_root in sorted((root / "derivatives").glob("fsl*")):
        if not group_root.is_dir():
            continue
        for folder, dirs, files in os.walk(group_root):
            dirs[:] = [name for name in dirs if not name.startswith(("sub-", ".")) and
                       name not in {"logs", "reg", "reg_standard", "stats", "tsplot", "mc"}]
            directory = Path(folder)
            for name in files:
                if not re.fullmatch(r"(?:cluster_mask|cluster_index)_zstat\d+\.nii(?:\.gz)?", name):
                    continue
                candidate = directory / name
                scanned += 1
                for roi, mask in masks.items():
                    if not counts[roi] or not same_grid(candidate, mask):
                        continue
                    results[roi]["same_grid_candidates"] += 1
                    bounds = fsl("fslstats", candidate, "-k", mask, "-R").split()
                    if len(bounds) != 2:
                        continue
                    low, high = map(number, bounds)
                    if low == high and low > 0 and low.is_integer() and voxels(
                        candidate, "-l", low - 0.5, "-u", low + 0.5
                    ) == counts[roi]:
                        results[roi]["exact_matches"][group_model(root, directory)] += 1
    left, right, bilateral = (masks[r] for r in MASK_ROIS)
    union = None
    if all(counts.values()) and same_grid(left, right) and same_grid(left, bilateral):
        shared = voxels(left, "-k", right)
        in_bilateral = (voxels(left, "-k", bilateral), voxels(right, "-k", bilateral))
        if shared is not None and None not in in_bilateral:
            union = (in_bilateral == (counts["leftMotor"], counts["rightMotor"]) and
                     counts["bilateralMotor"] == counts["leftMotor"] + counts["rightMotor"] - shared)
    return {"group_cluster_images_scanned": scanned, "bilateral_mask_matches_unilateral_union": union,
            "roi_masks": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/ZPOOL/data/projects/multiecho-pilot"))
    root = parser.parse_args().root.resolve()
    if not (root / "derivatives/fsl").is_dir():
        parser.error("Project FEAT directory unavailable.")
    for tool in ("fslhd", "fslstats", "fslmeants"):
        if not shutil.which(tool):
            parser.error(f"Load the existing FSL environment. Missing {tool}.")
    included = {re.sub("^sub-", "", sub) for sub in read(root / "code/sublist-included.txt").split()}
    included = sorted(sub for sub in included if all(
        extraction(root, sub, acq, "bilateralMotor").is_file() for acq in ACQUISITIONS))
    if not included:
        parser.error("No complete bilateral motor extraction sets found in the project subject list.")
    sample = set()
    for coil in (20, 64):
        members = {re.sub("^sub-", "", sub) for sub in read(root / f"code/sublist-{coil}ch.txt").split()}
        pool = [sub for sub in included if sub in members]
        start = max(0, (len(pool) - 2) // 2)
        sample.update(pool[start:start+2])
    result = {"complete_motor_extraction_sets": len(included), "sampled_for_image_checks": len(sample),
              "by_protocol": {}, "figure_2c_mask_candidates": mask_lineage(root)}
    for acq in ACQUISITIONS:
        metrics = {"model_2": Counter(), "model_4": Counter(), "reuse": Counter(),
                   "sampled_extraction_checks": {roi: {stat: Counter() for stat in STAT_FILES} for roi in ROIS},
                   "sampled_bilateral_averages": {roi: {stat: Counter() for stat in STAT_FILES}
                                                  for roi in ("bilateralMotor", "bilateralCerebellum")}}
        for sub in included:
            inspect_pair(root, sub, acq, metrics, sub in sample)
        result["by_protocol"][acq] = metrics
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

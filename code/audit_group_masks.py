"""Inspect saved FSL masks, AFNI history and outputs, and randomise provenance."""
from collections import Counter
from functools import lru_cache
import html
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

import nibabel as nib
from nibabel.processing import resample_from_to
import numpy as np

from audit_motor_repair import FEAT_INPUT, read


PRIMARY_EFFECTS = ("act-cope13", "ppi-cope17", "ppi-cope13", "act-zstat13",
                   "ppi-zstat17", "ppi-zstat13", "tsnr")


@lru_cache(maxsize=8)
def values(path, shape, affine, brick=None):
    image = nib.load(path)
    data = image.dataobj
    if len(image.shape) == 4:
        if brick is None and image.shape[3] != 1:
            raise ValueError("Expected a 3D mask or statistic")
        data = data[..., 0 if brick is None else brick]
    if np.shape(data) != shape or not np.allclose(image.affine, affine, atol=.001, rtol=0):
        image = resample_from_to(nib.Nifti1Image(np.asarray(data, dtype=np.float32), image.affine),
                                 (shape, affine), order=0)
        return image.get_fdata(dtype=np.float32)
    return np.asarray(data, dtype=np.float32)


def array(path, reference, brick=None):
    # numpy arrays are unhashable. Use a compact immutable affine key.
    affine = tuple(map(tuple, reference.affine))
    return values(path, reference.shape[:3], affine, brick)


def mask(path, reference):
    data = array(path, reference)
    return np.isfinite(data) & (data > .5)


def standard_feat_mask(path):
    standard = path / "reg_standard/mask.nii.gz"
    return standard if standard.is_file() else path / "mask.nii.gz"


def mask_grid_matches(path, reference_path):
    image = nib.as_closest_canonical(nib.load(path))
    reference = nib.as_closest_canonical(nib.load(reference_path))
    return image.shape[:3] == reference.shape[:3] and np.allclose(
        image.affine, reference.affine, atol=.001, rtol=0)


def describe(footprint, reference_mask, rois):
    return {
        "voxels": int(footprint.sum()),
        "inside_reference": int((footprint & reference_mask).sum()),
        "outside_reference": int((footprint & ~reference_mask).sum()),
        "reference_omitted": int((reference_mask & ~footprint).sum()),
        "roi_fraction": {name: round(float(footprint[roi].mean()), 5)
                         for name, roi in rois.items()},
        "roi_outside_reference_fraction": {
            name: round(float((footprint & ~reference_mask)[roi].mean()), 5)
            for name, roi in rois.items()
        },
    }


def tree(root, exclude_subjects=True):
    if root.is_dir():
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and
                            (not exclude_subjects or not d.startswith("sub-")) and
                            d not in {"tsplot", "mc", "reg", "reg_standard"})
            yield Path(directory), set(files)


def safe_location(root, path):
    value = str(path.relative_to(root))
    # Group names can include participant identifiers in local directory names.
    return re.sub(r"(?i)sub-[a-z0-9]+|(?<!\d)\d{5,}(?!\d)", "[redacted]", value)


def relocate(root, directory, value):
    path = Path(value)
    candidates = [path] if path.is_absolute() else [directory / path, root / path, root / "code" / path]
    if "/multiecho-pilot/" in value:
        candidates.append(root / value.split("/multiecho-pilot/", 1)[-1])
    return next((p for p in candidates if p.exists()), None)


def feat_inputs(root, directory):
    config = read(directory / "design.fsf")
    source = FEAT_INPUT.findall(config)
    return source, [relocate(root, directory, name.strip()) for name in source]


def input_feat_masks(inputs, contrast):
    for path in inputs:
        if path and path.is_file() and path.parent.name == "stats":
            path = path.parent.parent
        if not path or not path.is_dir():
            yield None
            continue
        if path.name.endswith(".gfeat"):
            yield path / f"cope{contrast}.feat" / "mask.nii.gz"
            continue
        yield standard_feat_mask(path)


def compare_feat(root, directory, reference, rois, common, subjects):
    source, inputs = feat_inputs(root, directory)
    result = {"location": safe_location(root, directory), "design_inputs": len(source)}
    if directory.name.endswith(".gfeat"):
        contrasts = sorted(directory.glob("cope*.feat/mask.nii.gz"))
    else:
        contrasts = [directory / "mask.nii.gz"]
    contrast_in_design = re.search(r"set fmri\(inputtype\)\s+([12])", read(directory / "design.fsf"))
    result["contrasts"] = {}
    result["design_input_type"] = int(contrast_in_design[1]) if contrast_in_design else None
    log_dirs = [directory, *(saved.parent for saved in contrasts)]
    mask_commands = "\n".join(
        read(folder / name) for folder in dict.fromkeys(log_dirs)
        for name in ("report_log.html", ".flame"))
    result["log_records_mask_intersection"] = bool(re.search(r"-Tmin\s+mask", mask_commands))
    result["log_records_flame_mask"] = bool(re.search(
        r"flameo[^\n]*--mask(?:=|\s+)(?:\S*/)?mask\b", mask_commands))
    for saved in contrasts:
        if not saved.is_file():
            continue
        target = mask(saved, reference)
        result["contrasts"][saved.parent.name] = describe(target, common, rois)
    if source:
        # For L2, all contrasts share the same incoming first-level masks.
        source_subjects = {
            int(match[1]) for name in source if (match := re.search(r"(?:^|/)sub-(\d+)/", name))
        }
        result["subjects_in_design"] = len(source_subjects)
        result["primary_subjects_in_design"] = len(source_subjects & {int(s) for s in subjects})
        for saved in contrasts:
            if not saved.is_file():
                continue
            match = re.fullmatch(r"cope(\d+)\.feat", saved.parent.name)
            possible = list(input_feat_masks(inputs, int(match[1]) if match else 1))
            row = result["contrasts"][saved.parent.name]
            row["input_masks_found"] = sum(path is not None and path.is_file() for path in possible)
            row["input_masks_on_saved_group_grid"] = sum(
                path is not None and path.is_file() and mask_grid_matches(path, saved)
                for path in possible)
            if row["input_masks_on_saved_group_grid"] == len(source):
                group_grid = nib.load(saved)
                intersection = np.ones(group_grid.shape[:3], dtype=bool)
                for path in possible:
                    intersection &= mask(path, group_grid)
                observed = mask(saved, group_grid)
                row["against_input_mask_intersection"] = {
                    "outside_reference": int((observed & ~intersection).sum()),
                    "reference_omitted": int((intersection & ~observed).sum()),
                }
    return result


def fsl_group_results(root, subjects, reference, rois, common):
    fsl = root / "derivatives/fsl"
    report = {"second_level": {}, "third_level": []}
    for model, kind in ((1, "act"), (1, "ppi"), (2, "act"), (3, "act")):
        summary = Counter()
        overlap = Counter()
        for subject in subjects:
            paths = sorted((fsl / f"sub-{subject}").glob(
                f"L2_task-sharedreward_model-{model}_type-{kind}*_sm-0_denoising-base.gfeat"))
            if len(paths) != 1:
                summary["missing_or_ambiguous"] += 1
                continue
            directory = paths[0]
            summary["directories"] += 1
            source, inputs = feat_inputs(root, directory)
            first = list(input_feat_masks(inputs, 1))
            saved = directory / "mask.nii.gz"
            if not saved.is_file():
                saved = directory / ("cope13.feat" if model == 1 else "cope3.feat") / "mask.nii.gz"
            if not saved.is_file() or not source or not all(p and p.is_file() for p in first):
                summary["incomplete_mask_provenance"] += 1
                continue
            if not all(mask_grid_matches(path, saved) for path in first):
                summary["saved_input_grids_differ"] += 1
                continue
            group_grid = nib.load(saved)
            expected = np.ones(group_grid.shape[:3], dtype=bool)
            for path in first:
                expected &= mask(path, group_grid)
            observed = mask(saved, group_grid)
            summary["compared"] += 1
            summary["matches_all_input_masks"] += int(np.array_equal(observed, expected))
            overlap["included_outside_input_intersection"] += int((observed & ~expected).sum())
            overlap["intersection_excluded"] += int((expected & ~observed).sum())
        report["second_level"][f"model{model}_{kind}"] = {"counts": dict(summary), "voxel_sums": dict(overlap)}

    for base in sorted((root / "derivatives").glob("fsl*")):
        for directory, files in tree(base):
            if not directory.name.startswith("L3_") or not directory.name.endswith(".gfeat"):
                continue
            if not re.search(r"cnum-(?:03|11|12|13|17)_", directory.name):
                continue
            report["third_level"].append(compare_feat(root, directory, reference, rois, common, subjects))
    return report


def afni_history(path):
    info = shutil.which("3dinfo")
    if info:
        result = subprocess.run([info, "-history", str(path)], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    return read(path) if path.suffix == ".HEAD" else ""


def command_option(history, program, option):
    lines = [line for line in history.replace("\\\n", " ").splitlines() if program in line]
    expression = r"(?:^|\s)" + re.escape(option) + r"(?:=|\s+)[\"']?([^\s\"'\\]+)"
    options = [match.group(1) for line in lines if (match := re.search(expression, line))]
    return options[-1] if options else None


def command_working_dir(root, directory, option, history, program):
    """Resolve a saved command path without returning the command or its absolute path."""
    if not option:
        return None
    bases = [directory]
    for line in history.splitlines():
        if program in line and (match := re.search(r"(?:^|\s)cd\s+([^;&]+)", line)):
            try:
                cwd = shlex.split(match[1])
            except ValueError:
                continue
            if len(cwd) == 1 and (local := relocate(root, directory, cwd[0])) and local.is_dir():
                bases.insert(0, local)
    for base in bases:
        for name in (option, option + ".nii.gz"):
            if resolved := relocate(root, base, name):
                return resolved
    return None


def afni_input_coverage(root, table, reference, subjects):
    counts = Counter()
    runs_by_subject = Counter()
    complete = np.ones(reference.shape[:3], dtype=bool)
    missing_filled_zero = np.zeros(reference.shape[:3], dtype=bool)
    missing_filled_nonzero = np.zeros(reference.shape[:3], dtype=bool)
    for line in read(table).splitlines():
        cells = line.strip().rstrip("\\").split()
        if not cells or cells[0] in {"Subj", "subject"} or cells[0].startswith("#"):
            continue
        counts["rows"] += 1
        name = cells[-1].strip("\"'")
        subject = re.search(r"(?:^|/)sub-(\d+)/", name)
        if subject:
            runs_by_subject[int(subject[1])] += 1
        input_path = relocate(root, table.parent, name)
        if not input_path or not input_path.is_file():
            counts["missing_input_file"] += 1
            continue
        source = input_path.parent.parent if input_path.parent.name == "stats" else input_path.parent
        feat_mask = source / "mask.nii.gz"
        if not feat_mask.is_file():
            counts["missing_input_mask"] += 1
            continue
        support = mask(feat_mask, reference)
        data = array(input_path, reference)
        complete &= support & np.isfinite(data)
        missing_filled_zero |= ~support & (data == 0)
        missing_filled_nonzero |= ~support & np.isfinite(data) & (data != 0)
        counts["checked"] += 1
    counts["subjects_in_input_paths"] = len(runs_by_subject)
    counts["primary_subjects_in_input_paths"] = len(runs_by_subject.keys() & {int(s) for s in subjects})
    counts["subjects_with_six_rows"] = sum(n == 6 for n in runs_by_subject.values())
    if not counts["checked"] or counts["checked"] != counts["rows"]:
        return dict(counts), None, None, None
    return dict(counts), complete, missing_filled_zero, missing_filled_nonzero


def afni_results(root, reference, rois, common, subjects):
    fsl = root / "derivatives/fsl"
    result = {}
    for effect in PRIMARY_EFFECTS:
        pattern = f"LME_output_{effect}"
        candidates = [p for base in (fsl, root / "code", root)
                      for ending in ("+tlrc.HEAD", ".nii.gz", ".nii")
                      if (p := base / f"{pattern}{ending}").is_file()]
        if not candidates:
            result[effect] = {"status": "unavailable"}
            continue
        output = candidates[0]
        history = afni_history(output)
        fit_mask = command_option(history, "3dLMEr", "-mask")
        table_name = command_option(history, "3dLMEr", "-dataTable")
        table = (relocate(root, output.parent, table_name.lstrip("@")) if table_name else None)
        if not table:
            table = next((p for base in (fsl, root / "code", root)
                          if (p := base / f"LME_table_corrected_{effect}.txt").is_file()), None)
        analysis = {
            "location": safe_location(root, output),
            "history_has_3dLMEr": "3dLMEr" in history,
            "history_has_fit_mask": bool(fit_mask) if "3dLMEr" in history else None,
            "history_has_bounds": bool(command_option(history, "3dLMEr", "-bounds"))
            if "3dLMEr" in history else None,
        }
        footprint = np.zeros(reference.shape[:3], dtype=bool)
        image = nib.load(output)
        for brick in range(image.shape[3] if len(image.shape) > 3 else 1):
            data = array(output, reference, brick)
            footprint |= np.isfinite(data) & (data != 0)
        analysis["nonzero_output_footprint_vs_primary_mask_intersection"] = describe(footprint, common, rois)
        cluster = next((p for base in (output.parent, fsl, root / "code", root)
                        if (p := base / "brain_mask.nii.gz").is_file()), None)
        for label, candidate in (("fit_mask", command_working_dir(root, output.parent, fit_mask,
                                                                history, "3dLMEr")),
                                 ("cluster_simulation_mask_candidate", cluster)):
            if candidate:
                support = mask(candidate, reference)
                analysis[label] = {
                    "location": safe_location(root, candidate),
                    "vs_primary_mask_intersection": describe(support, common, rois),
                    "nonzero_output_outside_mask": int((footprint & ~support).sum()),
                }
        if table:
            counts, full, zero_fill, nonzero_fill = afni_input_coverage(root, table, reference, subjects)
            analysis["input_table_mask_checks"] = counts
            if full is not None:
                analysis["nonzero_output_vs_actual_input_intersection"] = describe(footprint, full, rois)
                analysis["nonzero_output_with_masked_zero_input"] = int((footprint & zero_fill).sum())
                analysis["nonzero_output_with_masked_nonzero_input"] = int((footprint & nonzero_fill).sum())
        analysis["input_table_resolved"] = bool(table)
        result[effect] = analysis
    return result


def randomise_results(root, reference, rois, common):
    result = []
    bases = (root / "randomise", root / "derivatives/randomise",
             *(p for p in sorted((root / "derivatives").glob("fsl*")) if p.is_dir()))
    for base in bases:
        for directory, files in tree(base):
            outputs = sorted(f for f in files if re.search(r"(?:tfce_corrp_tstat|vox_corrp_tstat)\d+\.nii", f))
            if not outputs or directory.name == "stats":
                continue
            logs = []
            for name in sorted(files):
                if re.search(r"\.log$|^\.flame$|^report_log\.html$|^command.*\.txt$", name):
                    logs.append(html.unescape(re.sub(r"<[^>]*>", " ", read(directory / name))))
            history = "\n".join([*logs, afni_history(directory / outputs[0])])
            option = command_option(history, "randomise", "-m")
            input_option = command_option(history, "randomise", "-i")
            chosen = command_working_dir(root, directory, option, history, "randomise")
            row = {
                "location": safe_location(root, directory),
                "corrected_output_count": len(outputs),
                "mask_in_logged_command": bool(option),
            }
            source = command_working_dir(root, directory, input_option, history, "randomise")
            if chosen:
                support = mask(chosen, reference)
                row["logged_mask"] = {
                    "location": safe_location(root, chosen),
                    "vs_primary_mask_intersection": describe(support, common, rois),
                }
                if source and len(nib.load(source).shape) == 4:
                    data = nib.load(source)
                    # Zero-valued contrast/difference estimates may be valid. This
                    # is a value footprint, not an estimate of voxelwise coverage.
                    nonzero_all = np.ones(reference.shape[:3], dtype=bool)
                    for brick in range(data.shape[3]):
                        volume = array(source, reference, brick)
                        nonzero_all &= np.isfinite(volume) & (volume != 0)
                    row["logged_mask_vs_all_nonzero_input_values"] = describe(support, nonzero_all, rois)
                    row["input_volumes"] = int(data.shape[3])
            elif (directory / "mask.nii.gz").is_file():
                row["nearby_mask_candidate"] = describe(mask(directory / "mask.nii.gz", reference),
                                                        common, rois)
            design = directory / "design.mat"
            if design.is_file() and (m := re.search(r"/NumPoints\s+(\d+)", read(design))):
                row["design_observations"] = int(m[1])
            result.append(row)
    return result


def audit_groups(root, subjects, reference, rois, common):
    return {
        "fsl_feat": fsl_group_results(root, subjects, reference, rois, common),
        "afni_3dLMEr": afni_results(root, reference, rois, common, subjects),
        "fsl_randomise": randomise_results(root, reference, rois, common),
    }

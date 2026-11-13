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

from audit_motor_repair import ACQUISITIONS, FEAT_INPUT, read


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
    try:
        value = str(path.relative_to(root))
    except ValueError:
        value = "external_archive/" + path.name
    # Group names can include participant identifiers in local directory names.
    return re.sub(r"(?i)sub-[a-z0-9]+|(?<!\d)\d{5,}(?!\d)", "[redacted]", value)


def relocate(root, directory, value):
    path = Path(value)
    candidates = [path] if path.is_absolute() else [directory / path, root / path, root / "code" / path]
    if "/multiecho-pilot/" in value:
        candidates.append(root / value.split("/multiecho-pilot/", 1)[-1])
    return next((Path(os.path.abspath(p)) for p in candidates if p.exists()), None)


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
    if path.suffix == ".HEAD":
        return read(path)
    try:
        image = nib.load(path)
        chunks = []
        for extension in getattr(image.header, "extensions", []):
            if extension.get_code() == 4:
                chunks.append(bytes(extension.content).decode(errors="replace"))
        return "\n".join(chunks)
    except (OSError, ValueError, nib.filebasedimages.ImageFileError):
        return ""


def command_option(history, program, option):
    lines = [line for line in history.replace("\\\n", " ").splitlines()
             if re.search(r"(?:^|[\s/])" + re.escape(program) + r"(?=\s)", line)]
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
        for name in (option, option + ".nii.gz", option + ".nii", option + ".HEAD"):
            if resolved := relocate(root, base, name):
                return resolved
    return None


def afni_input_coverage(root, table, reference, subjects):
    counts = Counter()
    runs_by_subject = Counter()
    complete = np.ones(reference.shape[:3], dtype=bool)
    missing_filled_zero = np.zeros(reference.shape[:3], dtype=bool)
    missing_filled_nonzero = np.zeros(reference.shape[:3], dtype=bool)
    input_column = None
    for line in read(table).splitlines():
        line = line.strip().rstrip("\\").strip()
        if not line or line.startswith("#"):
            continue
        try:
            cells = shlex.split(line)
        except ValueError:
            counts["rows"] += 1
            counts["unparsed_input_row"] += 1
            continue
        if "InputFile" in cells:
            input_column = cells.index("InputFile")
            continue
        counts["rows"] += 1
        if input_column is None or len(cells) <= input_column:
            counts["unparsed_input_row"] += 1
            continue
        name, _, selector = cells[input_column].partition("[")
        if selector and not re.fullmatch(r"\d+\]", selector):
            counts["unsupported_subbrick_selector"] += 1
            continue
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
        if not mask_grid_matches(feat_mask, input_path):
            counts["input_and_mask_grid_mismatch"] += 1
            continue
        data = array(input_path, reference, int(selector[:-1]) if selector else None)
        complete &= support & np.isfinite(data)
        missing_filled_zero |= ~support & (data == 0)
        missing_filled_nonzero |= ~support & np.isfinite(data) & (data != 0)
        counts["checked"] += 1
    counts["subjects_in_input_paths"] = len(runs_by_subject)
    counts["primary_subjects_in_input_paths"] = len(runs_by_subject.keys() & {int(s) for s in subjects})
    counts["subjects_with_six_rows"] = sum(n == 6 for n in runs_by_subject.values())
    return dict(counts), complete, missing_filled_zero, missing_filled_nonzero


def afni_results(root, reference, rois, common, subjects, archive=None):
    fsl = root / "derivatives/fsl"
    result = {}
    for effect in PRIMARY_EFFECTS:
        pattern = f"LME_output_{effect}"
        candidates = [p for base in (fsl, root / "code", root)
                      for ending in ("+tlrc.HEAD", "+orig.HEAD", ".nii.gz", ".nii")
                      if (p := base / f"{pattern}{ending}").is_file()]
        if archive is not None:
            candidates = list(dict.fromkeys([*candidates, *archive["afni"].get(effect, [])]))
        if not candidates:
            result[effect] = {"status": "unavailable"}
            continue
        rows = [describe_afni(root, output, effect, reference, rois, common, subjects, archive)
                for output in candidates]
        result[effect] = rows[0] if len(rows) == 1 else {"saved_outputs": rows}
    return result


def describe_afni(root, output, effect, reference, rois, common, subjects, archive):
    fsl = root / "derivatives/fsl"
    history = afni_history(output)
    fit_mask = command_option(history, "3dLMEr", "-mask")
    table_name = command_option(history, "3dLMEr", "-dataTable")
    if table_name:
        table_name = table_name.lstrip("@")
    table = command_working_dir(root, output.parent, table_name, history, "3dLMEr")
    table_source = ("recorded_command" if table else "matching_filename_without_command_confirmation")
    table_basename = Path(table_name or f"LME_table_corrected_{effect}.txt").name
    if not table:
        table = next((p for base in (output.parent, fsl, root / "code", root)
                      if (p := base / table_basename).is_file()), None)
    if not table and archive is not None:
        possibilities = archive["tables"].get(table_basename, [])
        if len(possibilities) == 1:
            table = possibilities[0]
    analysis = {
        "location": safe_location(root, output),
        "history_has_3dLMEr": "3dLMEr" in history,
        "history_has_fit_mask": bool(fit_mask) if "3dLMEr" in history else None,
        "history_has_bounds": bool(command_option(history, "3dLMEr", "-bounds"))
        if "3dLMEr" in history else None,
    }
    footprint = np.zeros(reference.shape[:3], dtype=bool)
    try:
        image = nib.load(output)
        for brick in range(image.shape[3] if len(image.shape) > 3 else 1):
            data = array(output, reference, brick)
            footprint |= ~np.isnan(data) & (data != 0)
    except (OSError, nib.filebasedimages.ImageFileError):
        analysis["status"] = "header_or_image_unreadable"
        return analysis
    analysis["nonzero_output_footprint_vs_primary_mask_intersection"] = describe(footprint, common, rois)
    cluster = next((p for base in (output.parent, fsl, root / "code", root)
                    for name in ("brain_mask.nii.gz", "brain_mask.nii")
                    if (p := base / name).is_file()), None)
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
        analysis["input_table_source"] = table_source
        if counts.get("checked"):
            if counts["checked"] == counts["rows"]:
                analysis["nonzero_output_vs_actual_input_intersection"] = describe(footprint, full, rois)
            else:
                analysis["nonzero_output_outside_checked_input_intersection"] = int((footprint & ~full).sum())
            analysis["nonzero_output_with_masked_zero_input"] = int((footprint & zero_fill).sum())
            analysis["nonzero_output_with_masked_nonzero_input"] = int((footprint & nonzero_fill).sum())
    analysis["input_table_resolved"] = bool(table)
    return analysis


def randomise_results(root, reference, rois, common, saved_directories=None):
    result = []
    bases = (root / "randomise", root / "derivatives/randomise",
             *(p for p in sorted((root / "derivatives").glob("fsl*")) if p.is_dir()))
    directories = (saved_directories.items() if saved_directories is not None else
                   (entry for base in bases for entry in tree(base)))
    for directory, files in directories:
        outputs = sorted(f for f in files if re.search(r"(?:tfce_corrp_tstat|vox_corrp_tstat|clustere_corrp_tstat)\d+\.nii", f))
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


def discover_saved_outputs(root, extra_roots):
    archive = {"afni": {}, "tables": {}, "randomise": {}, "ppi_clusters": [], "brain_masks": []}
    seen = set()
    for start in (root, *extra_roots):
        for directory, files in tree(start):
            canonical = directory.resolve()
            if canonical in seen:
                continue
            seen.add(canonical)
            for filename in sorted(files):
                path = directory / filename
                if filename in {"brain_mask.nii", "brain_mask.nii.gz"}:
                    archive["brain_masks"].append(path)
                if re.fullmatch(r"(?:mask_)?MBxME_ppi_zstat17_thresh(?:\+(?:tlrc|orig)\.HEAD|\.nii(?:\.gz)?)",
                                filename, re.I):
                    archive["ppi_clusters"].append(path)
                m = re.fullmatch(r"LME_output_([a-z0-9-]+)(?:\+(?:tlrc|orig))?(?:\.HEAD|\.nii(?:\.gz)?)",
                                 filename, re.I)
                if m and m[1] in PRIMARY_EFFECTS:
                    archive["afni"].setdefault(m[1], []).append(path)
                if re.fullmatch(r"LME_table[\w-]*\.(?:txt|tsv)", filename, re.I):
                    archive["tables"].setdefault(filename, []).append(path)
                if re.search(r"(?:tfce_corrp_tstat|vox_corrp_tstat|clustere_corrp_tstat)\d+\.nii", filename):
                    archive["randomise"][directory] = files
    return archive


def cluster_footprint(root, cluster, reference, rois, common, ppi_common):
    footprint = np.zeros(reference.shape[:3], dtype=bool)
    img = nib.load(cluster)
    for brick in range(img.shape[3] if len(img.shape) == 4 else 1):
        data = array(cluster, reference, brick)
        footprint |= np.isfinite(data) & (data != 0)
    result = {"location": safe_location(root, cluster),
              "against_primary_activation_common_mask": describe(footprint, common, rois)}
    if ppi_common is not None:
        result["against_primary_ppi_common_mask"] = describe(footprint, ppi_common, rois)
    return result


def primary_ppi_intersection(root, reference, subjects):
    intersection = np.ones(reference.shape[:3], dtype=bool)
    found = 0
    for subject in subjects:
        for acquisition in ACQUISITIONS:
            feat = root / "derivatives/fsl" / f"sub-{subject}" / (
                f"L1_task-sharedreward_model-1_type-ppi_seed-VS_thr5_acq-{acquisition}_sm-0_denoising-base.feat")
            support = feat / "mask.nii.gz"
            if support.is_file():
                intersection &= mask(support, reference)
                found += 1
    expected = len(subjects) * len(ACQUISITIONS)
    return found, intersection if found == expected else None


def follow_up(root, reference, rois, common, subjects, extra_roots):
    archive = discover_saved_outputs(root, extra_roots)
    ppi_found, ppi_common = primary_ppi_intersection(root, reference, subjects)
    ppi_coverage = {"found": ppi_found, "expected": len(subjects) * len(ACQUISITIONS)}
    if ppi_common is not None:
        ppi_coverage["against_primary_activation_common_mask"] = describe(ppi_common, common, rois)
    return {
        "afni_3dLMEr": afni_results(root, reference, rois, common, subjects, archive),
        "primary_ppi_masks": ppi_coverage,
        "saved_figure7_cluster_candidates": [
            cluster_footprint(root, path, reference, rois, common, ppi_common)
            for path in archive["ppi_clusters"] if readable_image(path)],
        "cluster_simulation_mask_candidates": [
            {"location": safe_location(root, path),
             "against_primary_activation_common_mask": describe(mask(path, reference), common, rois)}
            for path in archive["brain_masks"] if readable_image(path)],
        "fsl_randomise": randomise_results(root, reference, rois, common, archive["randomise"]),
    }


def readable_image(path):
    try:
        nib.load(path)
    except (OSError, nib.filebasedimages.ImageFileError):
        return False
    return True


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--coverage-run", type=Path, required=True)
    parser.add_argument("--search-dir", type=Path, action="append", default=[])
    parser.add_argument("--fsldir", type=Path, default=Path(os.environ.get("FSLDIR", "/usr/local/fsl")))
    args = parser.parse_args()
    from audit_coverage import roi_masks
    from reextract_motor_model2 import manuscript_subjects

    root = args.root.resolve()
    reference = nib.load(args.coverage_run / "all_acquisitions_all_38_intersection.nii.gz")
    rois, _ = roi_masks(args.fsldir, reference)
    common = mask(args.coverage_run / "all_acquisitions_all_38_intersection.nii.gz", reference)
    subjects = manuscript_subjects(root)
    if len(subjects) != 38:
        parser.error("Expected the same 38 primary participants.")
    report = follow_up(root, reference, rois, common, subjects,
                       [path.resolve() for path in args.search_dir])
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

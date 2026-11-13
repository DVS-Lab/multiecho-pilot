#!/usr/bin/env python3
"""Read existing FEAT and echo images and create aggregate acquisition coverage maps."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import nibabel as nib
from nibabel.processing import resample_from_to
import numpy as np
import pandas as pd

from audit_motor_repair import ACQUISITIONS, FEAT_INPUT
from reextract_motor_model2 import manuscript_subjects
from audit_group_masks import audit_groups


THRESHOLDS = (25, 50, 75)
SPACE = "MNI152NLin6Asym"
ALL_COILS = "all", "20ch", "64ch"
ECHOES = "early", "late", "combined"


class Unavailable(ValueError):
    """A missing, ambiguous, or incompatible input."""


def same_grid(image, reference):
    return image.shape[:3] == reference.shape[:3] and np.allclose(
        image.affine, reference.affine, atol=.001, rtol=0)


def load(path):
    if not path or not path.is_file():
        raise Unavailable("missing_image")
    return nib.load(path)


def align(image, reference, order):
    if not same_grid(image, reference):
        image = resample_from_to(image, (reference.shape[:3], reference.affine), order=order)
    return image.get_fdata(dtype=np.float32)


def echo_time_ms(path, root, subject, acq, index):
    derivative = path.with_name(path.name.removesuffix(".nii.gz") + ".json")
    raw = (root / "bids" / f"sub-{subject}" / "func").glob(
        f"sub-{subject}_task-sharedreward_acq-{acq}_*echo-{index}*_bold.json")
    for sidecar in [derivative, *(p for p in raw if "_part-phase_" not in p.name)]:
        if sidecar.is_file():
            try:
                value = json.loads(sidecar.read_text()).get("EchoTime")
            except (ValueError, OSError):
                continue
            if isinstance(value, (int, float)) and 0 < value < 1:
                return round(1000 * value, 3)
    return None


def binary(image, reference):
    values = align(image, reference, 0)
    return np.isfinite(values) & (values > .5)


def on_grid(path, reference):
    image = load(path)
    image = nib.as_closest_canonical(image)
    if len(image.shape) != 3 or not same_grid(image, reference):
        raise Unavailable("unexpected_feat_grid")
    return image.get_fdata(dtype=np.float32)


def roi_masks(fsldir, reference):
    atlases = fsldir / "data/atlases"

    def harvard(kind, labels):
        label_xml = atlases / f"HarvardOxford-{'Cortical' if kind == 'cort' else 'Subcortical'}.xml"
        values = {node.text: int(node.attrib["index"]) + 1
                  for node in ElementTree.parse(label_xml).iter("label")}
        atlas = atlases / f"HarvardOxford/HarvardOxford-{kind}-maxprob-thr25-2mm.nii.gz"
        return np.isin(align(load(atlas), reference, 0), [values[label] for label in labels])

    cerebellar = atlases / "Cerebellum/Cerebellum-MNIfnirt-maxprob-thr25-2mm.nii.gz"
    rois = {
        "Orbitofrontal cortex": harvard("cort", ["Frontal Orbital Cortex"]),
        "Ventral striatum (accumbens)": harvard("sub", ["Left Accumbens", "Right Accumbens"]),
        "Anterior temporal cortex (temporal pole)": harvard("cort", ["Temporal Pole"]),
        "Cerebellum": binary(load(cerebellar), reference),
    }
    white = harvard("sub", ["Left Cerebral White Matter", "Right Cerebral White Matter"])
    if not all(mask.any() for mask in [white, *rois.values()]):
        raise Unavailable("empty_atlas_roi")
    return rois, white


def normalize(mask, signal, white):
    valid = mask & np.isfinite(signal) & (signal > 0)
    reference = valid & white
    if not reference.any():
        raise Unavailable("insufficient_normalization_roi")
    return valid, np.divide(signal, np.median(signal[reference]),
                            out=np.zeros_like(signal), where=valid)


class Coverage:
    def __init__(self, shape):
        self.n = 0
        self.mask_count = np.zeros(shape, dtype=np.int16)
        self.valid_count = np.zeros(shape, dtype=np.int16)
        self.signal_sum = np.zeros(shape, dtype=np.float64)
        self.retained = {limit: np.zeros(shape, dtype=np.int16) for limit in THRESHOLDS}

    def add(self, mask, signal, white):
        valid, scaled = normalize(mask, signal, white)
        self.n += 1
        self.mask_count += mask
        self.valid_count += valid
        self.signal_sum += scaled
        for limit, count in self.retained.items():
            count += valid & (scaled >= limit / 100)

    def intersection(self):
        return (self.mask_count == self.n) & (self.n > 0)

    def maps(self):
        if not self.n:
            return {}
        signal = np.divide(self.signal_sum, self.valid_count,
                           out=np.full(self.valid_count.shape, np.nan, dtype=np.float32),
                           where=self.valid_count > 0)
        return {
            "binary_fraction": self.mask_count.astype(np.float32) / self.n,
            "mask_participant_count": self.mask_count,
            "intersection": self.intersection(),
            "mean_normalized_signal": signal,
            "signal_participant_count": self.valid_count,
            "masked_or_invalid_fraction": 1 - self.valid_count.astype(np.float32) / self.n,
            "valid_below_50_fraction": (self.valid_count - self.retained[50]).astype(np.float32) / self.n,
            **{f"retained_{limit}": count.astype(np.float32) / self.n
               for limit, count in self.retained.items()},
        }


def select_bold_mask(func, image, fallback, reference):
    candidate = func / (image.name.split("_desc-")[0] + "_desc-brain_mask.nii.gz")
    return binary(load(candidate), reference) if candidate.is_file() else fallback


def save_map(directory, name, array, reference):
    array = array.astype(np.int16 if array.dtype.kind in "biu" else np.float32)
    nib.save(nib.Nifti1Image(array, reference.affine), directory / f"{name}.nii.gz")


def roi_summary(maps, rois):
    result = {}
    for name, mask in rois.items():
        row = {"atlas_voxels": int(mask.sum())}
        for metric, array in maps.items():
            values = array[mask]
            if metric == "mean_normalized_signal":
                values = values[np.isfinite(values)]
            row[metric] = round(float(values.mean()), 5) if values.size else None
        if "signal_participant_count" in maps:
            values = maps["signal_participant_count"][mask]
            row["minimum_signal_participants"] = int(values.min())
            row["maximum_signal_participants"] = int(values.max())
        result[name] = row
    return result


def feat_dir(root, subject, acq, model=1):
    return root / "derivatives/fsl" / f"sub-{subject}" / (
        f"L1_task-sharedreward_model-{model}_type-act_acq-{acq}_sm-0_denoising-base.feat")


def coil_groups(root, subjects):
    frame = pd.read_excel(root / "code/multiecho-pilot_Demographics.xlsx",
                          usecols=["Subject", "Headcoil"])
    frame = frame.assign(Subject=frame["Subject"].astype(str)).set_index("Subject")
    coils = {subject: f"{int(frame.loc[subject, 'Headcoil'])}ch" for subject in subjects}
    if Counter(coils.values()) != {"20ch": 16, "64ch": 22}:
        raise ValueError("The primary cohort must contain 16 and 22 participants by coil.")
    return coils


def temporal_mean(image):
    if len(image.shape) != 4 or image.shape[3] < 2:
        raise Unavailable("echo_not_a_time_series")
    values = image.get_fdata(dtype=np.float32, caching="unchanged")
    result = np.mean(values, axis=3, dtype=np.float64).astype(np.float32)
    return nib.Nifti1Image(result, image.affine)


def echo_triplet(root, subject, acq, reference, white, ants):
    """Pair echo 1 and echo 4 with the unsmoothed fMRIPrep combined image."""
    func = root / "derivatives/fmriprep" / f"sub-{subject}" / "func"
    files = sorted(func.glob(f"sub-{subject}_task-sharedreward_acq-{acq}_*_bold.nii.gz"))
    files = [path for path in files if "_part-phase_" not in path.name and "_part-phase." not in path.name]

    def find_echo(index, standard):
        candidates = [p for p in files if f"_echo-{index}_" in p.name
                      and p.name.endswith("_desc-preproc_bold.nii.gz")]
        return unique([p for p in candidates if (
            f"_space-{SPACE}_" in p.name if standard else
            "_space-" not in p.name or "_space-boldref_" in p.name
        )], "early_echo" if index == 1 else "late_echo")

    standard = [p for p in files if f"_space-{SPACE}_" in p.name and "_echo-" not in p.name]
    combined = unique([p for p in standard if p.name.endswith("_desc-preproc_bold.nii.gz")]
                      or [p for p in standard if p.name.endswith("_desc-optcom_bold.nii.gz")],
                      "standard_combined")
    prefix = combined.name.split("_desc-")[0]
    primary_mask = func / f"{prefix}_desc-brain_mask.nii.gz"
    common_mask = load(primary_mask if primary_mask.is_file() else unique([
        p for p in func.glob(f"sub-{subject}_task-sharedreward_acq-{acq}_*_desc-brain_mask.nii.gz")
        if f"_space-{SPACE}_" in p.name and "_echo-" not in p.name and "_part-phase_" not in p.name
    ], "standard_combined_mask"))
    standard_mask = binary(common_mask, reference)
    means = {"combined": (standard_mask, align(temporal_mean(load(combined)), reference, 1))}
    methods = {}
    for index, label in ((1, "early"), (4, "late")):
        try:
            path = find_echo(index, standard=True)
        except Unavailable as error:
            if str(error) != f"missing_{label}_echo":
                raise
            path = find_echo(index, standard=False)
            if not ants:
                raise Unavailable("native_echo_ants_unavailable") from error
            native = load(path)
            native_masks = [
                p for p in func.glob(f"sub-{subject}_task-sharedreward_acq-{acq}_*_mask.nii.gz")
                if ("_space-" not in p.name or "_space-boldref_" in p.name) and "_desc-brain_mask" in p.name
                and "_echo-" not in p.name and "_part-phase_" not in p.name
            ]
            native_masks = [mask for p in native_masks if same_grid(native, mask := load(p))]
            native_mask = (native_masks[0] if len(native_masks) == 1 else
                           nib.Nifti1Image(np.ones(native.shape[:3], dtype=np.uint8), native.affine))
            mean_image = temporal_mean(native)
            support, warped = project_native(root, subject, acq, native_mask, mean_image, reference, ants)
            means[label] = (standard_mask & support, warped)
            methods[label] = ("native_brain_mask" if len(native_masks) == 1 else "native_fov") + "_transformed"
        else:
            image = load(path)
            image_fov = nib.Nifti1Image(np.ones(image.shape[:3], dtype=np.uint8), image.affine)
            echo_mask = select_bold_mask(func, path, standard_mask, reference) & binary(image_fov, reference)
            means[label] = (echo_mask, align(temporal_mean(image), reference, 1))
            methods[label] = "saved_standard_echo"
        echo_time = echo_time_ms(path, root, subject, acq, index)
        if echo_time is not None:
            methods[f"{label}_echo_time"] = echo_time
    if all(f"{name}_echo_time" in methods for name in ("early", "late")):
        if methods["early_echo_time"] >= methods["late_echo_time"]:
            raise Unavailable("unexpected_echo_time_order")
    for mask, signal in means.values():
        normalize(mask, signal, white)
    return means, methods


def unique(paths, label):
    if len(paths) != 1:
        raise Unavailable(("missing_" if not paths else "ambiguous_") + label)
    return paths[0]


def project_native(root, subject, acq, native_mask, image, reference, ants):
    subdir = root / "derivatives/fmriprep" / f"sub-{subject}"
    stem = f"sub-{subject}_task-sharedreward_acq-{acq}_*"
    transforms = sorted((subdir / "func").glob(
        stem + "from-boldref_to-T1w_mode-image*xfm.txt"))
    if not transforms:
        transforms = sorted((subdir / "func").glob(
            stem + "from-scanner_to-T1w_mode-image*xfm.txt"))
    bold_to_t1 = unique(transforms, "bold_to_t1w_transform")
    t1_to_mni = unique(sorted((subdir / "anat").glob(
        f"sub-{subject}*_from-T1w_to-{SPACE}_mode-image_xfm.h5")), "t1w_to_mni_transform")
    with TemporaryDirectory(prefix="coverage_echo_") as tmp:
        tmp = Path(tmp)
        target = tmp / "reference.nii.gz"
        nib.save(nib.Nifti1Image(np.zeros(reference.shape[:3], dtype=np.uint8), reference.affine), target)
        source = tmp / "source.nii.gz"
        warped = tmp / "warped.nii.gz"
        results = []
        for data, interpolation in ((native_mask, "NearestNeighbor"), (image, "Linear")):
            nib.save(data, source)
            process = subprocess.run(
                [ants, "-d", "3", "-i", str(source), "-r", str(target), "-o", str(warped),
                 "-n", interpolation, "-t", str(t1_to_mni), "-t", str(bold_to_t1)],
                capture_output=True, check=False)
            if process.returncode or not warped.is_file():
                raise Unavailable("native_echo_transform_failed")
            results.append(on_grid(warped, reference))
    return results[0] > .5, results[1]


def make_slices(reference, rois):
    """Fixed MNI planes and identical world-coordinate extents within each ROI row."""
    inverse = np.linalg.inv(reference.affine)
    specs = [
        ("Orbitofrontal cortex", 1, 34, (-58, 58), (-36, 24)),
        ("Ventral striatum (accumbens)", 1, 10, (-48, 48), (-28, 32)),
        ("Anterior temporal cortex (temporal pole)", 2, -24, (-72, 72), (-38, 66)),
        ("Cerebellum", 1, -55, (-70, 70), (-78, 3)),
    ]
    for name, axis, requested, xlim, ylim in specs:
        world = np.zeros(3)
        world[axis] = requested
        index = int(np.rint(nib.affines.apply_affine(inverse, world)[axis]))
        if index < 0 or index >= reference.shape[axis]:
            raise ValueError(f"Reference does not cover {name} slice")
        other = 2 if axis == 1 else 1
        coordinates = np.zeros(3)
        coordinates[axis] = index
        actual = nib.affines.apply_affine(reference.affine, coordinates)[axis]
        yield name, axis, index, actual, xlim, ylim, other, rois[name]


def figure(columns, metrics, reference, background, rois, title):
    specs = list(make_slices(reference, rois))
    nrows = len(specs) * len(metrics)
    ncols = len(columns)
    fig, axes = plt.subplots(nrows, ncols, figsize=(1.45 * ncols + 2.05, 1.24 * nrows + .65),
                             squeeze=False, layout="constrained")
    fig.suptitle(title, fontsize=12, fontweight="bold")
    xyz = [reference.affine[d, d] * np.arange(reference.shape[d]) + reference.affine[d, 3]
           for d in range(3)]
    for band, (metric, label, cmap, vmax) in enumerate(metrics):
        last = None
        for r, (roi, axis, index, actual, xlim, ylim, other, boundary) in enumerate(specs):
            row = band * len(specs) + r
            extent = [xyz[0][0] - reference.affine[0, 0] / 2,
                      xyz[0][-1] + reference.affine[0, 0] / 2,
                      xyz[other][0] - reference.affine[other, other] / 2,
                      xyz[other][-1] + reference.affine[other, other] / 2]
            for c, (column, maps) in enumerate(columns):
                ax = axes[row, c]
                ax.imshow(np.take(background, index, axis=axis).T, extent=extent, origin="lower",
                          cmap="gray", vmin=0, vmax=7000, interpolation="nearest")
                if metric in maps:
                    layer = np.take(maps[metric], index, axis=axis).T
                    display = np.ma.masked_where(~np.isfinite(layer) | (layer == 0), layer)
                    last = ax.imshow(display, extent=extent, origin="lower", cmap=cmap, alpha=.87,
                                     vmin=0, vmax=vmax, interpolation="nearest")
                else:
                    ax.text(.5, .5, "Unavailable", color="white", ha="center", va="center",
                            transform=ax.transAxes, fontsize=7)
                outline = np.take(boundary, index, axis=axis).T
                if outline.any() and not outline.all():
                    ax.contour(xyz[0], xyz[other], outline, levels=[.5], colors=["#00d2cc"],
                               linewidths=.55)
                ax.set(xlim=xlim, ylim=ylim, xticks=[], yticks=[])
                if not row:
                    ax.set_title(column, fontsize=8)
                if not c:
                    short = roi.split(" (")[0]
                    ax.set_ylabel(f"{short}\n{'y' if axis == 1 else 'z'} = {actual:.1f} mm",
                                  fontsize=7, rotation=0, labelpad=42, va="center")
        if last is not None:
            bar = fig.colorbar(last, ax=axes[band*len(specs):(band+1)*len(specs), :], shrink=.62, pad=.02)
            bar.set_label(label, fontsize=8)
            bar.ax.tick_params(labelsize=7)
    return fig


METRICS = (
    ("binary_fraction", "Fraction in functional mask", "viridis", 1),
    ("intersection", "All participants covered", "viridis", 1),
    ("mean_normalized_signal", "Mean signal / WM median", "magma", 2),
    ("retained_50", "Fraction at ≥50% of WM median", "viridis", 1),
)


def run(args):
    root = args.root.resolve()
    subjects = manuscript_subjects(root)
    coils = coil_groups(root, subjects)
    if len(subjects) != 38:
        raise ValueError("The primary cohort must contain exactly 38 participants.")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fsldir = Path(args.fsldir)
    template = load(fsldir / "data/standard/MNI152_T1_2mm_brain.nii.gz")
    reference = nib.as_closest_canonical(template)
    # A fixed full template lattice counts ROI tissue even outside every functional FOV.
    if not np.allclose(reference.affine[:3, :3], np.diag(np.diag(reference.affine)[:3]), atol=.001):
        raise ValueError("The reference template lattice is oblique.")
    background = align(template, reference, 1)
    background *= 7000 / np.percentile(background[background > 0], 99)
    rois, white = roi_masks(fsldir, reference)
    report = {
        "subjects": len(subjects),
        "subjects_by_coil": dict(Counter(coils.values())),
        "reference_space": SPACE,
        "reference_lattice": "FSL MNI152 2 mm",
        "primary_resampling": "nearest neighbor from aligned MNI first-level FEAT images",
        "reference_shape": list(reference.shape),
        "voxel_volume_mm3": round(float(abs(np.linalg.det(reference.affine[:3, :3]))), 5),
        "threshold_percent_of_cerebral_white_matter_median": list(THRESHOLDS),
        "primary_input": "canonical model-1 activation FEAT mask.nii.gz and mean_func.nii.gz",
        "echo_input": "paired unsmoothed fMRIPrep echo 1, echo 4 and optimally combined BOLD",
        "fsl_version": (fsldir / "etc/fslversion").read_text().strip()
        if (fsldir / "etc/fslversion").is_file() else None,
        "primary_by_protocol": {},
        "mask_agreement_with_motor_and_ffa_models": {},
        "paired_echo_by_protocol": {},
    }
    primary, echo_panels, complete = {}, {}, {}
    for acq in ACQUISITIONS:
        cohorts = {coil: Coverage(reference.shape) for coil in ALL_COILS}
        paired = {mode: Coverage(reference.shape) for mode in ECHOES}
        echo_counts, echo_failures = Counter(), Counter()
        echo_times = {label: set() for label in ("early", "late")}
        model_support = {model: Counter() for model in (2, 3)}
        for subject in subjects:
            directory = feat_dir(root, subject, acq)
            mask_img, signal_img = (load(directory / name)
                                    for name in ("mask.nii.gz", "mean_func.nii.gz"))
            if not same_grid(mask_img, signal_img) or any(len(img.shape) != 3 for img in (mask_img, signal_img)):
                raise Unavailable("FEAT mean and mask lattices differ within a run")
            fsf = directory / "design.fsf"
            if fsf.is_file():
                values = FEAT_INPUT.findall(fsf.read_text())
                if values and "_space-" in values[0] and f"_space-{SPACE}_" not in values[0]:
                    raise Unavailable("primary FEAT input uses a different standard space")
            mask = binary(mask_img, reference)
            signal = align(signal_img, reference, 0)
            for model, counts in model_support.items():
                other = feat_dir(root, subject, acq, model) / "mask.nii.gz"
                if other.is_file():
                    other_mask = binary(load(other), reference)
                    counts["compared"] += 1
                    counts["identical"] += int(np.array_equal(other_mask, mask))
                    counts["voxels_in_model_1_only_summed_over_runs"] += int((mask & ~other_mask).sum())
                    counts[f"voxels_in_model_{model}_only_summed_over_runs"] += int((other_mask & ~mask).sum())
            for coil in ("all", coils[subject]):
                cohorts[coil].add(mask, signal, white)
            if acq.endswith("me4"):
                try:
                    triplet, methods = echo_triplet(root, subject, acq, reference, white, args.ants)
                except (Unavailable, nib.filebasedimages.ImageFileError, OSError) as error:
                    echo_failures[str(error) if isinstance(error, Unavailable) else "unreadable_echo_input"] += 1
                else:
                    for label, values in triplet.items():
                        paired[label].add(*values, white)
                    echo_counts[f"paired_{coils[subject]}"] += 1
                    for label, method in methods.items():
                        if label.endswith("_echo_time"):
                            echo_times[label.removesuffix("_echo_time")].add(method)
                        else:
                            echo_counts[f"{label}_{method}"] += 1
        primary[acq] = {}
        report["mask_agreement_with_motor_and_ffa_models"][acq] = {
            f"model_{model}": dict(counts) for model, counts in model_support.items()}
        report["primary_by_protocol"][acq] = {}
        for coil, cohort in cohorts.items():
            maps = cohort.maps()
            primary[acq][coil] = maps
            for name, image in maps.items():
                save_map(out, f"{acq}_{coil}_{name}", image, reference)
            report["primary_by_protocol"][acq][coil] = {
                "participants": cohort.n, "rois": roi_summary(maps, rois),
                "intersection_voxels": int(cohort.intersection().sum()),
            }
        complete[acq] = cohorts["all"].intersection()
        if acq.endswith("me4"):
            echo_panels[acq] = {}
            report["paired_echo_by_protocol"][acq] = {
                "paired_participants": paired["combined"].n, "excluded_runs": dict(echo_failures),
                "paired_participants_by_coil": {
                    key.removeprefix("paired_"): n for key, n in echo_counts.items()
                    if key.startswith("paired_")
                },
                "sources": {key: n for key, n in echo_counts.items() if not key.startswith("paired_")},
                "available_echo_times_ms": {label: sorted(values) for label, values in echo_times.items()},
                "maps": {},
            }
            for label, cohort in paired.items():
                maps = cohort.maps()
                echo_panels[acq][label] = maps
                for name, image in maps.items():
                    save_map(out, f"{acq}_{label}_{name}", image, reference)
                report["paired_echo_by_protocol"][acq]["maps"][label] = roi_summary(maps, rois)
        print(f"Processed {acq.upper()} ({cohorts['all'].n} participants)", flush=True)

    common = np.logical_and.reduce(list(complete.values()))
    save_map(out, "all_acquisitions_all_38_intersection", common, reference)
    report["all_acquisitions_all_participants"] = {
        "participants": len(subjects), "runs": len(subjects) * len(ACQUISITIONS),
        "intersection_voxels": int(common.sum()), "rois": roi_summary({"intersection": common}, rois),
    }
    report["group_masks"] = audit_groups(root, subjects, reference, rois, common)

    columns = [(f"{acq.upper()}\nn=38", primary[acq]["all"]) for acq in ACQUISITIONS]
    with PdfPages(out / "coverage_diagnostics.pdf") as pdf:
        for metric in METRICS:
            plot_columns = columns
            if metric[0] == "intersection":
                plot_columns = [*columns, ("All six\n38 × 6 runs", {"intersection": common})]
            fig = figure(plot_columns, [metric], reference, background, rois, metric[1])
            pdf.savefig(fig)
            plt.close(fig)
        fig = figure(columns, [("signal_participant_count", "Contributors per voxel", "viridis", 38)],
                     reference, background, rois, "Participants contributing to the mean functional image")
        pdf.savefig(fig)
        plt.close(fig)
        for limit in (25, 75):
            metric = (f"retained_{limit}", f"Fraction at ≥{limit}% of WM median", "viridis", 1)
            fig = figure(columns, [metric], reference, background, rois, metric[1])
            pdf.savefig(fig)
            plt.close(fig)
        for coil, n in (("20ch", 16), ("64ch", 22)):
            for metric in METRICS:
                fig = figure([(f"{acq.upper()}\nn={n}", primary[acq][coil]) for acq in ACQUISITIONS],
                             [metric], reference, background, rois, f"{coil} coil | {metric[1]}")
                pdf.savefig(fig)
                plt.close(fig)
        for acq, modes in echo_panels.items():
            n = report["paired_echo_by_protocol"][acq]["paired_participants"]
            if n:
                cols = [(f"{label.title()}\nn={n}", modes[label]) for label in ECHOES]
                for metrics in (METRICS[:2], METRICS[2:], (
                        ("retained_25", "Fraction at ≥25% of WM median", "viridis", 1),
                        ("retained_75", "Fraction at ≥75% of WM median", "viridis", 1))):
                    fig = figure(cols, metrics, reference, background, rois, f"{acq.upper()} paired echoes")
                    pdf.savefig(fig)
                    plt.close(fig)
    fig = figure(columns, METRICS,
                 reference, background, rois, "Acquisition coverage across the primary cohort")
    fig.savefig(out / "coverage_overview.png", dpi=180)
    plt.close(fig)
    (out / "coverage_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True, help="New local output directory")
    parser.add_argument("--fsldir", default=os.environ.get("FSLDIR", "/usr/local/fsl"))
    parser.add_argument("--ants", default=shutil.which("antsApplyTransforms"))
    run(parser.parse_args())

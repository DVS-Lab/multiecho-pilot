#!/usr/bin/env python3
"""Render group-only sagittal coverage figures from saved Linux1 audit inputs."""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import nibabel as nib
from nibabel.processing import resample_from_to
import numpy as np
from scipy.ndimage import label

from audit_coverage import ACQUISITIONS, METRICS, on_grid, roi_masks
from audit_group_masks import array, primary_ppi_intersection
from reextract_motor_model2 import manuscript_subjects


CLUSTER = "masks/mask_MBxME_ppi_zstat17_thresh.nii.gz"


def world_axes(image):
    steps = np.diag(image.affine)[:3]
    if np.any(steps <= 0) or not np.allclose(image.affine[:3, :3], np.diag(steps), atol=.001):
        raise ValueError("Expected an axis-aligned MNI grid in canonical orientation.")
    return tuple(steps[d] * np.arange(image.shape[d]) + image.affine[d, 3] for d in range(3))


def sagittal_extent(y, z):
    return (y[0] - (y[1] - y[0]) / 2, y[-1] + (y[1] - y[0]) / 2,
            z[0] - (z[1] - z[0]) / 2, z[-1] + (z[1] - z[0]) / 2)


def anatomy(ax, data, extent, vmax):
    ax.imshow(data.T, extent=extent, origin="lower", cmap="gray", vmin=0, vmax=vmax)
    ax.set(xticks=[], yticks=[])


def protocol_figure(run, reference, fsldir, output):
    summary = json.loads((run / "coverage_summary.json").read_text())
    if summary["subjects"] != 38:
        raise ValueError("The coverage run must use the primary 38-participant cohort.")
    rois, _ = roi_masks(fsldir, reference)
    outline_colors = ("#ff8f42", "#fc70b5", "#f5dc61", "#63e0eb")
    x, y, z = world_axes(reference)
    extent = sagittal_extent(y, z)
    background = reference.get_fdata(dtype=np.float32)
    vmax = np.percentile(background[background > 0], 99)
    slices = [int(np.abs(x - coordinate).argmin()) for coordinate in (-10, -30)]
    fig, axes = plt.subplots(8, 6, figsize=(14, 14), layout="constrained")
    fig.suptitle("Whole-brain coverage across acquisition protocols\n"
                 "Matched left sagittal slices · posterior at left",
                 fontsize=16, fontweight="bold")
    for band, (metric, title, cmap, maximum) in enumerate(METRICS):
        for column, protocol in enumerate(ACQUISITIONS):
            values = on_grid(run / f"{protocol}_all_{metric}.nii.gz", reference)
            for row, index in enumerate(slices):
                ax = axes[2 * band + row, column]
                brain = background[index]
                layer = values[index]
                valid = np.isfinite(layer) & ((brain > 0) | (layer > 0))
                if metric == "mean_normalized_signal":
                    valid &= layer > 0  # Zero denotes no contributing participants in this map.
                anatomy(ax, brain, extent, vmax)
                last = ax.imshow(np.ma.masked_where(~valid, layer).T, origin="lower", extent=extent,
                                 cmap=cmap, vmin=0, vmax=maximum, alpha=.82, interpolation="nearest")
                for region, color in zip(rois.values(), outline_colors):
                    if region[index].any():
                        ax.contour(y, z, region[index].T, levels=[.5], colors=[color], linewidths=.65)
                ax.set(xlim=extent[:2], ylim=extent[2:])
                if band == row == 0:
                    ax.set_title(f"{protocol.upper()}\nn = 38", fontsize=10)
                if column == 0:
                    ax.set_ylabel(f"x = {x[index]:g} mm", fontsize=9)
        colorbar = fig.colorbar(last, ax=axes[2*band:2*band+2, :], shrink=.85,
                                ticks=[0, maximum] if metric == "intersection" else
                                np.linspace(0, maximum, 5))
        colorbar.set_label(title, fontsize=9)
        if metric == "intersection":
            colorbar.set_ticklabels(["Incomplete", "All 38"])
    fig.legend(handles=[Patch(edgecolor=color, facecolor="none", label=name.split(" (")[0])
                        for name, color in zip(rois, outline_colors)],
               loc="outside lower center", ncol=4, frameon=False, fontsize=9)
    fig.savefig(output, dpi=175)
    plt.close(fig)


def figure7_layers(root):
    path = root / CLUSTER
    native = nib.load(path)
    data = array(path, native)
    cluster = np.isfinite(data) & (data != 0)
    if cluster.sum() != 140 or label(cluster)[1] != 1:
        raise ValueError("Expected a single 140-voxel component in the saved Figure 7 mask.")
    centroid = nib.affines.apply_affine(native.affine, np.argwhere(cluster).mean(axis=0))
    if np.linalg.norm(centroid - [-10, 12, -4]) > 1:
        raise ValueError("The saved mask does not match the Figure 7 centroid.")
    subjects = manuscript_subjects(root)
    found, common = primary_ppi_intersection(root, native, subjects)
    if len(subjects) != 38 or found != 228 or common is None:
        raise ValueError("Expected 228 PPI masks for the 38 primary participants.")

    # Classify on the original grid before reorienting the labels for display.
    covered = cluster & common
    excluded = cluster & ~common
    labels = covered.astype(np.uint8) + 2 * excluded.astype(np.uint8)
    native_report = json.loads((root / "first_level_feat_figure7_native_overlap.json").read_text())
    saved = next(row["components"][0] for row in native_report["figure7_saved_masks"]
                 if row["location"] == CLUSTER)
    if (int(covered.sum()), int(excluded.sum())) != (saved["inside_primary_ppi_intersection"],
                                                   saved["outside_primary_ppi_intersection"]):
        raise ValueError("Figure 7 overlap disagrees with the saved native-grid audit.")
    return nib.as_closest_canonical(nib.Nifti1Image(labels, native.affine))


def figure7_slices(labels_image, reference, output):
    labels = np.asarray(labels_image.dataobj)
    x, y, z = world_axes(labels_image)
    _, ref_y, ref_z = world_axes(reference)
    extent = sagittal_extent(y, z)
    ref_extent = sagittal_extent(ref_y, ref_z)
    # Sample the template at the exact x of each cluster slice. Keep the
    # template's finer in-plane lattice and the labels' native voxel edges.
    affine = reference.affine.copy()
    affine[0, 0], affine[0, 3] = labels_image.affine[0, 0], x[0]
    background = resample_from_to(reference, ((len(x), len(ref_y), len(ref_z)), affine), order=1)
    background = background.get_fdata(dtype=np.float32)
    vmax = np.percentile(background[background > 0], 99)
    indices = np.argwhere(labels != 0)
    slices = np.unique(indices[:, 0])
    limits = [(axis[indices[:, dim].min()] - 12, axis[indices[:, dim].max()] + 12)
              for dim, axis in ((1, y), (2, z))]
    colors = ["#17b9af", "#ef8839"]
    totals = [int(np.count_nonzero(labels == kind)) for kind in (1, 2)]
    columns = min(4, len(slices))
    rows = (len(slices) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(2.9*columns, 2.7*rows+.8),
                             squeeze=False, layout="constrained")
    fig.suptitle("Figure 7 target overlap with common PPI coverage\n"
                 "140 saved voxels · 38 participants × 6 acquisitions",
                 fontsize=13, fontweight="bold")
    for ax, index in zip(axes.flat, slices):
        anatomy(ax, background[index], ref_extent, vmax)
        layer = labels[index]
        ax.imshow(np.ma.masked_equal(layer, 0).T, extent=extent, origin="lower", alpha=.85,
                  cmap=ListedColormap(colors), vmin=.5, vmax=2.5, interpolation="nearest")
        counts = [int(np.count_nonzero(layer == kind)) for kind in (1, 2)]
        ax.set(xlim=limits[0], ylim=limits[1], xlabel="Posterior ←   → Anterior")
        ax.set_title(f"x = {x[index]:.1f} mm  |  {counts[0]} inside, {counts[1]} outside", fontsize=9)
    for ax in list(axes.flat)[len(slices):]:
        ax.set_visible(False)
    fig.legend(handles=[Patch(color=colors[0], label=f"Inside common mask ({totals[0]})"),
                        Patch(color=colors[1], label=f"Outside common mask ({totals[1]})")],
               loc="outside lower center", ncol=2, frameon=False)
    fig.savefig(output, dpi=175)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--coverage-run", type=Path, help="Default: latest completed coverage run")
    parser.add_argument("--fsldir", type=Path, default=Path(os.environ.get("FSLDIR", "/usr/local/fsl")))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run = args.coverage_run
    if run is None:
        summaries = list((args.root / "derivatives/coverage_audit").glob("*/coverage_summary.json"))
        if not summaries:
            parser.error("No saved coverage run found. Pass --coverage-run with the completed run directory.")
        run = max(summaries, key=lambda path: path.stat().st_mtime).parent
    reference = nib.as_closest_canonical(nib.load(args.fsldir / "data/standard/MNI152_T1_2mm_brain.nii.gz"))
    labels = figure7_layers(args.root)
    args.output.mkdir(parents=True, exist_ok=True)
    protocol_figure(run, reference, args.fsldir, args.output / "protocol_coverage_sagittal.png")
    figure7_slices(labels, reference, args.output / "figure7_cluster_coverage_sagittal.png")


if __name__ == "__main__":
    main()

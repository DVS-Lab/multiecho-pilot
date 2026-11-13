#!/usr/bin/env python3
"""Compare the saved Figure 7 target, AFNI effect, and simulation-mask candidate."""
import argparse
import json
from pathlib import Path
import re

import nibabel as nib
import numpy as np

from audit_group_masks import (
    afni_history, array, command_option, command_working_dir, mask, mask_grid_matches,
    primary_ppi_intersection, safe_location,
)
from reextract_motor_model2 import manuscript_subjects


CLUSTER = Path("derivatives/fsl/afni/MBxME_ppi_zstat17_thresh+tlrc.HEAD")
FIT = Path("derivatives/fsl/afni/LME_output_ppi-zstat17+tlrc.HEAD")
SIMULATION_MASK = Path("derivatives/fsl/brain_mask.nii.gz")


def compare(root, cluster_path, fit_path, simulation_path, subjects):
    target_image = nib.load(cluster_path)
    fit = nib.load(fit_path)
    cluster_values = array(cluster_path, target_image)
    target = np.isfinite(cluster_values) & (cluster_values != 0)
    if (target.sum() != 140 or fit.shape[:3] != target_image.shape[:3]
            or not np.allclose(fit.affine, target_image.affine, atol=.001, rtol=0)):
        raise ValueError("Expected the saved 140-voxel target and AFNI fit on the same voxel grid.")

    history = afni_history(cluster_path).replace("\\\n", " ")
    commands = [line for line in history.splitlines()
                if re.search(r"(?:^|[\s/])3dClusterize(?=\s)", line)]
    command = commands[-1] if commands else ""
    search_mask_name = command_option(command, "3dClusterize", "-mask")
    search_mask_path = command_working_dir(root, cluster_path.parent, search_mask_name,
                                         history, "3dClusterize")
    use_header_mask = bool(re.search(r"(?:^|\s)-mask_from_hdr(?:\s|$)", command))
    header_has_mask = "AFNI_CLUSTSIM_MASK" in getattr(fit.header, "info", {})
    inset = command_option(command, "3dClusterize", "-inset")
    fit_history = afni_history(fit_path)
    brick_text = command_option(command, "3dClusterize", "-ithr")
    if brick_text is not None and not brick_text.isdecimal():
        raise ValueError("The saved threshold brick has a non-numeric selector. Resolve it from the AFNI header.")
    brick = int(brick_text) if brick_text is not None else 5  # The tracked Figure 7 command uses brick 5.
    effect = array(fit_path, target_image, brick)
    effect_support = np.isfinite(effect) & (effect != 0)
    simulation_mask = mask(simulation_path, target_image)
    found, complete = primary_ppi_intersection(root, target_image, subjects)
    if found != 228 or complete is None:
        raise ValueError("Expected all 228 primary PPI masks.")
    if (int((target & complete).sum()), int((target & ~complete).sum())) != (122, 18):
        raise ValueError("Primary run coverage does not match the saved native-grid overlap.")
    outside_complete = target & ~complete
    result = {
        "target_voxels": int(target.sum()),
        "primary_ppi_masks_found": found,
        "target_voxels_outside_primary_ppi_intersection": int(outside_complete.sum()),
        "saved_clusterize_command_found": bool(command),
        "saved_clusterize_names_expected_fit": (Path(inset.split("[", 1)[0]).name.removesuffix(".HEAD")
                                                  == fit_path.name.removesuffix(".HEAD")) if inset else None,
        "saved_clusterize_command_passes_explicit_mask": bool(search_mask_name) if command else None,
        "saved_clusterize_explicit_mask_resolved": bool(search_mask_path) if search_mask_name else None,
        "saved_clusterize_command_requests_header_mask": use_header_mask if command else None,
        "fit_header_has_cluster_simulation_mask": header_has_mask,
        "saved_3dLMEr_history_passes_fit_mask": bool(command_option(fit_history, "3dLMEr", "-mask"))
        if "3dLMEr" in fit_history else None,
        "threshold_brick_index": brick,
        "threshold_brick_source": "saved_cluster_history" if brick_text is not None else "tracked_script",
        "simulation_mask_candidate": safe_location(root, simulation_path),
        "simulation_mask_candidate_matches_native_grid": mask_grid_matches(simulation_path, cluster_path),
        "target_voxels_inside_simulation_mask_candidate": int((target & simulation_mask).sum()),
        "target_voxels_outside_simulation_mask_candidate": int((target & ~simulation_mask).sum()),
        "incompletely_covered_target_voxels_inside_simulation_mask_candidate":
            int((outside_complete & simulation_mask).sum()),
        "target_voxels_with_nonzero_threshold_brick_statistic": int((target & effect_support).sum()),
        "nonzero_threshold_brick_voxels_outside_simulation_mask_candidate":
            int((effect_support & ~simulation_mask).sum()),
    }
    if search_mask_path:
        search_mask = mask(search_mask_path, target_image)
        result["target_voxels_outside_recorded_search_mask"] = int((target & ~search_mask).sum())
        result["search_and_simulation_mask_candidate_differing_voxels"] = int(
            np.count_nonzero(search_mask != simulation_mask))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--simulation-mask", type=Path, default=SIMULATION_MASK,
                        help="Saved mask named by the correction log, relative to the project root")
    args = parser.parse_args()
    root = args.root.resolve()
    report = compare(root, root / CLUSTER, root / FIT, root / args.simulation_mask, manuscript_subjects(root))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

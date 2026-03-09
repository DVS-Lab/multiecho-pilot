# Code directory guide

This directory contains both the active analysis pipeline and a substantial number of one-off notebooks, generated tables, and likely archival files, so the list below distinguishes reusable workflow code from materials that probably belong elsewhere.

## Core pipeline and metadata preparation

- `prepdata.sh`, `run_prepdata.sh`, `heuristics.py`, and `shiftdates.py` convert raw scanner data to BIDS, deface the T1w image, and shift scan dates for sharing.
- `warpkit.sh` and `run_warpkit.sh` build fieldmap-style outputs from multi-echo magnitude/phase images and copy them into each subject's `bids/sub-*/fmap` folder.
- `addUnits_func.py` updates BIDS JSON sidecars with `Units` fields for magnitude and phase images.
- `addIntendedFor_func.py` is misnamed and appears to duplicate part of `addUnits_func.py` by setting `Units`, so it should be reviewed for rename or possible deletion.
- `update_IntendedFor.ipynb` is an interactive metadata-fixing notebook that probably belongs in a more formal scripted workflow or an archive folder.
- `print-echotime.sh` prints echo times from BIDS JSON sidecars for quick verification.
- `check_TRs.sh` prints image dimensions for a specific acquisition as a quick consistency check.

## Behavioral conversion and EV generation

- `convertSharedReward2BIDSevents.m` converts raw shared-reward task logs into BIDS-compliant `_events.tsv` files and encodes the counterbalance-to-acquisition mapping.
- `gen3colfiles.sh`, `run_gen3colfiles.sh`, and `BIDSto3col.sh` convert BIDS events into FSL 3-column EV files under `derivatives/fsl/EVFiles`.
- `merge_ev_files.sh` appears to merge or reorganize EV timing files for downstream FSL use.
- `gen_missingevs.sh` appears to identify or generate missing EV placeholders for incomplete timing sets.
- `list_custom-evs.py` summarizes the presence and row counts of generated EV files into a CSV table.
- `list_custom-evs_terminal.py` prints the same EV-file audit to the terminal instead of saving a spreadsheet.
- `EV_Template2.ipynb` is a notebook version of EV-generation logic and is probably archival unless it is still the preferred development interface.

## MRIQC, fMRIPrep, smoothing, and confounds

- `mriqc.sh` and `run_mriqc.sh` run MRIQC participant-level jobs over the BIDS dataset.
- `fmriprep.sh`, `fmriprep-hpc.sh`, `run_fmriprep.sh`, and `run_fmriprep-hpc.sh` run fMRIPrep locally or on HPC for the study acquisitions.
- `smooth-3dBlurToFWHM.sh` and `run_smooth-3dBlurToFWHM.sh` create 5 mm blurred copies of fMRIPrep outputs with AFNI `3dBlurToFWHM`.
- `rsync_5mm_files.sh` copies the 5 mm smoothed fMRIPrep files to the HPC workspace.
- `MakeConfounds.py` extracts FSL-ready nuisance regressors from fMRIPrep confounds tables.
- `genTedanaConfounds.py` combines tedana rejected-component information with fMRIPrep confounds to create tedana-plus-confounds design files.
- `ApplyTransformAndTedanaConfounds.py` looks like an older notebook-export script that both warps tedana outputs and builds tedana confounds, so it should probably be split, renamed, or archived.
- `compare_confounds.sh` compares confounds files across versions for a requested acquisition.
- `regenerate_fd_mean.sh` recomputes framewise-displacement means for selected subjects and acquisitions.

## Tedana and multi-echo handling

- `tedana.sh` is a subject-specific local tedana runner hard-coded to `sub-10777sp`, so it looks like a one-off script rather than a general pipeline entry point.
- `tedana-hpc.sh`, `tedana-rf1-hpc.sh`, `run_tedana_mbme.sh`, and `run_tedana-rf1-hpc.sh` are batch wrappers for tedana execution, with some scripts targeting this repository and others still pointing to older project layouts.
- `run_tedana.sh` and `run_tedana-hpc.sh` still point to `rf1-sra-data` rather than `multiecho-pilot`, so they look like legacy carryovers that should be archived or deleted unless still needed elsewhere.
- `my_tedana_mbme.py` runs tedana across multi-echo acquisitions in parallel and appears to be an older Python entry point.
- `tedana-multi.py` runs tedana for one subject by discovering all multi-echo acquisitions in that subject's fMRIPrep output.

## FSL first-, second-, and third-level analyses

- `L1stats.sh` is the main first-level FSL script for activation, seed-based PPI, and network PPI analyses across acquisitions and denoising options.
- `run_L1stats.sh` is the main local wrapper that fans `L1stats.sh` across subjects, acquisitions, and denoising modes.
- `run_L1stats-copy.sh` repeats the same wrapper pattern for alternative first-level models.
- `L1stats-hpc.sh` is an HPC-oriented first-level command generator that appears to represent a variant pipeline rather than the current default local workflow.
- `run_L1stats-hpc.sh` looks incomplete or broken and should be reviewed before anyone relies on it.
- `run_L1stats-hpc-test.sh` is another HPC submission wrapper that references `sublist-final.txt`, which is not present here, so it also needs review.
- `cleanL1-linuxbox.sh` repairs FEAT registration links and removes bulky intermediate files after first-level runs.
- `L2stats.sh` combines the acquisition-specific first-level FEAT directories within subject to estimate within-subject sequence effects.
- `run_L2stats.sh`, `run_L2stats_model-2.sh`, and `run_L2stats_model-3.sh` batch the second-level script across subjects for different first-level model families.
- `copy-model-4.sh` moves model outputs from an HPC derivative tree back into the main `derivatives/fsl` tree.
- `L3stats.sh` runs group-level FEAT analyses and optional `randomise` permutation tests on selected copes.
- `run_L3stats.sh` batches the group-level script across cope numbers and contrast names.

## tSNR, smoothness, and extraction utilities

- `computeTSNRandSmoothness.sh`, `computeTSNRandSmoothness_ROIs.sh`, and `run_computeTSNRandSmoothness.sh` build special FEAT runs for estimating tSNR and AFNI smoothness across acquisitions.
- `multiecho-inputs.sh` merges coil information with `.feat`-level tSNR summaries into a CSV for downstream statistics.
- `extract_signal.sh` extracts ROI means for beta, variance, z-statistic, or tSNR images across subjects, acquisitions, and masks.
- `extract-coil.sh` and `get_coil.sh` are two versions of the same basic coil-extraction utility and could likely be consolidated.
- `tsnr-compile.sh` writes a list of FEAT directories for later `fslstats` summarization.
- `tsnr-fslstats.sh` reads that directory list and prints FEAT-derived summary values.
- `make_r-squared_diff.sh`, `compile_r-square_diff.sh`, `print_r-squared_diff.sh`, and `analyze_diff.sh` support comparison of base versus tedana model fit images and inspect differences between output files.

## Outlier identification and QC summaries

- `Outliers-motion.py` is the clearest acquisition-level MRIQC outlier script for this repository and writes outlier tables and group covariates.
- `OutlierID.py` appears to be an older adaptation of the outlier workflow and may be buggy because it references `outlier_run_Custom1` even though the script defines acquisition-level outliers.
- `IDoutliers.py` combines behavioral misses, motion, and MRIQC summaries into an exclusions table.
- `IDoutliers_test.ipynb` is a notebook version or test bed for the exclusions logic and is probably archival.
- `SRNDNA_OutlierID.py` is explicitly labeled as project-specific to another study and should probably be archived or deleted from this repository.

## AFNI mixed-effects follow-up

- `gen_anova-inputs.sh` generates lists of first-level PPI cope files that feed into AFNI mixed-effects analyses.
- `anova-inputs_ppi_20ch.txt` and `anova-inputs_ppi_64ch.txt` are generated file lists for AFNI modeling rather than reusable source code.
- `afni-3dLMEr_copes.sh` runs AFNI `3dLMEr` models on cope images and then performs smoothness estimation, cluster simulation, and thresholding.
- `afni-3dLMEr_zstats.sh` runs parallel AFNI `3dLMEr` models on z-stat images and then performs cluster-thresholded follow-up maps.
- `.3dLMEr.dbg.AFNI.args` is an AFNI debug artifact and should probably be deleted or moved out of versioned source code.

## Plotting, notebooks, and manuscript-oriented summaries

- `multiecho-plots.Rmd` is an R Markdown analysis of tSNR and smoothness by acquisition, echo structure, and coil.
- `plot_figures.ipynb` appears to be a notebook for study figures and summary visualizations.
- `print_statistics.ipynb`, `print_statistics-clean.ipynb`, and `print_statistics-update.ipynb` are successive notebook-based statistical reporting workflows, and only the most current version should probably stay in the main code area.
- `multiecho-pilot_Demographics.xlsx` is an analysis input or summary table rather than executable code and likely belongs in `derivatives/` or `reports/`.
- `smoothness-all.csv`, `smoothness-all-zero.csv`, and `smoothness_multi_echo_table.csv` are generated summary tables rather than source code and would fit better under `derivatives/` or `reports/`.
- `age_distribution_by_headcoil.png`, `dlpfc_motion_tedana_mb6me4.png`, and `ipl_motion_hc_interaction_mb1me4.png` are figure outputs and would be cleaner in a plots or reports folder instead of `code/`.

## Subject lists and run lists

- `sublist-20ch.txt`, `sublist-64ch.txt`, `sublist-all.txt`, `sublist-complete.txt`, `sublist-deriv.txt`, `sublist-fix.txt`, `sublist-headcoils.txt`, `sublist-included.txt`, `sublist-loc.txt`, `sublist-openneuro.txt`, `sublist-randomise.txt`, `sublist-source.txt`, `sublist-sp.txt`, and `sublist-test.txt` define analysis cohorts or convenience subsets for different pipeline steps.

## Scratch, state, and empty directories

- `.RData` is a saved R workspace and should probably be deleted from source control.
- `Untitled1.ipynb` appears empty and should probably be deleted.
- `design_matrices/` is currently empty and can either be populated intentionally or removed.
- `outputs/` is currently empty and can either be populated intentionally or removed.

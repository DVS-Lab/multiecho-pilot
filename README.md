# multiecho-pilot

This repository is a working analysis repository for a shared-reward fMRI sequence pilot that compares acquisition choices across multiband factor, multi-echo factor, and head coil, with later follow-up acquisitions added in a second pilot wave.

The repository is best understood as a study workspace rather than a polished software package: it contains the BIDS-formatted dataset, task assets, FSL templates, many pipeline scripts, downstream extraction and plotting code, and a mix of active, exploratory, and legacy files in `code/`.

## What the project is doing

At a high level, the project asks how acquisition choices affect task-relevant signal in a shared reward paradigm, with particular emphasis on reward-related, motor, face-sensitive, PPI, tSNR, and smoothness outcomes.

The code implements a fairly standard but customized workflow:

1. convert raw scanner data to BIDS and fix metadata;
2. generate BIDS events from task logs;
3. run MRIQC and fMRIPrep, with optional multi-echo denoising via tedana and optional fieldmap generation via warpkit;
4. generate confound regressors and FSL 3-column EV files;
5. run subject-level (`L1`), within-subject/acquisition-level (`L2`), and group-level (`L3`) FSL analyses;
6. compute tSNR and smoothness summaries and extract ROI values for downstream statistics;
7. run AFNI `3dLMEr` follow-up models to test head-coil, multiband, and multi-echo effects at the whole-brain level.

## Repository layout

- `bids/` contains the de-identified BIDS dataset, including participants metadata and task event files.
- `code/` contains pipeline scripts, wrappers, notebooks, summary tables, and a number of scratch or legacy files.
- `derivatives/` contains lightweight tracked outputs such as MRIQC-derived tables and ROI extraction text files; large imaging outputs are mostly expected to live outside Git.
- `stimuli/` contains the task scripts, design files, logs, and other materials used to build or document the shared reward task.
- `templates/` contains the FSL `.fsf` templates used by the `L1`, `L2`, and `L3` scripts.

## How the code is organized conceptually

The `code/` directory falls into a few broad groups:

- BIDS conversion and metadata repair.
- Event-to-EV generation for FSL.
- Preprocessing and denoising (`mriqc`, `fmriprep`, `tedana`, `warpkit`).
- First-, second-, and third-level FSL statistics.
- tSNR, smoothness, and ROI extraction utilities.
- AFNI mixed-effects follow-up analyses.
- Plotting notebooks and manuscript-oriented summaries.
- Subject lists, intermediate tables, and a handful of archival or scratch files.

A more detailed inventory is in [`code/README.md`](code/README.md).

## Important quirks of this snapshot

Many scripts hard-code local paths under `/ZPOOL/data/projects/multiecho-pilot`, so this repository is only partly portable without editing those paths.

Several scripts assume the presence of large derivative trees, masks, or helper files that are not included in this Git snapshot, which means the code documents the workflow well but will not run end-to-end as-is on a clean machine.

The `code/` directory mixes active pipeline code with notebooks, generated tables, figures, and files that look archival, project-external, or incomplete, so it should be treated as a study workbench rather than a minimal release artifact.

## Sequence/acquisition structure

The main acquisition set appears to compare standard combinations such as `mb1me1`, `mb1me4`, `mb3me1`, `mb3me4`, `mb6me1`, and `mb6me4`.

Subjects with IDs ending in `sp` appear to belong to a later pilot wave with alternate acquisitions such as `mb2me4`, `mb3me1fa50`, `mb3me3`, `mb3me3ip0`, and `mb3me4fa50`.

## Notes for future cleanup

The clearest cleanup opportunity is the `code/` directory, where reusable pipeline scripts are mixed with generated tables, one-off figures, saved workspaces, empty directories, and a few likely obsolete files.

A good first pass would be to keep the active pipeline scripts, move generated outputs into `derivatives/` or a `reports/` area, and archive or delete files marked as questionable in [`code/README.md`](code/README.md).

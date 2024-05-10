# rf1-mbm-pilot: Shared Reward Task Data with Multiband and Multi-Echo Task Analyses
This repository contains code related to our in prep project related to determine the optimal fMRI sequence for assessing activation in the striatum. All hypotheses and analysis plans were pre-registered on AsPredicted in the winter of 2021, and data collection commenced on shortly thereafter. Imaging data will be shared via [OpenNeuro][openneuro] when the manuscript is posted on bioRxiv.


## A few prerequisites and recommendations
- Understand BIDS and be comfortable navigating Linux
- Install [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation)
- Install [miniconda or anaconda](https://stackoverflow.com/questions/45421163/anaconda-vs-miniconda)


## Notes on repository organization and files
- Raw DICOMS (an input to heudiconv) are private and only accessible locally (Smith Lab Linux: /data/sourcedata). These files will have already been de-identified and converted to BIDS under a separate repository (DVS-Lab/istart-data)
- Some of the contents of this repository are not tracked (.gitignore) because the files are large and we do not yet have a nice workflow for datalad. These files/folders include parts of `bids` and `derivatives`.
- Tracked folders and their contents:
  - `code`: analysis code
  - `templates`: fsf template files used for FSL analyses
  - `masks`: images used as masks, networks, seeds, or target regions in analyses
  - `derivatives`: derivatives from analysis scripts, but only text files (re-run script to regenerate larger outputs)

## Internal: Keeping up with analyses on an ongoing basis
As we're collecting data, we must analyze it on an ongoing basis for the sake of quality assurance and identifying and correcting potential problems.

### Step 1: Checking your inputs
Before you do anything, you should make sure all your inputs are there. The person managing the preprocessing should have taken care of these steps:
1. Conversion to BIDS, defacing, and MRIQC (prepdata.sh and convertSharedReward2BIDSevents.m)
1. Preprocessing with [fmriprep][fmriprep] (fmriprep.sh)
1. Creation of confound EVs (MakeConfounds.py)
If you would like to replicate the preprocessing steps using the BIDS converted and de-identified images, you may run the following:
- 'bash run_heudiconv.sh' runs heudiconv for all subjects in input list (currently set to full sample of good subjects), as well as pydeface

### Step 2: Updating subject list
Usually we run analyses in batches (i.e., two or more subjects at a time). Rather than editing all of the run_* scripts that loop over those new subjects, you only need to update the subject numbers in the `bids/participants.tsv` file.

Update istart-sharedreward GitHub repository (assuming these were the only changes):
- `cd /data/projects/istart-sharedreward` (note: this can be done from any computer)
- `git add .`
- `git commit -m "new subjects in task-sharedreward"`
- `git push`

No other steps should create content that gets tracked in GitHub, and no scripts require any editing.

### Step 3: Updating BIDS sub-*\_events.tsv files
Since HeuDiConv can only put in a placeholder for your `sub-<sub>_task-<task>_run-<run>_events.tsv` files, you must convert your behavioral data into BIDS format. Those converted data should live with the other BIDS data. For the project in this repository, here are the steps you'd take.

First, before you do anything else, make sure local source data is current. These source data (or raw data) is stored on a different repository (`DVS-Lab/istart-data`).
  - `cd /data/projects/istart`
  - `git pull`

After you've ensured the local source data is current, you then run the following steps on the Smith Lab Linux box.
1. go to the correct location: `cd /data/projects/istart-data`
1. open Matlab: `matlab &`
1. run `run_convertSharedReward2BIDSevents.m` from Matlab (report errors on Asana and raise at lab meeting)
1. update GitHub (assuming these were the only changes):
  - `git add .`
  - `git commit -m "update BIDS tsv files for new subjects in task-sharedreward"`
  - `git push`


### Step 4: Creating 3-column files for FSL
1. go to the correct location: `cd /data/projects/istart-sharedreward`
1. run script: `bash code/run_gen3colfiles.sh`

### Step 5: Running the analyses
1. go to the correct location on the Smith Lab Linux box: `cd /data/projects/istart-sharedreward`
1. run scripts with nohup (prevents process from hanging up if you close your computer or lose your connection):
  - `nohup bash code/run_L1stats.sh > nohup_L1stats.out &` (wait till this is done before running L2stats.sh)
  - `nohup bash code/run_L2stats.sh > nohup_L2stats.out &`
1. review *.out logs from `nohup`. (if no errors, delete them. if errors, report on Asana and raise at lab meeting)



## External: Basic commands to reproduce our all of our analyses (under construction)
Note: this section is still under construction. It is intended for individuals outside the lab who might want to reproduce all of our analyses, from preprocessing to group-level stats in FSL. As a working example from a different study, please see https://github.com/DVS-Lab/srndna-trustgame

```
# get code and data (two options for data)
git clone https://github.com/DVS-Lab/istart-sharedreward
cd  istart-sharedreward

rm -rf bids # remove bids subdirectory since it will be replaced below
# can this be made into a sym link?

datalad clone https://github.com/OpenNeuroDatasets/ds003745.git bids
# the bids folder is a datalad dataset
# you can get all of the data with the command below:
datalad get sub-*

# run preprocessing and generate confounds and timing files for analyses
bash code/run_fmriprep.sh
python code/MakeConfounds.py --fmriprepDir="derivatives/fmriprep"
bash code/run_gen3colfiles.sh

# run statistics
bash code/run_L1stats.sh
bash code/run_L2stats.sh
bash code/run_L3stats.sh
```


## Acknowledgments
This work was supported, in part, by grants from the National Institutes of Health (R03-DA046733 to DVS and R15-MH122927 to DSF). DVS was a Research Fellow of the Public Policy Lab at Temple University during the preparation of the manuscript (2019-2020 academic year).

[openneuro]: https://openneuro.org/
[fmriprep]: http://fmriprep.readthedocs.io/en/latest/index.html

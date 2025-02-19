#!/usr/bin/env bash


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
istartdatadir=/ZPOOL/data/projects/multiecho-pilot #need to fix this upon release (no hard coding paths)

# study-specific inputs
TASK=sharedreward
sm=5
sub=$1
mbme=$2
acq=${mbme}


if [ "$mbme" == "mb1me1" -o  "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "$mbme" == "mb3me1fa50" ]; then
	INDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
	OUTDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold_${sm}mm.nii.gz
	MASK=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-brain_mask.nii.gz
else
	INDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
	OUTDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold_${sm}mm.nii.gz
	MASK=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-brain_mask.nii.gz
fi

if [ ! -e $INDATA ]; then
	echo ${sub} ${acq} "No data"
	exit
fi

#only run if we're missing output
if [ -e $OUTDATA ]; then
	exit
else
	3dBlurToFWHM -FWHM $sm -input $INDATA -prefix $OUTDATA -mask $MASK
fi

# not yet sure how to suppress or control this output, but it conflicts with other processes (no overwrite)
rm -rf ${scriptdir}/3dFWHMx.1D ${scriptdir}/3dFWHMx.1D.png

#!/bin/bash
#PBS -l walltime=12:00:00
#PBS -N fmriprep-test
#PBS -q normal
#PBS -l nodes=1:ppn=28

# load modules and go to workdir
module load fsl/6.0.2
source $FSLDIR/etc/fslconf/fsl.sh
module load singularity
cd $PBS_O_WORKDIR

# ensure paths are correct
projectname=multiecho-pilot #this should be the only line that has to change if the rest of the script is set up correctly
maindir=~/work/$projectname
scriptdir=$maindir/code
bidsdir=$maindir/bids
logdir=$maindir/logs
mkdir -p $logdir

#subjects=("${!1}")

rm -f $logdir/cmd_fmriprep_${PBS_JOBID}.txt
touch $logdir/cmd_fmriprep_${PBS_JOBID}.txt

# make derivatives folder if it doesn't exist.
# let's keep this out of bids for now
if [ ! -d $maindir/derivatives ]; then
	mkdir -p $maindir/derivatives
fi

scratchdir=~/scratch/$projectname/fmriprep
if [ ! -d $scratchdir ]; then
	mkdir -p $scratchdir
fi

TEMPLATEFLOW_DIR=~/work/tools/templateflow
MPLCONFIGDIR_DIR=~/work/mplconfigdir
export SINGULARITYENV_TEMPLATEFLOW_HOME=/opt/templateflow
export SINGULARITYENV_MPLCONFIGDIR=/opt/mplconfigdir

for sub in ${subjects[@]}; do
	echo singularity run --cleanenv \
-B ${TEMPLATEFLOW_DIR}:/opt/templateflow \
-B $maindir:/base \
-B /ZPOOL/data/tools/licenses:/opts \
-B $scratchdir:/scratch \
-B /mnt \
/ZPOOL/data/tools/fmriprep-24.1.1.simg \
/base/bids /base/derivatives/fmriprep \
participant --participant_label $sub \
--stop-on-first-crash \
--me-output-echos \
--output-spaces MNI152NLin6Asym \
--bids-filter-file /base/code/fmriprep_config.json \
--fs-no-reconall --fs-license-file /opts/fs_license.txt -w /scratch >> $logdir/cmd_fmriprep_${PBS_JOBID}.txt
done

torque-launch -p $logdir/chk_fmriprep_${PBS_JOBID}.txt $logdir/cmd_fmriprep_${PBS_JOBID}.txt

# NOTE: the --use-syn-sdc option will only be applied in cases where there is not a valid fmap.
# https://neurostars.org/t/using-use-syn-sdc-with-fieldmap-data/2592/2
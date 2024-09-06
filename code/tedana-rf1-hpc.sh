#!/bin/bash
#PBS -l walltime=12:00:00
#PBS -N tedana-07292024
#PBS -q normal
#PBS -m ae
#PBS -M cooper.sharp@temple.edu
#PBS -l nodes=1:ppn=28
cd $PBS_O_WORKDIR

# ensure paths are correct irrespective from where user runs the script
maindir=/home/tun46412/work/multiecho-pilot
scriptdir=$maindir/code
logdir=$maindir/logs
prepdir=$maindir/derivatives/fmriprep
mkdir -p $logdir

rm -f $logdir/cmd_tedana_${PBS_JOBID}.txt
touch $logdir/cmd_tedana_${PBS_JOBID}.txt

for sub in ${subjects[@]}; do
	for task in "sharedreward"; do
		for acq in "mb1me4" "mb3me4" "mb6me4" ; do # Need to update this loop

			# prepare inputs and outputs
			prepdir=${maindir}/derivatives/fmriprep/sub-${sub}/func
			echo1=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_desc-preproc_bold.nii.gz # Need to update these sequences
			echo2=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-2_part-mag_desc-preproc_bold.nii.gz
			echo3=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-3_part-mag_desc-preproc_bold.nii.gz
			echo4=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-4_part-mag_desc-preproc_bold.nii.gz
			outdir=${maindir}/derivatives/tedana/sub-${sub}

			# Check for the presence of all echo files
			if [ ! -e $echo1 ] || [ ! -e $echo2 ] || [ ! -e $echo3 ] || [ ! -e $echo4 ]; then
				echo "Missing one or more files for sub-${sub}, task-${task}, run-${run}" >> $scriptdir/missing-tedanaInput.log
				echo "Skipping sub-${sub}, task-${task}, run-${run}" >> $logdir/cmd_tedana_${PBS_JOBID}.txt
				continue
			fi

			mkdir -p $outdir

			# run tedana and log the command
			echo "tedana -d $echo1 $echo2 $echo3 $echo4 \
			-e 0.0138 0.03154 0.04928 0.06702 \
			--out-dir $outdir \
			--prefix sub-${sub}_task-${task}_run-${run} \
			--convention bids \
			--fittype curvefit \
			--overwrite" >> $logdir/cmd_tedana_${PBS_JOBID}.txt

			# clean up and save space
			rm -rf ${outdir}/sub-${sub}_task-${task}_run-${run}_*.nii.gz

		done
	done
done

torque-launch -p $logdir/chk_tedana_${PBS_JOBID}.txt $logdir/cmd_tedana_${PBS_JOBID}.txt

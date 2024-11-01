#!/bin/bash
#PBS -l walltime=12:00:00
#PBS -N tedana-07292024
#PBS -q normal
#PBS -m ae
#PBS -M cooper.sharp@temple.edu
#PBS -l nodes=1:ppn=28
cd $PBS_O_WORKDIR

# ensure paths are correct irrespective from where user runs the script
maindir=/home/tun31934/work/multiecho-pilot
scriptdir=$maindir/code
logdir=$maindir/logs
prepdir=$maindir/derivatives/fmriprep
mkdir -p $logdir

rm -f $logdir/cmd_tedana_${PBS_JOBID}.txt
touch $logdir/cmd_tedana_${PBS_JOBID}.txt

for sub in ${subjects[@]}; do
	for task in "sharedreward"; do
		for acq in mb1me4 mb3me4 mb6me4 mb2m4 mb3me3 mb3me3ip0 mb3me4 mb3me4fa50; do

			# prepare inputs and outputs
			prepdir=${maindir}/derivatives/fmriprep/sub-${sub}/func
			echo1=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_desc-preproc_bold.nii.gz
			echo2=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-mag_desc-preproc_bold.nii.gz
			echo3=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-mag_desc-preproc_bold.nii.gz
			echo4=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-4_part-mag_desc-preproc_bold.nii.gz
			outdir=${maindir}/derivatives/tedana/sub-${sub}

			# Check for the presence of all echo files
			if [ ! -e $echo1 ] || [ ! -e $echo2 ] || [ ! -e $echo3 ] || [ ! -e $echo4 ]; then
				echo "Missing one or more files for sub-${sub}, task-${task}, acq-${acq}" >> $scriptdir/missing-tedanaInput.log
				echo "Skipping sub-${sub}, task-${task}, acq-${acq}" >> $logdir/cmd_tedana_${PBS_JOBID}.txt
				continue
			fi

			mkdir -p $outdir
			
			    # Initialize echo time variables
    echotime1=""
    echotime2=""
    echotime3=""
    echotime4=""

    # Extract echo times from the first script output
    for echo in 1 2 3 4; do
        json_file=$(find "$bidsdir" -name "sub-${sub}_task-${task}_acq-${acq}_echo-${echo}_part-mag_bold.json")
        if [ -n "$json_file" ]; then
            echo_time=$(grep -o '"EchoTime": [0-9.]*' "$json_file" | cut -d' ' -f2 | tr -d '\r')
            eval "echotime${echo}=${echo_time}"
        else
            echo "missing JSON for echo-${echo} for sub-${sub}, task-${task}, acq-${acq}"
            echo "missing JSON for echo-${echo} for sub-${sub}, task-${task}, acq-${acq}" >> $scriptdir/missing-tedanaInput.log
        fi
    done


	if [ $acq == "mb3me3" ] || [ $acq == "mb3me3ip0" ]; then
			# run tedana and log the command
			echo "tedana -d $echo1 $echo2 $echo3 \
        -e $echotime1 $echotime2 $echotime3 \
        --out-dir $outdir \
        --prefix sub-${sub}_task-${task}_acq-${acq} \
        --convention bids \
        --fittype curvefit \
        --overwrite" >> $logdir/cmd_tedana_${PBS_JOBID}.txt
    else
    		echo "tedana -d $echo1 $echo2 $echo3 $echo4 \
        -e $echotime1 $echotime2 $echotime3 $echotime4 \
        --out-dir $outdir \
        --prefix sub-${sub}_task-${task}_acq-${acq} \
        --convention bids \
        --fittype curvefit \
        --overwrite"  >> $logdir/cmd_tedana_${PBS_JOBID}.txt
	fi
        			# clean up and save space
			rm -rf ${outdir}/sub-${sub}_task-${task}_acq-${acq}_*.nii.gz

		done
	done
done

torque-launch -p $logdir/chk_tedana_${PBS_JOBID}.txt $logdir/cmd_tedana_${PBS_JOBID}.txt

#!/bin/bash

# Ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

for task in sharedreward; do
	for acq in mb1me4 mb2me4 mb3me3 mb3me4 mb6me4 mb3me3ip0 mb3me4fa50; do

    sub=10777sp	
    # Prepare inputs and outputs; don't run if data is missing, but log missingness
    prepdir=${maindir}/derivatives/fmriprep/sub-${sub}/func
    bidsdir=${maindir}/bids/sub-${sub}/func
    echo1=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_desc-preproc_bold.nii.gz
    echo2=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-mag_desc-preproc_bold.nii.gz
    echo3=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-mag_desc-preproc_bold.nii.gz
    echo4=${prepdir}/sub-${sub}_task-${task}_acq-${acq}_echo-4_part-mag_desc-preproc_bold.nii.gz
    outdir=${maindir}/derivatives/tedana/sub-${sub}

    if [ ! -e $echo1 ]; then
        echo "missing ${echo1}"
        echo "missing ${echo1}" >> $scriptdir/missing-tedanaInput.log
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

    # Run tedana
    tedana -d $echo1 $echo2 $echo3 $echo4 \
        -e $echotime1 $echotime2 $echotime3 $echotime4 \
        --out-dir $outdir \
        --prefix sub-${sub}_task-${task}_acq-${acq} \
        --convention bids \
        --fittype curvefit \
        --overwrite

    # Clean up and save space
    rm -rf ${outdir}/sub-${sub}_task-${task}_*.nii.gz

	done
done

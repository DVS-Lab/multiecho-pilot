#!/bin/bash
# Ensure paths are correct
maindir=~/work/multiecho-pilot # This should be the only line that has to change if the rest of the script is set up correctly
scriptdir=$maindir/code
# Load the array from sublist-all.txt
mapfile -t myArray < ${scriptdir}/sublist-final.txt
# Grab elements in chunks of ntasks
ntasks=2
counter=0
# Define the script to be submitted
SCRIPTNAME=${scriptdir}/L1stats-hpc.sh
# Denoising options
while [ $counter -lt ${#myArray[@]} ]; do
    # Extract the current chunk of subjects
    subjects=("${myArray[@]:$counter:$ntasks}")
    echo "Processing subjects: ${subjects[@]}"
    # Submit the job with qsub
    qsub -v "subjects=${subjects[*]}" $SCRIPTNAME
    # Increment the counter
    let counter=counter+$ntasks
    # Add a small delay between submissions
    sleep 1s
done

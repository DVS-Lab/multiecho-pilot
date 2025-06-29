#!/bin/bash

# This script prints out all of the .feat directories for a given path
# The output of this script will work as the inputs for tsnr-fslstats.sh

# Create output file
output_file="tsnr-acq.txt"

# Loop through acquisitions
for mbme in "mb1me1" "mb1me4" "mb2me4" "mb3me1" "mb3me1fa50" "mb3me3" "mb3me4" "mb3me4fa50" "mb6me1" "mb6me4"; do
   ls -d -1 /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-*/*${mbme}*.feat
done

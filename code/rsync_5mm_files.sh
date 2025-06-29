#!/bin/bash

# Define source and destination base directories
SRC_BASE="/ZPOOL/data/projects/multiecho-pilot/derivatives/fmriprep"
DEST_BASE="/gpfs/scratch/tug87422/smithlab-shared/multiecho-pilot/derivatives/fmriprep"
USER="tun46412@owlsnest.hpc.temple.edu"  # Replace with actual username and destination hostname if needed

# Loop through each subject in the fmriprep directory
for sub in "$SRC_BASE"/sub-*; do
	echo "Running rsync for sub-$sub"
    if [[ -d "$sub/func" ]]; then
        sub_id=$(basename "$sub")  # Extract subject ID (e.g., "sub-10136")

        # Define source and destination func directories
        SRC_FUNC="$sub/func"
        DEST_FUNC="$DEST_BASE/$sub_id/func"

        # Ensure the destination directory exists
        ssh "$USER" "mkdir -p $DEST_FUNC"

        # Use rsync to copy only files containing '5mm'
        rsync -av --progress "$SRC_FUNC"/*5mm* "$USER:$DEST_FUNC/"
    fi
done

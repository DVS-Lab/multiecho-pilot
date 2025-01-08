#!/bin/bash

# Set the base directory path
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/bids"

# Print the table header
printf "%-10s %-10s\n" "Subject" "ReceiveCoilName"

# Loop through each subject's anat folder
for anat_dir in "$BASE_DIR"/sub*/anat/; do
    # Check if anat folder exists
    if [ -d "$anat_dir" ]; then
        # Loop through each JSON file in the anat folder
        for json_file in "$anat_dir"*.json; do
            if [ -f "$json_file" ]; then
                # Extract the subject ID without 'sub-' and ReceiveCoilName without 'HeadNeck_'
                subject_id=$(basename "$(dirname "$anat_dir")" | sed 's/sub-//')
                coil_name=$(grep -oP '"ReceiveCoilName"\s*:\s*"\K[^"]+' "$json_file" | sed 's/HeadNeck_//')
                # Print subject ID and cleaned ReceiveCoilName value in table format
                printf "%-10s %-10s\n" "$subject_id" "$coil_name"
            fi
        done
    fi
done

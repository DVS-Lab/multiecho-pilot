#!/bin/bash

# This script iterates through a BIDS directory, finds the
# sub-#####_T1w.json files in each subject's anat directory,
# and extracts the "ReceiveCoilName" field.

# IMPORTANT: Set your BIDS root directory here.
# Replace '/path/to/your/bids_directory' with the actual path.
# Example: BIDS_DIR="/home/user/my_bids_data"
# A common location might be ~/bids_data or a specific project directory.
BIDS_DIR="/ZPOOL/data/projects/multiecho-pilot/bids"

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "Error: 'jq' is not installed."
    echo "Please install 'jq' to run this script (e.g., sudo apt-get install jq on Debian/Ubuntu)."
    exit 1
fi

echo "Searching for 'ReceiveCoilName' in BIDS directory: $BIDS_DIR"
echo ""

# Check if the BIDS directory exists
if [ ! -d "$BIDS_DIR" ]; then
    echo "Error: BIDS directory '$BIDS_DIR' not found. Please verify the path."
    exit 1
fi

# Find all subject directories (e.g., sub-001, sub-002)
# The -maxdepth 1 prevents it from going into nested sub-directories
# The -type d ensures we only get directories
# The -name 'sub-*' filters for subject directories
find "$BIDS_DIR" -maxdepth 1 -type d -name 'sub-*' | sort | while read subject_dir; do
    # Extract the subject ID from the full path
    subject_id=$(basename "$subject_dir")

    # Construct the path to the anat directory
    anat_dir="$subject_dir/anat"

    # Check if the anat directory exists
    if [ ! -d "$anat_dir" ]; then
        echo "Warning: 'anat' directory not found for $subject_id. Skipping."
        continue
    fi

    # Construct the full path to the T1w JSON file
    json_file="$anat_dir/${subject_id}_T1w.json"

    # Check if the JSON file exists
    if [ ! -f "$json_file" ]; then
        echo "Warning: No '${subject_id}_T1w.json' found in '$anat_dir'. Skipping."
        continue
    fi

    # Extract the "ReceiveCoilName" using jq
    # -r makes the output raw (without quotes)
    # .ReceiveCoilName accesses the field
    receive_coil_name=$(jq -r '.ReceiveCoilName' "$json_file" 2>/dev/null)

    # Check if the field was found (jq returns null if not found)
    if [ "$receive_coil_name" != "null" ] && [ -n "$receive_coil_name" ]; then
        echo "$subject_id: ReceiveCoilName = $receive_coil_name"
    else
        echo "$subject_id: 'ReceiveCoilName' field not found or is empty in $(basename "$json_file")"
    fi

done

echo ""
echo "Script finished."


#!/bin/bash

# This script lists the file paths for R-squared_diff.nii.gz images
# based on a selected acquisition type.

echo "======================================================="
echo "Listing R-squared Difference Image Paths by Acquisition"
echo "======================================================="

# --- CONFIGURATION ---
# Choose ONE acquisition type by uncommenting the desired line.
# Only one line should be uncommented at a time.
SELECTED_ACQ_TYPE="mb1me4"
# SELECTED_ACQ_TYPE="mb3me4"
# SELECTED_ACQ_TYPE="mb6me4"
# ---------------------

# Define base paths
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl"
SUBLIST="/ZPOOL/data/projects/multiecho-pilot/code/sublist-openneuro.txt"

echo "Selected Acquisition Type: $SELECTED_ACQ_TYPE"
echo "-------------------------------------------------------"

# Check if a selection has been made
if [ -z "$SELECTED_ACQ_TYPE" ]; then
    echo "Error: Please uncomment one of the 'SELECTED_ACQ_TYPE' options at the top of the script."
    exit 1
fi

# Check if the subject list file exists
if [ ! -f "$SUBLIST" ]; then
    echo "Error: Subject list file not found at $SUBLIST"
    exit 1
fi

# Read subjects into an array, ensuring they are sorted if the file isn't already
# The sublist-complete.txt is already provided as sorted, so 'readarray' is sufficient.
readarray -t SUBJECTS < "$SUBLIST"

# Iterate over each subject
for SUB_ID in "${SUBJECTS[@]}"; do
    # Construct the expected path for the difference image
    DIFF_IMAGE_PATH="${BASE_DIR}/sub-${SUB_ID}/L1_task-sharedreward_model-1_type-act_acq-${SELECTED_ACQ_TYPE}_sm-0_denoising-tedana_r-square.feat/R-squared_diff.nii.gz"

    # Check if the difference image file exists
    if [ -f "$DIFF_IMAGE_PATH" ]; then
        echo "$DIFF_IMAGE_PATH"
    else
        echo "Image does not exist for sub-$SUB_ID, acq-$SELECTED_ACQ_TYPE: $DIFF_IMAGE_PATH"
    fi
done

echo "======================================================="
echo "Script Finished"
echo "======================================================="

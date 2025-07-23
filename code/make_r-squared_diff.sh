#!/bin/bash

# This script calculates the difference between R-squared images for base and tedana denoising.
# It iterates through a list of subjects and specified acquisition types.
# The difference image (base_r2 - tedana_r2) is saved in the tedana output directory.

echo "==================================================="
echo "Starting R-squared Difference Image Generation"
echo "==================================================="

# Define base paths
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl"
SUBLIST="/ZPOOL/data/projects/multiecho-pilot/code/sublist-openneuro.txt"

# Define acquisition types to iterate through
ACQ_TYPES=("mb1me4" "mb3me4" "mb6me4")

# Check if the subject list file exists
if [ ! -f "$SUBLIST" ]; then
    echo "Error: Subject list file not found at $SUBLIST"
    exit 1
fi

# Read subjects into an array
readarray -t SUBJECTS < "$SUBLIST"

# Iterate over each subject
for SUB_ID in "${SUBJECTS[@]}"; do
    echo "---------------------------------------------------"
    echo "Processing Subject: $SUB_ID"
    echo "---------------------------------------------------"

    # Iterate over each acquisition type
    for ACQ_TYPE in "${ACQ_TYPES[@]}"; do
        echo "  Processing Acquisition Type: $ACQ_TYPE"

        # Define input paths for base and tedana R-squared images
        BASE_R2_PATH="${BASE_DIR}/sub-${SUB_ID}/L1_task-sharedreward_model-1_type-act_acq-${ACQ_TYPE}_sm-0_denoising-base_r-square.feat/R-squared.nii.gz"
        TEDANA_R2_PATH="${BASE_DIR}/sub-${SUB_ID}/L1_task-sharedreward_model-1_type-act_acq-${ACQ_TYPE}_sm-0_denoising-tedana_r-square.feat/R-squared.nii.gz"

        # Define output directory and file for the difference image
        OUTPUT_DIR="${BASE_DIR}/sub-${SUB_ID}/L1_task-sharedreward_model-1_type-act_acq-${ACQ_TYPE}_sm-0_denoising-tedana_r-square.feat"
        OUTPUT_FILE="${OUTPUT_DIR}/R-squared_diff.nii.gz"

        # Check if base R-squared image exists
        if [ ! -f "$BASE_R2_PATH" ]; then
            echo "    Warning: Base R-squared image not found for sub-$SUB_ID, acq-$ACQ_TYPE at: $BASE_R2_PATH"
            continue # Skip to the next acquisition type
        fi

        # Check if tedana R-squared image exists
        if [ ! -f "$TEDANA_R2_PATH" ]; then
            echo "    Warning: Tedana R-squared image not found for sub-$SUB_ID, acq-$ACQ_TYPE at: $TEDANA_R2_PATH"
            continue # Skip to the next acquisition type
        fi

        # Ensure the output directory exists
        if [ ! -d "$OUTPUT_DIR" ]; then
            echo "    Creating output directory: $OUTPUT_DIR"
            mkdir -p "$OUTPUT_DIR"
        fi

        # Perform the subtraction using fslmaths: base_r2 - tedana_r2
        echo "    Calculating difference: $BASE_R2_PATH - $TEDANA_R2_PATH -> $OUTPUT_FILE"
        fslmaths "$BASE_R2_PATH" -sub "$TEDANA_R2_PATH" "$OUTPUT_FILE"

        # Check the exit status of fslmaths
        if [ $? -eq 0 ]; then
            echo "    Successfully created: $OUTPUT_FILE"
        else
            echo "    Error: fslmaths failed for sub-$SUB_ID, acq-$ACQ_TYPE. Check logs for details."
        fi
    done # End of ACQ_TYPES loop
    echo "" # Add a blank line for readability between subjects
done # End of SUBJECTS loop

echo "==================================================="
echo "R-squared Difference Image Generation Complete"
echo "==================================================="

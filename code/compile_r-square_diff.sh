#!/bin/bash

# This script compiles individual 3D r-square_diff.nii.gz images
# for a list of subjects into a single 4D NIfTI image using FSL's fslmerge.

echo "==================================================="
echo "Compiling r-square_diff images into a 4D NIfTI file"
echo "==================================================="

# --- Configuration ---
# Base directory for the FSL FEAT analysis derivatives.
# Adjust this path if your 'fsl_feat_pipeline_analysis' directory is elsewhere.
FEAT_DERIVATIVES_BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives"

# Path to the subject list file for randomise.
# This file should contain one subject ID (e.g., 10015) per line.
SUBLIST_FILE="/ZPOOL/data/projects/multiecho-pilot/code/sublist-randomise.txt"

# Output filename for the combined 4D NIfTI image.
# This will be created in the current directory where you run the script.
OUTPUT_4D_IMAGE="combined_r_square_diff_4D.nii.gz"

echo "FEAT derivatives base directory: ${FEAT_DERIVATIVES_BASE_DIR}"
echo "Subject list file: ${SUBLIST_FILE}"
echo "Output 4D image: ${OUTPUT_4D_IMAGE}"
echo "---------------------------------------------------"

# --- Validate Inputs ---
if [ ! -d "$FEAT_DERIVATIVES_BASE_DIR" ]; then
    echo "Error: FEAT derivatives base directory not found: ${FEAT_DERIVATIVES_BASE_DIR}"
    echo "Please update FEAT_DERIVATIVES_BASE_DIR in the script."
    exit 1
fi

if [ ! -f "$SUBLIST_FILE" ]; then
    echo "Error: Subject list file not found: ${SUBLIST_FILE}"
    echo "Please ensure sublist-randomise.txt exists at this path."
    exit 1
fi

# --- Collect Input Images ---
IMAGE_LIST=()
echo "Collecting individual r-square_diff images..."

# Read each subject ID from the sublist file
while IFS= read -r SUB_ID; do
    # Skip empty lines or lines with just whitespace
    if [[ -z "${SUB_ID// /}" ]]; then
        continue
    fi

    # Construct the path to the r-square_diff.nii.gz file for the current subject
    # Example path: /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl_feat_pipeline_analysis/sub-10024_sharedreward/feat/r-square_diff.nii.gz
    IMAGE_PATH="${FEAT_DERIVATIVES_BASE_DIR}/fsl/sub-${SUB_ID}/L1_task-sharedreward_model-1_type-act_acq-mb6me4_sm-0_denoising-tedana_r-square.feat/R-squared_diff.nii.gz"

    # Check if the image file exists
    if [ -f "$IMAGE_PATH" ]; then
        IMAGE_LIST+=("$IMAGE_PATH")
        echo "  Found: ${IMAGE_PATH}"
    else
        echo "  Warning: Image not found for sub-${SUB_ID}: ${IMAGE_PATH}" >&2
    fi
done < "$SUBLIST_FILE"

# --- Check if any images were found ---
if [ ${#IMAGE_LIST[@]} -eq 0 ]; then
    echo "Error: No r-square_diff.nii.gz images were found based on the provided subject list and path."
    echo "Please verify subject IDs and directory structure."
    exit 1
fi

echo "---------------------------------------------------"
echo "Found ${#IMAGE_LIST[@]} 3D images to combine."
echo "Running fslmerge..."

# --- Run fslmerge ---
# fslmerge -t combines images along the time dimension (creates a 4D image)
# The "${IMAGE_LIST[@]}" expands the array into separate arguments for fslmerge
fslmerge -t "$OUTPUT_4D_IMAGE" "${IMAGE_LIST[@]}"

# --- Check fslmerge exit status ---
if [ $? -eq 0 ]; then
    echo "---------------------------------------------------"
    echo "Successfully created 4D image: ${OUTPUT_4D_IMAGE}"
    echo "Total 3D volumes in 4D image: ${#IMAGE_LIST[@]}"
    echo "==================================================="
else
    echo "---------------------------------------------------"
    echo "Error: fslmerge failed. Please check the warnings above and FSL installation."
    echo "==================================================="
    exit 1
fi

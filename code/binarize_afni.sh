#!/bin/bash

# Script to binarize specific neuroimaging files and save them as masks
# Usage: ./binarize_afni.sh

# Set paths
SOURCE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/afni"
OUTPUT_DIR="/ZPOOL/data/projects/multiecho-pilot/masks"
PREFIX="mask_"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# List of images to binarize (plot=1 from your table)
declare -a IMAGES_TO_BINARIZE=(
    "LME_output_FWER_3way_FINAL.nii.gz"
    "LME_output_FWER_HCxME_bonf.nii.gz"
    "LME_output_FWER_MBxME.nii.gz"
    "LME_output_tsnr_MB3_vs_MB1_FDR.nii.gz"
    "LME_output_FWER_ME_bonf.nii.gz"
    "MB_main_ppi_zstat17_thresh.nii.gz"
    "MBxME_ppi_zstat17_thresh.nii.gz"
    "ME_main_ppi_zstat17_thresh.nii.gz"
    "overlap_ppi_zstat17_thr.nii.gz"
)

echo "Starting binarization of masks..."
echo "Source directory: $SOURCE_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Prefix: $PREFIX"
echo ""

# Counter for processed files
processed=0
errors=0

# Process each image
for image in "${IMAGES_TO_BINARIZE[@]}"; do
    input_file="$SOURCE_DIR/$image"
    
    # Create output filename with prefix
    output_file="$OUTPUT_DIR/${PREFIX}${image}"
    
    echo "Processing: $image"
    
    # Check if input file exists
    if [[ ! -f "$input_file" ]]; then
        echo "  ERROR: Input file not found: $input_file"
        ((errors++))
        continue
    fi
    
    # Run fslmaths to binarize (convert any non-zero values to 1)
    if fslmaths "$input_file" -bin "$output_file"; then
        echo "  SUCCESS: Created $output_file"
        ((processed++))
    else
        echo "  ERROR: fslmaths failed for $image"
        ((errors++))
    fi
    
    echo ""
done

# Summary
echo "=== SUMMARY ==="
echo "Files processed successfully: $processed"
echo "Errors encountered: $errors"
echo "Total files attempted: ${#IMAGES_TO_BINARIZE[@]}"

if [[ $errors -eq 0 ]]; then
    echo "All files processed successfully!"
    exit 0
else
    echo "Some files had errors. Please check the output above."
    exit 1
fi

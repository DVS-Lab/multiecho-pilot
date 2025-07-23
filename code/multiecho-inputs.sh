#!/bin/bash

# Set the base directory path
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/bids"
DERIVATIVES_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl"

# Create output file
output_file="combined_tsnr_coil_output.csv"

# Print the CSV header
echo "Subject,ReceiveCoilName,AcquisitionType,tsnrMean,tsnrMedian" > "$output_file"

# Loop through each subject's anat folder to find ReceiveCoilName
for anat_dir in "$BASE_DIR"/sub*/anat/; do
    if [ -d "$anat_dir" ]; then
        subject_id=$(basename "$(dirname "$anat_dir")" | sed 's/sub-//')
        coil_name=""
        for json_file in "$anat_dir"*.json; do
            if [ -f "$json_file" ]; then
                coil_name=$(grep -oP '"ReceiveCoilName"\s*:\s*"\K[^"]+' "$json_file" | sed 's/HeadNeck_//')
                break
            fi
        done

        # Check for .feat directories and process them
        for mbme in "mb1me1" "mb1me4" "mb2me4" "mb3me1" "mb3me1fa50" "mb3me3" "mb3me4" "mb3me4fa50" "mb6me1" "mb6me4"; do
            for feat_dir in "$DERIVATIVES_DIR"/sub-"$subject_id"/*"${mbme}"*.feat; do
                if [ -d "$feat_dir" ]; then
                    # Extract median tSNR and TR
                    tsnr_median=$(fslstats "$feat_dir/tsnr.nii.gz" -k "$feat_dir/mask.nii.gz" -p 50 2>/dev/null)
                    tsnr_mean=$(fslstats "$feat_dir/tsnr.nii.gz" -k "$feat_dir/mask.nii.gz" -m 2>/dev/null)
                    # Append to output file
                    echo "$subject_id,$coil_name,$mbme,$tsnr_median,$tsnr_mean" >> "$output_file"
                fi
            done
        done
    fi
done

# Display completion message
echo "Processing complete. Output saved to $output_file"

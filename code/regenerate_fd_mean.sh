#!/bin/bash

# This script calculates the nanmean of the 'framewise_displacement' column
# for specific subjects and acquisition types, and writes the results to a CSV file.

echo "==================================================="
echo "Calculating FD_mean for Missing Subjects/Acquisitions"
echo "and Writing to CSV"
echo "==================================================="

# --- Configuration ---
# Base directory where fmriprep output confounds files are located
FMRIPREP_BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fmriprep"

# List of subjects identified as having missing FD data
# (This list comes directly from your previous kernel's output)
SUBJECTS=(
    "10024" "10035" "10041" "10054" "10059" "10078" "10130" "10150"
    "10185" "10221" "10223" "10234" "10321" "10382" "10416" "10006"
    "10015" "10046" "10303" "10716" "10738" "10017"
)

# Acquisition types to process for these subjects
ACQ_TYPES=("mb1me4" "mb3me4" "mb6me4")

# Output CSV file path
# This will create the CSV in the current working directory where you run the script.
OUTPUT_CSV="missing_fd_mean_recalculated.csv"

echo "Processing FD_mean for the following subjects: ${SUBJECTS[*]}"
echo "For acquisition types: ${ACQ_TYPES[*]}"
echo "Results will be saved to: $OUTPUT_CSV"
echo "---------------------------------------------------"

# Create the CSV file and write the header
printf "subject,acquisition,fd_mean\n" > "$OUTPUT_CSV"

# Iterate over each subject
for SUB_ID in "${SUBJECTS[@]}"; do
    # Iterate over each acquisition type
    for ACQ_TYPE in "${ACQ_TYPES[@]}"; do
        # Construct the full path to the confounds TSV file
        CONFOUNDS_FILE="${FMRIPREP_BASE_DIR}/sub-${SUB_ID}/func/sub-${SUB_ID}_task-sharedreward_acq-${ACQ_TYPE}_part-mag_desc-confounds_timeseries.tsv"

        FD_MEAN_VALUE="NaN" # Default to NaN if file not found or error occurs

        # Check if the confounds file exists
        if [ -f "$CONFOUNDS_FILE" ]; then
            # Extract 'framewise_displacement' column and calculate nanmean using Python
            # awk -F'\t' sets tab as delimiter
            # NR==1 finds the header row and determines the column index (col_idx) for 'framewise_displacement'
            # NR>1 prints the value from that column for all subsequent rows
            # grep -v "n/a" filters out literal "n/a" strings (common for initial frames)
            # Python one-liner reads stdin, filters out 'NaN' strings and non-numeric,
            # converts to float, calculates nanmean, and prints.
            FD_DATA=$(awk -F'\t' '
                NR==1 {
                    for(i=1; i<=NF; i++) {
                        if($i=="framewise_displacement") {
                            col_idx=i;
                            break;
                        }
                    }
                }
                NR>1 {print $col_idx}
            ' "$CONFOUNDS_FILE" | grep -v "n/a" | python -c "
import numpy as np
import sys
# Read all non-empty lines from stdin, filter out 'NaN' string and convert to float
data = [float(x) for x in sys.stdin.read().splitlines() if x and x.strip().lower() != 'nan']
# Calculate nanmean; if data is empty after filtering, np.nanmean returns NaN
if data:
    print(np.nanmean(data))
else:
    print(np.nan)
")
            # Assign the calculated value, handling potential empty output if nanmean failed
            if [ -n "$FD_DATA" ]; then
                FD_MEAN_VALUE="$FD_DATA"
            fi
        else
            echo "Warning: Confounds file not found for sub-${SUB_ID}, acq-${ACQ_TYPE}: $CONFOUNDS_FILE" >&2 # Output warnings to stderr
        fi

        # Write the subject ID, acquisition type, and calculated fd_mean to the CSV file
        printf "%s,%s,%s\n" "${SUB_ID}" "${ACQ_TYPE}" "${FD_MEAN_VALUE}" >> "$OUTPUT_CSV"
    done # End of ACQ_TYPES loop
done # End of SUBJECTS loop

echo "==================================================="
echo "FD_mean Calculation and CSV Output Complete"
echo "==================================================="

#!/bin/bash

# Base directory
base_dir="/ZPOOL/data/projects/multiecho-pilot/bids"

# Print headers
printf "%-50s\t%-15s\t%-8s\t%-10s\n" "File" "Acquisition" "Echo" "EchoTime"
printf "%${COLUMNS}s\n" | tr ' ' '-'

# Find all matching JSON files
find "$base_dir" -path "*/sub-*/func/sub-*_task-sharedreward_acq-*_echo-*_part-mag_bold.json" | while read -r file; do
    # Extract acq and echo values from filename
    acq_value=$(echo "$file" | grep -o 'acq-[^_]*' | cut -d'-' -f2)
    echo_value=$(echo "$file" | grep -o 'echo-[^_]*' | cut -d'-' -f2)
    
    # Extract EchoTime value from JSON
    echo_time=$(grep -o '"EchoTime": [0-9.]*' "$file" | cut -d' ' -f2)
    
    # Print formatted output
    printf "%-50s\t%-15s\t%-8s\t%-10s\n" \
        "$(basename "$file")" "$acq_value" "$echo_value" "$echo_time"
done

#!/bin/bash

# Define the base directories
source_base="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-hpc"
destination_base="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl"

# Loop through all subject directories in the source directory
for sub in $(ls "$source_base"); do
    # Define the source and destination paths
    source_dir="${source_base}/${sub}/"
    destination_dir="${destination_base}/${sub}/"

    # Check if the source directory exists
    if [ -d "$source_dir" ]; then
        # Create the destination directory if it doesn't exist
        mkdir -p "$destination_dir"

        # Move the files
        mv "$source_dir"* "$destination_dir"

        echo "Moved files from $source_dir to $destination_dir"
    else
        echo "Source directory $source_dir does not exist. Skipping..."
    fi
done

echo "File transfer complete."

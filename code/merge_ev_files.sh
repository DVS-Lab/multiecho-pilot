#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

# Base directory for EVFiles
base_dir="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/EVFiles"

# Loop through each subject
for sub in `cat ${scriptdir}/sublist-all.txt`; do

    # Define the subject's base directory
    subj_dir="$base_dir/sub-${sub}/sharedreward"

    # Check if the subject's base directory exists
    if [ -d "$subj_dir" ]; then
        echo "Processing subject: $sub"

        # Loop through each subdirectory within the subject's sharedreward directory
        for sub_dir in "$subj_dir"/*/; do
            # Ensure sub_dir is a directory
            if [ -d "$sub_dir" ]; then
                echo "  Processing subdirectory: $sub_dir"

                # Merge _guess_leftButton_computer.txt and _guess_leftButton_face.txt
                cat "$sub_dir/_guess_leftButton_computer.txt" \
                    "$sub_dir/_guess_leftButton_face.txt" | \
                    sort -k1,1n > "$sub_dir/_guess_allLeftButton.txt"

                # Merge _guess_rightButton_computer.txt and _guess_rightButton_face.txt
                cat "$sub_dir/_guess_rightButton_computer.txt" \
                    "$sub_dir/_guess_rightButton_face.txt" | \
                    sort -k1,1n > "$sub_dir/_guess_allRightButton.txt"

                # Merge _outcome_computer_reward.txt, _outcome_computer_punish.txt, and _outcome_computer_neutral.txt
                cat "$sub_dir/_guess_leftButton_computer.txt" \
                    "$sub_dir/_guess_rightButton_computer.txt" | \
                    sort -k1,1n > "$sub_dir/_guess_allComputer.txt"

                # Merge _outcome_stranger_reward.txt, _outcome_stranger_punish.txt, and _outcome_stranger_neutral.txt
                cat "$sub_dir/_guess_leftButton_face.txt" \
                    "$sub_dir/_guess_rightButton_face.txt" | \
                    sort -k1,1n > "$sub_dir/_guess_allFace.txt"

                echo "    Finished processing subdirectory: $sub_dir"
            else
                echo "    Skipping non-directory: $sub_dir"
            fi
        done

        echo "Finished processing subject: $sub"
    else
        echo "Directory not found for subject: $sub. Skipping."
    fi
done

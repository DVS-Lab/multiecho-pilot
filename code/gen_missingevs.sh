#!/bin/bash

# Define the base directory
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/EVfiles"

# Define the list of files to be created
FILES=(
    "_guess_rightButton_computer.txt" "_guess_rightButton_face.txt" "_guess_leftButton_computer.txt" "_guess_leftButton_face.txt" "_miss_decision.txt" "_miss_outcome.txt" "_outcome_computer_neutral.txt" "_outcome_computer_punish.txt" "_outcome_computer_reward.txt" "_outcome_stranger_neutral.txt" "_outcome_stranger_punish.txt" "_outcome_stranger_reward.txt")

# Iterate through each subject directory with numeric IDs
for SUB_DIR in "$BASE_DIR"/sub-*; do
	# Check for sp subs
	sub_id=$(basename "$SUB_DIR")
	if [[ "$sub_id" == *sp ]]; then
		echo "$sub_id contains 'sp' suffix."
		acq=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3ip0" "mb3me4" "mb3me4fa50")
	else
		echo "$sub_id does not contain the 'sp' suffix."
		acq=("mb1me1" "mb1me4" "mb3me1" "me3me4" "mb6me1" "mb6me4")
	fi
	for EV_DIR in "${SUB_DIR}/sharedreward/${acq[@]}"; do
		# Check if the directory exists
    		if [ -d "$EV_DIR" ]; then
        		# Iterate through each file
        		for FILE in "${FILES[@]}"; do
            			# Define the full path to the file
            			FILE_PATH="$EV_DIR/$FILE"
            			# Check if the file already exists
            			if [ ! -f "$FILE_PATH" ]; then
                			# Create the file with the contents "0 0 0"
                			echo "0 0 0" > "$FILE_PATH"
                			echo "Created $FILE_PATH"
            			else
                			echo "$FILE_PATH already exists, skipping."
            			fi
        		done
    		else
        		echo "Directory $EV_DIR does not exist, skipping."
    		fi

	done
done

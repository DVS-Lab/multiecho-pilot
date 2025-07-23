import os

# Define the base directory where the subject folders are located
base_dir = "/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/"

# Define acquisition sets for regular and "sp" subjects
standard_acqs = ["mb1me1", "mb1me4", "mb3me1", "mb3me4", "mb6me1", "mb6me4"]
sp_acqs = ["mb3me4", "mb2me4", "mb3me1fa50", "mb3me3", "mb3me3ip0", "mb3me4fa50"]

# Loop through each item in the base directory
for sub in os.listdir(base_dir):
    sub_path = os.path.join(base_dir, sub)
    
    # Check if the item is a directory and starts with 'sub-'
    if os.path.isdir(sub_path) and sub.startswith("sub-"):
        # Determine which acquisition set to use
        acqs_to_check = sp_acqs if sub.endswith("sp") else standard_acqs
        
        # Loop through each acquisition we want to check
        for acq in acqs_to_check:
            # Define the path to the custom_timing_files directory
            timing_files_path = os.path.join(
                sub_path,
                f"L1_task-sharedreward_model-1_type-act_acq-{acq}_sm-4_denoising-base.feat",
                "custom_timing_files"
            )
            
            # Print the subject ID and acquisition ID
            print(f"Subject: {sub}, Acquisition: {acq}")
            print("Files:")
            
            # Check if the custom_timing_files directory exists
            if os.path.isdir(timing_files_path):
                # If the directory exists, loop through ev1.txt to ev12.txt and check each file
                for i in range(1, 13):
                    filename = f"ev{i}.txt"
                    file_path = os.path.join(timing_files_path, filename)
                    
                    # Check if the file exists and count rows if it does
                    if os.path.isfile(file_path):
                        with open(file_path, 'r') as f:
                            row_count = sum(1 for line in f)
                        print(f"  - {filename}: {row_count} rows")
                    else:
                        # If file doesn't exist, print NA
                        print(f"  - {filename}: NA")
            else:
                # If the custom_timing_files directory does not exist, print NA for each expected file
                for i in range(1, 13):
                    print(f"  - ev{i}.txt: NA")
                
            print("-" * 50)  # Separator for readability

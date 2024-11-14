import os
import pandas as pd

# Define the paths for the script and the data
script_dir = "/ZPOOL/data/projects/multiecho-pilot/code"
data_dir = "/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/"

# Initialize an empty list to store the data for each row in the spreadsheet
spreadsheet_data = []

# Loop through each subject folder in the derivatives directory
for sub in os.listdir(data_dir):
    sub_dir = os.path.join(data_dir, sub)
    
    # Ensure it is a directory matching the expected structure
    if not os.path.isdir(sub_dir) or not sub.startswith("sub-"):
        continue

    # Loop through each acquisition directory for this subject
    for acq in os.listdir(sub_dir):
        acq_path = os.path.join(sub_dir, acq, "L1_task-sharedreward_model-1_type-act_acq-{}_sm-4_denoising-base.feat/custom_timing_files".format(acq))
        
        # Ensure that the custom timing files directory exists
        if not os.path.isdir(acq_path):
            continue

        # Initialize a list for the current row, starting with the acquisition name
        row = [acq]

        # Loop through "ev1" to "ev12" to check each corresponding .txt file
        for ev_num in range(1, 13):
            ev_file_path = os.path.join(acq_path, f"ev{ev_num}.txt")
            
            # Check if the ev file exists
            if os.path.isfile(ev_file_path):
                # Count the number of rows in the file
                with open(ev_file_path, 'r') as file:
                    row_count = sum(1 for line in file if line.strip())  # count non-empty lines
                row.append(row_count)
            else:
                # Append 0 if the file is missing
                row.append(0)

        # Append the current row to the spreadsheet data
        spreadsheet_data.append(row)

# Create a DataFrame with appropriate column names
columns = ["acq"] + [f"ev{i}" for i in range(1, 13)]
df = pd.DataFrame(spreadsheet_data, columns=columns)

# Save the DataFrame to an Excel file
output_path = os.path.join(script_dir, "ev_file_row_counts.xlsx")
df.to_excel(output_path, index=False)

print(f"Spreadsheet created successfully at {output_path}")

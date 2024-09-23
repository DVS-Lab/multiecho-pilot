import json
import os

# Define paths
bidsdir = "/ZPOOL/data/projects/multiecho-pilot/bids/"
func_dir = "func"  # Directory containing the functional images

# Find all subject directories in the BIDS directory
subs = [d for d in os.listdir(bidsdir) if os.path.isdir(os.path.join(bidsdir, d)) and d.startswith('sub')]

for subj in subs:
    # Sub 10006 is missing func data
    if subj == 'sub-10006':
        continue

    print("Running subject:", subj)

    func_dir_path = os.path.join(bidsdir, subj, 'func')
    json_files = [f for f in os.listdir(func_dir_path) if f.endswith('bold.json') or f.endswith('sbref.json')]

    for json_file in json_files:
        json_path = os.path.join(func_dir_path, json_file)
        with open(json_path, 'r') as f:
            data = json.load(f)

            # Part phase images need to be arbitrary or rad
            if 'part-phase' in json_file:
                data["Units"] = "arbitrary"
            else:
                data["Units"] = "Hz"

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

        # Optionally print a message for confirmation
        # print("Updated units in", json_path)

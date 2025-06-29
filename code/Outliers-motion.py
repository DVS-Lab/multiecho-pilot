import numpy as np
import json
import pandas as pd
import os
import argparse
from scipy.stats import zscore
import re  # re will let us parse text in a nice way

bids_dir = "bids"  # Edit if necessary

# Check argument (input path)
parser = argparse.ArgumentParser(description="Give me a path to your mriqc output")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--mriqcDir', default=None, type=str, help="This is the path to your mriqc dir")
args = parser.parse_args()
mriqc_path = args.mriqcDir

all_subs = [s for s in os.listdir(bids_dir) if s.startswith('sub')]

# Make list of JSON files
j_files = []
for root, dirs, files in os.walk(mriqc_path):
    for f in files:
        if f.endswith('bold.json'):
            j_files.append(os.path.join(root, f))

keys = ['tsnr', 'fd_mean']  # The IQMs we might care about
sr = ['Sub', 'task', 'acq']

# Open an empty array and fill it
rows = []
for i in range(len(j_files)):
    sub = re.search('/mriqc/(.*)/func', j_files[i]).group(1)  # Parse the text for a string like sub-###
    task = re.search('task-(.*)_acq', j_files[i]).group(1)
    acq = re.search('_acq-(.*)_bold.json', j_files[i]).group(1)  # Parse for acquisition
    with open(j_files[i]) as f:  # Load the JSON file and extract the dictionary info
        data = json.load(f)
    now = [sub, task, acq] + [data[x] for x in keys]  # The currently created row in the loop
    rows.append(now)  # Append the row

df_full = pd.DataFrame(rows, columns=sr + keys)

for task in df_full.task.unique():
    print(f"Processing task: {task}")
    df = df_full[df_full['task'] == task]
    mriqc_subs = np.setdiff1d(all_subs, df.Sub.unique())
    print(f"Subjects missing MRIQC OUTPUT for task {task}: {mriqc_subs}")

    # Compute bounds for outliers
    Q1 = df[keys].quantile(0.25)
    Q3 = df[keys].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    upper.tsnr = upper.tsnr * 100  # Adjust for "too good" signal-to-noise ratio

    print("Upper and lower bounds for metrics:")
    print(lower.to_frame(name='lower').join(upper.to_frame(name='upper')))

    outList = (df[keys] < upper) & (df[keys] > lower)
    df['outlier_acq_Custom1'] = ~outList.all(axis='columns')

    print("Outlier acquisitions identified:")
    print(df[df['outlier_acq_Custom1']])

    # Save task-level outlier information
    df.to_csv(f'derivatives/Task-{task}_Level-Acq_Outlier-info_mriqc-0.16.1.tsv', sep='\t', index=False)

    # Compute good and bad subjects
    GS = df[df['outlier_acq_Custom1'] == False]
    GS = GS.Sub.value_counts().reset_index(name="count")
    GS.columns = ['Sub', 'count']
    print("Good subjects and their counts:")
    print(GS)

    GS = list(GS.query("count > 0")['Sub'])  # Keep good subjects
    BS = df[~df.Sub.isin(GS)]['Sub']

    # Covariate data for good subjects
    df_cov = df[df.Sub.isin(GS)]
    df_cov = df_cov[df_cov['outlier_acq_Custom1'] == False]
    df_cov = df_cov[['Sub'] + keys]
    df_cov[['tsnr', 'fd_mean']] = df_cov[['tsnr', 'fd_mean']].apply(zscore)
    # Filter only numeric columns for the mean computation
    print("Inspecting df_cov before aggregation...")
    print(df_cov.head())
    print(df_cov.info())

    # Select numeric columns for aggregation
    numeric_cols = df_cov.select_dtypes(include=[np.number]).columns
    df_cov = df_cov[['Sub'] + list(numeric_cols)]

    # Group by 'Sub' and compute the mean for numeric columns
    df_cov = df_cov.groupby(by='Sub').mean().reset_index()

    # Debugging step: Check the final output
    print("Aggregated covariate data:")
    print(df_cov.head())
    df_cov.to_csv(f'derivatives/Task-{task}_Level-Group_Covariates_mriqc-0.16.1.tsv', sep='\t', index=False)


    # Outliers information
    df_out = df[df.Sub.isin(BS)]
    df_out = df_out.Sub.value_counts().reset_index()
    df_out.columns = ['Sub', 'count']
    df_out = df_out.sort_values(by='count')
    df_out.to_csv(f'derivatives/Task-{task}_CustomSubOutlier_mriqc-0.16.1.tsv', sep='\t', index=False)
    print("Outliers saved to file.")

#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import os
import re

import pandas as pd
from tedana import workflows
import time

import argparse

parser = argparse.ArgumentParser(
    description='Give me a path to your fmriprep output and number of cores to run')
parser.add_argument('--fmriprepDir',default=None, type=str,help="This is the full path to your fmriprep dir")
parser.add_argument('--bidsDir',default=None, type=str,help="This is the full path to your BIDS directory")
parser.add_argument('--cores',default=None, type=int,help="This is the number of parallel jobs to run")

args = parser.parse_args()
#inputs

prep_data = args.fmriprepDir
bids_dir=args.bidsDir
cores=args.cores

# # Obtain Echo files

#find the prefix and suffix to that echo #
echo_images=[f for root, dirs, files in os.walk(prep_data)
             for f in files if ('_echo-' in f)& (f.endswith('_bold.nii.gz'))]

#Make a list of filenames that match the prefix
image_prefix_list=[re.search('(.*)_echo-',f).group(1) for f in echo_images]
image_prefix_list=set(image_prefix_list)

#Make a dataframe where C1 is Sub C2 is inputFiles and C3 is Echotimes
data=[]
for acq in image_prefix_list:
    print(acq)
    #Use RegEx to find Sub
    sub="sub-"+re.search('sub-(.*)_task',acq).group(1)
    
    #Make a list of the json's w/ appropriate header info from BIDS
    ME_headerinfo=[os.path.join(root, f) for root, dirs, files in os.walk(bids_dir) for f in files
               if (acq in f)& (f.endswith('_bold.json'))]
    
    #Read Echo times out of header info and sort
    echo_times=[json.load(open(f))['EchoTime'] for f in ME_headerinfo]
    echo_times.sort()
    
    #Find images matching the appropriate acq prefix
    acq_image_files=[os.path.join(root, f) for root, dirs, files in os.walk(prep_data) for f in files
              if (acq in f) & ('echo' in f) & (f.endswith('_desc-preproc_bold.nii.gz'))]
    acq_image_files.sort()

    confounds_file=[os.path.join(root, f) for root, dirs, files in os.walk(prep_data) for f in files
              if (acq in f) & (f.endswith('_desc-confounds_timeseries.tsv'))]

    out_dir= os.path.join(
        os.path.abspath(
            os.path.dirname( prep_data )), "tedana/%s"%(sub))

    #print(prep_data,out_dir)

    data.append([sub,acq,acq_image_files,echo_times,out_dir])

InData_df=pd.DataFrame(data=data,columns=['sub','acq','EchoFiles','EchoTimes','OutDir'])
args=zip(InData_df['sub'].tolist(),
         InData_df['acq'].tolist(),
         InData_df['EchoFiles'].tolist(),
         InData_df['EchoTimes'].tolist(),
         InData_df['OutDir'].tolist())

#Changes can be reasonably made to
#fittype: 'loglin' is faster but maybe less accurate than 'curvefit'
#tedpca:'mdl'Minimum Description Length returns the least number of components (default) and recommeded
#'kic' Kullback-Leibler Information Criterion medium aggression
# 'aic' Akaike Information Criterion least aggressive; i.e., returns the most components.
#gscontrol: post-processing to remove spatially diffuse noise. options implemented here are...
#global signal regression (GSR), minimum image regression (MIR),
#But anatomical CompCor, Go Decomposition (GODEC), and robust PCA can also be used


def RUN_Tedana(sub,prefix,EchoFiles,EchoTimes,OutDir):

    
    time.sleep(2)
    #print(sub,acq+'\n')
    
    if os.path.exists("%s/%s_desc-optcomDenoised_bold.nii.gz "%(OutDir,acq)):
        print('Tedana was previously run for Sub %s acq- %s remove directory if they need to be reanalyzed'%(sub,acq))
    else:
  
        os.makedirs(OutDir,exist_ok=True)
        print("Running TEDANA for %s"%(acq)+'\n')
        
        workflows.tedana_workflow(
	    EchoFiles,
	    EchoTimes,
	    out_dir=OutDir,
	    prefix="%s"%(prefix),
	    fittype="curvefit",
	    tedpca="kic",
	    verbose=True,
	    gscontrol=None)
    
from multiprocessing import Pool

pool = Pool(cores)
results = pool.starmap(RUN_Tedana, args)
    





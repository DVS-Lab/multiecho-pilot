#!/usr/bin/env python

import json
import os
import re
import pandas as pd
from tedana import workflows
import time
import argparse


# define function
def RUN_Tedana(sub,prefix,EchoFiles,EchoTimes,OutDir):
	previousFile = os.path.join(OutDir, "%s_desc-optcomDenoised_bold.nii.gz" % (acq))
	#print(previousFile)
	if os.path.exists(previousFile):
		print('WARNING: skipping since TEDANA output exists for %s ' % (acq))
	else: 	
		os.makedirs(OutDir,exist_ok=True)
		print("Running TEDANA for %s"%(acq)+'\n')
		
		workflows.tedana_workflow(
		EchoFiles, EchoTimes, out_dir=OutDir, prefix="%s"%(prefix), fittype="curvefit", tedpca="aic", gscontrol=None)
	    
	    # t2smap=fmriprep/func/sub-10188_task-sharedreward_acq-mb3me4_space-MNI152NLin6Asym_T2starmap.nii.gz

	    #verbose=True,
	    


# collect inputs
parser = argparse.ArgumentParser(
    description='Give me a path to your fmriprep output and number of cores to run')
parser.add_argument('--fmriprepDir',default=None, type=str,help="This is the full path to your fmriprep dir")
parser.add_argument('--bidsDir',default=None, type=str,help="This is the full path to your BIDS directory")
parser.add_argument('--sub',default=None, type=str, help="This is the subject number.")
args = parser.parse_args()
prep_data = args.fmriprepDir
bids_dir = args.bidsDir
sub = args.sub

#find the prefix and suffix to that echo #
echo_images=[f for root, dirs, files in os.walk(prep_data)
             for f in files if ('_echo-' in f)& (f.endswith('_bold.nii.gz'))]


#Make a list of filenames that match the prefix
image_prefix_list=[re.search('(.*)_echo-',f).group(1) for f in echo_images]
image_prefix_list=set(image_prefix_list)


# run tedana on each set of multi-echo images
for acq in image_prefix_list:
    #print(acq)
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

    out_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(bids_dir), '..', 'derivatives')), 'tedana/%s/%s'%(sub,acq))



    
    RUN_Tedana(sub,acq,acq_image_files,echo_times,out_dir)

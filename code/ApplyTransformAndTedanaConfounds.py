#!/usr/bin/env python
# coding: utf-8

# In[1]:


import ants
import matplotlib.pyplot as plt
import os
import re
cores=4


# In[2]:


fmriprep_dir='../derivatives/fmriprep/'
tedana_dir='../derivatives/tedana/'

bold_imgs=[os.path.join(root,f) for root,dirs,files in os.walk(tedana_dir) for f in files if f.endswith('desc-optcom_bold.nii.gz')]


# In[3]:


def auto_antstransform(img):
    sub='sub-'+re.search('/sub-(.*)/sub',img).group(1)
    task=re.search('task-(.*)_acq',img).group(1)
    acq=re.search('acq-(.*)_desc',img).group(1)
    

    output='%s/%s/func/%s_task-%s_acq-%s_desc-optcom-dewarped_bold.nii.gz'%(fmriprep_dir,sub,sub,task,acq)

    if not os.path.isfile(output):
        print('Applying Transforms: \n',sub,'task: '+task,'acquisition: '+acq)
        fixed = ants.image_read(
            '../masks/bg_image.nii') 
        moving = ants.image_read( 
            img)
        reg_bold2T1w='%s/%s/func/%s_task-%s_acq-%s_from-scanner_to-T1w_mode-image_xfm.txt'%(
            fmriprep_dir,sub,sub,task,acq)
        reg_t1w2MNI='%s/%s/anat/%s_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5'%(
            fmriprep_dir,sub,sub)

        mywarpedimage = ants.apply_transforms( fixed=fixed, moving=moving,imagetype=3,
                                                   transformlist=[reg_bold2T1w,reg_t1w2MNI] )
        mywarpedimage.to_filename(output)
    else:
        print(output+' already exists please remove if this nees to be re-run')


# In[4]:


from multiprocessing import Pool

pool = Pool(cores)
results = pool.map(auto_antstransform, bold_imgs)


# In[ ]:


import os
import pandas as pd
from natsort import natsorted
import re
import numpy as np


# In[5]:


metric_files = natsorted([os.path.join(root,f) for root,dirs,files in os.walk(
    '../derivatives/tedana/') for f in files if f.endswith("PCA_metrics.tsv")])
subs=set([re.search("tedana/(.*)/sub-",file).group(1) for file in metric_files])
for sub in subs:
    print(sub,"has %s acqs of denoised tedana"%(sum(sub in s for s in metric_files)))
for file in metric_files:
    #Read in the directory, sub-number, and acquisition
    base=re.search("(.*)PCA_metrics",file).group(1)
    sub=re.search("tedana/(.*)/sub-",file).group(1)
    acq=re.search("acq-(.*)_desc",file).group(1)
    #print(sub,acq)
    
    #import the data as dataframes
    fmriprep_fname="../derivatives/fmriprep/%s/func/%s_task-sharedreward_acq-%s_desc-confounds_timeseries.tsv"%(sub,sub,acq)
    if os.path.exists(fmriprep_fname):
        print("Making Counfounds: %s %s"%(sub,acq))
        fmriprep_confounds=pd.read_csv(fmriprep_fname,sep='\t')
        PCA_mixing=pd.read_csv('%sPCA_mixing.tsv'%(base),sep='\t')
        PCA_metrics=pd.read_csv('%sPCA_metrics.tsv'%(base),sep='\t')
        ICA_mixing=pd.read_csv('%sICA_mixing.tsv'%(base),sep='\t')
        ICA_metrics=pd.read_csv('%stedana_metrics.tsv'%(base),sep='\t')
        # Select columns from each data frame for final counfounds file
        ICA_mixing=ICA_mixing[ICA_metrics[ICA_metrics['classification']=='rejected']['Component']]
        PCA_mixing=PCA_mixing[PCA_metrics[PCA_metrics['classification']=='rejected']['Component']]

        cosine = [col for col in fmriprep_confounds if col.startswith('cosine')]
        NSS = [col for col in fmriprep_confounds if col.startswith('non_steady_state')]
        motion = ['trans_x','trans_y','trans_z','rot_x','rot_y','rot_z']
        fd = ['framewise_displacement']
        filter_col=np.concatenate([cosine,NSS,motion,fd])
        fmriprep_confounds=fmriprep_confounds[filter_col]

        #Combine horizontally
        Comp_confounds=pd.concat([ICA_mixing, PCA_mixing], axis=1)
        confounds_df=pd.concat([fmriprep_confounds, Comp_confounds], axis=1)
        #Output in fsl-friendly format
        outfname='../derivatives/fsl/confounds_tedana/%s/%s_task-sharedreward_acq-%s_desc-TedanaPlusConfounds.tsv'%(sub,sub,acq)
        confounds_df.to_csv(outfname,index=False,header=False,sep='\t')
    else:
        print("fmriprep failed for %s %s"%(sub,acq))


# In[ ]:





#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import os
import re
import json


# In[2]:
cwd = dir_path = os.path.dirname(os.path.realpath(__file__)) 
# bidsdir = os.path.join('%s/../bids'%(cwd))
bidsdir='/ZPOOL/data/projects/multiecho-pilot/bids/'

print(bidsdir)

event_files=[os.path.join(root,f) for root,dirs,files in os.walk(bidsdir) for f in files if f.endswith('events.tsv')]
#print(event_files)
data=[]
for file in event_files:
	sub='sub-'+re.search('func/sub-(.*)_task',file).group(1)
	acq=re.search('_acq-(.*)_events',file).group(1)
	tmp_df=pd.read_csv(file,sep='\t')
	print(tmp_df)
	if tmp_df.shape[0]>0:
		#print(sub,acq)
		tmp_df['sub']=sub
		tmp_df['acq']=acq
		data.append(tmp_df)
events_df=pd.concat(data)
#print(events_df)
# In[ ]:

#print(events_df['sub'].unique())

# In[ ]:

data=[]
for sub in events_df['sub'].unique():
    print(sub)
    for acq in events_df['acq'].unique():
        fname='%s/../derivatives/fsl/mcflirt/%s/%s/_abs.rms'%(cwd,sub,acq)
        if os.path.exists(fname):
            absolute=np.loadtxt(fname)

            if acq in ['mb1me4','mb3me4','mb6me4', 'mb3mb4fa50','mb3me3ip0','mb2me4','mb3me3']:
                f = open("%s/../derivatives/mriqc/%s/func/%s_task-sharedreward_acq-%s_echo-2_bold.json"%(cwd,sub,sub,acq))
            else:
                f = open("%s/../derivatives/mriqc/%s/func/%s_task-sharedreward_acq-%s_bold.json"%(cwd,sub,sub,acq))

            # returns JSON object as 
            # a dictionary
            FD = json.load(f)
            f.close
            FD=FD['fd_mean']
            #FD=np.loadtxt('%s/../derivatives/fsl/mcflirt/%s/%s/_rel.rms'%(cwd,sub,acq))

            row=[sub,acq,
                events_df[(events_df['sub']==sub)&(events_df['acq']==acq)]['trial_type'].str.count('miss_decision').sum(),
                absolute.max(),FD]
            data.append(row)

exclusions_df=pd.DataFrame(data=data,columns=['sub','acq','TrialCount_misses','Max_Abs_motion','FD_mean'])
exclusions_df['FD_exclusion']=exclusions_df['FD_mean']>0.5
exclusions_df['ABS_exclusion']=exclusions_df['Max_Abs_motion']>1.35
exclusions_df['Beh_TrialExclusion']=exclusions_df['TrialCount_misses']>27


# In[ ]:



results=exclusions_df.groupby(by='sub').sum().reset_index().rename(columns={"TrialCount_misses": "TotalCount_misses"})
results['Beh_TotalExclusion']=results['TotalCount_misses']>81
results=results[['sub','TotalCount_misses','Beh_TotalExclusion']]


# In[ ]:


exclusions_df.merge(results,on='sub')
exclusions_df.to_csv('../derivatives/exclusions.csv', index=False)


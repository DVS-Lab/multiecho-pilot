#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

for sub in `cat ${scriptdir}/sublist-all.txt` ; do

	# Print fslinfo for MB1ME4 sequence for each subs
	echo "sub-${sub}"	
	fslinfo ${maindir}/bids/sub-${sub}/func/sub-${sub}_task-sharedreward_acq-mb1me4_echo-1_part-mag_bold.nii.gz | grep 'dim[1-4]' | grep -v 'pixdim'

done



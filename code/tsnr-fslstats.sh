#!/bin/bash
# First echo statement is mean, second is median, third is TRs

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

for path in `cat ${scriptdir}/tsnr-acq.txt`; do
	#echo $(fslstats $path/tsnr.nii.gz -k $path/mask.nii.gz -m)
	#echo $(fslstats $path/tsnr.nii.gz -k $path/mask.nii.gz -p 50)
	echo $(fslval $path/stats/cope1.nii.gz pixdim4)
done

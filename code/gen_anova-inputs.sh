#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

for sub in `cat ${scriptdir}/sublist-20ch.txt`; do
	ls -1d ${basedir}/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-ppi_seed-VS_thr5_acq-mb*.feat/stats/cope13.nii.gz
done

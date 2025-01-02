#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

task=sharedreward # edit if necessary

for sub in `cat ${scriptdir}/sublist-all.txt`; do # `ls -d ${basedir}/derivatives/fmriprep/sub-*/`
	sub=${sub#*sub-}
	sub=${sub%/}

	if [[ $sub == *sp ]]; then
		acqs=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3fa50" "mb3me4" "mb3me4fa50")
	else
		acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")
	fi
	
	for mbme in "${acqs[@]}"; do
	
	  	# Manages the number of jobs and cores
	  	SCRIPTNAME=${basedir}/code/computeTSNRandSmoothness.sh
	  	NCORES=15
	  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
	    		sleep 5s
	  	done
	  	bash $SCRIPTNAME $sub $mbme &
		sleep 1s
	done
done

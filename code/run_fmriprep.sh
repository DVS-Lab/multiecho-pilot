#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

for sub in `cat ${scriptdir}/sublist-all.txt` ; do
#or sub in 10606sp 10391 10003 ; do
	script=${scriptdir}/fmriprep.sh
	NCORES=10
	while [ $(ps -ef | grep -v grep | grep $script | wc -l) -ge $NCORES ]; do
		sleep 1s
	done
	bash $script $sub &

done

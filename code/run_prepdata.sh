#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

#for sub in `cat ${scriptdir}/sublist_all.txt` ; do
for sub in 10006 10015 10017 10024 10028 10035 10041 10043 10046 10054 ; do

	script=${scriptdir}/prepdata.sh
	NCORES=40
	while [ $(ps -ef | grep -v grep | grep $script | wc -l) -ge $NCORES ]; do
		sleep 5s
	done
	bash $script $sub &
	sleep 5s

done



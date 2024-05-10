#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

for sub in `cat ${scriptdir}/sublist-all.txt` ; do

	# one at a time to avoid race conditions
	bash ${scriptdir}/prepdata.sh $sub

done



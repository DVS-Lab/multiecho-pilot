#!/bin/bash

# ensure paths are correct
maindir=~/work/multiecho-pilot #this should be the only line that has to change if the rest of the script is set up correctly
scriptdir=$maindir/code


mapfile -t myArray < ${scriptdir}/sublist-all.txt


# grab the first 10 elements
ntasks=2
counter=0
while [ $counter -lt ${#myArray[@]} ]; do
	subjects=${myArray[@]:$counter:$ntasks}
	echo $subjects
	let counter=$counter+$ntasks
	qsub -v subjects="${subjects[@]}" fmriprep-hpc.sh
done

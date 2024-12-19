#!/bin/bash

# ensure paths are correct
maindir=~/work/multiecho-pilot #this should be the only line that has to change if the rest of the script is set up correctly
scriptdir=$maindir/code


mapfile -t myArray < sublist_all.txt


# grab the first 10 elements
ntasks=2
counter=0

for denoise in "base"; do # "base" = aCompCor confounds; "tedana" = aCompCor + tedana
	for ppi in "VS_thr5"; do #"VS_thr5"; do #"VS_thr5"; do # putting 0 first will indicate "activation" "VS_thr5"
		for model in 1; do

			#for sub in 10137; do
			for sub in `cat ${scriptdir}/sublist-complete.txt`; do # `ls -d ${basedir}/derivatives/fmriprep/sub-*/`
				sub=${sub#*sub-}
				sub=${sub%/}

      		while [ $counter -lt ${#myArray[@]} ]; do
			subjects=${myArray[@]:$counter:$ntasks}
			echo $subjects
			let counter=$counter+$ntasks
			qsub -v subjects="${subjects[@]}" L1stats-hpc.sh
		done

			bash $SCRIPTNAME $sub $run $ppi $task &
	  		sleep 1s
			done	  	
	  	done
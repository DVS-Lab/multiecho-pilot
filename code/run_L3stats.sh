#!/bin/bash

# This run_* script is a wrapper for L3stats.sh, so it will loop over several
# copes and models. Note that Contrast N for PPI is always PHYS in these models.


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


# this loop defines the different types of analyses that will go into the group comparisons
for analysis in ppi_seed-VS_thr5; do # act ppi_seed-VS_thr5 nppi-dmn nppi-ecn ppi_seed %  ppi_seed-NAcc | type-${type}_run-01
	analysistype=type-${analysis}

	# these define the cope number (copenum) and cope name (copename)
#model-1	
	for copeinfo in "1 C_left" "2 C_right" "3 S_left" "4 S_right" "5 C_P" "6 C_N" "7 C_Rew" "8 S_P" "9 S_N" "10 S_Rew" "11 StrVsComp" "12 LeftVsRight" "13 RewVsPun" "14 RandPvsN" "15 RewVsNeu" "16 NeuVsPun"; do
#model-2
	#for copeinfo in "1 Left" "2 Right" "3 Left-Right"; do
#model-3
	#for copeinfo in "1 Str" "2 Comp" "3 Str-Comp"; do
		# split copeinfo variable
		set -- $copeinfo
		copenum=$1
		copename=$2

		if [ "${analysistype}" == "type-act" ] && [ "${copeinfo}" == "17 phys" ]; then
			echo "skipping phys for activation since it does not exist..."
			continue
		fi

		# rename copeinfo variable for activation and ppi analyses
		#if [ "${analysistype}" == "type-act" ] && [ "${copeinfo}" == "16 F-SC_rew-pun" ]; then
		#	copenum=16
		#	copename=F-SC_rew-pun
		if [ "${analysistype}" == "type-ppi_seed-NAcc" ] && [ "${copeinfo}" == "16 F-SC_rew-pun" ]; then
			copenum=16
			copename=F-SC_rew-pun
		elif [ "${analysistype}" == "type-ppi_seed-NAcc" ] && [ "${copeinfo}" == "17 phys" ]; then
			copenum=17
			copename=phys
		fi

		NCORES=12
		SCRIPTNAME=${maindir}/code/L3stats.sh
		while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
			sleep 1s
		done
		bash $SCRIPTNAME $copenum $copename $analysistype &

	done
done

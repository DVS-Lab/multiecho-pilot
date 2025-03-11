#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# setting inputs and common variables
sub=$1
type=$2
model=$3
denoising=$4
task=sharedreward # edit if necessary
sm=0 # edit if necessary
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}


# --- start EDIT HERE start: exceptions and conditionals for the task
NCOPES=16

# ppi has more contrasts than act (phys), so need a different L2 template
if [ "${type}" == "act" ]; then
	if [ ${sub} -eq 10084 ]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10084.fsf
	elif [ ${sub} -eq 10094 ]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10094.fsf
	elif [ ${sub} -eq 10438 ]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10438.fsf
	elif [[ ${sub} == 10741sp ]]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10741sp.fsf
	else
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act.fsf
	fi	
	NCOPES=${NCOPES}
elif [ "${type}" == "act" ] && [ "${model}" == "1" ]; then
	ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act.fsf
	NCOPES=${NCOPES}
	#10303 missing Input 4, 10185 missing Input 6, 10198 missing Input 1
	#need to make L2 templates for them, or remove them from design.fsf file for L2_model-1 and run again by hand
else
	ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-ppi.fsf
	let NCOPES=${NCOPES}+1 # add 1 since we tend to only have one extra contrast for PPI
fi

if [[ $sub == *sp ]]; then
        INPUT1=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb2me4_sm-${sm}_denoising-${denoising}.feat
        INPUT2=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me1fa50_sm-${sm}_denoising-${denoising}.feat
        INPUT3=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me3_sm-${sm}_denoising-${denoising}.feat
        INPUT4=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me3ip0_sm-${sm}_denoising-${denoising}.feat
        INPUT5=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me4_sm-${sm}_denoising-${denoising}.feat
        INPUT6=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me4fa50_sm-${sm}_denoising-${denoising}.feat
else
	INPUT1=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb1me1_sm-${sm}_denoising-${denoising}.feat
	INPUT2=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb1me4_sm-${sm}_denoising-${denoising}.feat
	INPUT3=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me1_sm-${sm}_denoising-${denoising}.feat
	INPUT4=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb3me4_sm-${sm}_denoising-${denoising}.feat
	INPUT5=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb6me1_sm-${sm}_denoising-${denoising}.feat
	INPUT6=${MAINOUTPUT}/L1_task-${task}_model-${model}_type-${type}_acq-mb6me4_sm-${sm}_denoising-${denoising}.feat
fi

# --- end EDIT HERE end: exceptions and conditionals for the task; need to exclude bad/missing runs


# check for existing output and re-do if missing/incomplete
OUTPUT=${MAINOUTPUT}/L2_task-${task}_model-${model}_type-${type}_sm-${sm}_denoising-${denoising}
if [ -e ${OUTPUT}.gfeat/cope${NCOPES}.feat/cluster_mask_zstat1.nii.gz ]; then # check last (act) or penultimate (ppi) cope
	echo "skipping existing output"
else
	echo "re-doing: ${OUTPUT}" >> re-runL2.log
	rm -rf ${OUTPUT}.gfeat


	# set output template and run template-specific analyses
	#for sub-10085 & 10438, run mb1me1 not motion outlier
	if [ ${sub} -eq 10085 ] || [ ${sub} -eq 10438 ]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10085.fsf
		OTEMPLATE=${MAINOUTPUT}/L2_task-${task}_model-${model}_type-${type}_denoising-${denoising}.fsf
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@INPUT2@'$INPUT2'@g' \
		-e 's@INPUT3@'$INPUT3'@g' \
		-e 's@INPUT4@'$INPUT4'@g' \
		-e 's@INPUT5@'$INPUT5'@g' \
		-e 's@INPUT6@'$INPUT6'@g' \
		<$ITEMPLATE> $OTEMPLATE
		feat $OTEMPLATE
	#for sub-10094, run mb1me1, mb3me1, mb3me4, mb6me4 motion outliers
	elif [ ${sub} -eq 10094 ]; then
		ITEMPLATE=${maindir}/templates/L2_task-${task}_model-${model}_type-act_10094.fsf
		OTEMPLATE=${MAINOUTPUT}/L2_task-${task}_model-${model}_type-${type}_denoising-${denoising}.fsf
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@INPUT1@'$INPUT1'@g' \
		-e 's@INPUT2@'$INPUT2'@g' \
		<$ITEMPLATE> $OTEMPLATE
		feat $OTEMPLATE
	#for sub-10743sp, run mb2me4 & mb3me1fa50 motion outliers
	elif [[ ${sub} == 10741sp ]]; then
		OTEMPLATE=${MAINOUTPUT}/L2_task-${task}_model-${model}_type-${type}_denoising-${denoising}.fsf
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@INPUT1@'$INPUT1'@g' \
		-e 's@INPUT2@'$INPUT2'@g' \
		-e 's@INPUT3@'$INPUT3'@g' \
		-e 's@INPUT4@'$INPUT4'@g' \
		<$ITEMPLATE> $OTEMPLATE
		feat $OTEMPLATE
	else
		OTEMPLATE=${MAINOUTPUT}/L2_task-${task}_model-${model}_type-${type}_denoising-${denoising}.fsf
		sed -e 's@OUTPUT@'$OUTPUT'@g' \
		-e 's@INPUT1@'$INPUT1'@g' \
		-e 's@INPUT2@'$INPUT2'@g' \
		-e 's@INPUT3@'$INPUT3'@g' \
		-e 's@INPUT4@'$INPUT4'@g' \
		-e 's@INPUT5@'$INPUT5'@g' \
		-e 's@INPUT6@'$INPUT6'@g' \
		<$ITEMPLATE> $OTEMPLATE
		feat $OTEMPLATE
	fi
	# delete unused files
	for cope in `seq ${NCOPES}`; do
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/res4d.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/corrections.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/threshac1.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/filtered_func_data.nii.gz
		rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/var_filtered_func_data.nii.gz
	done

fi

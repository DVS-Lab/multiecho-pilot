#!/usr/bin/env bash


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
istartdatadir=/ZPOOL/data/projects/multiecho-pilot #need to fix this upon release (no hard coding paths)

# study-specific inputs
TASK=sharedreward
sm=0
model=$1
sub=$2
mbme=$3
acq=${mbme}


# set inputs and general outputs (should not need to chage across studies in Smith Lab)
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT

if [ "$mbme" == "mb1me1" -o  "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "$mbme" == "mb3me1fa50" ]; then
	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
else
	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
fi

if [ ! -e $DATA ]; then
	echo ${sub} ${acq} "No data"
	exit
fi

#Handling different inputs for multi vs single echos
#if [ $me -gt 1 ];then
#echo "multiple echos"
#	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_desc-optcom-dewarped_bold.nii.gz
#else
#echo "single echo"
#	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
#fi

NVOLUMES=`fslnvols $DATA`
#OUR DATA won't have all the same TR
TR_INFO=`fslval $DATA pixdim4`

if [ ${denoise} == "tedana" ]; then
	CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds_tedana/sub-${sub}/sub-${sub}_task-${TASK}_acq-${acq}_desc-TedanaPlusConfounds.tsv
	echo ${denoise}
	echo ${CONFOUNDEVS}
fi


if [ ! -e $CONFOUNDEVS ]; then
	echo ${sub} ${acq} "missing confounds"
	echo "missing confounds: $CONFOUNDEVS " >> ${maindir}/re-runL1.log
	exit # exiting to ensure nothing gets run without confounds
fi

#echo ${TR_INFO}

EVDIR=${maindir}/derivatives/fsl/EVFiles/sub-${sub}/${TASK}/acq-${acq} #
if [ ! -e $EVDIR ]; then
	echo ${sub} ${acq} "EVDIR missing"
	echo "missing events files: $EVDIR " >> ${maindir}/re-runL1.log
	exit # exiting to ensure nothing gets run without confounds
fi

# empty EVs (specific to this study)
EV_MISSED_DEC=${EVDIR}/_miss_decision.txt
if [ -e $EV_MISSED_DEC ]; then
	SHAPE_MISSED_DEC=3
else
	SHAPE_MISSED_DEC=10
fi

EV_MISSED_OUTCOME=${EVDIR}/_miss_outcome.txt
if [ -e $EV_MISSED_OUTCOME ]; then
	SHAPE_MISSED_OUTCOME=3
else
	SHAPE_MISSED_OUTCOME=10
fi
LB_comp=${EVDIR}/_guess_leftButton_computer.txt
if [ -e $LB_comp ]; then
	SHAPE_LB_comp=3
else
	SHAPE_LB_comp=10
fi
RB_comp=${EVDIR}/_guess_rightButton_computer.txt
if [ -e $RB_comp ]; then
	SHAPE_RB_comp=3
else
	SHAPE_RB_comp=10
fi
LB_face=${EVDIR}/_guess_leftButton_face.txt
if [ -e $LB_face ]; then
	SHAPE_LB_face=3
else
	SHAPE_LB_face=10
fi
RB_face=${EVDIR}/_guess_rightButton_face.txt
if [ -e $RB_face ]; then
	SHAPE_RB_face=3
else
	SHAPE_RB_face=10
fi


# set output based in whether it is activation or ppi
if [ "$ppi" == "0" ]; then
	TYPE=act
	OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-${TYPE}_acq-${acq}_sm-${sm}_denoising-${denoise}
	OTEMPLATE=${MAINOUTPUT}/tSNRandSmoothness_model-${model}_type-${TYPE}_acq-${acq}_sm-${sm}_denoising-${denoise}.fsf
fi

# check for output and skip existing
if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
	exit
else
	echo "missing feat output: $OUTPUT " >> ${maindir}/re-runL1.log
	rm -rf ${OUTPUT}.feat
fi
    
# create template and run analyses
ITEMPLATE=${maindir}/templates/L1_task-${TASK}_model-${model}_type-${TYPE}.fsf
sed -e 's@OUTPUT@'$OUTPUT'@g' \
-e 's@DATA@'$DATA'@g' \
-e 's@EVDIR@'$EVDIR'@g' \
-e 's@SMOOTH@'$sm'@g' \
-e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
-e 's@NVOLUMES@'$NVOLUMES'@g' \
-e 's@SHAPE_MISSED_DEC@'$SHAPE_MISSED_DEC'@g' \
-e 's@SHAPE_MISSED_OUTCOME@'$SHAPE_MISSED_OUTCOME'@g' \
-e 's@TR_INFO@'"$TR_INFO"'@g' \
<$ITEMPLATE> $OTEMPLATE
feat $OTEMPLATE

# extract smoothness and tSNR
fslmaths ${OUTPUT}.feat/filtered_func_data.nii.gz -Tmean ${OUTPUT}.feat/func_mean
fslmaths ${OUTPUT}.feat/filtered_func_data.nii.gz -Tstd ${OUTPUT}.feat/func_std
fslmaths ${OUTPUT}.feat/func_mean -div ${OUTPUT}.feat/func_std ${OUTPUT}.feat/tsnr

rm -rf ${OUTPUT}.feat/3dFWHMx.1D ${OUTPUT}.feat/3dFWHMx.1D.png
3dFWHMx -geom -mask ${OUTPUT}.feat/mask.nii.gz -input ${OUTPUT}.feat/stats/res4d.nii.gz -ShowMeClassicFWHM > ${OUTPUT}.feat/smoothness.txt


# delete unused files
rm -rf ${OUTPUT}.feat/stats/res4d.nii.gz
rm -rf ${OUTPUT}.feat/stats/corrections.nii.gz
rm -rf ${OUTPUT}.feat/stats/threshac1.nii.gz
rm -rf ${OUTPUT}.feat/filtered_func_data.nii.gz

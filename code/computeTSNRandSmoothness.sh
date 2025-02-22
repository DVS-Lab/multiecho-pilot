#!/usr/bin/env bash


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
istartdatadir=/ZPOOL/data/projects/multiecho-pilot #need to fix this upon release (no hard coding paths)

# study-specific inputs
TASK=sharedreward
sm=5
model=1 #probably will need to adjust this for some subjects with missing EVs
sub=$1
mbme=$2
acq=${mbme}
ppi=0
denoise=base


# set inputs and general outputs (should not need to chage across studies in Smith Lab)
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT

if [ "$mbme" == "mb1me1" -o "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "$mbme" == "mb3me1fa50" ]; then
	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold_${sm}mm.nii.gz
	RAWDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
else
	DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold_${sm}mm.nii.gz
	RAWDATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
fi

if [ ! -e $DATA ]; then
	echo "NO DATA: ${DATA}"
	exit
fi


NVOLUMES=`fslnvols $DATA`
#OUR DATA won't have all the same TR
TR_INFO=`fslval $DATA pixdim4`

if [ ${denoise} == "base" ]; then
	if [ "$mbme" == "mb1me1" -o  "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "${mbme}" == "mb3me1fa50" ]; then
	    CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${mbme}_desc-confounds_acq-${mbme}_desc-confounds_desc-fslConfounds.tsv
	else
	    CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${mbme}_part-mag_desc-confounds_acq-${mbme}_part-mag_desc-confounds_desc-fslConfounds.tsv
	fi	
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
if [ -e ${OUTPUT}.feat/smoothness.txt ]; then
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

# extract from smoothed data
rm -rf ${OUTPUT}.feat/3dFWHMx.1D ${OUTPUT}.feat/3dFWHMx.1D.png
3dFWHMx -detrend -ACF -mask ${OUTPUT}.feat/mask.nii.gz -input ${DATA} > ${OUTPUT}.feat/smoothness-5mm.txt
rm -rf ${scriptdir}/3dFWHMx.1D ${scriptdir}/3dFWHMx.1D.png

# extract from raw data
rm -rf ${OUTPUT}.feat/3dFWHMx.1D ${OUTPUT}.feat/3dFWHMx.1D.png
3dFWHMx -detrend -ACF -mask ${OUTPUT}.feat/mask.nii.gz -input ${RAWDATA} > ${OUTPUT}.feat/smoothness-0mm.txt
rm -rf ${scriptdir}/3dFWHMx.1D ${scriptdir}/3dFWHMx.1D.png



# delete unused files
rm -rf ${OUTPUT}.feat/stats/res4d.nii.gz
rm -rf ${OUTPUT}.feat/stats/corrections.nii.gz
rm -rf ${OUTPUT}.feat/stats/threshac1.nii.gz
rm -rf ${OUTPUT}.feat/filtered_func_data.nii.gz

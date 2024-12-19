#!/bin/bash
#PBS -l walltime=12:00:00
#PBS -N L1stats-trust-all
#PBS -q normal
#PBS -m ae
#PBS -M cooper.sharp@temple.edu
#PBS -l nodes=1:ppn=28

# load modules and go to workdir
cd $PBS_O_WORKDIR

# ensure paths are correct
istartdatadir=/home/tun31934/work/multiecho-pilot # Adjust this path as needed
scriptdir=$istartdatadir/code
bidsdir=$istartdatadir/bids
logdir=$istartdatadir/logs
mkdir -p $logdir

rm -f $logdir/cmd_feat_${PBS_JOBID}.txt
touch $logdir/cmd_feat_${PBS_JOBID}.txt

# study-specific inputs
TASK=sharedreward
sm=4
model=$1
sub=$2
mbme=$3
ppi=$4 # 0 for activation, otherwise seed region or network
acq=${mbme}
denoise=$5

# Define acquisition arrays
if [[ $sub == *sp ]]; then
    acqs=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3fa50" "mb3me4" "mb3me4fa50")
else
    acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")
fi

# Loop through subjects and acquisitions
for sub in ${subjects[@]}; do
    for mbme in "${acqs[@]}"; do

        # Set inputs and general outputs
        MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
        mkdir -p $MAINOUTPUT

        if [[ "$mbme" == "mb1me1" || "$mbme" == "mb3me1" || "$mbme" == "mb6me1" || "$mbme" == "mb3me1fa50" ]]; then
            DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
        else
            DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
        fi

        # Check if data exists
        if [ ! -e $DATA ]; then
            echo "${sub} ${acq} No data"
            exit
        fi

        NVOLUMES=$(fslnvols $DATA)
        TR_INFO=$(fslval $DATA pixdim4)

        if [[ ${denoise} == "tedana" ]]; then
            CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds_tedana/sub-${sub}/sub-${sub}_task-${TASK}_acq-${acq}_desc-TedanaPlusConfounds.tsv
        elif [[ ${denoise} == "base" ]]; then
            if [[ "$mbme" == "mb1me1" || "$mbme" == "mb3me1" || "$mbme" == "mb6me1" || "$mbme" == "mb3me1fa50" ]]; then
                CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${acq}_desc-confounds.tsv
            else
                CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${acq}_part-mag_desc-confounds.tsv
            fi
        fi

        if [ ! -e $CONFOUNDEVS ]; then
            echo "${sub} ${acq} missing confounds"
            echo "Missing confounds: $CONFOUNDEVS" >> ${maindir}/re-runL1.log
            exit
        fi

        EVDIR=${maindir}/derivatives/fsl/EVFiles/sub-${sub}/${TASK}/acq-${acq}
        if [ ! -e $EVDIR ]; then
            echo "${sub} ${acq} EVDIR missing"
            echo "Missing events files: $EVDIR" >> ${maindir}/re-runL1.log
            exit
        fi

        # Handle missing EVs
        EV_MISSED_DEC=${EVDIR}/_miss_decision.txt
        SHAPE_MISSED_DEC=$( [ -e $EV_MISSED_DEC ] && echo 3 || echo 10 )

        EV_MISSED_OUTCOME=${EVDIR}/_miss_outcome.txt
        SHAPE_MISSED_OUTCOME=$( [ -e $EV_MISSED_OUTCOME ] && echo 3 || echo 10 )

        LB_comp=${EVDIR}/_guess_leftButton_computer.txt
        SHAPE_LB_comp=$( [ -e $LB_comp ] && echo 3 || echo 10 )

        RB_comp=${EVDIR}/_guess_rightButton_computer.txt
        SHAPE_RB_comp=$( [ -e $RB_comp ] && echo 3 || echo 10 )

        LB_face=${EVDIR}/_guess_leftButton_face.txt
        SHAPE_LB_face=$( [ -e $LB_face ] && echo 3 || echo 10 )

        RB_face=${EVDIR}/_guess_rightButton_face.txt
        SHAPE_RB_face=$( [ -e $RB_face ] && echo 3 || echo 10 )

        # Determine whether to perform network-based PPI or activation
        if [[ "$ppi" == "ecn" || "$ppi" == "dmn" ]]; then
            OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-nppi-${ppi}_acq-${acq}_sm-${sm}_denoising-${denoise}
            if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
                echo "${OUTPUT} already exists, skipping to next subject"
                continue
            else
                echo "Missing feat output: $OUTPUT" >> ${maindir}/re-runL1.log
                rm -rf ${OUTPUT}.feat
            fi

            # Create template for network-based PPI
            ITEMPLATE=${maindir}/templates/L1_task-${TASK}_model-${model}_type-nppi.fsf
            OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_seed-${ppi}_acq-${acq}.fsf

            # Run analyses
            sed -e "s@OUTPUT@$OUTPUT@g" \
                -e "s@DATA@$DATA@g" \
                -e "s@EVDIR@$EVDIR@g" \
                -e "s@SHAPE_MISSED_DEC@$SHAPE_MISSED_DEC@g" \
                -e "s@SHAPE_MISSED_OUTCOME@$SHAPE_MISSED_OUTCOME@g" \
                -e "s@CONFOUNDEVS@$CONFOUNDEVS@g" \
                -e "s@NVOLUMES@$NVOLUMES@g" \
                -e "s@TR_INFO@$TR_INFO@g" \
                <$ITEMPLATE> $OTEMPLATE

            feat $OTEMPLATE
        fi

        echo "feat $OTEMPLATE" >> $logdir/cmd_feat_${PBS_JOBID}.txt
    done
done

torque-launch -p $logdir/chk_feat_${PBS_JOBID}.txt $logdir/cmd_feat_${PBS_JOBID}.txt

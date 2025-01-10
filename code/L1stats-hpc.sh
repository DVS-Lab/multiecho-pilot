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
istartdatadir=/gpfs/scratch/tug87422/smithlab-shared/multiecho-pilot # Adjust this path as needed
scriptdir=$istartdatadir/code
bidsdir=$istartdatadir/bids
logdir=$istartdatadir/logs
mkdir -p $logdir

rm $scriptdir/L1stats-trust-all.*

rm -f $logdir/cmd_feat_${PBS_JOBID}.txt
touch $logdir/cmd_feat_${PBS_JOBID}.txt

# study-specific inputs
TASK=sharedreward
sm=4
model=1
ppi="0" # 0 for activation, otherwise seed region or network
denoise="base"

# set inputs and general outputs (should not need to chage across studies in Smith Lab)
MAINOUTPUT=${istartdatadir}/derivatives/fsl/sub-${sub}
mkdir -p $MAINOUTPUT

# Loop through subjects and acquisitions
for sub in ${subjects[@]}; do
    if [[ $sub == *sp ]]; then
        acqs=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3fa50" "mb3me4" "mb3me4fa50" "mb3me3ip0")
    else
        acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")
    fi

    for mbme in "${acqs[@]}"; do
        # Set inputs and general outputs
        MAINOUTPUT=${istartdatadir}/derivatives/fsl/sub-${sub}
        mkdir -p $MAINOUTPUT

        if [ "$mbme" == "mb1me1" -o  "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "$mbme" == "mb3me1fa50" ]; then
            DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${mbme}_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
        else
            DATA=${istartdatadir}/derivatives/fmriprep/sub-${sub}/func/sub-${sub}_task-${TASK}_acq-${mbme}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz
        fi

        # Check if data exists
        if [ ! -e $DATA ]; then
            echo "${sub} ${mbme} No data"
            continue
        fi

        NVOLUMES=$(fslnvols $DATA)
        #OUR DATA won't have all the same TR
        TR_INFO=$(fslval $DATA pixdim4)

        #NVOLUMES=274
        #TR_INFO=1.615000

        if [ ${denoise} == "tedana" ]; then
            CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds_tedana/sub-${sub}/sub-${sub}_task-${TASK}_acq-${mbme}_desc-TedanaPlusConfounds.tsv
            echo ${denoise}
            echo ${CONFOUNDEVS}
        fi

        if [ ${denoise} == "base" ]; then
            if [ "$mbme" == "mb1me1" -o  "$mbme" == "mb3me1" -o "$mbme" == "mb6me1" -o "${mbme}" == "mb3me1fa50" ]; then
                CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${mbme}_desc-confounds_acq-${mbme}_desc-confounds_desc-fslConfounds.tsv
            else
                CONFOUNDEVS=${istartdatadir}/derivatives/fsl/confounds/sub-${sub}/sub-${sub}_task-${TASK}_acq-${mbme}_part-mag_desc-confounds_acq-${mbme}_part-mag_desc-confounds_desc-fslConfounds.tsv
            fi
            echo ${denoise}
            echo ${CONFOUNDEVS}
        fi

        if [ ! -e $CONFOUNDEVS ]; then
            echo ${sub} ${mbme} "missing confounds"
            echo "missing confounds: $CONFOUNDEVS $NVOLUMES $TR_INFO" >> ${istartdatadir}/re-runL1.log
            continue # exiting to ensure nothing gets run without confounds
        fi

        EVDIR=${istartdatadir}/derivatives/fsl/EVFiles/sub-${sub}/${TASK}/acq-${mbme} #
        if [ ! -e $EVDIR ]; then
            echo ${sub} ${mbme} "EVDIR missing"
            echo "missing events files: $EVDIR " >> ${istartdatadir}/re-runL1.log
            continue # exiting to ensure nothing gets run without confounds
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

        # if network (ecn or dmn), do nppi; otherwise, do activation or seed-based ppi
        if [ "$ppi" == "ecn" -o  "$ppi" == "dmn" ]; then
            # check for output and skip existing
            OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-nppi-${ppi}_acq-${mbme}_sm-${sm}_denoising-${denoise}
            if [ -e ${OUTPUT}.feat/cluster_mask_zstat1.nii.gz ]; then
                echo "${OUTPUT} already exists, skipping to next sub"
                exit
            else
                echo "missing feat output: $OUTPUT " >> ${istartdatadir}/re-runL1.log
                rm -rf ${OUTPUT}.feat
            fi

            # network extraction. need to ensure you have run Level 1 activation
            MASK=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-act_acq-${mbme}_sm-${sm}.feat/mask
            if [ ! -e ${MASK}.nii.gz ]; then
                echo "cannot run nPPI because you're missing $MASK"
                exit
            fi

            for net in `seq 0 9`; do
                NET=${istartdatadir}/masks/nan_rPNAS_2mm_net000${net}.nii.gz
                TSFILE=${MAINOUTPUT}/ts_task-${TASK}_net000${net}_nppi-${ppi}_acq-${mbme}.txt
                fsl_glm -i $DATA -d $NET -o $TSFILE --demean -m $MASK
                eval INPUT${net}=$TSFILE
            done

            # set names for network ppi (we generally only care about ECN and DMN)
            DMN=$INPUT3
            ECN=$INPUT7
            if [ "$ppi" == "dmn" ]; then
                MAINNET=$DMN
                OTHERNET=$ECN
            else
                MAINNET=$ECN
                OTHERNET=$DMN
            fi

            # create template and run analyses
            ITEMPLATE=${istartdatadir}/templates/L1_task-${TASK}_model-${model}_type-nppi.fsf
            OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_seed-${ppi}_acq-${mbme}.fsf
            sed -e 's@OUTPUT@'$OUTPUT'@g' \
                -e 's@DATA@'$DATA'@g' \
                -e 's@EVDIR@'$EVDIR'@g' \
                -e 's@SHAPE_MISSED_DEC@'$SHAPE_MISSED_DEC'@g' \
                -e 's@SHAPE_MISSED_OUTCOME@'$SHAPE_MISSED_OUTCOME'@g' \
                -e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
                -e 's@MAINNET@'$MAINNET'@g' \
                -e 's@OTHERNET@'$OTHERNET'@g' \
                -e 's@INPUT0@'$INPUT0'@g' \
                -e 's@INPUT1@'$INPUT1'@g' \
                -e 's@INPUT2@'$INPUT2'@g' \
                -e 's@INPUT4@'$INPUT4'@g' \
                -e 's@INPUT5@'$INPUT5'@g' \
                -e 's@INPUT6@'$INPUT6'@g' \
                -e 's@INPUT8@'$INPUT8'@g' \
                -e 's@INPUT9@'$INPUT9'@g' \
                -e 's@NVOLUMES@'$NVOLUMES'@g' \
                -e 's@TR_INFO@'"$TR_INFO"'@g' \
                <$ITEMPLATE> $OTEMPLATE
            feat $OTEMPLATE
        else # otherwise, do activation and seed-based ppi
            # set output based in whether it is activation or ppi
            if [ "$ppi" == "0" ]; then
                TYPE=act
                OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-${TYPE}_acq-${mbme}_sm-${sm}_denoising-${denoise}
                OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-${TYPE}_acq-${mbme}_sm-${sm}_denoising-${denoise}.fsf
            else
                TYPE=ppi
                OUTPUT=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-${TYPE}_seed-${ppi}_acq-${mbme}_sm-${sm}_denoising-${denoise}
                OTEMPLATE=${MAINOUTPUT}/L1_task-${TASK}_model-${model}_type-${TYPE}_seed-${ppi}_acq-${mbme}_sm-${sm}_denoising-${denoise}.fsf
            fi

            # create template and run analyses
            ITEMPLATE=${istartdatadir}/templates/L1_task-${TASK}_model-${model}_type-${TYPE}.fsf
            if [ "$ppi" == "0" ]; then
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
            else
                PHYS=${MAINOUTPUT}/ts_task-${TASK}_mask-${ppi}_acq-${mbme}.txt
                MASK=${istartdatadir}/masks/seed-${ppi}.nii.gz
                fslmeants -i $DATA -o $PHYS -m $MASK
                sed -e 's@OUTPUT@'$OUTPUT'@g' \
                    -e 's@DATA@'$DATA'@g' \
                    -e 's@EVDIR@'$EVDIR'@g' \
                    -e 's@SHAPE_MISSED_DEC@'$SHAPE_MISSED_DEC'@g' \
                    -e 's@SHAPE_MISSED_OUTCOME@'"$SHAPE_MISSED_OUTCOME"'@g' \
                    -e 's@SHAPE_LB_comp@'$SHAPE_LB_comp'@g' \
                    -e 's@SHAPE_RB_comp@'$SHAPE_RB_comp'@g' \
                    -e 's@SHAPE_LB_face@'$SHAPE_LB_face'@g' \
                    -e 's@SHAPE_RB_face@'$SHAPE_RB_face'@g' \
                    -e 's@PHYS@'$PHYS'@g' \
                    -e 's@_SMOOTH_@'$sm'@g' \
                    -e 's@CONFOUNDEVS@'$CONFOUNDEVS'@g' \
                    -e 's@NVOLUMES@'$NVOLUMES'@g' \
                    -e 's@TR_INFO@'"$TR_INFO"'@g' \
                    <$ITEMPLATE> $OTEMPLATE
            fi
        fi

        echo "feat $OTEMPLATE" >> $logdir/cmd_feat_${PBS_JOBID}.txt
    done
done

torque-launch -p $logdir/chk_feat_${PBS_JOBID}.txt $logdir/cmd_feat_${PBS_JOBID}.txt

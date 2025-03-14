#!/bin/bash

# ensure paths are correct irrespective of where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

input=beta # tsnr, beta, or zstat

for denoise in "tedana"; do # "base" "tedana" 
  for mask in "VS_constrained" "VMPFC"; do # "rightMotor" "leftCerebellum" "leftMotor" "rightCerebellum" "rFFA"; do
    for ppi in "act"; do
      for sub in $(cat ${scriptdir}/sublist-included.txt); do 
        sub=${sub#*sub-}
        sub=${sub%/}

        if [[ "$sub" == *sp ]]; then
          acqs=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3ip0" "mb3me4" "mb3me4fa50")
        else
          acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")
        fi
        
        for mbme in "${acqs[@]}"; do
          # Define tsnr, beta, & zstat images
          if [[ "$mask" == "VS_constrained" ]] || [[ "$mask" == "VMPFC" ]]; then
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/cope13.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/zstat13.nii.gz"
          elif [[ "$mask" == "rightMotor" ]] || [[ "$mask" == "leftCerebellum" ]]; then
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/zstat3.nii.gz"
          elif [[ "$mask" == "leftMotor" ]] || [[ "$mask" == "rightCerebellum" ]]; then
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-4_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-4_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/zstat3.nii.gz"
          elif [[ "$mask" == "rFFA" ]]; then
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-3_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-3_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-3_type-${ppi}_acq-${mbme}_sm-4_denoising-${denoise}.feat/stats/zstat3.nii.gz"
          else
            echo "Invalid mask: $mask"
            continue
          fi

          if [[ "$input" == "tsnr" ]]; then
            input_image="$tsnr_image"
          elif [[ "$input" == "beta" ]]; then
            input_image="$beta_image"
          elif [[ "$input" == "zstat" ]]; then
            input_image="$zstat_image"
          else
            echo "Invalid input type: $input"
            exit 1
          fi

          if [[ -f "$input_image" ]]; then
		fslmeants -i "$input_image" -m /ZPOOL/data/projects/multiecho-pilot/masks/mask_${mask}.nii.gz -o "/ZPOOL/data/projects/multiecho-pilot/derivatives/extractions/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-${mask}_denoise_${denoise}.txt"
	else
  		echo "Warning: Input file $input_image does not exist. Skipping."
	fi
        done
      done
    done
  done
done

#!/bin/bash

# ensure paths are correct irrespective of where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

input=tsnr # tsnr, beta, or zstat

for denoise in "base"; do # "base" "tedana" 
  for mask in "VSconstrained" "VMPFC" "rightMotor" "leftMotor" "rightCerebellum" "leftCerebellum" "rFFA"; do
  #for mask in "leftMotor" "rightMotor" "leftCerebellum" "rightCerebellum"; do
  #for mask in "leftMotor"; do
    for ppi in "act"; do # "act" "ppi_seed-VS"
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
          if [[ "$mask" == "VSconstrained" ]] || [[ "$mask" == "VMPFC" ]]; then
            #tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-act_acq-${mbme}_sm-5_denoising-base_forTSNR.feat/tsnr.nii.gz"
	    beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/cope13.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/zstat13.nii.gz"
          elif [[ "$mask" == "rightMotor" ]] || [[ "$mask" == "leftCerebellum" ]]; then
            #tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-act_acq-${mbme}_sm-5_denoising-base_forTSNR.feat/tsnr.nii.gz"
	    beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-2_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/zstat3.nii.gz"
          elif [[ "$mask" == "leftMotor" ]] || [[ "$mask" == "rightCerebellum" ]]; then
            #tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-act_acq-${mbme}_sm-5_denoising-base_forTSNR.feat/tsnr.nii.gz"
	    beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-4_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-4_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/zstat3.nii.gz"
          elif [[ "$mask" == "rFFA" ]]; then
            #tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl-archive-2/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-5_denoising-${denoise}_EstimateSmoothing.feat/tsnr.nii.gz"
            tsnr_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-act_acq-${mbme}_sm-5_denoising-base_forTSNR.feat/tsnr.nii.gz"
	    beta_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-3_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/cope3.nii.gz"
            zstat_image="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-3_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats/zstat3.nii.gz"
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

# After the main loop, create bilateral averaged outputs
echo "Creating bilateral outputs..."

# Process each subject and acquisition
for sub in $(cat ${scriptdir}/sublist-included.txt); do 
  sub=${sub#*sub-}
  sub=${sub%/}
  
  if [[ "$sub" == *sp ]]; then
    acqs=("mb2me4" "mb3me1fa50" "mb3me3" "mb3me3ip0" "mb3me4" "mb3me4fa50")
  else
    acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")
  fi
  
  for mbme in "${acqs[@]}"; do
    for ppi in "act"; do
      # Define the output paths
      output_dir="/ZPOOL/data/projects/multiecho-pilot/derivatives/extractions"
      
      # Process bilateral Motor cortex (left + right)
      left_motor="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-leftMotor_denoise_${denoise}.txt"
      right_motor="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-rightMotor_denoise_${denoise}.txt"
      bilateral_motor="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-bilateralMotor_denoise_${denoise}.txt"
      
      # Process bilateral Cerebellum (left + right)
      left_cereb="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-leftCerebellum_denoise_${denoise}.txt"
      right_cereb="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-rightCerebellum_denoise_${denoise}.txt"
      bilateral_cereb="${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-bilateralCerebellum_denoise_${denoise}.txt"
      
      # Average Motor cortex values if both files exist
      if [[ -f "$left_motor" && -f "$right_motor" ]]; then
        echo "Averaging left and right motor for sub-${sub}, acq-${mbme}"
        # Use paste to combine files side by side, then awk to calculate the average
        paste "$left_motor" "$right_motor" | awk '{print ($1 + $2) / 2}' > "$bilateral_motor"
      else
        echo "Warning: Cannot create bilateral motor output for sub-${sub}, acq-${mbme} (missing files)"
      fi
      
      # Average Cerebellum values if both files exist
      if [[ -f "$left_cereb" && -f "$right_cereb" ]]; then
        echo "Averaging left and right cerebellum for sub-${sub}, acq-${mbme}"
        # Use paste to combine files side by side, then awk to calculate the average
        paste "$left_cereb" "$right_cereb" | awk '{print ($1 + $2) / 2}' > "$bilateral_cereb"
      else
        echo "Warning: Cannot create bilateral cerebellum output for sub-${sub}, acq-${mbme} (missing files)"
      fi
    done
  done
done

echo "Processing complete!"

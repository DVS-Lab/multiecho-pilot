#!/bin/bash

# Extract cope13, varcope13, and zstat13 from each subject's first-level PPI .feat
# directory using the 5 whole-brain zstat13 cluster masks.

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="/ZPOOL/data/projects/multiecho-pilot"

denoise="base"
ppi="ppi_seed-VS_thr5"
acqs=("mb1me1" "mb1me4" "mb3me1" "mb3me4" "mb6me1" "mb6me4")

masks=(
	"HCxMBxME_ppi_zstat13_cluster1"
	"MBxME_ppi_zstat13_cluster1"
	"HCxME_ppi_zstat13_cluster1"
	"HCxMB_ppi_zstat13_cluster1"
	"ME_ppi_zstat13_cluster1"
)

mask_dir="${basedir}/derivatives/fsl/afni"
output_dir="${basedir}/derivatives/extractions"
mkdir -p "${output_dir}"

for mask in "${masks[@]}"; do
	for input in "beta" "varcope" "zstat"; do
		for sub in $(cat ${scriptdir}/sublist-included.txt); do
			sub=${sub#*sub-}
			sub=${sub%/}

			for mbme in "${acqs[@]}"; do
				feat_dir="${basedir}/derivatives/fsl/sub-${sub}/L1_task-sharedreward_model-1_type-${ppi}_acq-${mbme}_sm-0_denoising-${denoise}.feat/stats"

				if [[ "$input" == "beta" ]]; then
					input_image="${feat_dir}/cope13.nii.gz"
				elif [[ "$input" == "varcope" ]]; then
					input_image="${feat_dir}/varcope13.nii.gz"
				elif [[ "$input" == "zstat" ]]; then
					input_image="${feat_dir}/zstat13.nii.gz"
				fi

				if [[ -f "$input_image" ]]; then
					echo "Extracting sub-${sub} acq-${mbme} img-${input} mask-${mask}"
					fslmeants -i "$input_image" \
						-m "${mask_dir}/${mask}.nii.gz" \
						-o "${output_dir}/ts_sub-${sub}_acq_${mbme}_type-${ppi}_img-${input}_mask-${mask}_denoise_${denoise}.txt"
				else
					echo "Warning: Missing ${input_image}"
				fi
			done
		done
	done
done

echo "Extraction complete!"

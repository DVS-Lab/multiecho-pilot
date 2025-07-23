#!/usr/bin/env bash


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


### -- Estimate models

# ppi phys regressor
3dLMEr -prefix /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat17 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_ppi-zstat17.txt


# ppi reward > punish
3dLMEr -prefix /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat13 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_ppi-zstat13.txt


# act reward > punish
3dLMEr -prefix /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_act-zstat13 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_act-zstat13.txt



### -- PPI cope17 effects (phys regressor)

# MB3 vs MB1
3dFWHMx -mask brain_mask.nii.gz -acf \
  -input /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat17+tlrc'[8]' \
  > acf_MB3_vs_MB1_ppi_zstat17.txt

# MB6 vs MB1
3dFWHMx -mask brain_mask.nii.gz -acf \
  -input /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat17+tlrc'[10]' \
  > acf_MB6_vs_MB1_ppi_zstat17.txt

# ME4 vs ME1
3dFWHMx -mask brain_mask.nii.gz -acf \
  -input /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat17+tlrc'[12]' \
  > acf_ME4_vs_ME1_ppi_zstat17.txt

# HC vs 20ch
3dFWHMx -mask brain_mask.nii.gz -acf \
  -input /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-zstat17+tlrc'[14]' \
  > acf_HC_vs_20ch_ppi_zstat17.txt



3dClustSim -mask brain_mask.nii.gz \
           -acf 0.892078 2.12894 14.2735 \
           -prefix ClustSim_ppi_zstat17_bonf \
           -pthr 0.05 -athr 0.00714




# HC main effect
3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 0 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map HC_main_ppi_zstat17_thresh
#nothing

# MB main effect
3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 1 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map MB_main_ppi_zstat17_thresh

# ME main effect
3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 2 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map ME_main_ppi_zstat17_thresh


# 2-way interactions
3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 3 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map HCxMB_ppi_zstat17_thresh
# nothing here

3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 4 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map HCxME_ppi_zstat17_thresh
# nothing here

3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 5 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map MBxME_ppi_zstat17_thresh

# 3-way interactions
3dClusterize -inset LME_output_ppi-zstat17+tlrc \
             -ithr 6 -NN 1 -clust_nvox 78 -bisided p=0.05 \
             -pref_map 3way_ppi_zstat17_thresh
# nothing here


3dAFNItoNIFTI -prefix MB_main_ppi_zstat17_thresh.nii.gz MB_main_ppi_zstat17_thresh+tlrc
3dAFNItoNIFTI -prefix ME_main_ppi_zstat17_thresh.nii.gz ME_main_ppi_zstat17_thresh+tlrc
3dAFNItoNIFTI -prefix MBxME_ppi_zstat17_thresh.nii.gz MBxME_ppi_zstat17_thresh+tlrc


mricron L3_model-1_task-sharedreward_n40_mixedeffects-flame1+2_denoising-base/L3_task-sharedreward_type-act_cnum-01_cname-C_left_onegroup_denoising-base.gfeat/mean_func.nii.gz &

# striatum in all three, so this could be something to plot



### -- PPI cope13 effects (reward > punish ppi)
# summary: nothing here

3dFWHMx -input LME_output_ppi-zstat13+tlrc'[8]'  -mask brain_mask.nii.gz -acf > acf_MB3_vs_MB1_ppi_zstat13.txt
3dFWHMx -input LME_output_ppi-zstat13+tlrc'[10]' -mask brain_mask.nii.gz -acf > acf_MB6_vs_MB1_ppi_zstat13.txt
3dFWHMx -input LME_output_ppi-zstat13+tlrc'[12]' -mask brain_mask.nii.gz -acf > acf_ME4_vs_ME1_ppi_zstat13.txt
3dFWHMx -input LME_output_ppi-zstat13+tlrc'[14]' -mask brain_mask.nii.gz -acf > acf_HC_vs_20ch_ppi_zstat13.txt



for effect in MB3_vs_MB1 MB6_vs_MB1 ME4_vs_ME1 HC_vs_20ch; do
  file="acf_${effect}_ppi_zstat13.txt"
  if [[ -f "$file" ]]; then
    echo "Effect: $effect"
    awk 'NR==2 { printf "ACF params: %.6f  %.6f  %.6f\n\n", $1, $2, $3 }' "$file"
  else
    echo "Missing: $file"
  fi
done


3dClustSim -mask brain_mask.nii.gz \
           -acf 0.960875 2.092270 18.485800 \
           -prefix ClustSim_ppi_zstat13_bonf \
           -pthr 0.05 -athr 0.00714


# MB main effect
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 1 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map MB_main_ppi_zstat13_thresh

# ME main effect
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 2 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map ME_main_ppi_zstat13_thresh

# HC main effect
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 0 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map HC_main_ppi_zstat13_thresh

# MB × ME interaction
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 5 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map MBxME_ppi_zstat13_thresh

# HC × MB interaction
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 3 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map HCxMB_ppi_zstat13_thresh

# HC × ME interaction
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 4 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map HCxME_ppi_zstat13_thresh

# 3-way interaction
3dClusterize -inset LME_output_ppi-zstat13+tlrc \
             -ithr 6 -NN 1 -clust_nvox 40 -bisided p=0.05 \
             -pref_map 3way_ppi_zstat13_thresh

# NOTHING WITH COPE13 on PPI



### -- activation cope13 effects (reward > punish )


3dFWHMx -input LME_output_act-zstat13+tlrc'[8]' -mask brain_mask.nii.gz -acf > acf_MB3_vs_MB1_act_zstat13.txt
3dFWHMx -input LME_output_act-zstat13+tlrc'[10]' -mask brain_mask.nii.gz -acf > acf_MB6_vs_MB1_act_zstat13.txt
3dFWHMx -input LME_output_act-zstat13+tlrc'[12]' -mask brain_mask.nii.gz -acf > acf_ME4_vs_ME1_act_zstat13.txt
3dFWHMx -input LME_output_act-zstat13+tlrc'[14]' -mask brain_mask.nii.gz -acf > acf_HC_vs_20ch_act_zstat13.txt


# get smoothness
for effect in MB3_vs_MB1 MB6_vs_MB1 ME4_vs_ME1 HC_vs_20ch; do
  file="acf_${effect}_act_zstat13.txt"
  if [[ -f "$file" ]]; then
    echo "Effect: $effect"
    awk 'NR==2 { printf "ACF params: %.6f  %.6f  %.6f\n\n", $1, $2, $3 }' "$file"
  else
    echo "Missing: $file"
  fi
done


3dClustSim -mask brain_mask.nii.gz \
           -acf 0.821032 2.107260 18.687500 \
           -prefix ClustSim_act_zstat13_bonf \
           -pthr 0.05 -athr 0.00714


# Bonferroni-corrected cluster threshold = 191 voxels
THRESH=0.05
CLUST=191
INSET=LME_output_act-zstat13+tlrc

3dClusterize -inset $INSET -ithr 0 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map HC_main_act13_thresh
3dClusterize -inset $INSET -ithr 1 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map MB_main_act13_thresh
3dClusterize -inset $INSET -ithr 2 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map ME_main_act13_thresh
3dClusterize -inset $INSET -ithr 3 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map HCxMB_act13_thresh
3dClusterize -inset $INSET -ithr 4 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map HCxME_act13_thresh
3dClusterize -inset $INSET -ithr 5 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map MBxME_act13_thresh
3dClusterize -inset $INSET -ithr 6 -NN 1 -clust_nvox $CLUST -bisided p=$THRESH -pref_map HCxMBxME_act13_thresh





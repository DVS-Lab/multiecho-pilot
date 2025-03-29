#!/usr/bin/env bash


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


## Estimate models

# ppi phys regressor
3dLMEr -prefix ${maindir}/derivatives/fsl/LME_output_ppi-cope17 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_ppi-cope17.txt


# ppi reward > punish
3dLMEr -prefix /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_ppi-cope13 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_ppi-cope13.txt


# act reward > punish
3dLMEr -prefix /ZPOOL/data/projects/multiecho-pilot/derivatives/fsl/LME_output_act-cope13 \
      -jobs 8 \
      -model "HC+MB+ME+HC:MB+HC:ME+MB:ME+HC:MB:ME+(1|Subj)" \
      -gltCode MB3_vs_MB1 "MB : +1*MB3 -1*MB1" \
      -gltCode MB6_vs_MB1 "MB : +1*MB6 -1*MB1" \
      -gltCode ME4_vs_ME1 "ME : +1*ME4 -1*ME1" \
      -gltCode HC_vs_20ch "HC : +1*64ch -1*20ch" \
      -dataTable @LME_table_corrected_act-cope13.txt



## PPI phys post-hoc tests

3dFWHMx -input LME_output_ppi-cope17+tlrc'[6]'         -mask brain_mask.nii.gz         -acf > acf_3way.txt
3dFWHMx -input LME_output_ppi-cope17+tlrc'[8]' -mask brain_mask.nii.gz -acf > acf_MB3_vs_MB1.txt
3dFWHMx -input LME_output_ppi-cope17+tlrc'[12]' -mask brain_mask.nii.gz -acf > acf_ME4_vs_ME1.txt
3dFWHMx -input LME_output_ppi-cope17+tlrc'[1]' -mask brain_mask.nii.gz -acf > acf_MB_main.txt
3dFWHMx -input LME_output_ppi-cope17+tlrc'[2]' -mask brain_mask.nii.gz -acf > acf_ME_main.txt
3dFWHMx -input LME_output_ppi-cope17+tlrc'[6]' -mask brain_mask.nii.gz -acf > acf_3way.txt
3dFWHMx -mask brain_mask.nii.gz -acf -input LME_output_ppi-cope13+tlrc'[8]' > acf_MB3_vs_MB1_cope13.txt
3dFWHMx -mask brain_mask.nii.gz -acf -input LME_output_ppi-cope13+tlrc'[10]' > acf_MB6_vs_MB1_cope13.txt
3dFWHMx -mask brain_mask.nii.gz -acf -input LME_output_ppi-cope13+tlrc'[12]' > acf_ME4_vs_ME1_cope13.txt
3dFWHMx -mask brain_mask.nii.gz -acf -input LME_output_ppi-cope13+tlrc'[14]' > acf_HC_vs_20ch_cope13.txt


3dClustSim -mask brain_mask.nii.gz \
           -acf 0.879067 2.13714 13.4847 \
           -prefix ClustSim_safest

3dClusterize -inset LME_output_ppi-cope17+tlrc \
             -ithr 6 -NN 1 -clust_nvox 60 -bisided p=0.05 \
             -pref_map LME_output_FWER_3way_FINAL


# 2-way interactions
3dClusterize -inset LME_output_ppi-cope17+tlrc \
             -ithr 3 -NN 1 -clust_nvox 60 -bisided p=0.05 \
             -pref_map LME_output_FWER_HCxMB
# nothing here


3dClusterize -inset LME_output_ppi-cope17+tlrc \
             -ithr 4 -NN 1 -clust_nvox 60 -bisided p=0.05 \
             -pref_map LME_output_FWER_HCxME

3dClusterize -inset LME_output_ppi-cope17+tlrc \
             -ithr 5 -NN 1 -clust_nvox 60 -bisided p=0.05 \
             -pref_map LME_output_FWER_MBxME

3dAFNItoNIFTI -prefix LME_output_FWER_HCxMB.nii.gz LME_output_FWER_HCxMB+tlrc # skip
3dAFNItoNIFTI -prefix LME_output_FWER_HCxME.nii.gz LME_output_FWER_HCxME+tlrc
3dAFNItoNIFTI -prefix LME_output_FWER_MBxME.nii.gz LME_output_FWER_MBxME+tlrc




# take care of multiple comparisons


3dClustSim -mask brain_mask.nii.gz \
           -acf 0.879067 2.13714 13.4847 \
           -prefix ClustSim_bonf \
           -pthr 0.05 \
           -athr 0.00714

cat ClustSim_bonf.NN1_bisided.1D

3dClusterize -inset LME_output_ppi-cope17+tlrc \
             -ithr 5 -NN 1 -clust_nvox 88 -bisided p=0.05 \
             -pref_map LME_output_FWER_MBxME_bonf


for fname in HC MB ME HCxMB HCxME MBxME 3way; do
  3dAFNItoNIFTI -prefix LME_output_FWER_${fname}_bonf.nii.gz LME_output_FWER_${fname}_bonf+tlrc
done



3dClustSim -mask brain_mask.nii.gz \
           -acf 0.925349 1.92623 14.7885 \
           -prefix ClustSim_cope13_ppi \
           -pthr 0.05 -athr 0.00714


# no effects for cope-13_PPI


3dinfo -verb LME_output_act-cope13+tlrc.HEAD





# Cope 13 for activation
# MB3 vs MB1 Z-stat = sub-brick [8]
3dFWHMx -input LME_output_act-cope13+tlrc'[8]' -mask brain_mask.nii.gz -acf > acf_MB3_vs_MB1_act_cope13.txt

# MB6 vs MB1 Z-stat = sub-brick [10]
3dFWHMx -input LME_output_act-cope13+tlrc'[10]' -mask brain_mask.nii.gz -acf > acf_MB6_vs_MB1_act_cope13.txt

# ME4 vs ME1 Z-stat = sub-brick [12]
3dFWHMx -input LME_output_act-cope13+tlrc'[12]' -mask brain_mask.nii.gz -acf > acf_ME4_vs_ME1_act_cope13.txt

# HC vs 20ch Z-stat = sub-brick [14]
3dFWHMx -input LME_output_act-cope13+tlrc'[14]' -mask brain_mask.nii.gz -acf > acf_HC_vs_20ch_act_cope13.txt

3dClustSim -mask brain_mask.nii.gz \
           -acf 3.70353 3.83141 3.86924 \
           -prefix ClustSim_act_cope13 \
           -pthr 0.05 -athr 0.00714


# main effects and interactions
# HC main effect
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 0 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map HC_main_act13_thresh

# MB main effect
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 1 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map MB_main_act13_thresh

# ME main effect
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 2 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map ME_main_act13_thresh

# HC × MB interaction
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 3 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map HCxMB_act13_thresh

# HC × ME interaction
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 4 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map HCxME_act13_thresh

# MB × ME interaction
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 5 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map MBxME_act13_thresh

# HC × MB × ME interaction
3dClusterize -inset LME_output_act-cope13+tlrc \
             -ithr 6 -NN 1 -clust_nvox 159 -bisided p=0.05 \
             -pref_map HCxMBxME_act13_thresh


# no significnat whole-brain results for activation (cope 13) or PPI (cope 13)







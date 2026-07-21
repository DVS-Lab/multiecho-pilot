# Acquisition metadata audit

## 1. Executive summary

This audit separates complete-dataset evidence from the public release and uses JSON/TSV metadata as primary evidence. NIfTI geometry is used only when image content is already available.

Complete-source statuses: DATA_SOURCE_UNAVAILABLE=41, SUPPORTED=1.

Public-source statuses: CONTRADICTED=4, NOT_REPRESENTED_IN_DATASET=1, NOT_VERIFIABLE_FROM_METADATA=5, PARTIALLY_SUPPORTED=12, SUPPORTED=20.

## 2. Data sources and access

| label | identity | root | access | participants | JSON | TSV | NIfTI available | NIfTI pointers/unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete |  | /ZPOOL/data/projects/multiecho-pilot/bids | BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids | 0 | 0 | 0 | 0 | 0 |
| local_repository |  | /Users/tug87422/github/multiecho-pilot/bids | BIDS root inspected directly | 64 | 0 | 430 | 0 | 0 |
| openneuro | doi:10.18112/openneuro.ds005085.v1.0.0 | /private/tmp/ds005085-metadata-audit-20260720 | BIDS root inspected directly | 10 | 408 | 55 | 0 | 399 |

No imaging content was fetched by this program.

## 3. Scope of the complete Linux1 dataset

`complete` was unavailable at `/ZPOOL/data/projects/multiecho-pilot/bids`.

## 4. Scope of the public OpenNeuro release

Source `openneuro` (Sequence pilot: multiecho and multiband fMRI; doi:10.18112/openneuro.ds005085.v1.0.0; 1.8.0) at `/private/tmp/ds005085-metadata-audit-20260720` contains 10 participant identifiers, 44 participant-acquisition BOLD units, and acquisition labels: mb1me1, mb1me4, mb3me1, mb3me4, mb6me1, mb6me4.
The inventory contains 408 JSON files, 55 TSV files, 399 NIfTI entries, 0 locally available NIfTI files, and 399 unavailable pointer entries.

## 5. Functional acquisition parameters

| dataset_source | acquisition_label | participant_count | bold_file_count | observed_echo_count | echo_times_s | repetition_time_s | multiband_acceleration_factor | flip_angle_deg | number_of_slices | nifti_voxel_dimensions_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openneuro | mb1me1 | 8 | 8 | 1 | 0.03 | 1.7 \| 3.39 |  | 20 | 27 (SliceTiming; header unavailable) \| 51 (SliceTiming; header unavailable) |  |
| openneuro | mb1me4 | 7 | 28 | 4 | 0.0138; 0.03154; 0.04928; 0.06702 | 4.71 |  | 20 | 50 (SliceTiming; header unavailable) |  |
| openneuro | mb3me1 | 7 | 7 | 1 | 0.03 | 1.15 \| 1.7 | 3 | 20 | 51 (SliceTiming; header unavailable) |  |
| openneuro | mb3me4 | 8 | 32 | 4 | 0.0138; 0.03154; 0.04928; 0.06702 | 1.615 | 3 | 20 | 51 (SliceTiming; header unavailable) |  |
| openneuro | mb6me1 | 7 | 7 | 1 | 0.03 | 0.626 \| 1.7 | 6 | 20 | 54 (SliceTiming; header unavailable) |  |
| openneuro | mb6me4 | 7 | 28 | 4 | 0.014; 0.0321; 0.0502; 0.0683 | 0.878 | 6 | 20 | 54 (SliceTiming; header unavailable) |  |

`bold_file_count` counts magnitude or no-part sidecars and excludes phase sidecars. Full parameter sets and source paths are in `acquisition_parameters.tsv`.

## 6. Structural acquisition parameters

| dataset_source | participant_count | repetition_time_s | echo_times_s | flip_angle_deg | nifti_matrix_dimensions | nifti_voxel_dimensions_mm | base_resolution | acquisition_matrix_pe | recon_matrix_pe | slice_thickness_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openneuro | 10 | 2.4 | 0.00217 | 8 |  |  | 224 | 224 | 224 | 1 |

## 7. Field-map parameters

| dataset_source | acquisition_label | participant_count | echo_times_s | repetition_time_s | flip_angle_deg | number_of_slices | nifti_matrix_dimensions | base_resolution | acquisition_matrix_pe | recon_matrix_pe | slice_thickness_mm | spacing_between_slices_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openneuro | fmap-bold-run-1 | 10 | 0.00492; 0.00738 | 0.645 | 60 | 54 (SliceTiming; header unavailable) |  | 80 \| 86 | 62 \| 80 | 80 \| 86 | 2.7 | 2.97 |
| openneuro | fmap-bold-run-2 | 8 | 0.00492; 0.00738 | 0.645 | 60 | 54 (SliceTiming; header unavailable) |  | 80 \| 86 | 62 \| 80 | 80 \| 86 | 2.7 | 2.97 |
| openneuro | fmap-bold-run-3 | 1 | 0.00492; 0.00738 | 0.645 | 60 | 54 (SliceTiming; header unavailable) |  | 80 | 80 | 80 | 2.7 | 2.97 |

Field-map gap assessment: implied gap=10%.

## 8. SBRef inventory

| dataset | acquisition | SBRef sidecars | participants |
| --- | --- | --- | --- |
| complete | mb1me1 | 0 | 0 |
| complete | mb1me4 | 0 | 0 |
| complete | mb3me1 | 0 | 0 |
| complete | mb3me4 | 0 | 0 |
| complete | mb6me1 | 0 | 0 |
| complete | mb6me4 | 0 | 0 |
| local_repository | mb1me1 | 0 | 0 |
| local_repository | mb1me4 | 0 | 0 |
| local_repository | mb3me1 | 0 | 0 |
| local_repository | mb3me4 | 0 | 0 |
| local_repository | mb6me1 | 0 | 0 |
| local_repository | mb6me4 | 0 | 0 |
| openneuro | mb1me1 | 0 | 0 |
| openneuro | mb1me4 | 0 | 0 |
| openneuro | mb3me1 | 7 | 7 |
| openneuro | mb3me4 | 32 | 8 |
| openneuro | mb6me1 | 7 | 7 |
| openneuro | mb6me4 | 28 | 7 |

## 9. Head-coil distribution

| dataset | distribution |
| --- | --- |
| complete | DATA_SOURCE_UNAVAILABLE |
| local_repository | unknown=64 |
| openneuro | 64ch=10 |

ReceiveCoilName is treated as primary evidence; repository subject lists are secondary context only.

## 10. Acquisition order and counterbalancing

| dataset | scans.tsv participants | complete six-condition orders | assignment status |
| --- | --- | --- | --- |
| complete | 0 | 0 | DATA_SOURCE_UNAVAILABLE |
| local_repository | 64 | 55 | PARTIALLY_SUPPORTED |
| openneuro | 10 | 6 | PARTIALLY_SUPPORTED |

The definition source establishes the intended scheme; participant adherence is evaluated separately from scans.tsv row order. Acquisition timestamps are not reproduced.

## 11. Complete-versus-public dataset comparison

| measure | value |
| --- | --- |
| complete_participant_ids | DATA_SOURCE_UNAVAILABLE |
| openneuro_participant_ids | sub-10006; sub-10015; sub-10017; sub-10024; sub-10028; sub-10035; sub-10041; sub-10043; sub-10046; sub-10054 |
| complete_acquisition_labels | DATA_SOURCE_UNAVAILABLE |
| openneuro_acquisition_labels | mb1me1; mb1me4; mb3me1; mb3me4; mb6me1; mb6me4 |
| complete_coil_distribution | DATA_SOURCE_UNAVAILABLE |
| openneuro_coil_distribution | 64ch=10 |
| complete_bold_acquisition_count | DATA_SOURCE_UNAVAILABLE |
| openneuro_bold_acquisition_count | 44 |
| missing_participants_in_openneuro | not assessable |
| missing_acquisition_conditions_in_openneuro | not assessable |
| metadata_fields_that_differ | not assessable |
| sidecar_values_that_differ | not assessable |
| openneuro_appears_subset | not assessable |
| difference_interpretation | Public participant IDs are a subset of local_repository's participant table, but equivalence to the unavailable complete imaging dataset is not established. |
| evidence_files | openneuro:participants.tsv; openneuro:sub-10006/sub-10006_scans.tsv; openneuro:sub-10015/sub-10015_scans.tsv; openneuro:sub-10017/sub-10017_scans.tsv; openneuro:sub-10024/sub-10024_scans.tsv; openneuro:sub-10028/sub-10028_scans.tsv; openneuro:sub-10035/sub-10035_scans.tsv; openneuro:sub-10041/sub-10041_scans.tsv; openneuro:sub-10043/sub-10043_scans.tsv; openneuro:sub-10046/sub-10046_scans.tsv; openneuro:sub-10054/sub-10054_scans.tsv |

## 12. Technical propositions requiring correction or qualification

| claim_id | complete | public | correction |
| --- | --- | --- | --- |
| functional_t2star_weighting | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Describe T2* weighting as an inference from BOLD EPI metadata unless an authoritative sequence source states it explicitly. |
| functional_descending_slice_order | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Qualify the direction when NIfTI affines are unavailable. |
| six_principal_acquisitions | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Report condition-specific participant coverage. |
| multiband_factors_1_3_6 | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | State that factors 3 and 6 are explicit and factor 1 is inferred when its field is absent. |
| functional_resolution_identical | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Distinguish voxel dimensions from matrix size, slice count, and anatomical coverage. |
| functional_voxel_dimensions_2p7 | DATA_SOURCE_UNAVAILABLE | CONTRADICTED | Report NIfTI voxel dimensions when available; otherwise report slice thickness and spacing separately. |
| sbref_each_acquisition | DATA_SOURCE_UNAVAILABLE | CONTRADICTED | Report SBRef availability by acquisition rather than asserting universal availability. |
| t1_matrix_224 | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Do not equate acquisition, base, reconstruction, and NIfTI matrices. |
| t1_voxel_dimensions_1mm | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Use NIfTI header voxel dimensions for the isotropic-voxel statement. |
| fieldmap_matrix_80 | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | State which matrix definition is intended. |
| fieldmap_voxel_dimensions_2p7 | DATA_SOURCE_UNAVAILABLE | CONTRADICTED | Report slice thickness, spacing, and NIfTI voxel dimensions separately. |
| fieldmap_slices_54 | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Verify the slice count from NIfTI headers when content is available. |
| public_release_contains_both_coils | DATA_SOURCE_UNAVAILABLE | CONTRADICTED | Do not infer an unrepresented coil group from subject-list files. |
| scan_order_reconstructable | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Do not treat incomplete scan lists as verified complete assignments. |
| six_acquisition_orders_observed | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Distinguish an order scheme being defined from all orders being observed in participant data. |
| latin_square_assignments_verified | DATA_SOURCE_UNAVAILABLE | PARTIALLY_SUPPORTED | Treat participants with incomplete scan inventories as unverified. |

## 13. Propositions not verifiable from metadata

| claim_id | complete | public | reason |
| --- | --- | --- | --- |
| facility_tubric | DATA_SOURCE_UNAVAILABLE | NOT_VERIFIABLE_FROM_METADATA | Complete: BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids Public: Institution metadata names a Temple University site but does not explicitly identify TUBRIC. |
| whole_brain_coverage | DATA_SOURCE_UNAVAILABLE | NOT_VERIFIABLE_FROM_METADATA | Complete: BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids Public: File inventories, slice counts, and orientation do not establish anatomical coverage. |
| ventral_cerebellum_coverage | DATA_SOURCE_UNAVAILABLE | NOT_VERIFIABLE_FROM_METADATA | Complete: BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids Public: File inventories, slice counts, and orientation do not establish anatomical coverage. |
| t1_slices_224 | DATA_SOURCE_UNAVAILABLE | NOT_VERIFIABLE_FROM_METADATA | Complete: BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids Public: Slice count is taken from NIfTI headers; no substitute field is used. |
| coil_64ch_primary_sample | DATA_SOURCE_UNAVAILABLE | NOT_VERIFIABLE_FROM_METADATA | Complete: BIDS root is unavailable: /ZPOOL/data/projects/multiecho-pilot/bids Public: Receive-coil metadata assigns acquisition hardware but does not define an analysis sample as primary. |

An optimal-flip-angle comparison is not treated as a dataset fact because it requires external physiological assumptions.

## 14. Reproducibility instructions

Run from the repository root with nibabel installed when NIfTI content is available:

```bash
python code/validate_acquisition_metadata.py \
  --dataset complete=/ZPOOL/data/projects/multiecho-pilot/bids \
  --dataset local_repository=/Users/tug87422/github/multiecho-pilot/bids \
  --dataset openneuro=/private/tmp/ds005085-metadata-audit-20260720 \
  --counterbalance-file /Users/tug87422/github/multiecho-pilot/code/convertSharedReward2BIDSevents.m \
  --output-dir /Users/tug87422/github/multiecho-pilot/reports/acquisition_metadata_audit
```

For a fresh complete-dataset audit, replace the dataset arguments with labeled paths available on that host; use labels containing `complete` and `openneuro` to populate both comparison roles.

The program exits successfully when technical propositions are unsupported; malformed arguments or unrecoverable output errors still produce a nonzero exit status.

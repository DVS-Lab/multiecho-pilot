# Acquisition metadata audit

## 1. Executive summary

This audit separates complete-dataset evidence from the public release and uses JSON/TSV metadata as primary evidence. NIfTI geometry is used only when image content is already available.

Complete-source statuses: CONTRADICTED=6, NOT_VERIFIABLE_FROM_METADATA=5, PARTIALLY_SUPPORTED=9, SUPPORTED=22.

Public-source statuses: DATA_SOURCE_UNAVAILABLE=41, SUPPORTED=1.

## 2. Data sources and access

| label | identity | root | access | participants | JSON | TSV | NIfTI available | NIfTI pointers/unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete | TODO: eventually a DOI for the dataset | /ZPOOL/data/projects/multiecho-pilot/bids | BIDS root inspected directly | 64 | 3583 | 502 | 3497 | 0 |

No imaging content was fetched by this program.

## 3. Scope of the complete Linux1 dataset

Source `complete` (TODO: name of the dataset; TODO: eventually a DOI for the dataset; 1.8.0) at `/ZPOOL/data/projects/multiecho-pilot/bids` contains 64 participant identifiers, 360 participant-acquisition BOLD units, and acquisition labels: mb1me1, mb1me4, mb2me4, mb3me1, mb3me1fa50, mb3me3, mb3me3ip0, mb3me4, mb3me4fa50, mb6me1, mb6me4.
The inventory contains 3583 JSON files, 502 TSV files, 3497 NIfTI entries, 3497 locally available NIfTI files, and 0 unavailable pointer entries.

## 4. Scope of the public OpenNeuro release

No `openneuro` source was supplied; this evidence role is unavailable.

## 5. Functional acquisition parameters

| dataset_source | acquisition_label | participant_count | bold_file_count | observed_echo_count | echo_times_s | repetition_time_s | multiband_acceleration_factor | flip_angle_deg | number_of_slices | nifti_voxel_dimensions_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete | mb1me1 | 46 | 46 | 1 | 0.03 | 1.7 \| 3.39 |  | 20 | 27 \| 51 | [2.69767451, 2.69767451, 2.97000003] \| [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |
| complete | mb1me4 | 47 | 188 | 4 | 0.0138; 0.03154; 0.04928; 0.06702 | 4.71 |  | 20 | 50 | [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |
| complete | mb3me1 | 47 | 47 | 1 | 0.03 | 1.15 \| 1.7 | 3 | 20 | 51 | [2.69767451, 2.69767451, 2.97000003] \| [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |
| complete | mb3me4 | 59 | 236 | 4 | 0.0138; 0.03154; 0.04928; 0.06702 | 1.615 | 3 | 20 | 51 | [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |
| complete | mb6me1 | 47 | 47 | 1 | 0.03 | 0.626 \| 1.7 | 6 | 20 | 54 | [2.69767451, 2.69767451, 2.97000003] \| [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |
| complete | mb6me4 | 45 | 180 | 4 | 0.014; 0.0321; 0.0502; 0.0683 | 0.878 | 6 | 20 | 54 | [2.70000005, 2.70000005, 2.96999979] \| [2.70000005, 2.70000005, 2.97000003] |

`bold_file_count` counts magnitude or no-part sidecars and excludes phase sidecars. Full parameter sets and source paths are in `acquisition_parameters.tsv`.

## 6. Structural acquisition parameters

| dataset_source | participant_count | repetition_time_s | echo_times_s | flip_angle_deg | nifti_matrix_dimensions | nifti_voxel_dimensions_mm | base_resolution | acquisition_matrix_pe | recon_matrix_pe | slice_thickness_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete | 34 | 2.4 | 0.00217 | 8 | [192, 224, 224] | [1, 1, 1] | 224 | 224 | 224 | 1 |
| complete | 28 | 2.4 | 0.00217 | 8 | [192, 224, 224] | [1, 1, 1] | 224 | 224 | 224 | 1 |
| complete | 1 | 2.4 | 0.00217 | 8 | [192, 224, 224] | [1, 1.01785719, 1.01785719] | 224 | 224 | 224 | 1 |
| complete | 1 | 2.4 | 0.00218 | 8 | [192, 224, 224] | [1, 0.98214287, 0.98214287] | 224 | 224 | 224 | 1 |

## 7. Field-map parameters

| dataset_source | acquisition_label | participant_count | echo_times_s | repetition_time_s | flip_angle_deg | number_of_slices | nifti_matrix_dimensions | base_resolution | acquisition_matrix_pe | recon_matrix_pe | slice_thickness_mm | spacing_between_slices_mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete | fmap-bold-run-1 | 64 | 0.00492; 0.00738 | 0.645 | 60 | 54 | [80, 80, 54] \| [86, 86, 54] | 80 \| 86 | 62 \| 80 | 80 \| 86 | 2.7 | 2.97 |
| complete | fmap-bold-run-2 | 48 | 0.00492; 0.00738 | 0.645 | 60 | 54 | [80, 80, 54] \| [86, 86, 54] | 80 \| 86 | 62 \| 80 | 80 \| 86 | 2.7 | 2.97 |
| complete | fmap-bold-run-3 | 3 | 0.00492; 0.00738 | 0.645 | 60 | 54 | [80, 80, 54] | 80 | 80 | 80 | 2.7 | 2.97 |

Field-map gap assessment: implied gap=10%.

## 8. SBRef inventory

| dataset | acquisition | SBRef sidecars | participants |
| --- | --- | --- | --- |
| complete | mb1me1 | 0 | 0 |
| complete | mb1me4 | 0 | 0 |
| complete | mb3me1 | 47 | 47 |
| complete | mb3me4 | 236 | 59 |
| complete | mb6me1 | 47 | 47 |
| complete | mb6me4 | 180 | 45 |

## 9. Head-coil distribution

| dataset | distribution |
| --- | --- |
| complete | 20ch=36; 64ch=28 |

ReceiveCoilName is treated as primary evidence; repository subject lists are secondary context only.

## 10. Acquisition order and counterbalancing

| dataset | scans.tsv participants | complete six-condition orders | assignment status |
| --- | --- | --- | --- |
| complete | 64 | 55 | PARTIALLY_SUPPORTED |

The definition source establishes the intended scheme; participant adherence is evaluated separately from scans.tsv row order. Acquisition timestamps are not reproduced.

## 11. Complete-versus-public dataset comparison

| measure | value |
| --- | --- |
| complete_participant_ids | sub-10006; sub-10015; sub-10017; sub-10024; sub-10028; sub-10035; sub-10041; sub-10043; sub-10046; sub-10054; sub-10059; sub-10069; sub-10074; sub-10078; sub-10080; sub-10085; sub-10094; sub-10108; sub-10125; sub-10130; sub-10136; sub-10137; sub-10142; sub-10150; sub-10154; sub-10166; sub-10185; sub-10186; sub-10188; sub-10198; sub-10203; sub-10221; sub-10223; sub-10234; sub-10296; sub-10303; sub-10318; sub-10319; sub-10320; sub-10321; sub-10363; sub-10382; sub-10391; sub-10416; sub-10422; sub-10438; sub-10589sp; sub-10590sp; sub-10603sp; sub-10606sp; sub-10608sp; sub-10640sp; sub-10644sp; sub-10652; sub-10659sp; sub-10690sp; sub-10691sp; sub-10716; sub-10723sp; sub-10738; sub-10741sp; sub-10777sp; sub-10803sp; sub-12042 |
| openneuro_participant_ids | DATA_SOURCE_UNAVAILABLE |
| complete_acquisition_labels | mb1me1; mb1me4; mb2me4; mb3me1; mb3me1fa50; mb3me3; mb3me3ip0; mb3me4; mb3me4fa50; mb6me1; mb6me4 |
| openneuro_acquisition_labels | DATA_SOURCE_UNAVAILABLE |
| complete_coil_distribution | 20ch=36; 64ch=28 |
| openneuro_coil_distribution | DATA_SOURCE_UNAVAILABLE |
| complete_bold_acquisition_count | 360 |
| openneuro_bold_acquisition_count | DATA_SOURCE_UNAVAILABLE |
| missing_participants_in_openneuro | not assessable |
| missing_acquisition_conditions_in_openneuro | not assessable |
| metadata_fields_that_differ | not assessable |
| sidecar_values_that_differ | not assessable |
| openneuro_appears_subset | not assessable |
| difference_interpretation | Complete-versus-public comparison requires both sources. |
| evidence_files | complete:participants.tsv; complete:sub-10006/sub-10006_scans.tsv; complete:sub-10015/sub-10015_scans.tsv; complete:sub-10017/sub-10017_scans.tsv; complete:sub-10024/sub-10024_scans.tsv; complete:sub-10028/sub-10028_scans.tsv; complete:sub-10035/sub-10035_scans.tsv; complete:sub-10041/sub-10041_scans.tsv; complete:sub-10043/sub-10043_scans.tsv; complete:sub-10046/sub-10046_scans.tsv; complete:sub-10054/sub-10054_scans.tsv |

## 12. Technical propositions requiring correction or qualification

| claim_id | complete | public | correction |
| --- | --- | --- | --- |
| functional_t2star_weighting | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Describe T2* weighting as an inference from BOLD EPI metadata unless an authoritative sequence source states it explicitly. |
| six_principal_acquisitions | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Report condition-specific participant coverage. |
| multiband_factors_1_3_6 | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | State that factors 3 and 6 are explicit and factor 1 is inferred when its field is absent. |
| functional_flip_angle_20 | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | No correction suggested. |
| functional_resolution_identical | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Distinguish voxel dimensions from matrix size, slice count, and anatomical coverage. |
| functional_voxel_dimensions_2p7 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Report NIfTI voxel dimensions when available; otherwise report slice thickness and spacing separately. |
| sbref_each_acquisition | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Report SBRef availability by acquisition rather than asserting universal availability. |
| t1_te_2p17ms | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | No correction suggested. |
| t1_matrix_224 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Do not equate acquisition, base, reconstruction, and NIfTI matrices. |
| t1_voxel_dimensions_1mm | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Use NIfTI header voxel dimensions for the isotropic-voxel statement. |
| fieldmap_matrix_80 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | State which matrix definition is intended. |
| fieldmap_voxel_dimensions_2p7 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Report slice thickness, spacing, and NIfTI voxel dimensions separately. |
| scan_order_reconstructable | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Do not treat incomplete scan lists as verified complete assignments. |
| six_acquisition_orders_observed | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Distinguish an order scheme being defined from all orders being observed in participant data. |
| latin_square_assignments_verified | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Treat participants with incomplete scan inventories as unverified. |

## 13. Propositions not verifiable from metadata

| claim_id | complete | public | reason |
| --- | --- | --- | --- |
| facility_tubric | NOT_VERIFIABLE_FROM_METADATA | DATA_SOURCE_UNAVAILABLE | Complete: Institution metadata names a Temple University site but does not explicitly identify TUBRIC. Public: No dataset with the requested evidence role was supplied. |
| scanner_3t | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All represented sidecars report the expected MagneticFieldStrength. Public: No dataset with the requested evidence role was supplied. |
| scanner_siemens | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Evaluated Manufacturer across represented imaging sidecars. Public: No dataset with the requested evidence role was supplied. |
| scanner_prisma | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Evaluated ManufacturersModelName across represented imaging sidecars. Public: No dataset with the requested evidence role was supplied. |
| functional_bold | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: BIDS suffix and datatype identify the represented files as BOLD. Public: No dataset with the requested evidence role was supplied. |
| functional_epi | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: ScanningSequence was evaluated for the EP code. Public: No dataset with the requested evidence role was supplied. |
| functional_t2star_weighting | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: T2* weighting is inferred from BOLD/EPI labeling and echo times; an explicit weighting field is absent. Public: No dataset with the requested evidence role was supplied. |
| functional_axial_orientation | NOT_VERIFIABLE_FROM_METADATA | DATA_SOURCE_UNAVAILABLE | Complete: Orientation uses NIfTI axes when available and DICOM orientation metadata otherwise. Public: No dataset with the requested evidence role was supplied. |
| functional_descending_slice_order | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: SliceTiming supports slice-index ordering; physical direction also requires a defensible index-to-space mapping. Public: No dataset with the requested evidence role was supplied. |
| six_principal_acquisitions | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All six labels are present but participant coverage is evaluated separately. Public: No dataset with the requested evidence role was supplied. |
| multiband_factors_1_3_6 | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: An MB1 label with a missing field supports only an inference, not direct confirmation. Public: No dataset with the requested evidence role was supplied. |
| echo_counts_1_and_4 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Echo entities and distinct EchoTime values were grouped within participant and acquisition. Public: No dataset with the requested evidence role was supplied. |
| functional_flip_angle_20 | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: The expected FlipAngle is reported for only part of the represented data. Public: No dataset with the requested evidence role was supplied. |
| functional_resolution_identical | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Sidecar thickness and spacing are consistent, but complete NIfTI voxel dimensions are unavailable. Public: No dataset with the requested evidence role was supplied. |
| functional_voxel_dimensions_2p7 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: Nonzero through-plane spacing relative to slice thickness is incompatible with isotropic sampling as stated. Public: No dataset with the requested evidence role was supplied. |
| whole_brain_coverage | NOT_VERIFIABLE_FROM_METADATA | DATA_SOURCE_UNAVAILABLE | Complete: File inventories, slice counts, and orientation do not establish anatomical coverage. Public: No dataset with the requested evidence role was supplied. |
| ventral_cerebellum_coverage | NOT_VERIFIABLE_FROM_METADATA | DATA_SOURCE_UNAVAILABLE | Complete: File inventories, slice counts, and orientation do not establish anatomical coverage. Public: No dataset with the requested evidence role was supplied. |
| sbref_each_acquisition | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: SBRef metadata is absent for 93 represented participant-acquisition units. Public: No dataset with the requested evidence role was supplied. |
| t1_tr_2p4 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All represented sidecars report the expected RepetitionTime. Public: No dataset with the requested evidence role was supplied. |
| t1_te_2p17ms | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: The expected EchoTime is reported for only part of the represented data. Public: No dataset with the requested evidence role was supplied. |
| t1_matrix_224 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: NIfTI header matrix dimensions were evaluated. Public: No dataset with the requested evidence role was supplied. |
| t1_voxel_dimensions_1mm | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: Slice thickness alone does not establish three-dimensional isotropy. Public: No dataset with the requested evidence role was supplied. |
| t1_slices_224 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Slice count is taken from NIfTI headers; no substitute field is used. Public: No dataset with the requested evidence role was supplied. |
| t1_flip_angle_8 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All represented sidecars report the expected FlipAngle. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_present | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Field-map suffixes and GRE-related sequence metadata were evaluated. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_tr_645ms | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All represented sidecars report the expected RepetitionTime. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_te1_4p92ms | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: EchoTime1 is preferred when present; magnitude1 EchoTime is used otherwise. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_te2_7p38ms | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: EchoTime2 is preferred when present; magnitude2 EchoTime is used otherwise. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_matrix_80 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: JSON matrix concepts are reported separately from NIfTI dimensions. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_voxel_dimensions_2p7 | CONTRADICTED | DATA_SOURCE_UNAVAILABLE | Complete: Through-plane spacing differs from slice thickness when a nonzero gap is present. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_slices_54 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: SliceTiming length is corroborating evidence only; NIfTI headers are primary. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_gap_10pct | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Calculated as (SpacingBetweenSlices - SliceThickness) / SliceThickness x 100. Public: No dataset with the requested evidence role was supplied. |
| fieldmap_flip_angle_60 | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: All represented sidecars report the expected FlipAngle. Public: No dataset with the requested evidence role was supplied. |
| coil_64ch_present | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: ReceiveCoilName is used as participant-level primary evidence. Public: No dataset with the requested evidence role was supplied. |
| coil_20ch_present | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: ReceiveCoilName is used as participant-level primary evidence. Public: No dataset with the requested evidence role was supplied. |
| coil_assignment_complete | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Participants without metadata-based assignment: none. Public: No dataset with the requested evidence role was supplied. |
| coil_64ch_primary_sample | NOT_VERIFIABLE_FROM_METADATA | DATA_SOURCE_UNAVAILABLE | Complete: Receive-coil metadata assigns acquisition hardware but does not define an analysis sample as primary. Public: No dataset with the requested evidence role was supplied. |
| public_release_contains_both_coils | SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: ReceiveCoilName is used as participant-level primary evidence. Public: No dataset with the requested evidence role was supplied. |
| scan_order_reconstructable | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Row order in scans.tsv reconstructs acquisition order without reporting acquisition timestamps. Public: No dataset with the requested evidence role was supplied. |
| six_acquisition_orders_observed | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Only complete six-condition scans.tsv orders are counted as observed orders. Public: No dataset with the requested evidence role was supplied. |
| latin_square_assignments_verified | PARTIALLY_SUPPORTED | DATA_SOURCE_UNAVAILABLE | Complete: Defined mappings establish the scheme; scans.tsv order is used to test represented assignments. Public: No dataset with the requested evidence role was supplied. |

An optimal-flip-angle comparison is not treated as a dataset fact because it requires external physiological assumptions.

## 14. Reproducibility instructions

Run from the repository root with nibabel installed when NIfTI content is available:

```bash
python code/validate_acquisition_metadata.py \
  --dataset complete=/ZPOOL/data/projects/multiecho-pilot/bids \
  --counterbalance-file /ZPOOL/data/projects/multiecho-pilot/code/convertSharedReward2BIDSevents.m \
  --output-dir /ZPOOL/data/projects/multiecho-pilot/reports/acquisition_metadata_audit_linux1
```

For a fresh complete-dataset audit, replace the dataset arguments with labeled paths available on that host; use labels containing `complete` and `openneuro` to populate both comparison roles.

The program exits successfully when technical propositions are unsupported; malformed arguments or unrecoverable output errors still produce a nonzero exit status.

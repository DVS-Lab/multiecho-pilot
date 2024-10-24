#!/bash/bin


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

sub=$1
task=sharedreward
acq=$2

outdir=$maindir/derivatives/warpkit/sub-${sub}
if [ ! -d $outdir ]; then
	mkdir -p $outdir
fi

indir=${maindir}/bids/sub-${sub}/func
if [ ! -e $indir/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.json ]; then
	echo "NO DATA: sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.json"
	echo "NO DATA: sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.json" >> $scriptdir/missingFiles-warpkit.log
	exit
fi

# don't re-do existing output
if [ -e $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${acq}_fieldmap.json ]; then
	echo "EXISTS (skipping): sub-${sub}/fmap/sub-${sub}_acq-${acq}_fieldmap.json"
	exit
fi

if [ "$acq" == "mb3me3" ] || [ "$acq" == "mb3me3ip0" ]; then
	/ZPOOL/data/tools/apptainer/bin/singularity run --cleanenv \
	-B $indir:/base \
	-B $outdir:/out \
	/ZPOOL/data/tools/warpkit.sif \
	--magnitude /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.nii.gz \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-mag_bold.nii.gz \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-mag_bold.nii.gz \
	--phase /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-phase_bold.nii.gz \
			/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-phase_bold.nii.gz \
			/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-phase_bold.nii.gz \
	--metadata /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-phase_bold.json \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-phase_bold.json \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-phase_bold.json \
	--out_prefix /out/sub-${sub}_task-${task}_acq-${acq}
else
	/ZPOOL/data/tools/apptainer/bin/singularity run --cleanenv \
	-B $indir:/base \
	-B $outdir:/out \
	/ZPOOL/data/tools/warpkit.sif \
	--magnitude /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.nii.gz \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-mag_bold.nii.gz \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-mag_bold.nii.gz \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-4_part-mag_bold.nii.gz \
	--phase /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-phase_bold.nii.gz \
			/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-phase_bold.nii.gz \
			/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-phase_bold.nii.gz \
			/base/sub-${sub}_task-${task}_acq-${acq}_echo-4_part-phase_bold.nii.gz \
	--metadata /base/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-phase_bold.json \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-2_part-phase_bold.json \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-3_part-phase_bold.json \
				/base/sub-${sub}_task-${task}_acq-${acq}_echo-4_part-phase_bold.json \
	--out_prefix /out/sub-${sub}_task-${task}_acq-${acq}
fi

# extract first volume as fieldmap and copy to fmap dir. still need json files for these. 
fslroi $outdir/sub-${sub}_task-${task}_acq-${acq}_fieldmaps.nii $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${acq}_fieldmap 0 1
fslroi $indir/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.nii.gz $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${acq}_magnitude 0 1

# placeholders for json files. will need editing.
cp $indir/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-mag_bold.json $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${acq}_magnitude.json
cp $indir/sub-${sub}_task-${task}_acq-${acq}_echo-1_part-phase_bold.json $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${acq}_fieldmap.json

# trash the rest
rm -rf $outdir/sub-${sub}_task-${task}_acq-${acq}_displacementmaps.nii
rm -rf $outdir/sub-${sub}_task-${task}_acq-${acq}_fieldmaps_native.nii


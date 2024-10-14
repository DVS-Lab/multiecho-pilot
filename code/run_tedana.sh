#scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
python my_tedana.py --fmriprepDir /ZPOOL/data/projects/rf1-sra-data/derivatives/fmriprep --bidsDir /ZPOOL/data/projects/rf1-sra-data/bids --cores 8

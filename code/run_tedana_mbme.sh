#!/bin/bash

sub=$1
python3 tedana-multi.py \
--fmriprepDir /ZPOOL/data/projects/multiecho-pilot/derivatives/fmriprep/sub-${sub} \
--bidsDir /ZPOOL/data/projects/multiecho-pilot/bids/sub-${sub} \
--sub $sub

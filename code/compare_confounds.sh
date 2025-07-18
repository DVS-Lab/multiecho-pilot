#!/bin/bash

# Script to compare confounds files across three versions
# Usage: ./compare_confounds.sh <acq_type>
# Example: ./compare_confounds.sh mb1me4

set -e

# Check if acq_type is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <acq_type>"
    echo "Example: $0 mb1me4"
    exit 1
fi

ACQ_TYPE=$1

# Base directories
BASE_DIR="/ZPOOL/data/projects/multiecho-pilot/derivatives/fsl"
BASE_CONFOUNDS_DIR="${BASE_DIR}/confounds"
OLD_TEDANA_DIR="${BASE_DIR}/archive_confounds_tedana"
NEW_TEDANA_DIR="${BASE_DIR}/confounds_tedana"

# Function to get file dimensions (rows,cols)
get_dimensions() {
    local file=$1
    if [ -f "$file" ]; then
        # Count rows (excluding header) and columns
        local rows=$(tail -n +2 "$file" | wc -l)
        local cols=$(head -n 1 "$file" | tr '\t' '\n' | wc -l)
        echo "${rows}x${cols}"
    else
        echo "missing"
    fi
}

# Function to compare file contents
compare_files() {
    local file1=$1
    local file2=$2
    
    if [ -f "$file1" ] && [ -f "$file2" ]; then
        # Use diff to compare files, return 0 if identical, 1 if different
        if diff -q "$file1" "$file2" > /dev/null 2>&1; then
            echo "0"
        else
            echo "1"
        fi
    else
        echo "NA"
    fi
}

# Function to find first difference location
find_first_diff() {
    local file1=$1
    local file2=$2
    
    if [ -f "$file1" ] && [ -f "$file2" ]; then
        # Use diff with line numbers to find first difference
        local diff_output=$(diff -n "$file1" "$file2" 2>/dev/null | head -n 1)
        if [ -n "$diff_output" ]; then
            # Extract line number from diff output
            local line_num=$(echo "$diff_output" | grep -o '^[0-9]*' | head -n 1)
            if [ -n "$line_num" ]; then
                echo "line_${line_num}"
            else
                echo "unknown"
            fi
        else
            echo "identical"
        fi
    else
        echo "NA"
    fi
}

# Function to get detailed diff info
get_diff_type() {
    local file1=$1
    local file2=$2
    
    if [ -f "$file1" ] && [ -f "$file2" ]; then
        # Check if files are identical
        if diff -q "$file1" "$file2" > /dev/null 2>&1; then
            echo "identical"
            return
        fi
        
        # Check for whitespace-only differences
        if diff -b -q "$file1" "$file2" > /dev/null 2>&1; then
            echo "whitespace_only"
            return
        fi
        
        # Check for tab delimiter issues by comparing column counts
        local cols1=$(head -n 2 "$file1" | tail -n 1 | tr '\t' '\n' | wc -l)
        local cols2=$(head -n 2 "$file2" | tail -n 1 | tr '\t' '\n' | wc -l)
        local header_cols1=$(head -n 1 "$file1" | tr '\t' '\n' | wc -l)
        local header_cols2=$(head -n 1 "$file2" | tr '\t' '\n' | wc -l)
        
        # Check if column counts are inconsistent (suggests formatting issues)
        if [ "$cols1" -ne "$header_cols1" ] || [ "$cols2" -ne "$header_cols2" ] || [ "$cols1" -ne "$cols2" ]; then
            echo "formatting_error"
            return
        fi
        
        # Check for numerical precision differences (rough approximation)
        local temp1=$(mktemp)
        local temp2=$(mktemp)
        
        # Round numbers to 6 decimal places for comparison
        sed 's/\([0-9]\+\.[0-9]\{6\}\)[0-9]*/\1/g' "$file1" > "$temp1" 2>/dev/null || cp "$file1" "$temp1"
        sed 's/\([0-9]\+\.[0-9]\{6\}\)[0-9]*/\1/g' "$file2" > "$temp2" 2>/dev/null || cp "$file2" "$temp2"
        
        if diff -q "$temp1" "$temp2" > /dev/null 2>&1; then
            echo "precision_diff"
        else
            echo "content_diff"
        fi
        
        rm -f "$temp1" "$temp2"
    else
        echo "NA"
    fi
}

# Function to compare dimensions
compare_dimensions() {
    local dim1=$1
    local dim2=$2
    
    if [ "$dim1" = "missing" ] || [ "$dim2" = "missing" ]; then
        echo "NA"
    elif [ "$dim1" = "$dim2" ]; then
        echo "0"
    else
        echo "1"
    fi
}

# Print header
echo -e "Subject\tBase_Dimensions\tOld_Tedana_Dimensions\tNew_Tedana_Dimensions\tNew_vs_Base_Diff\tNew_vs_Old_Diff\tNew_vs_Old_Values_Diff\tFirst_Diff_Location\tDiff_Type"

# Get list of subjects from base confounds directory
for subject_dir in "${BASE_CONFOUNDS_DIR}"/sub-*; do
    if [ -d "$subject_dir" ]; then
        subject=$(basename "$subject_dir")
        
        # Construct file paths based on acq_type
        case "$ACQ_TYPE" in
            mb1me4)
                base_file="${BASE_CONFOUNDS_DIR}/${subject}/${subject}_task-sharedreward_acq-mb1me4_part-mag_desc-confounds_acq-mb1me4_part-mag_desc-confounds_desc-fslConfounds.tsv"
                ;;
            mb3me4)
                base_file="${BASE_CONFOUNDS_DIR}/${subject}/${subject}_task-sharedreward_acq-mb3me4_part-mag_desc-confounds_acq-mb3me4_part-mag_desc-confounds_desc-fslConfounds.tsv"
                ;;
            mb6me4)
                base_file="${BASE_CONFOUNDS_DIR}/${subject}/${subject}_task-sharedreward_acq-mb6me4_part-mag_desc-confounds_acq-mb6me4_part-mag_desc-confounds_desc-fslConfounds.tsv"
                ;;
            *)
                echo "Error: Unknown acq_type $ACQ_TYPE" >&2
                exit 1
                ;;
        esac
        
        old_tedana_file="${OLD_TEDANA_DIR}/${subject}/${subject}_task-sharedreward_acq-${ACQ_TYPE}_desc-TedanaPlusConfounds.tsv"
        new_tedana_file="${NEW_TEDANA_DIR}/${subject}/${subject}_task-sharedreward_acq-${ACQ_TYPE}_desc-TedanaPlusConfounds.tsv"
        
        # Get dimensions
        base_dims=$(get_dimensions "$base_file")
        old_tedana_dims=$(get_dimensions "$old_tedana_file")
        new_tedana_dims=$(get_dimensions "$new_tedana_file")
        
        # Compare dimensions
        new_vs_base_diff=$(compare_dimensions "$new_tedana_dims" "$base_dims")
        new_vs_old_diff=$(compare_dimensions "$new_tedana_dims" "$old_tedana_dims")
        
        # Compare actual values between new and old tedana
        new_vs_old_values_diff=$(compare_files "$new_tedana_file" "$old_tedana_file")
        
        # Get additional diagnostic info
        first_diff_location=$(find_first_diff "$new_tedana_file" "$old_tedana_file")
        diff_type=$(get_diff_type "$new_tedana_file" "$old_tedana_file")
        
        # Print results
        echo -e "${subject}\t${base_dims}\t${old_tedana_dims}\t${new_tedana_dims}\t${new_vs_base_diff}\t${new_vs_old_diff}\t${new_vs_old_values_diff}\t${first_diff_location}\t${diff_type}"
    fi
done

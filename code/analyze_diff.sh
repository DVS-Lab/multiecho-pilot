#!/bin/bash

# Detailed analysis script for understanding the differences
# Usage: ./analyze_diff.sh <old_file> <new_file>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <old_file> <new_file>"
    exit 1
fi

OLD_FILE=$1
NEW_FILE=$2

echo "=== DETAILED DIFF ANALYSIS ==="
echo "Old file: $OLD_FILE"
echo "New file: $NEW_FILE"
echo ""

# 1. Basic file info
echo "1. BASIC FILE INFO:"
echo "Old file size: $(wc -c < "$OLD_FILE") bytes"
echo "New file size: $(wc -c < "$NEW_FILE") bytes"
echo "Old file lines: $(wc -l < "$OLD_FILE")"
echo "New file lines: $(wc -l < "$NEW_FILE")"
echo ""

# 2. Check dimensions consistency
echo "2. DIMENSION CONSISTENCY:"
echo "Checking if all rows have same number of columns..."

# Check old file
echo "Old file column counts per row (first 5 rows):"
head -5 "$OLD_FILE" | nl | while read num line; do
    cols=$(echo "$line" | tr '\t' '\n' | wc -l)
    echo "  Row $num: $cols columns"
done

echo "New file column counts per row (first 5 rows):"
head -5 "$NEW_FILE" | nl | while read num line; do
    cols=$(echo "$line" | tr '\t' '\n' | wc -l)
    echo "  Row $num: $cols columns"
done
echo ""

# 3. Show the actual differences
echo "3. FIRST FEW DIFFERENCES:"
diff -u "$OLD_FILE" "$NEW_FILE" | head -20
echo ""

# 4. Check for specific patterns
echo "4. PATTERN ANALYSIS:"

# Look for number concatenation patterns
echo "Checking for concatenated numbers (no space/tab between)..."
echo "Old file suspicious patterns:"
grep -n -E '[0-9]\.[0-9]+-[0-9]\.[0-9]+' "$OLD_FILE" | head -3

echo "New file suspicious patterns:"
grep -n -E '[0-9]\.[0-9]+-[0-9]\.[0-9]+' "$NEW_FILE" | head -3
echo ""

# 5. Character-by-character comparison of a problematic line
echo "5. CHARACTER ANALYSIS OF PROBLEMATIC LINES:"
echo "Looking at the line that diff says is different..."

# Get the line number of first difference
DIFF_LINE=$(diff "$OLD_FILE" "$NEW_FILE" | grep -E '^[0-9]+c[0-9]+' | head -1 | cut -d'c' -f1)

if [ -n "$DIFF_LINE" ]; then
    echo "First different line number: $DIFF_LINE"
    echo ""
    echo "Old file line $DIFF_LINE (showing tabs as [TAB]):"
    sed -n "${DIFF_LINE}p" "$OLD_FILE" | sed 's/\t/[TAB]/g'
    echo ""
    echo "New file line $DIFF_LINE (showing tabs as [TAB]):"
    sed -n "${DIFF_LINE}p" "$NEW_FILE" | sed 's/\t/[TAB]/g'
    echo ""
    
    # Count tabs
    OLD_TABS=$(sed -n "${DIFF_LINE}p" "$OLD_FILE" | tr -cd '\t' | wc -c)
    NEW_TABS=$(sed -n "${DIFF_LINE}p" "$NEW_FILE" | tr -cd '\t' | wc -c)
    echo "Old file tabs in this line: $OLD_TABS"
    echo "New file tabs in this line: $NEW_TABS"
    echo ""
    
    # Show invisible characters
    echo "Old file line with all characters visible:"
    sed -n "${DIFF_LINE}p" "$OLD_FILE" | cat -A
    echo ""
    echo "New file line with all characters visible:"
    sed -n "${DIFF_LINE}p" "$NEW_FILE" | cat -A
fi

echo ""
echo "6. NUMERICAL PRECISION CHECK:"
echo "Checking if differences are just floating-point precision..."

# Extract first differing line and compare numerically
if [ -n "$DIFF_LINE" ]; then
    echo "Extracting numbers from differing line for comparison..."
    echo "Old line numbers (first 10):"
    sed -n "${DIFF_LINE}p" "$OLD_FILE" | tr '\t' '\n' | head -10 | nl
    echo ""
    echo "New line numbers (first 10):"
    sed -n "${DIFF_LINE}p" "$NEW_FILE" | tr '\t' '\n' | head -10 | nl
fi

#! /usr/bin/env dash

################################################################################
#                                                                              #
#   COMP3331/COMP9331 Computer Networks and Applications                       #
#   STP Assignment                                                             #
#   Script to analyse receiver log summary statistics                          #
#                                                                              #
#   Author: Tim Arney (t.arney@unsw.edu.au)                                    #
#   Date:   09/04/2024                                                         #
#                                                                              #
#   Usage: ./analyse_receiver_log.sh <log_file>                                #
#                                                                              #
#   If log_file not provided, default is 'receiver_log.txt'                    #
#                                                                              #
################################################################################

# Helper function to sum integers in a file
sum() {
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <file>" >&2
        exit 1
    fi

    sum=0
    
    while read -r i; do                               # read each line
        [ "$i" -eq "$i" ] 2> /dev/null || continue    # test if an integer
        sum=$(( sum + i ))                            # sum
    done < "$1"

    echo "$sum"
}

# Default log file and exit code
log="receiver_log.txt"
exit_code=0

# Check for log file argument
if [ $# -eq 1 ]; then
    log="$1"
fi

# Check if log file exists
if [ ! -f "$log" ]; then
    echo "Log file not found: $log" >&2
    exit 1
fi

# Temporary files for analysis
list=$(mktemp)
summary=$(mktemp)
trap 'rm "$list" "$summary"' INT HUP QUIT TERM EXIT

cat << EOF
################################################################################
#                      Original data received (bytes)                          #
################################################################################
EOF

grep -F 'DATA' "$log" |
sed -E 's/^[[:space:]]+//' |
sed -E 's/[[:space:]]+/ /g' |
cut -d ' ' -f 4,5 |
sort -k2,2rn -k1,1n |
uniq > "$list"
cut -d ' ' -f 2,2 "$list" > "$summary"

analysed=$(sum "$summary")
reported=$(grep -iF 'original data' "$log" | cut -d: -f2 | tr -d ' ')
echo
echo "Log reported: $reported"
echo "Log analysed: $analysed"
echo
if [ "$analysed" -gt 0 ]; then
    echo "Original segments detected in log:"
    echo
    uniq "$list"
    echo
fi
if [ "$analysed" -ne "$reported" ]; then
    exit_code=1
fi

cat << EOF
################################################################################
#                         Original segments received                           #
################################################################################
EOF

grep -F 'DATA' "$log" |
sed -E 's/^[[:space:]]+//' |
sed -E 's/[[:space:]]+/ /g' |
cut -d ' ' -f 4 |
sort -n > "$list"

analysed=$(uniq "$list" | wc -l | tr -d ' ')
reported=$(grep -iF 'original segments' "$log" | cut -d: -f2 | tr -d ' ')
echo
echo "Log reported: $reported"
echo "Log analysed: $analysed"
echo
if [ "$analysed" -gt 0 ]; then
    echo "Original segments detected in log:"
    echo
    uniq "$list"
    echo
fi
if [ "$analysed" -ne "$reported" ]; then
    exit_code=1
fi

cat << EOF
################################################################################
#                         Dup data segments received                           #
################################################################################
EOF

sed -n '/DATA/,/FIN/p' "$log" |
grep -F 'DATA' | 
sed -E 's/^[[:space:]]+//' |
sed -E 's/[[:space:]]+/ /g' |
cut -d ' ' -f 4 |
sort -n |
uniq -D > "$list"

uniq -c "$list" > "$summary"

list_count=$(wc -l < "$list" | tr -d ' ')
original_count=$(wc -l < "$summary" | tr -d ' ')
analysed=$((list_count - original_count))
reported=$(grep -iF 'dup data' "$log" | cut -d: -f2 | tr -d ' ')
echo
echo "Log reported: $reported"
echo "Log analysed: $analysed"
echo
if [ "$analysed" -gt 0 ]; then
    echo "Counts of duplicate segments (including original) detected in log:"
    echo
    cat "$summary"
    echo
fi
if [ "$analysed" -ne "$reported" ]; then
    exit_code=1
fi

cat << EOF
################################################################################
#                           Dup ack segments sent                              #
################################################################################
EOF

sed -n '/DATA/,/FIN/p' "$log" |
grep -F 'ACK' | 
sed -E 's/^[[:space:]]+//' |
sed -E 's/[[:space:]]+/ /g' |
cut -d ' ' -f 4 |
sort -n |
uniq -D > "$list"

uniq -c "$list" > "$summary"

list_count=$(wc -l < "$list" | tr -d ' ')
original_count=$(wc -l < "$summary" | tr -d ' ')
analysed=$((list_count - original_count))
reported=$(grep -iF 'dup ack' "$log" | cut -d: -f2 | tr -d ' ')
echo
echo "Log reported: $reported"
echo "Log analysed: $analysed"
echo
if [ "$analysed" -gt 0 ]; then
    echo "Counts of duplicate segments (including original) detected in log:"
    echo
    cat "$summary"
    echo
fi
if [ "$analysed" -ne "$reported" ]; then
    exit_code=1
fi

if [ "$exit_code" -eq 0 ]; then
    echo "-------------  PASS: Calculated statistics match reported values.  -------------"
else
    echo "----------  FAIL: Calculated statistics DO NOT match reported values.  ---------"
fi

exit "$exit_code"


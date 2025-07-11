#!/bin/bash

# Usage: ./split-audio.sh input.m4a output-dir/
# Requires: ffmpeg, silencedetect

INPUT_FILE="$1"
OUTPUT_DIR="$2"

# Shared-Verzeichnis standardmäßig verwenden, wenn keine absoluten Pfade
SHARED_DIR="/shared"
if [[ "$INPUT_FILE" != /* ]]; then
  INPUT_FILE="$SHARED_DIR/$INPUT_FILE"
fi
if [[ "$OUTPUT_DIR" != /* ]]; then
  OUTPUT_DIR="$SHARED_DIR/$OUTPUT_DIR"
fi

# Ensure audio subdirectories exist
mkdir -p "$SHARED_DIR/audio/in" "$SHARED_DIR/audio/out"

# Temporäre Datei für Stille-Erkennung
TMP_SILENCE=$(mktemp)

# Check input
if [[ -z "$INPUT_FILE" || -z "$OUTPUT_DIR" ]]; then
  echo "Usage: $0 input_file output_dir"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Step 1: Detect silence
echo "Detecting silence..." 
ffmpeg -i "$INPUT_FILE" -af silencedetect=noise=-30dB:d=1 -f null - 2> "$TMP_SILENCE"

# Step 2: Parse silence log to find optimal split points near 10min intervals
SPLIT_POINTS=()
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_FILE")
TARGET_INTERVAL=600  # 10 minutes
NEXT_SPLIT=$TARGET_INTERVAL

while read -r line; do
  if [[ "$line" =~ silence_end: ]]; then
    TIME=$(echo "$line" | grep -oP 'silence_end: \K[0-9\.]+')
    if (( $(echo "$TIME >= $NEXT_SPLIT" | bc -l) )); then
      SPLIT_POINTS+=("$TIME")
      NEXT_SPLIT=$(echo "$TIME + $TARGET_INTERVAL" | bc)
    fi
  fi
done < "$TMP_SILENCE"

# Add file end as last split point
SPLIT_POINTS+=("$DURATION")

# Step 3: Cut file
START=0
INDEX=1

for END in "${SPLIT_POINTS[@]}"; do
  OUTFILE=$(printf "%s/part_%02d.m4a" "$OUTPUT_DIR" "$INDEX")
  DURATION_PART=$(echo "$END - $START" | bc)
  echo "Exporting $OUTFILE (start=$START, duration=$DURATION_PART)"
  ffmpeg -y -i "$INPUT_FILE" -ss "$START" -t "$DURATION_PART" -c copy "$OUTFILE"
  START="$END"
  INDEX=$((INDEX + 1))
done

# Clean up temporary silence file
rm "$TMP_SILENCE"

echo "Done. Split into $((INDEX - 1)) parts."
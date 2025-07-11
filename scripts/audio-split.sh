#!/bin/bash
# audio-split.sh - Split audio files in fixed or silence-based chunks
# Usage:
#   ./audio-split.sh --mode fixed|silence --chunk-length <seconds> --input <file> [--output <dir>] [--silence-seek <seconds>] [--silence-duration <seconds>] [--silence-threshold <dB>] [--padding <seconds>]


# Default directories
BASE_DIR="/shared/audio"
BASE_IN_DIR="$BASE_DIR/in"
BASE_OUT_DIR="$BASE_DIR/out"
mkdir -p "$BASE_DIR"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2;;
    --chunk-length) CHUNK_LENGTH="$2"; shift 2;;
    --input) INPUT_PATH="$2"; shift 2;;
    --output) OUTPUT_DIR_ARG="$2"; shift 2;;
    --silence-seek) SILENCE_SEEK="$2"; shift 2;;
    --silence-duration) SILENCE_DURATION="$2"; shift 2;;
    --silence-threshold) SILENCE_THRESHOLD="$2"; shift 2;;
    --padding) PADDING="$2"; shift 2;;
    *) echo "Unknown parameter: $1"; exit 1;;
  esac
done

# Validate required parameters
if [[ -z "$MODE" || -z "$CHUNK_LENGTH" || -z "$INPUT_PATH" ]]; then
  echo "Usage: $0 --mode fixed|silence --chunk-length <seconds> --input <file> [--output <dir>] [--silence-seek <seconds>] [--silence-duration <seconds>] [--silence-threshold <dB>] [--padding <seconds>]"
  exit 1
fi

# Silence mode requires extra parameters
if [[ "$MODE" == "silence" ]]; then
  if [[ -z "$SILENCE_SEEK" || -z "$SILENCE_DURATION" ]]; then
    echo "For silence mode, --silence-seek and --silence-duration are required"
    exit 1
  fi
  SILENCE_THRESHOLD=${SILENCE_THRESHOLD:-30}
  PADDING=${PADDING:-0}
fi

# Resolve input path
if [[ "$INPUT_PATH" != /* ]]; then
  INPUT_FILE="$BASE_IN_DIR/$INPUT_PATH"
else
  INPUT_FILE="$INPUT_PATH"
fi

# Determine output directory
if [[ -n "$OUTPUT_DIR_ARG" ]]; then
  if [[ "$OUTPUT_DIR_ARG" != /* ]]; then
    OUTPUT_DIR="$BASE_OUT_DIR/$OUTPUT_DIR_ARG"
  else
    OUTPUT_DIR="$OUTPUT_DIR_ARG"
  fi
else
  TIMESTAMP=$(date +%Y%m%d%H%M%S)
  OUTPUT_DIR="$BASE_OUT_DIR/$TIMESTAMP"
fi

# Create necessary directories
mkdir -p "$BASE_IN_DIR" "$BASE_OUT_DIR" "$OUTPUT_DIR"

# Verify input exists
if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Input file not found: $INPUT_FILE"
  exit 1
fi

# Get total duration
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_FILE")
START=0
INDEX=1

if [[ "$MODE" == "fixed" ]]; then
  # Fixed interval splitting
  while (( $(echo "$START < $DURATION" | bc -l) )); do
    END=$(echo "$START + $CHUNK_LENGTH" | bc)
    if (( $(echo "$END > $DURATION" | bc -l) )); then
      END="$DURATION"
    fi
    DURATION_PART=$(echo "$END - $START" | bc)
    OUTFILE=$(printf "%s/part_%02d.m4a" "$OUTPUT_DIR" "$INDEX")
    echo "Exporting $OUTFILE (start=$START, duration=$DURATION_PART)"
    ffmpeg -y -i "$INPUT_FILE" -ss "$START" -t "$DURATION_PART" "$OUTFILE" || { echo "Error splitting $OUTFILE"; exit 1; }
    START="$END"
    INDEX=$((INDEX + 1))
  done
else
  # Silence-based splitting
  TMP_SILENCE=$(mktemp)
  echo "Detecting silence (threshold=${SILENCE_THRESHOLD}dB, min_duration=${SILENCE_DURATION}s) up to ${CHUNK_LENGTH}s with seek window ${SILENCE_SEEK}s"
  ffmpeg -i "$INPUT_FILE" -af silencedetect=noise=-${SILENCE_THRESHOLD}dB:d=${SILENCE_DURATION} -f null - 2> "$TMP_SILENCE" || { echo "Error during silence detection"; rm "$TMP_SILENCE"; exit 1; }

  SPLIT_POINTS=()
  NEXT_SPLIT="$CHUNK_LENGTH"

  while read -r LINE; do
    if [[ "$LINE" =~ silence_end: ]]; then
      TIME=$(echo "$LINE" | grep -oP 'silence_end: \K[0-9\.]+')
      # Check if TIME falls within [NEXT_SPLIT - SILENCE_SEEK, NEXT_SPLIT]
      LOWER=$(echo "$NEXT_SPLIT - $SILENCE_SEEK" | bc)
      if (( $(echo "$TIME <= $NEXT_SPLIT" | bc -l) )) && (( $(echo "$TIME >= $LOWER" | bc -l) )); then
        CUT_POINT=$(echo "$TIME - $PADDING" | bc)
        (( $(echo "$CUT_POINT < 0" | bc -l) )) && CUT_POINT=0
        SPLIT_POINTS+=("$CUT_POINT")
        NEXT_SPLIT=$(echo "$NEXT_SPLIT + $CHUNK_LENGTH" | bc)
      fi
    fi
  done < "$TMP_SILENCE"
  rm "$TMP_SILENCE"

  # Ensure final end point
  SPLIT_POINTS+=("$DURATION")

  for END in "${SPLIT_POINTS[@]}"; do
    DURATION_PART=$(echo "$END - $START" | bc)
    OUTFILE=$(printf "%s/part_%02d.m4a" "$OUTPUT_DIR" "$INDEX")
    echo "Exporting $OUTFILE (start=$START, duration=$DURATION_PART)"
    ffmpeg -y -i "$INPUT_FILE" -ss "$START" -t "$DURATION_PART" "$OUTFILE" || { echo "Error splitting $OUTFILE"; exit 1; }
    START="$END"
    INDEX=$((INDEX + 1))
  done
fi

echo "Done. Split into $((INDEX - 1)) parts."
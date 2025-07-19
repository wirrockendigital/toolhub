#!/bin/bash
set -euo pipefail
LOGFILE="/logs/audio-split.log"
# Ensure log directories exist
mkdir -p "$(dirname "$LOGFILE")"
# Initialize log files
touch "$LOGFILE"
# Redirect stdout and stderr to main log
exec >>"$LOGFILE" 2>&1
echo "Script invoked at $(date) with arguments: $*"
echo "Environment PATH: $PATH"
# Trap errors: log any failed command with timestamp, line number and exit status
trap 'echo "[$(date)] ERROR in $0 at line $LINENO: \"$BASH_COMMAND\" exited with status $?." >> "$LOGFILE"' ERR
echo "==== $(date) ===="
# Verify required tools are available before continuing
for cmd in ffmpeg ffprobe bc; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command '$cmd' not found" >&2
    exit 1
  fi
done
echo "Verified required commands: ffmpeg, ffprobe, bc"
# audio-split.sh - Split audio files in fixed or silence-based chunks
# Usage:
#   ./audio-split.sh --mode fixed|silence --chunk-length <seconds> --input <file> [--output <dir>] [--silence-seek <seconds>] [--silence-duration <seconds>] [--silence-threshold <dB>] [--padding <seconds>] [--enhance] [--enhance-speech]


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
    --enhance) ENHANCE=1; shift ;;
    --enhance-speech) ENHANCE_SPEECH=1; shift ;;
    *) echo "Unknown parameter: $1"; exit 1;;
  esac
done
echo "Parsed parameters: MODE=$MODE, CHUNK_LENGTH=$CHUNK_LENGTH, INPUT_PATH=$INPUT_PATH, OUTPUT_DIR_ARG=${OUTPUT_DIR_ARG-}, SILENCE_SEEK=${SILENCE_SEEK-}, SILENCE_DURATION=${SILENCE_DURATION-}, SILENCE_THRESHOLD=${SILENCE_THRESHOLD-}, PADDING=${PADDING-}, ENHANCE=${ENHANCE-}, ENHANCE_SPEECH=${ENHANCE_SPEECH-}"

# Ensure enhance flags are mutually exclusive
if [[ -n "${ENHANCE-}" && -n "${ENHANCE_SPEECH-}" ]]; then
  echo "Error: --enhance and --enhance-speech cannot be used together" >&2
  exit 1
fi

# Validate required parameters
if [[ -z "${MODE-}" || -z "${CHUNK_LENGTH-}" || -z "${INPUT_PATH-}" ]]; then
  echo "Usage: $0 --mode fixed|silence --chunk-length <seconds> --input <file> [--output <dir>] [--silence-seek <seconds>] [--silence-duration <seconds>] [--silence-threshold <dB>] [--padding <seconds>] [--enhance] [--enhance-speech]"
  exit 1
fi

# Silence mode requires extra parameters
if [[ "$MODE" == "silence" ]]; then
  if [[ -z "${SILENCE_SEEK-}" || -z "${SILENCE_DURATION-}" ]]; then
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
echo "Resolved input file path: $INPUT_FILE"

# Preprocess audio with optional filters
if [[ "${ENHANCE_SPEECH-}" == "1" ]]; then
  FILTERS="highpass=f=80, lowpass=f=4000, equalizer=f=1000:width_type=o:width=2:g=6, afftdn"
elif [[ "${ENHANCE-}" == "1" ]]; then
  FILTERS="highpass=f=100, lowpass=f=3000, afftdn"
fi

if [[ -n "${FILTERS-}" ]]; then
  echo "Enhancing audio: setting mono, 16kHz, 64k bitrate, filters [$FILTERS]"
  ENHANCED_FILE=$(mktemp --suffix ".m4a")
  echo "Running: ffmpeg -y -i \"$INPUT_FILE\" -ar 16000 -ac 1 -b:a 64k -af \"$FILTERS\" \"$ENHANCED_FILE\""
  ffmpeg -y -i "$INPUT_FILE" -ar 16000 -ac 1 -b:a 64k -af "$FILTERS" "$ENHANCED_FILE" || { echo "Error enhancing audio" >&2; exit 1; }
  INPUT_FILE="$ENHANCED_FILE"
fi

# Determine output directory
if [[ -n "${OUTPUT_DIR_ARG-}" ]]; then
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
echo "Total input duration: $DURATION seconds"
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
    echo "Running: ffmpeg -y -i \"$INPUT_FILE\" -ss \"$START\" -t \"$DURATION_PART\" \"$OUTFILE\""
    ffmpeg -y -i "$INPUT_FILE" -ss "$START" -t "$DURATION_PART" "$OUTFILE" || { echo "Error splitting $OUTFILE" >&2; exit 1; }
    echo "Created chunk file: $OUTFILE"
    START="$END"
    INDEX=$((INDEX + 1))
  done
else
  # Silence-based splitting
  TMP_SILENCE=$(mktemp)
  echo "Detecting silence (threshold=${SILENCE_THRESHOLD}dB, min_duration=${SILENCE_DURATION}s) up to ${CHUNK_LENGTH}s with seek window ${SILENCE_SEEK}s"
  echo "Running: ffmpeg -i \"$INPUT_FILE\" -af silencedetect=noise=${SILENCE_THRESHOLD}dB:d=${SILENCE_DURATION} -f null -"
  ffmpeg -i "$INPUT_FILE" -af silencedetect=noise=${SILENCE_THRESHOLD}dB:d=${SILENCE_DURATION} -f null - 2> "$TMP_SILENCE" || { echo "Error during silence detection" >&2; rm "$TMP_SILENCE"; exit 1; }
  echo "Silence detection log:"
  cat "$TMP_SILENCE"

  # Collect all silence_end timestamps
  SILENCE_TIMES=()
  while read -r LINE; do
    if [[ "$LINE" =~ silence_end: ]]; then
      TIME=$(echo "$LINE" | grep -oP 'silence_end: \K[0-9\.]+')
      SILENCE_TIMES+=("$TIME")
    fi
  done < "$TMP_SILENCE"
  rm "$TMP_SILENCE"
  echo "Collected silence end times: ${SILENCE_TIMES[*]}"

  # Determine split points at each chunk boundary or nearest silence
  SPLIT_POINTS=()
  CURRENT=0
  while (( $(echo "$CURRENT + $CHUNK_LENGTH < $DURATION" | bc -l) )); do
    BOUNDARY=$(echo "$CURRENT + $CHUNK_LENGTH" | bc)
    LOWER=$(echo "$BOUNDARY - $SILENCE_SEEK" | bc)
    SELECTED="$BOUNDARY"
    for T in "${SILENCE_TIMES[@]}"; do
      if (( $(echo "$T <= $BOUNDARY" | bc -l) )) && (( $(echo "$T >= $LOWER" | bc -l) )); then
        SELECTED="$T"
        break
      fi
    done
    CUT_POINT=$(echo "$SELECTED - $PADDING" | bc)
    if (( $(echo "$CUT_POINT < 0" | bc -l) )); then CUT_POINT=0; fi
    SPLIT_POINTS+=("$CUT_POINT")
    CURRENT="$BOUNDARY"
  done
  # Always include end of file
  SPLIT_POINTS+=("$DURATION")
  echo "Calculated split points: ${SPLIT_POINTS[*]}"

  for END in "${SPLIT_POINTS[@]}"; do
    DURATION_PART=$(echo "$END - $START" | bc)
    OUTFILE=$(printf "%s/part_%02d.m4a" "$OUTPUT_DIR" "$INDEX")
    echo "Exporting $OUTFILE (start=$START, duration=$DURATION_PART)"
    echo "Running: ffmpeg -y -i \"$INPUT_FILE\" -ss \"$START\" -t \"$DURATION_PART\" \"$OUTFILE\""
    ffmpeg -y -i "$INPUT_FILE" -ss "$START" -t "$DURATION_PART" "$OUTFILE" || { echo "Error splitting $OUTFILE" >&2; exit 1; }
    echo "Created chunk file: $OUTFILE"
    START="$END"
    INDEX=$((INDEX + 1))
  done
fi

# Clean up temporary enhanced file if created
if [[ -n "${ENHANCED_FILE-}" ]]; then
  rm "$ENHANCED_FILE"
fi
echo "Cleaned up enhanced file: ${ENHANCED_FILE-}"

echo "Listing output directory before verification:"
ls -1 "$OUTPUT_DIR"

# Verify that at least one output file exists
if ! compgen -G "$OUTPUT_DIR/*.m4a" > /dev/null; then
  echo "No audio chunks were created. Exiting with error." >&2
  exit 1
fi

echo "Final directory contents:"
ls -1 "$OUTPUT_DIR"

echo "Done. Split into $((INDEX - 1)) parts."

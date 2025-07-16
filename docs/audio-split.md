# Audio Split Usage

`scripts/audio-split.sh` splits an audio file into fixed-size chunks or at points of silence.

## Syntax

```bash
./audio-split.sh --mode fixed|silence --chunk-length <seconds> --input <file> [--output <dir>] \
  [--silence-seek <seconds>] [--silence-duration <seconds>] [--silence-threshold <dB>] \
  [--padding <seconds>] [--enhance] [--enhance-speech]
```

- `--mode fixed` splits on exact intervals.
- `--mode silence` begins each chunk on the next silence. Use `--silence-seek`, `--silence-duration`, and `--silence-threshold` to fine‑tune detection. Optional `--padding` adds silence around cuts.
- `--chunk-length` sets the desired chunk duration.
- `--input` is the path to the source audio file. `--output` sets the destination directory (defaults to `/shared/audio/out`).
- `--enhance` or `--enhance-speech` apply noise‑reduction filters (mutually exclusive).

## Examples

Split every 30 seconds:

```bash
./audio-split.sh --mode fixed --chunk-length 30 --input song.m4a
```

Split on silence, starting detection from the beginning:

```bash
./audio-split.sh --mode silence --chunk-length 30 --input talk.m4a \
  --silence-seek 0 --silence-duration 0.3 --silence-threshold -30
```

Logs are stored in `/logs/split-audio.log`.

## Usage via SSH

1. Copy your `.m4a` file into `/shared/audio/in`.
2. Run the script inside the container:
   ```bash
   /scripts/audio-split.sh --mode fixed --chunk-length 30 --input myfile.m4a
   ```
3. Chunks are written to `/shared/audio/out/<timestamp>/`.

## Usage via Webhook

Send a `POST` request to the `/audio-split` endpoint. Example using `curl`:

```bash
curl -F "file=@myfile.m4a" -F "mode=fixed" -F "chunk_length=30" \
     http://<toolhub-ip>:5656/audio-split -o audio-split.zip
```

The endpoint returns a ZIP archive containing the split audio files.

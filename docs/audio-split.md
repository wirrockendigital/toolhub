from flask import Flask, request, jsonify, send_file
import subprocess
import tempfile
import os
import zipfile
import uuid

app = Flask(__name__)

@app.route('/audio-split', methods=['POST'])
def audio_split():
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400

    mode = request.form.get('mode')
    chunk_length = request.form.get('chunk_length')
    silence_seek = request.form.get('silence_seek')
    silence_duration = request.form.get('silence_duration')
    silence_threshold = request.form.get('silence_threshold')
    padding = request.form.get('padding')

    # Enhancement flags
    enhance = bool(request.form.get('enhance'))
    enhance_speech = bool(request.form.get('enhance_speech'))
    if enhance and enhance_speech:
        return jsonify(error="`enhance` and `enhance_speech` cannot be used together"), 400

    if not mode or not chunk_length:
        return jsonify(error="Missing required parameters"), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, 'input_audio')
        file.save(input_path)

        output_dir = os.path.join(tmpdir, 'output')
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            '/volume1/docker/toolhub/scripts/audio-split.sh',
            '--mode', mode,
            '--chunk-length', chunk_length,
            '--input', input_path,
            '--output', output_dir
        ]

        if mode == 'silence':
            if silence_seek:
                cmd.extend(['--silence-seek', silence_seek])
            if silence_duration:
                cmd.extend(['--silence-duration', silence_duration])
            if silence_threshold:
                cmd.extend(['--silence-threshold', silence_threshold])
            if padding:
                cmd.extend(['--padding', padding])

        # Pass enhancement flags to the splitter script
        if enhance_speech:
            cmd.append('--enhance-speech')
        elif enhance:
            cmd.append('--enhance')

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            return jsonify(error=f"Audio splitting failed: {e.stderr}"), 500

        zip_path = os.path.join(tmpdir, 'result.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(output_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, output_dir)
                    zipf.write(filepath, arcname)

        return send_file(zip_path, mimetype='application/zip', as_attachment=True,
                         download_name=f"split-audio-{uuid.uuid4()}.zip")

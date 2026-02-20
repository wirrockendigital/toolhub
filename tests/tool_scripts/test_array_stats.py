from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ArrayStatsScriptTests(unittest.TestCase):
    def test_array_stats_from_inline_json(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir)
            script = Path(__file__).resolve().parents[2] / "scripts" / "array-stats.py"
            command = [
                "python3",
                str(script),
                "--numbers-json",
                "[1,2,3,4]",
                "--output-dir",
                str(output_dir),
                "--output-filename",
                "stats.json",
            ]

            # Execute script as CLI to verify argument parsing and JSON output.
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            payload = json.loads(result.stdout)
            self.assertEqual(payload.get("status"), "ok")
            output_file = Path(payload["output_file"])
            self.assertTrue(output_file.exists())

            saved = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["count"], 4)
            self.assertAlmostEqual(saved["mean"], 2.5)
            self.assertAlmostEqual(saved["sum"], 10.0)


if __name__ == "__main__":
    unittest.main()

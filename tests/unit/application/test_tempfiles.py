import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from depression_detection.shared.tempfiles import FFMPEG_PREFIX, UPLOAD_PREFIX, WHISPER_PREFIX, cleanup_stale_temp_artifacts


class TempfileCleanupTests(unittest.TestCase):
    def test_cleanup_stale_temp_artifacts_removes_only_old_known_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_file = root / f"{UPLOAD_PREFIX}old.wav"
            old_file.write_text("x", encoding="utf-8")
            old_dir = root / f"{WHISPER_PREFIX}old"
            old_dir.mkdir()
            (old_dir / "a.txt").write_text("x", encoding="utf-8")
            recent_file = root / f"{FFMPEG_PREFIX}recent.wav"
            recent_file.write_text("x", encoding="utf-8")
            other_file = root / "unrelated.tmp"
            other_file.write_text("x", encoding="utf-8")

            old_timestamp = time.time() - 1000
            os.utime(old_file, (old_timestamp, old_timestamp))
            os.utime(old_dir, (old_timestamp, old_timestamp))
            os.utime(recent_file, None)

            with patch("depression_detection.shared.tempfiles.get_temp_root", return_value=root):
                result = cleanup_stale_temp_artifacts(max_age_seconds=300)

            self.assertEqual(result["removed_files"], 1)
            self.assertEqual(result["removed_dirs"], 1)
            self.assertFalse(old_file.exists())
            self.assertFalse(old_dir.exists())
            self.assertTrue(recent_file.exists())
            self.assertTrue(other_file.exists())


if __name__ == "__main__":
    unittest.main()

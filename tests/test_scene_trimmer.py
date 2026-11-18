
import unittest

from clipmate.modules.scene_trimmer import SceneTrimmer


class TestSceneTrimmer(unittest.TestCase):

    def setUp(self):
        self.trimmer = SceneTrimmer()

    def test_negative_start_time(self):
        with self.assertRaises(ValueError):
            self.trimmer.trim("missing.mp4", -1, 10)

    def test_end_before_start(self):
        with self.assertRaises(ValueError):
            self.trimmer.trim("missing.mp4", 10, 5)

    def test_equal_timestamps(self):
        with self.assertRaises(ValueError):
            self.trimmer.trim("missing.mp4", 10, 10)

    def test_missing_video(self):
        with self.assertRaises(FileNotFoundError):
            self.trimmer.trim("missing.mp4", 0, 10)

    def test_infinite_timestamp(self):
        with self.assertRaises(ValueError):
            self.trimmer.trim("missing.mp4", 0, float("inf"))


if __name__ == "__main__":
    unittest.main()

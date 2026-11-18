
import unittest

from clipmate.pipeline import (
    ClipMatePipeline,
    PipelineSettings
)


class TestPipelineTrimming(unittest.TestCase):

    def test_trimming_disabled(self):
        settings = PipelineSettings(trim_scenes=False)
        pipeline = ClipMatePipeline(settings)

        with self.assertRaises(RuntimeError):
            pipeline.trim_video("missing.mp4", 0, 10)

    def test_invalid_timestamps_rejected(self):
        pipeline = ClipMatePipeline()

        with self.assertRaises(ValueError):
            pipeline.trim_video("missing.mp4", 10, 5)


if __name__ == "__main__":
    unittest.main()

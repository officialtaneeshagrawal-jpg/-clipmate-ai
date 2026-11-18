import unittest

from clipmate.pipeline import (
    ClipMatePipeline,
    PipelineSettings
)


class TestClipMatePipeline(unittest.TestCase):

    def test_default_workflow(self):
        pipeline = ClipMatePipeline()
        workflow = pipeline.get_workflow()["workflow"]

        self.assertIn("highlight_detection", workflow)
        self.assertIn("caption_generation", workflow)
        self.assertIn("final_clip_generation", workflow)

    def test_disabled_features(self):
        settings = PipelineSettings(
            generate_captions=False,
            enhance_audio=False
        )

        pipeline = ClipMatePipeline(settings)
        workflow = pipeline.get_workflow()["workflow"]

        self.assertNotIn("caption_generation", workflow)
        self.assertNotIn("audio_enhancement", workflow)

    def test_final_generator_always_runs(self):
        settings = PipelineSettings(
            detect_highlights=False,
            trim_scenes=False,
            generate_captions=False,
            convert_to_reel=False,
            smart_reframing=False,
            enhance_audio=False
        )

        pipeline = ClipMatePipeline(settings)

        self.assertEqual(
            pipeline.get_workflow()["workflow"],
            ["final_clip_generation"]
        )


if __name__ == "__main__":
    unittest.main()
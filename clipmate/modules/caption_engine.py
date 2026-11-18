"""
ClipMate AI - Caption Engine

Responsible for generating subtitles
in Hindi, Hinglish and English.
"""


class CaptionEngine:

    def generate(self, video_path: str, language: str = "auto") -> dict:

        supported_languages = [
            "auto",
            "english",
            "hindi",
            "hinglish"
        ]

        if language not in supported_languages:
            raise ValueError("Unsupported caption language.")

        raise NotImplementedError(
            "Speech recognition and caption generation "
            "will be connected later."
        )
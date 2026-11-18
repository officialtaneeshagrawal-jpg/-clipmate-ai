"""
ClipMate AI - Highlight Detector

Responsible for identifying interesting moments
in a video and returning their timestamps.
"""


class HighlightDetector:

    def detect(self, video_path: str) -> list:
        """
        Analyze a video and return selected highlights.

        Each highlight will eventually contain:
        - start_seconds
        - end_seconds
        - score
        - reason
        """

        raise NotImplementedError(
            "Highlight detection engine is not implemented yet."
        )
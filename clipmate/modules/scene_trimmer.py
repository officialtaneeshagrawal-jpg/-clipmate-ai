"""
ClipMate AI - Scene Trimmer

Responsible for trimming selected video sections.
"""


class SceneTrimmer:

    def trim(self, video_path: str, start_seconds: float,
             end_seconds: float) -> dict:

        if start_seconds < 0:
            raise ValueError("Start time cannot be negative.")

        if end_seconds <= start_seconds:
            raise ValueError("End time must be after start time.")

        raise NotImplementedError(
            "Video trimming engine is not connected yet."
        )
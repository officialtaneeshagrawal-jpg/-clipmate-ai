
"""
ClipMate AI - Video Intelligence

Analyses uploaded videos and provides:
- Video metadata
- Scene change detection
- Keyframe extraction
"""

import json
import subprocess
from pathlib import Path

import cv2


class VideoIntelligence:

    def __init__(self):
        self.ffmpeg = None

    def _get_ffmpeg(self):
        if self.ffmpeg is None:
            import imageio_ffmpeg
            self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        return self.ffmpeg

    def get_video_metadata(self, video_path: str) -> dict:
        source = Path(video_path)

        if not source.is_file():
            raise FileNotFoundError("Input video file was not found.")

        capture = cv2.VideoCapture(str(source))

        if not capture.isOpened():
            raise RuntimeError("Unable to open video.")

        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frame_count = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

            duration = (
                frame_count / fps
                if fps > 0 else 0
            )

            return {
                "status": "success",
                "file": source.name,
                "duration_seconds": round(duration, 2),
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "fps": round(fps, 2),
                "frame_count": frame_count,
                "has_video": frame_count > 0
            }

        finally:
            capture.release()

    def detect_scenes(
        self,
        video_path: str,
        threshold: float = 30.0,
        minimum_gap_seconds: float = 1.0
    ) -> dict:

        source = Path(video_path)

        if not source.is_file():
            raise FileNotFoundError("Input video file was not found.")

        if threshold <= 0 or minimum_gap_seconds < 0:
            raise ValueError("Invalid scene detection settings.")

        capture = cv2.VideoCapture(str(source))

        if not capture.isOpened():
            raise RuntimeError("Unable to open video.")

        fps = capture.get(cv2.CAP_PROP_FPS)

        if fps <= 0:
            capture.release()
            raise RuntimeError("Unable to determine video FPS.")

        scenes = []
        previous_frame = None
        frame_number = 0
        last_scene_time = 0.0

        try:
            while True:
                success, frame = capture.read()

                if not success:
                    break

                frame_number += 1

                # Resize frames for efficient comparison.
                small = cv2.resize(
                    frame,
                    (320, 180)
                )

                gray = cv2.cvtColor(
                    small,
                    cv2.COLOR_BGR2GRAY
                )

                if previous_frame is not None:
                    difference = cv2.absdiff(
                        previous_frame,
                        gray
                    )

                    score = float(difference.mean())
                    timestamp = frame_number / fps

                    if (
                        score >= threshold
                        and timestamp - last_scene_time
                        >= minimum_gap_seconds
                    ):
                        scenes.append({
                            "timestamp_seconds": round(
                                timestamp, 2
                            ),
                            "change_score": round(score, 2)
                        })

                        last_scene_time = timestamp

                previous_frame = gray

        finally:
            capture.release()

        return {
            "status": "success",
            "video": source.name,
            "scene_count": len(scenes) + 1,
            "scene_changes": scenes
        }

    def extract_keyframes(
        self,
        video_path: str,
        output_dir: str = "/tmp/clipmate/keyframes",
        interval_seconds: float = 10.0
    ) -> dict:

        source = Path(video_path)

        if not source.is_file():
            raise FileNotFoundError("Input video file was not found.")

        if interval_seconds <= 0:
            raise ValueError("Interval must be greater than zero.")

        output = (
            Path(output_dir) /
            source.stem
        )

        output.mkdir(parents=True, exist_ok=True)

        capture = cv2.VideoCapture(str(source))

        if not capture.isOpened():
            raise RuntimeError("Unable to open video.")

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(
            capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if fps <= 0:
            capture.release()
            raise RuntimeError("Unable to determine video FPS.")

        duration = frame_count / fps
        keyframes = []

        try:
            timestamp = 0.0
            index = 1

            while timestamp < duration:
                capture.set(
                    cv2.CAP_PROP_POS_MSEC,
                    timestamp * 1000
                )

                success, frame = capture.read()

                if not success:
                    break

                filename = f"keyframe_{index:04d}.jpg"
                frame_path = output / filename

                saved = cv2.imwrite(
                    str(frame_path),
                    frame
                )

                if not saved:
                    raise RuntimeError(
                        f"Could not save keyframe: {filename}"
                    )

                keyframes.append({
                    "timestamp_seconds": round(timestamp, 2),
                    "file": str(frame_path)
                })

                timestamp += interval_seconds
                index += 1

        finally:
            capture.release()

        return {
            "status": "success",
            "video": source.name,
            "keyframe_count": len(keyframes),
            "keyframes": keyframes
        }

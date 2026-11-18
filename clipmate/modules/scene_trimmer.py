
"""
ClipMate AI - Scene Trimmer

Cuts a selected section from a video and exports it as MP4.
"""

import math
import subprocess
import uuid
from pathlib import Path


class SceneTrimmer:

    def trim(
        self,
        video_path: str,
        start_seconds: float,
        end_seconds: float,
        output_path: str = None
    ) -> dict:

        # Validate timestamps
        if not math.isfinite(start_seconds) or not math.isfinite(end_seconds):
            raise ValueError("Timestamps must be finite numbers.")

        if start_seconds < 0:
            raise ValueError("Start time cannot be negative.")

        if end_seconds <= start_seconds:
            raise ValueError("End time must be after start time.")

        source = Path(video_path)

        if not source.is_file():
            raise FileNotFoundError("Input video file was not found.")

        if output_path is None:
            output_dir = Path("/tmp/clipmate/clips")
            output_dir.mkdir(parents=True, exist_ok=True)

            output = output_dir / (
                f"{source.stem}_{uuid.uuid4().hex[:8]}.mp4"
            )
        else:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

        if source.resolve() == output.resolve():
            raise ValueError("Input and output paths must be different.")

        # Load FFmpeg only when actual processing is requested.
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        duration = end_seconds - start_seconds

        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-ss", str(start_seconds),
            "-i", str(source),
            "-t", str(duration),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output)
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Video trimming timed out.")

        except subprocess.CalledProcessError as error:
            message = (error.stderr or "Unknown FFmpeg error")[-1000:]
            raise RuntimeError(f"FFmpeg failed: {message}")

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not produce a valid output file.")

        return {
            "status": "success",
            "input": str(source),
            "output": str(output),
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "duration_seconds": duration,
            "format": "mp4"
        }


import os
import uuid
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
import yt_dlp
import imageio_ffmpeg

from clipmate.pipeline import ClipMatePipeline, PipelineSettings

from clipmate.modules.captioner import add_captions, transcribe_video

from clipmate.modules.video_intelligence import VideoIntelligence

PORT = int(os.environ.get("PORT", 8000))

app = FastMCP(
    "ClipMate AI",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True
)

video_intelligence = VideoIntelligence()

BASE_DIR = Path("/tmp/clipmate")
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


@app.tool()
def get_project_status() -> dict:
    """Get ClipMate AI project information."""

    return {
        "name": "ClipMate AI",
        "creator": "Taneesh Agrawal",
        "status": "Running",
        "features": [
            "Video information",
            "Video downloading",
            "Basic clip generation",
            "MP4 export",
            "Modular pipeline",
            "FFmpeg scene trimming"
        ]
    }


@app.tool()
def get_pipeline_workflow(
    detect_highlights: bool = True,
    trim_scenes: bool = True,
    generate_captions: bool = True,
    convert_to_reel: bool = True,
    smart_reframing: bool = True,
    enhance_audio: bool = True
) -> dict:
    """Configure and inspect the processing workflow."""

    settings = PipelineSettings(
        detect_highlights=detect_highlights,
        trim_scenes=trim_scenes,
        generate_captions=generate_captions,
        convert_to_reel=convert_to_reel,
        smart_reframing=smart_reframing,
        enhance_audio=enhance_audio
    )

    return ClipMatePipeline(settings).get_workflow()



@app.tool()
def inspect_video_url(url: str) -> dict:
    """Inspect an authorized video URL and collect diagnostic information."""

    if urlparse(url).scheme != "https":
        return {"error": "Only HTTPS URLs are accepted."}

    class DiagnosticLogger:
        def __init__(self):
            self.messages = []

        def debug(self, message):
            self.messages.append(str(message))

        def warning(self, message):
            self.messages.append("WARNING: " + str(message))

        def error(self, message):
            self.messages.append("ERROR: " + str(message))

    logger = DiagnosticLogger()

    options = {
        "quiet": True,
        "no_warnings": False,
        "verbose": True,
        "skip_download": True,
        "noplaylist": True,
        "logger": logger
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "duration_seconds": info.get("duration"),
            "uploader": info.get("uploader"),
            "status": "Video information retrieved"
        }

    except Exception as error:
        return {
            "status": "Inspection failed",
            "error": str(error)[:1000],
            "diagnostic_logs": logger.messages[-30:]
        }



@app.tool()
def create_basic_clips(url: str, clip_count: int = 3) -> dict:
    """Create evenly spaced clips from an authorized video."""

    if urlparse(url).scheme != "https":
        return {"error": "Only HTTPS URLs are accepted."}

    if not 1 <= clip_count <= 5:
        return {"error": "Choose between 1 and 5 clips."}

    job_id = uuid.uuid4().hex[:10]
    source = DOWNLOAD_DIR / f"{job_id}.mp4"

    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": str(source),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        duration = float(info.get("duration") or 0)

        if duration <= 0:
            return {"error": "Could not determine video duration."}

        segment = duration / clip_count
        results = []

        for index in range(clip_count):
            start = index * segment
            length = min(segment, duration - start)

            output = OUTPUT_DIR / f"{job_id}_clip_{index + 1}.mp4"

            command = [
                FFMPEG, "-y",
                "-ss", str(start),
                "-i", str(source),
                "-t", str(length),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                str(output)
            ]

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=300
            )

            results.append({
                "clip": index + 1,
                "start_seconds": round(start, 2),
                "end_seconds": round(start + length, 2),
                "file": str(output)
            })

        return {
            "creator": "Taneesh Agrawal",
            "video_title": info.get("title"),
            "clips": results,
            "note": "Basic evenly spaced clips, not AI-selected highlights."
        }

    except Exception as error:
        return {"error": str(error)[:500]}

    finally:
        if source.exists():
            source.unlink()


@app.tool()
def trim_video_section(
    video_path: str,
    start_seconds: float,
    end_seconds: float
) -> dict:
    """
    Trim a video already present in the server's downloads folder.
    The user must own or have permission to process the video.
    """

    try:
        source = Path(video_path).resolve()
        allowed_directory = DOWNLOAD_DIR.resolve()

        if not source.is_relative_to(allowed_directory):
            return {
                "error": "Video must be inside the server downloads folder."
            }

        if not source.is_file():
            return {"error": "Video file not found on the server."}

        job_id = uuid.uuid4().hex[:10]
        output = OUTPUT_DIR / f"{job_id}_trimmed.mp4"

        pipeline = ClipMatePipeline()

        result = pipeline.trim_video(
            video_path=str(source),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            output_path=str(output)
        )

        return {
            "creator": "Taneesh Agrawal",
            "result": result,
            "note": (
                "The MP4 is saved on the server. "
                "A downloadable link is not implemented yet."
            )
        }

    except Exception as error:
        return {"error": str(error)[:1000]}


@app.tool()
def transcribe_uploaded_video(video_path: str) -> dict:
    """
    Extract speech and return detected language
    with timestamped transcript segments to Claude.
    """

    try:
        source = Path(video_path).resolve()
        allowed_directory = DOWNLOAD_DIR.resolve()

        if not source.is_relative_to(allowed_directory):
            return {
                "status": "error",
                "message": "Video must be inside the server downloads folder."
            }

        if not source.is_file():
            return {
                "status": "error",
                "message": "Uploaded video not found."
            }

        return transcribe_video(str(source))

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)[:1000]
        }


@app.tool()
def caption_uploaded_video(video_path: str) -> dict:
    """Generate and burn captions into a video already uploaded to cloud."""

    try:
        source = Path(video_path).resolve()
        allowed_directory = DOWNLOAD_DIR.resolve()

        if not source.is_relative_to(allowed_directory):
            return {
                "error": "Video must be inside the server downloads folder."
            }

        if not source.is_file():
            return {"error": "Uploaded video not found."}

        job_id = uuid.uuid4().hex[:10]
        output = OUTPUT_DIR / f"{job_id}_captioned.mp4"

        result = add_captions(
            str(source),
            str(output)
        )

        return {
            "creator": "Taneesh Agrawal",
            "status": "Captioning completed",
            "result": result,
            "output_file": str(output)
        }

    except Exception as error:
        return {
            "status": "Captioning failed",
            "error": str(error)[:1000]
        }


@app.tool()
def analyze_video_metadata(video_path: str) -> dict:
    """
    Get video duration, resolution, FPS and frame count.
    """
    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside the uploads directory."
            }

        return video_intelligence.get_video_metadata(
            str(source)
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }


@app.tool()
def detect_video_scenes(
    video_path: str,
    threshold: float = 30.0,
    minimum_gap_seconds: float = 1.0
) -> dict:
    """
    Detect scene changes and return their timestamps.
    """
    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside the uploads directory."
            }

        return video_intelligence.detect_scenes(
            str(source),
            threshold=threshold,
            minimum_gap_seconds=minimum_gap_seconds
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }

@app.tool()
def extract_video_keyframes(
    video_path: str,
    interval_seconds: float = 10.0
) -> dict:
    """
    Extract representative frames from an uploaded video at regular intervals.
    """
    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside the uploads directory."
            }

        return video_intelligence.extract_keyframes(
            str(source),
            interval_seconds=interval_seconds
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }


if __name__ == "__main__":
    app.run(transport="streamable-http")

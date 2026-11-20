
"""
ClipMate AI - MCP Server
Existing video tools + direct HTTP upload + full-video captioning.
"""

from clipmate import clipmate_caption_support as caption_support

import os
import shutil
import uuid
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
import imageio_ffmpeg

from mcp.server.fastmcp import FastMCP

from clipmate.pipeline import ClipMatePipeline, PipelineSettings
from clipmate.modules.captioner import add_captions
from clipmate.modules.video_intelligence import VideoIntelligence

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PORT = int(os.environ.get("PORT", "8000"))

BASE_DIR = Path(
    os.environ.get("CLIPMATE_BASE_DIR", "/tmp/clipmate")
)

DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Both the MCP tools and HTTP upload module use this directory.
os.environ["CLIPMATE_DOWNLOADS"] = str(DOWNLOAD_DIR)

FFMPEG = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()

video_intelligence = VideoIntelligence()

# ---------------------------------------------------------
# MCP server
# ---------------------------------------------------------

app = FastMCP(
    "ClipMate AI",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True,
)
caption_support.register(app)

# Register direct upload, transcription and caption rendering.
import clipmate_caption_support as caption_support

caption_support.register(app)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def safe_download_path(video_path: str) -> Path:
    source = Path(video_path).resolve()
    allowed = DOWNLOAD_DIR.resolve()

    if not source.is_relative_to(allowed):
        raise ValueError(
            "Video must be inside the ClipMate downloads folder."
        )

    if not source.is_file():
        raise FileNotFoundError("Video file not found.")

    return source


# ---------------------------------------------------------
# Project information
# ---------------------------------------------------------

@app.tool()
def get_project_status() -> dict:
    """Get ClipMate AI project information."""

    return {
        "name": "ClipMate AI",
        "creator": "Taneesh Agrawal",
        "status": "Running",
        "features": [
            "Direct HTTP video upload",
            "Full video transcription",
            "Word-level timestamps",
            "Hindi and English speech detection",
            "Claude-prepared captions",
            "Full-video caption rendering",
            "MP4 export",
            "Video information",
            "Basic clip generation",
            "Scene detection",
            "Keyframe extraction",
            "Video trimming",
        ],
        "upload_page": "/upload-page",
    }


# ---------------------------------------------------------
# Pipeline workflow
# ---------------------------------------------------------

@app.tool()
def get_pipeline_workflow(
    detect_highlights: bool = True,
    trim_scenes: bool = True,
    generate_captions: bool = True,
    convert_to_reel: bool = True,
    smart_reframing: bool = True,
    enhance_audio: bool = True,
) -> dict:

    settings = PipelineSettings(
        detect_highlights=detect_highlights,
        trim_scenes=trim_scenes,
        generate_captions=generate_captions,
        convert_to_reel=convert_to_reel,
        smart_reframing=smart_reframing,
        enhance_audio=enhance_audio,
    )

    return ClipMatePipeline(settings).get_workflow()


# ---------------------------------------------------------
# URL inspection
# ---------------------------------------------------------

@app.tool()
def inspect_video_url(url: str) -> dict:
    """Inspect an HTTPS video URL."""

    if urlparse(url).scheme != "https":
        return {"error": "Only HTTPS URLs are accepted."}

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }) as ydl:

            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "duration_seconds": info.get("duration"),
            "uploader": info.get("uploader"),
            "status": "Video information retrieved",
        }

    except Exception as error:
        return {
            "status": "Inspection failed",
            "error": str(error)[:1000],
        }


# ---------------------------------------------------------
# Basic clip generation
# ---------------------------------------------------------

@app.tool()
def create_basic_clips(
    url: str,
    clip_count: int = 3
) -> dict:
    """Create evenly spaced clips from an HTTPS video URL."""

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
        "noplaylist": True,
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

            output = OUTPUT_DIR / (
                f"{job_id}_clip_{index + 1}.mp4"
            )

            command = [
                FFMPEG,
                "-y",
                "-ss", str(start),
                "-i", str(source),
                "-t", str(length),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                str(output),
            ]

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=300,
            )

            results.append({
                "clip": index + 1,
                "start_seconds": round(start, 2),
                "end_seconds": round(start + length, 2),
                "file": str(output),
            })

        return {
            "creator": "Taneesh Agrawal",
            "video_title": info.get("title"),
            "clips": results,
            "note": "Basic evenly spaced clips.",
        }

    except Exception as error:
        return {"error": str(error)[:500]}

    finally:
        source.unlink(missing_ok=True)


# ---------------------------------------------------------
# Video trimming
# ---------------------------------------------------------

@app.tool()
def trim_video_section(
    video_path: str,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    """Trim a video stored in ClipMate downloads."""

    try:
        source = safe_download_path(video_path)

        output = OUTPUT_DIR / (
            f"{uuid.uuid4().hex[:10]}_trimmed.mp4"
        )

        result = ClipMatePipeline().trim_video(
            video_path=str(source),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            output_path=str(output),
        )

        return {
            "creator": "Taneesh Agrawal",
            "result": result,
            "output_file": str(output),
        }

    except Exception as error:
        return {"error": str(error)[:1000]}


# ---------------------------------------------------------
# Automatic captioning
# ---------------------------------------------------------

@app.tool()
def caption_uploaded_video(video_path: str) -> dict:
    """Automatically transcribe and caption an uploaded video."""

    try:
        source = safe_download_path(video_path)

        output = OUTPUT_DIR / (
            f"{uuid.uuid4().hex[:10]}_captioned.mp4"
        )

        result = add_captions(
            str(source),
            str(output),
        )

        return {
            "creator": "Taneesh Agrawal",
            "status": "Captioning completed",
            "result": result,
            "output_file": str(output),
        }

    except Exception as error:
        return {
            "status": "Captioning failed",
            "error": str(error)[:1000],
        }


# ---------------------------------------------------------
# Video metadata
# ---------------------------------------------------------

@app.tool()
def analyze_video_metadata(video_path: str) -> dict:
    """Get video duration, resolution, FPS and frame count."""

    try:
        source = safe_download_path(video_path)

        return video_intelligence.get_video_metadata(
            str(source)
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)[:1000],
        }


# ---------------------------------------------------------
# Scene detection
# ---------------------------------------------------------

@app.tool()
def detect_video_scenes(
    video_path: str,
    threshold: float = 30.0,
    minimum_gap_seconds: float = 1.0,
) -> dict:

    try:
        source = safe_download_path(video_path)

        return video_intelligence.detect_scenes(
            str(source),
            threshold=threshold,
            minimum_gap_seconds=minimum_gap_seconds,
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)[:1000],
        }


# ---------------------------------------------------------
# Keyframe extraction
# ---------------------------------------------------------

@app.tool()
def extract_video_keyframes(
    video_path: str,
    interval_seconds: float = 10.0,
) -> dict:

    try:
        source = safe_download_path(video_path)

        return video_intelligence.extract_keyframes(
            str(source),
            interval_seconds=interval_seconds,
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)[:1000],
        }


# ---------------------------------------------------------
# Start server
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(transport="streamable-http")

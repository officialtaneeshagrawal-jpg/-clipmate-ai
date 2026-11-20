import os
import base64
import hmac
import uuid
import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP, Context
import yt_dlp
import imageio_ffmpeg

from clipmate.pipeline import ClipMatePipeline, PipelineSettings

from clipmate.modules.captioner import (
    add_captions,
    transcribe_video,
    render_claude_captions
)

from clipmate.modules.video_intelligence import VideoIntelligence


# =====================================================
# CONFIGURATION
# =====================================================

PORT = int(os.environ.get("PORT", 8000))

UPLOAD_TOKEN = os.environ.get("CLIPMATE_UPLOAD_TOKEN")

BASE_DIR = Path("/tmp/clipmate")
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()

video_intelligence = VideoIntelligence()


# =====================================================
# MCP SERVER
# =====================================================

app = FastMCP(
    "ClipMate AI",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True
)


# =====================================================
# UPLOAD VIDEO
# =====================================================

@app.tool()
def upload_video(
    filename: str,
    video_base64: str,
    token: str,
    ctx: Context
) -> dict:
    """Upload a video into ClipMate's downloads directory."""

    if not UPLOAD_TOKEN:
        return {
            "status": "error",
            "message": "Upload authentication is not configured."
        }

    if not hmac.compare_digest(token, UPLOAD_TOKEN):
        return {
            "status": "error",
            "message": "Invalid upload authentication."
        }

    if not filename.lower().endswith(
        (".mp4", ".mov", ".mkv", ".webm")
    ):
        return {
            "status": "error",
            "message": "Unsupported video format."
        }

    try:
        video_data = base64.b64decode(
            video_base64,
            validate=True
        )

        if not video_data:
            return {
                "status": "error",
                "message": "Empty video file."
            }

        job_id = uuid.uuid4().hex[:12]

        safe_filename = (
            f"{job_id}_{Path(filename).name}"
        )

        destination = DOWNLOAD_DIR / safe_filename

        destination.write_bytes(video_data)

        return {
            "status": "success",
            "filename": safe_filename,
            "video_path": str(destination),
            "size_bytes": destination.stat().st_size
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc)
        }


# =====================================================
# PROJECT STATUS
# =====================================================

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
            "FFmpeg scene trimming",
            "Video transcription",
            "Caption rendering"
        ]
    }


# =====================================================
# PIPELINE WORKFLOW
# =====================================================

@app.tool()
def get_pipeline_workflow(
    detect_highlights: bool = True,
    trim_scenes: bool = True,
    generate_captions: bool = True,
    convert_to_reel: bool = True,
    smart_reframing: bool = True,
    enhance_audio: bool = True
) -> dict:

    settings = PipelineSettings(
        detect_highlights=detect_highlights,
        trim_scenes=trim_scenes,
        generate_captions=generate_captions,
        convert_to_reel=convert_to_reel,
        smart_reframing=smart_reframing,
        enhance_audio=enhance_audio
    )

    return ClipMatePipeline(settings).get_workflow()


# =====================================================
# INSPECT VIDEO URL
# =====================================================

@app.tool()
def inspect_video_url(url: str) -> dict:

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


# =====================================================
# BASIC CLIPS
# =====================================================

@app.tool()
def create_basic_clips(
    url: str,
    clip_count: int = 3
) -> dict:

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
            return {
                "error": "Could not determine video duration."
            }

        segment = duration / clip_count
        results = []

        for index in range(clip_count):

            start = index * segment
            length = min(segment, duration - start)

            output = OUTPUT_DIR / (
                f"{job_id}_clip_{index + 1}.mp4"
            )

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
            "note": "Basic evenly spaced clips."
        }

    except Exception as error:
        return {"error": str(error)[:500]}

    finally:
        if source.exists():
            source.unlink()


# =====================================================
# TRIM VIDEO
# =====================================================

@app.tool()
def trim_video_section(
    video_path: str,
    start_seconds: float,
    end_seconds: float
) -> dict:

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "error": "Video must be inside the server downloads folder."
            }

        if not source.is_file():
            return {"error": "Video file not found."}

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
            "output_file": str(output)
        }

    except Exception as error:
        return {"error": str(error)[:1000]}


# =====================================================
# TRANSCRIBE VIDEO
# =====================================================

@app.tool()
def transcribe_uploaded_video(video_path: str) -> dict:
    """Extract speech and return timestamped transcript."""

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside downloads."
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


# =====================================================
# RENDER CLAUDE CAPTIONS
# =====================================================

@app.tool()
def render_captioned_video(
    video_path: str,
    caption_segments: list
) -> dict:
    """Render Claude-prepared captions onto an uploaded video."""

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside downloads."
            }

        if not source.is_file():
            return {
                "status": "error",
                "message": "Uploaded video not found."
            }

        job_id = uuid.uuid4().hex[:10]

        output = OUTPUT_DIR / (
            f"{job_id}_claude_captioned.mp4"
        )

        result = render_claude_captions(
            str(source),
            str(output),
            caption_segments
        )

        return {
            "status": "success",
            "result": result,
            "output_file": str(output)
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)[:1000]
        }


# =====================================================
# AUTOMATIC CAPTIONING
# =====================================================

@app.tool()
def caption_uploaded_video(video_path: str) -> dict:
    """Generate and burn captions into an uploaded video."""

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "error": "Video must be inside downloads."
            }

        if not source.is_file():
            return {
                "error": "Uploaded video not found."
            }

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


# =====================================================
# VIDEO METADATA
# =====================================================

@app.tool()
def analyze_video_metadata(video_path: str) -> dict:

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside downloads."
            }

        if not source.is_file():
            return {
                "status": "error",
                "message": "Video not found."
            }

        return video_intelligence.get_video_metadata(
            str(source)
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }


# =====================================================
# SCENE DETECTION
# =====================================================

@app.tool()
def detect_video_scenes(
    video_path: str,
    threshold: float = 30.0,
    minimum_gap_seconds: float = 1.0
) -> dict:

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside downloads."
            }

        if not source.is_file():
            return {
                "status": "error",
                "message": "Video not found."
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


# =====================================================
# EXTRACT KEYFRAMES
# =====================================================

@app.tool()
def extract_video_keyframes(
    video_path: str,
    interval_seconds: float = 10.0
) -> dict:

    try:
        source = Path(video_path).resolve()

        if not source.is_relative_to(DOWNLOAD_DIR.resolve()):
            return {
                "status": "error",
                "message": "Video must be inside downloads."
            }

        if not source.is_file():
            return {
                "status": "error",
                "message": "Video not found."
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


# =====================================================
# START SERVER
# =====================================================

if __name__ == "__main__":
    app.run(transport="streamable-http")

    

import os
import uuid
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
import yt_dlp
import imageio_ffmpeg

PORT = int(os.environ.get("PORT", 8000))

app = FastMCP(
    "ClipMate AI",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True
)

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
        "github": "officialtaneeshagrawal-jpg",
        "status": "Running",
        "features": [
            "Video information",
            "Video downloading",
            "Basic clip generation",
            "MP4 export"
        ]
    }


@app.tool()
def inspect_video_url(url: str) -> dict:
    """Inspect an authorized video URL."""
    if urlparse(url).scheme != "https":
        return {"error": "Only HTTPS URLs are accepted."}

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True
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
        return {"error": str(error)[:500]}


@app.tool()
def create_basic_clips(url: str, clip_count: int = 3) -> dict:
    """
    Create basic evenly spaced clips from a video
    that the user owns or is authorized to process.
    """

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
                FFMPEG,
                "-y",
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


if __name__ == "__main__":
    app.run(transport="streamable-http")



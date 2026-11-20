
"""
ClipMate AI - Direct Video Upload and Full-Video Caption Support

Features:
1. Direct HTTP video upload (no Base64 through MCP).
2. Full-video transcription using faster-whisper.
3. Word-level timestamps.
4. Claude-prepared caption rendering.
5. Original video audio preserved.
6. Secure MP4 download links.
"""

import os
import hmac
import json
import time
import uuid
import secrets
import subprocess

from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DOWNLOADS = Path(
    os.environ.get(
        "CLIPMATE_DOWNLOADS",
        "/tmp/clipmate/downloads"
    )
).resolve()

FONT = os.environ.get("CAPTION_FONT", "DejaVu Sans")

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

VIDEO_EXT = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
}

_download_tokens = {}


# ---------------------------------------------------------
# Security
# ---------------------------------------------------------

def _token_ok(given):

    secret = (
        os.environ.get("CLIPMATE_UPLOAD_TOKEN")
        or os.environ.get("CLIPMATE_TOKEN")
        or ""
    )

    return (
        bool(secret)
        and isinstance(given, str)
        and hmac.compare_digest(given, secret)
    )


def _safe_path(name):

    path = Path(name)

    if not path.is_absolute():
        path = DOWNLOADS / path.name

    path = path.resolve()

    if DOWNLOADS not in path.parents:
        raise ValueError(
            "Video must be inside ClipMate downloads."
        )

    if not path.is_file():
        raise FileNotFoundError(
            "Video file not found."
        )

    return path


# ---------------------------------------------------------
# Video information
# ---------------------------------------------------------

def _probe(path):

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    return {
        "width": int(data["streams"][0]["width"]),
        "height": int(data["streams"][0]["height"]),
        "duration": float(data["format"]["duration"]),
    }


# ---------------------------------------------------------
# ASS caption formatting
# ---------------------------------------------------------

def _ass_time(seconds):

    seconds = max(float(seconds), 0.0)

    centiseconds = int(round(seconds * 100))

    return (
        f"{centiseconds // 360000}:"
        f"{centiseconds // 6000 % 60:02d}:"
        f"{centiseconds // 100 % 60:02d}."
        f"{centiseconds % 100:02d}"
    )


def _ass_text(text, emphasis=None):

    emphasized = {
        word.lower().strip(".,!?;:\"'")
        for word in (emphasis or [])
    }

    words = []

    for word in str(text).replace(
        "\r", ""
    ).replace("\n", " \\N ").split(" "):

        if word == "\\N":
            words.append(word)
            continue

        word = word.replace("{", "(").replace("}", ")")

        if word.lower().strip(".,!?;:\"'") in emphasized:

            word = (
                r"{\c&H00D7FF&\b1}"
                + word
                + r"{\r}"
            )

        words.append(word)

    return " ".join(words)


def build_ass(segments, width, height, duration):

    size = (
        int(height * 0.045)
        if height >= width
        else int(width * 0.06)
    )

    margin_v = (
        int(height * 0.18)
        if height > width
        else int(height * 0.08)
    )

    margin_h = int(width * 0.07)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n\n"

        "[V4+ Styles]\n"

        "Format: Name,Fontname,Fontsize,PrimaryColour,"
        "SecondaryColour,OutlineColour,BackColour,Bold,"
        "Italic,Underline,StrikeOut,ScaleX,ScaleY,"
        "Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"

        f"Style: Default,{FONT},{size},"
        "&H00FFFFFF,&H00FFFFFF,"
        "&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,"
        f"{max(3, size // 12)},1,2,"
        f"{margin_h},{margin_h},{margin_v},1\n\n"

        "[Events]\n"

        "Format: Layer,Start,End,Style,Name,"
        "MarginL,MarginR,MarginV,Effect,Text\n"
    )

    lines = []

    for segment in sorted(
        segments,
        key=lambda item: float(item["start"])
    ):

        start = max(
            0.0,
            float(segment["start"])
        )

        end = min(
            duration,
            float(segment["end"])
        )

        text = str(
            segment.get("text", "")
        ).strip()

        if end - start < 0.05 or not text:
            continue

        lines.append(
            f"Dialogue: 0,"
            f"{_ass_time(start)},"
            f"{_ass_time(end)},"
            f"Default,,0,0,0,,"
            f"{_ass_text(text, segment.get('emphasis'))}"
        )

    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------
# Render full captioned video
# ---------------------------------------------------------

def burn_captions(video, segments, output):

    info = _probe(video)

    ass_file = output.with_suffix(".ass")

    ass_file.write_text(
        build_ass(
            segments,
            info["width"],
            info["height"],
            info["duration"],
        ),
        encoding="utf-8",
    )

    ass_path = (
        str(ass_file)
        .replace("\\", "/")
        .replace(":", r"\:")
    )

    command = [
        "ffmpeg",
        "-y",
        "-v", "error",
        "-i", str(video),
        "-vf", f"ass='{ass_path}'",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr[-1000:]
        )

    output_info = _probe(output)

    return {
        "input_duration": info["duration"],
        "output_duration": output_info["duration"],
    }


# ---------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------

_model = None


def _get_model():

    global _model

    if _model is None:

        from faster_whisper import WhisperModel

        _model = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )

    return _model


def transcribe(path):

    segments, info = _get_model().transcribe(
        str(path),
        word_timestamps=True,
        vad_filter=True,
        task="transcribe",
    )

    output = []

    for segment in segments:

        output.append({

            "start": round(segment.start, 2),

            "end": round(segment.end, 2),

            "text": segment.text.strip(),

            "words": [

                {
                    "w": word.word.strip(),
                    "start": round(word.start, 2),
                    "end": round(word.end, 2),
                }

                for word in (segment.words or [])
            ],
        })

    return {

        "status": "ok",

        "language": info.language,

        "language_probability": round(
            info.language_probability, 3
        ),

        "duration": round(info.duration, 2),

        "segments": output,

        "note": (
            "Hindi may be transcribed in Devanagari. "
            "Claude should romanise Hindi into Hinglish."
        ),
    }


# ---------------------------------------------------------
# Browser upload page
# ---------------------------------------------------------

UPLOAD_PAGE = """
<!doctype html>

<html>

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>ClipMate AI Upload</title>

</head>

<body>

<h2>ClipMate AI Video Upload</h2>

<input
id="token"
type="password"
placeholder="Upload token">

<br><br>

<input
id="file"
type="file"
accept="video/mp4,video/*">

<br><br>

<button onclick="uploadFile()">
Upload Video
</button>

<pre id="result"></pre>

<script>

async function uploadFile() {

    const file =
        document.getElementById("file").files[0];

    const token =
        document.getElementById("token").value;

    const result =
        document.getElementById("result");

    if (!file || !token) {

        result.textContent =
            "Select a video and enter the token.";

        return;
    }

    result.textContent = "Uploading...";

    try {

        const response = await fetch(
            "/upload?filename=" +
            encodeURIComponent(file.name),

            {
                method: "POST",

                headers: {
                    "x-upload-token": token
                },

                body: file
            }
        );

        result.textContent =
            await response.text();

    } catch (error) {

        result.textContent = String(error);

    }
}

</script>

</body>

</html>
"""


# ---------------------------------------------------------
# Register HTTP routes and MCP tools
# ---------------------------------------------------------

def register(mcp):

    from starlette.responses import (
        FileResponse,
        HTMLResponse,
        JSONResponse,
    )

    # Upload page

    @mcp.custom_route(
        "/upload-page",
        methods=["GET"]
    )
    async def upload_page(request):

        return HTMLResponse(UPLOAD_PAGE)


    # Direct streaming upload

    @mcp.custom_route(
        "/upload",
        methods=["POST"]
    )
    async def upload(request):

        if not _token_ok(
            request.headers.get("x-upload-token", "")
        ):

            return JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid upload token."
                },
                status_code=401,
            )

        filename = Path(
            request.query_params.get("filename", "")
        ).name

        if Path(filename).suffix.lower() not in VIDEO_EXT:

            return JSONResponse(
                {
                    "status": "error",
                    "message": "Unsupported video format."
                },
                status_code=400,
            )

        DOWNLOADS.mkdir(
            parents=True,
            exist_ok=True
        )

        destination = DOWNLOADS / (
            f"{uuid.uuid4().hex[:10]}_{filename}"
        )

        total_bytes = 0

        try:

            with destination.open("wb") as file:

                async for chunk in request.stream():

                    if not chunk:
                        continue

                    file.write(chunk)

                    total_bytes += len(chunk)

            if total_bytes == 0:

                destination.unlink(missing_ok=True)

                return JSONResponse(
                    {
                        "status": "error",
                        "message": "Empty upload."
                    },
                    status_code=400,
                )

            return JSONResponse({

                "status": "success",

                "filename": destination.name,

                "video_path": str(destination),

                "size_bytes": total_bytes,

            })

        except Exception as error:

            destination.unlink(missing_ok=True)

            return JSONResponse(
                {
                    "status": "error",
                    "message": str(error)[:500]
                },
                status_code=500,
            )


    # Secure download route

    @mcp.custom_route(
        "/files/{name}",
        methods=["GET"]
    )
    async def download_file(request):

        token = request.query_params.get(
            "token", ""
        )

        record = _download_tokens.get(token)

        if (
            not record
            or record["expires"] < time.time()
        ):

            return JSONResponse(
                {
                    "status": "error",
                    "message": "Download link expired or invalid."
                },
                status_code=401,
            )

        try:

            path = _safe_path(
                request.path_params["name"]
            )

            if path != record["path"]:
                raise ValueError("Invalid file.")

        except Exception:

            return JSONResponse(
                {
                    "status": "error",
                    "message": "File not found."
                },
                status_code=404,
            )

        return FileResponse(
            path,
            media_type="video/mp4",
            filename=path.name,
        )


    # Transcription tool

    @mcp.tool()
    def transcribe_uploaded_video(
        video_path: str
    ) -> dict:
        """Transcribe the complete uploaded video."""

        try:

            return transcribe(
                _safe_path(video_path)
            )

        except Exception as error:

            return {
                "status": "error",
                "message": str(error)[:1000],
            }


    # Caption rendering tool

    @mcp.tool()
    def render_captioned_video(
        video_path: str,
        caption_segments: list,
    ) -> dict:
        """
        Burn Claude-prepared captions into the entire video.

        Each caption:
        {
            "start": 0.0,
            "end": 2.0,
            "text": "Caption text",
            "emphasis": []
        }
        """

        try:

            if not isinstance(
                caption_segments, list
            ):

                raise ValueError(
                    "Caption segments must be a list."
                )

            source = _safe_path(video_path)

            output = DOWNLOADS / (
                f"{source.stem}_captioned_"
                f"{uuid.uuid4().hex[:6]}.mp4"
            )

            result = burn_captions(
                source,
                caption_segments,
                output,
            )

            download_token = secrets.token_urlsafe(24)

            _download_tokens[download_token] = {

                "path": output.resolve(),

                "expires": time.time() + 86400,

            }

            base_url = os.environ.get(
                "PUBLIC_BASE_URL", ""
            ).rstrip("/")

            download_url = None

            if base_url:

                download_url = (
                    f"{base_url}/files/{output.name}"
                    f"?token={download_token}"
                )

            return {

                "status": "success",

                "output_path": str(output),

                "download_url": download_url,

                "download_link_expires_in_hours": 24,

                "segments_rendered": len(caption_segments),

                **result,

            }

        except Exception as error:

            return {

                "status": "error",

                "message": str(error)[:1000],

            }

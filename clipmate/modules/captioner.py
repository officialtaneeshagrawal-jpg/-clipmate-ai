
import math
import shutil
import subprocess
import uuid
from pathlib import Path

import imageio_ffmpeg
from faster_whisper import WhisperModel


def get_ffmpeg():
    return shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


def format_time(seconds):
    milliseconds = round(seconds * 1000)

    hours = milliseconds // 3600000
    minutes = (milliseconds % 3600000) // 60000
    seconds_part = (milliseconds % 60000) // 1000
    millis = milliseconds % 1000

    return (
        f"{hours:02}:{minutes:02}:"
        f"{seconds_part:02},{millis:03}"
    )


def extract_audio(source, audio, ffmpeg):
    subprocess.run(
        [
            ffmpeg, "-y",
            "-i", str(source),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(audio)
        ],
        check=True,
        capture_output=True,
        timeout=600
    )


def transcribe_video(video_path):
    """
    Extract speech and return detected language
    with timestamped transcript segments for Claude.
    """

    source = Path(video_path).resolve()

    if not source.is_file():
        raise FileNotFoundError("Input video not found.")

    job_id = uuid.uuid4().hex[:10]
    audio = source.parent / f"{job_id}_audio.wav"

    ffmpeg = get_ffmpeg()

    try:
        extract_audio(source, audio, ffmpeg)

        model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

        segments, info = model.transcribe(
            str(audio),
            beam_size=5,
            vad_filter=True
        )

        transcript = []

        for segment in segments:
            transcript.append({
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip()
            })

        if not transcript:
            raise RuntimeError("No speech was detected.")

        return {
            "status": "success",
            "detected_language": info.language,
            "language_probability": round(
                info.language_probability, 4
            ),
            "segments": transcript
        }

    finally:
        audio.unlink(missing_ok=True)


def add_captions(video_path, output_path):
    """
    Original automatic Whisper captioning function.
    """

    source = Path(video_path).resolve()
    output = Path(output_path).resolve()

    if not source.is_file():
        raise FileNotFoundError("Input video not found.")

    if source == output:
        raise ValueError("Input and output must be different.")

    output.parent.mkdir(parents=True, exist_ok=True)

    job_id = uuid.uuid4().hex[:10]
    audio = output.parent / f"{job_id}_audio.wav"
    subtitles = output.parent / f"{job_id}.srt"

    ffmpeg = get_ffmpeg()

    try:
        extract_audio(source, audio, ffmpeg)

        model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

        segments, info = model.transcribe(
            str(audio),
            beam_size=5,
            vad_filter=True
        )

        count = 0

        with open(subtitles, "w", encoding="utf-8") as file:
            for count, segment in enumerate(segments, start=1):
                file.write(f"{count}\n")
                file.write(
                    f"{format_time(segment.start)} --> "
                    f"{format_time(segment.end)}\n"
                )
                file.write(f"{segment.text.strip()}\n\n")

        if count == 0:
            raise RuntimeError("No speech was detected.")

        render_subtitles(source, output, subtitles, ffmpeg)

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Captioned video was not created.")

        return {
            "status": "success",
            "output": str(output),
            "subtitle_file": str(subtitles),
            "language": info.language,
            "captions": count
        }

    finally:
        audio.unlink(missing_ok=True)
        subtitles.unlink(missing_ok=True)


def render_claude_captions(video_path, output_path, caption_segments):
    """
    Render timestamped captions supplied by Claude onto a video.
    """

    source = Path(video_path).resolve()
    output = Path(output_path).resolve()

    if not source.is_file():
        raise FileNotFoundError("Input video not found.")

    if source == output:
        raise ValueError("Input and output must be different.")

    if not isinstance(caption_segments, list) or not caption_segments:
        raise ValueError("No caption segments provided.")

    output.parent.mkdir(parents=True, exist_ok=True)

    job_id = uuid.uuid4().hex[:10]
    subtitles = output.parent / f"{job_id}.srt"

    ffmpeg = get_ffmpeg()

    try:
        with open(subtitles, "w", encoding="utf-8") as file:
            for index, segment in enumerate(caption_segments, start=1):

                start = float(segment["start"])
                end = float(segment["end"])
                text = str(segment["text"]).strip()

                if (
                    not math.isfinite(start)
                    or not math.isfinite(end)
                    or start < 0
                    or end <= start
                    or not text
                ):
                    raise ValueError("Invalid caption segment.")

                text = " ".join(text.split())
                text = text.replace("-->", "→")

                file.write(f"{index}\n")
                file.write(
                    f"{format_time(start)} --> {format_time(end)}\n"
                )
                file.write(f"{text}\n\n")

        render_subtitles(source, output, subtitles, ffmpeg)

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Captioned video was not created.")

        return {
            "status": "success",
            "output": str(output),
            "captions": len(caption_segments)
        }

    finally:
        subtitles.unlink(missing_ok=True)


def render_subtitles(source, output, subtitles, ffmpeg):
    """
    Burn an SRT subtitle file into a video using FFmpeg.
    """

    subtitle_path = str(subtitles).replace("\\", "/")
    subtitle_path = subtitle_path.replace(":", r"\:")
    subtitle_path = subtitle_path.replace("'", r"\'")

    command = [
        ffmpeg, "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf",
        (
            f"subtitles=filename='{subtitle_path}':"
            "force_style='FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=2,"
            "Alignment=2,MarginV=60'"
        ),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output)
    ]

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        timeout=3600
    )


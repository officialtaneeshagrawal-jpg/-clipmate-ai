
import subprocess
import os

def export_clip(video_path, start, end, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    duration = end - start

    if duration <= 0:
        raise ValueError("Invalid clip duration")

    command = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path
    ]

    subprocess.run(command, check=True)

    return output_path

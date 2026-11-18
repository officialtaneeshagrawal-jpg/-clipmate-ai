
import subprocess
import os

def make_vertical_video(
    input_path,
    output_path,
    width=1080,
    height=1920
):
    if not os.path.exists(input_path):
        raise FileNotFoundError("Input video not found")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]

    subprocess.run(command, check=True)

    return output_path


from faster_whisper import WhisperModel
import os

def generate_captions(video_path, output_path="output/captions.srt"):
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    segments, info = model.transcribe(
        video_path,
        beam_size=5
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        for index, segment in enumerate(segments, start=1):
            start = format_time(segment.start)
            end = format_time(segment.end)

            file.write(f"{index}\n")
            file.write(f"{start} --> {end}\n")
            file.write(f"{segment.text.strip()}\n\n")

    return output_path


def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)

    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:02},{milliseconds:03}"
    )


from src.video_info import get_video_info
from src.clip_detector import detect_highlights
from src.clip_exporter import export_clip
from src.video_editor import make_vertical_video
from src.caption_generator import generate_captions

def process_video(video_path):
    print("ClipMate AI starting...")

    info = get_video_info(video_path)
    print("Video information:", info)

    clips = detect_highlights(info, clip_count=5)
    print("Selected clips:", clips)

    for index, clip in enumerate(clips, start=1):
        output = f"output/clip_{index}.mp4"
        export_clip(
            video_path,
            clip["start"],
            clip["end"],
            output
        )

        print("Exported:", output)

    print("ClipMate AI processing complete!")

if __name__ == "__main__":
    video_path = input("Enter video file path: ")
    process_video(video_path)


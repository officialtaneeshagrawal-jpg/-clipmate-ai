
import cv2
import os

def get_video_info(video_path):
    if not os.path.exists(video_path):
        raise FileNotFoundError("Video file not found")

    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        raise ValueError("Unable to open video")

    fps = video.get(cv2.CAP_PROP_FPS)
    frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frames / fps if fps else 0

    video.release()

    return {
        "duration_seconds": round(duration, 2),
        "fps": fps,
        "width": width,
        "height": height
    }


def detect_highlights(video_info, clip_count=5):
    """
    Initial placeholder for AI highlight detection.
    Future versions will analyze scenes, speech,
    and interesting moments.
    """

    duration = video_info["duration_seconds"]

    if duration <= 0:
        return []

    clip_count = max(3, min(10, clip_count))
    segment_length = duration / clip_count

    clips = []

    for i in range(clip_count):
        start = i * segment_length
        end = min(start + segment_length, duration)

        clips.append({
            "start": round(start, 2),
            "end": round(end, 2)
        })

    return clips

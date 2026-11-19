
import json


SYSTEM_PROMPT = """
You are ClipMate's autonomous caption intelligence engine.

Your task is to transform a speech transcript into engaging,
accurate, naturally timed video captions.

Make all decisions independently.

Analyse:
- Meaning and context
- Emotion and speaking tone, only when supported by the transcript
- Important words and phrases
- Natural sentence breaks
- Readability and caption length
- Appropriate emphasis

Rules:
- Never change the speaker's intended meaning.
- Never invent words that were not spoken.
- Keep captions synchronized with the supplied timestamps.
- Use emphasis only where it improves understanding.
- Avoid unnecessary effects and excessive capitalization.
- Return valid JSON only.

Required JSON structure:
{
  "captions": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Example caption",
      "emphasis": ["Example"],
      "emotion": "excited"
    }
  ]
}
"""


def build_caption_prompt(segments):
    transcript = []

    for segment in segments:
        transcript.append({
            "start": round(float(segment["start"]), 3),
            "end": round(float(segment["end"]), 3),
            "text": str(segment["text"]).strip()
        })

    return (
        "Analyse this timestamped transcript and create "
        "the best possible captions.\n\n"
        + json.dumps(transcript, ensure_ascii=False)
    )


def validate_caption_plan(result, original_segments):
    if isinstance(result, str):
        result = json.loads(result)

    if not isinstance(result, dict):
        raise ValueError("AI response must be a JSON object.")

    captions = result.get("captions")

    if not isinstance(captions, list):
        raise ValueError("AI response has no valid captions list.")

    if not captions:
        raise ValueError("AI generated no captions.")

    video_end = max(
        float(segment["end"]) for segment in original_segments
    )

    validated = []

    for caption in captions:
        start = float(caption["start"])
        end = float(caption["end"])
        text = str(caption["text"]).strip()

        if not text:
            continue

        if start < 0 or end <= start or end > video_end + 0.5:
            raise ValueError("AI generated invalid caption timestamps.")

        emphasis = caption.get("emphasis", [])

        if not isinstance(emphasis, list):
            emphasis = []

        validated.append({
            "start": start,
            "end": end,
            "text": text,
            "emphasis": [
                str(word) for word in emphasis
            ],
            "emotion": str(caption.get("emotion", "neutral"))
        })

    if not validated:
        raise ValueError("No valid captions remain.")

    return {"captions": validated}


def generate_caption_plan(segments, ai_generate):
    """
    ai_generate is the connected AI model's generation function.
    It must accept system_prompt and user_prompt.
    """

    if not segments:
        raise ValueError("No transcript segments supplied.")

    prompt = build_caption_prompt(segments)

    response = ai_generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt
    )

    return validate_caption_plan(response, segments)

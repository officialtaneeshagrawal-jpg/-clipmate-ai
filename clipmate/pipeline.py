"""
ClipMate AI - Central Pipeline

Coordinates all specialist processing modules.
"""

from dataclasses import dataclass


@dataclass
class PipelineSettings:
    detect_highlights: bool = True
    trim_scenes: bool = True
    generate_captions: bool = True
    convert_to_reel: bool = True
    smart_reframing: bool = True
    enhance_audio: bool = True


class ClipMatePipeline:

    def __init__(self, settings=None):
        self.settings = settings or PipelineSettings()

    def get_workflow(self):
        workflow = []

        modules = {
            "highlight_detection": self.settings.detect_highlights,
            "scene_trimming": self.settings.trim_scenes,
            "caption_generation": self.settings.generate_captions,
            "reel_conversion": self.settings.convert_to_reel,
            "smart_reframing": self.settings.smart_reframing,
            "audio_enhancement": self.settings.enhance_audio,
        }

        for module, enabled in modules.items():
            if enabled:
                workflow.append(module)

        workflow.append("final_clip_generation")

        return {
            "project": "ClipMate AI",
            "workflow": workflow,
            "creator": "Taneesh Agrawal",
            "status": "Workflow configured; processing engines pending"
        }
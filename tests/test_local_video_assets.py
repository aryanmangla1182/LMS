import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.domain.models import VideoScenePlan
from lms_engine.integrations.local_video_assets import build_scene_svg, write_concat_file


class LocalVideoAssetsTestCase(unittest.TestCase):
    def test_build_scene_svg_includes_training_copy_and_visual_cues(self) -> None:
        scene = VideoScenePlan(
            scene_number=2,
            title="Customer-facing example",
            duration_seconds=12,
            narration=(
                "Conversion for Area Store Manager. Scene 2: Customer-facing example. "
                "Show how a manager can coach the team to invite the shopper into the next step."
            ),
            visual_direction="Retail floor visuals, coach-led explanation, bold lower-third cues.",
            sora_prompt="unused",
        )

        markup = build_scene_svg(scene, "Area Store Manager", "CONVERSION", 1)

        self.assertIn("<svg", markup)
        self.assertIn("Customer-facing example", markup)
        self.assertIn("Area Store Manager", markup)
        self.assertIn("CONVERSION", markup)
        self.assertIn("subtitle", markup)
        self.assertIn("icon badge", markup)

    def test_write_concat_file_uses_absolute_scene_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            scene_paths = [
                output_dir / "scene_01.mp4",
                output_dir / "scene_02.mp4",
            ]
            for path in scene_paths:
                path.write_bytes(b"mock")

            concat_path = output_dir / "scenes.txt"
            write_concat_file(scene_paths, concat_path)

            lines = concat_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(
            lines,
            [
                "file '{0}'".format(scene_paths[0].resolve()),
                "file '{0}'".format(scene_paths[1].resolve()),
            ],
        )


if __name__ == "__main__":
    unittest.main()

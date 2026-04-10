import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.domain.models import VideoScenePlan
from lms_engine.integrations.local_video_assets import (
    build_scene_svg,
    export_final_audio_track,
    render_openai_voiceover,
    render_voice_track,
    render_elevenlabs_voiceover,
    write_concat_file,
)


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

    def test_render_elevenlabs_voiceover_writes_response_bytes(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b"mock-mp3-audio"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voiceover.mp3"
            with patch(
                "lms_engine.integrations.local_video_assets.request.urlopen",
                return_value=FakeResponse(),
            ) as mocked_urlopen:
                render_elevenlabs_voiceover(
                    text="Coach the team through a better floor conversion example.",
                    output_path=output_path,
                    api_key="test-key",
                    voice_id="voice-123",
                    model_id="eleven_multilingual_v2",
                )

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"mock-mp3-audio")
            req = mocked_urlopen.call_args.args[0]
            self.assertEqual(req.full_url, "https://api.elevenlabs.io/v1/text-to-speech/voice-123")
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.headers["Xi-api-key"], "test-key")
            self.assertEqual(req.headers["Accept"], "audio/mpeg")
            self.assertIn(b'"text": "Coach the team through a better floor conversion example."', req.data)
            self.assertIn(b'"model_id": "eleven_multilingual_v2"', req.data)

    def test_render_openai_voiceover_writes_response_bytes(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b"mock-openai-mp3-audio"

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voiceover.mp3"
            with patch(
                "lms_engine.integrations.local_video_assets.request.urlopen",
                return_value=FakeResponse(),
            ) as mocked_urlopen:
                render_openai_voiceover(
                    text="Coach the team through a better floor conversion example.",
                    output_path=output_path,
                    api_key="test-openai-key",
                    model="gpt-4o-mini-tts",
                    voice="marin",
                    base_url="https://api.openai.com/v1",
                )

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"mock-openai-mp3-audio")
            req = mocked_urlopen.call_args.args[0]
            self.assertEqual(req.full_url, "https://api.openai.com/v1/audio/speech")
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.headers["Authorization"], "Bearer test-openai-key")
            self.assertEqual(req.headers["Content-type"], "application/json")
            self.assertIn(b'"model": "gpt-4o-mini-tts"', req.data)
            self.assertIn(b'"voice": "marin"', req.data)
            self.assertIn(b'"response_format": "mp3"', req.data)
    def test_render_voice_track_requires_elevenlabs_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voiceover.mp3"
            with self.assertRaisesRegex(ValueError, "ElevenLabs voice is selected but ELEVENLABS_API_KEY is missing"):
                render_voice_track(
                    text="Coach the team through a better floor conversion example.",
                    output_path=output_path,
                    voice_provider="elevenlabs",
                    elevenlabs_api_key="",
                    elevenlabs_voice_id="siw1N9V8LmYeEWKyWBxv",
                )

    def test_render_voice_track_requires_openai_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voiceover.mp3"
            with self.assertRaisesRegex(ValueError, "OpenAI voice is selected but OPENAI_API_KEY is missing"):
                render_voice_track(
                    text="Coach the team through a better floor conversion example.",
                    output_path=output_path,
                    voice_provider="openai",
                    openai_api_key="",
                    openai_tts_model="gpt-4o-mini-tts",
                    openai_tts_voice="marin",
                )

    def test_export_final_audio_track_builds_debug_audio_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            final_video_path = output_dir / "final_video.mp4"
            final_video_path.write_bytes(b"video")

            with patch("lms_engine.integrations.local_video_assets.run_command") as mocked_run_command:
                audio_path = export_final_audio_track(final_video_path, output_dir)

        self.assertEqual(audio_path, output_dir / "final_voiceover.m4a")
        mocked_run_command.assert_called_once_with(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(final_video_path),
                "-vn",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_dir / "final_voiceover.m4a"),
            ]
        )


if __name__ == "__main__":
    unittest.main()

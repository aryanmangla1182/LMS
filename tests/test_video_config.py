import os
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.integrations.video import (
    DemoVideoGateway,
    LocalStoryboardVideoGateway,
    OpenAISoraVideoGateway,
    build_video_gateway,
)


class VideoConfigTestCase(unittest.TestCase):
    def test_build_video_gateway_reads_local_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = os.path.join(temp_dir, ".env.local")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("LMS_VIDEO_PROVIDER=openai\n")
                handle.write("OPENAI_API_KEY=test-key\n")
                handle.write("OPENAI_VIDEO_MODEL=test-model\n")

            gateway = build_video_gateway(env={}, env_path=env_path)

        self.assertIsInstance(gateway, OpenAISoraVideoGateway)
        self.assertEqual(gateway.api_key, "test-key")
        self.assertEqual(gateway.model, "test-model")

    def test_build_video_gateway_uses_demo_mode_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = os.path.join(temp_dir, ".env.local")
            gateway = build_video_gateway(env={}, env_path=env_path)
        self.assertIsInstance(gateway, LocalStoryboardVideoGateway)

    def test_build_video_gateway_can_force_demo_mode(self) -> None:
        gateway = build_video_gateway(env={"LMS_VIDEO_PROVIDER": "demo"}, env_path="/tmp/missing.env")
        self.assertIsInstance(gateway, DemoVideoGateway)

    def test_build_video_gateway_reads_local_elevenlabs_voice_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = os.path.join(temp_dir, ".env.local")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("LMS_VIDEO_PROVIDER=local\n")
                handle.write("LMS_VOICE_PROVIDER=elevenlabs\n")
                handle.write("ELEVENLABS_API_KEY=test-eleven-key\n")
                handle.write("ELEVENLABS_VOICE_ID=test-voice-id\n")
                handle.write("ELEVENLABS_MODEL_ID=eleven_multilingual_v2\n")
                handle.write("LOCAL_VOICE_NAME=Allison\n")

            gateway = build_video_gateway(env={}, env_path=env_path)

        self.assertIsInstance(gateway, LocalStoryboardVideoGateway)
        self.assertEqual(gateway.voice_provider, "elevenlabs")
        self.assertEqual(gateway.elevenlabs_api_key, "test-eleven-key")
        self.assertEqual(gateway.elevenlabs_voice_id, "ack0QsRaQyDLnVyMQTSd")
        self.assertEqual(gateway.elevenlabs_model_id, "eleven_multilingual_v2")
        self.assertEqual(gateway.local_voice_name, "Allison")


if __name__ == "__main__":
    unittest.main()

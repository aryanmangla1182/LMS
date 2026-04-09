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


if __name__ == "__main__":
    unittest.main()

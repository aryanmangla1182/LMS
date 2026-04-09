import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.api.http import route_request
from lms_engine.bootstrap import build_container


class KPIStudioTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_provider = os.environ.get("LMS_VIDEO_PROVIDER")
        self.previous_render_mode = os.environ.get("LMS_VIDEO_RENDER_MODE")
        os.environ["LMS_VIDEO_PROVIDER"] = "local"
        os.environ["LMS_VIDEO_RENDER_MODE"] = "mock"
        self.container = build_container()
        self.item = self.container.kpi_studio.list_items()[0]
        self.role_name = "Area Store Manager"

    def tearDown(self) -> None:
        if self.previous_provider is None:
            os.environ.pop("LMS_VIDEO_PROVIDER", None)
        else:
            os.environ["LMS_VIDEO_PROVIDER"] = self.previous_provider

        if self.previous_render_mode is None:
            os.environ.pop("LMS_VIDEO_RENDER_MODE", None)
        else:
            os.environ["LMS_VIDEO_RENDER_MODE"] = self.previous_render_mode

    def test_kpi_studio_keeps_only_latest_three_versions(self) -> None:
        version_one = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})
        version_two = self.container.kpi_studio.generate_video_version(
            self.item.id,
            {"role_name": self.role_name, "revision_prompt": "Revise pace"},
        )
        version_three = self.container.kpi_studio.generate_video_version(
            self.item.id,
            {"role_name": self.role_name, "revision_prompt": "Add more examples"},
        )
        version_four = self.container.kpi_studio.generate_video_version(
            self.item.id,
            {"role_name": self.role_name, "revision_prompt": "Use store-floor language"},
        )

        item = self.container.kpi_studio.get_item(self.item.id)
        self.assertEqual(item.role_name, self.role_name)
        self.assertEqual([version.version_number for version in item.video_versions], [2, 3, 4])
        self.assertNotIn(version_one.id, [version.id for version in item.video_versions])
        self.assertEqual(version_two.id, item.video_versions[0].id)
        self.assertEqual(version_four.id, item.video_versions[-1].id)

    def test_completed_video_auto_generates_quiz(self) -> None:
        version = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})

        item = self.container.kpi_studio.get_item(self.item.id)
        self.assertEqual(item.final_version_id, version.id)
        self.assertIsNotNone(item.quiz)
        self.assertEqual(len(item.quiz.questions), 10)
        self.assertFalse(item.published)

    def test_reopen_requires_new_finalization_cycle(self) -> None:
        version = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})
        self.container.kpi_studio.approve_version(self.item.id, version.id)

        reopened = self.container.kpi_studio.reopen_item(self.item.id)
        self.assertIsNone(reopened.final_version_id)
        self.assertIsNone(reopened.quiz)
        self.assertFalse(reopened.published)

    def test_http_kpi_studio_endpoints_expose_versions_and_quiz(self) -> None:
        version_response = route_request(
            self.container,
            "POST",
            "/studio/kpis/{0}/versions".format(self.item.id),
            {},
            {"role_name": self.role_name, "revision_prompt": "Make it more actionable"},
        )
        version_id = version_response["item"]["id"]
        item_response = route_request(self.container, "GET", "/studio/kpis/{0}".format(self.item.id), {}, None)

        self.assertEqual(item_response["item"]["final_version_id"], version_id)
        self.assertEqual(len(item_response["item"]["video_versions"]), 1)
        self.assertEqual(len(item_response["item"]["quiz"]["questions"]), 10)
        self.assertFalse(item_response["item"]["published"])

    def test_list_items_backfills_quiz_for_existing_completed_video(self) -> None:
        version = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})
        item = self.container.kpi_studio.get_item(self.item.id)
        item.quiz = None
        item.final_version_id = None

        refreshed = self.container.kpi_studio.list_items()[0]
        self.assertEqual(refreshed.final_version_id, version.id)
        self.assertIsNotNone(refreshed.quiz)
        self.assertEqual(refreshed.quiz.video_version_id, version.id)

    def test_role_name_is_required_for_first_video_generation(self) -> None:
        with self.assertRaisesRegex(ValueError, "role_name is required"):
            self.container.kpi_studio.generate_video_version(self.item.id, {})

    def test_kpi_studio_seed_ids_are_stable(self) -> None:
        another_container = build_container()
        current_ids = {item.kpi_name: item.id for item in self.container.kpi_studio.list_items()}
        other_ids = {item.kpi_name: item.id for item in another_container.kpi_studio.list_items()}
        self.assertEqual(current_ids, other_ids)

    def test_local_generation_creates_preview_asset_path(self) -> None:
        version = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})
        self.assertEqual(version.generation_job.provider, "local_storyboard")
        self.assertTrue(version.video_url)
        self.assertTrue(any(scene.clip_url for scene in version.scene_plan))

    def test_scene_narration_stays_brief_enough_for_target_runtime(self) -> None:
        version = self.container.kpi_studio.generate_video_version(self.item.id, {"role_name": self.role_name})
        longest_scene_words = max(len(scene.narration.split()) for scene in version.scene_plan)
        self.assertLessEqual(longest_scene_words, 28)

    def test_known_skill_uses_saved_training_guide_for_script_and_scenes(self) -> None:
        skill_item = next(
            item for item in self.container.kpi_studio.list_items()
            if item.kpi_name == "Adaptability & Problem Solving"
        )

        version = self.container.kpi_studio.generate_video_version(skill_item.id, {"role_name": self.role_name})
        refreshed = self.container.kpi_studio.get_item(skill_item.id)

        self.assertIn("Things do not always go as planned in a store", refreshed.script_draft)
        self.assertIn("not available", refreshed.script_draft)
        self.assertTrue(any("offer a solution" in scene.narration.lower() for scene in version.scene_plan))

    def test_known_kpi_quiz_uses_saved_training_guide_content(self) -> None:
        kpi_item = next(
            item for item in self.container.kpi_studio.list_items()
            if item.kpi_name == "UNIT PER TRANSACTION"
        )

        self.container.kpi_studio.generate_video_version(kpi_item.id, {"role_name": self.role_name})
        refreshed = self.container.kpi_studio.get_item(kpi_item.id)

        self.assertIsNotNone(refreshed.quiz)
        prompt_text = " ".join(question.prompt for question in refreshed.quiz.questions)
        explanation_text = " ".join(question.explanation for question in refreshed.quiz.questions)
        self.assertIn("UPT", prompt_text)
        self.assertIn("add-on", explanation_text.lower())
        option_text = " ".join(
            option
            for question in refreshed.quiz.questions
            for option in question.options
        )
        self.assertIn("Suggest jeans or accessories", option_text)
        self.assertIn("Bill only the T-shirt", option_text)


if __name__ == "__main__":
    unittest.main()

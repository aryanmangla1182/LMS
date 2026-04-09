import os
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.ai import AIContentGenerator
from lms_engine.application.mvp import AuthorizationError, LMSEngineService
from lms_engine.storage import AssetStore, JsonStore


class FakeSpeechClient:
    enabled = True

    def transcribe_audio(self, audio_bytes, filename, mime_type, language_code="en"):
        return {
            "text": audio_bytes.decode("utf-8"),
            "model_id": "fake_speech",
            "source": "test",
            "raw": {"filename": filename, "mime_type": mime_type, "language_code": language_code},
        }


class LMSEngineMVPTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        store_path = os.path.join(self.temp_dir.name, "state.json")
        asset_path = os.path.join(self.temp_dir.name, "assets")
        self.service = LMSEngineService(
            store=JsonStore(store_path),
            asset_store=AssetStore(asset_path),
            generator=AIContentGenerator(),
            speech_client=FakeSpeechClient(),
        )
        trainer_code = self.service.request_login_code({"phone_number": self.service.default_trainer_phone})["code"]
        trainer_login = self.service.verify_login_code(
            {"phone_number": self.service.default_trainer_phone, "code": trainer_code}
        )
        self.trainer_token = trainer_login["token"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_trainer_can_generate_publish_role_and_create_phone_user(self) -> None:
        self.service.require_trainer(self.trainer_token)

        role = self.service.generate_role_blueprint(
            {
                "segment": "Retail",
                "title": "Store Manager",
                "level": "L3",
                "legacy_mappings": ["Store Lead"],
                "work_summary": "Owns store performance and team growth.",
                "responsibilities": [
                    "Run compliant daily operations",
                    "Coach the team on service and conversion",
                    "Prepare strong staff for the next level",
                ],
            }
        )
        self.assertEqual(role["status"], "draft")
        reviewed = self.service.apply_role_review(role["id"], {"review_note": "Strengthen compliance emphasis."})
        self.assertEqual(len(reviewed["review_notes"]), 1)
        published = self.service.publish_role(role["id"])
        self.assertEqual(published["status"], "published")

        created = self.service.create_user(
            {
                "name": "Asha",
                "phone_number": "9000000011",
                "role_id": role["id"],
                "org_unit": "Retail South",
            }
        )
        self.assertEqual(created["user"]["user_type"], "learner")
        self.assertEqual(created["learner"]["phone_number"], "9000000011")

    def test_review_preserves_trainer_defined_skills_and_kpis(self) -> None:
        role = self.service.generate_role_blueprint(
            {
                "segment": "Retail",
                "title": "Store Manager",
                "level": "L3",
                "legacy_mappings": ["Store Lead"],
                "work_summary": "Owns store performance and team growth.",
                "responsibilities": ["Manage the store end to end"],
                "skills": [
                    "Adaptability & Problem Solving",
                    "Communication & Empathy",
                    "Customer Focus & Service Excellence",
                    "Initiative & Drive for Results",
                    "Leadership & People Development",
                    "Teamwork & Collaboration",
                ],
                "kpis": [
                    {
                        "name": "UPT",
                        "description": "UNIT PER TRANSACTION",
                        "target_value": 3,
                        "unit": "count",
                        "weak_threshold": 0.85,
                    },
                    {
                        "name": "ATV",
                        "description": "AVERAGE TRANSACTION VALUE",
                        "target_value": 2500,
                        "unit": "INR",
                        "weak_threshold": 0.9,
                    },
                    {
                        "name": "ASP",
                        "description": "AVERAGE SELLING PRICE",
                        "target_value": 1200,
                        "unit": "INR",
                        "weak_threshold": 0.9,
                    },
                    {
                        "name": "Conv",
                        "description": "CONVERSION",
                        "target_value": 30,
                        "unit": "%",
                        "weak_threshold": 0.85,
                    },
                ],
            }
        )

        reviewed = self.service.apply_role_review(role["id"], {"review_note": "Add more floor coaching emphasis."})

        self.assertEqual(
            [item["name"] for item in reviewed["skills"]],
            [
                "Adaptability & Problem Solving",
                "Communication & Empathy",
                "Customer Focus & Service Excellence",
                "Initiative & Drive for Results",
                "Leadership & People Development",
                "Teamwork & Collaboration",
            ],
        )
        self.assertEqual([item["name"] for item in reviewed["kpis"]], ["UPT", "ATV", "ASP", "Conv"])
        self.assertGreaterEqual(len(reviewed["course_template"]["assessment"]["questions"]), 8)
        total_lessons = sum(len(section["lessons"]) for section in reviewed["course_template"]["sections"])
        self.assertGreaterEqual(total_lessons, 9)
        video_lessons = [
            lesson
            for section in reviewed["course_template"]["sections"]
            for lesson in section["lessons"]
            if lesson["resource_type"] == "video"
        ]
        self.assertGreaterEqual(len(video_lessons), 6)
        self.assertTrue(all("content_asset" in lesson for section in reviewed["course_template"]["sections"] for lesson in section["lessons"]))
        self.assertIn("content_asset", reviewed["course_template"]["assessment"])

    def test_phone_login_and_role_scoped_learner_flow(self) -> None:
        role = self.service.generate_role_blueprint(
            {
                "segment": "Gym",
                "title": "Area Manager",
                "level": "L4",
                "legacy_mappings": ["Cluster Manager"],
                "work_summary": "Owns multi-club performance.",
                "responsibilities": [
                    "Review club performance weekly",
                    "Coach gym managers on weak KPIs",
                    "Maintain compliance standards",
                ],
            }
        )
        self.service.publish_role(role["id"])
        created = self.service.create_user(
            {
                "name": "Riya Sharma",
                "phone_number": "9000000022",
                "role_id": role["id"],
                "org_unit": "City East",
            }
        )
        learner_id = created["learner"]["id"]

        code = self.service.request_login_code({"phone_number": "9000000022"})["code"]
        learner_login = self.service.verify_login_code({"phone_number": "9000000022", "code": code})
        learner_token = learner_login["token"]
        current_user = self.service.get_current_user(learner_token)
        self.assertEqual(current_user["user_type"], "learner")
        self.assertEqual(current_user["learner_id"], learner_id)

        dashboard = self.service.get_my_dashboard(learner_token)
        self.assertEqual(dashboard["learner"]["id"], learner_id)
        lesson = dashboard["enrollment"]["course"]["sections"][0]["lessons"][0]
        self.service.complete_my_lesson(learner_token, lesson["id"])

        dashboard = self.service.get_my_dashboard(learner_token)
        self.assertEqual(dashboard["metrics"]["lessons_completed"], 1)

        assignment = next(
            lesson
            for section in dashboard["enrollment"]["course"]["sections"]
            for lesson in section["lessons"]
            if lesson["resource_type"] == "assignment"
        )
        submission = self.service.submit_my_assignment(
            learner_token,
            assignment["id"],
            {
                "responses": [
                    {"prompt_id": prompt["id"], "response_text": "Completed action note"}
                    for prompt in assignment["assignment_prompts"]
                ]
            },
        )
        self.assertEqual(submission["lesson_id"], assignment["id"])

        questions = dashboard["enrollment"]["course"]["assessment"]["questions"]
        answers = [
            {
                "question_id": question["id"],
                "selected_option_index": question["correct_option_index"],
            }
            for question in questions
        ]
        attempt = self.service.submit_my_assessment(learner_token, {"answers": answers})
        self.assertTrue(attempt["passed"])

        weak_result = self.service.record_my_kpi(
            learner_token,
            {
                "kpi_id": dashboard["role"]["kpis"][0]["id"],
                "value": 40,
                "target_value": dashboard["role"]["kpis"][0]["target_value"],
                "period_label": "May 2026",
            },
        )
        self.assertEqual(weak_result["observation"]["status"], "weak")
        self.assertTrue(weak_result["assignments"])

        self.service.record_my_kpi(
            learner_token,
            {
                "kpi_id": dashboard["role"]["kpis"][0]["id"],
                "value": dashboard["role"]["kpis"][0]["target_value"],
                "target_value": dashboard["role"]["kpis"][0]["target_value"],
                "period_label": "June 2026",
            },
        )
        updated_dashboard = self.service.get_my_dashboard(learner_token)
        self.assertEqual(updated_dashboard["metrics"]["weak_kpis"], 0)
        self.assertEqual(updated_dashboard["remediation_assignments"][0]["status"], "resolved")

    def test_trainer_and_learner_permissions_are_separated(self) -> None:
        role = self.service.generate_role_blueprint(
            {
                "segment": "Retail",
                "title": "Store Manager",
                "level": "L3",
                "legacy_mappings": ["Store Lead"],
                "work_summary": "Owns store performance.",
                "responsibilities": [
                    "Run compliant daily operations",
                    "Coach the team",
                    "Review KPI weak areas",
                ],
            }
        )
        self.service.publish_role(role["id"])
        created = self.service.create_user(
            {
                "name": "Dev",
                "phone_number": "9000000033",
                "role_id": role["id"],
                "org_unit": "Retail West",
            }
        )
        code = self.service.request_login_code({"phone_number": "9000000033"})["code"]
        learner_login = self.service.verify_login_code({"phone_number": "9000000033", "code": code})
        learner_token = learner_login["token"]

        with self.assertRaises(AuthorizationError):
            self.service.require_trainer(learner_token)

        trainer = self.service.get_current_user(self.trainer_token)
        self.assertEqual(trainer["user_type"], "trainer")
        self.assertEqual(created["user"]["user_type"], "learner")

    def test_learner_pitch_analysis_is_persisted_and_visible_in_dashboards(self) -> None:
        role = self.service.generate_role_blueprint(
            {
                "segment": "Retail",
                "title": "Store Manager",
                "level": "",
                "legacy_mappings": [],
                "work_summary": "Owns store performance.",
                "responsibilities": [
                    "Serve customers confidently",
                    "Understand needs before recommending a plan",
                    "Close with a clear next step",
                ],
            }
        )
        self.service.publish_role(role["id"])
        created = self.service.create_user(
            {
                "name": "Asha",
                "phone_number": "9000000044",
                "role_id": role["id"],
            }
        )
        code = self.service.request_login_code({"phone_number": "9000000044"})["code"]
        learner_token = self.service.verify_login_code({"phone_number": "9000000044", "code": code})["token"]

        session = self.service.analyze_my_pitch(
            learner_token,
            {
                "title": "Store walk-in pitch",
                "base64_data": "SGVsbG8sIHdlbGNvbWUgdG8gQ3VsdGZpdC4gSSB3YW50IHRvIHVuZGVyc3RhbmQgeW91ciBnb2FsLCByZWNvbW1lbmQgdGhlIHJpZ2h0IHBsYW4sIGFuZCBoZWxwIHlvdSBqb2luIHRvZGF5Lg==",
                "extension": "txt",
                "mime_type": "text/plain",
            },
        )

        self.assertEqual(session["title"], "Store walk-in pitch")
        self.assertTrue(session["transcript"])
        self.assertIn("overall_score", session["analysis"])
        self.assertTrue(session["audio_asset"]["url"].startswith("/media/pitch/"))

        dashboard = self.service.get_my_dashboard(learner_token)
        self.assertEqual(len(dashboard["pitch_sessions"]), 1)
        self.assertEqual(dashboard["pitch_sessions"][0]["id"], session["id"])

        trainer_dashboard = self.service.get_trainer_dashboard()
        self.assertEqual(trainer_dashboard["summary"]["pitch_sessions"], 1)
        self.assertTrue(trainer_dashboard["summary"]["pitch_average"] is not None)


if __name__ == "__main__":
    unittest.main()

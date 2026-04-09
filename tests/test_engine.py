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
from lms_engine.storage import JsonStore


class LMSEngineMVPTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        store_path = os.path.join(self.temp_dir.name, "state.json")
        self.service = LMSEngineService(store=JsonStore(store_path), generator=AIContentGenerator())
        owner_code = self.service.request_login_code({"phone_number": self.service.default_owner_phone})["code"]
        owner_login = self.service.verify_login_code(
            {"phone_number": self.service.default_owner_phone, "code": owner_code}
        )
        self.owner_token = owner_login["token"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_owner_can_generate_publish_role_and_create_phone_user(self) -> None:
        self.service.require_owner(self.owner_token)

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

    def test_review_preserves_owner_defined_skills_and_kpis(self) -> None:
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

    def test_owner_and_learner_permissions_are_separated(self) -> None:
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
            self.service.require_owner(learner_token)

        owner = self.service.get_current_user(self.owner_token)
        self.assertEqual(owner["user_type"], "owner")
        self.assertEqual(created["user"]["user_type"], "learner")


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.bootstrap import build_container


class LMSEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.container = build_container()

    def test_role_framework_learning_path_and_readiness(self) -> None:
        coaching = self.container.role_framework.create_competency(
            {
                "name": "Team Coaching",
                "description": "Coach frontline staff on daily performance.",
                "category": "people",
            }
        )
        operations = self.container.role_framework.create_competency(
            {
                "name": "Store Operations",
                "description": "Run opening, closing, and audit operations.",
                "category": "operations",
            }
        )

        role = self.container.role_framework.create_role(
            {
                "name": "Store Manager",
                "description": "Own store execution and team outcomes.",
                "responsibilities": ["Run shifts", "Coach the team", "Maintain compliance"],
                "growth_outcomes": ["Become promotion ready for Area Manager"],
            }
        )
        self.container.role_framework.add_requirement(
            role.id,
            {
                "competency_id": coaching.id,
                "required_level": 4,
                "mandatory": True,
                "weight": 1.0,
            },
        )
        self.container.role_framework.add_requirement(
            role.id,
            {
                "competency_id": operations.id,
                "required_level": 5,
                "mandatory": True,
                "weight": 1.2,
            },
        )

        asset = self.container.learning_catalog.create_asset(
            {
                "title": "Daily Floor Coaching",
                "summary": "How to coach store staff using floor observations.",
                "content_type": "video",
                "competency_ids": [coaching.id],
                "estimated_minutes": 15,
            }
        )
        assessment = self.container.learning_catalog.create_assessment(
            {
                "title": "Store Operations Certification",
                "assessment_type": "practical",
                "competency_ids": [operations.id],
                "passing_score": 80,
                "max_score": 100,
            }
        )

        path = self.container.learning_paths.generate_for_role(role.id)
        self.assertEqual(path.role_id, role.id)
        self.assertEqual(len(path.items), 2)
        self.assertIn(asset.id, path.items[0].asset_ids)
        self.assertIn(assessment.id, path.items[1].assessment_ids)

        employee = self.container.people.create_employee(
            {
                "name": "Asha",
                "email": "asha@cult.fit",
                "current_role_id": role.id,
                "org_unit": "Retail South",
            }
        )

        self.container.evidence.record_evidence(
            employee.id,
            {
                "competency_id": coaching.id,
                "evidence_type": "manager_signoff",
                "status": "verified",
                "notes": "Observed weekly floor coaching.",
            },
        )
        self.container.evidence.record_evidence(
            employee.id,
            {
                "competency_id": operations.id,
                "evidence_type": "practical_evaluation",
                "status": "passed",
                "score": 100,
                "max_score": 100,
            },
        )

        readiness = self.container.readiness.evaluate(employee.id)
        self.assertEqual(readiness.compliance_score, 100.0)
        self.assertEqual(readiness.competency_coverage, 100.0)
        self.assertTrue(readiness.ready)

    def test_kpi_analysis_recommends_learning_and_manager_insights(self) -> None:
        conversion = self.container.role_framework.create_competency(
            {
                "name": "Sales Conversion",
                "description": "Convert walk-ins into revenue.",
                "category": "commercial",
            }
        )
        coaching = self.container.role_framework.create_competency(
            {
                "name": "Team Coaching",
                "description": "Coach staff against weak sales metrics.",
                "category": "people",
            }
        )

        role = self.container.role_framework.create_role(
            {
                "name": "Store Manager",
                "description": "Drive store conversion and people performance.",
                "responsibilities": ["Manage the store floor"],
                "growth_outcomes": ["Improve team-level commercial execution"],
            }
        )
        self.container.role_framework.add_requirement(
            role.id,
            {
                "competency_id": conversion.id,
                "required_level": 4,
                "mandatory": True,
                "weight": 1.1,
            },
        )

        asset = self.container.learning_catalog.create_asset(
            {
                "title": "Conversion Recovery Clinic",
                "summary": "Improve low conversion through scripting.",
                "content_type": "microlearning",
                "competency_ids": [conversion.id, coaching.id],
                "estimated_minutes": 10,
            }
        )
        assessment = self.container.learning_catalog.create_assessment(
            {
                "title": "Conversion Scenario Test",
                "assessment_type": "scenario",
                "competency_ids": [conversion.id],
                "passing_score": 75,
                "max_score": 100,
            }
        )
        kpi = self.container.kpis.create_kpi(
            {
                "name": "Conversion Rate",
                "description": "Inbound lead conversion performance.",
                "competency_ids": [conversion.id, coaching.id],
                "weak_threshold": 0.85,
            }
        )

        first_employee = self.container.people.create_employee(
            {
                "name": "Asha",
                "email": "asha@cult.fit",
                "current_role_id": role.id,
                "org_unit": "Retail South",
            }
        )
        second_employee = self.container.people.create_employee(
            {
                "name": "Dev",
                "email": "dev@cult.fit",
                "current_role_id": role.id,
                "org_unit": "Retail West",
            }
        )

        self.container.kpis.record_observation(
            first_employee.id,
            {
                "kpi_id": kpi.id,
                "value": 18,
                "target_value": 25,
                "period_label": "March 2026",
            },
        )
        self.container.kpis.record_observation(
            second_employee.id,
            {
                "kpi_id": kpi.id,
                "value": 16,
                "target_value": 25,
                "period_label": "March 2026",
            },
        )

        analysis = self.container.kpis.analyze_employee(first_employee.id)
        self.assertEqual(len(analysis.weak_kpis), 1)
        self.assertEqual(analysis.weak_kpis[0].kpi_id, kpi.id)
        self.assertIn(asset.id, analysis.weak_kpis[0].asset_ids)
        self.assertIn(assessment.id, analysis.weak_kpis[0].assessment_ids)

        report = self.container.kpis.manager_improvement_report()
        self.assertEqual(len(report.weak_kpis), 1)
        self.assertEqual(report.weak_kpis[0].weak_observation_count, 2)
        self.assertEqual(report.weak_kpis[0].affected_employee_count, 2)
        self.assertEqual(report.weak_kpis[0].linked_asset_count, 1)
        self.assertEqual(report.weak_kpis[0].linked_assessment_count, 1)


if __name__ == "__main__":
    unittest.main()

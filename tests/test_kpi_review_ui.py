import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


class KPIReviewUITestCase(unittest.TestCase):
    def test_review_tab_owns_kpi_video_studio_ui(self) -> None:
        html_path = os.path.join(PROJECT_ROOT, "src", "lms_engine", "ui", "index.html")
        script_path = os.path.join(PROJECT_ROOT, "src", "lms_engine", "ui", "app.js")

        with open(html_path, "r", encoding="utf-8") as handle:
            html = handle.read()
        with open(script_path, "r", encoding="utf-8") as handle:
            script = handle.read()

        self.assertNotIn('data-subtab="trainer-kpi-studio"', html)
        self.assertIn('id="trainer-review"', html)
        self.assertIn('id="kpi-studio-summary"', html)
        self.assertIn('id="kpi-studio-list"', html)
        self.assertNotIn('id="kpi-studio-detail"', html)
        self.assertIn("2. Learning Path", html)
        self.assertIn("Learner Course Preview", html)
        self.assertEqual(html.count('id="role-detail"'), 1)
        self.assertEqual(html.count('id="review-note"'), 1)
        self.assertIn('setSubtab("admin", "trainer-review")', script)
        self.assertNotIn('setSubtab("admin", "trainer-kpi-studio")', script)
        self.assertIn("Generate New Course", script)
        self.assertNotIn("Generate Missing Videos", script)
        self.assertNotIn("studio-item-generate-btn", script)
        self.assertNotIn("studio-item-open-btn", script)
        self.assertNotIn("Approve Video", script)
        self.assertNotIn("Reopen KPI", script)
        self.assertIn("The quiz will appear automatically once the video is generated.", script)
        self.assertNotIn("Feedback For Changes", script)
        self.assertNotIn("Create Revised Video", script)
        self.assertIn("learning-path-summary", script)
        self.assertIn('addEventListener("toggle"', script)
        self.assertIn('data-can-open', script)
        self.assertIn('openItemIds', script)
        self.assertIn('state.kpiStudio.activeItemId = null', script)
        self.assertNotIn('|| state.kpiStudio.items[0] || null', script)
        self.assertIn('lessonCount', script)
        self.assertIn('quizCount', script)
        self.assertIn('quizzes', script)
        self.assertNotIn('<h3 class="section-title">Learning Path</h3>', script)
        self.assertNotIn('<h3 class="section-title">Assessment Coverage</h3>', script)


if __name__ == "__main__":
    unittest.main()

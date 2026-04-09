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
        self.assertIn('id="kpi-studio-detail"', html)
        self.assertIn('setSubtab("admin", "trainer-review")', script)
        self.assertNotIn('setSubtab("admin", "trainer-kpi-studio")', script)
        self.assertNotIn('<h3 class="section-title">Learning Path</h3>', script)
        self.assertNotIn('<h3 class="section-title">Assessment Coverage</h3>', script)


if __name__ == "__main__":
    unittest.main()

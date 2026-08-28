from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "apps/studio-web/app/page.tsx"
LAYOUT = ROOT / "apps/studio-web/app/layout.tsx"
CSS = ROOT / "apps/studio-web/app/landing.css"


class Phase3LandingPageTests(unittest.TestCase):
    def test_offer_and_proof_are_specific_and_honest(self) -> None:
        page = PAGE.read_text()
        self.assertIn("Verified product path", page)
        self.assertIn("Working code, not a concept reel", page)
        self.assertIn("$0", page)
        self.assertIn("during the gated build", page)
        self.assertIn("Not yet. The product is in a gated build sprint", page)
        self.assertNotIn("fully production-ready", page.lower())

    def test_primary_conversion_routes_are_implemented(self) -> None:
        page = PAGE.read_text()
        self.assertGreaterEqual(page.count('href="/sign-in"'), 4)
        self.assertTrue((ROOT / "apps/studio-web/app/sign-in/page.tsx").is_file())
        self.assertTrue((ROOT / "apps/studio-web/app/api/auth/sign-in/route.ts").is_file())
        self.assertNotIn("disabled", page)

    def test_in_page_navigation_has_no_dead_targets(self) -> None:
        page = PAGE.read_text()
        targets = set(re.findall(r'href="#([a-z-]+)"', page))
        ids = set(re.findall(r'id="([a-z-]+)"', page))
        self.assertTrue(targets)
        self.assertEqual(set(), targets - ids)

    def test_accessibility_motion_and_responsive_contract(self) -> None:
        page = PAGE.read_text()
        css = CSS.read_text()
        self.assertIn("Skip to main content", page)
        self.assertIn("Illustrated Montage source-to-story workflow", page)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("summary", css)

    def test_metadata_and_analytics_boundary_are_explicit(self) -> None:
        layout = LAYOUT.read_text()
        self.assertIn("openGraph", layout)
        self.assertIn("twitter", layout)
        self.assertIn('data-analytics-scope="consent-required"', layout)


if __name__ == "__main__":
    unittest.main()

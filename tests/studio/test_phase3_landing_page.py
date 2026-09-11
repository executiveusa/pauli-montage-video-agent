from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "apps/studio-web/app/page.tsx"
HERO = ROOT / "apps/studio-web/components/MontageHero.tsx"
WAITLIST_FORM = ROOT / "apps/studio-web/components/BetaWaitlistForm.tsx"
LAYOUT = ROOT / "apps/studio-web/app/layout.tsx"
CSS = ROOT / "apps/studio-web/app/landing.css"
BRAND_CSS = ROOT / "apps/studio-web/app/brand-launch.css"
STATIC_FORM = ROOT / "apps/studio-web/public/waitlist.html"
THANKS_PAGE = ROOT / "apps/studio-web/app/thanks/page.tsx"


class Phase3LandingPageTests(unittest.TestCase):
    def test_offer_and_proof_are_specific_and_honest(self) -> None:
        page = PAGE.read_text()
        hero = HERO.read_text()
        self.assertIn("Verified product path", page)
        self.assertIn("Real editing infrastructure · private beta", page)
        self.assertIn("Request early access", page)
        self.assertIn("source masters stay protected", hero)
        self.assertIn("AI-assisted video editing · Private beta", hero)
        self.assertNotIn("fully production-ready", (page + hero).lower())
        self.assertNotIn("10,000", page + hero)

    def test_primary_conversion_routes_are_implemented(self) -> None:
        page = PAGE.read_text()
        hero = HERO.read_text()
        form = WAITLIST_FORM.read_text()
        static_form = STATIC_FORM.read_text()
        thanks = THANKS_PAGE.read_text()
        surface = page + hero + form

        self.assertGreaterEqual(surface.count('href="#waitlist"'), 3)
        self.assertGreaterEqual(surface.count("Request beta access"), 4)
        self.assertIn("<BetaWaitlistForm />", page)
        self.assertIn('name="montage-waitlist"', form)
        self.assertIn('data-netlify="true"', form)
        self.assertIn('data-netlify-honeypot="bot-field"', form)
        self.assertIn('name="form-name" value="montage-waitlist"', form)
        self.assertIn('fetch("/", {', form)
        self.assertIn('"Content-Type": "application/x-www-form-urlencoded"', form)
        self.assertIn('window.location.assign("/thanks")', form)
        self.assertIn('name="montage-waitlist"', static_form)
        self.assertIn('data-netlify="true"', static_form)
        self.assertIn('data-netlify-honeypot="bot-field"', static_form)
        self.assertIn('action="/"', static_form)
        self.assertIn("Request received.", thanks)

    def test_in_page_navigation_has_no_dead_targets(self) -> None:
        page = PAGE.read_text()
        hero = HERO.read_text()
        surface = page + hero
        targets = set(re.findall(r'href="#([a-z-]+)"', surface))
        ids = set(re.findall(r'id="([a-z-]+)"', page))
        self.assertTrue(targets)
        self.assertEqual(set(), targets - ids)

    def test_accessibility_motion_and_responsive_contract(self) -> None:
        page = PAGE.read_text()
        hero = HERO.read_text()
        form = WAITLIST_FORM.read_text()
        css = CSS.read_text() + BRAND_CSS.read_text()
        self.assertIn("Skip to main content", page)
        self.assertIn("Illustrated Montage source-to-story workflow", page)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-reduced-motion: reduce", hero)
        self.assertIn("Pause hero montage", hero)
        self.assertIn("max-width: 620px", hero)
        self.assertIn('role="alert"', form)
        self.assertIn('aria-busy={submitting}', form)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("summary", css)

    def test_metadata_and_analytics_boundary_are_explicit(self) -> None:
        layout = LAYOUT.read_text()
        self.assertIn("openGraph", layout)
        self.assertIn("twitter", layout)
        self.assertIn("Turn raw footage into one finished story", layout)
        self.assertIn('data-analytics-scope="consent-required"', layout)


if __name__ == "__main__":
    unittest.main()

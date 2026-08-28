from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FRAME = ROOT / "apps/studio-web/components/StudioFrame.tsx"
UI = ROOT / "apps/studio-web/components/ui/StudioUI.tsx"
CSS = ROOT / "apps/studio-web/app/design-system.css"


class Phase2ApplicationShellTests(unittest.TestCase):
    def test_keyboard_navigation_contract(self) -> None:
        frame = FRAME.read_text()
        css = CSS.read_text()
        self.assertIn('href="#studio-content"', frame)
        self.assertIn('aria-current={active === item.label ? "page"', frame)
        self.assertIn('id="studio-content"', frame)
        self.assertIn(":focus-visible", css)
        self.assertIn("min-height: 44px", css)

    def test_shared_state_and_dialog_contract(self) -> None:
        ui = UI.read_text()
        for export in ("StudioNotice", "StudioLoadingState", "StudioEmptyState", "StudioErrorState", "StudioDialog"):
            self.assertIn(f"export function {export}", ui)
        self.assertIn('aria-live="polite"', ui)
        self.assertIn('role="alert"', ui)
        self.assertIn("showModal()", ui)

    def test_desktop_tablet_mobile_and_motion_contract(self) -> None:
        css = CSS.read_text()
        self.assertIn("@media (max-width: 1000px)", css)
        self.assertIn("@media (max-width: 620px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("grid-template-columns: 1fr 1fr", css)

    def test_every_shell_action_has_a_real_route(self) -> None:
        frame = FRAME.read_text()
        expected = {
            'href: "/studio"': ROOT / "apps/studio-web/app/studio/page.tsx",
            'href: "/studio/new"': ROOT / "apps/studio-web/app/studio/new/page.tsx",
            'action="/api/auth/sign-out"': ROOT / "apps/studio-web/app/api/auth/sign-out/route.ts",
            'href="/"': ROOT / "apps/studio-web/app/page.tsx",
        }
        for source, target in expected.items():
            self.assertIn(source, frame)
            self.assertTrue(target.is_file(), f"missing route target for {source}: {target}")


if __name__ == "__main__":
    unittest.main()

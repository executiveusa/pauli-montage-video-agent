"""Browser acceptance for the zero-credit local Montage editing loop.

This test intentionally exercises the product surface, not only helper functions:
create -> ingest -> canonical timeline -> source-backed preview -> split ->
undo/redo -> save/reopen -> timed presentation -> deterministic render -> verify.
"""

from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("MONTAGE_STUDIO_TEST_URL", "http://127.0.0.1:3000")
FIXTURE = Path(os.environ.get("MONTAGE_STUDIO_TEST_FIXTURE", "/tmp/montage-browser-source.mp4")).resolve()
SCREENSHOT = Path("/tmp/montage-browser-failure.png")
TRACE = Path("/tmp/montage-browser-trace.zip")


def main() -> int:
    if not FIXTURE.is_file():
        raise SystemExit(f"fixture not found: {FIXTURE}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1200})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        try:
            page.goto(f"{BASE_URL}/studio/new", wait_until="networkidle")
            page.get_by_label("Project title").fill("ASC3ND WHY WE STARTED Browser Acceptance")
            page.get_by_label("Project slug").fill("asc3nd-browser-acceptance")
            page.get_by_label("What are we making?").fill("Prove source-backed local editing and a verified 9:16 review without publishing.")
            page.get_by_label("Primary deliverable").select_option(label="9:16 vertical master")
            page.get_by_role("button", name="Create project").click()
            page.wait_for_url(re.compile(r"/studio/projects/local_.+/footage$"), timeout=15_000)

            expect(page.get_by_role("heading", name="Ready on this computer")).to_be_visible(timeout=10_000)
            file_input = page.locator('input[type="file"]')
            expect(file_input).to_be_enabled()
            file_input.set_input_files(str(FIXTURE))
            expect(page.get_by_text("Canonical asset · local bytes synced")).to_be_visible(timeout=30_000)
            source_name = FIXTURE.name
            expect(page.locator(".source-card strong")).to_have_text(source_name)

            page.get_by_role("link", name="Timeline").click()
            page.wait_for_url(re.compile(r"/studio/projects/local_.+/edit$"), timeout=10_000)
            expect(page.get_by_text("source-backed playback")).to_be_visible(timeout=10_000)
            video = page.locator("video").first
            expect(video).to_have_attribute("src", re.compile(r"127\.0\.0\.1:4788/files/.+/assets/"))

            # Prove this is not a decorative preview: the real media element must
            # decode/play and advance the canonical timeline playhead.
            playhead = page.get_by_label("Playhead")
            page.get_by_role("button", name="Play", exact=True).click()
            page.wait_for_timeout(450)
            playback_value = float(playhead.input_value())
            if playback_value <= 0.05:
                raise AssertionError(f"source playback did not advance timeline playhead: {playback_value}")
            page.get_by_role("button", name="Pause", exact=True).click()

            timeline_clips = page.locator('button[class*="timelineClip"]')
            expect(timeline_clips).to_have_count(1)
            timeline_clips.first.click()

            # Seek with the actual accessible range control. Keyboard arrows fire
            # the product's real input/change path and avoid clicking through a
            # source clip that visually covers the lane.
            playhead.focus()
            playhead.press("Home")
            for _ in range(10):
                playhead.press("ArrowRight")
            playhead_value = float(playhead.input_value())
            if playhead_value <= 0.05 or playhead_value >= 1.75:
                raise AssertionError(f"timeline seek did not move playhead inside clip: {playhead_value}")

            timeline_clips.first.click(position={"x": 8, "y": 8})
            page.get_by_role("button", name="Split at playhead").first.click()
            expect(timeline_clips).to_have_count(2)

            page.get_by_role("button", name="Undo").first.click()
            expect(timeline_clips).to_have_count(1)
            page.get_by_role("button", name="Redo").first.click()
            expect(timeline_clips).to_have_count(2)

            save = page.get_by_role("button", name=re.compile(r"Save v\d+"))
            save.click()
            expect(page.get_by_text(re.compile(r"Saved locally as timeline v\d+"))).to_be_visible(timeout=10_000)
            page.get_by_role("button", name="Reopen saved").click()
            expect(timeline_clips).to_have_count(2)

            # Add typed presentation state through the same saved StudioProject timeline.
            page.get_by_label("Role").select_option("title")
            page.get_by_label("Text").fill("WHY WE STARTED")
            page.get_by_label("Start").fill("0")
            page.get_by_label("Duration").fill("0.45")
            page.get_by_role("button", name="Add to timeline").click()
            expect(page.get_by_text(re.compile(r"Added title to canonical timeline v\d+"))).to_be_visible()

            page.get_by_label("Role").select_option("lower_third")
            page.get_by_label("Text").fill("Otha Minnifield — Founder, ASC3ND Collective")
            page.get_by_label("Start").fill("0.15")
            page.get_by_label("Duration").fill("0.55")
            page.get_by_role("button", name="Add to timeline").click()
            expect(page.get_by_text(re.compile(r"Added lower third to canonical timeline v\d+"))).to_be_visible()

            page.get_by_role("button", name="Reopen saved").click()
            expect(page.get_by_text("WHY WE STARTED", exact=True)).to_be_visible(timeout=10_000)

            page.get_by_role("button", name="Render + verify 9:16 review").click()
            expect(page.get_by_text(re.compile(r"Verified \d+ source range"))).to_be_visible(timeout=120_000)
            review_link = page.get_by_role("link", name=re.compile(r"Open verified MP4"))
            expect(review_link).to_be_visible()
            review_url = review_link.get_attribute("href")
            if not review_url:
                raise AssertionError("verified review link had no href")
            with urllib.request.urlopen(review_url, timeout=30) as response:
                payload = response.read(64)
                if response.status != 200 or len(payload) == 0:
                    raise AssertionError("verified review MP4 was not retrievable from local worker")

            if page_errors:
                raise AssertionError(f"uncaught browser errors: {page_errors}")
            context.tracing.stop(path=str(TRACE))
            browser.close()
            return 0
        except Exception:
            try:
                page.screenshot(path=str(SCREENSHOT), full_page=True)
            finally:
                context.tracing.stop(path=str(TRACE))
                browser.close()
            raise


if __name__ == "__main__":
    raise SystemExit(main())

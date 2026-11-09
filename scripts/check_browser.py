"""Exercise the actual Streamlit UI and retain screenshots or a labelled walkthrough."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tunebench.dashboard import PRESETS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--assets", type=Path, default=Path("docs/assets"))
    parser.add_argument("--chromium", default=shutil.which("chromium"))
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--live", action="store_true", help="Run one real local model request")
    args = parser.parse_args()
    args.assets.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="tunebench-browser-") as temporary:
        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--no-sandbox"]}
            if args.chromium:
                launch["executable_path"] = args.chromium
            browser = playwright.chromium.launch(**launch)
            context_options = {"viewport": {"width": 1440, "height": 1080}}
            if args.video:
                context_options.update(
                    record_video_dir=temporary, record_video_size={"width": 1440, "height": 1080}
                )
            context = browser.new_context(**context_options)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url)
            page.get_by_text("Try a request", exact=True).wait_for(timeout=20000)
            assert "this mode does not use an LLM" in page.locator("body").inner_text()

            def preset(name):
                page.get_by_role("combobox", name="Start with an example").click()
                page.get_by_role("option", name=name, exact=True).click()
                expect(page.get_by_role("textbox", name="Your request", exact=True)).to_have_value(
                    PRESETS[name]
                )

            def run_and_wait(expected):
                page.get_by_role("button", name="Run request →", exact=True).click()
                page.get_by_text(expected, exact=False).first.wait_for(timeout=20000)
                page.wait_for_timeout(2000 if args.video else 450)

            run_and_wait("Demo order TB-1001 is shipped.")
            page.screenshot(path=str(args.assets / "tunebench-playground.png"), full_page=True)
            checks.append("Actual simulated order lookup in quick rules mode")

            preset("Ask for a missing amount")
            run_and_wait("Please specify refund_amount.")
            assert (
                "This workbench handles one complete request at a time"
                in page.locator("body").inner_text()
            )
            page.screenshot(path=str(args.assets / "tunebench-clarification.png"), full_page=True)
            checks.append("Missing amount clarifies with a full-request follow-up instruction")

            preset("Prepare a refund proposal")
            run_and_wait("Simulated proposal SIM-")
            assert "250.00" in page.locator("body").inner_text()
            checks.append("Nonmutating INR250 mock refund proposal")

            preset("Decline a real payment")
            run_and_wait("This action is unavailable.")
            checks.append("Actual-payment request returns no tool")

            page.get_by_role("textbox", name="Your request", exact=True).fill(
                "Check the status of order TB-9999."
            )
            run_and_wait("order_id is not in the fictional demo order store")
            page.screenshot(path=str(args.assets / "tunebench-blocked.png"), full_page=True)
            checks.append("Unknown fictional order blocked before execution")

            page.get_by_role("textbox", name="Your request", exact=True).fill("   ")
            page.get_by_role("textbox", name="Your request", exact=True).press("Tab")
            page.wait_for_timeout(350)
            assert page.get_by_role("button", name="Run request →", exact=True).is_disabled()
            checks.append("Blank input cannot run")

            page.get_by_role("combobox", name="Run mode").click()
            page.get_by_role("option", name="Saved model replay", exact=True).click()
            page.get_by_role("button", name="View recorded response", exact=True).click()
            page.get_by_text(
                "Recorded response from the original CPU model run.", exact=False
            ).first.wait_for()
            assert "recorded generation time" in page.locator("body").inner_text()
            checks.append("Recorded replay is labelled and performs no new tool execution")
            page.screenshot(path=str(args.assets / "tunebench-replay.png"), full_page=True)

            page.get_by_role("tab", name="Evaluation", exact=True).click()
            page.get_by_text("Evidence, with the context attached", exact=True).wait_for()
            assert "the same 12 development cases" in page.locator("body").inner_text()
            page.screenshot(path=str(args.assets / "tunebench-evaluation.png"), full_page=True)
            checks.append("Evaluation distinguishes historical datasets and backend identities")

            page.get_by_role("tab", name="Project", exact=True).click()
            page.get_by_text("A small system, built all the way through", exact=True).wait_for()
            checks.append("Architecture and honest scope visible")

            page.get_by_role("tab", name="Playground", exact=True).click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(500)
            sizes = page.evaluate(
                "({width:innerWidth,scroll:document.documentElement.scrollWidth})"
            )
            assert sizes["scroll"] <= sizes["width"]
            page.screenshot(path=str(args.assets / "tunebench-mobile.png"), full_page=True)
            checks.append("390px viewport has no horizontal overflow")
            page.set_viewport_size({"width": 1440, "height": 1080})

            if args.live:
                page.get_by_role("combobox", name="Run mode").click()
                page.get_by_role("option", name="Live local Qwen", exact=True).click()
                preset("Track an order")
                page.get_by_role("button", name="Run request →", exact=True).click()
                page.get_by_text("Live local Qwen ·", exact=False).first.wait_for(timeout=180000)
                assert "The request could not run" not in page.locator("body").inner_text()
                assert "Demo order TB-1001 is shipped." in page.locator("body").inner_text()
                page.get_by_text("Raw responses & validation trace", exact=True).click()
                assert page.get_by_text("Attempt 1", exact=True).is_visible()
                assert page.get_by_text("Model review · attempt 1", exact=True).is_visible()
                assert "probabilistic" in page.locator("body").inner_text() or (
                    "Fallible model judgement" in page.locator("body").inner_text()
                )
                page.screenshot(path=str(args.assets / "tunebench-live.png"), full_page=True)
                checks.append("Actual local Qwen response and its raw attempt are visible")
            assert not errors, errors
            video = page.video
            context.close()
            if args.video:
                video.save_as(str(args.assets / "tunebench-demo.webm"))
            browser.close()
    evidence = {"checks_passed": checks, "browser_errors": errors, "live_model_checked": args.live}
    (args.assets / "browser-checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()

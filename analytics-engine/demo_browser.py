"""
Playwright browser automation demo for PortfolioDashboard.
Launches a headed Chromium browser, navigates to the frontend,
logs in with demo account, and explores all dashboard tabs.
"""
import time
import os
import sys

from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:5173"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_browser_demo():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--window-size=1280,800",
                "--window-position=100,100",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        page = context.new_page()

        # ── 1. Navigate to auth page directly ────────────────
        print("[01] Opening SmartPortfolio Advisor - Auth page...")
        page.goto(FRONTEND_URL + "/auth", wait_until="networkidle")
        time.sleep(3)

        # ── 2. Click Demo Login ──────────────────────────────
        print("[02] Clicking Try Demo...")
        demo_btn = page.locator("text=Try Demo")
        if demo_btn.count() > 0:
            demo_btn.click()
        else:
            # Fallback: try clicking Sign In with any email/password
            page.fill('input[type="email"]', "demo@smartadvisor.ai")
            page.fill('input[type="password"]', "Demo1234!")
            page.locator("text=Sign In").click()
        time.sleep(3)

        # ── 3. Wait for dashboard redirect ───────────────────
        print("[03] Waiting for dashboard to load...")
        try:
            page.wait_for_url("**/dashboard**", timeout=15000)
        except Exception:
            # Manually navigate if redirect fails
            page.goto(FRONTEND_URL + "/dashboard", wait_until="domcontentloaded")
        time.sleep(2)

        # ── 4. Wait for portfolio analysis pipeline ────────────
        print("[04] Waiting for pipeline (~80s)...")
        try:
            page.wait_for_selector("text=Running portfolio analysis pipeline...", timeout=5000)
        except Exception:
            pass  # Pipeline might already be done

        # Wait for the loading spinner to disappear (data loaded)
        try:
            page.wait_for_selector("text=Running portfolio analysis pipeline...", state="hidden", timeout=120000)
        except Exception:
            # If it times out, the data might have loaded already or failed
            # Try waiting for the portfolio score element instead
            try:
                page.wait_for_selector("text=Portfolio Score", timeout=10000)
            except Exception:
                print("  WARNING: Pipeline might have timed out in UI")

        time.sleep(3)  # Show overview with data

        # ── 5. Capture each tab ──────────────────────────────
        tabs = ["Overview", "Risk & Budget", "Performance", "Intelligence", "Recommendations"]
        for i, tab_name in enumerate(tabs):
            print(f"[05.{i+1}] Switching to tab: {tab_name}")
            tab = page.locator(f"text={tab_name}")
            if tab.count() > 0:
                tab.click()
            time.sleep(6)

        # ── 6. Show recommendations detail ─────────────────────
        print("[06] Recommendations tab detail view")
        time.sleep(3)

        # ── 7. Return to Overview ────────────────────────────
        print("[07] Returning to Overview")
        page.locator("text=Overview").click()
        time.sleep(4)

        # ── Done ─────────────────────────────────────────────
        print("[DONE] Browser demo complete.")
        browser.close()


if __name__ == "__main__":
    run_browser_demo()

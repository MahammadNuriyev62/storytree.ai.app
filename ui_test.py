"""Visual UI test: verify Claude's markdown renders instead of showing raw asterisks."""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 900, "height": 1100})

        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        # fresh visit => no saved progress => no confirm dialog; accept any just in case
        page.on("dialog", lambda d: asyncio.create_task(d.accept()))

        await page.goto(f"{BASE}/stories/1/play")

        # Sanity: marked.js loaded and working in-page
        marked_ok = await page.evaluate("() => window.marked ? marked.parse('*x*').includes('<em>') : false")
        print(f"marked.js working in page: {marked_ok}")

        # Wait for root scene (scene 1) to render
        await page.wait_for_selector("#scene-text", state="visible", timeout=20000)
        await page.wait_for_function("() => document.querySelector('#scene-text').innerText.trim().length > 0", timeout=20000)
        await page.screenshot(path="/tmp/ui_scene1.png")
        print("captured scene 1")

        # Click the first choice -> scene 2 (cached, contains *emphasis*)
        await page.wait_for_selector("#choices-container button", timeout=20000)
        await page.click("#choices-container button >> nth=0")

        # Wait for scene 2 specifically ("damp embrace" is unique to it).
        await page.wait_for_function(
            "() => document.querySelector('#scene-text').innerText.includes('damp embrace')",
            timeout=60000,
        )
        await page.wait_for_timeout(800)
        await page.screenshot(path="/tmp/ui_scene2.png", full_page=True)
        print("captured scene 2")

        html = await page.inner_html("#scene-text")
        text = await page.inner_text("#scene-text")

        has_em = "<em>" in html or "<strong>" in html
        # Did any literal markdown asterisks leak into visible text?
        leaked = "*" in text
        print(f"\nrendered HTML contains <em>/<strong>: {has_em}")
        print(f"visible text still contains literal '*': {leaked}")
        print(f"console/page errors: {errors if errors else 'none'}")
        snippet = html[:300].replace("\n", " ")
        print(f"\nHTML snippet: {snippet}")

        await browser.close()

        print("\n=== VERDICT ===")
        ok = marked_ok and has_em and not leaked and not errors
        print("PASS ✅" if ok else "ISSUES ❌")

asyncio.run(main())

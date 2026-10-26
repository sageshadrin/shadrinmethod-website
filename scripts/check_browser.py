#!/usr/bin/env python3
"""Exercise the static site in Chromium. Requires the optional Playwright package."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
NAV_ROUTES = ["/", "/method/", "/books/", "/author/", "/resources/"]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def check():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", help="Optional system Chromium executable")
    parser.add_argument("--screenshots", type=Path, help="Optional preview output directory")
    parser.add_argument("--axe", type=Path, help="Optional local axe-core axe.min.js")
    args = parser.parse_args()
    routes = ["/" + file.relative_to(ROOT).as_posix().removesuffix("index.html")
              for file in sorted(ROOT.rglob("*.html"))]
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    problems, results = [], []
    try:
        with sync_playwright() as playwright:
            options = {"executable_path": args.chromium} if args.chromium else {}
            browser = playwright.chromium.launch(**options)
            try:
                page = browser.new_page()
                page.on("pageerror", lambda error: problems.append(str(error)))
                page.on("console", lambda message: problems.append(message.text) if message.type == "error" else None)
                page.on("requestfailed", lambda request: problems.append(f"Request failed: {request.url}"))
                page.on("response", lambda response: problems.append(f"HTTP {response.status}: {response.url}") if response.status >= 400 else None)
                for width in [320, 375, 768, 1440]:
                    page.set_viewport_size({"width": width, "height": 900})
                    for route in routes:
                        response = page.goto(origin + route, wait_until="networkidle")
                        assert response.status == 200, route
                        assert page.locator("h1").count() == 1, route
                        current_section = "/ru/books/" if route.startswith("/ru/books/") else ("/books/" if route.startswith("/books/") else route)
                        assert page.locator('nav a[aria-current="page"]').get_attribute("href") == current_section
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow: {route} at {width}"
                        # The first keyboard action must reveal the skip link and move focus to main.
                        page.keyboard.press("Tab")
                        assert page.locator(".skip-link").evaluate("el => el === document.activeElement"), route
                        assert page.locator(".skip-link").evaluate("el => el.getBoundingClientRect().top >= 0"), route
                        page.keyboard.press("Enter")
                        assert page.locator("main").evaluate("el => el === document.activeElement"), route
                        if width in [375, 1440] and args.screenshots:
                            page.screenshot(path=str(args.screenshots / f"{route.strip('/').replace('/', '-') or 'home'}-{width}.png"), full_page=True)
                        if args.axe and width in [375, 1440]:
                            page.add_script_tag(path=str(args.axe))
                            audit = page.evaluate("async () => (await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}})).violations")
                            if audit:
                                problems.append(f"Accessibility {route} at {width}: " + json.dumps(audit))
                        # Click every navigation entry from each page at every viewport.
                        for destination in (["/ru" + x for x in NAV_ROUTES] if route.startswith("/ru/") else NAV_ROUTES):
                            page.locator(f'.nav-links a[href="{destination}"]').click()
                            page.wait_for_url(origin + destination)
                            assert urlsplit(page.url).path == destination
                        results.append({"route": route, "width": width, "navigation": "passed", "keyboard": "passed"})
                page.emulate_media(reduced_motion="reduce")
                page.goto(origin, wait_until="networkidle")
                assert page.locator("html").evaluate("el => getComputedStyle(el).scrollBehavior") == "auto"
                for href in ["#approach", "#top"]:
                    link = page.locator(f'a[href="{href}"]').first
                    link.focus()
                    link.click()
                    page.wait_for_url(origin + "/" + href)
                    assert page.locator(href).count() == 1
                for asset in ["/favicon.ico", "/assets/favicon.svg", "/assets/site.css", "/assets/social-card.png"]:
                    assert page.request.get(origin + asset).status == 200, asset
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"PASS: {len(results)} page/viewport checks; {len(results) * len(NAV_ROUTES)} navigation clicks; keyboard skip links; home anchors; reduced motion; assets; no browser errors.")
    if args.axe:
        print("PASS: axe-core WCAG 2.1 A/AA checks at 375 and 1440 px (automated checks only).")


if __name__ == "__main__":
    check()

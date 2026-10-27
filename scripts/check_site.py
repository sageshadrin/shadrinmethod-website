#!/usr/bin/env python3
"""Check static pages, metadata, local links and image assets without dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import struct
import re
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://shadrinmethod.com"


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attrs(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


def local_file(path):
    target = (ROOT / unquote(path).lstrip("/")).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError(f"Path escapes site root: {path}")
    return target / "index.html" if target.is_dir() else target


def check():
    errors = []
    files = sorted(ROOT.rglob("*.html"))
    pages = {file: Page(file.read_text()) for file in files}
    links_checked = 0
    for file, page in pages.items():
        relative = file.relative_to(ROOT).as_posix()
        path = "/" + relative.removesuffix("index.html")
        expected_url = ORIGIN + path
        ids = [attrs["id"] for _, attrs in page.tags if "id" in attrs]
        if len(ids) != len(set(ids)):
            errors.append(f"{relative}: duplicate IDs")
        if len(page.attrs("h1")) != 1:
            errors.append(f"{relative}: expected one h1")
        # Heading-system guard: all pages inherit H1/hero typography from shared site.css.
        if any(a.get("style") for a in page.attrs("h1")):
            errors.append(f"{relative}: H1 must not have inline style")
        local_styles = re.findall(r"<style\b[^>]*>(.*?)</style>", file.read_text(), flags=re.I | re.S)
        for local_style in local_styles:
            if re.search(r"(?m)^\s*(?:h1|\.hero|\.page-hero)(?:\s+h1)?\s*\{", local_style):
                errors.append(f"{relative}: page-specific hero/H1 typography forbidden; update assets/site.css instead")

        expected_lang = "ru" if path.startswith("/ru/") else "en"
        if not page.attrs("html") or page.attrs("html")[0].get("lang") != expected_lang:
            errors.append(f"{relative}: missing {expected_lang} language declaration")
        canonical = [a.get("href") for a in page.attrs("link") if a.get("rel") == "canonical"]
        if canonical != [expected_url]:
            errors.append(f"{relative}: canonical must be {expected_url}")
        meta = {a.get("property", a.get("name")): a.get("content", "") for a in page.attrs("meta")}
        for key in ["description", "viewport", "og:title", "og:description", "og:type", "og:site_name", "og:url", "og:image", "og:image:alt"]:
            if not meta.get(key):
                errors.append(f"{relative}: missing {key}")
        if meta.get("og:url") != expected_url:
            errors.append(f"{relative}: og:url differs from canonical")
        if len(page.attrs("title")) != 1:
            errors.append(f"{relative}: expected one title")
        icons = [a for a in page.attrs("link") if a.get("rel") == "icon"]
        if not icons:
            errors.append(f"{relative}: missing favicon")
        nav = [a for a in page.attrs("a") if a.get("aria-current") == "page"]
        expected_nav = "/ru/books/" if path.startswith("/ru/books/") else ("/books/" if path.startswith("/books/") else path)
        if len(nav) != 1 or nav[0].get("href") != expected_nav:
            errors.append(f"{relative}: incorrect current navigation item")
        references = [a[key] for _, a in page.tags for key in ["href", "src"] if key in a]
        references.append(meta.get("og:image", ""))
        for reference in references:
            if not reference or reference == "#" or "{{" in reference:
                errors.append(f"{relative}: empty or unresolved reference {reference!r}")
                continue
            resolved = urlsplit(urljoin(expected_url, reference))
            if resolved.scheme not in ["http", "https"] or resolved.netloc != urlsplit(ORIGIN).netloc:
                continue
            target = local_file(resolved.path)
            links_checked += 1
            if not target.is_file():
                errors.append(f"{relative}: missing target {reference}")
            elif resolved.fragment:
                parsed = pages.get(target)
                if parsed is None or unquote(resolved.fragment) not in [a.get("id") for _, a in parsed.tags]:
                    errors.append(f"{relative}: missing fragment {reference}")
        if "{{" in file.read_text():
            errors.append(f"{relative}: unresolved template token")
    for path in ["/", "/method/", "/books/", "/author/", "/resources/", "/ru/", "/ru/method/", "/ru/books/", "/ru/author/", "/ru/resources/"]:
        if not local_file(path).is_file():
            errors.append(f"Missing required page: {path}")
    image = (ROOT / "assets/social-card.png").read_bytes()
    if image[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", image[16:24]) != (1200, 630):
        errors.append("Social image must be a 1200 × 630 PNG")
    if (ROOT / "favicon.ico").read_bytes()[:4] != b"\x00\x00\x01\x00":
        errors.append("Invalid ICO favicon")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(pages)} pages; {links_checked} local references; metadata, anchors and image assets.")


if __name__ == "__main__":
    check()

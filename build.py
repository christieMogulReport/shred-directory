#!/usr/bin/env python3
"""Build a small static directory site from Markdown/YAML page files."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from html import escape
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent


def _ensure_deps() -> None:
    """Import PyYAML and Markdown, creating a local .venv if needed."""
    try:
        import markdown  # noqa: F401
        import yaml  # noqa: F401
        return
    except ImportError:
        pass

    import os
    import subprocess
    import venv as venv_mod

    venv_dir = ROOT / ".venv"
    venv_py = venv_dir / "bin" / "python"
    req = ROOT / "requirements.txt"

    if Path(sys.executable).resolve() == venv_py.resolve():
        sys.stderr.write(
            "Missing dependencies in .venv. Run: .venv/bin/pip install -r requirements.txt\n"
        )
        sys.exit(1)

    if not venv_py.exists():
        print("Creating .venv and installing requirements...")
        venv_mod.create(venv_dir, with_pip=True)
        subprocess.check_call([str(venv_py), "-m", "pip", "install", "-r", str(req)])
    else:
        probe = subprocess.run(
            [str(venv_py), "-c", "import markdown, yaml"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode != 0:
            print("Installing requirements into .venv...")
            subprocess.check_call([str(venv_py), "-m", "pip", "install", "-r", str(req)])

    os.execv(str(venv_py), [str(venv_py), *sys.argv])


_ensure_deps()
import markdown
import yaml
CONTENT_PAGES = ROOT / "content" / "pages"
HOME_MD = ROOT / "content" / "home.md"
STATIC = ROOT / "static"
CONFIG_PATH = ROOT / "config.yml"
DIST = ROOT / "dist"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)

MD = markdown.Markdown(extensions=["sane_lists", "smarty", "fenced_code"])


def die(message: str) -> None:
    sys.stderr.write(f"error: {message}\n")
    sys.exit(1)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        die(f"missing config file: {CONFIG_PATH}")
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        die("config.yml must be a mapping")
    data["site_name"] = str(data.get("site_name") or "Directory")
    data["site_tagline"] = str(data.get("site_tagline") or "").strip()
    data["site_description"] = str(data.get("site_description") or "").strip()
    data["site_owner"] = str(data.get("site_owner") or "").strip()
    data["language"] = str(data.get("language") or "en")
    data["base_url"] = str(data.get("base_url") or "").rstrip("/")
    base_path = str(data.get("base_path") or "").strip()
    if base_path in ("/", ""):
        base_path = ""
    elif not base_path.startswith("/"):
        die("config base_path must start with / or be empty")
    data["base_path"] = base_path.rstrip("/")
    disclosure = data.get("affiliate_disclosure") or ""
    if isinstance(disclosure, str):
        data["affiliate_disclosure"] = " ".join(disclosure.split())
    else:
        die("config affiliate_disclosure must be a string")
    return data


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def parse_date(value: Any, source: Path) -> dt.date:
    if value is None:
        die(f"{source}: last_updated is required (YYYY-MM-DD)")
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value).strip())
    except ValueError:
        die(f"{source}: last_updated must be YYYY-MM-DD, got {value!r}")
        raise


def render_markdown(text: str) -> str:
    MD.reset()
    return MD.convert(text or "")


def href_for(listing: dict[str, Any]) -> tuple[str, bool]:
    affiliate = str(listing.get("affiliate_url") or "").strip()
    url = str(listing.get("url") or "").strip()
    if affiliate:
        return affiliate, True
    return url, False


def site_href(config: dict[str, Any], path: str = "/") -> str:
    """Return a root-relative path, honoring base_path."""
    base = config["base_path"]
    if not path.startswith("/"):
        path = "/" + path
    if path == "/":
        return f"{base}/" if base else "/"
    return f"{base}{path}"


def absolute_url(config: dict[str, Any], path: str = "/") -> str:
    rel = site_href(config, path)
    if config["base_url"]:
        return config["base_url"] + rel
    return rel


def format_long_date(value: dt.date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def asset(config: dict[str, Any], path: str) -> str:
    return site_href(config, path)


def layout(
    config: dict[str, Any],
    *,
    title: str,
    description: str,
    canonical_path: str,
    body: str,
    extra_head: str = "",
) -> str:
    site_name = config["site_name"]
    full_title = title if title == site_name else f"{title} · {site_name}"
    desc = escape(description, quote=True)
    canonical = ""
    if config["base_url"]:
        canonical = (
            f'  <link rel="canonical" href="{escape(absolute_url(config, canonical_path), quote=True)}">\n'
        )
    tagline = ""
    if config["site_tagline"]:
        tagline = f'      <p class="tagline">{escape(config["site_tagline"])}</p>\n'
    disclosure = ""
    if config["affiliate_disclosure"]:
        disclosure = f'      <p class="disclosure">{escape(config["affiliate_disclosure"])}</p>\n'
    credit = ""
    if config["site_owner"]:
        credit = f'      <p class="credit">{escape(site_name)} · {escape(config["site_owner"])}</p>\n'
    else:
        credit = f'      <p class="credit">{escape(site_name)}</p>\n'
    home = site_href(config, "/")
    css = asset(config, "/css/style.css")
    return f"""<!DOCTYPE html>
<html lang="{escape(config["language"], quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(full_title)}</title>
  <meta name="description" content="{desc}">
{canonical}  <link rel="stylesheet" href="{escape(css, quote=True)}">
{extra_head}</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site">
    <div class="wrap">
      <a class="site-name" href="{escape(home, quote=True)}">{escape(site_name)}</a>
{tagline}    </div>
  </header>
  <main id="main">
    <div class="wrap">
{body}    </div>
  </main>
  <footer class="site">
    <div class="wrap">
{disclosure}{credit}    </div>
  </footer>
</body>
</html>
"""


def render_listings(listings: list[dict[str, Any]]) -> str:
    if not listings:
        return ""
    items: list[str] = []
    for listing in listings:
        name = str(listing.get("name") or "").strip()
        if not name:
            continue
        summary = str(listing.get("summary") or listing.get("description") or "").strip()
        category = str(listing.get("category") or "").strip()
        href, is_affiliate = href_for(listing)
        heading: str
        if href:
            rel = "sponsored noopener noreferrer" if is_affiliate else "noopener noreferrer"
            heading = (
                f'<h3><a href="{escape(href, quote=True)}" rel="{rel}" '
                f'target="_blank">{escape(name)}</a></h3>'
            )
        else:
            heading = f"<h3>{escape(name)}</h3>"
        summary_html = f"<p>{escape(summary)}</p>" if summary else ""
        meta_bits: list[str] = []
        if category:
            meta_bits.append(escape(category))
        if is_affiliate:
            meta_bits.append("Affiliate link")
        meta_html = (
            f'<p class="meta">{" · ".join(meta_bits)}</p>' if meta_bits else ""
        )
        items.append(
            f'        <li class="listing">\n'
            f"          {heading}\n"
            f"          {summary_html}\n"
            f"          {meta_html}\n"
            f"        </li>"
        )
    if not items:
        return ""
    return (
        '      <section class="listings" aria-labelledby="listings-heading">\n'
        '        <h2 id="listings-heading">Listings</h2>\n'
        '        <ul class="listings">\n'
        + "\n".join(items)
        + "\n        </ul>\n"
        "      </section>\n"
    )


def render_page(config: dict[str, Any], page: dict[str, Any]) -> str:
    updated = page["last_updated"]
    body_html = render_markdown(page["body"])
    prose = f'      <div class="prose">\n{body_html}\n      </div>\n' if body_html else ""
    listings = render_listings(page.get("listings") or [])
    inner = (
        "      <article>\n"
        f"        <h1>{escape(page['title'])}</h1>\n"
        f'        <p class="updated"><time datetime="{updated.isoformat()}">'
        f"Last updated {format_long_date(updated)}</time></p>\n"
        f"{prose}{listings}"
        "      </article>\n"
    )
    return layout(
        config,
        title=page["title"],
        description=page["description"],
        canonical_path=f"/{page['slug']}/",
        body=inner,
    )


def render_home(config: dict[str, Any], pages: list[dict[str, Any]]) -> str:
    intro = ""
    if HOME_MD.exists():
        intro_html = render_markdown(HOME_MD.read_text(encoding="utf-8").strip())
        intro = f'      <div class="prose">\n{intro_html}\n      </div>\n'
    elif config["site_description"]:
        intro = f'      <div class="prose">\n        <p>{escape(config["site_description"])}</p>\n      </div>\n'

    if pages:
        items: list[str] = []
        for page in pages:
            href = site_href(config, f"/{page['slug']}/")
            updated = page["last_updated"]
            desc = escape(page["description"]) if page["description"] else ""
            desc_html = f'<p class="desc">{desc}</p>' if desc else ""
            items.append(
                "        <li>\n"
                f'          <a class="title" href="{escape(href, quote=True)}">{escape(page["title"])}</a>\n'
                f"          {desc_html}\n"
                f'          <p class="updated"><time datetime="{updated.isoformat()}">'
                f"Last updated {format_long_date(updated)}</time></p>\n"
                "        </li>"
            )
        listing = (
            '      <h2>Directory pages</h2>\n'
            '      <ul class="page-list">\n'
            + "\n".join(items)
            + "\n      </ul>\n"
        )
    else:
        listing = (
            '      <p class="empty">Guides are on the way.</p>\n'
        )

    inner = f"      <h1>{escape(config['site_name'])}</h1>\n{intro}{listing}"
    return layout(
        config,
        title=config["site_name"],
        description=config["site_description"] or config["site_tagline"] or config["site_name"],
        canonical_path="/",
        body=inner,
    )


def load_page(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        die(f"{path}: each page needs YAML front matter between --- lines")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        die(f"{path}: invalid YAML front matter: {exc}")
    if not isinstance(meta, dict):
        die(f"{path}: front matter must be a mapping")

    title = str(meta.get("title") or "").strip()
    if not title:
        die(f"{path}: title is required")

    slug = str(meta.get("slug") or "").strip() or slugify(path.stem)
    if not SLUG_RE.match(slug):
        die(f"{path}: slug {slug!r} must be lowercase letters, numbers, and hyphens")

    description = str(meta.get("description") or "").strip()
    if not description:
        die(f"{path}: description is required (used as the meta description)")

    listings = meta.get("listings") or []
    if listings is None:
        listings = []
    if not isinstance(listings, list):
        die(f"{path}: listings must be a list")
    cleaned: list[dict[str, Any]] = []
    for i, item in enumerate(listings, start=1):
        if not isinstance(item, dict):
            die(f"{path}: listings[{i}] must be a mapping")
        if not str(item.get("name") or "").strip():
            die(f"{path}: listings[{i}] needs a name")
        href, _ = href_for(item)
        if not href:
            die(f"{path}: listings[{i}] needs url or affiliate_url")
        cleaned.append(item)

    return {
        "source": path,
        "title": title,
        "slug": slug,
        "description": description,
        "last_updated": parse_date(meta.get("last_updated"), path),
        "draft": bool(meta.get("draft", False)),
        "listings": cleaned,
        "body": match.group(2).strip(),
        "meta": meta,
    }


def collect_pages(*, include_drafts: bool) -> tuple[list[dict[str, Any]], int]:
    if not CONTENT_PAGES.exists():
        die(f"missing pages directory: {CONTENT_PAGES}")
    files = sorted(CONTENT_PAGES.glob("*.md"))
    pages: list[dict[str, Any]] = []
    drafts = 0
    seen: dict[str, Path] = {}
    for path in files:
        page = load_page(path)
        if page["draft"]:
            drafts += 1
            if not include_drafts:
                continue
        if page["slug"] in seen:
            die(f"duplicate slug {page['slug']!r}: {seen[page['slug']]} and {path}")
        seen[page["slug"]] = path
        pages.append(page)
    pages.sort(key=lambda p: (p["title"].lower(), p["slug"]))
    return pages, drafts


def write_sitemap(config: dict[str, Any], pages: list[dict[str, Any]]) -> None:
    urls: list[tuple[str, dt.date]] = [("/", max((p["last_updated"] for p in pages), default=dt.date.today()))]
    for page in pages:
        urls.append((f"/{page['slug']}/", page["last_updated"]))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, lastmod in urls:
        loc = xml_escape(absolute_url(config, path), {"'": "&apos;", '"': "&quot;"})
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f"    <lastmod>{lastmod.isoformat()}</lastmod>")
        parts.append("  </url>")
    parts.append("</urlset>")
    parts.append("")
    (DIST / "sitemap.xml").write_text("\n".join(parts), encoding="utf-8")


def write_robots(config: dict[str, Any]) -> None:
    sitemap = absolute_url(config, "/sitemap.xml")
    text = "User-agent: *\nAllow: /\n\nSitemap: " + sitemap + "\n"
    (DIST / "robots.txt").write_text(text, encoding="utf-8")


def copy_static() -> None:
    if not STATIC.exists():
        return
    for src in STATIC.rglob("*"):
        if src.is_file():
            dest = DIST / src.relative_to(STATIC)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def build(*, include_drafts: bool) -> None:
    config = load_config()
    pages, drafts = collect_pages(include_drafts=include_drafts)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    copy_static()
    (DIST / "index.html").write_text(render_home(config, pages), encoding="utf-8")
    for page in pages:
        out_dir = DIST / page["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render_page(config, page), encoding="utf-8")
    write_sitemap(config, pages)
    write_robots(config)

    skipped = drafts if not include_drafts else 0
    included_drafts = drafts if include_drafts else 0
    print(f"Built {len(pages)} page(s) into {DIST}")
    if skipped:
        print(f"Skipped {skipped} draft page(s)")
    if included_drafts:
        print(f"Included {included_drafts} draft page(s) (--drafts)")
    if not config["base_url"]:
        print("Note: config base_url is empty; sitemap <loc> values are root-relative. Set base_url before publishing.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the static directory site into dist/")
    parser.add_argument(
        "--drafts",
        action="store_true",
        help="include pages with draft: true (for local preview only)",
    )
    args = parser.parse_args(argv)
    build(include_drafts=args.drafts)


if __name__ == "__main__":
    main()

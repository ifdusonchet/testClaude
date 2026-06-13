"""
build_static.py — Render all pages to static HTML for GitHub Pages preview.
Outputs everything to the ../docs/ folder.

Run from inside melodic-techno-site/:
    ADMIN_PASSWORD=x SECRET_KEY=x python build_static.py
"""

import os
import re
import shutil

# ── Setup env before importing the app ───────────────────────
os.environ.setdefault("SECRET_KEY", "static-build-key")
os.environ.setdefault("ADMIN_PASSWORD", "unused")
os.environ.setdefault("SITE_NAME", "TheFAB")

import app as flask_app

client = flask_app.app.test_client()
flask_app.app.config["SERVER_NAME"] = None

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "..", "docs")


def clean_docs():
    if os.path.exists(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(DOCS)


def copy_static():
    src = os.path.join(ROOT, "static")
    dst = os.path.join(DOCS, "static")
    shutil.copytree(src, dst)


def fix_html(html: str, depth: int = 0) -> str:
    """
    Convert Flask/absolute paths to relative paths suitable for a static site.
    depth=0 means the file is at the root of docs/.
    """
    prefix = "../" * depth

    # Static assets: /static/... → (prefix)static/...
    html = re.sub(r'(href|src)="/static/', rf'\1="{prefix}static/', html)

    # Internal page links
    replacements = {
        'href="/"':            f'href="{prefix}index.html"',
        'href="/about"':       f'href="{prefix}about.html"',
        'href="/gear"':        f'href="{prefix}gear.html"',
        'href="/music"':       f'href="{prefix}music.html"',
        'href="/cooking"':     f'href="{prefix}cooking.html"',
        'href="/downloads"':   f'href="{prefix}downloads.html"',
        # Forms and admin are non-functional in static preview; disable gracefully
        'action="/downloads"': 'action="#"',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    return html


def render_page(route: str, filename: str, depth: int = 0,
                method: str = "GET", cookie_jar=None):
    """Render a Flask route and save the fixed HTML to docs/."""
    with flask_app.app.test_client() as c:
        if cookie_jar:
            for name, value in cookie_jar.items():
                c.set_cookie(name, value)
        response = c.open(route, method=method)

    html = response.data.decode("utf-8")
    html = fix_html(html, depth=depth)

    # Add a small static-preview notice banner
    notice = """
<div style="
  position:fixed; bottom:16px; right:16px; z-index:9999;
  background:#1a6bff; color:#fff; padding:10px 16px;
  border-radius:6px; font-family:monospace; font-size:12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.5); max-width:240px;
  line-height:1.4;
">
  👁 Frontend preview only<br>
  <span style="opacity:0.8;">Forms &amp; downloads disabled</span>
</div>
"""
    html = html.replace("</body>", notice + "\n</body>")

    out_dir = os.path.join(DOCS, os.path.dirname(filename))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(DOCS, filename), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ok  {filename}")


def build():
    print("Building static preview -> docs/")
    clean_docs()
    copy_static()

    # Public pages
    render_page("/",          "index.html")
    render_page("/about",     "about.html")
    render_page("/gear",      "gear.html")
    render_page("/music",     "music.html")
    render_page("/cooking",   "cooking.html")

    # Downloads -- soft gate (no cookie present = locked buttons + unlock modal)
    render_page("/downloads", "downloads.html")

    print("\nDone. Push the docs/ folder and enable GitHub Pages.")


if __name__ == "__main__":
    build()

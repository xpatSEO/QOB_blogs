#!/usr/bin/env python3
"""Map articles from JSON export to a Webflow blog CSV import.

Output columns match the existing Webflow CSV:
Meta Title, Slug, Collection ID, Locale ID, Item ID, Archived, Draft,
Created On, Updated On, Published On, H1, Meta Description, Cover,
Keypoints, Content, Category, Reading Time, Article Author, Article date
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE_JSON = ROOT / "qpbra_articles-export-2026-05-04.json"
TEMPLATE_CSV = ROOT / "Qobra website - Blogs - 6638a00ea9dd4a19035f607c.csv"
OUTPUT_CSV = ROOT / "qobra-blogs-new.csv"

COLLECTION_ID = "6638a00ea9dd4a19035f607c"
LOCALE_ID = "6603f4e90d5af57f5cd72ada"

WEBFLOW_DATE_FMT = "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)"


def fmt_webflow_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return dt.strftime(WEBFLOW_DATE_FMT)


def clean_content_html(html: str) -> str:
    """Remove editor-only blocks (video placeholders, suggestion widgets)
    and collapse whitespace, while keeping the article HTML intact."""
    # Drop video-placeholder editor widgets (entire div + nested content).
    html = re.sub(
        r'<div\s+class="video-placeholder[^"]*"[\s\S]*?</div>\s*</div>\s*</div>',
        "",
        html,
    )
    # Fallback: any remaining stand-alone video-placeholder wrappers.
    html = re.sub(
        r'<div\s+class="video-placeholder[^"]*"[\s\S]*?</div>',
        "",
        html,
    )
    # Collapse runs of whitespace between tags.
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def extract_keypoints(html: str, max_points: int = 5) -> str:
    """Build a Webflow Keypoints <ol> by taking the first sentence of each
    of the first N <h2> sections of the article."""
    section_re = re.compile(
        r"<h2[^>]*>.*?</h2>\s*(<p[^>]*>(.*?)</p>)",
        re.DOTALL | re.IGNORECASE,
    )
    points: list[str] = []
    for match in section_re.finditer(html):
        para = match.group(2)
        # Strip inline tags but keep text.
        text = re.sub(r"<[^>]+>", "", para).strip()
        # Take the first sentence (split on . ! ? followed by space/end).
        sentence_match = re.match(r"(.+?[\.!?])(\s|$)", text, re.DOTALL)
        sentence = sentence_match.group(1).strip() if sentence_match else text
        if sentence:
            points.append(sentence)
        if len(points) >= max_points:
            break

    if not points:
        return ""

    items = "".join(f'<li id="">{p}</li>' for p in points)
    return f'<ol id="">{items}</ol>'


def reading_time(word_count: int) -> str:
    return str(max(1, round(word_count / 200)))


def map_article(art: dict) -> dict:
    created = fmt_webflow_date(art["created_at"])
    updated = fmt_webflow_date(art["updated_at"])
    content = clean_content_html(art["content_html"])
    keypoints = extract_keypoints(art["content_html"])

    return {
        "Meta Title": art.get("metatitle") or art["title"],
        "Slug": art["slug"],
        "Collection ID": COLLECTION_ID,
        "Locale ID": LOCALE_ID,
        "Item ID": "",
        "Archived": "false",
        "Draft": "true",
        "Created On": created,
        "Updated On": updated,
        "Published On": "",
        "H1": art["title"],
        "Meta Description": art.get("metadescription", ""),
        "Cover": "",
        "Keypoints": keypoints,
        "Content": content,
        "Category": "",
        "Reading Time": reading_time(art.get("word_count", 0)),
        "Article Author": "",
        "Article date": "",
    }


def main() -> None:
    with TEMPLATE_CSV.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))

    articles = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    rows = [map_article(a) for a in articles]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV.name}")


if __name__ == "__main__":
    main()

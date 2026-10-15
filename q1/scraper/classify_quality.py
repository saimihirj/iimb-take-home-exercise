#!/usr/bin/env python3
"""
Adds two audit columns to q1/manifest.csv for every saved HTML file:

    visible_text_chars   number of characters of human-visible text in the saved HTML
    content_quality      one of
        content         a normal page with readable text (300 or more visible characters)
        js_shell        a client-side rendered app. The HTML is a script shell, so the text is not in the raw file
        redirect_stub   a meta-refresh or JavaScript redirect page
        server_default  a web-server placeholder such as "IIS Windows Server" or "Welcome to nginx"
        moved_notice    a "we have moved" notice page
        near_empty      under 300 characters of text and none of the patterns above

These pages are faithful copies of what the site served on that date. They are NOT download errors. The label lets a
researcher filter them out before text analysis. Run:  python3 q1/scraper/classify_quality.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.csv"

STRIP = re.compile(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>|<!--.*?-->|<[^>]+>", re.S | re.I)


def classify(html):
    text = re.sub(r"\s+", " ", STRIP.sub(" ", html)).strip()
    n = len(text)
    low = html.lower()
    if n >= 300:
        return n, "content"
    if re.search(r'http-equiv\s*=\s*["\']?refresh', low) or re.search(r"window\.location|location\.replace", low) and n < 150:
        return n, "redirect_stub"
    if re.search(r"iis windows server|welcome to nginx|apache2 (ubuntu )?default|default web site page|index of /", low):
        return n, "server_default"
    if re.search(r"we[''’]?ve moved|we have moved|has moved|site has moved", low):
        return n, "moved_notice"
    if re.search(r'id=["\'](root|__next|app)["\']|/_next/static|<app-root|ng-version', low):
        return n, "js_shell"
    return n, "near_empty"


def main():
    m = pd.read_csv(MANIFEST, dtype=str).fillna("")
    for c in ("visible_text_chars", "content_quality"):
        if c in m.columns:
            m = m.drop(columns=c)
    chars, quality = [], []
    for f in m["file"]:
        p = ROOT / f if f else None
        if p is not None and p.is_file():
            n, q = classify(p.read_text(errors="ignore"))
            chars.append(n)
            quality.append(q)
        else:
            chars.append("")
            quality.append("")
    m["visible_text_chars"] = chars
    m["content_quality"] = quality
    m.to_csv(MANIFEST, index=False)
    print(m[m.content_quality != ""].groupby(["page_type", "content_quality"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()

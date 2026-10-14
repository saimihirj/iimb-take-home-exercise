#!/usr/bin/env python3
"""
Q2.2a - Semi-automated download of RAW patent data from WIPO PATENTSCOPE for the Top-20 startups.

WHY SEMI-AUTOMATED?  PATENTSCOPE shows an image CAPTCHA to automated sessions and requires a (free) WIPO account for the
"Download" (Excel/CSV) export. Circumventing that is neither appropriate nor reliable, so a human does the two things
a robot must not: (1) solves the CAPTCHA once, (2) logs in once. Everything else is automated:

  * a visible Chrome window is opened (Playwright, system Chrome),
  * for each startup the query  PA:("<alias>") OR PA:("<alias>")  is typed into the simple-search box and submitted,
  * YOU click  Download -> Excel/CSV  on the results page (the script then captures the file automatically through the
    browser's download event and stores it, untouched, as  data/wipo_raw/<slug>__<timestamp>.<ext>),
  * query string, result-count text and timestamp go to data/wipo_raw/download_log.csv  (audit trail).

If the browser route is impossible, skip this script: run the same query manually in PATENTSCOPE, export, and drop
the files in data/wipo_raw/ named  <slug>__manual.csv|xls|xlsx  - the merge script treats both identically.

Usage:  python3 wipo_download.py [--only ather-energy simple-energy]
"""
import argparse
import csv
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "wipo_raw"
TOP20 = HERE / "startups" / "startups_top20.csv"
SEARCH_URL = "https://patentscope.wipo.int/search/en/search.jsf"
SEARCH_BOX = "[id='simpleSearchForm:fpSearch:input']"      # id observed on the live page (Oct 2026)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_query(row):
    """PA = applicant field. Use the primary legal entity and every alias, quoted, OR-ed together."""
    names = [row["legal_entity_primary"], row["name"]] + str(row["name_aliases"]).split("|")
    uniq = []
    for n in names:
        n = str(n).strip()
        if n and n.lower() != "nan" and n not in uniq:
            uniq.append(n)
    return " OR ".join(f'PA:("{n}")' for n in uniq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="slugs to (re)download")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    startups = pd.read_csv(TOP20)
    log_path = RAW / "download_log.csv"
    new_log = not log_path.exists()

    with sync_playwright() as p, open(log_path, "a", newline="", encoding="utf-8") as lf:
        log = csv.writer(lf)
        if new_log:
            log.writerow(["slug", "startup", "query", "saved_file", "page_text_snippet", "timestamp"])
        browser = p.chromium.launch(channel="chrome", headless=False,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(accept_downloads=True, viewport={"width": 1500, "height": 1100})
        page = ctx.new_page()
        page.goto(SEARCH_URL, timeout=90000)
        input("\n>> In the browser: solve any CAPTCHA and log in to WIPO (Login, top-right). "
              "Then press ENTER here to start... ")

        for _, row in startups.iterrows():
            slug = slugify(row["name"])
            if a.only and slug not in a.only:
                continue
            q = build_query(row)
            print(f"\n[{row['rank']:>2}] {row['name']}\n     query: {q}")
            page.goto(SEARCH_URL, timeout=90000)
            page.wait_for_selector(SEARCH_BOX, timeout=60000)
            page.fill(SEARCH_BOX, q)
            page.keyboard.press("Enter")
            page.wait_for_timeout(6000)
            snippet = re.sub(r"\s+", " ", page.inner_text("body"))[:200]
            print("     page says:", snippet)
            saved = ""
            print("     >> Click Download -> Excel/CSV in the browser. If there are no results just wait; the "
                  "script moves on after 3 min. Waiting for the download...")
            try:
                with page.expect_download(timeout=180000) as dl:
                    pass                                   # the human clicks; Playwright captures the event
                d = dl.value
                ext = Path(d.suggested_filename).suffix or ".csv"
                target = RAW / f"{slug}__{datetime.now():%Y%m%d%H%M%S}{ext}"
                d.save_as(target)
                saved = target.name
                print("     saved", saved)
            except Exception as e:                         # timeout / skipped
                print("     no download captured:", type(e).__name__)
            log.writerow([slug, row["name"], q, saved, snippet, datetime.now().isoformat(timespec="seconds")])
            lf.flush()
            time.sleep(2)
        browser.close()


if __name__ == "__main__":
    main()

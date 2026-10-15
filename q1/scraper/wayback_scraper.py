#!/usr/bin/env python3
"""
Question 1.2: Automated collection of homepage and about page HTML files for the top 20 incubators.

The scraper collects two distinct data streams.
First, it retrieves current web pages through live HTTP requests.
Second, it collects historical captures from the Internet Archive Wayback Machine.
The collection captures the earliest successful HTTP 200 HTML snapshot in each calendar month.
The archival timeline extends from January 2022 through September 2026.

Design Summary
1. The script reads the top 20 incubator list from the ranking dataset.
2. For homepages, the script submits monthly CDX queries for root domain records.
3. For about pages, the script detects candidate paths across live links, archival captures, and common URL patterns.
4. The candidate path with the highest temporal coverage is selected for each monthly period.
5. Snapshot downloads retrieve raw original bytes using the raw capture format.
6. Execution logs capture every monthly interval in manifest.csv, including historical snapshot gaps.

Usage:
    python3 wayback_scraper.py
    python3 wayback_scraper.py --sites NSRCEL SINE
    python3 wayback_scraper.py --skip-live
    python3 wayback_scraper.py --start 2022-01 --end 2026-09
"""
import argparse
import csv
import hashlib
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "scraped_html"                       # deliverable: the scraped HTML files
RANKING_CSV = HERE.parent / "incubator_ranking" / "incubators_ranked.csv"
MANIFEST = HERE.parent / "manifest.csv"                  # one row per (site, page, month)

CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_RAW = "https://web.archive.org/web/{ts}id_/{url}"
UA = "Mozilla/5.0 (compatible; IIMB-research-scraper/1.0; academic take-home; +mailto:researcher@example.com)"
DEFAULT_START, DEFAULT_END = "2022-01", "2026-09"

# Generic about-page URL patterns tried in addition to the links discovered on the homepages.
ABOUT_PATTERNS = ["/about", "/about-us", "/aboutus", "/about-us/", "/about/", "/about.html", "/about-us.html",
                  "/who-we-are", "/about-us.php", "/about.php"]
MAX_ABOUT_CANDIDATES = 16        # cap CDX calls per site
WORKERS = 4                      # parallel download threads
MIN_INTERVAL = 0.6               # global seconds between ANY two requests to archive.org (politeness / avoids 429)
MIN_BYTES_OK = 500               # smaller bodies are flagged as suspicious ("tiny_body")

session = requests.Session()
session.headers.update({"User-Agent": UA})

# ----------------------------------------------------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------------------------------------------------
_rate_lock = threading.Lock()
_last_call = [0.0]


def polite_get(url, params=None, timeout=60, retries=5, stream=False):
    """GET with a global rate limit and exponential back-off on 429 / 5xx / network errors. Returns Response or None."""
    for attempt in range(retries):
        with _rate_lock:                                   # enforce a global minimum spacing between requests
            wait = MIN_INTERVAL - (time.time() - _last_call[0])
            if wait > 0:
                time.sleep(wait)
            _last_call[0] = time.time()
        try:
            r = session.get(url, params=params, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r
            if r.status_code in (404, 403, 410):           # definitive: do not retry
                return r
            # 429 / 5xx -> back off
        except requests.RequestException:
            pass
        time.sleep(min(60, 2 ** attempt * 3))
    return None


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def month_range(start, end):
    """Yield 'YYYY-MM' strings from start to end inclusive."""
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def normalise_site(website):
    """'www.foo.org/' -> ('https://foo.org/', 'foo.org')."""
    w = website.strip()
    if not w.startswith("http"):
        w = "https://" + w
    p = urlparse(w)
    return f"{p.scheme}://{p.netloc}/", p.netloc.lower().removeprefix("www.")


# ----------------------------------------------------------------------------------------------------------------------
# Wayback CDX
# ----------------------------------------------------------------------------------------------------------------------
def cdx_monthly(url, start, end):
    """
    Return {YYYY-MM: (timestamp, original_url)} - the EARLIEST HTTP-200 text/html capture for each month.
    Wayback's CDX index is sorted by time, and `collapse=timestamp:6` collapses adjacent rows with an identical
    first-6 digits (YYYYMM), keeping the first one => earliest capture per month.
    `url` is canonicalised by Wayback (scheme / www / trailing slash differences are merged).
    """
    params = {
        "url": url, "from": start.replace("-", ""), "to": end.replace("-", "") + "31",
        "output": "json", "fl": "timestamp,original,statuscode,mimetype",
        "filter": ["statuscode:200", "mimetype:text/html"], "collapse": "timestamp:6",
    }
    r = polite_get(CDX, params=params, timeout=120)
    if r is None or r.status_code != 200 or not r.text.strip():
        return {}
    try:
        rows = r.json()[1:]                                # first row is the header
    except ValueError:
        return {}
    return {f"{row[0][:4]}-{row[0][4:6]}": (row[0], row[1]) for row in rows}


# ----------------------------------------------------------------------------------------------------------------------
# About-page discovery
# ----------------------------------------------------------------------------------------------------------------------
ABOUT_RE = re.compile(r"about|who[\s-]?we[\s-]?are|our[\s-]?story", re.I)

# A real About page has an "about"-style word as the LAST path segment (tier 2, e.g. /about-us/) or as the FIRST segment
# of a short path (tier 1, e.g. /about/awards). Anything else is rejected. This stops blog posts whose slug merely
# contains the word "about" (for example /news/about-38-of-startups-run-out-of-funds) from being scraped as About pages.
_ABOUT_WORDS = re.compile(r"^(about|about-us|aboutus|about_us|aboutme|who-we-are|whoweare|our-story|about-[a-z0-9]{2,20}|"
                          r"about(-us)?\.(php|html?|aspx))$", re.I)


def about_tier(url):
    """2 = canonical About URL, 1 = page under an /about/ section, 0 = not an About page (homepage, blog post, etc.)."""
    segs = [s for s in urlparse(url).path.split("/") if s]
    if not segs:
        return 0                                  # the bare homepage is never an About page
    if _ABOUT_WORDS.match(segs[-1]):
        return 2
    if len(segs) <= 3 and _ABOUT_WORDS.match(segs[0]):
        return 1
    return 0


def extract_about_links(html, base_url):
    """Return same-site URLs from <a> tags whose text or href looks like an 'about us' link (best matches first)."""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).netloc.lower().removeprefix("www.")
    scored = []
    for a in soup.find_all("a", href=True):
        href, text = a["href"].strip(), a.get_text(" ", strip=True)
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if not (ABOUT_RE.search(text) or ABOUT_RE.search(href)):
            continue
        full = urljoin(base_url, href).split("#")[0]
        # strip the Wayback prefix if the page came from the archive
        full = re.sub(r"^https?://web\.archive\.org/web/\d+[a-z_]*/", "", full)
        if urlparse(full).netloc.lower().removeprefix("www.") != host:
            continue
        score = 0 if re.fullmatch(r"(about( us)?|about [a-z0-9 .\-]{1,25})", text.strip().lower()) else 1
        scored.append((score, len(full), full))
    seen, out = set(), []
    for _, _, u in sorted(scored):
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:4]


def cdx_about_urls(home_url, start, end, limit=6):
    """
    Archive-side discovery that works even for JS-rendered sites with no <a> tags in the HTML: ask the CDX index for
    every distinct HTTP-200 HTML URL on the host whose address contains 'about' / 'who-we-are' in the window, and keep
    the shortest few (shallow paths such as /about-us beat /about-us/team/john).
    """
    host = urlparse(home_url).netloc
    params = {"url": host + "/*", "from": start.replace("-", ""), "to": end.replace("-", "") + "31",
              "output": "json", "fl": "original", "collapse": "urlkey", "limit": 400,
              "filter": ["statuscode:200", "mimetype:text/html", "original:(?i).*(about|who-we-are).*"]}
    r = polite_get(CDX, params=params, timeout=120)
    if r is None or r.status_code != 200 or not r.text.strip():
        return []
    try:
        urls = [row[0] for row in r.json()[1:]]
    except ValueError:
        return []
    urls = [u for u in urls if not re.search(r"\.(pdf|jpg|png|css|js)(\?|$)", u, re.I) and "?" not in u
            and about_tier(u) > 0]                 # drop blog posts etc. whose slug merely contains "about"
    urls.sort(key=lambda u: (urlparse(u).path.rstrip("/").count("/"), len(u)))
    return urls[:limit]


def discover_about_candidates(home_url, live_html, home_snaps, start=DEFAULT_START, end=DEFAULT_END):
    """Candidate about URLs = links on live homepage + links on one archived homepage per year + CDX discovery
    + generic patterns."""
    cands = []
    if live_html:
        cands += extract_about_links(live_html, home_url)
    by_year = {}
    for ym, (ts, orig) in sorted(home_snaps.items()):      # first archived homepage of every year
        by_year.setdefault(ym[:4], (ts, orig))
    for ts, orig in by_year.values():
        r = polite_get(WAYBACK_RAW.format(ts=ts, url=orig))
        if r is not None and r.status_code == 200:
            cands += extract_about_links(r.text, orig)
    cands += cdx_about_urls(home_url, start, end)
    base = home_url.rstrip("/")
    cands += [base + p for p in ABOUT_PATTERNS]
    seen, out = set(), []
    for c in cands:                                        # de-duplicate on host+path (ignore scheme/www/slash)
        k = urlparse(c).netloc.removeprefix("www.") + urlparse(c).path.rstrip("/").lower()
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out[:MAX_ABOUT_CANDIDATES]


def pick_about_per_month(cand_maps, months):
    """
    cand_maps: {candidate_url: {month: (ts, orig)}}.
    Candidates that are not real About pages (about_tier == 0) are dropped. Per month the script then prefers a canonical
    About URL (tier 2) over a sub-page (tier 1), then the candidate with the highest overall coverage (consistency across
    time), then the earliest timestamp. A month with no valid candidate is recorded as a gap instead of a wrong page.
    """
    cand_maps = {c: m for c, m in cand_maps.items() if about_tier(c) > 0}
    coverage = {c: len(m) for c, m in cand_maps.items()}
    chosen = {}
    for ym in months:
        options = [(-about_tier(c), -coverage[c], m[ym][0], c) for c, m in cand_maps.items() if ym in m]
        if options:
            _, _, ts, c = min(options)
            chosen[ym] = (ts, cand_maps[c][ym][1], c)
    return chosen



# ----------------------------------------------------------------------------------------------------------------------
# Download + manifest
# ----------------------------------------------------------------------------------------------------------------------
MANIFEST_FIELDS = ["site", "slug", "page_type", "source", "month", "snapshot_timestamp", "original_url",
                   "fetch_url", "status", "bytes", "sha256", "file", "note", "fetched_at_utc"]
manifest_lock = threading.Lock()
rows_out = []


def save_html(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return len(content), hashlib.sha256(content).hexdigest()


def download_archived(job):
    """Download one archived snapshot (resumable). Returns a manifest row dict."""
    site, slug, ptype, ym, ts, orig = job
    fname = OUT / slug / ptype / f"{ym}_{ts}.html"
    row = dict(site=site, slug=slug, page_type=ptype, source="wayback", month=ym, snapshot_timestamp=ts,
               original_url=orig, fetch_url=WAYBACK_RAW.format(ts=ts, url=orig), status="", bytes="", sha256="",
               file=str(fname.relative_to(HERE.parent)), note="",
               fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if fname.exists() and fname.stat().st_size > 0:        # resume support
        b = fname.read_bytes()
        row.update(status="ok_cached", bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
        return row
    r = polite_get(row["fetch_url"], timeout=90)
    if r is None or r.status_code != 200:
        row.update(status="download_failed", file="", note=f"http={getattr(r, 'status_code', 'none')}")
        return row
    n, h = save_html(fname, r.content)
    row.update(status="ok", bytes=n, sha256=h, note="tiny_body" if n < MIN_BYTES_OK else "")
    return row


def fetch_live(site, slug, home_url, about_candidates):
    """Fetch CURRENT homepage and about page (first live candidate that returns 200). Returns (rows, live_home_html)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows, home_html = [], None
    for ptype, urls in (("home", [home_url, home_url.replace("https://", "https://www.")]), ("about", about_candidates)):
        done = False
        for u in urls:
            r = polite_get(u, timeout=30, retries=2)
            if r is not None and r.status_code == 200 and "html" in r.headers.get("content-type", "").lower():
                fname = OUT / slug / ptype / f"LIVE_{today}.html"
                n, h = save_html(fname, r.content)
                rows.append(dict(site=site, slug=slug, page_type=ptype, source="live", month=today[:7],
                                 snapshot_timestamp=today, original_url=u, fetch_url=r.url, status="ok", bytes=n,
                                 sha256=h, file=str(fname.relative_to(HERE.parent)),
                                 note="redirected" if r.url.rstrip("/") != u.rstrip("/") else "",
                                 fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds")))
                if ptype == "home":
                    home_html = r.text
                done = True
                break
        if not done:
            rows.append(dict(site=site, slug=slug, page_type=ptype, source="live", month=today[:7],
                             snapshot_timestamp=today, original_url=urls[0] if urls else "", fetch_url="",
                             status="live_unavailable", bytes="", sha256="", file="", note="no 200 HTML response",
                             fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return rows, home_html


# ----------------------------------------------------------------------------------------------------------------------
# Main per-site pipeline
# ----------------------------------------------------------------------------------------------------------------------
def process_site(name, website, start, end, skip_live):
    slug = slugify(name)
    home_url, _ = normalise_site(website)
    months = list(month_range(start, end))
    print(f"\n=== {name}  ({home_url}) ===", flush=True)

    # (a) homepage snapshots per month
    home_snaps = cdx_monthly(home_url, start, end)
    print(f"  homepage months with snapshot: {len(home_snaps)}/{len(months)}", flush=True)

    # (b) live fetch (also gives the live homepage HTML for about-link discovery)
    live_rows, live_html = ([], None)
    if not skip_live:
        # about candidates for the live fetch: generic patterns first (the live homepage is not yet parsed)
        live_rows, live_html = fetch_live(site=name, slug=slug, home_url=home_url, about_candidates=[])
        if live_html:
            live_about = extract_about_links(live_html, home_url) + [home_url.rstrip("/") + p for p in ABOUT_PATTERNS]
            about_live_rows, _ = fetch_live(name, slug, home_url, live_about)
            live_rows = [r for r in live_rows if r["page_type"] == "home"] + \
                        [r for r in about_live_rows if r["page_type"] == "about"]
        else:
            live_rows = [r for r in live_rows if r["page_type"] == "home"] + [
                dict(site=name, slug=slug, page_type="about", source="live", month="", snapshot_timestamp="",
                     original_url="", fetch_url="", status="live_unavailable", bytes="", sha256="", file="",
                     note="homepage not reachable", fetched_at_utc="")]

    # (c) about-page discovery + monthly CDX per candidate
    candidates = discover_about_candidates(home_url, live_html, home_snaps, start, end)
    print(f"  about candidates: {len(candidates)}", flush=True)
    cand_maps = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:    # CDX is slow (tens of seconds) -> query in parallel
        for c, m in zip(candidates, ex.map(lambda u: cdx_monthly(u, start, end), candidates)):
            if m:
                cand_maps[c] = m
    about_choice = pick_about_per_month(cand_maps, months)
    print(f"  about months with snapshot: {len(about_choice)}/{len(months)}", flush=True)

    # (d) build jobs (+ explicit 'missing' rows so gaps are documented)
    jobs, rows = [], list(live_rows)
    for ym in months:
        if ym in home_snaps:
            ts, orig = home_snaps[ym]
            jobs.append((name, slug, "home", ym, ts, orig))
        else:
            rows.append(dict(site=name, slug=slug, page_type="home", source="wayback", month=ym, status="no_snapshot",
                             snapshot_timestamp="", original_url=home_url, fetch_url="", bytes="", sha256="", file="",
                             note="no HTTP-200 capture in this month", fetched_at_utc=""))
        if ym in about_choice:
            ts, orig, _ = about_choice[ym]
            jobs.append((name, slug, "about", ym, ts, orig))
        else:
            rows.append(dict(site=name, slug=slug, page_type="about", source="wayback", month=ym, status="no_snapshot",
                             snapshot_timestamp="", original_url="", fetch_url="", bytes="", sha256="", file="",
                             note="no HTTP-200 capture of any about-URL candidate in this month", fetched_at_utc=""))

    # (e) download in parallel (global rate limiter keeps us polite)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, row in enumerate(ex.map(download_archived, jobs), 1):
            rows.append(row)
            if i % 25 == 0:
                print(f"  downloaded {i}/{len(jobs)}", flush=True)
    return rows


def write_manifest(rows):
    rows.sort(key=lambda r: (r["site"], r["page_type"], r["source"], r["month"]))
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)


def load_sites(limit_names):
    with open(RANKING_CSV, newline="", encoding="utf-8") as f:
        top = [r for r in csv.DictReader(f) if r["in_top20"] == "True"]
    top.sort(key=lambda r: int(r["final_rank"]))
    if limit_names:
        wanted = [slugify(x) for x in limit_names]
        top = [r for r in top if any(w in slugify(r["name"]) for w in wanted)]
    return [(r["name"], r["website"]) for r in top]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", nargs="*", help="substring(s) of incubator names to run (default: all top-20)")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--skip-live", action="store_true")
    a = ap.parse_args()

    sites = load_sites(a.sites)
    if not sites:
        sys.exit("No matching sites.")
    # keep rows from previous partial runs for sites we are not re-running
    all_rows = []
    if MANIFEST.exists() and a.sites:
        with open(MANIFEST, newline="", encoding="utf-8") as f:
            running = {n for n, _ in sites}
            all_rows = [r for r in csv.DictReader(f) if r["site"] not in running]
    for name, website in sites:
        all_rows += process_site(name, website, a.start, a.end, a.skip_live)
        write_manifest(all_rows)                           # checkpoint after each site
    ok = sum(r["status"].startswith("ok") for r in all_rows)
    print(f"\nDone. {ok} files saved; manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()

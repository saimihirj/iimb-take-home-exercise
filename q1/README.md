# Question 1 – Indian startup incubators: ranking + Wayback scraper

```
q1/
├── incubator_ranking/        Q1.1  search method, ranking, spreadsheet
│   ├── METHODOLOGY.md        search methodology + ranking justification  (deliverables 1 & 2)
│   ├── candidate_pool.csv    hand-curated inputs (24 candidates, with sources/confidence)
│   ├── build_ranking.py      computes both rankings + Top-20
│   ├── incubators_top20.xlsx basic incubator details (deliverable 3)
│   └── incubators_ranked.csv same, flat
├── scraper/
│   ├── wayback_scraper.py    Q1.2  annotated Python 3 scraper
│   └── preflight_check.py    optional: live/archived reachability report for every site
├── scraped_html/<incubator>/{home,about}/YYYY-MM_<timestamp>.html   +  LIVE_<date>.html
├── manifest.csv              one row per (incubator, page, month): what was fetched, or why not
└── coverage_summary.csv      months-covered per incubator/page (generated)
```

## 1. What the scraper does
For each of the Top-20 incubators it collects the **home page** and **about-us page** in two forms:

| Form | How |
|---|---|
| **Current** | live HTTP fetch on the day of the run (`LIVE_<date>.html`) |
| **Archived** | Internet Archive Wayback Machine – the **earliest HTTP-200 HTML snapshot in each calendar month, Jan-2022 → Sep-2026 (57 months)** |

### Pipeline (see the docstrings in `wayback_scraper.py`)
1. **Site list** – read from `incubator_ranking/incubators_ranked.csv` (`in_top20 == True`).
2. **Homepage snapshots** – one CDX-API call per site: `filter=statuscode:200`, `mimetype:text/html`, `collapse=timestamp:6`. Because the CDX index is time-ordered and `collapse=timestamp:6` keeps the first row of every `YYYYMM`, the result is *exactly* "earliest available page each month". Wayback canonicalises `http/https`, `www`, trailing slash, so variants are merged.
3. **About-page discovery** (URLs differ between sites and change over time):
   a. anchor tags whose text/href contain *about / who we are / our story* on the live homepage **and** on one archived homepage per year;
   b. CDX discovery (`host/*` with `original:.*(about|who-we-are).*`) – works for JS-rendered sites with no static links;
   c. generic patterns (`/about`, `/about-us`, `/aboutus`, `/about.html`, `/who-we-are` …).
   Each candidate gets the same monthly CDX query. **Per month** the candidate with the greatest overall time-coverage is chosen (keeps the series consistent), taking its earliest capture that month.
4. **Download** raw bytes with the `…/web/<ts>id_/<url>` form (original HTML, no Wayback toolbar/URL rewriting).
5. **Manifest** – every cell of the 57-month × 2-page × 20-site grid is logged, including `no_snapshot` months. Gaps are data, not errors.
6. **Politeness / robustness** – global rate limit (0.6 s between requests, 4 worker threads), exponential back-off on 429/5xx, resumable (existing files skipped), checkpoint of the manifest after every site.

## 2. Running it
```bash
pip install requests beautifulsoup4 pandas openpyxl
cd q1/scraper
python3 wayback_scraper.py                       # all 20 sites (≈ 1–1.5 h; needs internet)
python3 wayback_scraper.py --sites SINE NSRCEL   # subset
python3 wayback_scraper.py --skip-live --start 2022-01 --end 2026-09
python3 preflight_check.py                       # optional diagnostics
```
Python ≥ 3.9. No API key needed.

## 3. Manifest columns
`site, slug, page_type (home|about), source (wayback|live), month, snapshot_timestamp, original_url, fetch_url, status, bytes, sha256, file, note, fetched_at_utc`
`status`: `ok`, `ok_cached` (already on disk), `no_snapshot` (nothing archived that month), `download_failed`, `live_unavailable`. `note=tiny_body` flags <500-byte files (often JS shells or error pages – inspect before analysing).

## 4. Assumptions, caveats
* "Earliest available page every month" = earliest **HTTP-200 text/html** capture; redirects (3xx) and error captures are ignored so every file is real content.
* The Wayback timestamp can differ from the month's first day by weeks; the exact timestamp is in the file name and manifest.
* "About page" is a best-effort identification; the chosen URL for each month is in `manifest.csv` (`original_url`) – audit it. Sites may restructure; the series then switches URL where the old one is no longer captured.
* Many modern sites are JS-rendered; raw HTML then contains little visible text (check `bytes` and `tiny_body`). A headless-browser re-render is out of scope.
* Some sites are unreachable live from some networks (e.g. CIIE, IISc SID, IIT Mandi Catalyst failed in the pre-flight test on 14-Oct-2026); this is recorded as `live_unavailable`, archive series is unaffected.
* Archived snapshots are third-party copies; embedded images/CSS are **not** downloaded (HTML only, as specified).
* Use for research under the Internet Archive's terms; identifying `User-Agent` set (edit the contact e-mail in `UA`).

# Question 1: Indian Startup Incubators Ranking and Wayback Scraper

```
q1/
├── incubator_ranking/        Q1.1 search method, ranking, and spreadsheet
│   ├── METHODOLOGY.md        Search methodology and ranking justification
│   ├── candidate_pool.csv    Curated inputs with sources and confidence levels
│   ├── build_ranking.py      Script computing both rankings and the Top 20
│   ├── incubators_top20.xlsx Multi-sheet spreadsheet with basic incubator details
│   └── incubators_ranked.csv Flat CSV containing all ranked candidates
├── scraper/
│   ├── wayback_scraper.py    Annotated Python 3 scraper
│   ├── preflight_check.py    Live and archive reachability test script
│   ├── classify_quality.py   Labels each saved file as content, js_shell, redirect_stub and so on
│   └── build_coverage.py     Rebuilds coverage_summary.csv from the manifest
├── scraped_html/             Directory storing downloaded HTML snapshots
│   └── <incubator>/
│       ├── home/             Monthly snapshots and live homepage captures
│       └── about/            Monthly snapshots and live about page captures
├── manifest.csv              Record tracking all requested snapshots and gaps
└── coverage_summary.csv      Summary of months covered per incubator and page
```

## 1. Scope of the Scraper

The scraping pipeline collects the homepage and about page for each of the top 20 incubators in two formats.

| Format | Collection Mechanism |
|---|---|
| Current Website | Live HTTP fetch retrieved on the execution date and saved as `LIVE_<date>.html`. |
| Archived Website | Earliest successful HTTP 200 HTML snapshot per calendar month from the Internet Archive Wayback Machine. The collection period covers January 2022 to September 2026, totaling 57 calendar months. |

### Execution Pipeline

1. **Target site loading**. The script reads the top 20 incubator records from `incubator_ranking/incubators_ranked.csv`.
2. **Homepage snapshot resolution**. The script queries the Wayback CDX API for the root domain. It filters specifically for HTTP 200 responses with HTML MIME types. The parameter `collapse=timestamp:6` collapses all records within a given month into the first capture. This step reliably yields the earliest available capture in each monthly interval. The Wayback CDX index automatically normalizes protocol, subdomain, and path variations.
3. **About page URL discovery**. About page URLs vary widely across organizations and shift during website redesigns. The script identifies valid target URLs through three coordinated methods.
   * First, it parses anchor tags containing text or path tokens like "about", "who we are", or "our story" on live homepages and annual snapshots.
   * Second, it queries the CDX index directly for URL paths containing "about" tokens. This handles client-rendered pages that lack static links in their raw HTML. Results pass the strict About-URL rule in section 4.
   * Third, it tests common URL structures such as `/about`, `/about-us`, and `/who-we-are`.
   For each monthly period, the script prefers a canonical About URL over a sub-page, then the candidate with the greatest multi-year coverage. This logic maintains continuity across the historical archive.
4. **Clean content download**. Snapshots are requested using the raw capture format with the `id_` modifier. This retrieves the original web page without the Wayback navigation header or rewritten URLs.
5. **Manifest audit trail**. Every monthly cell across the 57-month timeline generates a record in `manifest.csv`. Months lacking archived captures are marked explicitly as `no_snapshot`. Gaps are documented clearly for academic reproducibility.
6. **Polite rate limiting and resume capability**. A synchronized rate limiter enforces a minimum 0.6 second pause between outbound requests. Four worker threads process downloads concurrently. Exponential back-off manages temporary server throttling. Existing files on disk are verified and skipped automatically during rerun commands.

## 2. Running the Scraper

The code requires Python 3.9 or newer.

```bash
pip install -r requirements.txt
cd q1/scraper

# Run the complete collection across all 20 incubators
python3 wayback_scraper.py

# Run collection for specific institutions
python3 wayback_scraper.py --sites SINE NSRCEL

# Run collection over a custom date window
python3 wayback_scraper.py --skip-live --start 2022-01 --end 2026-09

# Optional: Run domain diagnostics before scraping
python3 preflight_check.py
```

No external API keys are required.

## 3. Manifest Structure

The output file `manifest.csv` records metadata for every collection target:
`site, slug, page_type, source, month, snapshot_timestamp, original_url, fetch_url, status, bytes, sha256, file, note, fetched_at_utc, visible_text_chars, content_quality`

The `status` field categorizes collection outcomes:
* `ok`. Snapshot downloaded and saved successfully.
* `ok_cached`. File was already present on disk from an earlier run.
* `no_snapshot`. The Wayback Machine contains no valid HTTP 200 HTML capture for that month.
* `download_failed`. The request failed due to a server or network error.
* `live_unavailable`. The live domain was unreachable during real-time retrieval.

Entries with `note=tiny_body` flag files smaller than 500 bytes.

After scraping, run `python3 q1/scraper/classify_quality.py` and then `python3 q1/scraper/build_coverage.py`. The first adds two columns to the manifest. `visible_text_chars` counts the readable text in each file. `content_quality` labels each file as `content`, `js_shell`, `redirect_stub`, `server_default`, `moved_notice`, or `near_empty`. The labelled stub pages are real archived responses. They are not download errors. Filter on `content_quality == "content"` before any text analysis. The second script rebuilds `coverage_summary.csv`.

## 4. Methodological Assumptions and Constraints

* The collection protocol selects the earliest valid HTTP 200 HTML capture in each calendar month. The Wayback CDX filter excludes non-200 responses. A 200 response can still be a redirect page, a server placeholder, or a JavaScript shell. These are kept as archived and labelled in `content_quality`, because they show what the site served on that date.
* Snapshot timestamps reflect crawler visits by the Internet Archive. Visits often occur mid-month rather than on the first calendar day.
* About page identification applies automated discovery rules. A candidate URL is accepted only if its last path segment is an About-style word, such as `/about-us/`, or if it sits directly under an `/about/` section. This filter excludes press releases, news articles, and blog posts whose title slug merely contains the word "about". If no valid About URL exists in the archive for a given month, that month is marked as `no_snapshot` rather than substituting an unrelated page. Users can review the `original_url` column in `manifest.csv` to inspect selected URLs.
* CIIE.CO and KIIT-TBI have no historical About-page captures in the Wayback Machine, and Startup Village has only one. In such cases, the scraper records `no_snapshot` rather than falling back to the homepage.
* Archive coverage is uneven. Many months have no capture, and About pages are archived less often than homepages. `coverage_summary.csv` shows the count per incubator.
* Many modern institutional websites rely on client-side JavaScript rendering. Raw HTML files from these sites contain little text, for example SINE and StartupTN in recent years.
* Real-time website availability depends on local network routing. Certain institutions returned connection failures during live collection tests. These entries are logged as `live_unavailable` without altering historical records.
* The scraper collects HTML documents exclusively. Embedded media, stylesheets, and images are not downloaded.
* The tool identifies itself through a custom User-Agent header with an academic contact address. Users should update the contact email in `wayback_scraper.py` before conducting extended research.

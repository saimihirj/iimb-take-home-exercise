# IIMB Research Associate Take-Home Exercise

This repository contains my submission for the IIM Bangalore Research Associate take-home exercise. The materials are organized into two dedicated folders: `q1/` for Question 1 (incubator ranking and web scraping) and `q2/` for Question 2 (environment startups and WIPO patent analysis).

## Repository Overview

```
.
├── README.md               Project overview and navigation guide
├── requirements.txt        Python dependencies for replication
├── q1/                     Question 1: Incubator ranking and web scraping
│   ├── README.md           Detailed documentation for Question 1
│   ├── incubator_ranking/  Search methodology, ranking code, and workbook
│   │   ├── METHODOLOGY.md  Methodology justification and data notes
│   │   ├── candidate_pool.csv Candidate database with confidence ratings
│   │   ├── build_ranking.py Script computing dual rankings and Top 20
│   │   ├── incubators_top20.xlsx Deliverable spreadsheet
│   │   └── incubators_ranked.csv Full ranked candidate dataset
│   ├── scraper/            Automated collection tools
│   │   ├── wayback_scraper.py Annotated Wayback Machine and live scraper
│   │   ├── preflight_check.py Domain diagnostic script
│   │   ├── classify_quality.py Labels each saved HTML file by content quality
│   │   └── build_coverage.py Rebuilds coverage summary from manifest
│   ├── scraped_html/       Archived and live HTML files (1,265 files)
│   ├── manifest.csv        Audit log tracking all collection requests and quality labels
│   └── coverage_summary.csv Monthly coverage table across all 20 incubators
└── q2/                     Question 2: Environment startups and WIPO patent analysis
    ├── README.md           Detailed documentation for Question 2
    ├── startups/           Identification, funding ranges, and ranking
    │   ├── candidate_pool.csv Candidate pool with funding ranges
    │   ├── rank_startups.py Script evaluating rankings and sensitivity
    │   ├── startups_top20.csv Flat CSV of ranked environment startups
    │   └── startups_top20.xlsx Deliverable spreadsheet
    ├── wipo_download.py    Semi-automated downloader for WIPO PATENTSCOPE
    ├── data/
    │   ├── wipo_raw/       Raw exports, manual record files, and download activity log
    │   └── merged/         Harmonized patent tables and review records
    └── merge_and_match.py  Patent cleaning, matching, and aggregation script
```

## Question 1 Summary

* **Methodology and Ranking:** Documented in [`q1/incubator_ranking/METHODOLOGY.md`](q1/incubator_ranking/METHODOLOGY.md). I evaluated incubators using two independent frameworks: cumulative output scale (Method A) and composite institutional strength (Method B). The final ranking combines both via Borda rank averaging.
* **Incubator Spreadsheet:** [`q1/incubator_ranking/incubators_top20.xlsx`](q1/incubator_ranking/incubators_top20.xlsx) details host institutions, city, state, founding year, website, reported startups, and methodological scores across all candidates.
* **Web Scraper:** Fully annotated Python 3 script in [`q1/scraper/wayback_scraper.py`](q1/scraper/wayback_scraper.py), with operational guidance in [`q1/README.md`](q1/README.md).
* **Scraped HTML Dataset:** Stored in [`q1/scraped_html/`](q1/scraped_html/). The dataset contains 1,265 HTML files across all 20 incubators (795 archived homepages, 440 archived About pages, and 30 live captures).
* **Coverage and Quality Audit:** Monthly collection covers January 2022 to September 2026. Audit logs in [`q1/manifest.csv`](q1/manifest.csv) and [`q1/coverage_summary.csv`](q1/coverage_summary.csv) document capture timestamps, gaps, and content quality classifications.

## Question 2 Summary

* **Search Methodology and Ranking:** Documented in [`q2/README.md`](q2/README.md). The candidate pool covers climate tech ventures founded in 2008 or later across renewable energy, clean mobility, battery tech, and circular resource recovery. Startups are ranked by cumulative venture funding, with sensitivity bounds (`rank_if_low` and `rank_if_high`).
* **Startup Spreadsheet:** Basic corporate details, incorporation years, locations, and funding tiers are compiled in [`q2/startups/startups_top20.xlsx`](q2/startups/startups_top20.xlsx).
* **WIPO PATENTSCOPE Collection:** All 20 startups were searched on WIPO PATENTSCOPE. Raw exports for queries with downloadable results are stored in [`q2/data/wipo_raw/`](q2/data/wipo_raw/) alongside `download_log.csv`. Two single-hit records (Ecozen and Exponent Energy) that had no export button were added manually. The download script [`q2/wipo_download.py`](q2/wipo_download.py) coordinates authenticated sessions.
* **Merged Patent Dataset:** The harmonization script [`q2/merge_and_match.py`](q2/merge_and_match.py) cleans applicant strings, filters foreign homonyms, and aggregates patent metrics. Final outputs are in [`q2/data/merged/startups_with_patents.xlsx`](q2/data/merged/startups_with_patents.xlsx), linking 567 matched patents across 22 jurisdictions.
* **Matching Process Description:** Detailed criteria and homonym filtering rules are documented in [`q2/README.md`](q2/README.md).

## Submission Links

1. Question 1: `https://github.com/saimihirj/iimb-take-home-exercise/tree/main/q1`
2. Question 2: `https://github.com/saimihirj/iimb-take-home-exercise/tree/main/q2`

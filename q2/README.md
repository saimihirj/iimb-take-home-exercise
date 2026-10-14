# Question 2 – India's largest environment startups + WIPO patent data

```
q2/
├── startups/
│   ├── candidate_pool.csv     22 candidates (20 ranked + 2 excluded), funding with low/high range & confidence
│   ├── rank_startups.py       ranking → startups_top20.csv / .xlsx   (deliverable 1.3)
│   └── startups_top20.xlsx    basic startup details
├── wipo_download.py           semi-automated raw download from WIPO PATENTSCOPE (deliverable 2.1)
├── data/wipo_raw/             raw, untouched PATENTSCOPE exports + download_log.csv
├── merge_and_match.py         merge + fuzzy matching (deliverables 2.2, 2.3)
└── data/merged/               patents_matched / patents_review / patents_unmatched / startups_with_patents
```

## 1. Which startups? (search methodology & ranking)
**Scope (assumptions)**
* *Environment startup* = climate/cleantech company: renewable energy (rooftop solar, bio-CNG, microgrids), clean mobility (EV makers, charging, swapping, fleets), recycling & circular economy, carbon markets, agri-cleantech. Pure EV hardware is included because transport decarbonisation dominates Indian climate-tech funding (Tracxn: EV & renewables are the largest segments).
* *Startup* = founded 2008 or later and venture-funded; recently listed ventures (Ola Electric, Ather) are retained and flagged because they were venture-backed startups until 2024-25. Corporate subsidiaries and infrastructure conglomerates (Inox Clean Energy, Greenko) are **excluded** (sheet `Excluded`).
* *Largest* = **cumulative external funding raised (USD m)** – the one size metric available for private companies in every source. Alternatives (revenue, employees) are not consistently public for private firms.

**Search**: (1) Tracxn / India Tech Report climate-tech sector summaries and category leaders (renewables, EV, battery recycling, waste); (2) press funding trackers (Inc42, Entrackr, EVreporter) to cross-check totals; (3) founding-year/legal-entity details from company sites. Candidates were sought across sub-sectors so one sector does not crowd out the others.

**Ranking**: sort by `total_funding_usd_m` (midpoint of the range reported by different trackers) → top 20. `rank_if_low` / `rank_if_high` columns re-rank using the lowest/highest reported total: the Top-20 membership is unchanged; only order within neighbours (BluSmart/Battery Smart, Lohum/Husk, ChargeZone/GPS/Log9) shifts.

**Caveats**: funding totals come from aggregator summaries (Tracxn, Inc42, etc.) retrieved Oct-2026, mix equity and sometimes debt, and were **not** verified against filings (Ola Electric, Ather, ChargeZone, Varaha = Low confidence). BluSmart's operations were disrupted in 2025. Replace with a Tracxn/Crunchbase export if available. The cut-off (BatX at #20 vs Varaha at #21) is thin – Varaha's figure is an analyst estimate.

## 2. WIPO PATENTSCOPE download
**Status – needs one manual step.** PATENTSCOPE served an image CAPTCHA ("select the picture containing a blue eye") to my automated browser session on 14-Oct-2026 and the Excel/CSV export needs a free WIPO login. I did not try to bypass either control, so **`data/wipo_raw/` is empty until you run the downloader**.

```bash
pip install playwright pandas openpyxl && # Google Chrome must be installed
python3 wipo_download.py        # opens Chrome; you solve CAPTCHA + log in once, then click Download for each startup
```
For each startup the script types `PA:("<legal name>") OR PA:("<brand>") OR PA:("<alias>")` (PA = applicant) and captures whatever file you download, untouched, as `data/wipo_raw/<slug>__<timestamp>.<ext>`; queries/timestamps are logged in `download_log.csv`. Manual alternative: run the same query in PATENTSCOPE (Simple Search), export, save as `<slug>__manual.xls`.
Scope of the query: *all* collections (PCT + national offices incl. IN, US…) – "filed or granted" is covered by applications (A-kind codes) and grants (B-kind codes); the PATENTSCOPE export has no universal granted flag, hence the heuristic below.

## 3. Matching process (`merge_and_match.py`)
1. Normalise applicant strings (Unicode-fold, lower-case, strip punctuation and legal forms: *pvt, private, ltd, limited, inc, llp, india…*).
2. Split co-applicant cells (`; | newline /`).
3. Compare with each startup's normalised {legal entity, brand name, aliases}: **exact** → accept; similarity ≥ 0.90 (difflib on character sequence and on sorted tokens) → accept as **fuzzy**, flagged; 0.80-0.90 → **not accepted**, goes to `patents_review.csv`; no hit → `patents_unmatched.csv` (false positives from the WIPO query, e.g. "Atherton Energy").
4. One row per (publication number, startup); multi-startup co-filings kept.
5. Startup-level join to `startups_top20.csv` → `startups_with_patents.csv/xlsx`: patent records, heuristic granted count (kind codes B/C/S/T/Y = grant, A = application), first/last publication year, number of fuzzy matches.
6. Recommended human QA: read `patents_review.csv` and a sample of `fuzzy` rows; check that has_wipo_download is True for all 20.

Tested only on a 4-row synthetic fixture (exact match, co-applicant, near-name rejection "Atherton Energy", cross-startup hit) – **not on real WIPO exports**, whose column headers may differ slightly; `canon_columns()` maps headers by keyword (applicant, publication number, date, kind…). If a header is missed the corresponding field is blank, not wrong.

## 4. Limitations
* Startups often file under a founder, a parent/predecessor entity or a foreign affiliate (e.g. Husk Power Systems Inc., Ather's former name) – add aliases in `candidate_pool.csv` and re-run.
* PATENTSCOPE coverage of Indian national filings is partial; Indian grants may be missing (InPASS is the authoritative Indian source).
* Name-based matching cannot separate namesakes (e.g. generic names like "Yulu", "Recykal"); review fuzzy/short-name matches.

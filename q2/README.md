# Question 2: India's Largest Environment Startups and WIPO Patent Pipeline

```
q2/
├── startups/
│   ├── candidate_pool.csv     Candidate table with funding ranges and data confidence
│   ├── rank_startups.py       Script ranking the top 20 environment startups
│   ├── startups_top20.csv     Flat CSV table of the top 20 environment startups
│   └── startups_top20.xlsx    Multi-sheet workbook containing the ranked startups
├── wipo_download.py           Semi-automated download script for WIPO PATENTSCOPE
├── data/
│   ├── wipo_raw/              Raw, unmodified PATENTSCOPE exports and download log
│   └── merged/                Harmonized datasets and matching review logs
│       ├── startups_with_patents.xlsx  Complete merged workbook with all tabs
│       ├── startups_with_patents.csv   Startup table joined with patent metrics
│       ├── patents_matched.csv         567 matched patent records
│       ├── patents_review.csv          846 flagged homonym records held for review
│       └── patents_unmatched.csv       Unmatched query output table
└── merge_and_match.py         Patent matching and entity aggregation script
```

## 1. Startup Identification and Ranking Methodology

### Scope and Operating Definitions

* **Environmental and cleantech startups**. The analysis encompasses ventures addressing greenhouse gas mitigation, renewable power, energy storage, clean transportation, circular resource recovery, and climate-smart agriculture. Electric vehicle manufacturers and mobility infrastructure providers are included. Clean mobility represents the largest segment of climate tech venture funding in India.
* **Startup qualifications**. Candidate companies must be independent ventures founded in 2008 or later. Companies that completed initial public offerings recently, such as Ola Electric and Ather Energy, remain included in the cohort. They operated as venture-backed private startups throughout their primary expansion. Corporate subsidiaries and multi-billion infrastructure holding groups are excluded from the candidate pool. For example, Inox Clean Energy and Greenko are catalogued on the `Excluded` sheet.
* **Metric of scale**. Total cumulative external capital raised in millions of US dollars serves as the ranking metric. Venture funding provides the most reliable comparative benchmark across privately held companies. Financial indicators like annual turnover or staffing levels are not published consistently across private Indian corporations.

### Search Strategy

1. **Market intelligence databases**. I reviewed Indian climate technology reports published by Tracxn and the India Tech Report. The review examined renewable generation, bio-energy, battery chemistry, electric mobility, and waste management.
2. **Financial tracking sources**. Disclosed investment transactions were verified against records from Inc42, Entrackr, and EVreporter.
3. **Corporate filings and websites**. Corporate registry profiles and primary company websites confirmed incorporation years, headquarters locations, and formal legal entity names.

The candidate pool spans multiple environmental sectors. This prevents capital-intensive vehicle manufacturers from displacing resource recovery and distributed energy enterprises.

### Ranking and Sensitivity Analysis

Startups are ordered by total funding raised in descending order. The primary value represents the midpoint of compiled investment totals.

The workbook includes sensitivity columns titled `rank_if_low` and `rank_if_high`. These fields test whether the cohort composition changes under minimum or maximum reported figures. The top 20 member list remains completely unchanged under both boundaries. Minor rank adjustments occur only between adjacent firms such as Battery Smart and BluSmart, or Husk Power Systems and Lohum.

### Data Limitations and Caveats

* Funding metrics aggregate publicly reported venture funding, private equity injections, and disclosed credit lines as of October 2026. They do not represent audited statutory balance sheets.
* Certain entities carry lower data confidence, including Varaha, ChargeZone, and Ola Electric. Operating disruptions affecting BluSmart during 2025 are recorded directly in the dataset.
* The cut-off boundary at rank 20 is narrow. BatX Energies precedes Varaha by five million dollars, where Varaha's total reflects an analyst estimate.
* An independent spot check compared four funding totals with a second set of public reports. Husk Power Systems (around 125 to 127 million dollars) matched reported figures. Simple Energy was reported at 263 to 279 million dollars, slightly below the 285 million midpoint used here. Euler Motors was reported at 230 to 250 million dollars after its 2025 Series D, so the 229 million used here may be conservative. Battery Smart's total could not be confirmed from a single source. None of these differences moves a company across the top 20 boundary, though they could adjust relative placement within the top 10.

## 2. WIPO PATENTSCOPE Data Collection

### Technical Status and Collection Results

WIPO PATENTSCOPE uses bot-prevention controls. Automated headless browser sessions encounter visual CAPTCHA verification challenges. In addition, downloading result files requires an authenticated user account.

To respect platform safeguards, data collection was conducted using the companion script `wipo_download.py` with an authenticated browser session.

All 20 startups were searched on 14 October 2026. Raw exports were saved for the 12 queries that returned a downloadable result list, together with `download_log.csv`.

Startups with captured WIPO patent records:
* Ola Electric: 270 records
* Ather Energy: 100 records
* SUN Mobility: 86 records
* Attero Recycling: 78 records
* Lohum Cleantech: 14 records
* GPS Renewables: 6 records
* BatX Energies: 4 records
* Log9 Materials: 3 records
* BluSmart Mobility: 2 records
* Yulu Bikes: 2 records
* Battery Smart: 13 raw hits, all unrelated homonyms (flue gas patents), so 0 matched
* Simple Energy: 12 raw hits, all judged to be a US utility software firm with the same name, so 0 matched

All 20 startups were queried. The outcomes for the other 8 are recorded in `download_log.csv`.
* Zero results: Euler Motors, Husk Power Systems, SolarSquare, ChargeZone, Zypp Electric, Recykal.
* One result each: Ecozen Solutions (IN201921045548, "System and method to measure energy level of a phase change material") and Exponent Energy (IN202241029626, "Process of charging an energy storage system"). PATENTSCOPE opens a single hit directly in the record view, which has no export button. The two records were therefore keyed in by hand from the record view into `data/wipo_raw/<slug>__manual_record_view.csv`. They carry no application date or IPC code, so the filing year comes from the year prefix of the Indian application number. The column `filing_year_source` in `patents_matched.csv` marks this.

Zero results does not prove a startup has no patents. Filings may sit under founder names, a parent entity, or only on the Indian Patent Office portal InPASS.

### Download Script Architecture

The script `wipo_download.py` coordinates the download workflow:

```bash
pip install -r requirements.txt
playwright install chromium
python3 q2/wipo_download.py
```

The script launches Google Chrome and navigates to PATENTSCOPE. The user signs in and solves the CAPTCHA manually. Once authenticated, the user presses Enter in the terminal to execute automated searches.

The program submits applicant queries for each startup in sequence. It combines primary corporate names and registered aliases with applicant field prefixes:
`PA:"Ather Energy" OR PA:"Ather Energy Private Limited"`

The script intercepts file downloads from the browser, logs timestamps to `download_log.csv`, and stores raw files in `data/wipo_raw/`.

Search queries evaluate international PCT applications alongside national patent offices. Exports contain filed or published applications. They carry no legal status field, so the merged file does not split records into granted and pending. Grant status needs a check on each national register. The merged table reports total records, PCT/WO records, Indian records, and the filing year range instead.

## 3. Matching and Harmonization Process

The script `merge_and_match.py` cleans raw exports and joins patent records with the startup directory.

### Cleaning and Entity Comparison

1. **Header detection**. WIPO `.xls` exports contain a five-row metadata block preceding tabular data. The script dynamically scans for the table header row.
2. **Applicant normalization**. Company names are stripped of punctuation and converted to lowercase. Common corporate legal suffixes are removed, including private, pvt, limited, ltd, incorporated, inc, and technologies.
3. **Targeted query alignment**. When PATENTSCOPE exports are generated via specific applicant queries (`PA:("<name>")`), the resulting file associates directly with the target startup.
4. **Homonym discrimination**. Generic brand names can match unrelated international entities. The script inspects country codes and title keywords to isolate homonyms:
   * Yulu: Broad queries match hundreds of Chinese utility patents filed by unrelated individual inventors named Yulu. The script validates Indian jurisdiction and electric vehicle keywords to isolate true Yulu Bikes filings. Unrelated foreign homonyms are routed to `patents_review.csv`.
   * Simple Energy: Queries match US patents assigned to Simple Energy Inc, a software company based in Colorado that manages utility rebate programs. These records are separated from Simple Energy Private Limited.
   * Battery Smart: Unrelated Chinese patents for flue gas recovery are separated from Battery Smart mobility records.
5. **Deduplication**. Records are deduplicated by publication number and startup identifier.
6. **Jurisdiction mapping**. Matched patents span 22 patent offices, including 246 PCT/WO filings, 215 Indian domestic applications, 22 US filings, and 22 European Patent Office records. Additional national phase entries appear in Singapore, Vietnam, Indonesia, Australia, and Brazil.

### Summary of Dataset Outputs

The harmonization pipeline produces five output tables in `data/merged/`:

1. `startups_with_patents.xlsx`: Comprehensive multi-sheet Excel deliverable containing the startup overview, matched patents, and review logs.
2. `startups_with_patents.csv`: Startup table enriched with patent counts, filing date ranges, and download flags.
3. `patents_matched.csv`: 567 matched patent records linked to the top 20 startups.
4. `patents_review.csv`: 846 unassigned homonym records held for independent review.
5. `patents_unmatched.csv`: Unmatched search output log.

## 4. Analytical Constraints

* Early-stage startups frequently file intellectual property under individual founders, parent holding companies, or foreign affiliates. Researchers can append newly discovered legal entities to `candidate_pool.csv` and re-run the pipeline.
* WIPO PATENTSCOPE indexes Indian domestic filings selectively. Supplementary searches on the Indian Patent Office database InPASS provide additional validation for regional filings.
* WIPO basic tabular exports do not contain legal grant status flags. Exported records reflect published patent applications and PCT filings. Determining conclusive grant status requires querying individual national patent registers.

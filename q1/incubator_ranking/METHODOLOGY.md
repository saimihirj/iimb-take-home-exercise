# Question 1.1: Top 20 Startup Incubators in India Search and Ranking Methodology

The primary dataset is stored in [`incubators_top20.xlsx`](incubators_top20.xlsx). It contains four sheets titled `Top20_final`, `MethodA_scale_all`, `MethodB_strength_all`, and `All_candidates`. The full ranked table is also provided in [`incubators_ranked.csv`](incubators_ranked.csv). You can run `python3 build_ranking.py` to regenerate both files.

## 1. Definitions and Working Assumptions

| ID | Operational Assumption |
|---|---|
| A1 | No public authority publishes an official league table ranking incubators by size. Therefore, the term "largest" lacks a single statutory definition. This study evaluates programs through two independent lenses, measuring output scale and institutional strength. |
| A2 | The primary unit of analysis is a single operating organization, such as NSRCEL, T-Hub, or KSUM. Umbrella funding programs are excluded from standalone evaluation. These networks include the 72 Atal Incubation Centres, the MeitY Startup Hub, and the NSTEDB NIDHI network. Evaluating umbrella programs directly would result in double counting. |
| A3 | State agencies such as KSUM and StartupTN remain in the candidate pool alongside STPI. Each operates as an active legal entity managing incubation facilities directly. Their numbers reflect broader definitions of supported enterprises. These definitions are documented in the `count_definition` column. |
| A4 | The reference date for institutional age calculations is October 2026. Age is computed as 2026 minus the founding year. |
| A5 | Startup counts rely on cumulative figures disclosed across public reports. These disclosures apply varying internal criteria across institutions. The `count_confidence` field records the data quality tier for each entry. Candidate rows marked as analyst estimates lack official disclosures and require independent verification. |

## 2. Search Methodology

The candidate pool was constructed through systematic review across four distinct data sources.

1. **Government and ministerial directories**. The review examined technology business incubators and centres of excellence listed by the National Science and Technology Entrepreneurship Development Board (NSTEDB). It incorporated Atal Incubation Centres recognized by NITI Aayog's Atal Innovation Mission. It also included Centres of Entrepreneurship under Software Technology Parks of India (STPI), along with official state missions in Kerala, Tamil Nadu, Telangana, and Gujarat.
2. **Global benchmarking reports**. The search consulted evaluation studies by UBI Global, including recognitions awarded to public and university-linked incubation centres in India.
3. **Institutional disclosures**. Annual reports, official impact web pages, and academic portal releases provided verified founding dates, startup milestones, and managed funds.
4. **Ecosystem mapping**. The review mapped active incubation wings across premier academic institutions, including Indian Institutes of Technology, Indian Institutes of Management, the Indian Institute of Science, and the International Institute of Information Technology. It also tracked established private and corporate accelerators.

The initial screening yielded 24 qualifying candidate institutions. Four candidate organizations lacked verified cumulative counts, specifically IKP Knowledge Park, Zone Startups India, Startup Oasis, and IIM Calcutta Innovation Park. These four entries rely on conservative analyst estimates with low confidence ratings.

### Methodological Justification
Using multiple source streams limits institutional selection bias. Government registries frequently emphasize state agencies and regional grant recipients. In contrast, financial news reporting focuses disproportionately on top-tier engineering and management institutes. Combining public registries, global benchmark rankings, and primary portal releases ensures balanced representation.

## 3. Two Ranking Methodologies

### Method A: Output Scale
Method A ranks candidate institutions by cumulative startups supported, as recorded in `startups_reported`. This metric highlights programs with the widest historical reach. However, reporting criteria differ across institutions. State agencies frequently report broader outreach numbers than university research parks.

### Method B: Composite Institutional Strength
Method B calculates a weighted composite rating on a scale from 1.0 to 5.0.

`score_B = 0.30 * Govt_recognition + 0.30 * Capital_access + 0.25 * Ecosystem_reach + 0.15 * Age_score`

The four dimensions evaluate distinct facets of operational maturity:
* **Government recognition**. Rated on a scale of 1 to 5. This evaluates official accreditation, such as designation as a NIDHI Centre of Excellence, recognition as an Atal Incubation Centre, or formal state agency authority.
* **Capital access**. Rated on a scale of 1 to 5. This measures internal seed funds, dedicated venture capital affiliations, and grant distribution capacity.
* **Ecosystem reach**. Rated on a scale of 1 to 5. This reflects brand strength, corporate partnerships, mentor depth, and cross-sector portfolio breadth.
* **Institutional maturity**. Rated on a scale of 1 to 5. The metric is calculated as `1.0 + 4.0 * min(age, 25) / 25`. Scores saturate at 25 years of continuous operation.

Method B balances numerical output by recognizing institutional stability, financial backing, and regulatory standing.

## 4. Ranking Justification and Final Selection

The final ranking merges both methodologies using Borda rank averaging.

`mean_rank = (rank_A_scale + rank_B_strength) / 2`

Ties are resolved by the composite strength score, followed by cumulative startups reported. The top 20 candidates form the primary cohort. Four candidate entities fell below the top 20 threshold, specifically Axilor Ventures, Startup Oasis, Zone Startups India, and GUSEC.

Rank averaging prevents distortion from single extreme variables. High volume alone does not guarantee a top placement. For example, CIIE.CO attains the first overall position because it ranks within the top five across both independent methodologies.

### Known Limitations and Sensitivity
* Boundary positions between rank 17 and rank 20 remain sensitive to minor score changes. Social Alpha, IKP Knowledge Park, CIE IIITH, and IISc SID sit within two rank points of excluded entities. A single point adjustment in qualitative scoring can alter their inclusion.
* Figures for IKP Knowledge Park and IIM Calcutta Innovation Park represent estimated baselines rather than audited historical counts.
* Milestone metrics reflect publicly compiled data as of October 2026. Academic researchers should review audited annual reports for formal verification.

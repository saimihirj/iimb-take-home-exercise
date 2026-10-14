# Q1.1 – Top-20 startup incubators in India: search & ranking methodology

Spreadsheet: [`incubators_top20.xlsx`](incubators_top20.xlsx) (sheets: `Top20_final`, `MethodA_scale_all`, `MethodB_strength_all`, `All_candidates`) · CSV: [`incubators_ranked.csv`](incubators_ranked.csv) · Re-run: `python3 build_ranking.py`

## 1. Definitions & assumptions
| # | Assumption |
|---|---|
| A1 | "Largest" has no single official definition (no regulator publishes a league table by size). I therefore use **two independent lenses**: *output scale* and *institutional strength* (below). |
| A2 | The unit is a **single operating organisation** (e.g. NSRCEL, T-Hub, KSUM). Umbrella *networks* (Atal Incubation Centres – 72 centres, MeitY Startup Hub, NSTEDB/NIDHI scheme) are **excluded**: they are programmes that fund many incubators, so counting them double-counts. |
| A3 | State agencies (KSUM, StartupTN) and STPI are kept because each is one legal entity that runs incubation itself, but their counts are flagged because their definition of "startup supported" is broader (see `count_definition`). |
| A4 | Reference date: October 2026; "age" = 2026 − founding year. |
| A5 | Startup counts are **self-reported, cumulative, non-comparable definitions**. They are a noisy proxy – confidence is recorded per row (`count_confidence`). Rows marked *ANALYST ESTIMATE* have no source figure and should be verified before use. |

## 2. Search methodology (how the candidate pool was built)
1. **Government/institutional lists** – DST-NSTEDB (NIDHI TBIs & Centres of Excellence), NITI Aayog AIM (AIC hosts), MeitY/STPI CoEs, Startup India incubator directory; state startup missions (Kerala, Tamil Nadu, Telangana, Gujarat).
2. **Rankings / awards** – UBI Global benchmark reports (KSUM global #1 public incubator), NSTEDB performance mentions.
3. **Press & institutional web pages** – each incubator's own "impact" page and press reports for cumulative startup counts, funds managed, founding year.
4. **Snowballing** – from IIT/IIM/IISc/IIIT incubators and private accelerators (Axilor, Zone Startups, Social Alpha) mentioned in the above.
5. Result: **24 candidates**; 4 had no sourced count (IKP, Zone Startups, Startup Oasis, IIMCIP → analyst estimates, low confidence).

Justification: using several source families (government, ranking body, institutions, press) reduces the bias of any one source (e.g. IIT/IIM incubators over-represented in press; state bodies over-represented in government lists).

## 3. Two ranking methodologies
**Method A – Scale.** Rank by cumulative startups incubated/supported (`startups_reported`). Answers "who has touched the most startups?". Weakness: definitions differ; state agencies inflate.

**Method B – Institutional strength (0-5 composite).**
`score_B = 0.30·Govt recognition + 0.30·Capital access + 0.25·Ecosystem reach + 0.15·Age score`
* *Govt recognition (1-5)*: NIDHI-TBI/CoE, AIC host, state-agency mandate, MeitY/CSIR backing.
* *Capital access (1-5)*: own seed/VC fund, grant disbursing ability, anchor funders (e.g. CIIE's funds = 5).
* *Ecosystem reach (1-5)*: brand/network, corporate & investor connections, geographic/sector breadth.
* *Age score*: 1 + 4·min(age, 25)/25.
The first three are analyst judgements (1-5 rubric in `candidate_pool.csv`), so Method B is explicitly **subjective** – its value is that it penalises mere volume and rewards durability and funding access.

## 4. Ranking justification (arriving at the Top-20)
`mean_rank = (rank_A + rank_B)/2` (Borda-style rank aggregation). Ties → higher Method-B score → higher count. The 20 lowest mean ranks form the Top-20; the 4 dropped are Axilor Ventures, Startup Oasis, Zone Startups India, GUSEC.
Why rank-averaging: it needs no common unit between a count and a score and is robust to one metric's outliers (e.g. KSUM's 6,000 would otherwise dominate; CIIE.CO is #1 because it is top-5 on both lenses).

### Known limitations / sensitivity (read before relying on it)
* Cut-off positions 17-20 (Social Alpha, IKP, CIE-IIITH, IISc SID) are within 1-2 mean-rank points of the excluded Axilor/Startup Oasis; changing a rubric score by 1 can flip them.
* IKP Knowledge Park and IIMCIP counts are estimates, not sourced figures.
* Counts come from web summaries gathered Oct-2026; they have **not** been verified against each incubator's annual report.

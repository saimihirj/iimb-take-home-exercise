#!/usr/bin/env python3
"""Q2.1 - Rank India's largest environment (climate/cleantech) startups by total external funding raised (USD m).
Excludes rows flagged startup_in_scope == 'N'. Output: startups_top20.csv / .xlsx"""
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent
df = pd.read_csv(HERE / "candidate_pool.csv")
scope = df[df.startup_in_scope == "Y"].copy()
scope = scope.sort_values(["total_funding_usd_m", "funding_low_usd_m"], ascending=False).reset_index(drop=True)
scope["rank"] = scope.index + 1
scope["in_top20"] = scope["rank"] <= 20
# robustness: rank using the LOW and HIGH ends of the funding range -> shows how stable the cut-off is
scope["rank_if_low"] = scope.funding_low_usd_m.rank(ascending=False, method="min").astype(int)
scope["rank_if_high"] = scope.funding_high_usd_m.rank(ascending=False, method="min").astype(int)
scope = scope.drop(columns=["rank_seed"])
cols = ["rank", "in_top20", "name", "legal_entity_primary", "name_aliases", "founded", "hq_city", "sub_sector",
        "total_funding_usd_m", "funding_low_usd_m", "funding_high_usd_m", "rank_if_low", "rank_if_high",
        "funding_confidence", "status_note", "website"]
scope = scope[cols]
top = scope[scope.in_top20]
top.to_csv(HERE / "startups_top20.csv", index=False)
with pd.ExcelWriter(HERE / "startups_top20.xlsx") as xw:
    top.to_excel(xw, "Top20", index=False)
    scope.to_excel(xw, "Ranked_all_in_scope", index=False)
    df[df.startup_in_scope == "N"].to_excel(xw, "Excluded", index=False)
print(top[["rank", "name", "total_funding_usd_m", "rank_if_low", "rank_if_high"]].to_string(index=False))

#!/usr/bin/env python3
"""
Question 1.1: Rank India's largest startup incubators using two independent methodologies.
The script combines both results to identify the top 20 cohort.

Method A evaluates scale by ranking cumulative startups supported.
Method B evaluates institutional strength using a composite score.
Final rankings use rank averaging with Borda count aggregation.

Inputs: candidate_pool.csv
Outputs: incubators_ranked.csv, incubators_top20.xlsx

Usage: python3 build_ranking.py
"""
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent
REF_YEAR = 2026
W = {"govt": 0.30, "capital": 0.30, "reach": 0.25, "age": 0.15}
AGE_CAP = 25


def main():
    df = pd.read_csv(HERE / "candidate_pool.csv")

    # Method A: Output Scale
    df["rank_A_scale"] = df["startups_reported"].rank(ascending=False, method="min").astype(int)

    # Method B: Composite Institutional Strength
    df["age_years"] = REF_YEAR - df["founded"]
    df["age_score_1to5"] = (df["age_years"].clip(upper=AGE_CAP) / AGE_CAP * 4 + 1).round(2)
    df["score_B"] = (
        W["govt"] * df["govt_recognition_1to5"]
        + W["capital"] * df["capital_access_1to5"]
        + W["reach"] * df["ecosystem_reach_1to5"]
        + W["age"] * df["age_score_1to5"]
    ).round(3)
    df["rank_B_strength"] = df["score_B"].rank(ascending=False, method="min").astype(int)

    # Combined Rank
    df["mean_rank"] = (df["rank_A_scale"] + df["rank_B_strength"]) / 2
    df = df.sort_values(["mean_rank", "score_B", "startups_reported"],
                        ascending=[True, False, False]).reset_index(drop=True)
    df["final_rank"] = df.index + 1
    df["in_top20"] = df["final_rank"] <= 20

    cols = ["final_rank", "in_top20", "name", "host_institution", "city", "state", "type",
            "founded", "age_years", "website", "startups_reported", "count_definition",
            "count_confidence", "rank_A_scale", "govt_recognition_1to5", "capital_access_1to5",
            "ecosystem_reach_1to5", "age_score_1to5", "score_B", "rank_B_strength", "mean_rank",
            "focus", "source_notes"]
    df = df[cols]
    df.to_csv(HERE / "incubators_ranked.csv", index=False)

    with pd.ExcelWriter(HERE / "incubators_top20.xlsx") as xw:
        df[df.in_top20].to_excel(xw, "Top20_final", index=False)
        df.sort_values("rank_A_scale").to_excel(xw, "MethodA_scale_all", index=False)
        df.sort_values("rank_B_strength").to_excel(xw, "MethodB_strength_all", index=False)
        df.to_excel(xw, "All_candidates", index=False)
    print(df[["final_rank", "name", "startups_reported", "rank_A_scale", "score_B",
              "rank_B_strength", "mean_rank"]].to_string(index=False))


if __name__ == "__main__":
    main()

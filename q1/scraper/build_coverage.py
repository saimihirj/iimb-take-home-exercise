#!/usr/bin/env python3
"""Rebuilds q1/coverage_summary.csv from q1/manifest.csv. Run: python3 q1/scraper/build_coverage.py"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
m = pd.read_csv(ROOT / "manifest.csv", dtype=str).fillna("")
wb = m[m.source == "wayback"]
rows = []
for site, g in m.groupby("site"):
    r = {"site": site}
    for pt in ("about", "home"):
        w = g[(g.source == "wayback") & (g.page_type == pt)]
        r[pt] = int(w.status.isin(["ok", "ok_cached"]).sum())
    r["months_total"] = int(wb[(wb.site == site) & (wb.page_type == "home")].shape[0])
    for pt in ("about", "home"):
        l = g[(g.source == "live") & (g.page_type == pt)]
        r[f"live_{pt}"] = l.status.iloc[0] if len(l) else "missing"
    if "content_quality" in g.columns:
        ok = g[g.status.isin(["ok", "ok_cached"])]
        r["files_with_readable_text"] = int((ok.content_quality == "content").sum())
        r["files_total"] = int(len(ok))
    rows.append(r)
out = pd.DataFrame(rows)[["site", "about", "home", "months_total", "live_about", "live_home"] +
                         (["files_with_readable_text", "files_total"] if "content_quality" in m.columns else [])]
out.to_csv(ROOT / "coverage_summary.csv", index=False)
print(out.to_string(index=False))
print("TOTAL files:", int(out["about"].sum() + out["home"].sum()), "wayback + live ok:",
      int(m.status.isin(["ok", "ok_cached"]).sum()))

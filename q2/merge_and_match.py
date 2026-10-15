#!/usr/bin/env python3
"""
Question 2.2: Harmonize raw WIPO PATENTSCOPE exports with the top 20 environment startups.

Inputs:
    data/wipo_raw/ contains raw exports from PATENTSCOPE.
    startups/startups_top20.csv contains the ranked startup directory.

Outputs:
    data/merged/patents_matched.csv records matched patent records.
    data/merged/patents_review.csv flags borderline matches and query homonyms.
    data/merged/patents_unmatched.csv records unassigned patents from broad queries.
    data/merged/startups_with_patents.csv joins patent summary metrics to the startup table.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "wipo_raw"
OUT = HERE / "data" / "merged"
STARTUPS = HERE / "startups" / "startups_top20.csv"

LEGAL_WORDS = r"\b(private|pvt|ltd|limited|inc|incorporated|llp|llc|corp|corporation|co|company|india|indian|plc|gmbh)\b"
FUZZY_ACCEPT, FUZZY_REVIEW = 0.90, 0.80

COLS = {
    "pub_number": ["publication number", "pub. no", "publication no", "pub number", "application id"],
    "pub_date": ["publication date", "pub. date"],
    "app_number": ["application number", "appl. no"],
    "app_date": ["application date", "filing date", "appl. date"],
    "title": ["title"],
    "applicants": ["applicant", "applicants"],
    "inventors": ["inventor", "inventors"],
    "ipc": ["ipc", "main ipc", "i p c"],
    "country": ["office", "country", "authority"],
    "kind": ["kind"],
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(LEGAL_WORDS, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b):
    if not a or not b:
        return 0.0
    ta, tb = " ".join(sorted(a.split())), " ".join(sorted(b.split()))
    return max(SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, ta, tb).ratio())


def read_any(path):
    if path.suffix.lower() == ".csv":
        try:
            return pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(path, dtype=str, encoding="latin-1", sep=None, engine="python")
    raw = pd.read_excel(path, header=None, dtype=str)
    for i in range(min(15, len(raw))):
        vals = [str(x).strip().lower() for x in raw.iloc[i].dropna()]
        if any(k in vals for k in ["title", "application id", "application number", "applicant"]):
            raw.columns = [str(c).strip() for c in raw.iloc[i].values]
            df = raw.iloc[i + 1:].dropna(how="all").copy()
            return df
    return raw


def canon_columns(df):
    ren = {}
    low = {c: str(c).lower().strip() for c in df.columns}
    for canon, keys in COLS.items():
        for c, l in low.items():
            if c not in ren and any(k in l for k in keys):
                ren[c] = canon
                break
    out = df.rename(columns=ren)
    for canon in COLS:
        if canon not in out.columns:
            out[canon] = ""
    return out[list(COLS)]


def load_raw():
    frames = []
    for f in sorted(RAW.glob("*")):
        if f.suffix.lower() not in (".csv", ".xls", ".xlsx") or f.name == "download_log.csv":
            continue
        slug = f.name.split("__")[0]
        parsed = read_any(f)
        if parsed.empty:
            continue
        df = canon_columns(parsed).fillna("")
        df["query_startup_slug"] = slug
        df["raw_file"] = f.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def is_homonym_mismatch(slug, row):
    country = str(row.get("country", "")).strip().upper()
    title = str(row.get("title", "")).lower()

    if slug == "yulu":
        if country == "IN":
            return False
        if any(k in title for k in ["shared mobility", "electric vehicle", "bicycle", "dockless"]):
            return False
        return True

    if slug == "battery-smart":
        if country == "IN":
            return False
        if any(k in title for k in ["battery swapping", "swapping station", "electric vehicle"]):
            return False
        return True

    if slug == "simple-energy":
        if any(k in title for k in ["rebate", "utility", "demand response", "plastic"]):
            return True
        if any(k in title for k in ["scooter", "two-wheeler", "vehicle", "battery pack", "electric"]):
            return False
        return True

    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(STARTUPS)
    st["slug"] = st["name"].str.lower().str.replace(r"[^a-z0-9]+", "-", regex=True).str.strip("-")
    names = {}
    for _, r in st.iterrows():
        vs = {norm(r["legal_entity_primary"]), norm(r["name"])} | {norm(x) for x in str(r["name_aliases"]).split("|")}
        names[r["slug"]] = {v for v in vs if v}

    raw = load_raw()
    if raw.empty:
        print("No raw WIPO files in", RAW)
        return

    raw["pub_number"] = raw["pub_number"].str.strip()
    raw = raw.drop_duplicates(["pub_number", "query_startup_slug"])

    matched, review, unmatched = [], [], []

    for _, p in raw.iterrows():
        base = p.to_dict()
        q_slug = p["query_startup_slug"]
        has_applicants = bool(str(p["applicants"]).strip())

        if has_applicants:
            apps = [a.strip() for a in re.split(r";|\||\n| / ", p["applicants"]) if a.strip()]
            hits, rev = {}, {}
            for a in apps:
                na = norm(a)
                for slug, vs in names.items():
                    best = max((sim(na, v) for v in vs), default=0)
                    kind = "exact" if na in vs else None
                    if kind is None and best >= FUZZY_ACCEPT:
                        kind = "fuzzy"
                    if kind:
                        if slug not in hits or best > hits[slug][1]:
                            hits[slug] = (kind, best, a)
                    elif best >= FUZZY_REVIEW:
                        rev[slug] = (best, a)
            for slug, (kind, score, a) in hits.items():
                matched.append({**base, "startup_slug": slug, "match_type": kind, "match_score": round(score, 3),
                                "matched_applicant_string": a, "from_own_query": slug == q_slug})
            if not hits:
                for slug, (score, a) in rev.items():
                    review.append({**base, "candidate_slug": slug, "match_score": round(score, 3), "applicant_string": a,
                                   "review_reason": "fuzzy_threshold_review"})
                if not rev:
                    unmatched.append(base)
        else:
            if is_homonym_mismatch(q_slug, p):
                review.append({**base, "candidate_slug": q_slug, "match_score": 0.0,
                               "applicant_string": f"Query: {q_slug}",
                               "review_reason": "international_query_homonym_mismatch"})
            else:
                matched.append({**base, "startup_slug": q_slug, "match_type": "query_direct", "match_score": 1.0,
                                "matched_applicant_string": f"Targeted query: {q_slug}", "from_own_query": True})

    m = pd.DataFrame(matched).drop_duplicates(["pub_number", "startup_slug"]) if matched else pd.DataFrame(
        columns=list(COLS) + ["startup_slug"])

    if not m.empty:
        # Filing year from the application date. Where the export has no date (manual single-record entries),
        # fall back to the year prefix of an Indian application number such as 201921045548.
        date_series = m["app_date"].fillna("").astype(str)
        m["filing_year"] = pd.to_datetime(date_series, format="%d.%m.%Y", errors="coerce").dt.year
        m["filing_year"] = m["filing_year"].fillna(pd.to_datetime(date_series, dayfirst=True, errors="coerce").dt.year)
        in_year = m["app_number"].astype(str).str.extract(r"^(20\d{2})\d{8}$")[0].astype(float)
        m["filing_year"] = m["filing_year"].fillna(in_year)
        m["filing_year_source"] = m["app_date"].fillna("").astype(str).str.len().gt(0).map(
            {True: "application_date", False: "IN_application_number_prefix"})

    m.to_csv(OUT / "patents_matched.csv", index=False)
    pd.DataFrame(review).to_csv(OUT / "patents_review.csv", index=False)
    pd.DataFrame(unmatched).to_csv(OUT / "patents_unmatched.csv", index=False)

    # Startup level aggregation. WIPO exports carry no legal-status field, so no granted/pending split is attempted.
    if m.empty:
        agg = pd.DataFrame({"slug": st["slug"], "patent_records": 0})
    else:
        m["is_pct"] = m["country"].str.upper().eq("WO")
        m["is_in"] = m["country"].str.upper().eq("IN")
        agg = m.groupby("startup_slug").agg(
            patent_records=("pub_number", "nunique"),
            pct_wo_records=("is_pct", "sum"),
            india_records=("is_in", "sum"),
            earliest_filing_year=("filing_year", "min"),
            latest_filing_year=("filing_year", "max"),
        ).reset_index().rename(columns={"startup_slug": "slug"})
        m = m.drop(columns=["is_pct", "is_in"])

    merged = st.merge(agg, on="slug", how="left")
    for c in ("patent_records", "pct_wo_records", "india_records"):
        merged[c] = merged[c].fillna(0).astype(int)
    merged["has_wipo_download"] = merged["slug"].isin(raw["query_startup_slug"].unique())

    # Record what the PATENTSCOPE search returned, so a zero is explained in the data and not only in the README.
    log = RAW / "download_log.csv"
    if log.exists():
        lg = pd.read_csv(log, dtype=str).fillna("")
        def outcome(s):
            x = re.search(r"(\d+) results", s)
            return f"{x.group(1)} hits" if x else "1 hit (record view, no export button)"
        lg["wipo_query_outcome"] = lg["page_text_snippet"].map(outcome)
        merged = merged.merge(lg[["slug", "wipo_query_outcome"]], on="slug", how="left")

    merged.to_csv(OUT / "startups_with_patents.csv", index=False)
    with pd.ExcelWriter(OUT / "startups_with_patents.xlsx") as xw:
        merged.to_excel(xw, "startups_with_patents", index=False)
        m.to_excel(xw, "patents_matched", index=False)
        pd.DataFrame(review).to_excel(xw, "needs_review", index=False)

    print(merged[["rank", "name", "patent_records", "pct_wo_records", "india_records", "wipo_query_outcome"]].to_string(index=False))
    print(f"\nMatched records: {len(m)}")
    print(f"Review records: {len(review)}")
    print(f"Unmatched records: {len(unmatched)}")


if __name__ == "__main__":
    main()

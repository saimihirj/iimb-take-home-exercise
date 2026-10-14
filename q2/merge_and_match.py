#!/usr/bin/env python3
"""
Q2.2b - Merge raw WIPO PATENTSCOPE exports with the Top-20 startup table and document the match quality.

Inputs : data/wipo_raw/*.csv|xls|xlsx   (raw, untouched PATENTSCOPE exports; file name starts with  <startup-slug>__ )
         startups/startups_top20.csv
Outputs: data/merged/patents_matched.csv      one row per (patent, startup) after matching
         data/merged/patents_review.csv       fuzzy / ambiguous matches a human should eyeball
         data/merged/patents_unmatched.csv    exported rows whose applicants matched NO startup (false hits of the query)
         data/merged/startups_with_patents.csv / .xlsx   startup table + patent KPIs  (the "merged" deliverable)

MATCHING PROCESS (also in README.md)
 1. Normalise every applicant string: Unicode-fold, lower-case, drop punctuation, remove legal-form words
    (private, pvt, ltd, limited, inc, llp, llc, corp, india, technologies ...) and collapse spaces.
 2. Split multi-applicant cells on ';' '|' newline and ' / '.
 3. Compare each applicant with each startup's normalised {legal entity, brand name, aliases}.
      exact   : identical normalised string                              -> accepted
      fuzzy   : similarity (difflib ratio on tokens) >= 0.90                -> accepted, flagged 'fuzzy'
      review  : 0.80 <= similarity < 0.90                                  -> NOT accepted; written to patents_review.csv
 4. A patent can match several startups (co-applicants) -> one row per pair.
 5. De-duplicate on (publication number, startup).
 6. Filing/Granting status is inferred from the publication kind code (see KIND_GRANTED); this is a heuristic since the
    export has no explicit "granted" flag for every office.
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
# Kind codes treated as "granted" (US B1/B2, EP B1, IN/CN/KR/JP B/C/S etc). A1/A2/A3/A4/A9 = application publications.
KIND_GRANTED = re.compile(r"^(B\d?|C\d?|S\d?|T\d?|Y\d?)$")

# header-name tolerant mapping: canonical -> substrings to look for in lower-cased column names
COLS = {
    "pub_number": ["publication number", "pub. no", "publication no", "pub number"],
    "pub_date": ["publication date", "pub. date"],
    "app_number": ["application number", "appl. no"],
    "app_date": ["application date", "filing date", "appl. date"],
    "title": ["title"],
    "applicants": ["applicant"],
    "inventors": ["inventor"],
    "ipc": ["ipc", "main ipc"],
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
    ta, tb = " ".join(sorted(a.split())), " ".join(sorted(b.split()))   # order-insensitive
    return max(SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, ta, tb).ratio())


def read_any(path):
    if path.suffix.lower() == ".csv":
        try:
            return pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(path, dtype=str, encoding="latin-1", sep=None, engine="python")
    df = pd.read_excel(path, dtype=str)
    # PATENTSCOPE .xls exports sometimes carry a few banner rows before the header
    for i in range(min(10, len(df))):
        if any("applicant" in str(c).lower() for c in df.iloc[i].values):
            df.columns = df.iloc[i].values
            df = df.iloc[i + 1:]
            break
    return df


def canon_columns(df):
    ren = {}
    low = {c: str(c).lower() for c in df.columns}
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
        df = canon_columns(read_any(f)).fillna("")
        df["query_startup_slug"], df["raw_file"] = slug, f.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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
        print("No raw WIPO files in", RAW, "- run wipo_download.py first (or drop manual exports there).")
        return
    raw["pub_number"] = raw["pub_number"].str.strip()
    raw = raw.drop_duplicates(["pub_number", "query_startup_slug"])

    matched, review, unmatched = [], [], []
    for _, p in raw.iterrows():
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
        base = p.to_dict()
        for slug, (kind, score, a) in hits.items():
            matched.append({**base, "startup_slug": slug, "match_type": kind, "match_score": round(score, 3),
                            "matched_applicant_string": a, "from_own_query": slug == p["query_startup_slug"]})
        if not hits:
            for slug, (score, a) in rev.items():
                review.append({**base, "candidate_slug": slug, "match_score": round(score, 3), "applicant_string": a})
            if not rev:
                unmatched.append(base)

    m = pd.DataFrame(matched).drop_duplicates(["pub_number", "startup_slug"]) if matched else pd.DataFrame(
        columns=list(COLS) + ["startup_slug"])
    if not m.empty:
        m["is_granted_heuristic"] = m["kind"].str.strip().str.upper().apply(lambda k: bool(KIND_GRANTED.match(k)))
        m["pub_year"] = pd.to_datetime(m["pub_date"], errors="coerce", dayfirst=True).dt.year
    m.to_csv(OUT / "patents_matched.csv", index=False)
    pd.DataFrame(review).to_csv(OUT / "patents_review.csv", index=False)
    pd.DataFrame(unmatched).to_csv(OUT / "patents_unmatched.csv", index=False)

    # ----- startup-level merge -----
    if m.empty:
        agg = pd.DataFrame({"slug": st["slug"]})
        agg["patent_records"] = 0
    else:
        agg = m.groupby("startup_slug").agg(
            patent_records=("pub_number", "nunique"),
            granted_records_heuristic=("is_granted_heuristic", "sum"),
            first_pub_year=("pub_year", "min"), last_pub_year=("pub_year", "max"),
            fuzzy_matches=("match_type", lambda s: int((s == "fuzzy").sum())),
        ).reset_index().rename(columns={"startup_slug": "slug"})
    merged = st.merge(agg, on="slug", how="left")
    merged["patent_records"] = merged["patent_records"].fillna(0).astype(int)
    merged["has_wipo_download"] = merged["slug"].isin(raw["query_startup_slug"].unique())
    merged.to_csv(OUT / "startups_with_patents.csv", index=False)
    with pd.ExcelWriter(OUT / "startups_with_patents.xlsx") as xw:
        merged.to_excel(xw, "startups_with_patents", index=False)
        m.to_excel(xw, "patents_matched", index=False)
        pd.DataFrame(review).to_excel(xw, "needs_review", index=False)
    print(merged[["rank", "name", "patent_records", "has_wipo_download"]].to_string(index=False))
    print(f"\nmatched={len(m)}  review={len(review)}  unmatched={len(unmatched)}")


if __name__ == "__main__":
    main()

"""Pre-flight check: for each top-20 site report live status (several URL variants), Wayback month coverage, about links."""
import csv
from concurrent.futures import ThreadPoolExecutor
import wayback_scraper as w

rows = w.load_sites(None)


def check(item):
    name, site = item
    home, host = w.normalise_site(site)
    live = {}
    for v in (home, f"https://www.{host}/", f"http://{host}/"):
        r = w.polite_get(v, timeout=20, retries=1)
        live[v] = (r.status_code, len(r.text), r.url) if r is not None else None
    snaps = w.cdx_monthly(home, "2022-01", "2026-09")
    links = []
    if snaps:
        ts, o = sorted(snaps.items())[-1][1]
        r = w.polite_get(w.WAYBACK_RAW.format(ts=ts, url=o))
        if r is not None and r.status_code == 200:
            links = w.extract_about_links(r.text, o)
    return name, home, live, len(snaps), links


with ThreadPoolExecutor(4) as ex:
    for res in ex.map(check, rows):
        print(res, flush=True)

#!/usr/bin/env python3
"""Build static per-ZIP frost-date JSON from NOAA 1991-2020 U.S. Climate Normals.

Source: NOAA NCEI Annual/Seasonal Normals (station CSVs, agricultural normals)
        + U.S. Census ZCTA gazetteer (ZIP centroids).
Output: site/frost/<zip>.json  (static API, host on GitHub Pages)

Safe by design: auto-detects the date encoding, then verifies it against a
known station (eastern-US stations). If anything looks wrong the build aborts and
nothing is published.
"""
import argparse, csv, datetime as dt, io, json, math, os, re, sys, tarfile, urllib.request, zipfile
import numpy as np
from scipy.spatial import cKDTree

NCEI_DIR = "https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/archive/"
GAZ_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
           "2023_Gazetteer/2023_Gaz_zcta_national.zip")
LAST_RE = re.compile(r"PRBLST.*T32.*50", re.I)    # last spring 32F, 50% probability
FIRST_RE = re.compile(r"PRBFST.*T32.*50", re.I)   # first fall 32F, 50% probability
SOURCE = "NOAA NCEI 1991-2020 U.S. Climate Normals (Annual/Seasonal), 32F, 50% probability"
MAX_MI, WARN_MI = 100.0, 50.0
UA = {"User-Agent": "trmnl-farmers-almanac-data/1.0"}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300)


def find_tar_url():
    html = fetch(NCEI_DIR).read().decode("utf-8", "replace")
    links = re.findall(r'href="([^"]+\.tar\.gz)"', html)
    for l in links:
        if "by-station" in l and "annualseasonal" in l and "multivariate" in l:
            return NCEI_DIR + l
    sys.exit("Could not find the by-station tarball. Links seen: %s" % links)


def mmdd(value, fmt):
    s = value.strip()
    if fmt == "slash":
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", s)
        if not m:
            return None
        try:
            dt.date(2001, int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
        return "%02d-%02d" % (int(m.group(1)), int(m.group(2)))
    try:
        f = float(s)
    except ValueError:
        return None
    if not math.isfinite(f) or f <= 0 or f != int(f):
        return None
    s = str(int(f))
    if fmt == "doy":
        n = int(s)
        if n > 366:
            return None
        d = dt.date(2001, 1, 1) + dt.timedelta(days=min(n, 365) - 1)
        return "%02d-%02d" % (d.month, d.day)
    s = s.zfill(4)
    try:
        dt.date(2001, int(s[:2]), int(s[2:]))
    except ValueError:
        return None
    return s[:2] + "-" + s[2:]


def stations(tar_fileobj):
    """Yield (id, name, lat, lon, raw_last, raw_first) for stations with both values."""
    seen_cols = False
    with tarfile.open(fileobj=tar_fileobj, mode="r|gz") as tf:
        for m in tf:
            if not (m.isfile() and m.name.lower().endswith(".csv")):
                continue
            rows = list(csv.DictReader(io.StringIO(tf.extractfile(m).read().decode("utf-8-sig"))))
            if not rows:
                continue
            row = rows[0]
            cols = [c for c in row if not c.upper().endswith("ATTRIBUTES")]
            lc = next((c for c in cols if LAST_RE.search(c)), None)
            fc = next((c for c in cols if FIRST_RE.search(c)), None)
            if not seen_cols and (lc or fc):
                seen_cols = True
                frosty = [c for c in cols if re.search(r"PRB(LST|FST)", c, re.I)]
                print("Frost columns in first file that has them (%d): %s" % (len(frosty), frosty[:12]))
            if not (lc and fc):
                continue
            try:
                lat, lon = float(row["LATITUDE"]), float(row["LONGITUDE"])
            except (KeyError, ValueError):
                continue
            yield row.get("STATION", ""), row.get("NAME", "").title(), lat, lon, row[lc], row[fc]


def pick_format(st):
    """Calibrate the date encoding on eastern-US stations; abort if ambiguous.

    In that region last-spring 32F is ~Feb 15-Jun 15 and first-fall 32F is
    ~Sep 15-Dec 15. The right encoding fits nearly all stations; a wrong one
    does not. If neither is clearly right, abort so nothing bad is published.
    """
    ref = [x for x in st if 30 <= x[2] <= 45 and -100 <= x[3] <= -70]
    if len(ref) < 5:
        sys.exit("Too few calibration stations (%d); aborting." % len(ref))
    best = {}
    for fmt in ("slash", "mmdd", "doy"):
        ok = 0
        for x in ref:
            a, b = mmdd(x[4], fmt), mmdd(x[5], fmt)
            if a and b and "02-15" <= a <= "06-15" and "09-15" <= b <= "12-15":
                ok += 1
        best[fmt] = ok / len(ref)
    ranked = sorted(best, key=best.get, reverse=True)
    fmt, other = ranked[0], ranked[1]
    print("Date format fit: %s" % best)
    if best[fmt] < 0.85 or best[other] > 0.5:
        sys.exit("Calibration failed: encoding is ambiguous; aborting.")
    return fmt


def unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def read_zips(path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".txt"))
        rdr = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8"), delimiter="\t")
        hdr = [h.strip() for h in next(rdr)]
        gi, li, oi = hdr.index("GEOID"), hdr.index("INTPTLAT"), hdr.index("INTPTLONG")
        return [(r[gi].strip(), float(r[li]), float(r[oi])) for r in rdr if len(r) > oi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tar", help="local by-station tar.gz (testing)")
    ap.add_argument("--gaz", help="local gazetteer zip (testing)")
    ap.add_argument("--out", default="site")
    a = ap.parse_args()

    tar_obj = open(a.tar, "rb") if a.tar else fetch(find_tar_url())
    st = list(stations(tar_obj))
    print("Stations with frost normals:", len(st))
    print("Sample raw (last, first) values:", [(x[4], x[5]) for x in st[:12]])
    if len(st) < 500 and not a.tar:
        sys.exit("Too few stations (%d); aborting." % len(st))
    fmt = pick_format(st)

    good = []
    for sid, name, lat, lon, rl, rf in st:
        l, f = mmdd(rl, fmt), mmdd(rf, fmt)
        if l and f:
            good.append((sid, name, lat, lon, l, f))
    print("Stations with valid dates:", len(good))
    tree = cKDTree(unit(np.array([g[2] for g in good]), np.array([g[3] for g in good])))

    gaz = a.gaz or "gaz.zip"
    if not a.gaz:
        open(gaz, "wb").write(fetch(GAZ_URL).read())
    zips = read_zips(gaz)
    chord, idx = tree.query(unit(np.array([z[1] for z in zips]), np.array([z[2] for z in zips])))
    miles = 2 * 3958.8 * np.arcsin(np.clip(chord / 2, 0, 1))

    os.makedirs(os.path.join(a.out, "frost"), exist_ok=True)
    n = 0
    for (z, _, _), i, d in zip(zips, idx, miles):
        if d > MAX_MI:
            continue
        sid, name, _, _, l, f = good[i]
        days = (dt.date(2001, int(f[:2]), int(f[3:])) - dt.date(2001, int(l[:2]), int(l[3:]))).days
        rec = {"zip": z, "last_frost": l, "first_frost": f, "season_days": days,
               "station": name, "station_id": sid, "distance_mi": round(float(d), 1),
               "low_confidence": bool(d > WARN_MI), "source": SOURCE}
        with open(os.path.join(a.out, "frost", z + ".json"), "w") as fh:
            json.dump(rec, fh, separators=(",", ":"))
        n += 1
    meta = {"built": dt.date.today().isoformat(), "zips": n, "stations": len(good), "source": SOURCE}
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"))
    open(os.path.join(a.out, "index.html"), "w").write(
        "<!doctype html><title>TRMNL Farmer's Almanac data</title>"
        "<p>Static frost-date API: <code>/frost/&lt;zip&gt;.json</code>. Data: %s. "
        "Estimates only; microclimates vary. Built %s.</p>" % (SOURCE, meta["built"]))
    print("Wrote %d ZIP files" % n)
    if n < 20000 and not a.tar:
        sys.exit("Suspiciously few ZIP files (%d); aborting." % n)


if __name__ == "__main__":
    main()

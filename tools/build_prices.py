#!/usr/bin/env python3
"""Build prices.json from retailer quote files.

Usage: python3 tools/build_prices.py tools/quotes-YYYY-MM-DD-*.json > prices.json

Each quote file is a JSON array of {id, store, url, fetched, vitolas:[...], notes} objects, one per
(catalog line, store), as the monthly fetch produces them. Vitola rows carry single, fivePack
(pack price; packCount when not 5), box, count, inStock.

Per stick, in order of trust: the single price; the box price divided by its count (the count
borrowed from another store's quote of the same size when a store doesn't print it); the pack
price divided by its count. Quotes marked out of stock still count — they are the price the
store asks — but a store whose whole line is sold-out clearance is left out (note says so).
Vitolas are grouped by size within a line, since names vary store to store; the catalog's own
vitola name is used when a size matches one, else the most common store name.
"""
import json, sys, statistics, re, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
catalog = {e["brand"] + "|" + e["line"]: e for e in json.load(open(ROOT / "catalog.json"))}
sources = json.load(open(ROOT / "sources.json"))
stores = sources["stores"]

def size_key(s):
    """'5.375 x 52' → (5.38, 52); tolerant of '5 1/2 x 50', '6x60', '3 15/16 x 60'."""
    if not s: return None
    t = s.lower().replace("×", "x").replace('"', "")
    m = re.match(r"\s*(\d+(?:\.\d+)?)(?:\s+(\d+)/(\d+))?\s*x\s*(\d+)", t)
    if not m: return None
    length = float(m.group(1)) + (float(m.group(2)) / float(m.group(3)) if m.group(2) else 0)
    return (round(length, 2), int(m.group(4)))

def catalog_name(entry, key):
    if not entry: return None
    for v in entry["vitolas"]:
        if size_key(v["size"]) == key: return v["name"]
    return None

quotes = []
for path in sys.argv[1:]:
    quotes += json.load(open(path))

by_line = {}
for q in quotes:
    if "clearance" in (q.get("notes") or "").lower(): continue
    by_line.setdefault(q["id"], []).append(q)

out_lines = []
for line_id, qs in sorted(by_line.items()):
    entry = catalog.get(line_id)
    # Group every row by size
    groups = {}
    for q in qs:
        for v in q["vitolas"]:
            k = size_key(v.get("size"))
            if not k: continue
            groups.setdefault(k, []).append((q, v))
    vitolas = []
    for k, rows in sorted(groups.items()):
        known_count = next((v["count"] for _, v in rows if v.get("count")), None)
        names = [v["vitola"] for _, v in rows]
        name = catalog_name(entry, k) or max(sorted(set(names)), key=names.count)  # sorted: same name every run on ties
        qlist, per_stick = [], []
        for q, v in rows:
            count = v.get("count") or known_count
            pack_n = v.get("packCount") or 5
            if v.get("single"):
                stick, basis = v["single"], "single"
            elif v.get("box") and count:
                stick, basis = round(v["box"] / count, 2), "box"
            elif v.get("fivePack"):
                stick, basis = round(v["fivePack"] / pack_n, 2), "pack"
            else:
                stick, basis = None, None
            qlist.append({"store": q["store"], "name": v["vitola"], "single": v.get("single"),
                          "box": v.get("box"), "count": count, "pack": v.get("fivePack"), "packCount": pack_n if v.get("fivePack") else None,
                          "perStick": stick, "basis": basis, "inStock": v.get("inStock"), "url": q["url"], "fetched": q["fetched"]})
            if stick: per_stick.append(stick)
        stats = {"low": min(per_stick), "median": round(statistics.median(per_stick), 2), "high": max(per_stick), "stores": len(per_stick)} if per_stick else None
        vitolas.append({"name": name, "size": f"{k[0]:g} x {k[1]}", **(stats or {"low": None, "median": None, "high": None, "stores": 0}), "quotes": qlist})
    fetched = max(q["fetched"] for q in qs)
    out_lines.append({"id": line_id, "display": (entry["line"] if entry and entry["line"].startswith(entry["brand"]) else f"{entry['brand']} {entry['line']}") if entry else line_id,
                      "fetched": fetched, "storesTried": sorted({q["store"] for q in qs}),
                      "storesWithPrices": sorted({q["store"] for q in qs if q["vitolas"]}), "vitolas": vitolas})

prices = {"schema": 1, "generated": datetime.date.today().isoformat(),
          "stores": {k: {"name": v["name"], "home": v["home"]} for k, v in stores.items()},
          "note": "perStick basis: single = listed single price; box = box price / count; pack = pack price / pack size. low/median/high are across stores.",
          "lines": out_lines}
json.dump(prices, sys.stdout, indent=1, ensure_ascii=False)

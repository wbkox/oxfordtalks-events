#!/usr/bin/env python3
"""
sync-luma: pull Oxford Talks events from Luma and write them for the site.

Reads Luma's public calendar endpoint (no key, public events only) for each calendar in
CALENDARS, normalises the events into the compact shape the homepage rail renders from
(window.OT_EVENTS), and writes:

  events.json   the list, upcoming soonest-first then past newest-first
  events.js     window.OT_EVENTS=[...]; served by GitHub Pages at a fixed URL, loaded by oxfordtalks.io

The site never calls Luma from the browser (Luma sends no CORS headers), so this script is the
sync. GitHub Actions runs it daily and commits the two files; GitHub Pages serves them.
"""
import json, sys, subprocess, datetime, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root
CALENDARS = ["cal-djel2Nc4RreIsVD",  # Oxford Talks (luma.com/oxfordtalks)
             "cal-qbQ4TJiyJAVhyGp"]  # Waleed's personal calendar, where the events currently live
MAX_UP, MAX_PAST = 8, 6
TEAM = {"Waleed Khalid", "Wiktoria Korbecka", "Matt Bateman", "Michaela", "Kate Lincoln", "Stripe Community", "Robin Jones"}

def fetch(cal, period):
    url = f"https://api.lu.ma/calendar/get-items?calendar_api_id={cal}&period={period}&pagination_limit=50"
    # curl rather than urllib: the python.org build on this Mac has no root certificates
    out = subprocess.run(["curl", "-sS", "--max-time", "20", url], capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("entries", [])

def money(ti):
    if not ti: return ""
    if ti.get("is_free"): return "Free"
    p = ti.get("price") or {}
    if not p.get("cents"): return ""
    sym = {"gbp": "£", "usd": "$", "eur": "€"}.get(p.get("currency", ""), p.get("currency", "").upper() + " ")
    c = p["cents"]
    return f"{sym}{c // 100}" if c % 100 == 0 else f"{sym}{c / 100:.2f}"

def norm(entry):
    ev = entry["event"]
    if ev.get("visibility") != "public": return None
    geo = ev.get("geo_address_info") or {}
    loc = " · ".join(x for x in [geo.get("city"), geo.get("address")] if x) if geo else ("Online" if ev.get("location_type") in ("zoom", "online", "google_meet") else "")
    hosts = [h.get("name", "") for h in entry.get("hosts", [])]
    guests = [h for h in hosts if h not in TEAM]
    ti = entry.get("ticket_info") or {}
    return {
        "id": ev["api_id"],
        "n": ev["name"].strip(),
        "s": ev["start_at"], "e": ev.get("end_at"), "tz": ev.get("timezone") or "Europe/London",
        "u": "https://luma.com/" + ev["url"],
        "c": ev.get("cover_url") or "",
        "l": loc,
        "p": money(ti),
        "so": bool(ti.get("is_sold_out")),
        "t": "Salon" if "salon" in ev["name"].lower() else "Event",
        "w": ("With " + guests[0]) if guests else "Hosted by Oxford Talks",
    }

def main():
    seen, out = set(), []
    for cal in CALENDARS:
        for period in ("future", "past"):
            for e in fetch(cal, period):
                n = norm(e)
                if n and n["id"] not in seen:
                    seen.add(n["id"]); out.append(n)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    up = sorted([e for e in out if e["s"] >= now], key=lambda e: e["s"])[:MAX_UP]
    past = sorted([e for e in out if e["s"] < now], key=lambda e: e["s"], reverse=True)[:MAX_PAST]
    events = up + past
    (ROOT / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1) + "\n")
    js = "/* Oxford Talks events from Luma. Written daily by scripts/sync-luma.py in github.com/wbkox/oxfordtalks-events; read by ot-events.js on oxfordtalks.io. */\nwindow.OT_EVENTS=" + json.dumps(events, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "events.js").write_text(js)
    print(f"{len(up)} upcoming, {len(past)} past, {len(js)} bytes")
    for e in events: print(" ", e["s"][:10], e["n"], "|", e["l"], "|", e["p"] or "—", "|", e["w"])

if __name__ == "__main__":
    main()

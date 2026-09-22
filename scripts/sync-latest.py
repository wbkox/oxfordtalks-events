#!/usr/bin/env python3
"""
sync-latest: find the newest talk on the Oxford Talks YouTube channel and write it for the homepage.

Reads the channel's public RSS feed (no key), keeps talks only (no Shorts, no podcast episodes),
and for the newest one writes:

  latest.json              the talk: id, title, orator, date, length, chapters, links, images,
                           plus "more": the next newest talks the site lists (one per orator, up to four)
  latest.js                window.OT_LATEST={...}; served by GitHub Pages, loaded by oxfordtalks.io
  latest/<id>-poster.jpg   YouTube's own still, 1280x720
  latest/<id>-sprite.jpg   40 frames of the talk side by side, 384x216 each, for the hover scrub

Chapters come from the timestamps in the video description ("0:00 Title" lines). The orator's
portrait and Fellow mark come from the live site (the orator page and the Talks page data), so a
talk by someone not yet on the site still shows, without portrait or mark, until the CMS catches up.

The sprite needs the video: yt-dlp + ffmpeg. If YouTube refuses the download (cloud runners are
sometimes challenged), the poster still ships and the tile simply has no hover scrub until the next
successful run. The homepage keeps its own fallback if this file is unreachable.
"""
import json, re, subprocess, pathlib, datetime, sys, html, unicodedata, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANNEL = "UCl74XQsIUqpb5JOkdCtlPeQ"
SITE = "https://www.oxfordtalks.io"
PAGES = "https://wbkox.github.io/oxfordtalks-events"
FRAMES, FW, FH = 40, 384, 216
MEDIA = ROOT / "latest"

def curl(url, binary=False, timeout=30):
    r = subprocess.run(["curl", "-sSL", "--max-time", str(timeout), "-A", "Mozilla/5.0 (oxfordtalks-events)", url],
                       capture_output=True, check=False)
    if r.returncode != 0: return None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")

def slugify(s):
    s = unicodedata.normalize("NFKC", s).lower().replace("&", " and ")
    s = re.sub(r"['’]", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:120]

def feed():
    xml = curl(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}")
    if not xml: sys.exit("feed unreachable")
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        g = lambda tag: html.unescape((re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", e, re.S) or [None, ""])[1]).strip()
        link = (re.search(r'<link rel="alternate" href="([^"]+)"', e) or [None, ""])[1]
        out.append({"id": g("yt:videoId"), "title": g("title"), "published": g("published")[:10],
                    "link": link, "desc": g("media:description")})
    return out

def is_talk(v):
    t = v["title"]
    if "/shorts/" in v["link"]: return False
    if re.search(r"podcast|\bEP\s?\d+\b", t, re.I): return False
    if " | " not in t: return False          # every talk is "Title | Orator"
    return True

def watch(vid):
    """Length in seconds from the watch page; None if YouTube did not answer."""
    page = curl(f"https://www.youtube.com/watch?v={vid}")
    m = page and re.search(r'"lengthSeconds":"(\d+)"', page)
    return int(m.group(1)) if m else None

def chapters(desc):
    ch = []
    for line in desc.splitlines():
        m = re.match(r"^\s*\(?(\d{1,2}):(\d{2})(?::(\d{2}))?\)?\s*[-–—:]?\s*(.+?)\s*$", line)
        if not m: continue
        h, mnt, s, label = m.groups()
        t = (int(h) * 3600 + int(mnt) * 60 + int(s)) if s else (int(h) * 60 + int(mnt))
        ch.append({"t": t, "l": label})
    if len(ch) < 2 or ch[0]["t"] != 0: return []
    return ch

def site_data():
    """arcdata from the live Talks page: yt -> {slug, label, dur}."""
    page = curl(f"{SITE}/talks") or ""
    m = re.search(r'src="([^"]*ot-talks-data[^"]*\.js)"', page)
    if not m: return {}
    js = curl(m.group(1), timeout=60) or ""
    m = re.search(r"var D=(\{[\s\S]*?\});\s*(?:window|for|Object|\})", js)
    try: D = json.loads(m.group(1))
    except Exception: return {}
    return {t["yt"]: t for t in D.get("arcdata", [])}

def portrait(slug):
    """The orator page's image, only if the page exists. A missing page is Webflow's 404, which still
    carries the site-wide share image; that is not a portrait, so the tile goes without one instead."""
    r = subprocess.run(["curl", "-sSL", "--max-time", "30", "-A", "Mozilla/5.0 (oxfordtalks-events)",
                        "-w", "\n%{http_code}", f"{SITE}/speakers/{slug}"], capture_output=True, check=False)
    page, _, code = r.stdout.decode("utf-8", "replace").rpartition("\n")
    if r.returncode != 0 or code.strip() != "200" or "og:image" not in page: return None
    m = re.search(r'<meta content="([^"]+)" property="og:image"', page) or re.search(r'property="og:image" content="([^"]+)"', page)
    if not m or "og-share" in m.group(1): return None
    return m.group(1)

def media(vid, dur):
    MEDIA.mkdir(exist_ok=True)
    poster, sprite = MEDIA / f"{vid}-poster.jpg", MEDIA / f"{vid}-sprite.jpg"
    if not poster.exists():
        for name in ("maxresdefault", "sddefault", "hqdefault"):
            b = curl(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", binary=True)
            if b and len(b) > 5000 and b[:2] == b"\xff\xd8":
                poster.write_bytes(b); break
    if not sprite.exists():
        mp4 = MEDIA / f"{vid}.mp4"
        try:
            subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "bv*[height<=480][ext=mp4]/b[height<=480]/b",
                            "-o", str(mp4), f"https://www.youtube.com/watch?v={vid}"], check=True, timeout=600)
            d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                                     capture_output=True, text=True, check=True).stdout.strip())
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf",
                            f"fps={FRAMES}/{d},scale={FW}:{FH}:force_original_aspect_ratio=increase,crop={FW}:{FH},tile={FRAMES}x1",
                            "-frames:v", "1", "-q:v", "4", str(sprite)], check=True, timeout=600)
        except Exception as e:
            print("sprite skipped:", e)
        finally:
            if mp4.exists(): mp4.unlink()
    # keep only this talk's files
    for f in MEDIA.iterdir():
        if not f.name.startswith(vid): f.unlink()
    return (f"{PAGES}/latest/{poster.name}" if poster.exists() else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            f"{PAGES}/latest/{sprite.name}" if sprite.exists() else None)

def main():
    talks = [v for v in feed() if is_talk(v)]
    if not talks: sys.exit("no talk in the feed")
    talks.sort(key=lambda v: v["published"], reverse=True)
    v = talks[0]
    title, name = [s.strip() for s in v["title"].split(" | ")[:2]]
    dur = watch(v["id"])
    site = site_data()
    arc = site.get(v["id"], {})
    # the next newest talks the site lists (its own editorial list), one per orator, other orators only, at most four
    more = []
    for a in sorted(site.values(), key=lambda a: a.get("date", ""), reverse=True):
        if a["yt"] == v["id"] or a.get("speaker") == name or any(m["name"] == a.get("speaker") for m in more): continue
        mm, ss = (a.get("dur") or "0:00").split(":")
        more.append({"yt": a["yt"], "title": a.get("title"), "name": a.get("speaker"), "slug": a.get("slug"),
                     "dur": int(mm) * 60 + int(ss), "date": a.get("date")})
        if len(more) == 4: break
    if not dur and arc.get("dur"):
        mm, ss = arc["dur"].split(":"); dur = int(mm) * 60 + int(ss)
    slug = arc.get("slug") or slugify(name)
    img = portrait(slug)
    poster, sprite = media(v["id"], dur)
    out = {"yt": v["id"], "title": title, "name": name, "date": v["published"], "dur": dur or 0,
           "fellow": arc.get("label") == "Fellow", "slug": slug if img else None, "portrait": img,
           "ch": chapters(v["desc"]), "more": more, "poster": poster, "sprite": sprite, "frames": FRAMES,
           "written": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    # the job runs hourly: leave the files alone unless something other than the timestamp moved
    try:
        was = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
        if {k: v for k, v in was.items() if k != "written"} == {k: v for k, v in out.items() if k != "written"}:
            print(f"latest talk unchanged: {name} · {title}"); return
    except Exception:
        pass
    (ROOT / "latest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "latest.js").write_text(
        "/* Oxford Talks: the newest talk on YouTube. Written daily by scripts/sync-latest.py in github.com/wbkox/oxfordtalks-events; read by the homepage of oxfordtalks.io. */\n"
        "window.OT_LATEST=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"latest talk: {name} · {title} · {v['published']} · {dur}s · {len(out['ch'])} chapters · sprite {'yes' if sprite else 'no'} · portrait {'yes' if img else 'no'}")

if __name__ == "__main__":
    main()

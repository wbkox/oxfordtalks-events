#!/usr/bin/env python3
"""
sync-views: real YouTube view counts for every published talk, so the site's "Most watched" means it.

Waleed, 19 Sep 2026: "most watched should be directly correlated to how many views it has on YouTube",
and later the same day: "it needs to sync live directly from YouTube, so it can move the most watched
talks all by itself." Until then the Talks page sorted on numbers copied once into a data snapshot.

Runs daily here beside sync-luma.py and sync-latest.py. The talks to count are in views-ids.json
(one line per talk: YouTube id, title, orator), kept in this repo so the job needs nothing from the
website's private repo. yt-dlp reads the counts — no API key, no quota — and a video that fails is
left out, so the page keeps the number it already had rather than showing a zero.

Writes views.js (window.OT_VIEWS = { "<yt id>": <views>, ... }) and views.json, at the repo root,
where GitHub Pages serves them:  https://wbkox.github.io/oxfordtalks-events/views.js
"""
import json, subprocess, sys, pathlib, datetime, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDS  = ROOT / 'views-ids.json'
YTDLP = shutil.which('yt-dlp') or str(pathlib.Path.home() / '.local/bin/yt-dlp')

def fetch(ids):
    urls = [f'https://www.youtube.com/watch?v={i}' for i in ids]
    out = {}
    for k in range(0, len(urls), 20):                      # small batches: one bad id cannot sink the rest
        p = subprocess.run([YTDLP, '--no-warnings', '--ignore-errors', '--skip-download',
                            '--print', '%(id)s %(view_count)s'] + urls[k:k+20],
                           capture_output=True, text=True)
        for line in p.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                out[parts[0]] = int(parts[1])
    return out

talks = json.load(open(IDS, encoding='utf-8'))
ids = [t['yt'] for t in talks]
views = fetch(ids)
missing = [i for i in ids if i not in views]
if len(views) < len(ids) * 0.8:
    sys.exit(f'only {len(views)} of {len(ids)} counts came back; keeping the previous files')

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
(ROOT / 'views.json').write_text(json.dumps(views, indent=0, sort_keys=True) + '\n', encoding='utf-8')
(ROOT / 'views.js').write_text(
    f'/* Oxford Talks — real YouTube view counts, refreshed daily by scripts/sync-views.py.\n'
    f'   {stamp}, {len(views)} of {len(ids)} talks. Read by the Talks page for "Most watched". Do not hand-edit. */\n'
    f'window.OT_VIEWS={json.dumps(views, sort_keys=True, separators=(",", ":"))};\n', encoding='utf-8')
top = sorted(views.items(), key=lambda kv: -kv[1])[:3]
name = {t['yt']: t['orator'] for t in talks}
print(f'{len(views)} of {len(ids)} talks counted; missing: {missing or "none"}')
print('top:', ', '.join(f'{name.get(k, k)} {v:,}' for k, v in top))

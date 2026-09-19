# Oxford Talks events feed

`events.js` and `events.json` hold the public events from the Oxford Talks calendars on Luma,
upcoming first, then the most recent past ones. A GitHub Action refreshes them every morning
and the site's homepage loads `events.js` from GitHub Pages:

    https://wbkox.github.io/oxfordtalks-events/events.js

To refresh sooner, run the "Sync events from Luma" workflow from the Actions tab.
Nothing here is private: every event listed is public on Luma.

Each event carries `h`, the hosts who have a photo on Luma, guests before the Oxford Talks team,
so the homepage card can show the face of whoever is on the bill; plus `ap`, whether Luma asks
for approval, and `sr`, the places left.

## Latest talk

`latest.js` and `latest.json` hold the newest talk on the Oxford Talks YouTube channel: title,
orator, date, length, the chapters from the video description, and two images in `latest/`
(YouTube's still and a 40-frame strip for the hover scrub). The same Action refreshes them every
morning and the homepage loads:

    https://wbkox.github.io/oxfordtalks-events/latest.js

Published a talk and want it up now? Run the workflow from the Actions tab. Talks are found by
their titles ("Title | Orator"); Shorts and podcast episodes are skipped. Chapters appear when the
description carries "0:00 Title" lines. The hover strip needs the video download to succeed on the
runner; if YouTube refuses it, the still ships alone and the next successful run adds the strip.

## View counts

`views.js` and `views.json` hold the YouTube view count of every published talk, keyed by video id,
refreshed by the same Action every morning. The Talks page on the site loads `views.js` and sorts
"Most watched" on it, so the order follows YouTube by itself. The talks counted are listed in
`views-ids.json`; add a line when a talk is published.

    https://wbkox.github.io/oxfordtalks-events/views.js


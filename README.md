# Oxford Talks events feed

`events.js` and `events.json` hold the public events from the Oxford Talks calendars on Luma,
upcoming first, then the most recent past ones. A GitHub Action refreshes them every morning
and the site's homepage loads `events.js` from GitHub Pages:

    https://wbkox.github.io/oxfordtalks-events/events.js

To refresh sooner, run the "Sync events from Luma" workflow from the Actions tab.
Nothing here is private: every event listed is public on Luma.

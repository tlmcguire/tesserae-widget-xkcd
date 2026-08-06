# xkcd_comic widget for Tesserae

Shows the latest, a random, or a specific xkcd comic on a Tesserae e-ink
dashboard, and prints the **hovertext as a visible caption** under the
comic instead of leaving it as a mouseover-only tooltip, since e-ink
panels have no cursor.

Install via Settings → Widgets → Browse community widgets on
[Tesserae](https://github.com/dmellok/tesserae), once this is merged into
the catalog. Until then, copy `xkcd_comic/` into your server's `plugins/`
directory and restart.

## Folders shipped

- `xkcd_comic`

## What it shows

- **Latest** — whatever xkcd posted most recently.
- **Random** — a random past comic. The pick sticks for a configurable
  window (default 24h) instead of re-rolling on every dashboard rotation.
- **Specific number** — pin one comic (e.g. `353`, "Python").

Comic #404 is xkcd's own joke, the page really does 404, so it's skipped
automatically in Random mode and refused with a friendly message in Fixed
mode.

## Cell options

| Option | Type | Default | Notes |
|---|---|---|---|
| `mode` | select | `latest` | `latest`, `random`, or `fixed` |
| `comic_number` | number | `353` | Used when `mode` is `fixed` |
| `random_refresh_hours` | number | `24` | How long a random pick sticks before re-rolling |
| `show_title` | boolean | `true` | Comic title in the widget's title bar |
| `show_hovertext` | boolean | `true` | The whole point, prints `alt` as a caption |

No settings, no API key.

## Networking

- **Server-side** (`server.py:fetch`, capability-gated): `xkcd.com` only,
  for `https://xkcd.com/info.0.json` and `https://xkcd.com/<n>/info.0.json`.
  Declared in `plugin.json` as `requires: ["network:xkcd.com"]`.
- **Client-side** (the `<img>` tag the headless renderer loads when it
  screenshots the cell, not a Python socket call, so it's outside the
  capability scope): `imgs.xkcd.com`, xkcd's own image CDN.

## Rate limits / politeness

xkcd doesn't publish a rate limit. This widget is conservative anyway:
the "latest comic" lookup is cached 30 minutes, and any specific comic
number, once fetched, is cached forever (past comics never change), so
a dashboard rotating every 15-60 minutes makes at most one xkcd.com
request per cache window, not one per render.

## Stability tier: Best-effort

`xkcd.com/info.0.json` isn't an officially documented API, but it's been
in this exact shape for 15+ years and is what most third-party xkcd
clients read from. See
[Tesserae's stability tiers](https://docs.tesserae.ink/widgets/tiers/)
for what that classification means in practice.

## Attribution

xkcd comics are © Randall Munroe, licensed
[CC BY-NC 2.5](https://xkcd.com/license.html). This widget only links to
and displays xkcd's own hosted images and text; it doesn't redistribute
or modify them.

## Development

```sh
python -m pytest xkcd_comic/tests/test_smoke.py
ruff check xkcd_comic/
```

`test_widget_renders` needs a running Tesserae dev server's `/_test/render`
route (it uses the host app's `client` pytest fixture), so it only runs
inside a full Tesserae checkout with `xkcd_comic/` dropped into `plugins/`.
The rest of the suite runs standalone against `server.py`.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).

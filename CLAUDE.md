# Claude Usage Dashboard

Weekly token budget dashboard that visualizes Claude Code spend across days of the week.

## Project structure

- `dashboard.html` — single-file frontend (vanilla JS, no build step)
- `launcher.js` — Node.js script: runs `ccusage`, processes data, writes `usage_data.json`, serves the dashboard
- `usage_data.json` — generated at runtime by `launcher.js`, not committed

## Running the dashboard

```bash
node launcher.js                        # default: port 3131, auto-opens browser
node launcher.js --port 4000            # custom port
node launcher.js --no-open              # skip auto-open
node launcher.js --reset-day 1          # change week start (0=Sun … 6=Sat, default 3=Wed)
MACHINE_NAME="MacBook" node launcher.js # custom device label
```

For manual / multi-machine use:
```bash
npx ccusage daily --json > usage_daily.json
# Then open dashboard.html and upload the file
```

## Requirements

- Node.js 16+
- `npx` (bundled with Node.js)
- Claude Code sessions in `~/.claude/projects/`

## Architecture notes

- `launcher.js` runs `npx ccusage daily --json`, groups results into weekly buckets starting from `--reset-day`, and writes `usage_data.json`. The HTTP server serves `dashboard.html` and the JSON file on `127.0.0.1` only.
- `dashboard.html` supports two modes: **auto-load** (fetches `usage_data.json` from the local server when `?autoload` is in the URL) and **manual upload** (user uploads one or more JSON files). Multiple files are merged by date, with per-device color coding.
- The matrix layout is driven entirely by client-side JS — no framework, no bundler.

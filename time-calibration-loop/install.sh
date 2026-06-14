#!/usr/bin/env bash
# Time Calibration Loop installer (wall-clock analog of the token loop).
# Installs two Claude Code hooks that bake in this package's absolute path:
#   UserPromptSubmit -> inject current wall-clock time + a task-duration prior,
#                       and record this turn's start epoch.
#   Stop             -> measure elapsed since start and append the actual duration.
# Idempotent: re-running strips any prior time-loop hooks before adding fresh ones,
# so it is safe to run after `git pull` in a new workspace.
set -euo pipefail

LOOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
SCRIPT="$LOOP_DIR/time-loop.py"

echo "Loop package:    $LOOP_DIR"
echo "Claude settings: $SETTINGS"

# 1. Dependency / file checks (jq is NOT required; we parse JSON with python3)
command -v python3 >/dev/null || { echo "ERROR: python3 required"; exit 1; }
[ -f "$SCRIPT" ] || { echo "ERROR: missing $SCRIPT"; exit 1; }
chmod +x "$SCRIPT" 2>/dev/null || true

# 2. Merge the two hooks into settings.json (idempotent, preserves all other hooks)
python3 - "$SETTINGS" "$SCRIPT" <<'PY'
import json, os, sys
settings_path, script = sys.argv[1], sys.argv[2]
MARKER = "time-loop.py"                       # identifies any prior install
events = {
    "UserPromptSubmit": f"python3 {script} prompt 2>/dev/null || true",
    "Stop":             f"python3 {script} stop 2>/dev/null || true",
}
os.makedirs(os.path.dirname(settings_path) or ".", exist_ok=True)
s = {}
if os.path.exists(settings_path):
    with open(settings_path) as fh:
        s = json.load(fh)
hooks = s.setdefault("hooks", {})
for event, cmd in events.items():
    arr = hooks.get(event, [])
    for grp in arr:                            # strip prior time-loop hooks
        grp["hooks"] = [h for h in grp.get("hooks", []) if MARKER not in h.get("command", "")]
    arr = [g for g in arr if g.get("hooks")]   # drop now-empty groups
    arr.append({"hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
    hooks[event] = arr
with open(settings_path, "w") as fh:
    json.dump(s, fh, indent=2)
print("UserPromptSubmit + Stop hooks installed.")
PY

echo "Done. Open /hooks in Claude Code once (or restart) to load it this session."
echo "State + log live in: ~/.claude/time-loop/"
echo "Inspect actuals:  tail ~/.claude/time-loop/durations.log"
echo "Reset the prior:  rm ~/.claude/time-loop/durations.log"

#!/usr/bin/env python3
"""Time-calibration loop hook for Claude Code (wall-clock analog of the token loop).

Modes (argv[1]):
  prompt  -> UserPromptSubmit: inject current wall-clock time + a task-duration
             prior built from past turns, and record this turn's start time.
  stop    -> Stop: measure elapsed since the recorded start and append the actual
             duration to the rolling log, sharpening the next prediction.

State lives in ~/.claude/time-loop/:
  start-<session_id>   one file per live session holding the turn start epoch
  durations.log        tab-separated  <iso-timestamp>\t<seconds>  (global, rolling)

Reads the hook payload as JSON on stdin (needs session_id). On prompt mode it emits
a UserPromptSubmit additionalContext JSON object on stdout. Fails silent: a broken
hook must never block a turn.
"""
import sys, os, json, time, statistics
from datetime import datetime

DIR = os.path.expanduser("~/.claude/time-loop")
LOG = os.path.join(DIR, "durations.log")
WINDOW = 20          # how many recent turns define the prior
MAX_PLAUSIBLE = 86400  # ignore gaps > 24h (stale start file, clock jump)


def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def session_id(data):
    s = str(data.get("session_id") or "default")
    return "".join(c for c in s if c.isalnum() or c in "-_") or "default"


def human(seconds):
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60}s"
    return f"{s // 3600}h{(s % 3600) // 60}m"


def load_durations():
    out = []
    if not os.path.exists(LOG):
        return out
    try:
        with open(LOG) as f:
            for row in f:
                parts = row.strip().split("\t")
                if len(parts) >= 2 and parts[1].isdigit():
                    out.append(int(parts[1]))
    except Exception:
        pass
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "prompt"
    data = read_stdin_json()
    os.makedirs(DIR, exist_ok=True)
    start_file = os.path.join(DIR, f"start-{session_id(data)}")
    now = time.time()

    if mode == "stop":
        try:
            with open(start_file) as f:
                start = float(f.read().strip())
            dur = now - start
            if 0 <= dur < MAX_PLAUSIBLE:
                with open(LOG, "a") as f:
                    f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{int(dur)}\n")
        except Exception:
            pass
        finally:
            try:
                os.remove(start_file)
            except OSError:
                pass
        return

    # ---- prompt mode -------------------------------------------------------
    try:
        with open(start_file, "w") as f:
            f.write(str(now))
    except Exception:
        pass

    lines = [f"Wall-clock now: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z (%a)')}"]

    durs = load_durations()
    if durs:
        recent = durs[-WINDOW:]
        med = statistics.median(recent)
        last3 = ", ".join(human(d) for d in durs[-3:])
        lines.append(
            f"Task-duration prior (last {len(recent)} turns): median {human(med)}, "
            f"range {human(min(recent))}-{human(max(recent))}. Most recent: {last3}."
        )
        lines.append(
            "Before starting, PREDICT this turn's wall-clock duration in one short line "
            "(reason from the prior + this task's shape). Actual elapsed is measured at "
            "turn end and folded into the prior."
        )
    else:
        lines.append(
            "Task-duration prior: no samples yet. Before starting, PREDICT this turn's "
            "wall-clock duration in one short line; it is measured at turn end to seed the prior."
        )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }))


if __name__ == "__main__":
    main()

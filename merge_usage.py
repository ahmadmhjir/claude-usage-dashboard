#!/usr/bin/env python3
"""Merge two (or more) pre-processed usage_data.json files into one.

The dashboard's "launcher.js" format looks like:

    {
      "sources": ["DESKTOP-Q50JC6O"],
      "weeks": {
        "<weekStart>": {
          "entries": {
            "<date>": {
              "date", "inputTokens", "outputTokens",
              "cacheCreationTokens", "cacheReadTokens",
              "totalTokens", "totalCost",
              "modelsUsed": [...],
              "modelBreakdowns": [{modelName, inputTokens, ...}],
              "_devices": [...]
            }
          },
          "total": <sum of entry totalCost>
        }
      }
    }

Same-day usage from different machines is combined: token counts and cost are
summed, model breakdowns are merged per model, and the contributing devices are
tracked in "_devices" so the dashboard can colour the cell per machine.

Usage:
    python merge_usage.py file_a.json file_b.json [more.json ...] -o merged_usage_data.json
    python merge_usage.py usage_data.json macbook_usage_data.json
"""
import argparse
import json
import sys

TOKEN_FIELDS = (
    "inputTokens",
    "outputTokens",
    "cacheCreationTokens",
    "cacheReadTokens",
    "totalTokens",
)
BREAKDOWN_TOKEN_FIELDS = (
    "inputTokens",
    "outputTokens",
    "cacheCreationTokens",
    "cacheReadTokens",
    "cost",
)


def merge_breakdowns(target, incoming):
    """Merge modelBreakdowns lists keyed by modelName, summing token/cost fields."""
    by_model = {b.get("modelName"): b for b in target}
    for b in incoming:
        name = b.get("modelName")
        if name in by_model:
            dst = by_model[name]
            for f in BREAKDOWN_TOKEN_FIELDS:
                dst[f] = dst.get(f, 0) + b.get(f, 0)
        else:
            copy = dict(b)
            by_model[name] = copy
            target.append(copy)
    return target


def merge_entry(dst, src, source_label):
    """Merge one day entry (src) into dst (same date)."""
    for f in TOKEN_FIELDS:
        dst[f] = dst.get(f, 0) + src.get(f, 0)
    dst["totalCost"] = dst.get("totalCost", 0) + src.get("totalCost", 0)

    dst["modelsUsed"] = sorted(
        set(dst.get("modelsUsed", [])) | set(src.get("modelsUsed", []))
    )
    dst["modelBreakdowns"] = merge_breakdowns(
        dst.get("modelBreakdowns", []), src.get("modelBreakdowns", [])
    )

    devices = dst.get("_devices", [])
    for d in src.get("_devices", []) or [source_label]:
        if d not in devices:
            devices.append(d)
    dst["_devices"] = devices


def merge_into(acc, data):
    """Merge a loaded usage_data dict (data) into the accumulator (acc)."""
    # The device label for entries that don't carry their own _devices.
    source_label = (data.get("sources") or ["unknown"])[0]

    for s in data.get("sources", []):
        if s not in acc["sources"]:
            acc["sources"].append(s)

    for week_start, week in data.get("weeks", {}).items():
        acc_week = acc["weeks"].setdefault(week_start, {"entries": {}, "total": 0})
        for date, entry in week.get("entries", {}).items():
            if date in acc_week["entries"]:
                merge_entry(acc_week["entries"][date], entry, source_label)
            else:
                copy = json.loads(json.dumps(entry))  # deep copy
                if not copy.get("_devices"):
                    copy["_devices"] = [source_label]
                acc_week["entries"][date] = copy


def recompute_and_sort(acc):
    """Recompute week totals and sort weeks + entries by date for stable output."""
    sorted_weeks = {}
    for week_start in sorted(acc["weeks"]):
        week = acc["weeks"][week_start]
        entries = {d: week["entries"][d] for d in sorted(week["entries"])}
        total = sum(e.get("totalCost", 0) for e in entries.values())
        sorted_weeks[week_start] = {"entries": entries, "total": total}
    acc["weeks"] = sorted_weeks
    acc["sources"] = sorted(acc["sources"])


def main(argv=None):
    p = argparse.ArgumentParser(description="Merge usage_data.json files.")
    p.add_argument("files", nargs="+", help="usage_data.json files to merge (2+)")
    p.add_argument(
        "-o",
        "--output",
        default="merged_usage_data.json",
        help="output path (default: merged_usage_data.json)",
    )
    args = p.parse_args(argv)

    if len(args.files) < 2:
        p.error("provide at least two files to merge")

    acc = {"sources": [], "weeks": {}}
    for path in args.files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"error: cannot read {path}: {e}", file=sys.stderr)
            return 1
        if "weeks" not in data:
            print(
                f"error: {path} is not a pre-processed usage_data.json "
                "(missing 'weeks'). Run it through launcher.js first.",
                file=sys.stderr,
            )
            return 1
        merge_into(acc, data)

    recompute_and_sort(acc)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(acc, f, indent=2)

    n_weeks = len(acc["weeks"])
    n_days = sum(len(w["entries"]) for w in acc["weeks"].values())
    grand = sum(w["total"] for w in acc["weeks"].values())
    print(
        f"Merged {len(args.files)} files -> {args.output}\n"
        f"  sources: {', '.join(acc['sources'])}\n"
        "  weeks: {}  days: {}  total cost: ${:.2f}".format(n_weeks, n_days, grand)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

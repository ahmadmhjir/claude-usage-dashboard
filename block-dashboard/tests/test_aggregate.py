import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"

def run(tmp_path):
    out = tmp_path / "calibration.json"
    subprocess.run([sys.executable, str(ROOT / "aggregate.py"),
                    "--scorecard", str(FIX / "scorecard.jsonl"),
                    "--durations", str(FIX / "durations.log"),
                    "--priors", str(FIX / "priors.md"),
                    "--usage", str(FIX / "usage-cal.log"),
                    "--out", str(out)], check=True)
    return json.loads(out.read_text())

def test_passes_normalized_and_rescore_supersedes(tmp_path):
    d = run(tmp_path)
    # pass 2 RESCORE supersedes its SCORE -> only one metric row for pass 2, the ON_BUDGET one
    p2 = [p for p in d["passes"] if p["pass"] == 2]
    assert len(p2) == 1 and p2[0]["phase"] == "RESCORE" and p2[0]["verdict"] == "ON_BUDGET"
    # pred range "6-15" -> midpoint 10.5
    assert abs(p2[0]["pred_k"] - 10.5) < 1e-6
    # non-numeric actual_k row (pass 7) -> actual_k is null, err null
    p7 = [p for p in d["passes"] if p["pass"] == 7][0]
    assert p7["actual_k"] is None and p7["err"] is None

def test_verdict_bucketing(tmp_path):
    d = run(tmp_path)
    by_pass = {p["pass"]: p for p in d["passes"]}
    assert by_pass[2]["verdict"] == "ON_BUDGET"  # err 0.045 <= 0.2
    assert by_pass[3]["verdict"] == "BLIND"       # err 1.2 > 0.6

def test_turns_variable_columns_and_flags(tmp_path):
    d = run(tmp_path)
    turns = d["turns"]
    # the 3-number early row has total == None
    early = [t for t in turns if t["ts"] == "2026-06-14T21:56:53"][0]
    assert early["total"] is None and early["out"] == 3276
    # the 4-number row carries total
    late = [t for t in turns if t["ts"] == "2026-06-15T16:56:56"][0]
    assert late["total"] == 4523090
    # -1 row flagged unreadable and excluded from outlier/burn math
    unr = [t for t in turns if t["unreadable"]]
    assert len(unr) == 1
    # 740200 out is the outlier
    out_flag = [t for t in turns if t["outlier"]]
    assert len(out_flag) == 1 and out_flag[0]["out"] == 740200

def test_block_grouping_and_slope(tmp_path):
    d = run(tmp_path)
    # total drops at the 4th anchor -> two blocks
    assert len(d["blocks"]) == 2
    b0 = d["blocks"][0]
    assert len(b0["points"]) == 3
    # slope is positive least-squares tokens-per-pp; eff_cap = slope*100
    assert b0["slope_tok_per_pp"] > 0
    assert abs(b0["eff_cap"] - b0["slope_tok_per_pp"] * 100) < 1e-3

def test_single_anchor_block_slope_none(tmp_path, monkeypatch):
    # a block with one anchor -> slope None, no crash
    one = tmp_path / "u.log"
    one.write_text("2026-06-15T10:00:00\t10.0\t100\t999\n")
    out = tmp_path / "c.json"
    subprocess.run([sys.executable, str(ROOT / "aggregate.py"),
                    "--scorecard", str(FIX / "scorecard.jsonl"),
                    "--durations", str(FIX / "durations.log"),
                    "--priors", str(FIX / "priors.md"),
                    "--usage", str(one), "--out", str(out)], check=True)
    d = json.loads(out.read_text())
    assert d["blocks"][0]["slope_tok_per_pp"] is None

def test_priors_parsed_with_endash_and_units(tmp_path):
    d = run(tmp_path)
    pr = {p["profile"]: p for p in d["priors"]}
    assert pr["read+answer"]["tok_lo"] == 2 and pr["read+answer"]["tok_hi"] == 6
    assert pr["read+answer"]["seed"] is True   # n == 0
    # "2 – 6m" minutes -> seconds
    assert pr["multi-file feature"]["time_lo"] == 120 and pr["multi-file feature"]["time_hi"] == 360
    assert pr["design/doc write"]["time_lo"] == 60 and pr["design/doc write"]["time_hi"] == 120

def test_derived_rolling_mape_and_counts(tmp_path):
    d = run(tmp_path)
    der = d["derived"]
    assert der["counts"]["unreadable"] == 1
    assert der["counts"]["outliers"] == 1
    # convergence_score == 1 - last rolling_mape, clamped >= 0
    if der["rolling_mape"]:
        last = der["rolling_mape"][-1]["value"]
        assert abs(der["convergence_score"] - max(0.0, 1 - last)) < 1e-6
    # burn uses median+IQR, never min/max
    assert "burn_median" in der and isinstance(der["burn_iqr"], list)

def test_missing_source_degrades(tmp_path):
    out = tmp_path / "c.json"
    subprocess.run([sys.executable, str(ROOT / "aggregate.py"),
                    "--scorecard", str(tmp_path / "nope.jsonl"),
                    "--durations", str(tmp_path / "nope.log"),
                    "--priors", str(tmp_path / "nope.md"),
                    "--usage", str(tmp_path / "nope.log2"), "--out", str(out)], check=True)
    d = json.loads(out.read_text())
    assert d["passes"] == [] and d["turns"] == [] and d["blocks"] == []

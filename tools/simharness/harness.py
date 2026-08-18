#!/usr/bin/env python3
"""EnergyPlus → vectors.json FPR harness (phase B2B-2).

Runs a building epJSON under its own schedule-based baseline control,
logs the node variables our canonical points map to, converts each air
loop's week into a `cxf-library/vectors/v1` scenario expecting
`yFault == false` for the whole horizon, and replays it through
`tools/verify`. Every FAILed scenario is a false positive to explain —
either a rule robustness finding or a genuine fault baked into the
prototype's operation.

Usage (from repo root):
  python3 tools/simharness/harness.py run --building <dir> [--out <dir>]
      <dir> must hold building.epjson + a *.epw. Patches run period +
      Output:Variable requests, runs EnergyPlus (ENERGYPLUS_PATH), emits
      per-rule replay dirs, invokes cargo verify, prints the FPR table.

Point mapping (packaged VAV, e.g. B2B OfficeMedium; per air loop):
  sat        System Node Temperature @ "<loop> Supply Equipment Outlet Node"
  sat_sp     System Node Setpoint Temperature @ same node
  rat        System Node Temperature @ "<loop> Supply Equipment Inlet Node"
  mat        System Node Temperature @ the OA controller's mixed_air_node_name
  oat        Site Outdoor Air Drybulb Temperature (Environment)
  sf_status  Fan Electricity Rate @ "<loop> Fan" > 50 W  (bool proxy)
  clg_vlv_cmd  Cooling Coil Runtime Fraction × 100  (DX proxy — DOCUMENTED:
               packaged units have no CHW valve; runtime fraction is the
               cooling-command analog)
  oa_dmpr_cmd  Air System Outdoor Air Flow Fraction × 100 (proxy — the
               realized OA fraction, not the damper command signal)

Rules are auto-selected: any faults/ahu card whose frontmatter `points`
are a subset of the mapped set is replayed (per loop). Proxy caveats
apply to any conclusion drawn from proxied points.
"""

from __future__ import annotations
import argparse, csv, json, os, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAPPED_POINTS = {"sat", "sat_sp", "rat", "mat", "oat", "sf_status",
                 "clg_vlv_cmd", "oa_dmpr_cmd"}
STEP_S = 300           # 12 E+ timesteps/hour
FAN_ON_W = 50.0
ROUND = 3

# ---------------------------------------------------------------- epJSON

def loop_nodes(b: dict) -> dict:
    """Per-air-loop node map derived from the epJSON topology."""
    loops = {}
    for name, loop in b.get("AirLoopHVAC", {}).items():
        loops[name] = {
            "sat_node": loop["supply_side_outlet_node_names"],
            "rat_node": loop["supply_side_inlet_node_name"]
            if "supply_side_inlet_node_name" in loop
            else loop.get("supply_side_inlet_node_names"),
        }
    for name, oa in b.get("Controller:OutdoorAir", {}).items():
        loop = next((l for l in loops if name.startswith(l)), None)
        if loop:
            loops[loop]["mat_node"] = oa["mixed_air_node_name"]
            if not loops[loop].get("rat_node"):
                loops[loop]["rat_node"] = oa["return_air_node_name"]
    for name in b.get("Fan:VariableVolume", {}):
        loop = next((l for l in loops if name.startswith(l)), None)
        if loop:
            loops[loop]["fan"] = name
    for name in list(b.get("Coil:Cooling:DX:TwoSpeed", {})) + \
                list(b.get("Coil:Cooling:DX:SingleSpeed", {})):
        loop = next((l for l in loops if name.startswith(l)), None)
        if loop:
            loops[loop]["clg_coil"] = name
    for name in b.get("Coil:Heating:Fuel", {}):
        loop = next((l for l in loops if name.startswith(l)), None)
        if loop:
            loops[loop]["htg_coil"] = name
    return loops


def patch(b: dict, loops: dict, begin=(7, 6), end=(7, 12)) -> dict:
    """Set the run period and add the Output:Variable requests."""
    b = json.loads(json.dumps(b))  # deep copy
    for rp in b.get("RunPeriod", {}).values():
        rp["begin_month"], rp["begin_day_of_month"] = begin
        rp["end_month"], rp["end_day_of_month"] = end
    b.setdefault("Output:Variable", {})
    def req(key, var):
        n = f"simharness {len(b['Output:Variable'])}"
        b["Output:Variable"][n] = {"key_value": key, "variable_name": var,
                                   "reporting_frequency": "Timestep"}
    req("Environment", "Site Outdoor Air Drybulb Temperature")
    for lp, n in loops.items():
        req(n["sat_node"], "System Node Temperature")
        req(n["sat_node"], "System Node Setpoint Temperature")
        req(n["rat_node"], "System Node Temperature")
        req(n["mat_node"], "System Node Temperature")
        req(n["fan"], "Fan Electricity Rate")
        if "clg_coil" in n:
            req(n["clg_coil"], "Cooling Coil Runtime Fraction")
        if "htg_coil" in n:
            req(n["htg_coil"], "Heating Coil Heating Rate")
        req(lp, "Air System Outdoor Air Flow Fraction")
        req(lp, "Air System Outdoor Air Economizer Status")
    return b

# ------------------------------------------------------------------ E+

def run_energyplus(epjson: Path, epw: Path, outdir: Path) -> Path:
    ep = os.environ.get("ENERGYPLUS_PATH")
    if not ep:
        sys.exit("set ENERGYPLUS_PATH to the EnergyPlus install dir")
    exe = Path(ep) / "energyplus"
    r = subprocess.run([str(exe), "-w", str(epw), "-d", str(outdir), "-r",
                        str(epjson)], capture_output=True, text=True)
    csv_out = outdir / "eplusout.csv"
    if not csv_out.is_file():
        sys.exit(f"EnergyPlus produced no CSV; tail of stderr:\n{r.stderr[-2000:]}"
                 f"\nsee {outdir}/eplusout.err")
    return csv_out

# ------------------------------------------------------------- extract

def col(header: list[str], key: str, var: str) -> int:
    pat = f"{key.upper()}:{var}"
    for i, h in enumerate(header):
        if h.upper().startswith(pat.upper()):
            return i
    raise KeyError(pat)


def series(rows, idx, scale=1.0):
    return [round(float(r[idx]) * scale, ROUND) for r in rows]


def to_steps(vals: list) -> list | float | bool:
    """Compress a series into vectors/v1 piecewise-constant form."""
    if all(v == vals[0] for v in vals):
        return vals[0]
    steps, last = [], object()
    for i, v in enumerate(vals):
        if v != last:
            steps.append({"t": i * STEP_S, "value": v})
            last = v
    return steps


def extract(csv_path: Path, loops: dict) -> dict:
    with open(csv_path) as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    out = {}
    oat_i = col(header, "Environment", "Site Outdoor Air Drybulb Temperature")
    for lp, n in loops.items():
        pts = {
            "oat": series(data, oat_i),
            "sat": series(data, col(header, n["sat_node"], "System Node Temperature")),
            "sat_sp": series(data, col(header, n["sat_node"], "System Node Setpoint Temperature")),
            "rat": series(data, col(header, n["rat_node"], "System Node Temperature")),
            "mat": series(data, col(header, n["mat_node"], "System Node Temperature")),
            "oa_dmpr_cmd": series(data, col(header, lp, "Air System Outdoor Air Flow Fraction"), 100.0),
        }
        fan_w = series(data, col(header, n["fan"], "Fan Electricity Rate"))
        pts["sf_status"] = [w > FAN_ON_W for w in fan_w]
        if "clg_coil" in n:
            pts["clg_vlv_cmd"] = series(
                data, col(header, n["clg_coil"], "Cooling Coil Runtime Fraction"), 100.0)
        pts["_htg_w"] = series(data, col(header, n["htg_coil"], "Heating Coil Heating Rate")) \
            if "htg_coil" in n else [0.0] * len(pts["oat"])
        pts["_econ"] = series(data, col(header, lp, "Air System Outdoor Air Economizer Status"))
        out[lp] = pts
    return out


# ------------------------------------------------- operating states

ALL_OS = {1, 2, 3, 4, 5}
# G36-style OS sets transcribed from each card's operating_states frontmatter.
OS_MAP = {
    "AHU-FC-002": ALL_OS, "AHU-FC-003": ALL_OS,
    "AHU-FC-005": {1}, "AHU-FC-006": {1, 4}, "AHU-FC-008": {2},
    "AHU-FC-009": {2}, "AHU-FC-010": {3}, "AHU-FC-012": {2, 3, 4},
    "AHU-FC-014": {1, 2}, "AHU-FC-051": {4}, "AHU-FC-053": {2, 3, 4},
    "AHU-FC-054": ALL_OS, "AHU-FC-055": {1, 4}, "AHU-FC-062": ALL_OS,
    "AHU-FC-066": {2, 3, 4}, "AHU-FC-067": {1, 2, 3, 4}, "AHU-FC-068": {3},
}
SMOOTH_TICKS = 6   # 30 min any-window smoothing over DX/burner cycling


def derive_os(pts: dict) -> list:
    "Per-tick OS from actuator signatures (APAR-style, host-side)."
    n = len(pts["oat"])
    raw_clg = [v > 2.0 for v in pts.get("clg_vlv_cmd", [0.0] * n)]
    raw_htg = [w > 1000.0 for w in pts["_htg_w"]]
    econ = [v >= 0.5 for v in pts["_econ"]]
    def smooth(sig):
        return [any(sig[max(0, i - SMOOTH_TICKS):i + 1]) for i in range(n)]
    clg, htg = smooth(raw_clg), smooth(raw_htg)
    os_ = []
    for i in range(n):
        if htg[i] and not clg[i]:
            os_.append(1)
        elif econ[i] and clg[i]:
            os_.append(3)
        elif econ[i]:
            os_.append(2)
        elif clg[i]:
            os_.append(4)
        else:
            os_.append(0)   # vent-only: no rule's scoped state
    return os_

# --------------------------------------------------------------- rules

def card_points(card: Path) -> list[str]:
    fm = card.read_text().split("---", 2)[1]
    m = re.search(r"^points:\n((?:\s+-\s+\S+\n)+)", fm, re.M)
    return re.findall(r"-\s+(\S+)", m.group(1)) if m else []


def eligible_rules(families=("ahu",)) -> dict:
    rules = {}
    for fam in families:
        for d in sorted((REPO / "faults" / fam).iterdir()):
            card = d / "card.md"
            if card.is_file():
                pts = card_points(card)
                if pts and set(pts) <= MAPPED_POINTS:
                    rules[d.name] = {"dir": d, "points": pts}
    return rules

# -------------------------------------------------------------- replay

GATE_LEAD_S = 3600   # ignore assertions in the first hour after fan start:
                     # a real host suspends evaluation (NO_EVAL) while the
                     # precondition is unmet, so delay state accumulated
                     # overnight must be given time to clear.


OS_LEAD_S = 1800     # margin after entering a rule's scoped OS


def gated_windows(sf: list[bool], os_: list, allowed: set) -> list[tuple[int, int]]:
    """Fan-on ∩ scoped-OS intervals, shrunk by the lead margins."""
    ok = [on and (s in allowed) for on, s in zip(sf, os_)]
    wins, start = [], None
    for i, v in enumerate(ok + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            lead = GATE_LEAD_S if start == 0 else OS_LEAD_S
            a, b = start * STEP_S + lead, (i - 1) * STEP_S
            if b - a >= 1800:
                wins.append((a, b))
            start = None
    return wins


def emit_and_replay(building: str, loops_pts: dict, rules: dict, out: Path):
    replay = out / "replay"
    if replay.exists():
        shutil.rmtree(replay)
    horizon = None
    dirs = []
    for rid, r in rules.items():
        for lp, pts in loops_pts.items():
            n = len(next(iter(pts.values())))
            horizon = (n - 1) * STEP_S
            wins = gated_windows(pts["sf_status"], derive_os(pts),
                                 OS_MAP.get(rid, ALL_OS))
            if not wins:
                continue
            d = replay / f"{rid}__{lp.replace(' ', '_')}"
            d.mkdir(parents=True)
            shutil.copy(r["dir"] / "rule.cxf.jsonld", d / "rule.cxf.jsonld")
            scen = {
                "name": f"{building}__{lp}".replace("-", "_").replace(" ", "_").lower(),
                "description": f"Healthy-baseline EnergyPlus week, {building} {lp}. "
                               "Host precondition (fan running) applied as expect "
                               f"windows with a {GATE_LEAD_S}s lead margin; any "
                               "FAIL is a false positive to explain.",
                "inputs": {p: to_steps(pts[p]) for p in r["points"]},  # noqa
                "expect": [{"output": "yFault", "from_s": a, "to_s": b,
                            "equals": False} for a, b in wins],
            }
            (d / "vectors.json").write_text(json.dumps({
                "schema": "cxf-library/vectors/v1",
                "clock": {"step_s": STEP_S, "horizon_s": horizon},
                "scenarios": [scen]}, indent=1))
            dirs.append(d)
    r = subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path",
         str(REPO / "tools/verify/Cargo.toml"), "--", *map(str, dirs)],
        capture_output=True, text=True, cwd=REPO)
    return r.stdout + r.stderr

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("--building", required=True)
    runp.add_argument("--out", default=None)
    args = ap.parse_args()

    bdir = Path(args.building)
    out = Path(args.out) if args.out else bdir / "simharness_out"
    out.mkdir(parents=True, exist_ok=True)
    b = json.load(open(bdir / "building.epjson"))
    epw = next(bdir.glob("*.epw"))
    loops = loop_nodes(b)
    patched = patch(b, loops)
    pj = out / "patched.epjson"
    pj.write_text(json.dumps(patched))
    print(f"loops: {list(loops)}; running EnergyPlus…")
    csv_path = run_energyplus(pj, epw, out / "ep")
    loops_pts = extract(csv_path, loops)
    rules = eligible_rules()
    print(f"eligible rules (points ⊆ mapped): {sorted(rules)}")
    log = emit_and_replay(bdir.name, loops_pts, rules, out)
    (out / "verify.log").write_text(log)
    # tally per rule (dir name carries RULE__LOOP)
    per_rule: dict = {}
    cur = None
    for line in log.splitlines():
        m = re.search(r"replay/([A-Z]+-FC-\d+)__(\S+)", line)
        if m:
            cur = m.groups()
        elif cur and re.search(r"\b(PASS|FAIL)\b", line):
            ok = "PASS" in line
            per_rule.setdefault(cur[0], []).append((cur[1], ok, line.strip()))
    print(f"\n{'rule':<12} {'loops':>5} {'clean':>5} {'FP':>3}")
    findings = []
    for rid in sorted(per_rule):
        rows = per_rule[rid]
        fp = [r for r in rows if not r[1]]
        print(f"{rid:<12} {len(rows):>5} {len(rows)-len(fp):>5} {len(fp):>3}")
        findings += [(rid, *r[0:1], r[2]) for r in fp]
    for rid, lp, line in findings:
        print(f"  FP {rid} @ {lp}: {line.split('—')[-1].strip()}")
    print(f"full log: {out}/verify.log")


if __name__ == "__main__":
    main()

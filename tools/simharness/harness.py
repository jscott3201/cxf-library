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
OS_OVERRIDE: dict = {}   # rule-id -> set, only for cards whose prose defeats the parser


def parse_operating_states(s: str):
    """G36-style OS set from a card's operating_states frontmatter.

    Handles ranges (OS#2-#4), comma lists (OS 2, 3, 4), singletons, and
    a leading "all". Returns None when nothing parses — callers must treat
    that as an ERROR, never default to ALL_OS: the fleet sweep's two
    spurious FP clusters came from exactly that silent default.
    """
    s = s.strip().strip('"')
    out = set()
    for m in re.finditer(r'OS\s?#?\s?(\d)((?:\s*,\s*\d)*)(?:\s*[-–]\s*(?:OS\s?)?#?(\d))?', s):
        a, lst, b = m.groups()
        if b:
            out |= set(range(int(a), int(b) + 1))
        else:
            out.add(int(a))
            out |= {int(x) for x in re.findall(r'\d', lst or '')}
    if not out and re.match(r'(?i)^\s*"?all\b', s):
        return set(ALL_OS)
    return out or None


def rule_os_set(rid: str, card: Path):
    if rid in OS_OVERRIDE:
        return OS_OVERRIDE[rid]
    fm = card.read_text().split("---", 2)[1]
    m = re.search(r'^operating_states:\s*(.+)$', fm, re.M)
    got = parse_operating_states(m.group(1)) if m else None
    if got is None:
        sys.exit(f"{rid}: operating_states unparseable ({m.group(1)[:60] if m else 'missing'}) — "
                 "add an OS_OVERRIDE entry rather than defaulting")
    return got


SMOOTH_TICKS = 6   # 30 min any-window smoothing over DX/burner cycling


def derive_os(pts: dict) -> list:
    "Per-tick OS from actuator signatures (APAR-style, host-side)."
    n = len(pts["oat"])
    raw_clg = [v > 2.0 for v in pts.get("clg_vlv_cmd", [0.0] * n)]
    raw_htg = [w > 1000.0 for w in pts["_htg_w"]]
    econ = [v >= 0.5 for v in pts["_econ"]]
    def smooth(sig):
        # majority-of-window, not any-of-window: a single compressor blip
        # must not reclassify half an hour of economizing as OS#3
        # (fleet-sweep artifact: AHU-FC-011 false cluster, 2026-08-18)
        return [sum(sig[max(0, i - SMOOTH_TICKS):i + 1]) * 2
                > len(sig[max(0, i - SMOOTH_TICKS):i + 1])
                for i in range(n)]
    clg, htg = smooth(raw_clg), smooth(raw_htg)
    os_ = []
    for i in range(n):
        # heating takes precedence outright: under smoothing, htg and clg
        # can overlap at warmup transitions, and evaluating OS#2-4-scoped
        # rules during actual heating produced the AHU-FC-015 false
        # cluster (fleet sweep, 2026-08-18)
        if htg[i]:
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


def eligible_rules(families=("ahu",), mapped=None) -> dict:
    mapped = mapped or MAPPED_POINTS
    rules = {}
    for fam in families:
        for d in sorted((REPO / "faults" / fam).iterdir()):
            card = d / "card.md"
            if card.is_file():
                pts = card_points(card)
                if pts and set(pts) <= mapped:
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
                                 rule_os_set(rid, r["dir"] / "card.md"))
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



# ================================================================ plants

PLANT_EXCLUDE = {
    "CHW-FC-050": "host-fitted kW/ton baseline placeholders — needs a per-plant fit first",
    "CHW-FC-051": "reset-class: prototype uses a constant scheduled CHW setpoint, fires by construction",
    "HW-FC-050": "host-fitted baseline placeholders — needs a per-plant fit first",
    "HW-FC-051": "host-fitted baseline placeholders — needs a per-plant fit first",
    "HW-FC-057": "reset-class: constant scheduled HW setpoint, fires by construction",
    "HW-FC-056": "by-construction: constant HWST at low evening load IS the retuning condition it detects (no HWST reset in the prototype); verified firing correctly, Jan week",
}
PLANT_MAPPED = {"chwst", "chwrt", "chwst_sp", "chiller_load", "boiler_status",
                "hw_pump_status", "hws_temp", "hwr_temp", "hws_temp_sp",
                "hw_pump_vfd_speed", "oat"}
# rule -> gate key; rules absent here replay ungated (lead margin only):
# unnecessary-operation rules must NOT be gated on the equipment they accuse.
PLANT_GATE = {"CHW-FC-053": "chw_load40", "HW-FC-053": "hw_on", "HW-FC-056": "hw_on"}
PUMP_ON_W = 100.0


def plant_nodes(b: dict) -> dict:
    """CHW + HW loop node/equipment map (DOE prototype shapes)."""
    out = {}
    for name, pl in b.get("PlantLoop", {}).items():
        fluid = pl.get("fluid_type", "Water")
        entry = {"out_node": pl["plant_side_outlet_node_name"],
                 "in_node": pl["plant_side_inlet_node_name"],
                 "sp_node": pl.get("loop_temperature_setpoint_node_name")}
        if any(name.startswith(p) for p in ("CoolSys", "CHW")) and "Demand" not in name:
            entry["chillers"] = [c for c in b.get("Chiller:Electric:ReformulatedEIR", {})
                                 ] + [c for c in b.get("Chiller:Electric:EIR", {})]
            out["chw"] = entry
        elif any(name.startswith(p) for p in ("HeatSys", "HW")) and "SWH" not in name:
            entry["boilers"] = [x for x in b.get("Boiler:HotWater", {}) if name.split("_")[0].lower() in x.lower() or "Central" not in x]
            entry["pumps"] = [p for p in list(b.get("Pump:VariableSpeed", {})) if name.split("_")[0].lower() in p.lower()]
            out["hw"] = entry
    for name, cl in b.get("CondenserLoop", {}).items():
        out["tower"] = {"out_node": cl["condenser_side_outlet_node_name"],
                        "in_node": cl["condenser_side_inlet_node_name"],
                        "towers": list(b.get("CoolingTower:VariableSpeed", {}))
                                  + list(b.get("CoolingTower:SingleSpeed", {}))
                                  + list(b.get("CoolingTower:TwoSpeed", {}))}
    return out


def patch_plant(b: dict, pn: dict, begin, end) -> dict:
    b = json.loads(json.dumps(b))
    for rp in b.get("RunPeriod", {}).values():
        rp["begin_month"], rp["begin_day_of_month"] = begin
        rp["end_month"], rp["end_day_of_month"] = end
    b.setdefault("Output:Variable", {})
    def req(key, var):
        n = f"simharness {len(b['Output:Variable'])}"
        b["Output:Variable"][n] = {"key_value": key, "variable_name": var,
                                   "reporting_frequency": "Timestep"}
    req("Environment", "Site Outdoor Air Drybulb Temperature")
    if "chw" in pn:
        c = pn["chw"]
        req(c["out_node"], "System Node Temperature")
        req(c["in_node"], "System Node Temperature")
        req(c["sp_node"], "System Node Setpoint Temperature")
        for ch in c["chillers"]:
            req(ch, "Chiller Part Load Ratio")
    if "tower" in pn:
        tw = pn["tower"]
        req("Environment", "Site Outdoor Air Wetbulb Temperature")
        req(tw["out_node"], "System Node Temperature")
        req(tw["in_node"], "System Node Temperature")
        for c in tw["towers"]:
            req(c, "Cooling Tower Fan Electricity Rate")
    if "hw" in pn:
        h = pn["hw"]
        req(h["out_node"], "System Node Temperature")
        req(h["in_node"], "System Node Temperature")
        req(h["sp_node"], "System Node Setpoint Temperature")
        for bo in h["boilers"]:
            req(bo, "Boiler Part Load Ratio")
        for p in h["pumps"]:
            req(p, "Pump Electricity Rate")
            req(p, "Pump Mass Flow Rate")
    return b


def extract_plant(csv_path: Path, pn: dict, b: dict) -> dict:
    with open(csv_path) as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    oat = series(data, col(header, "Environment", "Site Outdoor Air Drybulb Temperature"))
    fams = {}
    if "chw" in pn:
        c = pn["chw"]
        plrs = [series(data, col(header, ch, "Chiller Part Load Ratio")) for ch in c["chillers"]]
        fams["chw"] = {
            "oat": oat,
            "chwst": series(data, col(header, c["out_node"], "System Node Temperature")),
            "chwrt": series(data, col(header, c["in_node"], "System Node Temperature")),
            "chwst_sp": series(data, col(header, c["sp_node"], "System Node Setpoint Temperature")),
            # plant chiller_load proxy: max PLR across chillers x100 — the
            # loaded chiller's PLR, the quantity the delta-T floor gates on
            "chiller_load": [round(max(v) * 100.0, ROUND) for v in zip(*plrs)],
        }
    if "tower" in pn:
        tw = pn["tower"]
        fan_w = [series(data, col(header, c, "Cooling Tower Fan Electricity Rate")) for c in tw["towers"]]
        fams["tower"] = {
            "oat": oat,
            "oa_wetbulb": series(data, col(header, "Environment", "Site Outdoor Air Wetbulb Temperature")),
            "tower_leaving_temp": series(data, col(header, tw["out_node"], "System Node Temperature")),
            "tower_entering_temp": series(data, col(header, tw["in_node"], "System Node Temperature")),
            "tower_fan_on": [max(v) > 100.0 for v in zip(*fan_w)],
        }
    if "hw" in pn:
        h = pn["hw"]
        plrs = [series(data, col(header, bo, "Boiler Part Load Ratio")) for bo in h["boilers"]]
        pump_w = [series(data, col(header, p, "Pump Electricity Rate")) for p in h["pumps"]]
        flows = [series(data, col(header, p, "Pump Mass Flow Rate")) for p in h["pumps"]]
        fmax = max(v for row in flows for v in row) or 1.0
        fams["hw"] = {
            "oat": oat,
            "hws_temp": series(data, col(header, h["out_node"], "System Node Temperature")),
            "hwr_temp": series(data, col(header, h["in_node"], "System Node Temperature")),
            "hws_temp_sp": series(data, col(header, h["sp_node"], "System Node Setpoint Temperature")),
            "boiler_status": [max(v) > 0.02 for v in zip(*plrs)],
            "hw_pump_status": [max(v) > PUMP_ON_W for v in zip(*pump_w)],
            # VFD speed proxy: pump mass-flow fraction of observed max x100
            # (affinity-law approximation; documented proxy)
            "hw_pump_vfd_speed": [round(max(v) / fmax * 100.0, ROUND) for v in zip(*flows)],
        }
    return fams


def plant_gate_windows(key: str | None, pts: dict, n: int) -> list:
    if key is None:
        return [(GATE_LEAD_S, (n - 1) * STEP_S)]
    if key == "chw_load40":
        ok = [v > 40.0 for v in pts["chiller_load"]]
    elif key == "hw_on":
        ok = pts["boiler_status"]
    else:
        raise KeyError(key)
    wins, start = [], None
    for i, v in enumerate(list(ok) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            a, b_ = start * STEP_S + OS_LEAD_S, (i - 1) * STEP_S
            if b_ - a >= 1800:
                wins.append((a, b_))
            start = None
    return wins



# ================================================================ vavcal

def vavcal(b, bdir, out, epw, begin, end, args):
    """Healthy VAV error-signal statistics for CUSUM calibration.

    Computes, per zone over occupied/fan-on ticks: Temperror (piecewise
    zone-temp error vs the dual setpoints, VPACC eq. form) and dTerror
    (terminal discharge temp minus the AHU SAT broadcast, reheat off).
    Emits vavcal.json with per-channel mean/std medians across zones —
    the normal-operation statistics NIST/PIER §5.1.5 says k and h must
    come from.
    """
    terms = b.get("AirTerminal:SingleDuct:VAV:Reheat", {})
    zones = {}
    for name, t in terms.items():
        zones[name] = {"out_node": t["air_outlet_node_name"],
                       "rht_coil": t.get("reheat_coil_name")}
    stats_b = json.loads(json.dumps(b))
    for rp in stats_b.get("RunPeriod", {}).values():
        rp["begin_month"], rp["begin_day_of_month"] = begin
        rp["end_month"], rp["end_day_of_month"] = end
    stats_b.setdefault("Output:Variable", {})
    def req(key, var):
        n = f"simharness {len(stats_b['Output:Variable'])}"
        stats_b["Output:Variable"][n] = {"key_value": key, "variable_name": var,
                                         "reporting_frequency": "Timestep"}
    req("*", "Zone Mean Air Temperature")
    req("*", "Zone Thermostat Heating Setpoint Temperature")
    req("*", "Zone Thermostat Cooling Setpoint Temperature")
    for z in zones.values():
        req(z["out_node"], "System Node Temperature")
        if z["rht_coil"]:
            req(z["rht_coil"], "Heating Coil Heating Rate")
    for name, loop in b.get("AirLoopHVAC", {}).items():
        req(loop["supply_side_outlet_node_names"], "System Node Temperature")
    pj = out / "patched.epjson"
    pj.write_text(json.dumps(stats_b))
    csv_path = out / "ep" / "eplusout.csv"
    if not (args.reuse and csv_path.is_file()):
        print(f"vavcal: {len(zones)} terminals; running EnergyPlus…")
        csv_path = run_energyplus(pj, epw, out / "ep")
    with open(csv_path) as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    import statistics as st
    temperr_stats, dterr_stats = [], []
    sat_cols = {lp: col(header, b["AirLoopHVAC"][lp]["supply_side_outlet_node_names"],
                        "System Node Temperature") for lp in b.get("AirLoopHVAC", {})}
    for tname, z in zones.items():
        zone_key = None
        for h in header:
            up = h.upper()
            if up.endswith(":Zone Mean Air Temperature [C](TimeStep)".upper()):
                zk = h.split(":")[0]
                if zk.upper() in tname.upper() or tname.upper().startswith(zk.upper()):
                    zone_key = zk
                    break
        if not zone_key:
            continue
        zt = series(data, col(header, zone_key, "Zone Mean Air Temperature"))
        hs = series(data, col(header, zone_key, "Zone Thermostat Heating Setpoint Temperature"))
        cs = series(data, col(header, zone_key, "Zone Thermostat Cooling Setpoint Temperature"))
        dat = series(data, col(header, z["out_node"], "System Node Temperature"))
        rht = series(data, col(header, z["rht_coil"], "Heating Coil Heating Rate")) \
            if z["rht_coil"] else [0.0] * len(zt)
        lp = None
        for l in sat_cols:                       # PACU_VAV_bot ↔ "…_bot…"/"…_bottom…"
            tag = l.upper().split("_")[-1]        # BOT / MID / TOP
            if tag and (f"_{tag}" in tname.upper() or f"_{tag.lower()}" in tname.lower()
                        or tag in tname.upper().replace("BOTTOM", "BOT")):
                lp = l
                break
        sat = series(data, sat_cols[lp]) if lp else None
        te = [ (t - c) if t > c else (t - h) if t < h else 0.0
               for t, h, c in zip(zt, hs, cs) ]
        occ = [h > 15.0 for h in hs]     # setback heating setpoint marks unoccupied
        te_occ = [e for e, o in zip(te, occ) if o]
        if len(te_occ) > 100:
            temperr_stats.append((st.mean(te_occ), st.pstdev(te_occ)))
        if sat:
            dte = [d_ - s for d_, s, r, o in zip(dat, sat, rht, occ)
                   if r < 100.0 and o]
            if len(dte) > 100:
                dterr_stats.append((st.mean(dte), st.pstdev(dte)))
    def med(v, i):
        v = sorted(x[i] for x in v)
        return round(v[len(v) // 2], 4) if v else None
    result = {
        "building": bdir.name, "period": f"{begin}-{end}",
        "zones_measured": len(temperr_stats),
        "temperror": {"mean_median": med(temperr_stats, 0), "std_median": med(temperr_stats, 1)},
        "dterror_reheat_off": {"mean_median": med(dterr_stats, 0), "std_median": med(dterr_stats, 1)},
    }
    (out / "vavcal.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("--building", required=True)
    runp.add_argument("--out", default=None)
    runp.add_argument("--begin", default="7-6", help="run period start M-D")
    runp.add_argument("--end", default="7-12", help="run period end M-D")
    runp.add_argument("--mode", default="airloop", choices=["airloop", "plant", "vavcal"])
    runp.add_argument("--reuse", action="store_true",
                      help="reuse an existing eplusout.csv instead of re-running EnergyPlus")
    runp.add_argument("--faultmodel", default=None, metavar="KIND=DELTA",
                      help="physics-level fault: patch FaultModel objects into the "
                           "epJSON before simulation (e.g. oa_temp_offset=4.0 — the "
                           "CONTROLLER acts on the biased sensor; FDD replays truth). "
                           "FAILs are DETECTIONS")
    runp.add_argument("--bias", default=None, metavar="POINT=DELTA",
                      help="TPR mode: add DELTA to POINT in the replayed inputs "
                           "(faulted-sensor-as-seen-by-FDD); FAILs are DETECTIONS")
    args = ap.parse_args()

    bdir = Path(args.building)
    out = Path(args.out) if args.out else bdir / "simharness_out"
    out.mkdir(parents=True, exist_ok=True)
    src = bdir / "building.epjson"
    if not src.is_file():
        src = next(bdir.glob("*.epJSON"))
    b = json.load(open(src))
    epw = next(bdir.glob("*.epw"))
    begin = tuple(int(x) for x in args.begin.split("-"))
    end = tuple(int(x) for x in args.end.split("-"))

    if args.mode == "plant":
        pn = plant_nodes(b)
        patched = patch_plant(b, pn, begin, end)
        pj = out / "patched.epjson"
        pj.write_text(json.dumps(patched))
        csv_path = out / "ep" / "eplusout.csv"
        if not (args.reuse and csv_path.is_file()):
            print(f"plant loops: {list(pn)}; running EnergyPlus…")
            csv_path = run_energyplus(pj, epw, out / "ep")
        fams = extract_plant(csv_path, pn, b)
        if "tower" in fams:
            tp = fams.pop("tower")
            on = tp["tower_fan_on"]
            appr = [round(l - w, 3) for l, w, o in
                    zip(tp["tower_leaving_temp"], tp["oa_wetbulb"], on) if o]
            rng = [round(e - l, 3) for e, l, o in
                   zip(tp["tower_entering_temp"], tp["tower_leaving_temp"], on) if o]
            if appr:
                import statistics as st
                def pct(v, q):
                    v = sorted(v); return round(v[min(len(v) - 1, int(q * len(v)))], 2)
                stats = {"ticks_tower_on": len(appr),
                         "approach_degC": {"p50": pct(appr, .5), "p90": pct(appr, .9),
                                            "p95": pct(appr, .95), "max": max(appr)},
                         "range_degC": {"p50": pct(rng, .5), "p90": pct(rng, .9),
                                         "max": max(rng)},
                         "wetbulb_degC": {"min": min(tp["oa_wetbulb"]),
                                           "max": max(tp["oa_wetbulb"])}}
                (out / "tower_stats.json").write_text(json.dumps(stats, indent=1))
                print(f"tower stats ({len(appr)} on-ticks): approach p50/p90/p95 = "
                      f"{stats['approach_degC']['p50']}/{stats['approach_degC']['p90']}/"
                      f"{stats['approach_degC']['p95']} degC; range p50 = {stats['range_degC']['p50']}")
            else:
                print("tower stats: tower never ran this period")
        rules = {}
        for fam in fams:
            for rid, r in eligible_rules(families=(fam, "sys"), mapped=PLANT_MAPPED).items():
                if rid not in rules:
                    if rid in PLANT_EXCLUDE:
                        print(f"  excluded {rid}: {PLANT_EXCLUDE[rid]}")
                    else:
                        rules[rid] = r
        print(f"eligible plant rules: {sorted(rules)}")
        replay = out / "replay"
        if replay.exists():
            shutil.rmtree(replay)
        dirs = []
        for rid, r in rules.items():
            fam = rid.split("-")[0].lower()
            pts = fams.get(fam) or fams.get("chw") or fams.get("hw")
            if not all(p in pts for p in r["points"]):
                continue
            n = len(pts["oat"])
            wins = plant_gate_windows(PLANT_GATE.get(rid), pts, n)
            if not wins:
                print(f"  {rid}: no gated windows this period"); continue
            d = replay / rid
            d.mkdir(parents=True)
            shutil.copy(r["dir"] / "rule.cxf.jsonld", d / "rule.cxf.jsonld")
            scen = {
                "name": f"{bdir.name}_{fam}".replace("-", "_").replace(".", "_").lower(),
                "description": f"Healthy-baseline EnergyPlus week ({bdir.name}); "
                               "plant-mode replay, gated; any FAIL is a false positive.",
                "inputs": {p: to_steps(pts[p]) for p in r["points"]},
                "expect": [{"output": "yFault", "from_s": a, "to_s": b_,
                            "equals": False} for a, b_ in wins],
            }
            (d / "vectors.json").write_text(json.dumps({
                "schema": "cxf-library/vectors/v1",
                "clock": {"step_s": STEP_S, "horizon_s": (n - 1) * STEP_S},
                "scenarios": [scen]}, indent=1))
            dirs.append(d)
        rr = subprocess.run(["cargo", "run", "--quiet", "--manifest-path",
                             str(REPO / "tools/verify/Cargo.toml"), "--", *map(str, dirs)],
                            capture_output=True, text=True, cwd=REPO)
        log = rr.stdout + rr.stderr
        (out / "verify.log").write_text(log)
        for line in log.splitlines():
            if re.search(r"replay/|PASS|FAIL", line):
                print(line if "replay/" not in line else "  " + line.split("replay/")[-1])
        return

    if args.mode == "vavcal":
        vavcal(b, bdir, out, epw, begin, end, args)
        return

    loops = loop_nodes(b)
    patched = patch(b, loops, begin, end)
    if args.faultmodel:
        kind, delta = args.faultmodel.split("=")
        assert kind == "oa_temp_offset", kind
        patched.setdefault("FaultModel:TemperatureSensorOffset:OutdoorAir", {})
        for i, oa in enumerate(patched.get("Controller:OutdoorAir", {})):
            patched["FaultModel:TemperatureSensorOffset:OutdoorAir"][f"simharness OAT fault {i}"] = {
                "controller_object_type": "Controller:OutdoorAir",
                "controller_object_name": oa,
                "temperature_sensor_offset": float(delta),
            }
        print(f"FaultModel injected: OAT sensor offset {delta} degC on "
              f"{len(patched.get('Controller:OutdoorAir', {}))} OA controllers — FAILs are DETECTIONS")
    pj = out / "patched.epjson"
    pj.write_text(json.dumps(patched))
    csv_path = out / "ep" / "eplusout.csv"
    if not (args.reuse and csv_path.is_file()):
        print(f"loops: {list(loops)}; running EnergyPlus…")
        csv_path = run_energyplus(pj, epw, out / "ep")
    loops_pts = extract(csv_path, loops)
    if args.bias:
        pt, delta = args.bias.split("=")
        delta = float(delta)
        for pts in loops_pts.values():
            if pt in pts:
                pts[pt] = [round(v + delta, ROUND) for v in pts[pt]]
        print(f"TPR bias applied: {pt} += {delta} — FAILs below are DETECTIONS")
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

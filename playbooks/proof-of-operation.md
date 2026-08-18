# Playbook: Proof-of-Operation Failure

| | |
|---|---|
| **Applies to** | AHU-0039 (supply fan), PMP-0003 (pump), HW-0009 (boiler) |
| **Fix complexity** | Remote (40%) · On-site (60%) |
| **Typical time** | 5–15 min remote; 30 min–2 h on-site |
| **Typical cost** | $0 remote / $100–$800 on-site (belt, contactor, overload reset; motor or drive repairs run higher) |
| **Energy impact** | Direction-dependent: fail-to-start costs delivery, not energy; unexpected-run is pure waste — a 10 kW pump left in HAND over a weekend is ~640 kWh nobody asked for, and the fan-affinity cube makes oversized fans worse |

**Library-authored playbook** for the proof-of-operation family: command
versus status, both directions (`yFailToStart` — commanded on, not proven;
`yUnexpectedRun` — proven on, not commanded). Grounded in ASHRAE Guideline
36-2021's proof definition (§5.1.6) and its alarm instances (§5.16.13.2
fans, §5.21.10.5 / §5.20.17.6 pumps and tower fans, §5.21.3 boiler prove),
paraphrased.

## Step 1 — Verify the fault

1. Identify the status device first — the diagnosis depends on it. A
   **current switch** proves the motor draws amps (a broken belt can still
   read ON); a **DP or flow switch** proves air/water actually moves; a
   **VFD status word** proves only what the drive believes; an **aux
   contact** proves the starter closed and nothing downstream.
2. For fail-to-start: confirm the command is actually reaching the
   equipment — read the BAS output at the controller, then the terminal.
   Check the HOA/HOA-equivalent switch position, the overload/reset flag,
   the drive's local/remote mode and fault code, and the disconnect.
3. For unexpected-run: look for HAND at the starter or drive, a local
   override, or a welded contactor (equipment runs with the starter
   de-energized — de-energize the circuit and listen).
4. Boilers (HW-0009): a failed prove usually means the burner-management
   system locked out — that is the BMS doing its safety job. Read the
   lockout code at the boiler. **Never bypass or repeatedly reset a
   safety lockout to clear an FDD alarm**; repeated lockout-retry cycles
   also surface as short-cycling (HW-0002).

## Step 2 — Remote fix

1. Release BAS/software overrides on the command point; confirm the
   output actually changes state at the controller.
2. Reset a tripped overload remotely only where the site's practice
   allows one reset; a second trip is an on-site electrical visit, not
   another reset.
3. If the status point is derived (VFD word, current threshold), sanity
   check its configuration — a current-switch threshold set above the
   motor's actual draw reports a running fan as off forever.

## Step 3 — On-site service

1. HOA in HAND: return to AUTO and find out why someone put it there —
   HAND is usually a workaround for a control problem this library has a
   rule for.
2. Broken or slipping belt, failed coupling: replace; check sheave
   alignment and tension. A current switch that kept reporting ON while
   the belt was broken should be replaced with a DP switch on rebuild.
3. Welded contactor or failed starter: replace the contactor; check coil
   voltage and cycling rate (chronic short-cycling welds contacts — see
   the equipment's short-cycling rule).
4. Drive faults: record the fault history before clearing; recurring
   drive faults are a power-quality or motor problem, not a reset ritual.
5. Boiler lockouts: service per the burner-management manual — flame
   sensor, pilot assembly, fuel train. FDD's job here ends at reporting
   availability; the fix belongs to a qualified burner technician.

## Step 4 — Confirm resolution

1. Command the equipment through a full stop→start→stop cycle from the
   BAS and watch both directions prove within their windows.
2. Both sub-condition flags should clear immediately on agreement; the
   fault should not reassert across at least one scheduled
   occupied/unoccupied transition.
3. If the same equipment reappears here monthly, the root cause is
   upstream: sizing, power quality, or an operator working around a
   control defect with the HOA switch.

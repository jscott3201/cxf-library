//! Fault-rule conformance runner (SCHEMA.md "Verification").
//!
//! For each fault directory: load `rule.cxf.jsonld` into a fresh engine per scenario, replay the
//! `vectors.json` inputs tick by tick, and check every assertion window. Exit code 0 only if every
//! scenario of every fault passes.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use oce_api::{Engine, PointDirection, PointValueType, Value};
use serde::Deserialize;

mod lint;

#[derive(Deserialize)]
struct Vectors {
    schema: String,
    clock: Clock,
    scenarios: Vec<Scenario>,
}

#[derive(Deserialize)]
struct Clock {
    step_s: f64,
    horizon_s: f64,
}

#[derive(Deserialize)]
struct Scenario {
    name: String,
    #[serde(default)]
    #[allow(dead_code)]
    description: Option<String>,
    inputs: serde_json::Map<String, serde_json::Value>,
    expect: Vec<Expect>,
}

#[derive(Deserialize)]
struct Expect {
    output: String,
    from_s: f64,
    to_s: f64,
    equals: serde_json::Value,
    #[serde(default)]
    tolerance: Option<f64>,
}

/// One staged input change: stage `value` on `path` before the first tick whose time >= `t`.
struct InputEvent {
    t: f64,
    path: String,
    value: Value,
}

/// Convert a JSON literal to an engine `Value`, coerced to the destination point's declared
/// type: a JSON number stages as `Integer` on an `Int` point and as `Real` on a `Real` point,
/// so vectors spell integer inputs as plain numbers with no format extension.
fn json_to_value(v: &serde_json::Value, want: PointValueType) -> Result<Value, String> {
    match (v, want) {
        (serde_json::Value::Bool(b), PointValueType::Bool) => Ok(Value::Boolean(*b)),
        (serde_json::Value::Number(n), PointValueType::Real) => n
            .as_f64()
            .map(Value::Real)
            .ok_or_else(|| format!("non-finite number {n}")),
        (serde_json::Value::Number(n), PointValueType::Int) => n
            .as_i64()
            .map(Value::Integer)
            .ok_or_else(|| format!("number {n} is not an exact i64 for an Int point")),
        (other, want) => Err(format!("value {other} cannot stage on a {want:?} point")),
    }
}

/// Resolve a canonical point name to the engine's full point path and declared value type.
/// Boundary connectors are `<root IRI>.<name>` per SCHEMA.md, so match on a `.<name>` or
/// `#<name>` suffix.
fn resolve_point(
    points: &[(String, PointDirection, PointValueType)],
    name: &str,
    want: PointDirection,
) -> Result<(String, PointValueType), String> {
    let dot = format!(".{name}");
    let hash = format!("#{name}");
    let hits: Vec<(&String, PointValueType)> = points
        .iter()
        .filter(|(p, d, _)| *d == want && (p.ends_with(&dot) || p.ends_with(&hash)))
        .map(|(p, _, vt)| (p, *vt))
        .collect();
    match hits.as_slice() {
        [(one, vt)] => Ok(((*one).clone(), *vt)),
        [] => Err(format!(
            "no {want:?} point matching `{name}`; available: {}",
            points
                .iter()
                .filter(|(_, d, _)| *d == want)
                .map(|(p, _, _)| p.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        )),
        many => Err(format!("point `{name}` is ambiguous: {many:?}")),
    }
}

fn values_match(got: &Value, expected: &serde_json::Value, tolerance: f64) -> bool {
    match (got, expected) {
        (Value::Boolean(g), serde_json::Value::Bool(e)) => g == e,
        (Value::Real(g), serde_json::Value::Number(n)) => {
            n.as_f64().is_some_and(|e| (g - e).abs() <= tolerance)
        }
        (Value::Integer(g), serde_json::Value::Number(n)) => n.as_i64().is_some_and(|e| *g == e),
        _ => false,
    }
}

fn fmt_value(v: &Value) -> String {
    match v {
        Value::Boolean(b) => b.to_string(),
        Value::Real(r) => r.to_string(),
        Value::Integer(i) => i.to_string(),
        other => format!("{other:?}"),
    }
}

fn run_scenario(
    rule_bytes: &[u8],
    clock: &Clock,
    scenario: &Scenario,
) -> Result<(), String> {
    let mut engine = Engine::in_memory();
    let report = engine
        .load_cxf(rule_bytes)
        .map_err(|e| format!("load_cxf failed: {e}"))?;
    for w in &report.warnings {
        eprintln!("      load warning: {w:?}");
    }

    let mut points: Vec<(String, PointDirection, PointValueType)> = engine
        .point_list(None)
        .map_err(|e| format!("point_list failed: {e}"))?
        .into_iter()
        .map(|p| (p.path, p.direction, p.value_type))
        .collect();
    // Root-declared boundary outputs are read aliases for their driving connectors — they appear
    // in `topology()`, not `point_list()`. `get_output` accepts the declared spelling directly.
    // `DeclaredOutput` carries no value type; the placeholder is never consulted because
    // `json_to_value` coercion only applies to staged inputs.
    for declared in engine.topology().boundary_outputs {
        points.push((declared.path, PointDirection::Out, PointValueType::Real));
    }

    // Flatten the input map into a time-sorted event list.
    let mut events: Vec<InputEvent> = Vec::new();
    for (name, spec) in &scenario.inputs {
        let (path, value_type) = resolve_point(&points, name, PointDirection::In)?;
        match spec {
            serde_json::Value::Array(steps) => {
                for step in steps {
                    let t = step
                        .get("t")
                        .and_then(serde_json::Value::as_f64)
                        .ok_or_else(|| format!("input `{name}`: step missing numeric `t`"))?;
                    let value = step
                        .get("value")
                        .ok_or_else(|| format!("input `{name}`: step missing `value`"))?;
                    events.push(InputEvent {
                        t,
                        path: path.clone(),
                        value: json_to_value(value, value_type)
                            .map_err(|e| format!("input `{name}`: {e}"))?,
                    });
                }
            }
            constant => events.push(InputEvent {
                t: 0.0,
                path: path.clone(),
                value: json_to_value(constant, value_type)
                    .map_err(|e| format!("input `{name}`: {e}"))?,
            }),
        }
    }
    events.sort_by(|a, b| a.t.total_cmp(&b.t));

    // Pre-resolve assertion outputs.
    let mut expects: Vec<(String, &Expect)> = Vec::new();
    for e in &scenario.expect {
        expects.push((resolve_point(&points, &e.output, PointDirection::Out)?.0, e));
    }

    let n_ticks = (clock.horizon_s / clock.step_s).floor() as u64;
    let mut next_event = 0usize;
    for k in 0..=n_ticks {
        let t = k as f64 * clock.step_s;
        while next_event < events.len() && events[next_event].t <= t {
            let ev = &events[next_event];
            engine
                .set_input(&ev.path, ev.value.clone())
                .map_err(|e| format!("set_input({}) failed: {e}", ev.path))?;
            next_event += 1;
        }
        engine.tick(t).map_err(|e| format!("tick({t}) failed: {e}"))?;
        for (path, exp) in &expects {
            if t < exp.from_s || t > exp.to_s {
                continue;
            }
            let got = engine
                .get_output(path)
                .map_err(|e| format!("get_output({path}) failed: {e}"))?;
            if !values_match(&got, &exp.equals, exp.tolerance.unwrap_or(1e-9)) {
                return Err(format!(
                    "t={t}s: `{}` = {} but expected {} (window {}..{}s)",
                    exp.output,
                    fmt_value(&got),
                    exp.equals,
                    exp.from_s,
                    exp.to_s
                ));
            }
        }
    }
    Ok(())
}

fn verify_fault_dir(dir: &Path) -> Result<bool, String> {
    let rule_path = dir.join("rule.cxf.jsonld");
    let vectors_path = dir.join("vectors.json");
    let rule_bytes =
        std::fs::read(&rule_path).map_err(|e| format!("{}: {e}", rule_path.display()))?;
    let vectors: Vectors = serde_json::from_slice(
        &std::fs::read(&vectors_path).map_err(|e| format!("{}: {e}", vectors_path.display()))?,
    )
    .map_err(|e| format!("{}: {e}", vectors_path.display()))?;
    if vectors.schema != "cxf-library/vectors/v1" {
        return Err(format!("unsupported vectors schema `{}`", vectors.schema));
    }

    println!("{}", dir.display());

    // Diagnostic identity: load once and report the engine's exported content id.
    let mut engine = Engine::in_memory();
    let mut content_id = None;
    match engine.load_cxf(&rule_bytes) {
        Ok(_) => match engine.export_cxf() {
            Ok(report) => match report.content_id_complete() {
                Ok(id) => {
                    println!("  content_id: {id}");
                    content_id = Some(id);
                }
                Err(e) => println!("  content_id unavailable (export warnings): {e}"),
            },
            Err(e) => println!("  export_cxf failed: {e}"),
        },
        Err(e) => return Err(format!("load_cxf failed: {e}")),
    }

    let mut all_pass = true;

    // Schema lint (SCHEMA.md conformance), including recorded-vs-actual content id.
    let repo_root = dir
        .canonicalize()
        .ok()
        .and_then(|d| d.parent().and_then(|p| p.parent()).and_then(|p| p.parent()).map(Path::to_path_buf))
        .ok_or("cannot locate repo root from fault dir")?;
    match lint::lint_fault_dir(dir, &repo_root) {
        Ok(report) => {
            let mut errors = report.errors;
            if matches!(report.status.as_str(), "verified" | "adopted")
                && let (Some(recorded), Some(actual)) = (&report.recorded_content_id, &content_id)
                && recorded != actual
            {
                errors.push(format!(
                    "verified.content_id `{recorded}` != engine export `{actual}` — re-verify and update the card"
                ));
            }
            if errors.is_empty() {
                println!("  LINT  ok");
            } else {
                all_pass = false;
                for e in errors {
                    println!("  LINT  {e}");
                }
            }
        }
        Err(e) => {
            all_pass = false;
            println!("  LINT  {e}");
        }
    }
    for scenario in &vectors.scenarios {
        match run_scenario(&rule_bytes, &vectors.clock, scenario) {
            Ok(()) => println!("  PASS  {}", scenario.name),
            Err(msg) => {
                all_pass = false;
                println!("  FAIL  {} — {msg}", scenario.name);
            }
        }
    }
    Ok(all_pass)
}

/// Every `faults/<equip>/<FAULT-ID>/` directory containing a rule document, sorted.
fn discover_fault_dirs(faults_root: &Path) -> Result<Vec<PathBuf>, String> {
    let mut dirs = Vec::new();
    for equip in std::fs::read_dir(faults_root).map_err(|e| format!("{}: {e}", faults_root.display()))? {
        let equip = equip.map_err(|e| e.to_string())?.path();
        if !equip.is_dir() {
            continue;
        }
        for fault in std::fs::read_dir(&equip).map_err(|e| e.to_string())? {
            let fault = fault.map_err(|e| e.to_string())?.path();
            if fault.is_dir() && fault.join("rule.cxf.jsonld").is_file() {
                dirs.push(fault);
            }
        }
    }
    dirs.sort();
    Ok(dirs)
}

fn main() -> ExitCode {
    let mut args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    if args.iter().any(|a| a.as_os_str() == "--all") {
        args = match discover_fault_dirs(Path::new("faults")) {
            Ok(dirs) => dirs,
            Err(e) => {
                eprintln!("--all: {e}");
                return ExitCode::from(2);
            }
        };
        println!("discovered {} fault dirs", args.len());
    }
    if args.is_empty() {
        eprintln!("usage: cxf-verify --all | <fault-dir>… (each containing rule.cxf.jsonld + vectors.json)");
        return ExitCode::from(2);
    }
    let mut ok = true;
    for dir in &args {
        match verify_fault_dir(dir) {
            Ok(pass) => ok &= pass,
            Err(msg) => {
                ok = false;
                println!("{}\n  ERROR {msg}", dir.display());
            }
        }
    }
    if ok {
        println!("all scenarios passed");
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}

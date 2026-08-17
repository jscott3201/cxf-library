//! Fault-rule conformance runner (SCHEMA.md "Verification").
//!
//! For each fault directory: load `rule.cxf.jsonld` into a fresh engine per scenario, replay the
//! `vectors.json` inputs tick by tick, and check every assertion window. Exit code 0 only if every
//! scenario of every fault passes.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use oce_api::{Engine, PointDirection, Value};
use serde::Deserialize;

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

fn json_to_value(v: &serde_json::Value) -> Result<Value, String> {
    match v {
        serde_json::Value::Bool(b) => Ok(Value::Boolean(*b)),
        serde_json::Value::Number(n) => n
            .as_f64()
            .map(Value::Real)
            .ok_or_else(|| format!("non-finite number {n}")),
        other => Err(format!("unsupported input value {other}")),
    }
}

/// Resolve a canonical point name to the engine's full point path. Boundary connectors are
/// `<root IRI>.<name>` per SCHEMA.md, so match on a `.<name>` or `#<name>` suffix.
fn resolve_point(
    points: &[(String, PointDirection)],
    name: &str,
    want: PointDirection,
) -> Result<String, String> {
    let dot = format!(".{name}");
    let hash = format!("#{name}");
    let hits: Vec<&String> = points
        .iter()
        .filter(|(p, d)| *d == want && (p.ends_with(&dot) || p.ends_with(&hash)))
        .map(|(p, _)| p)
        .collect();
    match hits.as_slice() {
        [one] => Ok((*one).clone()),
        [] => Err(format!(
            "no {want:?} point matching `{name}`; available: {}",
            points
                .iter()
                .filter(|(_, d)| *d == want)
                .map(|(p, _)| p.as_str())
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

    let mut points: Vec<(String, PointDirection)> = engine
        .point_list(None)
        .map_err(|e| format!("point_list failed: {e}"))?
        .into_iter()
        .map(|p| (p.path, p.direction))
        .collect();
    // Root-declared boundary outputs are read aliases for their driving connectors — they appear
    // in `topology()`, not `point_list()`. `get_output` accepts the declared spelling directly.
    for declared in engine.topology().boundary_outputs {
        points.push((declared.path, PointDirection::Out));
    }

    // Flatten the input map into a time-sorted event list.
    let mut events: Vec<InputEvent> = Vec::new();
    for (name, spec) in &scenario.inputs {
        let path = resolve_point(&points, name, PointDirection::In)?;
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
                        value: json_to_value(value).map_err(|e| format!("input `{name}`: {e}"))?,
                    });
                }
            }
            constant => events.push(InputEvent {
                t: 0.0,
                path: path.clone(),
                value: json_to_value(constant).map_err(|e| format!("input `{name}`: {e}"))?,
            }),
        }
    }
    events.sort_by(|a, b| a.t.total_cmp(&b.t));

    // Pre-resolve assertion outputs.
    let mut expects: Vec<(String, &Expect)> = Vec::new();
    for e in &scenario.expect {
        expects.push((resolve_point(&points, &e.output, PointDirection::Out)?, e));
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
    match engine.load_cxf(&rule_bytes) {
        Ok(_) => match engine.export_cxf() {
            Ok(report) => match report.content_id_complete() {
                Ok(id) => println!("  content_id: {id}"),
                Err(e) => println!("  content_id unavailable (export warnings): {e}"),
            },
            Err(e) => println!("  export_cxf failed: {e}"),
        },
        Err(e) => return Err(format!("load_cxf failed: {e}")),
    }

    let mut all_pass = true;
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

fn main() -> ExitCode {
    let args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    if args.is_empty() {
        eprintln!("usage: cxf-verify <fault-dir>… (each containing rule.cxf.jsonld + vectors.json)");
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

use std::path::Path;
use std::process::Command;

const ENGINE_ROOT: &str = "../../../open-control";

fn git(args: &[&str]) -> String {
    let output = Command::new("git")
        .arg("-C")
        .arg(ENGINE_ROOT)
        .args(args)
        .output()
        .expect("run git to identify the open-control engine source");
    if !output.status.success() {
        panic!(
            "cannot identify open-control engine source: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        );
    }
    String::from_utf8(output.stdout)
        .expect("open-control Git output must be UTF-8")
        .trim()
        .to_string()
}

fn main() {
    let revision = git(&["rev-parse", "HEAD"]);
    let pin = std::fs::read_to_string("../../ENGINE_PIN")
        .expect("read ENGINE_PIN")
        .trim()
        .to_string();
    assert_eq!(
        revision, pin,
        "open-control checkout must exactly match ENGINE_PIN"
    );

    let dirty = git(&["status", "--porcelain", "--untracked-files=no"]);
    assert!(
        dirty.is_empty(),
        "open-control checkout has tracked modifications; pinned verifier builds require a clean engine tree"
    );

    let git_dir = git(&["rev-parse", "--absolute-git-dir"]);
    println!("cargo:rerun-if-changed={git_dir}/HEAD");
    println!("cargo:rerun-if-changed={git_dir}/packed-refs");
    let symbolic_ref = Command::new("git")
        .arg("-C")
        .arg(ENGINE_ROOT)
        .args(["symbolic-ref", "-q", "HEAD"])
        .output()
        .expect("resolve open-control symbolic ref");
    if symbolic_ref.status.success() {
        let reference = String::from_utf8(symbolic_ref.stdout)
            .expect("open-control symbolic ref must be UTF-8")
            .trim()
            .to_string();
        println!(
            "cargo:rerun-if-changed={}",
            Path::new(&git_dir).join(reference).display()
        );
    }

    println!("cargo:rustc-env=CXF_ENGINE_SOURCE_REV={revision}");
    println!("cargo:rerun-if-changed={ENGINE_ROOT}/crates");
    println!("cargo:rerun-if-changed={ENGINE_ROOT}/Cargo.toml");
    println!("cargo:rerun-if-changed={ENGINE_ROOT}/Cargo.lock");
    println!("cargo:rerun-if-changed=../../ENGINE_PIN");
}

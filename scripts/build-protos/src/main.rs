//! Maintainers-only: generate prebuilt Rust into `crates/awpy-proto/src/proto.rs`.
//!
//! Run from the workspace root:
//!
//! ```sh
//! cargo run --manifest-path scripts/build-protos/Cargo.toml
//! ```
//!
//! Reads the allowlist at `crates/awpy-proto/proto/allowlist.txt`, compiles the
//! listed `.proto` files with prost, and concatenates the generated modules into
//! a single checked-in `proto.rs`.

use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};

fn read_allowlist(manifest: &Path) -> Vec<String> {
    let content = fs::read_to_string(manifest)
        .unwrap_or_else(|e| panic!("read manifest {}: {}", manifest.display(), e));

    let mut out = Vec::new();
    for (i, raw) in content.lines().enumerate() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        if !line.ends_with(".proto") {
            panic!(
                "manifest {} line {}: expected *.proto, got: {}",
                manifest.display(),
                i + 1,
                raw
            );
        }
        out.push(line.to_string());
    }
    out
}

fn main() {
    let manifest = Path::new("crates/awpy-proto/proto/allowlist.txt");
    let proto_root = Path::new("crates/awpy-proto/proto");
    let dest_dir = Path::new("crates/awpy-proto/src/");
    let out_file = dest_dir.join("proto.rs");

    if !manifest.exists() {
        eprintln!("manifest not found at {}", manifest.display());
        std::process::exit(1);
    }
    if !proto_root.exists() {
        eprintln!("proto root not found at {}", proto_root.display());
        std::process::exit(1);
    }

    let allow = read_allowlist(manifest);

    let mut protos: Vec<PathBuf> = Vec::with_capacity(allow.len());
    for name in &allow {
        let p = proto_root.join(name);
        if !p.exists() {
            eprintln!("missing proto: {}", p.display());
            std::process::exit(1);
        }
        protos.push(p);
    }

    let tmp = tempfile::tempdir().expect("tmp dir");
    let out_tmp = tmp.path().to_path_buf();

    let mut cfg = prost_build::Config::new();
    cfg.out_dir(&out_tmp);
    cfg.type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]");

    cfg.compile_protos(&protos, &[proto_root])
        .expect("prost compile");

    fs::create_dir_all(dest_dir).expect("create dest");

    let mut files: Vec<PathBuf> = fs::read_dir(&out_tmp)
        .expect("read tmp out")
        .filter_map(|e| {
            let p = e.ok()?.path();
            (p.extension().and_then(|s| s.to_str()) == Some("rs")).then_some(p)
        })
        .collect();
    files.sort();

    let mut out = fs::File::create(&out_file).expect("create output");
    writeln!(out, "// @generated — DO NOT EDIT.\n").unwrap();

    for fpath in files {
        let contents = fs::read_to_string(&fpath)
            .unwrap_or_else(|e| panic!("read {}: {}", fpath.display(), e));
        out.write_all(contents.as_bytes()).unwrap();
    }

    println!("Wrote {}", out_file.display());
}

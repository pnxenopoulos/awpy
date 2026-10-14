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
    sync::LazyLock,
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

// Valve's C++ annotations are not standard protobuf options. Remove only these
// annotations from temporary compiler inputs; keep defaults and wire fields.
fn rust_proto(source: &str) -> String {
    static OPTIONS: LazyLock<regex::Regex> = LazyLock::new(|| {
        regex::Regex::new(concat!(
            r#"(?P<include>\boption\s+additional_includes\s*=\s*"(?:\\.|[^"\\])*"\s*;)"#,
            r#"|(?P<before>[\[,])\s*(?:boxed_type|synthetic_default)\s*=\s*"(?:\\.|[^"\\])*"\s*(?P<after>[,\]])"#,
            r#"|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*(?s:.*?)\*/"#,
        ))
        .expect("C++ option pattern")
    });

    let mut source = source.to_owned();
    loop {
        let updated = OPTIONS.replace_all(&source, |captures: &regex::Captures<'_>| {
            if captures.name("include").is_some() {
                String::new()
            } else if let (Some(before), Some(after)) =
                (captures.name("before"), captures.name("after"))
            {
                match (before.as_str(), after.as_str()) {
                    ("[", "]") => "",
                    ("[", ",") => "[",
                    (",", "]") => "]",
                    _ => ",",
                }
                .to_owned()
            } else {
                captures[0].to_owned()
            }
        });
        if updated == source {
            return source;
        }
        // Adjacent annotations share a delimiter and need another pass.
        source = updated.into_owned();
    }
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

    let tmp = tempfile::tempdir().expect("tmp dir");
    let input_dir = tmp.path().join("proto");
    fs::create_dir(&input_dir).expect("create temporary inputs");
    let protos: Vec<PathBuf> = allow
        .iter()
        .map(|name| {
            let original = proto_root.join(name);
            let source = fs::read_to_string(&original)
                .unwrap_or_else(|e| panic!("read {}: {}", original.display(), e));
            let input = input_dir.join(name);
            fs::write(&input, rust_proto(&source)).expect("write temporary proto");
            input
        })
        .collect();

    let out_tmp = tmp.path();
    let mut cfg = prost_build::Config::new();
    cfg.out_dir(out_tmp);
    cfg.protoc_executable(protoc_bin_vendored::protoc_bin_path().expect("protoc path"));
    cfg.type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]");
    cfg.compile_protos(
        &protos,
        &[
            input_dir,
            protoc_bin_vendored::include_path().expect("protoc includes"),
        ],
    )
    .expect("prost compile");

    fs::create_dir_all(dest_dir).expect("create dest");

    let mut files: Vec<PathBuf> = fs::read_dir(out_tmp)
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

#[cfg(test)]
mod tests {
    use super::rust_proto;

    #[test]
    fn cpp_annotations_do_not_change_wire_options() {
        for (input, expected) in [
            (r#"[boxed_type = "Token"]"#, ""),
            (r#"[boxed_type = "Token", synthetic_default = "0"]"#, ""),
            (r#"[boxed_type = "Token", default = 42]"#, "[ default = 42]"),
            (
                r#"[default = 42, boxed_type = "Token", synthetic_default = "0"]"#,
                "[default = 42]",
            ),
            (
                r#"[boxed_type = "Pair<A, B>", packed = true, synthetic_default = "0", (key_field) = true]"#,
                "[ packed = true, (key_field) = true]",
            ),
            (r#"option additional_includes = "some/header.h";"#, ""),
        ] {
            assert_eq!(rust_proto(input), expected);
        }
    }

    #[test]
    fn strings_comments_and_other_options_are_unchanged() {
        let source = r#"
// [boxed_type = "Token"]
/* option additional_includes = "header.h"; */
optional string label = 1 [default = "a, [boxed_type = \"Token\"]"];
optional uint32 value = 2 [default = 42, (key_field) = true];
option unsupported_future_annotation = true;
"#;
        assert_eq!(rust_proto(source), source);
    }
}

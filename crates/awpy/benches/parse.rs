//! Parser pipeline benchmarks.
//!
//! Each phase of the parse pipeline is timed in isolation so it is obvious where
//! the time goes:
//!
//! - `init` group — the one-time costs paid before any tick is decoded:
//!   `from_file` (open + memory-map), `parse_send_tables`, `parse_class_info`,
//!   and `parse_init`.
//! - `decode` group — `messages` (enumerate every message without decoding
//!   entities), `events` (decode all game events), and `run_to_end` (full entity
//!   decode: every class, every tick). These report throughput (MiB/s).
//!
//! The demo is chosen from `$AWPY_BENCH_DEMO`, else the smallest `.dem` under the
//! repository's `demos/` directory. When none is present every benchmark skips.

use std::hint::black_box;
use std::path::PathBuf;
use std::time::Duration;

use criterion::{BatchSize, Criterion, Throughput, criterion_group, criterion_main};

use awpy::Parser;

/// Resolve the demo file to benchmark against.
fn demo_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("AWPY_BENCH_DEMO") {
        let p = PathBuf::from(p);
        return p.exists().then_some(p);
    }
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../demos");
    let mut demos: Vec<PathBuf> = std::fs::read_dir(dir)
        .ok()?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "dem"))
        .collect();
    demos.sort_by_key(|p| std::fs::metadata(p).map(|m| m.len()).unwrap_or(u64::MAX));
    demos.into_iter().next()
}

fn load_bytes() -> Option<Vec<u8>> {
    let path = demo_path()?;
    std::fs::read(path).ok()
}

fn bench_init(c: &mut Criterion) {
    let Some(bytes) = load_bytes() else {
        eprintln!("awpy parse bench: no demo available (set AWPY_BENCH_DEMO); skipping `init`");
        return;
    };

    let mut group = c.benchmark_group("init");
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("parse_send_tables", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| black_box(p.parse_send_tables().unwrap()),
            BatchSize::LargeInput,
        )
    });

    group.bench_function("parse_class_info", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| black_box(p.parse_class_info().unwrap()),
            BatchSize::LargeInput,
        )
    });

    group.bench_function("parse_init", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| black_box(p.parse_init().unwrap()),
            BatchSize::LargeInput,
        )
    });

    group.finish();
}

fn bench_decode(c: &mut Criterion) {
    let Some(bytes) = load_bytes() else {
        eprintln!("awpy parse bench: no demo available (set AWPY_BENCH_DEMO); skipping `decode`");
        return;
    };
    let len = bytes.len() as u64;

    let mut group = c.benchmark_group("decode");
    group.measurement_time(Duration::from_secs(15));
    group.throughput(Throughput::Bytes(len));

    group.bench_function("messages", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| black_box(p.messages().unwrap()),
            BatchSize::LargeInput,
        )
    });

    group.bench_function("events", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| black_box(p.events(None).unwrap()),
            BatchSize::LargeInput,
        )
    });

    group.bench_function("run_to_end", |b| {
        b.iter_batched(
            || Parser::from_bytes(bytes.clone()),
            |p| {
                let mut ticks = 0usize;
                p.run_to_end(|_ctx| ticks += 1).unwrap();
                black_box(ticks)
            },
            BatchSize::LargeInput,
        )
    });

    group.finish();
}

criterion_group!(benches, bench_init, bench_decode);
criterion_main!(benches);

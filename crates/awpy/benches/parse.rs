//! Parsing benchmarks for cargo-criterion and cargo bench.
//!
//! Set AWPY_BENCH_DEMO to a demo file. Otherwise, use the smallest demo in
//! the repository root or demos directory. See README.md in this directory.

use std::collections::HashSet;
use std::hint::black_box;
use std::path::PathBuf;
use std::time::Duration;

use awpy::{EventDatasetSelection, Parser};
use criterion::measurement::WallTime;
use criterion::{
    BatchSize, BenchmarkGroup, BenchmarkId, Criterion, SamplingMode, Throughput, criterion_group,
    criterion_main,
};

struct DemoInput {
    path: PathBuf,
    label: String,
    bytes: u64,
}

impl DemoInput {
    fn find() -> Option<Self> {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        let path = if let Some(path) = std::env::var_os("AWPY_BENCH_DEMO") {
            root.join(path)
        } else {
            let mut candidates = Vec::new();
            for directory in [root.join("demos"), root] {
                let entries = match std::fs::read_dir(&directory) {
                    Ok(entries) => entries,
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
                    Err(error) => panic!("cannot read {}: {error}", directory.display()),
                };
                for entry in entries {
                    let path = entry.expect("cannot read demo directory entry").path();
                    if path.extension().is_some_and(|extension| extension == "dem") {
                        let metadata = path.metadata().expect("cannot read demo metadata");
                        if metadata.is_file() {
                            candidates.push((metadata.len(), path));
                        }
                    }
                }
            }
            candidates.into_iter().min()?.1
        };

        let path = path
            .canonicalize()
            .unwrap_or_else(|error| panic!("cannot open demo {}: {error}", path.display()));
        let bytes = path.metadata().expect("cannot read demo metadata").len();
        let name = path.file_name().expect("demo path must name a file");
        let label = format!("{}-{bytes}B", name.to_string_lossy());
        let demo = Self { path, label, bytes };
        demo.open().verify().expect("invalid demo header");
        Some(demo)
    }

    fn open(&self) -> Parser {
        Parser::from_file(black_box(&self.path))
            .unwrap_or_else(|error| panic!("cannot map demo {}: {error}", self.path.display()))
    }
}

/// Exclude file mapping and final cleanup from the parse time.
/// Keep only one parser and one result alive at a time.
fn bench_parse<T>(
    group: &mut BenchmarkGroup<'_, WallTime>,
    demo: &DemoInput,
    name: &str,
    parse: impl Fn(&Parser) -> awpy::Result<T>,
) {
    group.bench_function(BenchmarkId::new(name, &demo.label), |b| {
        b.iter_batched_ref(
            || demo.open(),
            |parser| black_box(parse(black_box(&*parser)).expect("benchmark parse failed")),
            BatchSize::PerIteration,
        );
    });
}

fn bench_init(c: &mut Criterion, demo: &DemoInput) {
    let mut group = c.benchmark_group("init");
    group.sampling_mode(SamplingMode::Flat);
    group.bench_function(BenchmarkId::new("from_file", &demo.label), |b| {
        b.iter_batched(|| (), |()| black_box(demo.open()), BatchSize::PerIteration);
    });
    bench_parse(
        &mut group,
        demo,
        "parse_send_tables",
        Parser::parse_send_tables,
    );
    bench_parse(
        &mut group,
        demo,
        "parse_class_info",
        Parser::parse_class_info,
    );
    bench_parse(&mut group, demo, "parse_init", Parser::parse_init);
    group.finish();
}

fn bench_decode(c: &mut Criterion, demo: &DemoInput) {
    let mut group = c.benchmark_group("decode");
    group.sampling_mode(SamplingMode::Flat);
    group.throughput(Throughput::Bytes(demo.bytes));

    bench_parse(&mut group, demo, "messages", Parser::messages);
    bench_parse(&mut group, demo, "events", |parser| parser.events(None));
    bench_parse(&mut group, demo, "run_to_end", |parser| {
        let mut ticks = 0usize;
        parser.run_to_end(|_| ticks += 1)?;
        Ok(ticks)
    });
    let classes = HashSet::from(["CCSPlayerController", "CCSPlayerPawn"]);
    bench_parse(&mut group, demo, "player_entities", |parser| {
        let mut ticks = 0usize;
        parser.run_to_end_filtered(black_box(&classes), |_| ticks += 1)?;
        Ok(ticks)
    });
    group.finish();
}

fn bench_datasets(c: &mut Criterion, demo: &DemoInput) {
    let mut group = c.benchmark_group("datasets");
    group.sampling_mode(SamplingMode::Flat);
    group.throughput(Throughput::Bytes(demo.bytes));

    bench_parse(&mut group, demo, "players", Parser::players);
    bench_parse(&mut group, demo, "rounds", Parser::rounds);
    bench_parse(&mut group, demo, "stats", |parser| {
        parser.player_stats(true)
    });
    bench_parse(&mut group, demo, "event_datasets", Parser::event_datasets);
    bench_parse(&mut group, demo, "kills", Parser::kills);
    let selection = EventDatasetSelection {
        kills: true,
        bomb: true,
        shots: true,
        ..Default::default()
    };
    bench_parse(&mut group, demo, "kills_bomb_shots_combined", |parser| {
        parser.event_datasets_selected(black_box(selection))
    });
    bench_parse(&mut group, demo, "kills_bomb_shots_separate", |parser| {
        Ok((parser.kills()?, parser.bomb()?, parser.shots()?))
    });
    bench_parse(&mut group, demo, "projectiles", Parser::projectiles);
    let ticks = HashSet::new();
    bench_parse(&mut group, demo, "snapshots_every_64", |parser| {
        parser.snapshots_query(Some(64), black_box(&ticks), 0, i32::MAX)
    });
    group.finish();
}

fn bench_parser(c: &mut Criterion) {
    let Some(demo) = DemoInput::find() else {
        eprintln!(
            "awpy parse bench: no demo found; no measurements will run. \
             Set AWPY_BENCH_DEMO to a .dem file."
        );
        return;
    };
    eprintln!(
        "awpy parse bench: {} ({} bytes), AWPY_TICK_SEGMENTS={}",
        demo.path.display(),
        demo.bytes,
        std::env::var("AWPY_TICK_SEGMENTS").unwrap_or_else(|_| "auto".into()),
    );
    bench_init(c, &demo);
    bench_decode(c, &demo);
    bench_datasets(c, &demo);
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .sample_size(10)
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(10));
    targets = bench_parser
}
criterion_main!(benches);

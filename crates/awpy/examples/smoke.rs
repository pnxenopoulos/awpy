//! End-to-end smoke test: `cargo run --release --example smoke -- <demo.dem>`.
//!
//! Exercises the full pipeline against a real CS2 demo and prints a summary of
//! the header, message counts, top game events, class/serializer counts, and a
//! sample of decoded player entities from the middle of the match.

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use awpy::Parser;

fn main() {
    let path = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            eprintln!("usage: smoke <demo.dem>");
            std::process::exit(2);
        });

    let t0 = Instant::now();
    let parser = Parser::from_file(&path).expect("open demo");
    parser.verify().expect("verify magic");

    // ── Header ──
    let header = parser.file_header().expect("file header");
    println!("== header ==");
    println!("  demo_file_stamp : {:?}", header.demo_file_stamp);
    println!("  map_name        : {:?}", header.map_name);
    println!("  server_name     : {:?}", header.server_name);
    println!("  build_num       : {:?}", header.build_num);

    // ── File info ──
    match parser.file_info() {
        Ok(info) => {
            println!("== file_info ==");
            println!("  playback_ticks  : {:?}", info.playback_ticks);
            println!("  playback_time   : {:?}", info.playback_time);
            println!("  playback_frames : {:?}", info.playback_frames);
        }
        Err(e) => println!("== file_info == (unavailable: {e})"),
    }

    // ── Messages ──
    let messages = parser.messages().expect("messages");
    let mut by_cmd: HashMap<String, usize> = HashMap::new();
    for m in &messages {
        *by_cmd.entry(m.cmd_name.clone()).or_default() += 1;
    }
    println!("== messages: {} total ==", messages.len());
    let mut cmd_counts: Vec<_> = by_cmd.into_iter().collect();
    cmd_counts.sort_by_key(|&(_, n)| std::cmp::Reverse(n));
    for (name, n) in cmd_counts {
        println!("  {name:<20} {n}");
    }

    // ── Init: serializers, classes, string tables ──
    let ctx = parser.parse_init().expect("parse_init");
    println!("== init ==");
    println!("  serializers     : {}", ctx.serializers.serializers.len());
    println!("  classes         : {}", ctx.class_info.classes.len());
    println!("  class_id bits   : {}", ctx.class_info.bits);
    println!("  string tables   : {}", ctx.string_tables.tables().len());
    println!("  tick_interval   : {}", ctx.tick_interval);

    // ── Events ──
    let events = parser.events(None).expect("events");
    let mut ev_counts: HashMap<String, usize> = HashMap::new();
    for e in &events {
        *ev_counts.entry(e.name.clone()).or_default() += 1;
    }
    let mut ev: Vec<_> = ev_counts.into_iter().collect();
    ev.sort_by_key(|&(_, n)| std::cmp::Reverse(n));
    println!(
        "== events: {} total, {} distinct ==",
        events.len(),
        ev.len()
    );
    for (name, n) in ev.iter().take(20) {
        println!("  {name:<32} {n}");
    }

    // Show a couple of player_death events with their keys.
    println!("== sample player_death events ==");
    for e in events.iter().filter(|e| e.name == "player_death").take(3) {
        println!("  tick {}: {:?}", e.tick, e.keys);
    }

    // ── Full entity decode ──
    let t_run = Instant::now();
    let mut tick_count = 0usize;
    let mut max_entities = 0usize;
    let mut last_class_sample: Vec<String> = Vec::new();
    parser
        .run_to_end(|ctx| {
            tick_count += 1;
            max_entities = max_entities.max(ctx.entities.len());
            if tick_count == 1 {
                let mut names: Vec<String> = ctx
                    .entities
                    .iter()
                    .map(|(_, e)| e.class_name.clone())
                    .collect();
                names.sort();
                names.dedup();
                last_class_sample = names;
            }
        })
        .expect("run_to_end");
    println!("== run_to_end ==");
    println!("  ticks           : {tick_count}");
    println!("  peak entities   : {max_entities}");
    println!("  run_to_end time : {:?}", t_run.elapsed());
    println!(
        "  distinct classes on first tick: {}",
        last_class_sample.len()
    );

    // Look for CS2 player pawn/controller classes among active entities.
    for want in ["CCSPlayerPawn", "CCSPlayerController", "CCSGameRulesProxy"] {
        let present = last_class_sample.iter().any(|c| c == want);
        println!("  has {want:<22}: {present}");
    }

    println!("== done in {:?} ==", t0.elapsed());
}

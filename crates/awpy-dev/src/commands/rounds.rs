use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let rounds = parser.rounds()?;

    if json {
        return super::print_json(&rounds);
    }

    println!(
        "{:<5} {:<8} {:<10} {:<8} {:<10} {:<18} {}",
        "Rnd".bold(),
        "Start".bold(),
        "FreezeEnd".bold(),
        "End".bold(),
        "Official".bold(),
        "Winner".bold(),
        "Reason".bold(),
    );
    println!("{}", "-".repeat(80));

    let fmt_tick = |t: Option<i32>| t.map(|v| v.to_string()).unwrap_or_else(|| "-".into());

    for r in &rounds {
        let winner = if r.winner == 2 {
            r.winner_side.red().to_string()
        } else if r.winner == 3 {
            r.winner_side.blue().to_string()
        } else {
            r.winner_side.clone()
        };
        println!(
            "{:<5} {:<8} {:<10} {:<8} {:<10} {:<18} {}",
            r.round_num,
            fmt_tick(r.start_tick),
            fmt_tick(r.freeze_end_tick),
            r.end_tick,
            fmt_tick(r.official_end_tick),
            winner,
            r.reason_name,
        );
    }

    println!("\n{} rounds", rounds.len());
    Ok(())
}

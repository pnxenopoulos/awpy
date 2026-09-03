use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let stats = parser.player_stats(true)?;

    if json {
        println!("{}", serde_json::to_string_pretty(&stats)?);
        return Ok(());
    }

    println!(
        "{:<16} {:>3} {:>3} {:>3} {:>3} {:>3} {:>3} {:>3} {:>6} {:>6} {:>6}",
        "Player".bold(),
        "K".bold(),
        "D".bold(),
        "A".bold(),
        "HS".bold(),
        "OK".bold(),
        "OD".bold(),
        "TD".bold(),
        "KAST".bold(),
        "ADR".bold(),
        "CL".bold(),
    );
    println!("{}", "-".repeat(72));
    for s in &stats {
        println!(
            "{:<16} {:>3} {:>3} {:>3} {:>3} {:>3} {:>3} {:>3} {:>5.0}% {:>6.1} {:>6}",
            s.name,
            s.kills,
            s.deaths,
            s.assists,
            s.headshot_kills,
            s.opening_kills,
            s.opening_deaths,
            s.traded_deaths,
            s.kast,
            s.adr,
            format!("{}/{}", s.clutches_won, s.clutches_played),
        );
    }
    println!(
        "\n{} players over {} rounds. \
         K=kills D=deaths A=assists HS=headshot kills OK/OD=opening kills/deaths \
         TD=traded deaths CL=clutches won/played. \
         Use --json for all columns (flash assists, multi-kills, clutch breakdown).",
        stats.len(),
        stats.first().map(|s| s.rounds_played).unwrap_or(0),
    );
    Ok(())
}

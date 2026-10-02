use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let blinds = parser.blinds()?;

    let display_limit = limit.unwrap_or(blinds.len());
    let shown = &blinds[..display_limit.min(blinds.len())];

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    println!(
        "{:<8} {:<16} {:<16} {:<18} {}",
        "Tick".bold(),
        "Attacker".bold(),
        "Victim".bold(),
        "Victim side".bold(),
        "Duration".bold(),
    );
    println!("{}", "-".repeat(72));
    for b in shown {
        println!(
            "{:<8} {:<16} {:<16} {:<18} {:.2}s",
            b.tick,
            b.attacker_name.as_deref().unwrap_or("?"),
            b.victim_name.as_deref().unwrap_or("?"),
            b.victim_side.as_deref().unwrap_or("-"),
            b.duration,
        );
    }
    println!(
        "\n{} blinds total{}",
        blinds.len(),
        if display_limit < blinds.len() {
            format!(" (showing first {display_limit})")
        } else {
            String::new()
        }
    );
    Ok(())
}

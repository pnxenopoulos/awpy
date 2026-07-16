use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let shots = parser.shots()?;

    let display_limit = limit.unwrap_or(shots.len());
    let shown = &shots[..display_limit.min(shots.len())];

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    println!(
        "{:<8} {:<16} {:<20} {:<7} {:<6} {}",
        "Tick".bold(),
        "Player".bold(),
        "Weapon".bold(),
        "Scoped".bold(),
        "Clip".bold(),
        "Inaccuracy".bold(),
    );
    println!("{}", "-".repeat(70));
    for s in shown {
        println!(
            "{:<8} {:<16} {:<20} {:<7} {:<6} {:.4}",
            s.tick,
            s.name.as_deref().unwrap_or("?"),
            s.weapon,
            s.scoped
                .map(|b| if b { "yes" } else { "no" })
                .unwrap_or("-"),
            s.num_bullets_remaining
                .map(|c| c.to_string())
                .unwrap_or_else(|| "-".into()),
            s.inaccuracy.unwrap_or(0.0),
        );
    }
    println!(
        "\n{} shots total{}",
        shots.len(),
        if display_limit < shots.len() {
            format!(" (showing first {display_limit})")
        } else {
            String::new()
        }
    );
    Ok(())
}

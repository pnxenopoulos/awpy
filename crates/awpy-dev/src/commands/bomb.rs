use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let bomb = parser.bomb()?;

    if json {
        println!("{}", serde_json::to_string_pretty(&bomb)?);
        return Ok(());
    }

    println!(
        "{:<8} {:<16} {:<18} {:<8}",
        "Tick".bold(),
        "Event".bold(),
        "Player".bold(),
        "Site".bold(),
    );
    println!("{}", "-".repeat(54));
    for b in &bomb {
        println!(
            "{:<8} {:<16} {:<18} {:<8}",
            b.tick,
            b.event,
            b.name.as_deref().unwrap_or("?"),
            b.bombsite.as_deref().unwrap_or("-"),
        );
    }
    println!("\n{} bomb events", bomb.len());
    Ok(())
}

use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let items = parser.item_events()?;

    let display_limit = limit.unwrap_or(items.len());
    let shown = &items[..display_limit.min(items.len())];

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    println!(
        "{:<8} {:<9} {:<16} {:<14} {}",
        "Tick".bold(),
        "Action".bold(),
        "Player".bold(),
        "Item".bold(),
        "Cost".bold(),
    );
    println!("{}", "-".repeat(60));
    for i in shown {
        println!(
            "{:<8} {:<9} {:<16} {:<14} {}",
            i.tick,
            i.action,
            i.name.as_deref().unwrap_or("?"),
            i.item,
            i.cost
                .map(|c| format!("${c}"))
                .unwrap_or_else(|| "-".into()),
        );
    }
    println!(
        "\n{} item events total{}",
        items.len(),
        if display_limit < items.len() {
            format!(" (showing first {display_limit})")
        } else {
            String::new()
        }
    );
    Ok(())
}

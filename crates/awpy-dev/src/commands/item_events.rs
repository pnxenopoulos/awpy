use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let items = parser.item_events()?;

    let shown = super::limited(&items, limit);

    if json {
        return super::print_json(&shown);
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
    super::print_total("item events", items.len(), shown.len());
    Ok(())
}

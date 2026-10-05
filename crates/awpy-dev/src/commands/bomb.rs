use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let bomb = parser.bomb()?;

    if json {
        return super::print_json(&bomb);
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

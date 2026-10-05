use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let blinds = parser.blinds()?;

    let shown = super::limited(&blinds, limit);

    if json {
        return super::print_json(&shown);
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
    super::print_total("blinds", blinds.len(), shown.len());
    Ok(())
}

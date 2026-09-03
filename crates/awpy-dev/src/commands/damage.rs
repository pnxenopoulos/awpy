use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let damages = parser.damages()?;

    let display_limit = limit.unwrap_or(damages.len());
    let shown = &damages[..display_limit.min(damages.len())];

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    let who = |name: &Option<String>, side: &Option<String>| -> String {
        let n = name.clone().unwrap_or_else(|| "?".into());
        match side.as_deref() {
            Some("terrorist") => n.red().to_string(),
            Some("counter-terrorist") => n.blue().to_string(),
            _ => n,
        }
    };

    println!(
        "{:<8} {:<18} {:<18} {:<14} {:<6} {:<9} {}",
        "Tick".bold(),
        "Attacker".bold(),
        "Victim".bold(),
        "Weapon".bold(),
        "Dmg".bold(),
        "Hitgroup".bold(),
        "HP (pre→post)".bold(),
    );
    println!("{}", "-".repeat(84));

    for d in shown {
        println!(
            "{:<8} {:<18} {:<18} {:<14} {:<6} {:<9} {}→{}",
            d.tick,
            who(&d.attacker_name, &d.attacker_side),
            who(&d.victim_name, &d.victim_side),
            d.weapon,
            d.dmg_health,
            d.hitgroup_name,
            d.health_pre,
            d.health_post,
        );
    }

    println!(
        "\n{} damage events total{}",
        damages.len(),
        if display_limit < damages.len() {
            format!(" (showing first {display_limit})")
        } else {
            String::new()
        }
    );
    Ok(())
}

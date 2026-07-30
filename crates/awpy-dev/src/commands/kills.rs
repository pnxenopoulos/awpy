use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let kills = parser.kills()?;

    let display_limit = limit.unwrap_or(kills.len());
    let shown = &kills[..display_limit.min(kills.len())];

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
        "{:<8} {:<18} {:<18} {:<16} {:<8} {:<12} {}",
        "Tick".bold(),
        "Attacker".bold(),
        "Victim".bold(),
        "Weapon".bold(),
        "Headshot".bold(),
        "Trade".bold(),
        "Hitgroup".bold(),
    );
    println!("{}", "-".repeat(90));

    for k in shown {
        let hs = if k.headshot {
            "yes".yellow().to_string()
        } else {
            "no".to_string()
        };
        // Either flag can be set, including both on the same kill: a trade that
        // is itself traded back.
        let trade = match (k.is_trade, k.victim_traded) {
            (true, true) => "trade,traded".cyan().to_string(),
            (true, false) => "trade".cyan().to_string(),
            (false, true) => "traded".to_string(),
            (false, false) => "-".to_string(),
        };
        println!(
            "{:<8} {:<18} {:<18} {:<16} {:<8} {:<12} {}",
            k.tick,
            who(&k.attacker_name, &k.attacker_side),
            who(&k.victim_name, &k.victim_side),
            k.weapon,
            hs,
            trade,
            k.hitgroup_name,
        );
    }

    println!(
        "\n{} kills total{}",
        kills.len(),
        if display_limit < kills.len() {
            format!(" (showing first {display_limit})")
        } else {
            String::new()
        }
    );
    Ok(())
}

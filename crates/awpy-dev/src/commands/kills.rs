use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let kills = parser.kills()?;

    let shown = super::limited(&kills, limit);

    if json {
        return super::print_json(&shown);
    }

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
            super::player_label(k.attacker_name.as_deref(), k.attacker_side.as_deref()),
            super::player_label(k.victim_name.as_deref(), k.victim_side.as_deref()),
            k.weapon,
            hs,
            trade,
            k.hitgroup_name,
        );
    }

    super::print_total("kills", kills.len(), shown.len());
    Ok(())
}

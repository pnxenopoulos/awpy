use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let damages = parser.damages()?;

    let shown = super::limited(&damages, limit);

    if json {
        return super::print_json(&shown);
    }

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
            super::player_label(d.attacker_name.as_deref(), d.attacker_side.as_deref()),
            super::player_label(d.victim_name.as_deref(), d.victim_side.as_deref()),
            d.weapon,
            d.dmg_health,
            d.hitgroup_name,
            d.health_pre,
            d.health_post,
        );
    }

    super::print_total("damage events", damages.len(), shown.len());
    Ok(())
}

use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
    let shots = parser.shots()?;

    let shown = super::limited(&shots, limit);

    if json {
        return super::print_json(&shown);
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
    super::print_total("shots", shots.len(), shown.len());
    Ok(())
}

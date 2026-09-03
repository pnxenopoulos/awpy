use std::collections::BTreeMap;
use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let grenades = parser.grenades()?;

    if json {
        println!("{}", serde_json::to_string_pretty(&grenades)?);
        return Ok(());
    }

    // Summarize by grenade type (rows are per-tick trajectory samples).
    let mut throws: BTreeMap<&str, std::collections::HashSet<i32>> = BTreeMap::new();
    let mut samples: BTreeMap<&str, usize> = BTreeMap::new();
    for g in &grenades {
        throws
            .entry(&g.grenade_type)
            .or_default()
            .insert(g.entity_id);
        *samples.entry(&g.grenade_type).or_default() += 1;
    }

    println!(
        "{:<12} {:<10} {}",
        "Type".bold(),
        "Throws".bold(),
        "Samples".bold()
    );
    println!("{}", "-".repeat(36));
    for (ty, ids) in &throws {
        println!("{:<12} {:<10} {}", ty, ids.len(), samples[ty]);
    }
    println!(
        "\n{} trajectory samples across {} grenades (use --json for all rows)",
        grenades.len(),
        throws.values().map(|s| s.len()).sum::<usize>()
    );
    Ok(())
}

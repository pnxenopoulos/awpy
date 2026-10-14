use std::collections::HashSet;
use std::path::Path;

use anyhow::Result;
use colored::Colorize;

/// `kind` selects the dataset: "fires" (infernos) or "smokes".
pub fn run(file: &Path, kind: &str, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;

    // Both datasets share the same shape; serialize whichever was requested.
    if kind == "smokes" {
        let smokes = parser.smokes()?;
        if json {
            return super::print_json(&smokes);
        }
        let instances: HashSet<(i32, i32)> =
            smokes.iter().map(|s| (s.entity_id, s.start_tick)).collect();
        summary("smokes", smokes.len(), instances.len());
    } else {
        let fires = parser.fires()?;
        if json {
            return super::print_json(&fires);
        }
        let instances: HashSet<(i32, i32)> =
            fires.iter().map(|f| (f.entity_id, f.start_tick)).collect();
        summary("infernos", fires.len(), instances.len());
    }
    Ok(())
}

fn summary(label: &str, rows: usize, instances: usize) {
    println!("{}", format!("{instances} {label}").green().bold());
    println!("{rows} per-tick samples (use --json for all rows)");
}

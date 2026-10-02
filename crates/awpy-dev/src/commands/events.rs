use std::collections::BTreeMap;
use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

#[allow(clippy::too_many_arguments)]
pub fn run(
    file: &Path,
    name_filter: Option<String>,
    summary: bool,
    tick_filter: Option<i32>,
    min_tick: Option<i32>,
    max_tick: Option<i32>,
    limit: Option<usize>,
    json: bool,
) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let events = parser.events(max_tick)?;

    let matches = |name: &str, tick: i32| -> bool {
        if let Some(ref f) = name_filter
            && !name.to_lowercase().contains(&f.to_lowercase())
        {
            return false;
        }
        if let Some(t) = tick_filter
            && tick != t
        {
            return false;
        }
        if let Some(min) = min_tick
            && tick < min
        {
            return false;
        }
        true
    };

    let filtered: Vec<_> = events.iter().filter(|e| matches(&e.name, e.tick)).collect();

    if summary {
        let mut counts: BTreeMap<&str, usize> = BTreeMap::new();
        for e in &filtered {
            *counts.entry(e.name.as_str()).or_default() += 1;
        }
        if json {
            println!("{}", serde_json::to_string_pretty(&counts)?);
            return Ok(());
        }
        println!("{:<40} {}", "Event".bold(), "Count".bold());
        println!("{}", "-".repeat(52));
        let distinct = counts.len();
        let mut rows: Vec<_> = counts.into_iter().collect();
        rows.sort_by_key(|&(_, n)| std::cmp::Reverse(n));
        for (name, n) in rows {
            println!("{name:<40} {n}");
        }
        println!("\n{} events, {distinct} distinct", filtered.len());
        return Ok(());
    }

    let display_limit = limit.unwrap_or(filtered.len());
    let shown: Vec<_> = filtered.iter().take(display_limit).collect();

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    for e in &shown {
        let keys = if e.keys.is_empty() {
            String::new()
        } else {
            let parts: Vec<String> = e.keys.iter().map(|(k, v)| format!("{k}={v}")).collect();
            format!("  {}", parts.join(", ").dimmed())
        };
        println!(
            "[{:>8}] {}{}",
            e.tick.to_string().cyan(),
            e.name.bold(),
            keys
        );
    }

    println!(
        "\n{} events total{}",
        filtered.len(),
        if display_limit < filtered.len() {
            format!(" (showing first {})", display_limit)
        } else {
            String::new()
        }
    );

    Ok(())
}

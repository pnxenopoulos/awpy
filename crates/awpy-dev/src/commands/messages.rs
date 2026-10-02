use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

#[allow(clippy::too_many_arguments)]
pub fn run(
    file: &Path,
    cmd_filter: Option<String>,
    tick_filter: Option<i32>,
    min_tick: Option<i32>,
    max_tick: Option<i32>,
    limit: Option<usize>,
    json: bool,
) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let messages = parser.messages()?;

    let filtered: Vec<_> = messages
        .iter()
        .filter(|msg| {
            if let Some(ref cmd) = cmd_filter
                && !msg.cmd_name.to_lowercase().contains(&cmd.to_lowercase())
            {
                return false;
            }
            if let Some(tick) = tick_filter
                && msg.tick != tick
            {
                return false;
            }
            if let Some(min) = min_tick
                && msg.tick < min
            {
                return false;
            }
            if let Some(max) = max_tick
                && msg.tick > max
            {
                return false;
            }
            true
        })
        .collect();

    let display_limit = limit.unwrap_or(filtered.len());
    let output: Vec<_> = filtered.iter().take(display_limit).collect();

    if json {
        println!("{}", serde_json::to_string_pretty(&output)?);
        return Ok(());
    }

    println!(
        "{:<6} {:<8} {:<10} {:<8} {:<24}",
        "Index".bold(),
        "Tick".bold(),
        "Compress".bold(),
        "Size".bold(),
        "Command".bold(),
    );
    println!("{}", "-".repeat(60));

    for msg in &output {
        let compressed = if msg.compressed {
            "yes".yellow().to_string()
        } else {
            "no".to_string()
        };
        println!(
            "{:<6} {:<8} {:<10} {:<8} {}",
            msg.index, msg.tick, compressed, msg.body_size, msg.cmd_name,
        );
    }

    println!(
        "\n{} messages total{}{}",
        messages.len(),
        if filtered.len() != messages.len() {
            format!(" ({} matched filters)", filtered.len())
        } else {
            String::new()
        },
        if display_limit < filtered.len() {
            format!(" (showing first {})", display_limit)
        } else {
            String::new()
        }
    );

    Ok(())
}

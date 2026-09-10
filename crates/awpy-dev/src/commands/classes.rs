use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(file: &Path, filter: Option<String>, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let class_info = parser.parse_class_info()?;

    let mut classes: Vec<_> = class_info
        .classes()
        .iter()
        .filter(|c| {
            filter
                .as_ref()
                .map(|f| c.network_name.to_lowercase().contains(&f.to_lowercase()))
                .unwrap_or(true)
        })
        .collect();
    classes.sort_by_key(|c| c.class_id);

    let display_limit = limit.unwrap_or(classes.len());
    let shown: Vec<_> = classes.iter().take(display_limit).collect();

    if json {
        println!("{}", serde_json::to_string_pretty(&shown)?);
        return Ok(());
    }

    println!(
        "{:<8} {:<40} {}",
        "ID".bold(),
        "Network Name".bold(),
        "Table".bold()
    );
    println!("{}", "-".repeat(72));
    for c in &shown {
        println!("{:<8} {:<40} {}", c.class_id, c.network_name, c.table_name);
    }
    println!(
        "\n{} classes ({} bits per class id)",
        class_info.classes().len(),
        class_info.bits()
    );

    Ok(())
}

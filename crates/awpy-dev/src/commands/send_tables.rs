use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(
    file: &Path,
    filter: Option<String>,
    summary: bool,
    limit: Option<usize>,
    _json: bool,
) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let serializers = parser.parse_send_tables()?;

    let mut names: Vec<&str> = serializers
        .iter()
        .map(|(name, _)| name)
        .filter(|n| {
            filter
                .as_ref()
                .map(|f| n.to_lowercase().contains(&f.to_lowercase()))
                .unwrap_or(true)
        })
        .filter(|n| !n.is_empty())
        .collect();
    names.sort();

    let display_limit = limit.unwrap_or(names.len());

    for name in names.iter().take(display_limit) {
        let ser = serializers.get(name).unwrap();
        if summary {
            println!("{:<48} {} fields", name.bold(), ser.fields.len());
            continue;
        }
        println!("{} ({} fields)", name.green().bold(), ser.fields.len());
        for (i, f) in ser.fields.iter().enumerate() {
            println!("  [{i:>3}] {:<40} {}", f.var_name, f.var_type.dimmed());
        }
        println!();
    }

    println!("{} serializers total", names.len());
    Ok(())
}

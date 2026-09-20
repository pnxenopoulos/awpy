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

    let filter = filter.as_deref().map(str::to_lowercase);
    let mut selected: Vec<_> = serializers
        .iter()
        .filter(|(name, _)| !name.is_empty())
        .filter(|(name, _)| {
            filter
                .as_ref()
                .is_none_or(|filter| name.to_lowercase().contains(filter))
        })
        .collect();
    selected.sort_by_key(|(name, _)| *name);

    let display_limit = limit.unwrap_or(selected.len());

    for (name, ser) in selected.iter().take(display_limit) {
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

    println!("{} serializers total", selected.len());
    Ok(())
}

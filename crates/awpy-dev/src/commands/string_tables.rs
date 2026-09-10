use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

pub fn run(
    file: &Path,
    table_filter: Option<String>,
    limit: Option<usize>,
    _json: bool,
) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let ctx = parser.parse_init()?;

    let tables: Vec<_> = ctx
        .string_tables()
        .tables()
        .iter()
        .filter(|t| {
            table_filter
                .as_ref()
                .map(|f| t.name().to_lowercase().contains(&f.to_lowercase()))
                .unwrap_or(true)
        })
        .collect();

    for table in &tables {
        println!(
            "{} ({} entries)",
            table.name().green().bold(),
            table.entries().len()
        );

        // Only enumerate entries when a specific table was requested, to avoid
        // dumping the huge instancebaseline table by default.
        if table_filter.is_some() {
            let display_limit = limit.unwrap_or(table.entries().len());
            for (i, entry) in table.entries().iter().take(display_limit).enumerate() {
                let key = entry.string.as_deref().unwrap_or("<none>");
                let data_len = entry.user_data.as_ref().map(|d| d.len()).unwrap_or(0);
                println!("  [{i:>4}] {key:<40} ({data_len} bytes user data)");
            }
        }
    }

    println!(
        "\n{} string tables total",
        ctx.string_tables().tables().len()
    );
    Ok(())
}

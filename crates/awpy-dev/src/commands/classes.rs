use std::path::Path;

use anyhow::Result;
use colored::Colorize;

pub fn run(file: &Path, filter: Option<String>, limit: Option<usize>, json: bool) -> Result<()> {
    let parser = super::open_demo(file)?;
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

    let shown = super::limited(&classes, limit);

    if json {
        return super::print_json(&shown);
    }

    println!(
        "{:<8} {:<40} {}",
        "ID".bold(),
        "Network Name".bold(),
        "Table".bold()
    );
    println!("{}", "-".repeat(72));
    for c in shown {
        println!("{:<8} {:<40} {}", c.class_id, c.network_name, c.table_name);
    }
    println!(
        "\n{} classes ({} bits per class id)",
        class_info.classes().len(),
        class_info.bits()
    );

    Ok(())
}

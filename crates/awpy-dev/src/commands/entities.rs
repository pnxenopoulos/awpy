use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;

/// Snapshot entities at a given tick and list those matching a class filter.
pub fn run(
    file: &Path,
    tick: i32,
    class_filter: Option<String>,
    limit: Option<usize>,
    show_fields: bool,
    _json: bool,
) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;
    let ctx = parser.parse_to_tick(tick)?;

    let mut entities: Vec<_> = ctx
        .entities
        .iter()
        .map(|(_, e)| e)
        .filter(|e| e.active)
        .filter(|e| {
            class_filter
                .as_ref()
                .map(|f| e.class_name.to_lowercase().contains(&f.to_lowercase()))
                .unwrap_or(true)
        })
        .collect();
    entities.sort_by_key(|e| e.index);

    let display_limit = limit.unwrap_or(entities.len());

    println!(
        "{} active entities at tick {} (of {} total){}",
        entities.len().to_string().cyan(),
        ctx.tick,
        ctx.entities.len(),
        if let Some(ref f) = class_filter {
            format!(" matching '{f}'")
        } else {
            String::new()
        }
    );
    println!("{}", "-".repeat(60));

    for e in entities.iter().take(display_limit) {
        println!(
            "  #{:<5} {} {}",
            e.index,
            e.class_name.bold(),
            format!("({} fields)", e.fields.len()).dimmed()
        );
        if show_fields && let Some(serializer) = ctx.serializers.get(&e.class_name) {
            let mut shown = 0;
            for field in &serializer.fields {
                if let Some(key) = serializer.resolve_field_key(&field.var_name)
                    && let Some(value) = e.fields.get(&key)
                {
                    println!("      {:<32} = {:?}", field.var_name, value);
                    shown += 1;
                    if shown >= 24 {
                        println!("      ...");
                        break;
                    }
                }
            }
        }
    }

    Ok(())
}

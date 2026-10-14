//! CLI command implementations.

mod blinds;
mod bomb;
mod classes;
mod damage;
mod entities;
mod events;
mod fires;
mod grenades;
mod info;
mod item_events;
mod kills;
mod messages;
mod rounds;
mod send_tables;
mod shots;
mod stats;
mod string_tables;
mod verify;

pub use blinds::run as blinds;
pub use bomb::run as bomb;
pub use classes::run as classes;
pub use damage::run as damage;
pub use entities::run as entities;
pub use events::run as events;
pub use fires::run as fires;
pub use grenades::run as grenades;
pub use info::run as info;
pub use item_events::run as item_events;
pub use kills::run as kills;
pub use messages::run as messages;
pub use rounds::run as rounds;
pub use send_tables::run as send_tables;
pub use shots::run as shots;
pub use stats::run as stats;
pub use string_tables::run as string_tables;
pub use verify::run as verify;

fn open_demo(file: &std::path::Path) -> anyhow::Result<awpy::Parser> {
    use anyhow::Context;

    awpy::Parser::from_file(file).with_context(|| format!("failed to open {}", file.display()))
}

fn print_json(value: &(impl serde::Serialize + ?Sized)) -> anyhow::Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

fn limited<T>(rows: &[T], limit: Option<usize>) -> &[T] {
    &rows[..limit.unwrap_or(rows.len()).min(rows.len())]
}

fn print_total(label: &str, total: usize, shown: usize) {
    print!("\n{total} {label} total");
    if shown < total {
        print!(" (showing first {shown})");
    }
    println!();
}

fn player_label(name: Option<&str>, side: Option<&str>) -> String {
    use colored::Colorize;

    let name = name.unwrap_or("?");
    match side {
        Some("terrorist") => name.red().to_string(),
        Some("counter-terrorist") => name.blue().to_string(),
        _ => name.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::limited;

    #[test]
    fn limits_preserve_order_and_stay_within_rows() {
        let rows = [1, 2, 3];
        for (limit, expected) in [
            (None, &rows[..]),
            (Some(0), &rows[..0]),
            (Some(2), &rows[..2]),
            (Some(3), &rows[..]),
            (Some(usize::MAX), &rows[..]),
        ] {
            assert_eq!(limited(&rows, limit), expected);
            assert!(limited::<u8>(&[], limit).is_empty());
        }
    }
}

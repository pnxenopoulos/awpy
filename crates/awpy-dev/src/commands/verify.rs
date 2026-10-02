use std::path::Path;

use anyhow::Result;
use colored::Colorize;
use serde::Serialize;

#[derive(Serialize)]
struct VerifyOutput {
    valid: bool,
    file: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

pub fn run(file: &Path, json: bool) -> Result<()> {
    let result = awpy::Parser::from_file(file).and_then(|p| p.verify());

    match result {
        Ok(_) => {
            if json {
                let output = VerifyOutput {
                    valid: true,
                    file: file.display().to_string(),
                    error: None,
                };
                println!("{}", serde_json::to_string_pretty(&output)?);
            } else {
                println!("{} {}", "Valid demo file:".green().bold(), file.display());
            }
            Ok(())
        }
        Err(e) => {
            if json {
                let output = VerifyOutput {
                    valid: false,
                    file: file.display().to_string(),
                    error: Some(e.to_string()),
                };
                println!("{}", serde_json::to_string_pretty(&output)?);
                Err(e.into())
            } else {
                eprintln!("{} {}", "Invalid demo file:".red().bold(), file.display());
                eprintln!("  {}", e.to_string().red());
                Err(e.into())
            }
        }
    }
}

use std::path::Path;

use anyhow::{Context, Result};
use colored::Colorize;
use serde::Serialize;

#[derive(Serialize)]
struct InfoOutput {
    header: awpy_proto::proto::CDemoFileHeader,
    #[serde(skip_serializing_if = "Option::is_none")]
    info: Option<awpy_proto::proto::CDemoFileInfo>,
}

pub fn run(file: &Path, json: bool) -> Result<()> {
    let parser = awpy::Parser::from_file(file)
        .with_context(|| format!("failed to open {}", file.display()))?;

    let header = parser.file_header()?;

    if json {
        let info = parser.file_info().ok();
        let output = InfoOutput { header, info };
        println!("{}", serde_json::to_string_pretty(&output)?);
        return Ok(());
    }

    println!("{}", "File Header".green().bold());
    println!("  demo_file_stamp:  {}", header.demo_file_stamp);
    if let Some(ref v) = header.map_name {
        println!("  map_name:         {}", v);
    }
    if let Some(ref v) = header.server_name {
        println!("  server_name:      {}", v);
    }
    if let Some(ref v) = header.client_name {
        println!("  client_name:      {}", v);
    }
    if let Some(v) = header.build_num {
        println!("  build_num:        {}", v);
    }
    if let Some(ref v) = header.game_directory {
        println!("  game_directory:   {}", v);
    }
    if let Some(ref v) = header.demo_version_name {
        println!("  demo_version:     {}", v);
    }
    if let Some(v) = header.server_start_tick {
        println!("  server_start:     {}", v);
    }

    println!();
    match parser.file_info() {
        Ok(info) => {
            println!("{}", "File Info".green().bold());
            if let Some(v) = info.playback_time {
                let minutes = v as u32 / 60;
                let seconds = v as u32 % 60;
                println!("  playback_time:    {:.1}s ({}:{:02})", v, minutes, seconds);
            }
            if let Some(v) = info.playback_ticks {
                println!("  playback_ticks:   {}", v);
            }
            if let Some(v) = info.playback_frames {
                println!("  playback_frames:  {}", v);
            }
        }
        Err(e) => {
            println!("{}: {}", "File Info".yellow().bold(), e);
        }
    }

    Ok(())
}

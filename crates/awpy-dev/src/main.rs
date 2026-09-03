use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};

use awpy_dev::commands;

#[derive(Parser)]
#[command(
    name = "awpy-dev",
    about = "Awpy developer CLI — inspect CS2 demo files and parser internals \
             (the user-facing `awpy` command ships with the Python package)",
    version
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
    /// Output results as JSON
    #[arg(long, global = true)]
    json: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Verify a demo file's magic bytes and header
    Verify {
        /// Path to the demo file
        file: PathBuf,
    },
    /// Print the file header and file info
    Info {
        /// Path to the demo file
        file: PathBuf,
    },
    /// List all demo messages with metadata
    Messages {
        /// Path to the demo file
        file: PathBuf,
        /// Filter by command type (substring match)
        #[arg(long, value_name = "TYPE")]
        cmd: Option<String>,
        /// Filter by exact tick
        #[arg(long)]
        tick: Option<i32>,
        /// Filter by minimum tick
        #[arg(long, value_name = "TICK")]
        min_tick: Option<i32>,
        /// Filter by maximum tick
        #[arg(long, value_name = "TICK")]
        max_tick: Option<i32>,
        /// Maximum number of messages to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// List game events (player_death, round_end, weapon_fire, …)
    Events {
        /// Path to the demo file
        file: PathBuf,
        /// Filter events by name substring
        #[arg(long)]
        filter: Option<String>,
        /// Show per-event-name counts instead of individual events
        #[arg(long)]
        summary: bool,
        /// Filter by exact tick
        #[arg(long)]
        tick: Option<i32>,
        /// Filter by minimum tick
        #[arg(long, value_name = "TICK")]
        min_tick: Option<i32>,
        /// Stop parsing after this tick
        #[arg(long, value_name = "TICK")]
        max_tick: Option<i32>,
        /// Maximum number of events to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Reconstruct per-round info (start/freeze-end/end ticks, winner, reason)
    Rounds {
        /// Path to the demo file
        file: PathBuf,
    },
    /// List kills (from `player_death` events) with all fields
    Kills {
        /// Path to the demo file
        file: PathBuf,
        /// Maximum number of kills to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// List damage instances (from `player_hurt` events) with all fields
    Damage {
        /// Path to the demo file
        file: PathBuf,
        /// Maximum number of damage events to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// List bomb actions (pickup / drop / plant / defuse)
    Bomb {
        /// Path to the demo file
        file: PathBuf,
    },
    /// Summarize thrown-grenade trajectories (use --json for all rows)
    Grenades {
        /// Path to the demo file
        file: PathBuf,
    },
    /// Summarize burning infernos (use --json for all rows)
    Fires {
        /// Path to the demo file
        file: PathBuf,
    },
    /// Summarize deployed smoke clouds (use --json for all rows)
    Smokes {
        /// Path to the demo file
        file: PathBuf,
    },
    /// List flash events (who was blinded, by whom, and for how long)
    Blinds {
        /// Path to the demo file
        file: PathBuf,
        /// Maximum number of blinds to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// List weapon-item transactions (purchases, pickups, and drops)
    ItemEvents {
        /// Path to the demo file
        file: PathBuf,
        /// Maximum number of item events to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// List shots fired (from `weapon_fire` events) with shooter/weapon state
    Shots {
        /// Path to the demo file
        file: PathBuf,
        /// Maximum number of shots to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Per-player stats (kills, KAST, ADR, openings, trades, ...)
    Stats {
        /// Path to the demo file
        file: PathBuf,
    },
    /// Display entity class info (network name ↔ class id)
    Classes {
        /// Path to the demo file
        file: PathBuf,
        /// Filter classes by name substring
        #[arg(long)]
        filter: Option<String>,
        /// Maximum number of classes to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Display flattened serializers (entity field definitions)
    SendTables {
        /// Path to the demo file
        file: PathBuf,
        /// Filter serializers by name substring
        #[arg(long)]
        filter: Option<String>,
        /// Show only names and field counts
        #[arg(long)]
        summary: bool,
        /// Maximum number of serializers to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Display string tables
    StringTables {
        /// Path to the demo file
        file: PathBuf,
        /// Show entries of the named table (substring match)
        #[arg(long)]
        table: Option<String>,
        /// Maximum number of entries to display
        #[arg(long)]
        limit: Option<usize>,
    },
    /// Snapshot entities at a tick and list them by class
    Entities {
        /// Path to the demo file
        file: PathBuf,
        /// Tick to snapshot the game state at
        #[arg(long, default_value_t = 100000)]
        tick: i32,
        /// Filter entities by class name substring
        #[arg(long)]
        class: Option<String>,
        /// Maximum number of entities to display
        #[arg(long)]
        limit: Option<usize>,
        /// Also print each entity's decoded field values
        #[arg(long)]
        fields: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let json = cli.json;

    match cli.command {
        Commands::Verify { file } => commands::verify(&file, json),
        Commands::Info { file } => commands::info(&file, json),
        Commands::Messages {
            file,
            cmd,
            tick,
            min_tick,
            max_tick,
            limit,
        } => commands::messages(&file, cmd, tick, min_tick, max_tick, limit, json),
        Commands::Events {
            file,
            filter,
            summary,
            tick,
            min_tick,
            max_tick,
            limit,
        } => commands::events(
            &file, filter, summary, tick, min_tick, max_tick, limit, json,
        ),
        Commands::Rounds { file } => commands::rounds(&file, json),
        Commands::Kills { file, limit } => commands::kills(&file, limit, json),
        Commands::Damage { file, limit } => commands::damage(&file, limit, json),
        Commands::Bomb { file } => commands::bomb(&file, json),
        Commands::Grenades { file } => commands::grenades(&file, json),
        Commands::Fires { file } => commands::fires(&file, "fires", json),
        Commands::Smokes { file } => commands::fires(&file, "smokes", json),
        Commands::Blinds { file, limit } => commands::blinds(&file, limit, json),
        Commands::ItemEvents { file, limit } => commands::item_events(&file, limit, json),
        Commands::Shots { file, limit } => commands::shots(&file, limit, json),
        Commands::Stats { file } => commands::stats(&file, json),
        Commands::Classes {
            file,
            filter,
            limit,
        } => commands::classes(&file, filter, limit, json),
        Commands::SendTables {
            file,
            filter,
            summary,
            limit,
        } => commands::send_tables(&file, filter, summary, limit, json),
        Commands::StringTables { file, table, limit } => {
            commands::string_tables(&file, table, limit, json)
        }
        Commands::Entities {
            file,
            tick,
            class,
            limit,
            fields,
        } => commands::entities(&file, tick, class, limit, fields, json),
    }
}

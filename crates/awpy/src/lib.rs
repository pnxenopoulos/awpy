//! Awpy - A Counter-Strike 2 demo file parser
//!
//! This crate provides functionality for parsing Counter-Strike 2 demo files
//! (`.dem`), extracting game state, entity information, game events, and
//! metadata. CS2 uses the Source 2 engine, so the demo container (`PBDEMS2`),
//! bit-level encodings, flattened serializers, entity system, and string
//! tables are all shared with other Source 2 titles.
//!
//! # Quick start
//!
//! ```no_run
//! use std::path::Path;
//! use awpy::Parser;
//!
//! let parser = Parser::from_file(Path::new("match.dem")).unwrap();
//! let header = parser.file_header().unwrap();
//! println!("Map: {:?}", header.map_name);
//! ```
//!
//! # Reading game events
//!
//! ```no_run
//! use std::path::Path;
//! use awpy::Parser;
//!
//! let parser = Parser::from_file(Path::new("match.dem")).unwrap();
//! let events = parser.events(None).unwrap();
//! for event in &events {
//!     println!("[tick {}] {} (msg_type {})", event.tick, event.name, event.msg_type);
//! }
//! ```
//!
//! # Iterating entities per tick
//!
//! ```no_run
//! use std::path::Path;
//! use awpy::Parser;
//!
//! let parser = Parser::from_file(Path::new("match.dem")).unwrap();
//! parser.run_to_end(|ctx| {
//!     for (idx, entity) in ctx.entities.iter() {
//!         if entity.class_name == "CCSPlayerPawn" {
//!             let _ = idx; // slot index; access entity fields by resolved key
//!         }
//!     }
//! }).unwrap();
//! ```
//!
//! # Name lookups
//!
//! ```
//! // Resolve numeric IDs to human-readable names
//! assert_eq!(awpy::team_name(2), "terrorist");
//! assert_eq!(awpy::team_name(3), "counter-terrorist");
//! assert_eq!(awpy::hitgroup_name(1), "head");
//! assert_eq!(awpy::round_end_reason_name(7), "bomb_defused");
//! assert_eq!(awpy::game_phase_name(1), "pregame");
//! ```

pub mod datasets;
pub mod demo;
pub mod entity;
pub mod error;
pub mod game_phases;
pub mod geometry;
pub mod hitgroups;
pub mod io;
pub mod map_control;
pub mod nav;
pub mod position;
pub mod round_end_reasons;
pub mod stats;
pub mod teams;
pub mod weapons;

// Re-export commonly used types at the crate root for convenience
pub use datasets::{
    Blind, BombEvent, ChatMessage, Damage, Fire, Grenade, ItemEvent, Kill, Player, PlayerState,
    Round, RoundEconomy, Shot, Smoke,
};
pub use demo::{
    CmdHeader, Context, GameEvent, MessageInfo, Parser, command_name, decode_event_payload,
    user_message_name,
};
pub use entity::{
    ClassEntry, ClassInfo, ENTITY_HANDLE_INDEX_MASK, Entity, EntityContainer, FieldValue,
    INVALID_ENTITY_HANDLE, Serializer, SerializerContainer, SerializerField, StringTable,
    StringTableContainer, StringTableEntry, protobuf_handle_index,
};
pub use error::{Error, Result};
pub use game_phases::{all_game_phases, game_phase_name};
pub use geometry::{Mesh, VisibilityMesh};
pub use hitgroups::{all_hitgroups, hitgroup_name};
pub use map_control::{
    AreaControl, Control, MapControl, Observer, Occluder, Params as MapControlParams, Team,
    raycast_control, reachability_control, vision_control,
};
pub use nav::{Nav, NavArea, PathWeight};
pub use position::{CELL_BITS, CELL_SIZE, WORLD_HALF, cell_to_world};
pub use round_end_reasons::{all_round_end_reasons, round_end_reason_name};
pub use stats::PlayerStats;
pub use teams::{all_teams, team_name};
pub use weapons::{WeaponInfo, WeaponSlot, weapon_info};

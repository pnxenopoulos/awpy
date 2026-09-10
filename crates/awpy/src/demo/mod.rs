//! Demo file parsing and command handling.
//!
//! This module provides the main [`Parser`] for reading Counter-Strike 2 demo
//! files, along with command type definitions and header structures.

mod adapter;
mod command;
pub mod decode;
mod parser;

pub use command::{CmdHeader, EDemoCommands, SvcMessages, command_name, user_message_name};
pub use decode::decode_event_payload;
pub use parser::{Context, GameEvent, MessageInfo, Parser};

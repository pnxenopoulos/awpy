//! I/O utilities for reading demo file data.
//!
//! This module provides low-level readers for both bit-level and byte-level
//! access to demo file data.

mod bitreader;
mod reader;

pub use bitreader::BitReader;
pub use reader::ByteReader;

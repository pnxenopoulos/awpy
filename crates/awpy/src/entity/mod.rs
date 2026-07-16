//! Entity system for parsing and representing game state.
//!
//! This module handles everything related to entities in the demo:
//! - Entity lifecycle (create, update, delete)
//! - Serializers and field definitions
//! - Class information
//! - Field value decoding
//! - String tables

mod class_info;
mod entities;
mod field_decoder;
pub(crate) mod field_path;
mod field_value;
mod quantized_float;
mod serializers;
mod string_tables;

pub use class_info::{ClassEntry, ClassInfo};
pub use entities::{
    ENTITY_HANDLE_INDEX_MASK, Entity, EntityContainer, INVALID_ENTITY_HANDLE, protobuf_handle_index,
};
pub use field_decoder::{FieldDecodeContext, FieldMetadata};
pub use field_value::FieldValue;
pub use serializers::{Serializer, SerializerContainer, SerializerField};
pub use string_tables::{StringTable, StringTableContainer, StringTableEntry};

use std::collections::HashSet;

use rustc_hash::FxHashMap;

use crate::error::{Error, Result};
use crate::io::BitReader;

use super::class_info::ClassInfo;
use super::field_decoder::FieldDecodeContext;
use super::field_path::{self, FieldPath};
use super::field_value::FieldValue;
use super::serializers::{Serializer, SerializerContainer, SerializerField};
use super::string_tables::StringTableContainer;

use awpy_proto::proto::CsvcMsgPacketEntities;

// Serial-number layout for the entity *create* delta (legacy Source CBaseHandle):
// a create carries a 15-bit entity entry (`MAX_EDICT_BITS + 1`) followed by a
// 17-bit serial number. This governs only the serial read in `handle_create`; it
// is NOT the layout of a networked CHandle *field value*, whose entity index is
// the low 14 bits — see [`ENTITY_HANDLE_INDEX_MASK`] / [`EntityContainer::get_by_handle`].
const MAX_EDICT_BITS: u32 = 14;
const NUM_ENT_ENTRY_BITS: u32 = MAX_EDICT_BITS + 1;
const NUM_SERIAL_NUM_BITS: u32 = 32 - NUM_ENT_ENTRY_BITS;

/// Mask that extracts the entity-array index from a networked `CHandle` value.
///
/// Source 2 packs a 14-bit edict index (entity indices run 0–16383) in the low
/// bits of a handle with a serial number above it, so the index is recovered
/// with this 14-bit mask. A wider mask (e.g. `0x7FFF`) leaks a serial bit into
/// the index and resolves the wrong entity for any handle with an odd serial.
pub const ENTITY_HANDLE_INDEX_MASK: u32 = 0x3FFF;

/// Sentinel value for a `CHandle` field that points at no entity.
///
/// Protobuf handle fields (e.g. `modifier.parent`) are optional; callers
/// substitute this when the field is absent and skip handles equal to it.
pub const INVALID_ENTITY_HANDLE: u32 = 0x00FF_FFFF;

/// Resolve a protobuf-style optional `CHandle` to an entity-array index.
///
/// Returns `None` when the handle is absent (the protobuf field was not set)
/// or holds the [`INVALID_ENTITY_HANDLE`] sentinel; otherwise applies
/// [`ENTITY_HANDLE_INDEX_MASK`] and returns the entity-array index. Use this
/// for `Option<u32>` `CHandle` fields on user messages (e.g. a death message's
/// `attacker` / `victim`); it pairs naturally with `let-else`:
///
/// ```ignore
/// let Some(attacker_idx) = awpy::protobuf_handle_index(msg.attacker) else { continue };
/// ```
pub fn protobuf_handle_index(handle: Option<u32>) -> Option<i32> {
    handle
        .filter(|&h| h != INVALID_ENTITY_HANDLE)
        .map(|h| (h & ENTITY_HANDLE_INDEX_MASK) as i32)
}

/// Walk a serializer hierarchy along a field path to the addressed field.
///
/// Returns a [`Error::Parse`] rather than panicking when any component indexes
/// past its serializer's fields — which is the tell-tale symptom of a bitstream
/// desync (a corrupted field path addresses a nonexistent field), so surfacing
/// it as an error keeps a bad decode from taking down the whole parse.
fn resolve_field_path<'a>(
    serializer: &'a Serializer,
    fp: &FieldPath,
) -> Result<&'a SerializerField> {
    let oob = || Error::Parse {
        context: format!(
            "field path out of range for serializer '{}' ({} fields)",
            serializer.name,
            serializer.fields.len()
        ),
    };

    let mut field = serializer.fields.get(fp.get(0)).ok_or_else(oob)?;
    for i in 1..=fp.last {
        let idx = fp.get(i);
        if field.is_dynamic_array() {
            match field.field_serializer.as_ref() {
                Some(fs) => field = fs.fields.first().ok_or_else(oob)?,
                None => break,
            }
        } else if let Some(fs) = field.field_serializer.as_ref() {
            field = fs.fields.get(idx).ok_or_else(oob)?;
        } else {
            break;
        }
    }
    Ok(field)
}

// Each entity in a packet carries a 2-bit delta command. Rather than four
// opaque codes, Source 2 encodes it as two independent flags:
//
//   bit 0 (`CMD_LEAVE`)          0 → the entity is created or updated
//                                1 → the entity leaves the client's PVS
//   bit 1 (`CMD_CREATE_DELETE`)  on the create/update side: create (vs update)
//                                on the leave side:          delete (vs leave)
//
// So `0b10` = create, `0b00` = update, `0b01` = leave (keep, mark inactive),
// `0b11` = leave + delete (remove). Crucially, a plain leave (`0b01`) does NOT
// remove the entity — it merely goes dormant and can be re-activated by a later
// update, which is why entities must not be dropped on leave.
const CMD_LEAVE: u8 = 0x01;
const CMD_CREATE_DELETE: u8 = 0x02;

/// A single entity with its class, fields, and current state.
#[derive(Debug, Clone)]
pub struct Entity {
    /// Slot index in the entity array (0–16383).
    pub index: i32,
    /// Serial number for this slot (increments on reuse).
    pub serial: u32,
    /// Numeric class ID (indexes into [`ClassInfo`]).
    pub class_id: i32,
    /// Network class name (e.g. `"CCSPlayerController"`).
    pub class_name: String,
    /// Whether the entity is currently in the client's PVS.
    ///
    /// An entity that leaves the PVS (delta command `0b01`) is kept in the
    /// container but marked inactive rather than removed; a later update
    /// re-activates it. Consumers iterating [`EntityContainer`] that only want
    /// live entities should skip those with `active == false`.
    pub active: bool,
    /// Current field values, keyed by packed field path keys.
    pub fields: FxHashMap<u64, FieldValue>,
}

impl Entity {
    fn new(index: i32, class_id: i32, class_name: String) -> Self {
        Self {
            index,
            serial: 0,
            class_id,
            class_name,
            active: true,
            fields: FxHashMap::default(),
        }
    }

    /// Apply field path deltas from a bit reader using the given serializer.
    #[allow(clippy::needless_range_loop)]
    fn apply_update(
        &mut self,
        br: &mut BitReader,
        serializer: &Serializer,
        ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        field_path::read_field_paths(br, fp_buf)?;

        for fp_idx in 0..fp_buf.len() {
            let field = resolve_field_path(serializer, &fp_buf[fp_idx])?;

            let key = fp_buf[fp_idx].pack();
            let value = field
                .metadata
                .decoder
                .decode(ctx, br)
                .map_err(|e| Error::Parse {
                    context: format!(
                        "field #{} key={:#x} (type: {}, decoder: {:?}, pos: {}, remaining: {}): {}",
                        fp_idx,
                        key,
                        field.var_type,
                        field.metadata.decoder,
                        br.position(),
                        br.bits_remaining(),
                        e
                    ),
                })?;
            self.fields.insert(key, value);
        }

        Ok(())
    }

    /// Skip field updates - reads the data to advance the bit reader but doesn't store anything.
    /// This avoids allocations and FxHashMap insertions for entities we don't care about.
    #[allow(clippy::needless_range_loop)]
    fn skip_update(
        br: &mut BitReader,
        serializer: &Serializer,
        ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        field_path::read_field_paths(br, fp_buf)?;

        for fp_idx in 0..fp_buf.len() {
            let field = resolve_field_path(serializer, &fp_buf[fp_idx])?;
            // Skip the value - just advances the bit reader without decoding
            field.metadata.decoder.skip(ctx, br)?;
        }

        Ok(())
    }

    // ── Typed field accessors ──
    //
    // Each takes a field key pre-resolved with [`Serializer::resolve_field_key`]
    // (so it can be resolved once and reused across ticks) and reads the field
    // leniently: a missing key, an absent field, or a value of a different type
    // all yield the type's default rather than an error. Integer variants accept
    // any of the four integer encodings, since the network type is not always
    // known ahead of time.

    /// Read a field as `i64`, returning `0` when absent or non-integer.
    pub fn get_i64(&self, key: Option<u64>) -> i64 {
        key.and_then(|k| self.fields.get(&k))
            .and_then(|v| match v {
                FieldValue::U32(n) => Some(*n as i64),
                FieldValue::U64(n) => Some(*n as i64),
                FieldValue::I32(n) => Some(*n as i64),
                FieldValue::I64(n) => Some(*n),
                _ => None,
            })
            .unwrap_or(0)
    }

    /// Read a field as `u32`, returning `0` when absent or non-integer.
    pub fn get_u32(&self, key: Option<u64>) -> u32 {
        key.and_then(|k| self.fields.get(&k))
            .and_then(|v| match v {
                FieldValue::U32(n) => Some(*n),
                FieldValue::U64(n) => Some(*n as u32),
                FieldValue::I32(n) => Some(*n as u32),
                FieldValue::I64(n) => Some(*n as u32),
                _ => None,
            })
            .unwrap_or(0)
    }

    /// Read a field as `f32`, returning `0.0` when absent or non-float.
    pub fn get_f32(&self, key: Option<u64>) -> f32 {
        key.and_then(|k| self.fields.get(&k))
            .and_then(|v| match v {
                FieldValue::F32(f) => Some(*f),
                _ => None,
            })
            .unwrap_or(0.0)
    }

    /// Read a field as `bool`, returning `false` when absent or non-bool.
    pub fn get_bool(&self, key: Option<u64>) -> bool {
        key.and_then(|k| self.fields.get(&k))
            .and_then(|v| match v {
                FieldValue::Bool(b) => Some(*b),
                _ => None,
            })
            .unwrap_or(false)
    }

    /// Read a field as a `QAngle`, returning `[0.0; 3]` when absent or non-angle.
    pub fn get_qangle(&self, key: Option<u64>) -> [f32; 3] {
        key.and_then(|k| self.fields.get(&k))
            .and_then(|v| match v {
                FieldValue::QAngle(a) => Some(*a),
                _ => None,
            })
            .unwrap_or([0.0; 3])
    }

    /// Combine cell + in-cell offset fields into a world-coordinate `[x, y, z]`.
    ///
    /// Source 2 splits each axis of an entity's position across two networked
    /// fields — an integer cell index (e.g. `m_cellX`) and a quantized offset
    /// inside that cell (e.g. `m_vecOrigin.m_vecX`). Pass the resolved keys
    /// for both halves and this returns the full world position in Hammer
    /// units via [`cell_to_world`](crate::position::cell_to_world). Reading
    /// the offset alone gives a sawtooth that resets every cell boundary, not
    /// a usable coordinate.
    ///
    /// Cell keys with no resolved field decode as cell `0`, which means the
    /// result is shifted into a single cell-grid quadrant rather than
    /// returning a sentinel — verify the keys before relying on it.
    pub fn world_position(
        &self,
        cell_keys: [Option<u64>; 3],
        offset_keys: [Option<u64>; 3],
    ) -> [f32; 3] {
        let cell = [
            self.get_i64(cell_keys[0]) as i32,
            self.get_i64(cell_keys[1]) as i32,
            self.get_i64(cell_keys[2]) as i32,
        ];
        let offset = [
            self.get_f32(offset_keys[0]),
            self.get_f32(offset_keys[1]),
            self.get_f32(offset_keys[2]),
        ];
        [
            crate::position::cell_to_world(cell[0], offset[0]),
            crate::position::cell_to_world(cell[1], offset[1]),
            crate::position::cell_to_world(cell[2], offset[2]),
        ]
    }

    /// Read a raw `CHandle` field as `u32`, if present.
    ///
    /// Pass the result to [`EntityContainer::get_by_handle`] to follow the handle
    /// to its entity; that helper owns the index mask so callers never decode it
    /// by hand.
    pub fn get_handle(&self, key: Option<u64>) -> Option<u32> {
        key.and_then(|k| self.fields.get(&k)).and_then(|v| match v {
            FieldValue::U32(n) => Some(*n),
            FieldValue::U64(n) => Some(*n as u32),
            FieldValue::I32(n) => Some(*n as u32),
            FieldValue::I64(n) => Some(*n as u32),
            _ => None,
        })
    }

    /// Read a `u64`-ish field regardless of the concrete integer variant, or
    /// `None` when the field is absent or not an integer.
    pub fn get_u64(&self, key: Option<u64>) -> Option<u64> {
        key.and_then(|k| self.fields.get(&k)).and_then(|v| match v {
            FieldValue::U64(n) => Some(*n),
            FieldValue::U32(n) => Some(*n as u64),
            FieldValue::I64(n) => Some(*n as u64),
            FieldValue::I32(n) => Some(*n as u64),
            _ => None,
        })
    }

    /// Read a string field, or `None` when the field is absent or not a string.
    pub fn get_string(&self, key: Option<u64>) -> Option<String> {
        key.and_then(|k| self.fields.get(&k)).and_then(|v| match v {
            FieldValue::String(b) => Some(String::from_utf8_lossy(b).into_owned()),
            _ => None,
        })
    }
}

/// Container managing all active entities.
#[derive(Default)]
pub struct EntityContainer {
    /// Active (and dormant) entities, indexed **directly by entity index** — a
    /// dense slot array rather than a hash map, so every `get` / `get_mut` /
    /// `get_by_handle` (which fire on essentially every entity update) is a
    /// bounds-checked index instead of a hash lookup. Indices are `0..=16383`;
    /// empty slots hold `None`.
    entities: Vec<Option<Entity>>,
    /// `class_id` per index for entities that were filtered out at create time,
    /// so a later filtered update can pick the right serializer to advance past
    /// them. `-1` means "no skipped entity here". Same dense-slot layout.
    skipped_entity_classes: Vec<i32>,
}

impl EntityContainer {
    pub fn new() -> Self {
        Self::default()
    }

    /// A slotted entity, mutably (`None` if the index is out of range or empty).
    #[inline]
    fn entity_mut(&mut self, index: i32) -> Option<&mut Entity> {
        usize::try_from(index)
            .ok()
            .and_then(|i| self.entities.get_mut(i))
            .and_then(Option::as_mut)
    }

    /// Store an entity at its index, growing the slot array as needed.
    #[inline]
    fn put_entity(&mut self, index: i32, entity: Entity) {
        let Ok(i) = usize::try_from(index) else {
            return;
        };
        if i >= self.entities.len() {
            self.entities.resize_with(i + 1, || None);
        }
        self.entities[i] = Some(entity);
    }

    /// Empty an entity's slot.
    #[inline]
    fn take_entity(&mut self, index: i32) {
        if let Ok(i) = usize::try_from(index)
            && let Some(slot) = self.entities.get_mut(i)
        {
            *slot = None;
        }
    }

    /// The class_id of a skipped entity at `index`, if one was recorded.
    #[inline]
    fn skipped_class(&self, index: i32) -> Option<i32> {
        usize::try_from(index)
            .ok()
            .and_then(|i| self.skipped_entity_classes.get(i))
            .copied()
            .filter(|&c| c >= 0)
    }

    /// Record (or clear, with `None`) the class_id of a skipped entity at `index`.
    #[inline]
    fn set_skipped(&mut self, index: i32, class_id: Option<i32>) {
        let Ok(i) = usize::try_from(index) else {
            return;
        };
        let value = class_id.unwrap_or(-1);
        if i >= self.skipped_entity_classes.len() {
            if value < 0 {
                return; // clearing an absent slot is a no-op
            }
            self.skipped_entity_classes.resize(i + 1, -1);
        }
        self.skipped_entity_classes[i] = value;
    }

    /// Handle a CSVCMsg_PacketEntities message.
    pub fn handle_packet_entities(
        &mut self,
        msg: CsvcMsgPacketEntities,
        class_info: &ClassInfo,
        serializers: &SerializerContainer,
        string_tables: &StringTableContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        let has_pvs_vis_bits = msg.has_pvs_vis_bits_deprecated.unwrap_or(0);
        let entity_data = msg.entity_data.unwrap_or_default();
        let mut br = BitReader::new(&entity_data);

        let mut entity_index: i32 = -1;

        for _ in 0..msg.updated_entries.unwrap_or(0) {
            entity_index += br.read_ubitvar()? as i32 + 1;

            // Read the 2-bit delta command (see CMD_LEAVE / CMD_CREATE_DELETE).
            let cmd = br.read_bits(2)? as u8;

            if cmd & CMD_LEAVE == 0 {
                if cmd & CMD_CREATE_DELETE != 0 {
                    self.handle_create(
                        entity_index,
                        &mut br,
                        class_info,
                        serializers,
                        string_tables,
                        field_decode_ctx,
                        fp_buf,
                    )
                    .map_err(|e| Error::Parse {
                        context: format!("entity create #{}: {}", entity_index, e),
                    })?;
                } else {
                    // Legacy PVS-visibility bits (absent in modern CS2 demos):
                    // when present, a set low bit means "not actually updated".
                    if has_pvs_vis_bits > 0 && (br.read_bits(2)? & 0x01) != 0 {
                        continue;
                    }
                    self.handle_update(
                        entity_index,
                        &mut br,
                        serializers,
                        field_decode_ctx,
                        fp_buf,
                    )
                    .map_err(|e| Error::Parse {
                        context: format!(
                            "entity update #{} (class: {:?}): {}",
                            entity_index,
                            self.get(entity_index).map(|e| &e.class_name),
                            e
                        ),
                    })?;
                }
            } else {
                self.handle_leave(entity_index, cmd & CMD_CREATE_DELETE != 0);
            }
        }

        Ok(())
    }

    /// Handle an entity leaving the client's PVS.
    ///
    /// A plain leave (`delete == false`) marks the entity inactive but keeps it,
    /// so a subsequent update can re-activate it. A leave-and-delete removes it.
    /// Leaves targeting an already-inactive entity are ignored, matching Source
    /// 2's client behavior.
    fn handle_leave(&mut self, index: i32, delete: bool) {
        let active = match self.get(index) {
            Some(e) => e.active,
            None => return,
        };
        if !active {
            return;
        }
        if delete {
            self.take_entity(index);
        } else if let Some(e) = self.entity_mut(index) {
            e.active = false;
        }
    }

    /// Handle a CSVCMsg_PacketEntities message, only tracking specified entity classes.
    /// Entities not in the filter are parsed (to advance the bit reader) but not stored.
    #[allow(clippy::too_many_arguments)]
    pub fn handle_packet_entities_filtered(
        &mut self,
        msg: CsvcMsgPacketEntities,
        class_info: &ClassInfo,
        serializers: &SerializerContainer,
        string_tables: &StringTableContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        class_filter: &HashSet<&str>,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        let has_pvs_vis_bits = msg.has_pvs_vis_bits_deprecated.unwrap_or(0);
        let entity_data = msg.entity_data.unwrap_or_default();
        let mut br = BitReader::new(&entity_data);

        let mut entity_index: i32 = -1;

        for _ in 0..msg.updated_entries.unwrap_or(0) {
            entity_index += br.read_ubitvar()? as i32 + 1;

            // Read the 2-bit delta command (see CMD_LEAVE / CMD_CREATE_DELETE).
            let cmd = br.read_bits(2)? as u8;

            if cmd & CMD_LEAVE == 0 {
                if cmd & CMD_CREATE_DELETE != 0 {
                    self.handle_create_filtered(
                        entity_index,
                        &mut br,
                        class_info,
                        serializers,
                        string_tables,
                        field_decode_ctx,
                        class_filter,
                        fp_buf,
                    )?;
                } else {
                    if has_pvs_vis_bits > 0 && (br.read_bits(2)? & 0x01) != 0 {
                        continue;
                    }
                    self.handle_update_filtered(
                        entity_index,
                        &mut br,
                        class_info,
                        serializers,
                        field_decode_ctx,
                        fp_buf,
                    )?;
                }
            } else {
                self.handle_leave_filtered(entity_index, cmd & CMD_CREATE_DELETE != 0);
            }
        }

        Ok(())
    }

    /// Leave/delete handling for the class-filtered path.
    ///
    /// Tracked entities follow the same active/remove logic as [`handle_leave`].
    /// Untracked (skipped) entities carry no active flag; they are only dropped
    /// from the skip set on delete so their class is still known for updates
    /// while they merely go dormant.
    fn handle_leave_filtered(&mut self, index: i32, delete: bool) {
        match self.get(index).map(|e| e.active) {
            Some(true) => {
                if delete {
                    self.take_entity(index);
                } else if let Some(e) = self.entity_mut(index) {
                    e.active = false;
                }
            }
            Some(false) => {}
            None => {
                if delete {
                    self.set_skipped(index, None);
                }
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn handle_create(
        &mut self,
        index: i32,
        br: &mut BitReader,
        class_info: &ClassInfo,
        serializers: &SerializerContainer,
        string_tables: &StringTableContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        let class_id = br.read_bits(class_info.bits)? as i32;
        let _serial = br.read_bits(NUM_SERIAL_NUM_BITS as usize)?;
        let _unknown = br.read_uvarint32()?;

        let class_entry = class_info.by_id(class_id).ok_or_else(|| Error::Parse {
            context: format!("unknown class_id {}", class_id),
        })?;

        let serializer =
            serializers
                .get(&class_entry.network_name)
                .ok_or_else(|| Error::Parse {
                    context: format!("no serializer for {}", class_entry.network_name),
                })?;

        let mut entity = Entity::new(index, class_id, class_entry.network_name.clone());
        // Pre-size the field map to the class's field count: a create applies the
        // baseline plus the create delta, setting many fields at once, so starting
        // from an empty map otherwise rehashes repeatedly as it grows.
        entity.fields.reserve(serializer.fields.len());

        // Apply baseline from instancebaseline string table
        if let Some(baseline_data) = string_tables.instance_baselines.get(&class_id) {
            let mut baseline_br = BitReader::new(baseline_data);
            entity
                .apply_update(&mut baseline_br, serializer, field_decode_ctx, fp_buf)
                .map_err(|err| Error::Parse {
                    context: format!(
                        "baseline for {} (class_id {}): {}",
                        class_entry.network_name, class_id, err
                    ),
                })?;
        }

        // Apply create delta
        entity
            .apply_update(br, serializer, field_decode_ctx, fp_buf)
            .map_err(|err| Error::Parse {
                context: format!(
                    "create delta for {} (class_id {}): {}",
                    class_entry.network_name, class_id, err
                ),
            })?;
        self.put_entity(index, entity);

        Ok(())
    }

    fn handle_update(
        &mut self,
        index: i32,
        br: &mut BitReader,
        serializers: &SerializerContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<()> {
        let entity = match self.entity_mut(index) {
            Some(e) => e,
            None => {
                return Err(Error::Parse {
                    context: format!("tried to update non-existent entity #{}", index),
                });
            }
        };

        // An update re-activates an entity that had left the PVS.
        entity.active = true;

        let serializer = serializers
            .get(&entity.class_name)
            .ok_or_else(|| Error::Parse {
                context: format!("no serializer for {}", entity.class_name),
            })?;

        entity.apply_update(br, serializer, field_decode_ctx, fp_buf)?;
        Ok(())
    }

    /// Returns `true` if the entity's class passed the filter and was stored.
    #[allow(clippy::too_many_arguments)]
    fn handle_create_filtered(
        &mut self,
        index: i32,
        br: &mut BitReader,
        class_info: &ClassInfo,
        serializers: &SerializerContainer,
        string_tables: &StringTableContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        class_filter: &HashSet<&str>,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<bool> {
        let class_id = br.read_bits(class_info.bits)? as i32;
        let _serial = br.read_bits(NUM_SERIAL_NUM_BITS as usize)?;
        let _unknown = br.read_uvarint32()?;

        let class_entry = class_info.by_id(class_id).ok_or_else(|| Error::Parse {
            context: format!("unknown class_id {}", class_id),
        })?;

        let serializer =
            serializers
                .get(&class_entry.network_name)
                .ok_or_else(|| Error::Parse {
                    context: format!("no serializer for {}", class_entry.network_name),
                })?;

        // A create is a fresh entity at this slot. Clear any stale entry for the
        // index from the *other* map so a later update can't misroute to a
        // previous occupant of the slot (e.g. a tracked weapon that left the PVS
        // and stayed cached while the slot was reused by a skipped entity). This
        // matters because leaves keep entities around, so slots get reused.
        if !class_filter.contains(class_entry.network_name.as_str()) {
            // Skip this entity - just advance the bit reader, but track its
            // class_id so later updates to it can be skipped correctly.
            self.take_entity(index);
            self.set_skipped(index, Some(class_id));
            Entity::skip_update(br, serializer, field_decode_ctx, fp_buf)?;
            return Ok(false);
        }
        self.set_skipped(index, None);

        // Full processing for filtered entities
        let mut entity = Entity::new(index, class_id, class_entry.network_name.clone());
        // Pre-size the field map to the class's field count: a create applies the
        // baseline plus the create delta, setting many fields at once, so starting
        // from an empty map otherwise rehashes repeatedly as it grows.
        entity.fields.reserve(serializer.fields.len());

        if let Some(baseline_data) = string_tables.instance_baselines.get(&class_id) {
            let mut baseline_br = BitReader::new(baseline_data);
            entity.apply_update(&mut baseline_br, serializer, field_decode_ctx, fp_buf)?;
        }

        entity.apply_update(br, serializer, field_decode_ctx, fp_buf)?;
        self.put_entity(index, entity);

        Ok(true)
    }

    /// Returns `true` if this entity is tracked and was updated (vs. skipped).
    fn handle_update_filtered(
        &mut self,
        index: i32,
        br: &mut BitReader,
        class_info: &ClassInfo,
        serializers: &SerializerContainer,
        field_decode_ctx: &mut FieldDecodeContext,
        fp_buf: &mut Vec<FieldPath>,
    ) -> Result<bool> {
        // Check if we're tracking this entity
        if let Some(entity) = self.entity_mut(index) {
            // An update re-activates an entity that had left the PVS.
            entity.active = true;

            let serializer = serializers
                .get(&entity.class_name)
                .ok_or_else(|| Error::Parse {
                    context: format!("no serializer for {}", entity.class_name),
                })?;

            entity.apply_update(br, serializer, field_decode_ctx, fp_buf)?;
            return Ok(true);
        }

        // Entity is not tracked - check if we know its class from skipped creates
        if let Some(class_id) = self.skipped_class(index) {
            let class_entry = class_info.by_id(class_id).ok_or_else(|| Error::Parse {
                context: format!("unknown class_id {}", class_id),
            })?;

            let serializer =
                serializers
                    .get(&class_entry.network_name)
                    .ok_or_else(|| Error::Parse {
                        context: format!("no serializer for {}", class_entry.network_name),
                    })?;

            // Skip this update
            Entity::skip_update(br, serializer, field_decode_ctx, fp_buf)?;
            return Ok(false);
        }

        // Index is in neither map. This can only happen if the entity was
        // created before filtering began; a well-formed stream from the start
        // never reaches here.
        Ok(false)
    }

    /// Look up an entity by its slot index.
    pub fn get(&self, index: i32) -> Option<&Entity> {
        usize::try_from(index)
            .ok()
            .and_then(|i| self.entities.get(i))
            .and_then(Option::as_ref)
    }

    /// Resolve a networked `CHandle` to the entity it refers to, if still active.
    ///
    /// Applies [`ENTITY_HANDLE_INDEX_MASK`] to recover the entity index, then
    /// looks it up. This is the canonical way to follow a handle field such as
    /// `m_hPawn`; decoding the mask by hand risks resolving the wrong entity.
    pub fn get_by_handle(&self, handle: u32) -> Option<&Entity> {
        self.get((handle & ENTITY_HANDLE_INDEX_MASK) as i32)
    }

    /// Iterate over all slotted entities as `(index, entity)` pairs. Includes
    /// dormant (inactive) entities, so consumers that only want live ones must
    /// check [`Entity::active`]. Emitted in ascending index order.
    pub fn iter(&self) -> impl Iterator<Item = (i32, &Entity)> {
        self.entities
            .iter()
            .enumerate()
            .filter_map(|(i, slot)| slot.as_ref().map(|e| (i as i32, e)))
    }

    /// Number of slotted entities (active or dormant).
    pub fn len(&self) -> usize {
        self.entities.iter().filter(|slot| slot.is_some()).count()
    }

    pub fn is_empty(&self) -> bool {
        self.entities.iter().all(Option::is_none)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn container_new_is_empty() {
        let c = EntityContainer::new();
        assert!(c.is_empty());
        assert_eq!(c.len(), 0);
        assert!(c.get(0).is_none());
    }

    #[test]
    fn entity_fields_insert_and_get() {
        let mut e = Entity::new(1, 10, "TestClass".to_string());
        e.fields.insert(42, FieldValue::I32(100));
        assert!(matches!(e.fields.get(&42), Some(FieldValue::I32(100))));
    }

    #[test]
    fn container_insert_and_iter() {
        let mut c = EntityContainer::new();
        let e = Entity::new(5, 10, "Hero".to_string());
        c.put_entity(5, e);
        assert_eq!(c.len(), 1);
        assert!(!c.is_empty());
        assert!(c.get(5).is_some());
        assert_eq!(c.get(5).unwrap().class_name, "Hero");
    }

    #[test]
    fn container_iter_yields_entries() {
        let mut c = EntityContainer::new();
        c.put_entity(1, Entity::new(1, 1, "A".to_string()));
        c.put_entity(2, Entity::new(2, 2, "B".to_string()));
        let keys: Vec<i32> = c.iter().map(|(k, _)| k).collect();
        assert_eq!(keys.len(), 2);
    }

    #[test]
    fn entity_basic_fields() {
        let e = Entity::new(7, 42, "NPC".to_string());
        assert_eq!(e.index, 7);
        assert_eq!(e.class_id, 42);
        assert_eq!(e.class_name, "NPC");
        assert_eq!(e.serial, 0);
        assert!(e.fields.is_empty());
    }
}

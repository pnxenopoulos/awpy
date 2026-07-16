use std::collections::HashMap;

use crate::error::{Error, Result};
use crate::io::BitReader;

use super::class_info::ClassInfo;

use awpy_proto::proto::{CDemoStringTables, CsvcMsgCreateStringTable, CsvcMsgUpdateStringTable};

// String table delta encoding uses a circular buffer of recently-seen
// strings. New strings can reference a history entry by index and copy a
// prefix, then append the remainder. These constants control the buffer.
const HISTORY_SIZE: usize = 32;
const HISTORY_BITMASK: usize = HISTORY_SIZE - 1;

/// Maximum length (in characters) of a string table key.
const MAX_STRING_BITS: usize = 5;
const MAX_STRING_SIZE: usize = 1 << MAX_STRING_BITS;

/// Maximum size (in bytes) of per-entry user data.
const MAX_USERDATA_BITS: usize = 17;
const MAX_USERDATA_SIZE: usize = 1 << MAX_USERDATA_BITS;

/// The `instancebaseline` table stores default field values for each entity class.
pub const INSTANCE_BASELINE_TABLE_NAME: &str = "instancebaseline";

/// A single entry in a string table.
#[derive(Debug, Clone)]
pub struct StringTableEntry {
    pub string: Option<String>,
    pub user_data: Option<Vec<u8>>,
}

/// A string table.
#[derive(Debug)]
pub struct StringTable {
    pub name: String,
    user_data_fixed_size: bool,
    user_data_size: i32,
    user_data_size_bits: i32,
    flags: i32,
    using_varint_bitcounts: bool,
    pub entries: Vec<StringTableEntry>,
    /// Entry indices written since the last [`StringTableContainer::clear_dirty`]
    /// (i.e. since the previous per-tick callback). Lets consumers decode only
    /// what changed this tick instead of rescanning the whole table — see
    /// [`StringTable::dirty_indices`]. May contain duplicates if an index is
    /// touched more than once between callbacks.
    dirty: Vec<usize>,
}

impl StringTable {
    fn new(
        name: &str,
        user_data_fixed_size: bool,
        user_data_size: i32,
        user_data_size_bits: i32,
        flags: i32,
        using_varint_bitcounts: bool,
    ) -> Self {
        Self {
            name: name.to_string(),
            user_data_fixed_size,
            user_data_size,
            user_data_size_bits,
            flags,
            using_varint_bitcounts,
            entries: Vec::new(),
            dirty: Vec::new(),
        }
    }

    /// Entry indices written since the last per-tick callback.
    ///
    /// A consumer that maintains its own per-index state can react to only
    /// these entries rather than iterating (and decoding) every entry every
    /// tick. The list is cleared by the parser after each callback via
    /// [`StringTableContainer::clear_dirty`]. Indices may repeat.
    pub fn dirty_indices(&self) -> &[usize] {
        &self.dirty
    }

    /// Parse a string table update from a bit reader.
    pub fn parse_update(&mut self, br: &mut BitReader, num_entries: i32) -> Result<()> {
        let mut entry_index: i32 = -1;
        let mut history: Vec<[u8; MAX_STRING_SIZE]> = vec![[0u8; MAX_STRING_SIZE]; HISTORY_SIZE];
        let mut history_delta_index: usize = 0;
        let mut string_buf = vec![0u8; 1024];
        let mut user_data_buf = vec![0u8; MAX_USERDATA_SIZE];
        let mut user_data_uncompressed_buf = vec![0u8; MAX_USERDATA_SIZE];

        for _ in 0..num_entries as usize {
            // Read index
            entry_index = if br.read_bool()? {
                entry_index + 1
            } else {
                br.read_uvarint32()? as i32 + 1
            };

            // Read string
            let has_string = br.read_bool()?;
            let string = if has_string {
                let mut size: usize = 0;

                if br.read_bool()? {
                    // Uses history reference
                    let mut history_delta_zero = 0;
                    if history_delta_index > HISTORY_SIZE {
                        history_delta_zero = history_delta_index & HISTORY_BITMASK;
                    }

                    let index = (history_delta_zero + br.read_bits(5)? as usize) & HISTORY_BITMASK;
                    let bytes_to_copy = br.read_bits(MAX_STRING_BITS)? as usize;
                    size += bytes_to_copy;

                    string_buf[..bytes_to_copy].copy_from_slice(&history[index][..bytes_to_copy]);
                    size += br.read_string_into(&mut string_buf[bytes_to_copy..])?;
                } else {
                    size += br.read_string_into(&mut string_buf)?;
                }

                // Update history
                let mut she = [0u8; MAX_STRING_SIZE];
                let copy_len = size.min(MAX_STRING_SIZE);
                she[..copy_len].copy_from_slice(&string_buf[..copy_len]);
                history[history_delta_index & HISTORY_BITMASK] = she;
                history_delta_index += 1;

                Some(String::from_utf8_lossy(&string_buf[..size]).into_owned())
            } else {
                None
            };

            // Read user data
            let has_user_data = br.read_bool()?;
            let user_data = if has_user_data {
                if self.user_data_fixed_size {
                    br.read_bits_to_bytes(&mut user_data_buf, self.user_data_size_bits as usize)?;
                    Some(user_data_buf[..self.user_data_size as usize].to_vec())
                } else {
                    let mut is_compressed = false;
                    if (self.flags & 0x1) != 0 {
                        is_compressed = br.read_bool()?;
                    }

                    let size = if self.using_varint_bitcounts {
                        br.read_ubitvar()? as usize
                    } else {
                        br.read_bits(MAX_USERDATA_BITS)? as usize
                    };

                    br.read_bytes(&mut user_data_buf[..size])?;

                    if is_compressed {
                        let decomp_len = snap::raw::decompress_len(&user_data_buf[..size])
                            .map_err(|e| Error::Decompress(e.to_string()))?;
                        user_data_uncompressed_buf.resize(decomp_len, 0);
                        snap::raw::Decoder::new()
                            .decompress(&user_data_buf[..size], &mut user_data_uncompressed_buf)
                            .map_err(|e| Error::Decompress(e.to_string()))?;
                        Some(user_data_uncompressed_buf[..decomp_len].to_vec())
                    } else {
                        Some(user_data_buf[..size].to_vec())
                    }
                }
            } else {
                None
            };

            // Insert or update
            let idx = entry_index as usize;
            if idx < self.entries.len() {
                if let Some(ud) = user_data {
                    self.entries[idx].user_data = Some(ud);
                }
                if let Some(s) = string {
                    self.entries[idx].string = Some(s);
                }
            } else {
                // Extend entries to reach idx
                while self.entries.len() < idx {
                    self.entries.push(StringTableEntry {
                        string: None,
                        user_data: None,
                    });
                }
                self.entries.push(StringTableEntry { string, user_data });
            }
            self.dirty.push(idx);
        }

        Ok(())
    }
}

/// Container for all string tables.
#[derive(Default)]
pub struct StringTableContainer {
    tables: Vec<StringTable>,
    /// Cached instance baselines: class_id -> baseline data.
    pub instance_baselines: HashMap<i32, Vec<u8>>,
}

impl StringTableContainer {
    pub fn new() -> Self {
        Self::default()
    }

    /// Handle CSVCMsg_CreateStringTable. Returns `true` if the created table
    /// is `instancebaseline` (caller should refresh baselines).
    pub fn handle_create(&mut self, msg: CsvcMsgCreateStringTable) -> Result<bool> {
        let name = msg.name.as_deref().unwrap_or("");
        let is_baseline = name == INSTANCE_BASELINE_TABLE_NAME;
        let mut table = StringTable::new(
            name,
            msg.user_data_fixed_size.unwrap_or(false),
            msg.user_data_size.unwrap_or(0),
            msg.user_data_size_bits.unwrap_or(0),
            msg.flags.unwrap_or(0),
            msg.using_varint_bitcounts.unwrap_or(false),
        );

        let string_data = if msg.data_compressed.unwrap_or(false) {
            let sd = msg.string_data.as_deref().unwrap_or(&[]);
            let decomp_len =
                snap::raw::decompress_len(sd).map_err(|e| Error::Decompress(e.to_string()))?;
            let mut buf = vec![0u8; decomp_len];
            snap::raw::Decoder::new()
                .decompress(sd, &mut buf)
                .map_err(|e| Error::Decompress(e.to_string()))?;
            buf
        } else {
            msg.string_data.unwrap_or_default()
        };

        let mut br = BitReader::new(&string_data);
        table.parse_update(&mut br, msg.num_entries.unwrap_or(0))?;

        self.tables.push(table);
        Ok(is_baseline)
    }

    /// Handle CSVCMsg_UpdateStringTable. Returns `true` if the updated table
    /// is `instancebaseline` (caller should refresh baselines).
    pub fn handle_update(&mut self, msg: CsvcMsgUpdateStringTable) -> Result<bool> {
        let table_id = msg.table_id.unwrap_or(0) as usize;
        if table_id >= self.tables.len() {
            return Err(Error::Parse {
                context: format!("string table update for non-existent table {}", table_id),
            });
        }

        let is_baseline = self.tables[table_id].name == INSTANCE_BASELINE_TABLE_NAME;

        let string_data = msg.string_data.unwrap_or_default();
        let mut br = BitReader::new(&string_data);
        self.tables[table_id].parse_update(&mut br, msg.num_changed_entries.unwrap_or(0))?;

        Ok(is_baseline)
    }

    /// Do a full update from CDemoStringTables (used in full packets).
    pub fn do_full_update(&mut self, cmd: CDemoStringTables) {
        for incoming in &cmd.tables {
            let table_name = incoming.table_name.as_deref().unwrap_or("");
            if let Some(table) = self.tables.iter_mut().find(|t| t.name == table_name) {
                for (i, item) in incoming.items.iter().enumerate() {
                    let entry = StringTableEntry {
                        string: item.str.clone(),
                        user_data: item.data.clone(),
                    };
                    if i < table.entries.len() {
                        if entry.user_data.is_some() {
                            table.entries[i].user_data = entry.user_data;
                            table.dirty.push(i);
                        }
                    } else {
                        while table.entries.len() < i {
                            table.entries.push(StringTableEntry {
                                string: None,
                                user_data: None,
                            });
                        }
                        table.entries.push(entry);
                        table.dirty.push(i);
                    }
                }
            }
        }
    }

    /// Clear every table's dirty-index list.
    ///
    /// The parser calls this after each per-tick callback so that
    /// [`StringTable::dirty_indices`] reflects only the entries written since
    /// the previous callback.
    pub fn clear_dirty(&mut self) {
        for table in &mut self.tables {
            table.dirty.clear();
        }
    }

    /// Update instance baselines from the instancebaseline string table.
    pub fn update_instance_baselines(&mut self, _class_info: &ClassInfo) {
        if let Some(table) = self
            .tables
            .iter()
            .find(|t| t.name == INSTANCE_BASELINE_TABLE_NAME)
        {
            for entry in &table.entries {
                if let (Some(s), Some(data)) = (&entry.string, &entry.user_data)
                    && let Ok(class_id) = s.parse::<i32>()
                {
                    // Only clone if new or changed
                    if self.instance_baselines.get(&class_id) != Some(data) {
                        self.instance_baselines.insert(class_id, data.clone());
                    }
                }
            }
        }
    }

    /// Look up a string table by name.
    pub fn find_table(&self, name: &str) -> Option<&StringTable> {
        self.tables.iter().find(|t| t.name == name)
    }

    /// Returns a slice of all string tables.
    pub fn tables(&self) -> &[StringTable] {
        &self.tables
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn container_new_is_empty() {
        let c = StringTableContainer::new();
        assert!(c.tables().is_empty());
        assert!(c.instance_baselines.is_empty());
    }

    #[test]
    fn find_table_missing() {
        let c = StringTableContainer::new();
        assert!(c.find_table("nonexistent").is_none());
    }

    #[test]
    fn update_instance_baselines_on_empty_is_noop() {
        let mut c = StringTableContainer::new();
        let ci = ClassInfo::empty();
        c.update_instance_baselines(&ci);
        assert!(c.instance_baselines.is_empty());
    }

    #[test]
    fn handle_update_invalid_table_id() {
        let mut c = StringTableContainer::new();
        let msg = CsvcMsgUpdateStringTable {
            table_id: Some(99),
            num_changed_entries: Some(0),
            string_data: None,
        };
        let result = c.handle_update(msg);
        assert!(result.is_err());
    }

    #[test]
    fn handle_create_empty_uncompressed() {
        let mut c = StringTableContainer::new();
        let msg = CsvcMsgCreateStringTable {
            name: Some("test".to_string()),
            num_entries: Some(0),
            user_data_fixed_size: Some(false),
            user_data_size: Some(0),
            user_data_size_bits: Some(0),
            flags: Some(0),
            string_data: Some(vec![]),
            data_compressed: Some(false),
            using_varint_bitcounts: Some(false),
            ..Default::default()
        };
        c.handle_create(msg).unwrap();
        assert_eq!(c.tables().len(), 1);
        assert!(c.find_table("test").is_some());
    }
}

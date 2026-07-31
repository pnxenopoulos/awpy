use std::collections::HashMap;

use rustc_hash::FxHashMap;
// Arc (not Rc) so that SerializerContainer is Send + Sync and can be
// shared across threads.  The serializer graph is immutable after
// construction, so atomic refcounting adds negligible overhead.
use std::sync::Arc;

use prost::Message;

use crate::error::Result;
use crate::io::ByteReader;

use super::field_decoder::{self, FieldMetadata};
use super::field_path::FieldPath;

use awpy_proto::proto::{CDemoSendTables, CsvcMsgFlattenedSerializer};

/// Parsed type information from a `var_type` string (e.g. `"CNetworkUtlVectorBase< int32 >"`).
#[derive(Debug, Clone)]
pub struct FieldType {
    /// The core type name (e.g. `"int32"`, `"CNetworkUtlVectorBase"`).
    pub base_type: String,
    /// `true` if the type ends with `*` (pointer / handle).
    pub pointer: bool,
    /// Inner type parameter for generics (e.g. `int32` inside `CNetworkUtlVectorBase<int32>`).
    pub generic_type: Option<Box<FieldType>>,
    /// Numeric array length for `Type[N]` syntax.
    pub array_length: Option<usize>,
    /// Symbolic array length for `Type[SYMBOL]` syntax (e.g. `MAX_ABILITY_DRAFT_ABILITIES`).
    pub count: Option<String>,
}

/// A single field within a serializer, describing one network property.
#[derive(Debug, Clone)]
pub struct SerializerField {
    /// Source 2 type string (e.g. `"float32"`, `"CNetworkUtlVectorBase< int32 >"`).
    pub var_type: String,
    /// Field name (e.g. `"m_iHealth"`).
    pub var_name: String,
    /// Bit width hint for quantized floats and QAngle.
    pub bit_count: Option<i32>,
    /// Low end of quantized float range.
    pub low_value: Option<f32>,
    /// High end of quantized float range.
    pub high_value: Option<f32>,
    /// Quantized float encoding flags (see `QFE_*` constants).
    pub encode_flags: Option<i32>,
    /// Name of a nested serializer (for composite / array fields).
    pub field_serializer_name: Option<String>,
    /// Dotted path prefix used by the entity field name resolution.
    pub send_node: Option<String>,
    /// Optional encoder hint (e.g. `"coord"`, `"normal"`, `"fixed64"`).
    pub var_encoder: Option<String>,
    /// Resolved nested serializer (populated during [`SerializerContainer::parse`]).
    pub field_serializer: Option<Arc<Serializer>>,
    /// Parsed type information.
    pub field_type: FieldType,
    /// Resolved decoder and special descriptor.
    pub metadata: FieldMetadata,
}

impl SerializerField {
    /// Returns `true` if this field represents a variable-length array.
    pub fn is_dynamic_array(&self) -> bool {
        self.metadata.is_dynamic_array()
    }
}

/// A serializer: a named collection of fields describing an entity class.
#[derive(Debug, Clone)]
pub struct Serializer {
    pub name: String,
    pub fields: Vec<Arc<SerializerField>>,
}

impl Serializer {
    /// Resolve a dotted field name (e.g. "m_pGameRules.m_bGamePaused") to a packed u64 key.
    /// Walks the serializer hierarchy matching send_node + var_name against path components.
    pub fn resolve_field_key(&self, path: &str) -> Option<u64> {
        let parts: Vec<&str> = path.split('.').collect();
        self.resolve_parts(&parts, 0)
    }

    fn resolve_parts(&self, parts: &[&str], depth: usize) -> Option<u64> {
        if depth >= parts.len() {
            return None;
        }

        for (field_idx, field) in self.fields.iter().enumerate() {
            // Build the name parts this field contributes (send_node + var_name)
            let mut field_parts: Vec<&str> = Vec::new();
            if let Some(ref sn) = field.send_node
                && !sn.is_empty()
            {
                for part in sn.split('.') {
                    field_parts.push(part);
                }
            }
            if !field.var_name.is_empty() {
                field_parts.push(&field.var_name);
            }

            // Check if the remaining path starts with these field parts
            let remaining = &parts[depth..];
            if remaining.len() < field_parts.len() {
                continue;
            }
            if field_parts != remaining[..field_parts.len()] {
                continue;
            }

            let consumed = depth + field_parts.len();

            // If we've consumed all parts, this is the field
            if consumed == parts.len() {
                let mut fp = FieldPath::default();
                fp.data[0] = field_idx as u8;
                // last stays 0
                return Some(fp.pack());
            }

            // More parts remain — we need to recurse into a sub-serializer
            let next_part = parts[consumed];

            // Dynamic array: next part is a numeric index
            if field.is_dynamic_array() {
                if let Ok(array_idx) = next_part.parse::<usize>()
                    && let Some(ref fs) = field.field_serializer
                {
                    let inner_field = &fs.fields[0];
                    let after_idx = consumed + 1;

                    if after_idx == parts.len() {
                        // The array element itself is the value
                        let mut fp = FieldPath::default();
                        fp.data[0] = field_idx as u8;
                        fp.data[1] = array_idx as u8;
                        fp.last = 1;
                        return Some(fp.pack());
                    }

                    // Recurse into the inner field's serializer
                    if let Some(ref inner_fs) = inner_field.field_serializer
                        && let Some(key) = inner_fs.resolve_parts(parts, after_idx)
                    {
                        let inner_fp = FieldPath::unpack(key);
                        let mut fp = FieldPath::default();
                        fp.data[0] = field_idx as u8;
                        fp.data[1] = array_idx as u8;
                        fp.last = 2 + inner_fp.last;
                        for i in 0..=inner_fp.last {
                            fp.data[2 + i] = inner_fp.data[i];
                        }
                        return Some(fp.pack());
                    }
                }
                continue;
            }

            // Non-dynamic: recurse into field_serializer
            if let Some(ref fs) = field.field_serializer
                && let Some(key) = fs.resolve_parts(parts, consumed)
            {
                let inner_fp = FieldPath::unpack(key);
                let mut fp = FieldPath::default();
                fp.data[0] = field_idx as u8;
                fp.last = 1 + inner_fp.last;
                for i in 0..=inner_fp.last {
                    fp.data[1 + i] = inner_fp.data[i];
                }
                return Some(fp.pack());
            }
        }

        None
    }

    /// Convert a packed u64 key back to a dotted field name string.
    /// Walks the serializer hierarchy using the unpacked FieldPath.
    pub fn field_name_for_key(&self, key: u64) -> Option<String> {
        let fp = FieldPath::unpack(key);
        let mut parts: Vec<String> = Vec::new();
        let mut field = self.fields.get(fp.get(0))?;

        if let Some(ref sn) = field.send_node
            && !sn.is_empty()
        {
            for part in sn.split('.') {
                parts.push(part.to_string());
            }
        }
        parts.push(field.var_name.clone());

        for i in 1..=fp.last {
            let idx = fp.get(i);
            if field.is_dynamic_array() {
                parts.push(idx.to_string());
                if let Some(ref fs) = field.field_serializer {
                    field = &fs.fields[0];
                } else {
                    break;
                }
            } else if let Some(ref fs) = field.field_serializer {
                field = fs.fields.get(idx)?;
                if let Some(ref sn) = field.send_node
                    && !sn.is_empty()
                {
                    for part in sn.split('.') {
                        parts.push(part.to_string());
                    }
                }
                parts.push(field.var_name.clone());
            } else {
                break;
            }
        }

        Some(parts.join("."))
    }
}

/// Container holding all parsed serializers, indexed by name.
#[derive(Clone)]
pub struct SerializerContainer {
    // `FxHashMap` (not the default SipHash `HashMap`): `get` is called once per
    // entity update in the decode hot path, hashing the class-name string each
    // time; FxHash is markedly cheaper for short string keys.
    pub serializers: FxHashMap<String, Arc<Serializer>>,
}

impl SerializerContainer {
    /// Parse a CDemoSendTables message into a SerializerContainer.
    pub fn parse(cmd: CDemoSendTables) -> Result<Self> {
        let data = cmd.data.unwrap_or_default();
        let mut data_reader = ByteReader::new(&data);

        // Read varint size prefix, then decode the flattened serializer message
        let _size = data_reader.read_uvarint64()?;
        let remaining = data_reader.read_bytes(data_reader.remaining())?;
        let msg = CsvcMsgFlattenedSerializer::decode(remaining)?;

        let symbols = &msg.symbols;

        let resolve_sym = |i: i32| -> &str { &symbols[i as usize] };

        // Build fields and serializers
        let mut field_cache: HashMap<i32, Arc<SerializerField>> = HashMap::new();
        let mut serializer_map: FxHashMap<String, Arc<Serializer>> = FxHashMap::default();

        for serializer_proto in &msg.serializers {
            let ser_name = resolve_sym(serializer_proto.serializer_name_sym.unwrap_or(0));
            let mut serializer = Serializer {
                name: ser_name.to_string(),
                fields: Vec::with_capacity(serializer_proto.fields_index.len()),
            };

            for &field_index in &serializer_proto.fields_index {
                if let Some(cached) = field_cache.get(&field_index) {
                    serializer.fields.push(cached.clone());
                    continue;
                }

                let field_proto = &msg.fields[field_index as usize];

                let var_type = field_proto
                    .var_type_sym
                    .map(resolve_sym)
                    .unwrap_or("")
                    .to_string();
                let var_name = field_proto
                    .var_name_sym
                    .map(resolve_sym)
                    .unwrap_or("")
                    .to_string();
                let send_node = field_proto.send_node_sym.map(resolve_sym).map(String::from);
                let var_encoder = field_proto
                    .var_encoder_sym
                    .map(resolve_sym)
                    .map(String::from);
                let field_serializer_name = field_proto
                    .field_serializer_name_sym
                    .map(resolve_sym)
                    .map(String::from);

                let field_type = parse_type(&var_type);
                let mut metadata = field_decoder::get_field_metadata(
                    &var_type,
                    &var_name,
                    field_proto.bit_count,
                    field_proto.low_value,
                    field_proto.high_value,
                    field_proto.encode_flags,
                    var_encoder.as_deref(),
                    field_serializer_name.is_some(),
                );

                // Polymorphic fields (e.g. `m_pGameModeRules`) encode a presence
                // bool followed by a ubitvar selecting the concrete sub-type,
                // rather than the plain presence bool of a normal pointer.
                if !field_proto.polymorphic_types.is_empty() {
                    metadata.decoder = field_decoder::Decoder::Poly;
                }

                // Resolve field serializer
                let field_serializer = match &metadata {
                    fm if fm.is_fixed_array() => {
                        let length = fm.fixed_array_length().unwrap_or(0);
                        // Build a pseudo-serializer containing `length` copies of the inner field
                        let inner_ser = field_serializer_name
                            .as_deref()
                            .and_then(|n| serializer_map.get(n).cloned());

                        let inner_field = SerializerField {
                            var_type: var_type.clone(),
                            var_name: var_name.clone(),
                            bit_count: field_proto.bit_count,
                            low_value: field_proto.low_value,
                            high_value: field_proto.high_value,
                            encode_flags: field_proto.encode_flags,
                            field_serializer_name: field_serializer_name.clone(),
                            send_node: send_node.clone(),
                            var_encoder: var_encoder.clone(),
                            field_serializer: inner_ser,
                            field_type: field_type.clone(),
                            metadata: metadata.clone(),
                        };
                        let inner_rc = Arc::new(inner_field);
                        let mut fields = Vec::with_capacity(length);
                        fields.resize(length, inner_rc);
                        Some(Arc::new(Serializer {
                            name: String::new(),
                            fields,
                        }))
                    }
                    fm if fm.is_dynamic_array() => {
                        // For dynamic arrays of serializers, build a single-element serializer
                        if fm.is_dynamic_serializer_array() {
                            let inner_ser = field_serializer_name
                                .as_deref()
                                .and_then(|n| serializer_map.get(n).cloned());
                            let inner = Arc::new(SerializerField {
                                var_type: String::new(),
                                var_name: String::new(),
                                bit_count: None,
                                low_value: None,
                                high_value: None,
                                encode_flags: None,
                                field_serializer_name: None,
                                send_node: None,
                                var_encoder: None,
                                field_serializer: inner_ser,
                                field_type: parse_type(""),
                                metadata: FieldMetadata::default(),
                            });
                            Some(Arc::new(Serializer {
                                name: String::new(),
                                fields: vec![inner],
                            }))
                        } else {
                            // Dynamic array of primitives: single-element serializer with inner decoder
                            let inner_metadata = fm.dynamic_array_inner_metadata();
                            let inner = Arc::new(SerializerField {
                                var_type: String::new(),
                                var_name: String::new(),
                                bit_count: None,
                                low_value: None,
                                high_value: None,
                                encode_flags: None,
                                field_serializer_name: None,
                                send_node: None,
                                var_encoder: None,
                                field_serializer: None,
                                field_type: parse_type(""),
                                metadata: inner_metadata,
                            });
                            Some(Arc::new(Serializer {
                                name: String::new(),
                                fields: vec![inner],
                            }))
                        }
                    }
                    fm if fm.is_pointer() => field_serializer_name
                        .as_deref()
                        .and_then(|n| serializer_map.get(n).cloned()),
                    _ => field_serializer_name
                        .as_deref()
                        .and_then(|n| serializer_map.get(n).cloned()),
                };

                let field = Arc::new(SerializerField {
                    var_type,
                    var_name,
                    bit_count: field_proto.bit_count,
                    low_value: field_proto.low_value,
                    high_value: field_proto.high_value,
                    encode_flags: field_proto.encode_flags,
                    field_serializer_name,
                    send_node,
                    var_encoder,
                    field_serializer,
                    field_type,
                    metadata,
                });

                field_cache.insert(field_index, field.clone());
                serializer.fields.push(field);
            }

            serializer_map.insert(serializer.name.clone(), Arc::new(serializer));
        }

        Ok(Self {
            serializers: serializer_map,
        })
    }

    /// Look up a serializer by class network name.
    pub fn get(&self, name: &str) -> Option<&Serializer> {
        self.serializers.get(name).map(|arc| arc.as_ref())
    }
}

/// Parse a var_type string into a FieldType.
pub fn parse_type(s: &str) -> FieldType {
    let s = s.trim();

    // Check for pointer
    if let Some(stripped) = s.strip_suffix('*') {
        return FieldType {
            base_type: stripped.trim().to_string(),
            pointer: true,
            generic_type: None,
            array_length: None,
            count: None,
        };
    }

    // Check for array: type[length]
    if let Some(bracket_pos) = s.find('[')
        && s.ends_with(']')
    {
        let base = s[..bracket_pos].trim();
        let len_str = s[bracket_pos + 1..s.len() - 1].trim();
        let array_length = len_str.parse::<usize>().ok();
        let count = if array_length.is_none() {
            Some(len_str.to_string())
        } else {
            None
        };
        return FieldType {
            base_type: base.to_string(),
            pointer: false,
            generic_type: None,
            array_length,
            count,
        };
    }

    // Check for generic: Type< InnerType >
    if let Some(angle_pos) = s.find('<')
        && let Some(close_pos) = s.rfind('>')
    {
        let base = s[..angle_pos].trim();
        let inner = s[angle_pos + 1..close_pos].trim();
        return FieldType {
            base_type: base.to_string(),
            pointer: false,
            generic_type: Some(Box::new(parse_type(inner))),
            array_length: None,
            count: None,
        };
    }

    // Simple type
    FieldType {
        base_type: s.to_string(),
        pointer: false,
        generic_type: None,
        array_length: None,
        count: None,
    }
}

#[cfg(test)]
mod tests {
    use super::super::field_decoder::{Decoder, FieldMetadata};
    use super::*;

    // ── parse_type ──

    #[test]
    fn parse_type_simple() {
        let ft = parse_type("int32");
        assert_eq!(ft.base_type, "int32");
        assert!(!ft.pointer);
        assert!(ft.generic_type.is_none());
        assert!(ft.array_length.is_none());
        assert!(ft.count.is_none());
    }

    #[test]
    fn parse_type_pointer() {
        let ft = parse_type("CBaseEntity*");
        assert_eq!(ft.base_type, "CBaseEntity");
        assert!(ft.pointer);
    }

    #[test]
    fn parse_type_array_numeric() {
        let ft = parse_type("int32[4]");
        assert_eq!(ft.base_type, "int32");
        assert_eq!(ft.array_length, Some(4));
        assert!(ft.count.is_none());
    }

    #[test]
    fn parse_type_array_symbolic() {
        let ft = parse_type("int32[MAX_ABILITIES]");
        assert_eq!(ft.base_type, "int32");
        assert!(ft.array_length.is_none());
        assert_eq!(ft.count.as_deref(), Some("MAX_ABILITIES"));
    }

    #[test]
    fn parse_type_generic() {
        let ft = parse_type("CNetworkUtlVectorBase< int32 >");
        assert_eq!(ft.base_type, "CNetworkUtlVectorBase");
        let inner = ft.generic_type.as_ref().unwrap();
        assert_eq!(inner.base_type, "int32");
    }

    #[test]
    fn parse_type_generic_nested() {
        let ft = parse_type("CHandle< CBaseEntity >");
        assert_eq!(ft.base_type, "CHandle");
        assert_eq!(ft.generic_type.as_ref().unwrap().base_type, "CBaseEntity");
    }

    #[test]
    fn parse_type_whitespace_trimming() {
        let ft = parse_type("  float32  ");
        assert_eq!(ft.base_type, "float32");
    }

    #[test]
    fn parse_type_empty_string() {
        let ft = parse_type("");
        assert_eq!(ft.base_type, "");
        assert!(!ft.pointer);
    }

    #[test]
    fn parse_type_complex_all_fields() {
        let ft = parse_type("uint32[16]");
        assert_eq!(ft.base_type, "uint32");
        assert!(!ft.pointer);
        assert!(ft.generic_type.is_none());
        assert_eq!(ft.array_length, Some(16));
        assert!(ft.count.is_none());
    }

    // ── Serializer key resolution ──

    fn make_field(name: &str, send_node: Option<&str>) -> Arc<SerializerField> {
        Arc::new(SerializerField {
            var_type: String::new(),
            var_name: name.to_string(),
            bit_count: None,
            low_value: None,
            high_value: None,
            encode_flags: None,
            field_serializer_name: None,
            send_node: send_node.map(String::from),
            var_encoder: None,
            field_serializer: None,
            field_type: parse_type(""),
            metadata: FieldMetadata {
                decoder: Decoder::U64,
                special: None,
            },
        })
    }

    #[test]
    fn resolve_field_key_found() {
        let ser = Serializer {
            name: "test".to_string(),
            fields: vec![make_field("m_iHealth", None)],
        };
        assert!(ser.resolve_field_key("m_iHealth").is_some());
    }

    #[test]
    fn resolve_field_key_not_found() {
        let ser = Serializer {
            name: "test".to_string(),
            fields: vec![make_field("m_iHealth", None)],
        };
        assert!(ser.resolve_field_key("m_iMana").is_none());
    }

    #[test]
    fn field_name_roundtrip() {
        let ser = Serializer {
            name: "test".to_string(),
            fields: vec![make_field("m_iHealth", None), make_field("m_iMana", None)],
        };
        let key = ser.resolve_field_key("m_iMana").unwrap();
        let name = ser.field_name_for_key(key).unwrap();
        assert_eq!(name, "m_iMana");
    }

    #[test]
    fn resolve_with_send_node() {
        let ser = Serializer {
            name: "test".to_string(),
            fields: vec![make_field("m_bPaused", Some("m_pGameRules"))],
        };
        let key = ser.resolve_field_key("m_pGameRules.m_bPaused");
        assert!(key.is_some());
        let name = ser.field_name_for_key(key.unwrap()).unwrap();
        assert_eq!(name, "m_pGameRules.m_bPaused");
    }
}

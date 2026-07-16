use crate::error::Result;
use crate::io::BitReader;

use super::field_value::FieldValue;
use super::quantized_float::QuantizedFloat;

/// Mutable state shared across field decoders during a single parse pass.
pub struct FieldDecodeContext {
    /// Current tick interval; used by the simulation-time decoder.
    pub tick_interval: f32,
    /// Reusable buffer for string decoding (avoids per-field allocations).
    pub string_buf: Vec<u8>,
}

impl FieldDecodeContext {
    pub fn new(tick_interval: f32) -> Self {
        Self {
            tick_interval,
            string_buf: Vec::with_capacity(512),
        }
    }
}

/// Describes how to read a single field value from a [`BitReader`](crate::io::BitReader).
///
/// Each variant corresponds to a Source 2 wire encoding. The correct
/// variant is chosen at parse time by [`get_field_metadata`].
#[derive(Debug, Clone)]
pub enum Decoder {
    Bool,
    I64,
    U64,
    U64Fixed64,
    F32NoScale,
    F32SimulationTime,
    F32Coord,
    F32Normal,
    F32Quantized(QuantizedFloat),
    /// Clip ammo: a varint transmitted as `actual_ammo + 1`.
    ///
    /// CS2 special-cases `m_iClip1` this way; decode subtracts one (guarding
    /// against the `0` sentinel to avoid a wrapping underflow).
    Ammo,
    String,
    Vector2(Box<Decoder>),
    Vector3(Box<Decoder>),
    Vector3Normal,
    Vector4(Box<Decoder>),
    /// Fixed-count float vector for types wider than 4 components (e.g.
    /// `Quaternion` = 4, `CTransform` = 6). Each component uses `inner`.
    FloatVecN {
        count: usize,
        inner: Box<Decoder>,
    },
    /// Length-prefixed byte blob (`CUtlBinaryBlock`): a varint byte count
    /// followed by that many raw bytes.
    BinaryBlock,
    /// Polymorphic pointer leaf (e.g. `m_pGameModeRules`): a presence bool plus
    /// a ubitvar selecting which concrete sub-serializer is active. We keep the
    /// bool as the field value; the selector affects deeper field paths.
    Poly,
    QAnglePrecise,
    QAngleBitCount {
        bit_count: usize,
    },
    QAngleCoord,
    /// Used as a placeholder/invalid decoder.
    Default,
}

impl Decoder {
    /// Read a single field value from the bitstream.
    pub fn decode(&self, ctx: &mut FieldDecodeContext, br: &mut BitReader) -> Result<FieldValue> {
        match self {
            Decoder::Bool => Ok(FieldValue::Bool(br.read_bool()?)),

            Decoder::I64 => Ok(FieldValue::I64(br.read_varint64()?)),

            Decoder::U64 => Ok(FieldValue::U64(br.read_uvarint64()?)),

            Decoder::U64Fixed64 => {
                let mut buf = [0u8; 8];
                br.read_bytes(&mut buf)?;
                Ok(FieldValue::U64(u64::from_le_bytes(buf)))
            }

            Decoder::F32NoScale => Ok(FieldValue::F32(br.read_f32()?)),

            Decoder::F32SimulationTime => {
                let ticks = br.read_uvarint32()?;
                Ok(FieldValue::F32(ticks as f32 * ctx.tick_interval))
            }

            Decoder::F32Coord => Ok(FieldValue::F32(br.read_bitcoord()?)),

            Decoder::F32Normal => Ok(FieldValue::F32(br.read_bitnormal()?)),

            Decoder::F32Quantized(qf) => Ok(FieldValue::F32(qf.decode(br)?)),

            Decoder::Ammo => {
                let raw = br.read_uvarint32()?;
                Ok(FieldValue::I32(if raw > 0 { (raw - 1) as i32 } else { 0 }))
            }

            Decoder::String => {
                ctx.string_buf.clear();
                br.read_string_raw(&mut ctx.string_buf)?;
                Ok(FieldValue::String(ctx.string_buf.clone()))
            }

            Decoder::Vector2(inner) => {
                let x = inner.decode_f32(ctx, br)?;
                let y = inner.decode_f32(ctx, br)?;
                Ok(FieldValue::Vector2([x, y]))
            }

            Decoder::Vector3(inner) => {
                let x = inner.decode_f32(ctx, br)?;
                let y = inner.decode_f32(ctx, br)?;
                let z = inner.decode_f32(ctx, br)?;
                Ok(FieldValue::Vector3([x, y, z]))
            }

            Decoder::Vector3Normal => Ok(FieldValue::Vector3(br.read_bitvec3normal()?)),

            Decoder::FloatVecN { count, inner } => {
                let mut v = Vec::with_capacity(*count);
                for _ in 0..*count {
                    v.push(inner.decode_f32(ctx, br)?);
                }
                Ok(FieldValue::FloatVector(v))
            }

            Decoder::BinaryBlock => {
                let n = br.read_uvarint32()? as usize;
                ctx.string_buf.clear();
                ctx.string_buf.resize(n, 0);
                br.read_bytes(&mut ctx.string_buf)?;
                Ok(FieldValue::String(ctx.string_buf.clone()))
            }

            Decoder::Poly => {
                let present = br.read_bool()?;
                let _poly_type_index = br.read_ubitvar()?;
                Ok(FieldValue::Bool(present))
            }

            Decoder::Vector4(inner) => {
                let x = inner.decode_f32(ctx, br)?;
                let y = inner.decode_f32(ctx, br)?;
                let z = inner.decode_f32(ctx, br)?;
                let w = inner.decode_f32(ctx, br)?;
                Ok(FieldValue::Vector4([x, y, z, w]))
            }

            Decoder::QAnglePrecise => {
                // CS2 `qangle_precise`: each present component is a 20-bit angle
                // re-centred to [-180, 180) via the `- 180` offset.
                let mut v = [0.0f32; 3];
                let rx = br.read_bool()?;
                let ry = br.read_bool()?;
                let rz = br.read_bool()?;
                if rx {
                    v[0] = br.read_bitangle(20)? - 180.0;
                }
                if ry {
                    v[1] = br.read_bitangle(20)? - 180.0;
                }
                if rz {
                    v[2] = br.read_bitangle(20)? - 180.0;
                }
                Ok(FieldValue::QAngle(v))
            }

            Decoder::QAngleBitCount { bit_count } => {
                let x = br.read_bitangle(*bit_count)?;
                let y = br.read_bitangle(*bit_count)?;
                let z = br.read_bitangle(*bit_count)?;
                Ok(FieldValue::QAngle([x, y, z]))
            }

            Decoder::QAngleCoord => Ok(FieldValue::QAngle(br.read_bitvec3coord()?)),

            Decoder::Default => Ok(FieldValue::U64(br.read_uvarint64()?)),
        }
    }

    /// Helper to decode a field value as f32 (used by vector decoders).
    fn decode_f32(&self, ctx: &mut FieldDecodeContext, br: &mut BitReader) -> Result<f32> {
        match self.decode(ctx, br)? {
            FieldValue::F32(v) => Ok(v),
            _ => Ok(0.0),
        }
    }

    /// Skip a field value without fully decoding it - just advances the bit reader.
    /// This is faster than decode() when we don't need the value.
    #[allow(clippy::only_used_in_recursion)]
    pub fn skip(&self, ctx: &mut FieldDecodeContext, br: &mut BitReader) -> Result<()> {
        match self {
            Decoder::Bool => {
                br.skip_bits(1)?;
            }

            Decoder::I64 => {
                br.skip_varint()?;
            }

            Decoder::U64 => {
                br.skip_varint()?;
            }

            Decoder::U64Fixed64 => {
                br.skip_bits(64)?;
            }

            Decoder::F32NoScale => {
                br.skip_bits(32)?;
            }

            Decoder::F32SimulationTime => {
                br.skip_varint()?;
            }

            Decoder::F32Coord => {
                br.skip_bitcoord()?;
            }

            Decoder::F32Normal => {
                br.skip_bitnormal()?;
            }

            Decoder::F32Quantized(qf) => {
                qf.skip(br)?;
            }

            Decoder::Ammo => {
                br.skip_varint()?;
            }

            Decoder::String => {
                br.skip_string()?;
            }

            Decoder::Vector2(inner) => {
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
            }

            Decoder::Vector3(inner) => {
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
            }

            Decoder::Vector3Normal => {
                br.skip_bitvec3normal()?;
            }

            Decoder::FloatVecN { count, inner } => {
                for _ in 0..*count {
                    inner.skip(ctx, br)?;
                }
            }

            Decoder::BinaryBlock => {
                let n = br.read_uvarint32()? as usize;
                br.skip_bits(n * 8)?;
            }

            Decoder::Poly => {
                br.skip_bits(1)?;
                br.read_ubitvar()?;
            }

            Decoder::Vector4(inner) => {
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
                inner.skip(ctx, br)?;
            }

            Decoder::QAnglePrecise => {
                let rx = br.read_bool()?;
                let ry = br.read_bool()?;
                let rz = br.read_bool()?;
                if rx {
                    br.skip_bits(20)?;
                }
                if ry {
                    br.skip_bits(20)?;
                }
                if rz {
                    br.skip_bits(20)?;
                }
            }

            Decoder::QAngleBitCount { bit_count } => {
                br.skip_bits(*bit_count * 3)?;
            }

            Decoder::QAngleCoord => {
                br.skip_bitvec3coord()?;
            }

            Decoder::Default => {
                br.skip_varint()?;
            }
        }
        Ok(())
    }
}

/// Special descriptor for fields that need non-standard handling
/// (arrays, pointers, or nested serializers).
#[derive(Debug, Clone)]
pub enum FieldSpecialDescriptor {
    /// Fixed-length array (e.g. `int32[4]`).
    FixedArray { length: usize },
    /// Variable-length array of a primitive type (e.g. `CNetworkUtlVectorBase<int32>`).
    DynamicArray { inner_decoder: Decoder },
    /// Variable-length array whose elements have a nested serializer.
    DynamicSerializerArray,
    /// Pointer / entity handle (encoded as a single boolean "present" flag).
    Pointer,
}

/// Metadata about how to decode a field.
#[derive(Debug, Clone)]
pub struct FieldMetadata {
    pub decoder: Decoder,
    pub special: Option<FieldSpecialDescriptor>,
}

impl Default for FieldMetadata {
    fn default() -> Self {
        Self {
            decoder: Decoder::Default,
            special: None,
        }
    }
}

impl FieldMetadata {
    pub fn is_dynamic_array(&self) -> bool {
        matches!(
            self.special,
            Some(FieldSpecialDescriptor::DynamicArray { .. })
                | Some(FieldSpecialDescriptor::DynamicSerializerArray)
        )
    }

    pub fn is_fixed_array(&self) -> bool {
        matches!(
            self.special,
            Some(FieldSpecialDescriptor::FixedArray { .. })
        )
    }

    pub fn fixed_array_length(&self) -> Option<usize> {
        match &self.special {
            Some(FieldSpecialDescriptor::FixedArray { length }) => Some(*length),
            _ => None,
        }
    }

    pub fn is_dynamic_serializer_array(&self) -> bool {
        matches!(
            self.special,
            Some(FieldSpecialDescriptor::DynamicSerializerArray)
        )
    }

    pub fn is_pointer(&self) -> bool {
        matches!(self.special, Some(FieldSpecialDescriptor::Pointer))
    }

    pub fn dynamic_array_inner_metadata(&self) -> FieldMetadata {
        match &self.special {
            Some(FieldSpecialDescriptor::DynamicArray { inner_decoder }) => FieldMetadata {
                decoder: inner_decoder.clone(),
                special: None,
            },
            _ => FieldMetadata::default(),
        }
    }
}

/// Build a float decoder based on field properties.
fn build_f32_decoder(
    var_name: &str,
    bit_count: Option<i32>,
    low_value: Option<f32>,
    high_value: Option<f32>,
    encode_flags: Option<i32>,
    var_encoder: Option<&str>,
) -> Decoder {
    // Simulation time special case
    if var_name == "m_flSimulationTime" || var_name == "m_flAnimTime" {
        return Decoder::F32SimulationTime;
    }

    // Check var_encoder
    if let Some(encoder) = var_encoder {
        match encoder {
            "coord" => return Decoder::F32Coord,
            "normal" => return Decoder::F32Normal,
            _ => {}
        }
    }

    let bc = bit_count.unwrap_or(0);
    if bc == 0 || bc == 32 {
        return Decoder::F32NoScale;
    }

    // Quantized float
    match QuantizedFloat::new(
        bc,
        encode_flags.unwrap_or(0),
        low_value.unwrap_or(0.0),
        high_value.unwrap_or(0.0),
    ) {
        Ok(qf) => Decoder::F32Quantized(qf),
        Err(_) => Decoder::F32NoScale,
    }
}

/// Determine the [`FieldMetadata`] (decoder + special descriptor) for a serializer field.
///
/// This is the main dispatch function that maps Source 2 network field descriptions
/// to the correct binary decoder. It inspects the type string, field name, and
/// encoder hints to choose the appropriate [`Decoder`] variant and, when the field
/// represents an array or pointer, attaches a [`FieldSpecialDescriptor`].
///
/// # Parameters
///
/// * `var_type` — the Source 2 type name (e.g. `"int32"`, `"Vector"`, `"CBaseEntity*"`,
///   `"CNetworkUtlVectorBase< float32 >"`). Pointer suffix (`*`), array brackets
///   (`[N]`), and generic angle brackets (`< T >`) are all handled.
/// * `var_name` — the field name (e.g. `"m_flSimulationTime"`). Certain names trigger
///   special-case decoders.
/// * `bit_count` — optional bit width from the serializer; used for quantized floats
///   and `QAngle` variants.
/// * `low_value` / `high_value` — optional range bounds for quantized float encoding.
/// * `encode_flags` — optional flags passed to [`QuantizedFloat`] when constructing a
///   quantized decoder.
/// * `var_encoder` — optional encoder hint string (e.g. `"coord"`, `"normal"`,
///   `"qangle_precise"`, `"fixed64"`).
/// * `has_field_serializer` — `true` when the field carries a nested serializer,
///   which upgrades dynamic arrays to [`FieldSpecialDescriptor::DynamicSerializerArray`].
#[allow(clippy::too_many_arguments)]
pub fn get_field_metadata(
    var_type: &str,
    var_name: &str,
    bit_count: Option<i32>,
    low_value: Option<f32>,
    high_value: Option<f32>,
    encode_flags: Option<i32>,
    var_encoder: Option<&str>,
    has_field_serializer: bool,
) -> FieldMetadata {
    // CS2 name-based special case: clip ammo is transmitted as `ammo + 1`
    // regardless of the field's declared integer type.
    if var_name == "m_iClip1" {
        return FieldMetadata {
            decoder: Decoder::Ammo,
            special: None,
        };
    }

    // Parse the type to determine category
    let trimmed = var_type.trim();

    // Pointer types
    if trimmed.ends_with('*') {
        return FieldMetadata {
            decoder: Decoder::Bool,
            special: Some(FieldSpecialDescriptor::Pointer),
        };
    }

    // Array types: type[length]
    if let Some(bracket_pos) = trimmed.find('[')
        && trimmed.ends_with(']')
    {
        let base = trimmed[..bracket_pos].trim();
        let len_str = trimmed[bracket_pos + 1..trimmed.len() - 1].trim();

        // char[N] is a string
        if base == "char" {
            return FieldMetadata {
                decoder: Decoder::String,
                special: None,
            };
        }

        let length = len_str.parse::<usize>().unwrap_or(match len_str {
            "MAX_ABILITY_DRAFT_ABILITIES" => 48,
            "DOTA_ABILITY_DRAFT_HEROES_PER_GAME" => 10,
            _ => 64,
        });

        let inner = get_field_metadata(
            base,
            var_name,
            bit_count,
            low_value,
            high_value,
            encode_flags,
            var_encoder,
            has_field_serializer,
        );

        return FieldMetadata {
            decoder: inner.decoder,
            special: Some(FieldSpecialDescriptor::FixedArray { length }),
        };
    }

    // Generic/template types: CNetworkUtlVectorBase< T >
    if let Some(angle_pos) = trimmed.find('<')
        && let Some(close_pos) = trimmed.rfind('>')
    {
        let base = trimmed[..angle_pos].trim();
        let inner_type = trimmed[angle_pos + 1..close_pos].trim();

        let is_vector_base = matches!(
            base,
            "CNetworkUtlVectorBase" | "CUtlVectorEmbeddedNetworkVar" | "CUtlVector"
        );

        if is_vector_base {
            if has_field_serializer {
                return FieldMetadata {
                    decoder: Decoder::U64,
                    special: Some(FieldSpecialDescriptor::DynamicSerializerArray),
                };
            }

            let inner = get_field_metadata(
                inner_type,
                var_name,
                bit_count,
                low_value,
                high_value,
                encode_flags,
                var_encoder,
                has_field_serializer,
            );

            return FieldMetadata {
                decoder: Decoder::U64,
                special: Some(FieldSpecialDescriptor::DynamicArray {
                    inner_decoder: inner.decoder,
                }),
            };
        }

        // For non-vector templates, decode as the base type
        return get_field_metadata(
            base,
            var_name,
            bit_count,
            low_value,
            high_value,
            encode_flags,
            var_encoder,
            has_field_serializer,
        );
    }

    // Identify the base type
    match trimmed {
        // Primitives
        "int8" | "int16" | "int32" | "int64" => FieldMetadata {
            decoder: Decoder::I64,
            special: None,
        },

        "bool" => FieldMetadata {
            decoder: Decoder::Bool,
            special: None,
        },

        "float32" | "CNetworkedQuantizedFloat" | "GameTime_t" => {
            let decoder = build_f32_decoder(
                var_name,
                bit_count,
                low_value,
                high_value,
                encode_flags,
                var_encoder,
            );
            FieldMetadata {
                decoder,
                special: None,
            }
        }

        // Pointer types: entity body/component handles transmitted as a
        // single boolean "present" flag on the wire.
        "CBodyComponentDCGBaseAnimating"
        | "CBodyComponentBaseAnimating"
        | "CBodyComponentBaseAnimatingOverlay"
        | "CBodyComponentBaseModelEntity"
        | "CBodyComponent"
        | "CBodyComponentSkeletonInstance"
        | "CBodyComponentPoint"
        | "CLightComponent"
        | "CRenderComponent"
        | "C_BodyComponentBaseAnimating"
        | "C_BodyComponentBaseAnimatingOverlay"
        | "CPhysicsComponent" => FieldMetadata {
            decoder: Decoder::Bool,
            special: Some(FieldSpecialDescriptor::Pointer),
        },

        // String types
        "CUtlSymbolLarge" | "CUtlString" | "CGlobalSymbol" | "char" => FieldMetadata {
            decoder: Decoder::String,
            special: None,
        },

        // Length-prefixed byte blob.
        "CUtlBinaryBlock" => FieldMetadata {
            decoder: Decoder::BinaryBlock,
            special: None,
        },

        // Wide float vectors (more than 4 components).
        "Quaternion" | "CTransform" => {
            let count = if trimmed == "CTransform" { 6 } else { 4 };
            let inner = build_f32_decoder(
                var_name,
                bit_count,
                low_value,
                high_value,
                encode_flags,
                var_encoder,
            );
            FieldMetadata {
                decoder: Decoder::FloatVecN {
                    count,
                    inner: Box::new(inner),
                },
                special: None,
            }
        }

        // Angle type. CS2 chooses the QAngle decoder purely from the
        // `qangle_precise` encoder and the bit count (there is no distinct
        // pitch/yaw form): precise → per-component 20-bit re-centred angles;
        // non-zero bit count → three fixed-width angles; otherwise a coord
        // triple gated by three presence bits.
        "QAngle" => {
            let bc = bit_count.unwrap_or(0) as usize;
            let decoder = if var_encoder == Some("qangle_precise") {
                Decoder::QAnglePrecise
            } else if bc != 0 {
                Decoder::QAngleBitCount { bit_count: bc }
            } else {
                Decoder::QAngleCoord
            };
            FieldMetadata {
                decoder,
                special: None,
            }
        }

        // Vector types
        "Vector" | "VectorWS" => {
            if var_encoder == Some("normal") {
                FieldMetadata {
                    decoder: Decoder::Vector3Normal,
                    special: None,
                }
            } else {
                let inner = build_f32_decoder(
                    var_name,
                    bit_count,
                    low_value,
                    high_value,
                    encode_flags,
                    var_encoder,
                );
                FieldMetadata {
                    decoder: Decoder::Vector3(Box::new(inner)),
                    special: None,
                }
            }
        }

        "Vector2D" => {
            let inner = build_f32_decoder(
                var_name,
                bit_count,
                low_value,
                high_value,
                encode_flags,
                var_encoder,
            );
            FieldMetadata {
                decoder: Decoder::Vector2(Box::new(inner)),
                special: None,
            }
        }

        "Vector4D" => {
            let inner = build_f32_decoder(
                var_name,
                bit_count,
                low_value,
                high_value,
                encode_flags,
                var_encoder,
            );
            FieldMetadata {
                decoder: Decoder::Vector4(Box::new(inner)),
                special: None,
            }
        }

        // Dynamic serializer arrays (special cases)
        "m_SpeechBubbles" | "DOTA_CombatLogQueryProgress" => FieldMetadata {
            decoder: Decoder::U64,
            special: Some(FieldSpecialDescriptor::DynamicSerializerArray),
        },

        // Default: unsigned integer
        _ => {
            let decoder = if var_encoder == Some("fixed64") {
                Decoder::U64Fixed64
            } else {
                Decoder::U64
            };
            FieldMetadata {
                decoder,
                special: None,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::BitReader;

    fn meta(var_type: &str, var_name: &str) -> FieldMetadata {
        get_field_metadata(var_type, var_name, None, None, None, None, None, false)
    }

    #[allow(clippy::too_many_arguments)]
    fn meta_full(
        var_type: &str,
        var_name: &str,
        bit_count: Option<i32>,
        low: Option<f32>,
        high: Option<f32>,
        encode_flags: Option<i32>,
        var_encoder: Option<&str>,
        has_fs: bool,
    ) -> FieldMetadata {
        get_field_metadata(
            var_type,
            var_name,
            bit_count,
            low,
            high,
            encode_flags,
            var_encoder,
            has_fs,
        )
    }

    // ── get_field_metadata dispatch ──

    #[test]
    fn pointer_type() {
        let m = meta("CBaseEntity*", "m_hOwner");
        assert!(matches!(m.decoder, Decoder::Bool));
        assert!(m.is_pointer());
    }

    #[test]
    fn bool_type() {
        let m = meta("bool", "m_bActive");
        assert!(matches!(m.decoder, Decoder::Bool));
        assert!(m.special.is_none());
    }

    #[test]
    fn int32_type() {
        let m = meta("int32", "m_iHealth");
        assert!(matches!(m.decoder, Decoder::I64));
    }

    #[test]
    fn float32_no_scale() {
        let m = meta("float32", "m_flValue");
        assert!(matches!(m.decoder, Decoder::F32NoScale));
    }

    #[test]
    fn simulation_time() {
        let m = meta("float32", "m_flSimulationTime");
        assert!(matches!(m.decoder, Decoder::F32SimulationTime));
    }

    #[test]
    fn coord_encoder() {
        let m = meta_full(
            "float32",
            "m_x",
            None,
            None,
            None,
            None,
            Some("coord"),
            false,
        );
        assert!(matches!(m.decoder, Decoder::F32Coord));
    }

    #[test]
    fn quantized_float() {
        let m = meta_full(
            "float32",
            "m_val",
            Some(8),
            Some(0.0),
            Some(255.0),
            None,
            None,
            false,
        );
        assert!(matches!(m.decoder, Decoder::F32Quantized(_)));
    }

    #[test]
    fn string_utl_symbol() {
        let m = meta("CUtlSymbolLarge", "m_iszName");
        assert!(matches!(m.decoder, Decoder::String));
    }

    #[test]
    fn char_array_is_string() {
        let m = meta("char[256]", "m_szName");
        assert!(matches!(m.decoder, Decoder::String));
        assert!(!m.is_fixed_array());
    }

    #[test]
    fn int32_array_is_fixed_array() {
        let m = meta("int32[4]", "m_values");
        assert!(m.is_fixed_array());
        assert_eq!(m.fixed_array_length(), Some(4));
    }

    #[test]
    fn dynamic_array_without_serializer() {
        let m = meta("CNetworkUtlVectorBase< int32 >", "m_items");
        assert!(m.is_dynamic_array());
        assert!(!m.is_dynamic_serializer_array());
    }

    #[test]
    fn dynamic_serializer_array() {
        let m = meta_full(
            "CNetworkUtlVectorBase< SomeType >",
            "m_items",
            None,
            None,
            None,
            None,
            None,
            true,
        );
        assert!(m.is_dynamic_serializer_array());
    }

    #[test]
    fn qangle_no_encoder_no_bits() {
        let m = meta("QAngle", "m_angle");
        assert!(matches!(m.decoder, Decoder::QAngleCoord));
    }

    #[test]
    fn qangle_with_bitcount() {
        let m = meta_full("QAngle", "m_angle", Some(16), None, None, None, None, false);
        assert!(matches!(
            m.decoder,
            Decoder::QAngleBitCount { bit_count: 16 }
        ));
    }

    #[test]
    fn qangle_precise() {
        let m = meta_full(
            "QAngle",
            "m_angle",
            Some(10),
            None,
            None,
            None,
            Some("qangle_precise"),
            false,
        );
        assert!(matches!(m.decoder, Decoder::QAnglePrecise));
    }

    #[test]
    fn clip1_is_ammo_decoder() {
        // `m_iClip1` is name-special-cased regardless of its declared type.
        let m = meta("uint16", "m_iClip1");
        assert!(matches!(m.decoder, Decoder::Ammo));
        assert!(m.special.is_none());
    }

    #[test]
    fn binary_block_type() {
        let m = meta("CUtlBinaryBlock", "m_topology");
        assert!(matches!(m.decoder, Decoder::BinaryBlock));
    }

    #[test]
    fn quaternion_and_transform_are_float_vectors() {
        assert!(matches!(
            meta("Quaternion", "m_q").decoder,
            Decoder::FloatVecN { count: 4, .. }
        ));
        assert!(matches!(
            meta("CTransform", "m_t").decoder,
            Decoder::FloatVecN { count: 6, .. }
        ));
    }

    #[test]
    fn bare_char_is_string() {
        assert!(matches!(meta("char", "m_c").decoder, Decoder::String));
    }

    #[test]
    fn decode_ammo_subtracts_one() {
        // Ammo transmits `actual + 1` as a varint; value 6 → 5.
        let data = [0x06];
        let mut br = BitReader::new(&data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::Ammo.decode(&mut ctx, &mut br).unwrap();
        assert!(matches!(val, FieldValue::I32(5)));
    }

    #[test]
    fn decode_ammo_zero_stays_zero() {
        let data = [0x00];
        let mut br = BitReader::new(&data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::Ammo.decode(&mut ctx, &mut br).unwrap();
        assert!(matches!(val, FieldValue::I32(0)));
    }

    #[test]
    fn decode_binary_block_reads_len_then_bytes() {
        // varint length 3, then 3 bytes "abc", then a trailing byte.
        let data = [0x03, b'a', b'b', b'c', 0xFF];
        let mut br = BitReader::new(&data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::BinaryBlock.decode(&mut ctx, &mut br).unwrap();
        match val {
            FieldValue::String(bytes) => assert_eq!(&bytes, b"abc"),
            other => panic!("expected String, got {other:?}"),
        }
        // Cursor should sit exactly on the trailing byte (32 bits consumed).
        assert_eq!(br.position(), 32);
    }

    #[test]
    fn decode_poly_reads_bool_and_ubitvar() {
        // presence bit 1, then a 6-bit ubitvar (top two bits 00 → 6-bit value).
        let data = [0b0000_0011];
        let mut br = BitReader::new(&data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::Poly.decode(&mut ctx, &mut br).unwrap();
        assert!(matches!(val, FieldValue::Bool(true)));
        // 1 bit (bool) + 6 bits (ubitvar) consumed.
        assert_eq!(br.position(), 7);
    }

    // ── Decoder::decode with BitReader ──

    #[test]
    fn decode_bool_from_1bit() {
        let data = [0x01];
        let mut br = BitReader::new(&data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::Bool.decode(&mut ctx, &mut br).unwrap();
        assert!(matches!(val, FieldValue::Bool(true)));
    }

    #[test]
    fn decode_f32_no_scale() {
        let bytes = 1.5f32.to_le_bytes();
        let mut br = BitReader::new(&bytes);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::F32NoScale.decode(&mut ctx, &mut br).unwrap();
        if let FieldValue::F32(f) = val {
            assert!((f - 1.5).abs() < f32::EPSILON);
        } else {
            panic!("expected F32");
        }
    }

    #[test]
    fn decode_string_null_terminated() {
        let data = b"hello\0";
        let mut br = BitReader::new(data);
        let mut ctx = FieldDecodeContext::new(1.0 / 64.0);
        let val = Decoder::String.decode(&mut ctx, &mut br).unwrap();
        if let FieldValue::String(s) = val {
            assert_eq!(&s, b"hello");
        } else {
            panic!("expected String");
        }
    }

    // ── FieldMetadata helpers ──

    #[test]
    fn field_metadata_helpers() {
        let dyn_arr = FieldMetadata {
            decoder: Decoder::U64,
            special: Some(FieldSpecialDescriptor::DynamicArray {
                inner_decoder: Decoder::I64,
            }),
        };
        assert!(dyn_arr.is_dynamic_array());
        assert!(!dyn_arr.is_fixed_array());
        assert!(!dyn_arr.is_pointer());

        let fixed = FieldMetadata {
            decoder: Decoder::I64,
            special: Some(FieldSpecialDescriptor::FixedArray { length: 8 }),
        };
        assert!(fixed.is_fixed_array());
        assert_eq!(fixed.fixed_array_length(), Some(8));

        let ptr = FieldMetadata {
            decoder: Decoder::Bool,
            special: Some(FieldSpecialDescriptor::Pointer),
        };
        assert!(ptr.is_pointer());
    }
}

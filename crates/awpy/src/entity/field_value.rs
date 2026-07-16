use std::fmt;

use crate::error::FieldValueConversionError;

/// Represents a decoded entity field value from the demo's entity system.
///
/// Each variant corresponds to a Source 2 network field type. The variant
/// chosen at runtime depends on the field's serializer metadata.
#[derive(Clone)]
pub enum FieldValue {
    Bool(bool),
    I32(i32),
    I64(i64),
    U32(u32),
    U64(u64),
    F32(f32),
    /// Raw byte string. Stored as `Vec<u8>` rather than `std::string::String`
    /// because some Source 2 strings are not guaranteed to be valid UTF-8.
    String(Vec<u8>),
    Vector2([f32; 2]),
    Vector3([f32; 3]),
    Vector4([f32; 4]),
    /// Arbitrary-length float vector, for multi-component types that don't fit
    /// the fixed vectors above (e.g. `Quaternion` = 4, `CTransform` = 6).
    FloatVector(Vec<f32>),
    /// Euler angles (pitch, yaw, roll) in degrees.
    QAngle([f32; 3]),
}

impl fmt::Debug for FieldValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Bool(v) => write!(f, "{v}"),
            Self::I32(v) => write!(f, "{v}"),
            Self::I64(v) => write!(f, "{v}"),
            Self::U32(v) => write!(f, "{v}"),
            Self::U64(v) => write!(f, "{v}"),
            Self::F32(v) => write!(f, "{v}"),
            Self::String(v) => write!(f, "{}", String::from_utf8_lossy(v)),
            Self::FloatVector(v) => write!(f, "{v:?}"),
            Self::Vector2(v) => write!(f, "[{}, {}]", v[0], v[1]),
            Self::Vector3(v) => write!(f, "[{}, {}, {}]", v[0], v[1], v[2]),
            Self::Vector4(v) => write!(f, "[{}, {}, {}, {}]", v[0], v[1], v[2], v[3]),
            Self::QAngle(v) => write!(f, "QAngle({}, {}, {})", v[0], v[1], v[2]),
        }
    }
}

impl fmt::Display for FieldValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(self, f)
    }
}

impl serde::Serialize for FieldValue {
    fn serialize<S: serde::Serializer>(
        &self,
        serializer: S,
    ) -> std::result::Result<S::Ok, S::Error> {
        match self {
            Self::Bool(v) => serializer.serialize_bool(*v),
            Self::I32(v) => serializer.serialize_i32(*v),
            Self::I64(v) => serializer.serialize_i64(*v),
            Self::U32(v) => serializer.serialize_u32(*v),
            Self::U64(v) => serializer.serialize_u64(*v),
            Self::F32(v) => serializer.serialize_f32(*v),
            Self::String(v) => serializer.serialize_str(&String::from_utf8_lossy(v)),
            Self::Vector2(v) => v.serialize(serializer),
            Self::Vector3(v) => v.serialize(serializer),
            Self::Vector4(v) => v.serialize(serializer),
            Self::FloatVector(v) => v.serialize(serializer),
            Self::QAngle(v) => v.serialize(serializer),
        }
    }
}

/// Generates `TryFrom<FieldValue>` for signed integer types.
/// Accepts `I32` and `I64` variants, with range checking via `try_from`.
macro_rules! impl_try_from_signed {
    ($($ty:ty),+) => {
        $(
            impl TryFrom<FieldValue> for $ty {
                type Error = FieldValueConversionError;
                fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
                    match v {
                        FieldValue::I32(val) => <$ty>::try_from(val).map_err(|_| FieldValueConversionError),
                        FieldValue::I64(val) => <$ty>::try_from(val).map_err(|_| FieldValueConversionError),
                        _ => Err(FieldValueConversionError),
                    }
                }
            }
        )+
    }
}

/// Generates `TryFrom<FieldValue>` for unsigned integer types.
/// Accepts `U32` and `U64` variants, with range checking via `try_from`.
macro_rules! impl_try_from_unsigned {
    ($($ty:ty),+) => {
        $(
            impl TryFrom<FieldValue> for $ty {
                type Error = FieldValueConversionError;
                fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
                    match v {
                        FieldValue::U32(val) => <$ty>::try_from(val).map_err(|_| FieldValueConversionError),
                        FieldValue::U64(val) => <$ty>::try_from(val).map_err(|_| FieldValueConversionError),
                        _ => Err(FieldValueConversionError),
                    }
                }
            }
        )+
    }
}

impl_try_from_signed!(i8, i16, i32, i64);
impl_try_from_unsigned!(u8, u16, u32, u64);

impl TryFrom<FieldValue> for f32 {
    type Error = FieldValueConversionError;
    fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
        match v {
            FieldValue::F32(val) => Ok(val),
            _ => Err(FieldValueConversionError),
        }
    }
}

impl TryFrom<FieldValue> for bool {
    type Error = FieldValueConversionError;
    fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
        match v {
            FieldValue::Bool(val) => Ok(val),
            _ => Err(FieldValueConversionError),
        }
    }
}

impl TryFrom<FieldValue> for [f32; 2] {
    type Error = FieldValueConversionError;
    fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
        match v {
            FieldValue::Vector2(val) => Ok(val),
            _ => Err(FieldValueConversionError),
        }
    }
}

impl TryFrom<FieldValue> for [f32; 3] {
    type Error = FieldValueConversionError;
    fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
        match v {
            FieldValue::Vector3(val) | FieldValue::QAngle(val) => Ok(val),
            _ => Err(FieldValueConversionError),
        }
    }
}

impl TryFrom<FieldValue> for [f32; 4] {
    type Error = FieldValueConversionError;
    fn try_from(v: FieldValue) -> std::result::Result<Self, Self::Error> {
        match v {
            FieldValue::Vector4(val) => Ok(val),
            _ => Err(FieldValueConversionError),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── TryFrom conversions ──

    #[test]
    fn try_from_i32_to_i32() {
        let v = FieldValue::I32(42);
        assert_eq!(i32::try_from(v).unwrap(), 42);
    }

    #[test]
    fn try_from_i64_to_i32() {
        let v = FieldValue::I64(100);
        assert_eq!(i32::try_from(v).unwrap(), 100);
    }

    #[test]
    fn try_from_u32_to_u32() {
        let v = FieldValue::U32(999);
        assert_eq!(u32::try_from(v).unwrap(), 999);
    }

    #[test]
    fn try_from_u64_to_u16() {
        let v = FieldValue::U64(65535);
        assert_eq!(u16::try_from(v).unwrap(), 65535);
    }

    #[test]
    fn try_from_f32() {
        let v = FieldValue::F32(1.5);
        assert!((f32::try_from(v).unwrap() - 1.5).abs() < f32::EPSILON);
    }

    #[test]
    fn try_from_bool() {
        let v = FieldValue::Bool(true);
        assert!(bool::try_from(v).unwrap());
    }

    #[test]
    fn try_from_vector2() {
        let v = FieldValue::Vector2([1.0, 2.0]);
        assert_eq!(<[f32; 2]>::try_from(v).unwrap(), [1.0, 2.0]);
    }

    #[test]
    fn try_from_vector3() {
        let v = FieldValue::Vector3([1.0, 2.0, 3.0]);
        assert_eq!(<[f32; 3]>::try_from(v).unwrap(), [1.0, 2.0, 3.0]);
    }

    #[test]
    fn try_from_vector4() {
        let v = FieldValue::Vector4([1.0, 2.0, 3.0, 4.0]);
        assert_eq!(<[f32; 4]>::try_from(v).unwrap(), [1.0, 2.0, 3.0, 4.0]);
    }

    #[test]
    fn try_from_qangle_to_f32_3() {
        let v = FieldValue::QAngle([10.0, 20.0, 30.0]);
        assert_eq!(<[f32; 3]>::try_from(v).unwrap(), [10.0, 20.0, 30.0]);
    }

    #[test]
    fn try_from_i64_overflow_to_i8() {
        let v = FieldValue::I64(200);
        assert!(i8::try_from(v).is_err());
    }

    #[test]
    fn try_from_u32_to_signed_fails() {
        let v = FieldValue::U32(1);
        assert!(i32::try_from(v).is_err());
    }

    #[test]
    fn try_from_i32_to_unsigned_fails() {
        let v = FieldValue::I32(1);
        assert!(u32::try_from(v).is_err());
    }

    // ── Debug / Display formatting ──

    #[test]
    fn debug_bool() {
        assert_eq!(format!("{:?}", FieldValue::Bool(true)), "true");
    }

    #[test]
    fn debug_i32() {
        assert_eq!(format!("{:?}", FieldValue::I32(-42)), "-42");
    }

    #[test]
    fn debug_string_utf8() {
        let v = FieldValue::String(b"hello".to_vec());
        assert_eq!(format!("{:?}", v), "hello");
    }

    #[test]
    fn debug_string_invalid_utf8_no_panic() {
        let v = FieldValue::String(vec![0xFF, 0xFE]);
        let s = format!("{:?}", v);
        assert!(!s.is_empty());
    }

    #[test]
    fn debug_vector3() {
        let v = FieldValue::Vector3([1.0, 2.0, 3.0]);
        assert_eq!(format!("{:?}", v), "[1, 2, 3]");
    }

    #[test]
    fn debug_qangle() {
        let v = FieldValue::QAngle([1.0, 2.0, 3.0]);
        assert!(format!("{:?}", v).starts_with("QAngle("));
    }

    #[test]
    fn display_delegates_to_debug() {
        let v = FieldValue::Bool(false);
        assert_eq!(format!("{}", v), format!("{:?}", v));
    }

    // ── Serialize ──

    #[test]
    fn serialize_bool_and_numbers() {
        let b = serde_json::to_value(FieldValue::Bool(true)).unwrap();
        assert_eq!(b, serde_json::json!(true));

        let n = serde_json::to_value(FieldValue::I32(-7)).unwrap();
        assert_eq!(n, serde_json::json!(-7));

        let u = serde_json::to_value(FieldValue::U32(42)).unwrap();
        assert_eq!(u, serde_json::json!(42));
    }

    #[test]
    fn serialize_string_and_vector() {
        let s = serde_json::to_value(FieldValue::String(b"hi".to_vec())).unwrap();
        assert_eq!(s, serde_json::json!("hi"));

        let v = serde_json::to_value(FieldValue::Vector3([1.0, 2.0, 3.0])).unwrap();
        assert!(v.is_array());
        assert_eq!(v.as_array().unwrap().len(), 3);
    }
}

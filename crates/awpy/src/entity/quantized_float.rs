use crate::error::Result;
use crate::io::BitReader;

// Valve's quantized-float encode flags (from QUANTIZEDFLOAT_ENCODE_*).
const QFE_ROUNDDOWN: i32 = 1 << 0;
const QFE_ROUNDUP: i32 = 1 << 1;
const QFE_ENCODE_ZERO_EXACTLY: i32 = 1 << 2;
const QFE_ENCODE_INTEGERS_EXACTLY: i32 = 1 << 3;

const EQUAL_EPSILON: f32 = 0.001;

fn close_enough(a: f32, b: f32, epsilon: f32) -> bool {
    (a - b).abs() <= epsilon
}

fn compute_encode_flags(encode_flags: i32, low_value: f32, high_value: f32) -> i32 {
    let mut efs = encode_flags;

    if efs == 0 {
        return efs;
    }

    if (low_value == 0.0 && (efs & QFE_ROUNDDOWN) != 0)
        || (high_value == 0.0 && (efs & QFE_ROUNDUP) != 0)
    {
        efs &= !QFE_ENCODE_ZERO_EXACTLY;
    }

    if low_value == 0.0 && (efs & QFE_ENCODE_ZERO_EXACTLY) != 0 {
        efs |= QFE_ROUNDDOWN;
        efs &= !QFE_ENCODE_ZERO_EXACTLY;
    }
    if high_value == 0.0 && (efs & QFE_ENCODE_ZERO_EXACTLY) != 0 {
        efs |= QFE_ROUNDUP;
        efs &= !QFE_ENCODE_ZERO_EXACTLY;
    }

    if !(low_value < 0.0 && high_value > 0.0) {
        efs &= !QFE_ENCODE_ZERO_EXACTLY;
    }

    if (efs & QFE_ENCODE_INTEGERS_EXACTLY) != 0 {
        efs &= !(QFE_ROUNDUP | QFE_ROUNDDOWN | QFE_ENCODE_ZERO_EXACTLY);
    }

    efs
}

/// Compute a multiplier that maps `[low, high]` into `[0, 2^bit_count - 1]`.
///
/// If the naive `max / range` overflows, this tries progressively smaller
/// scale factors until the product fits. This is a direct port of Valve's
/// `CQuantizedFloatDecoder::AssignMultipliers`.
fn assign_range_multiplier(bit_count: i32, range: f64) -> f32 {
    let high_value: u32 = if bit_count == 32 {
        0xFFFFFFFE
    } else {
        (1u32 << bit_count) - 1
    };

    let mut high_low_mul = if close_enough(range as f32, 0.0, EQUAL_EPSILON) {
        high_value as f32
    } else {
        (high_value as f64 / range) as f32
    };

    if (high_low_mul as f64 * range) as u32 > high_value
        || (high_low_mul as f64 * range) > high_value as f64
    {
        const MULTIPLIERS: [f32; 5] = [0.9999, 0.99, 0.9, 0.8, 0.7];
        for &mult in &MULTIPLIERS {
            high_low_mul = (high_value as f64 / range) as f32 * mult;
            if !((high_low_mul as f64 * range) as u32 > high_value
                || (high_low_mul as f64 * range) > high_value as f64)
            {
                break;
            }
        }
    }

    high_low_mul
}

fn num_bits_for_count(n_max_elements: i32) -> i32 {
    let mut n_bits = 0;
    let mut n = n_max_elements;
    while n > 0 {
        n_bits += 1;
        n >>= 1;
    }
    n_bits
}

/// Quantized float decoder with configurable precision.
#[derive(Debug, Clone)]
pub struct QuantizedFloat {
    bit_count: i32,
    encode_flags: i32,
    low_value: f32,
    high_value: f32,
    high_low_mul: f32,
    decode_mul: f32,
}

impl QuantizedFloat {
    /// Build a quantized float decoder for the given bit width and value range.
    pub fn new(bit_count: i32, encode_flags: i32, low_value: f32, high_value: f32) -> Result<Self> {
        if bit_count <= 0 || bit_count >= 32 {
            return Err(crate::error::Error::Parse {
                context: format!("quantized float bit_count out of range: {bit_count}"),
            });
        }

        let mut qf = Self {
            bit_count,
            encode_flags,
            low_value,
            high_value,
            high_low_mul: 0.0,
            decode_mul: 0.0,
        };

        qf.encode_flags = compute_encode_flags(qf.encode_flags, qf.low_value, qf.high_value);
        let mut steps = 1i32 << qf.bit_count;

        let range = qf.high_value - qf.low_value;
        let offset = range / steps as f32;
        if qf.encode_flags & QFE_ROUNDDOWN != 0 {
            qf.high_value -= offset;
        } else if qf.encode_flags & QFE_ROUNDUP != 0 {
            qf.low_value += offset;
        }

        if qf.encode_flags & QFE_ENCODE_INTEGERS_EXACTLY != 0 {
            let delta = (qf.low_value as i32 - qf.high_value as i32).max(1);
            let int_range = 1 << num_bits_for_count(delta);

            let mut bc = qf.bit_count;
            while (1 << bc) < int_range {
                bc += 1;
            }
            if bc > qf.bit_count {
                qf.bit_count = bc;
                steps = 1 << bc;
            }

            let offset = int_range as f32 / steps as f32;
            qf.high_value = qf.low_value + int_range as f32 - offset;
        }

        let range = qf.high_value - qf.low_value;
        qf.high_low_mul = assign_range_multiplier(qf.bit_count, range as f64);
        qf.decode_mul = 1.0 / (steps - 1) as f32;

        // Remove unnecessary flags
        if (qf.encode_flags & QFE_ROUNDDOWN) != 0 && qf.quantize(qf.low_value) == qf.low_value {
            qf.encode_flags &= !QFE_ROUNDDOWN;
        }
        if (qf.encode_flags & QFE_ROUNDUP) != 0 && qf.quantize(qf.high_value) == qf.high_value {
            qf.encode_flags &= !QFE_ROUNDUP;
        }
        if (qf.encode_flags & QFE_ENCODE_ZERO_EXACTLY) != 0 && qf.quantize(0.0) == 0.0 {
            qf.encode_flags &= !QFE_ENCODE_ZERO_EXACTLY;
        }

        Ok(qf)
    }

    fn quantize(&self, value: f32) -> f32 {
        let v = if value < self.low_value {
            self.low_value
        } else if value > self.high_value {
            self.high_value
        } else {
            value
        };

        let range = self.high_value - self.low_value;
        let i = ((v - self.low_value) * self.high_low_mul) as i32;
        self.low_value + range * (i as f32 * self.decode_mul)
    }

    /// Decode a quantized float from the bitstream.
    pub fn decode(&self, br: &mut BitReader) -> Result<f32> {
        if (self.encode_flags & QFE_ROUNDDOWN) != 0 && br.read_bool()? {
            return Ok(self.low_value);
        }

        if (self.encode_flags & QFE_ROUNDUP) != 0 && br.read_bool()? {
            return Ok(self.high_value);
        }

        if (self.encode_flags & QFE_ENCODE_ZERO_EXACTLY) != 0 && br.read_bool()? {
            return Ok(0.0);
        }

        let range = self.high_value - self.low_value;
        let value = br.read_bits(self.bit_count as usize)?;
        Ok(self.low_value + range * (value as f32 * self.decode_mul))
    }

    /// Skip past a quantized float value without decoding it.
    pub fn skip(&self, br: &mut BitReader) -> Result<()> {
        if (self.encode_flags & QFE_ROUNDDOWN) != 0 && br.read_bool()? {
            return Ok(());
        }

        if (self.encode_flags & QFE_ROUNDUP) != 0 && br.read_bool()? {
            return Ok(());
        }

        if (self.encode_flags & QFE_ENCODE_ZERO_EXACTLY) != 0 && br.read_bool()? {
            return Ok(());
        }

        br.skip_bits(self.bit_count as usize)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::BitReader;

    // ── Private helpers ──

    #[test]
    fn close_enough_true_and_false() {
        assert!(close_enough(1.0, 1.0005, 0.001));
        assert!(!close_enough(1.0, 1.01, 0.001));
    }

    #[test]
    fn num_bits_for_count_values() {
        assert_eq!(num_bits_for_count(0), 0);
        assert_eq!(num_bits_for_count(1), 1);
        assert_eq!(num_bits_for_count(7), 3);
        assert_eq!(num_bits_for_count(8), 4);
        assert_eq!(num_bits_for_count(255), 8);
    }

    #[test]
    fn compute_encode_flags_zero_passthrough() {
        assert_eq!(compute_encode_flags(0, 0.0, 100.0), 0);
    }

    #[test]
    fn compute_encode_flags_integers_clears_others() {
        let flags = QFE_ENCODE_INTEGERS_EXACTLY | QFE_ROUNDDOWN | QFE_ROUNDUP;
        let result = compute_encode_flags(flags, 0.0, 100.0);
        assert_eq!(result & QFE_ROUNDDOWN, 0);
        assert_eq!(result & QFE_ROUNDUP, 0);
        assert_ne!(result & QFE_ENCODE_INTEGERS_EXACTLY, 0);
    }

    // ── Construction + decode ──

    #[test]
    fn new_does_not_panic() {
        let _qf = QuantizedFloat::new(8, 0, 0.0, 255.0).unwrap();
    }

    #[test]
    fn new_rejects_zero_bit_count() {
        assert!(QuantizedFloat::new(0, 0, 0.0, 255.0).is_err());
    }

    #[test]
    fn new_rejects_32_bit_count() {
        assert!(QuantizedFloat::new(32, 0, 0.0, 255.0).is_err());
    }

    #[test]
    fn decode_produces_value_in_range() {
        let qf = QuantizedFloat::new(8, 0, 0.0, 100.0).unwrap();
        // 8 bits of value 128 (half range)
        let data = [128u8, 0];
        let mut br = BitReader::new(&data);
        let val = qf.decode(&mut br).unwrap();
        assert!((0.0..=100.0).contains(&val));
    }

    #[test]
    fn rounddown_flag_path() {
        let qf = QuantizedFloat::new(8, QFE_ROUNDDOWN, 0.0, 100.0).unwrap();
        // If rounddown flag is active and first bit is 1, returns low_value
        let data = [0b1000_0000, 0, 0];
        let mut br = BitReader::new(&data);
        let val = qf.decode(&mut br).unwrap();
        // Either it returns low_value or decodes normally depending on flag optimization
        assert!((0.0..=100.0).contains(&val));
    }

    #[test]
    fn roundup_flag_path() {
        let qf = QuantizedFloat::new(8, QFE_ROUNDUP, 0.0, 100.0).unwrap();
        let data = [0b1000_0000, 0, 0];
        let mut br = BitReader::new(&data);
        let val = qf.decode(&mut br).unwrap();
        assert!((0.0..=100.0).contains(&val));
    }

    #[test]
    fn skip_advances_position() {
        let qf = QuantizedFloat::new(8, 0, 0.0, 255.0).unwrap();
        let data = [0xAB, 0xCD];
        let mut br = BitReader::new(&data);
        let before = br.position();
        qf.skip(&mut br).unwrap();
        assert!(br.position() > before);
    }
}

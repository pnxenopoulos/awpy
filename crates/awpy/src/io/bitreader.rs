use crate::error::{Error, Result};

// Source 2 coordinate encoding constants. A coordinate is encoded as an
// optional integer part (14 bits) plus an optional fractional part (5 bits).
const COORD_INTEGER_BITS: usize = 14;
const COORD_FRACTIONAL_BITS: usize = 5;
const COORD_DENOMINATOR: f32 = (1 << COORD_FRACTIONAL_BITS) as f32;
const COORD_RESOLUTION: f32 = 1.0 / COORD_DENOMINATOR;

// Source 2 normal encoding constants. A normal component is a sign bit
// followed by an 11-bit fractional value in [0, 1].
const NORMAL_FRACTIONAL_BITS: usize = 11;
const NORMAL_DENOMINATOR: f32 = ((1 << NORMAL_FRACTIONAL_BITS) - 1) as f32;
const NORMAL_RESOLUTION: f32 = 1.0 / NORMAL_DENOMINATOR;

/// High-performance bit-level reader over a byte slice.
///
/// Uses safe unaligned 64-bit reads via `u64::from_le_bytes` for fast
/// bit extraction. Every read returns `Result<T>` with overflow checking.
pub struct BitReader<'a> {
    data: &'a [u8],
    position: usize,
    total_bits: usize,
}

impl<'a> BitReader<'a> {
    /// Create a new reader starting at bit 0 of `data`.
    #[inline]
    pub fn new(data: &'a [u8]) -> Self {
        Self {
            data,
            position: 0,
            total_bits: data.len() * 8,
        }
    }

    /// Number of bits between the cursor and the end of the buffer.
    #[inline]
    pub fn bits_remaining(&self) -> usize {
        self.total_bits.saturating_sub(self.position)
    }

    /// Current bit offset from the start of the buffer.
    #[inline]
    pub fn position(&self) -> usize {
        self.position
    }

    /// The full underlying byte slice (independent of the cursor).
    #[inline]
    pub fn data(&self) -> &'a [u8] {
        self.data
    }

    /// Read up to 64 bits. Returns the value right-aligned in a u64.
    #[inline]
    pub fn read_bits(&mut self, n: usize) -> Result<u64> {
        if n == 0 {
            return Ok(0);
        }
        if n > 64 || self.position + n > self.total_bits {
            return Err(Error::Overflow {
                needed: n,
                available: self.bits_remaining(),
            });
        }

        let value = self.peek_bits_unchecked(n);
        self.position += n;
        Ok(value)
    }

    /// Internal: peek without bounds checking.
    ///
    /// Reads a little-endian u64 from the byte at `position / 8`, shifts right by
    /// the intra-byte bit offset, and masks to `n` bits. The 8-byte window only
    /// holds `64 - bit_offset` valid bits after the shift, so a read that needs
    /// more (only possible for `n > 56` at a non-zero offset — e.g. a 64-bit read
    /// mid-stream) pulls the extra high bits from the following byte; without that
    /// they would be silently dropped.
    #[inline(always)]
    fn peek_bits_unchecked(&self, n: usize) -> u64 {
        let byte_pos = self.position / 8;
        let bit_offset = self.position % 8;
        let remaining_bytes = self.data.len() - byte_pos;

        let mut buf = [0u8; 8];
        if remaining_bytes >= 8 {
            buf.copy_from_slice(&self.data[byte_pos..byte_pos + 8]);
        } else {
            buf[..remaining_bytes]
                .copy_from_slice(&self.data[byte_pos..byte_pos + remaining_bytes]);
        }
        let low = u64::from_le_bytes(buf) >> bit_offset;
        if bit_offset + n <= 64 {
            return low & mask(n);
        }
        let taken = 64 - bit_offset;
        let hi = self.data.get(byte_pos + 8).copied().unwrap_or(0) as u64 & mask(n - taken);
        (low | (hi << taken)) & mask(n)
    }

    /// Read a single bit as a boolean.
    #[inline]
    pub fn read_bool(&mut self) -> Result<bool> {
        Ok(self.read_bits(1)? != 0)
    }

    /// Read 8 bits as a `u8`.
    #[inline]
    pub fn read_u8(&mut self) -> Result<u8> {
        Ok(self.read_bits(8)? as u8)
    }

    /// Read 32 bits as a little-endian `u32`.
    #[inline]
    pub fn read_u32(&mut self) -> Result<u32> {
        Ok(self.read_bits(32)? as u32)
    }

    /// Read 32 bits and reinterpret as an IEEE 754 `f32`.
    #[inline]
    pub fn read_f32(&mut self) -> Result<f32> {
        Ok(f32::from_bits(self.read_bits(32)? as u32))
    }

    /// Read N bytes into the provided buffer.
    pub fn read_bytes(&mut self, buf: &mut [u8]) -> Result<()> {
        let needed = buf.len() * 8;
        if self.position + needed > self.total_bits {
            return Err(Error::Overflow {
                needed,
                available: self.bits_remaining(),
            });
        }

        // Fast path: byte-aligned — direct memcpy.
        if self.position.is_multiple_of(8) {
            let byte_pos = self.position / 8;
            buf.copy_from_slice(&self.data[byte_pos..byte_pos + buf.len()]);
            self.position += needed;
            return Ok(());
        }

        // Slow path: unaligned — read byte at a time via bit extraction.
        for byte in buf.iter_mut() {
            *byte = self.peek_bits_unchecked(8) as u8;
            self.position += 8;
        }
        Ok(())
    }

    /// Read a specified number of bits into a byte buffer, filling LSB-first.
    pub fn read_bits_to_bytes(&mut self, buf: &mut [u8], bits: usize) -> Result<()> {
        let full_bytes = bits / 8;
        let remaining_bits = bits % 8;

        if remaining_bits == 0 {
            return self.read_bytes(&mut buf[..full_bytes]);
        }

        // Has trailing bits — can still fast-path the full bytes.
        if full_bytes > 0 {
            self.read_bytes(&mut buf[..full_bytes])?;
        }
        buf[full_bytes] = self.read_bits(remaining_bits)? as u8;
        Ok(())
    }

    /// Read an unsigned varint (up to 32 bits).
    pub fn read_uvarint32(&mut self) -> Result<u32> {
        let mut result: u32 = 0;
        for i in 0..5 {
            let byte = self.read_u8()? as u32;
            result |= (byte & 0x7F) << (7 * i);
            if byte & 0x80 == 0 {
                return Ok(result);
            }
        }
        Ok(result)
    }

    /// Read an unsigned varint (up to 64 bits).
    pub fn read_uvarint64(&mut self) -> Result<u64> {
        let mut result: u64 = 0;
        for i in 0..10 {
            let byte = self.read_u8()? as u64;
            result |= (byte & 0x7F) << (7 * i);
            if byte & 0x80 == 0 {
                return Ok(result);
            }
        }
        Ok(result)
    }

    /// Read a signed varint (zigzag encoded, 32-bit).
    pub fn read_varint32(&mut self) -> Result<i32> {
        let n = self.read_uvarint32()?;
        Ok(((n >> 1) as i32) ^ -((n & 1) as i32))
    }

    /// Read a signed varint (zigzag encoded, 64-bit).
    pub fn read_varint64(&mut self) -> Result<i64> {
        let n = self.read_uvarint64()?;
        Ok(((n >> 1) as i64) ^ -((n & 1) as i64))
    }

    /// Valve's variable-length unsigned integer encoding.
    ///
    /// Reads 6 bits; bits 4-5 select the total width:
    /// `00` → 6 bits, `01` → 4+4, `10` → 4+8, `11` → 4+28.
    pub fn read_ubitvar(&mut self) -> Result<u32> {
        let ret = self.read_bits(6)? as u32;
        match ret & (16 | 32) {
            16 => Ok((ret & 15) | (self.read_bits(4)? as u32) << 4),
            32 => Ok((ret & 15) | (self.read_bits(8)? as u32) << 4),
            48 => Ok((ret & 15) | (self.read_bits(28)? as u32) << 4),
            _ => Ok(ret),
        }
    }

    /// Field-path variant of ubitvar — cascading 1-bit selectors.
    ///
    /// Used exclusively for encoding field path operation indices:
    /// 2, 4, 10, 17, or 31 bits depending on which prefix bit is set.
    pub fn read_ubitvarfp(&mut self) -> Result<u32> {
        if self.read_bool()? {
            return Ok(self.read_bits(2)? as u32);
        }
        if self.read_bool()? {
            return Ok(self.read_bits(4)? as u32);
        }
        if self.read_bool()? {
            return Ok(self.read_bits(10)? as u32);
        }
        if self.read_bool()? {
            return Ok(self.read_bits(17)? as u32);
        }
        Ok(self.read_bits(31)? as u32)
    }

    /// Read a coordinate value.
    pub fn read_bitcoord(&mut self) -> Result<f32> {
        let has_int = self.read_bool()?;
        let has_frac = self.read_bool()?;

        if !has_int && !has_frac {
            return Ok(0.0);
        }

        let negative = self.read_bool()?;
        let mut value = 0.0f32;

        if has_int {
            value += self.read_bits(COORD_INTEGER_BITS)? as f32 + 1.0;
        }
        if has_frac {
            value += self.read_bits(COORD_FRACTIONAL_BITS)? as f32 * COORD_RESOLUTION;
        }

        if negative {
            value = -value;
        }

        Ok(value)
    }

    /// Read a normal component (sign + 11-bit fraction).
    pub fn read_bitnormal(&mut self) -> Result<f32> {
        let negative = self.read_bool()?;
        let frac = self.read_bits(NORMAL_FRACTIONAL_BITS)? as f32;
        let mut value = frac * NORMAL_RESOLUTION;
        if negative {
            value = -value;
        }
        Ok(value)
    }

    /// Read a 3D coordinate vector.
    pub fn read_bitvec3coord(&mut self) -> Result<[f32; 3]> {
        let has_x = self.read_bool()?;
        let has_y = self.read_bool()?;
        let has_z = self.read_bool()?;

        let x = if has_x { self.read_bitcoord()? } else { 0.0 };
        let y = if has_y { self.read_bitcoord()? } else { 0.0 };
        let z = if has_z { self.read_bitcoord()? } else { 0.0 };

        Ok([x, y, z])
    }

    /// Read a 3D normal vector (2 components + derived Z).
    pub fn read_bitvec3normal(&mut self) -> Result<[f32; 3]> {
        let has_x = self.read_bool()?;
        let has_y = self.read_bool()?;

        let x = if has_x { self.read_bitnormal()? } else { 0.0 };
        let y = if has_y { self.read_bitnormal()? } else { 0.0 };

        let z_sign = self.read_bool()?;
        let z_sq = 1.0 - x * x - y * y;
        let z = if z_sq > 0.0 { z_sq.sqrt() } else { 0.0 };
        let z = if z_sign { -z } else { z };

        Ok([x, y, z])
    }

    /// Read an angle encoded as N bits, returning degrees in [0, 360).
    pub fn read_bitangle(&mut self, n: usize) -> Result<f32> {
        let raw = self.read_bits(n)? as f32;
        let shift = (1u64 << n) as f32;
        Ok(raw * 360.0 / shift)
    }

    /// Read a string into the provided buffer, returning bytes written (excluding null).
    pub fn read_string_into(&mut self, buf: &mut [u8]) -> Result<usize> {
        let mut i = 0;
        loop {
            let b = self.read_u8()?;
            if b == 0 {
                break;
            }
            if i < buf.len() {
                buf[i] = b;
                i += 1;
            }
        }
        Ok(i)
    }

    /// Read a string as raw bytes into a Vec, returning bytes written (excluding null).
    pub fn read_string_raw(&mut self, buf: &mut Vec<u8>) -> Result<usize> {
        let start = buf.len();
        loop {
            let b = self.read_u8()?;
            if b == 0 {
                break;
            }
            buf.push(b);
        }
        Ok(buf.len() - start)
    }

    /// Skip forward by N bits.
    pub fn skip_bits(&mut self, n: usize) -> Result<()> {
        if self.position + n > self.total_bits {
            return Err(Error::Overflow {
                needed: n,
                available: self.bits_remaining(),
            });
        }
        self.position += n;
        Ok(())
    }

    /// Skip a varint without decoding it.
    pub fn skip_varint(&mut self) -> Result<()> {
        for _ in 0..10 {
            let byte = self.read_u8()?;
            if byte & 0x80 == 0 {
                return Ok(());
            }
        }
        Ok(())
    }

    /// Skip a bitcoord value.
    pub fn skip_bitcoord(&mut self) -> Result<()> {
        let has_int = self.read_bool()?;
        let has_frac = self.read_bool()?;

        if !has_int && !has_frac {
            return Ok(());
        }

        self.skip_bits(1)?; // negative flag

        if has_int {
            self.skip_bits(COORD_INTEGER_BITS)?;
        }
        if has_frac {
            self.skip_bits(COORD_FRACTIONAL_BITS)?;
        }

        Ok(())
    }

    /// Skip a bitnormal value.
    pub fn skip_bitnormal(&mut self) -> Result<()> {
        self.skip_bits(1 + NORMAL_FRACTIONAL_BITS)
    }

    /// Skip a 3D coordinate vector.
    pub fn skip_bitvec3coord(&mut self) -> Result<()> {
        let has_x = self.read_bool()?;
        let has_y = self.read_bool()?;
        let has_z = self.read_bool()?;

        if has_x {
            self.skip_bitcoord()?;
        }
        if has_y {
            self.skip_bitcoord()?;
        }
        if has_z {
            self.skip_bitcoord()?;
        }

        Ok(())
    }

    /// Skip a 3D normal vector.
    pub fn skip_bitvec3normal(&mut self) -> Result<()> {
        let has_x = self.read_bool()?;
        let has_y = self.read_bool()?;

        if has_x {
            self.skip_bitnormal()?;
        }
        if has_y {
            self.skip_bitnormal()?;
        }

        self.skip_bits(1)?; // z_sign

        Ok(())
    }

    /// Skip a null-terminated string.
    pub fn skip_string(&mut self) -> Result<()> {
        loop {
            let b = self.read_u8()?;
            if b == 0 {
                return Ok(());
            }
        }
    }
}

/// Create a bitmask with n bits set.
#[inline(always)]
fn mask(n: usize) -> u64 {
    if n >= 64 { u64::MAX } else { (1u64 << n) - 1 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_bits_wide_unaligned() {
        // A ≥58-bit read at a non-zero offset needs bits beyond the first 8-byte
        // window; the extra high bits must come from the next byte, not be dropped.
        let data: Vec<u8> = (0..16).collect();
        let full = u128::from_le_bytes(data[..16].try_into().unwrap());
        for offset in 0..8usize {
            for n in 57..=64usize {
                let mut br = BitReader::new(&data);
                if offset > 0 {
                    br.read_bits(offset).unwrap();
                }
                let got = br.read_bits(n).unwrap();
                let want = ((full >> offset) & ((1u128 << n) - 1)) as u64;
                assert_eq!(got, want, "read_bits({n}) at offset {offset}");
            }
        }
    }

    #[test]
    fn test_read_bits_basic() {
        let data = [0b10110100, 0b11001010];
        let mut br = BitReader::new(&data);

        assert_eq!(br.read_bits(1).unwrap(), 0);
        assert_eq!(br.read_bits(1).unwrap(), 0);
        assert_eq!(br.read_bits(1).unwrap(), 1);
        assert_eq!(br.read_bits(1).unwrap(), 0);
        assert_eq!(br.read_bits(1).unwrap(), 1);
        assert_eq!(br.read_bits(1).unwrap(), 1);
        assert_eq!(br.read_bits(1).unwrap(), 0);
        assert_eq!(br.read_bits(1).unwrap(), 1);
    }

    #[test]
    fn test_read_byte() {
        let data = [0xAB, 0xCD];
        let mut br = BitReader::new(&data);
        assert_eq!(br.read_u8().unwrap(), 0xAB);
        assert_eq!(br.read_u8().unwrap(), 0xCD);
    }

    #[test]
    fn test_read_across_boundary() {
        let data = [0xFF, 0x00, 0xFF];
        let mut br = BitReader::new(&data);
        br.read_bits(4).unwrap();
        let val = br.read_bits(8).unwrap();
        assert_eq!(val, 0x0F);
    }

    #[test]
    fn test_read_bool() {
        let data = [0b10000001];
        let mut br = BitReader::new(&data);
        assert!(br.read_bool().unwrap());
        assert!(!br.read_bool().unwrap());
    }

    #[test]
    fn test_overflow() {
        let data = [0xFF];
        let mut br = BitReader::new(&data);
        br.read_bits(8).unwrap();
        assert!(br.read_bits(1).is_err());
    }

    #[test]
    fn test_uvarint32() {
        // Encode 300 as varint: 300 = 0b100101100
        // byte 0: 10101100 (0xAC), byte 1: 00000010 (0x02)
        let data = [0xAC, 0x02];
        let mut br = BitReader::new(&data);
        assert_eq!(br.read_uvarint32().unwrap(), 300);
    }

    #[test]
    fn test_varint32_negative() {
        // zigzag(-1) = 1
        let data = [0x01];
        let mut br = BitReader::new(&data);
        assert_eq!(br.read_varint32().unwrap(), -1);
    }

    #[test]
    fn test_varint32_positive() {
        // zigzag(1) = 2
        let data = [0x02];
        let mut br = BitReader::new(&data);
        assert_eq!(br.read_varint32().unwrap(), 1);
    }

    #[test]
    fn test_read_f32() {
        let val: f32 = 1.5;
        let data = val.to_bits().to_le_bytes();
        let mut br = BitReader::new(&data);
        let read_val = br.read_f32().unwrap();
        assert!((read_val - val).abs() < f32::EPSILON);
    }

    #[test]
    fn test_bits_remaining() {
        let data = [0xFF, 0xFF];
        let mut br = BitReader::new(&data);
        assert_eq!(br.bits_remaining(), 16);
        br.read_bits(5).unwrap();
        assert_eq!(br.bits_remaining(), 11);
    }

    #[test]
    fn test_skip_bits() {
        let data = [0b11110000, 0b10101010];
        let mut br = BitReader::new(&data);
        br.skip_bits(4).unwrap();
        assert_eq!(br.read_bits(4).unwrap(), 0b1111);
    }

    #[test]
    fn test_ubitvar() {
        // Simple case: value fits in 6 bits, bits 4,5 = 00
        // Value 5 = 0b000101
        let data = [0b00000101];
        let mut br = BitReader::new(&data);
        assert_eq!(br.read_ubitvar().unwrap(), 5);
    }

    #[test]
    fn test_bitangle() {
        let data = [0x00, 0x00, 0x00, 0x00];
        let mut br = BitReader::new(&data);
        assert!((br.read_bitangle(16).unwrap() - 0.0).abs() < f32::EPSILON);
    }
}

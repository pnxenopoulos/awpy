use crate::error::{Error, Result};

/// Byte-aligned, forward-scanning cursor over a `&[u8]` buffer.
///
/// `ByteReader` is used to walk the **outer** demo command stream — the
/// sequence of `(cmd, tick, size, body)` tuples that make up a `.dem` file
/// after the 16-byte file header. All multi-byte integers are little-endian,
/// and variable-length integers use protobuf-style LEB128 encoding.
///
/// For **bit-level** access inside decompressed packet payloads, see
/// [`BitReader`](crate::io::BitReader).
pub struct ByteReader<'a> {
    data: &'a [u8],
    position: usize,
}

impl<'a> ByteReader<'a> {
    /// Create a new reader starting at the beginning of `data`.
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, position: 0 }
    }

    /// Current byte offset from the start of the buffer.
    #[inline]
    pub fn position(&self) -> usize {
        self.position
    }

    /// Number of bytes between the cursor and the end of the buffer.
    #[inline]
    pub fn remaining(&self) -> usize {
        self.data.len().saturating_sub(self.position)
    }

    /// Returns `true` when the cursor is at or past the end of the buffer.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.position >= self.data.len()
    }

    /// Move the cursor to an absolute byte `position`.
    ///
    /// Returns [`Error::Overflow`] if `position` exceeds the buffer length.
    pub fn seek(&mut self, position: usize) -> Result<()> {
        if position > self.data.len() {
            return Err(Error::Overflow {
                needed: position,
                available: self.data.len(),
            });
        }
        self.position = position;
        Ok(())
    }

    fn check_remaining(&self, n: usize) -> Result<()> {
        if self.position + n > self.data.len() {
            return Err(Error::Overflow {
                needed: n,
                available: self.remaining(),
            });
        }
        Ok(())
    }

    /// Read a single byte and advance the cursor.
    pub fn read_u8(&mut self) -> Result<u8> {
        self.check_remaining(1)?;
        let val = self.data[self.position];
        self.position += 1;
        Ok(val)
    }

    /// Read a little-endian `u32` and advance the cursor by 4 bytes.
    pub fn read_u32(&mut self) -> Result<u32> {
        self.check_remaining(4)?;
        let val = u32::from_le_bytes([
            self.data[self.position],
            self.data[self.position + 1],
            self.data[self.position + 2],
            self.data[self.position + 3],
        ]);
        self.position += 4;
        Ok(val)
    }

    /// Borrow `n` bytes starting at the cursor and advance past them.
    pub fn read_bytes(&mut self, n: usize) -> Result<&'a [u8]> {
        self.check_remaining(n)?;
        let slice = &self.data[self.position..self.position + n];
        self.position += n;
        Ok(slice)
    }

    /// Read a protobuf-style unsigned varint (up to 32 bits / 5 bytes).
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

    /// Read a protobuf-style unsigned varint (up to 64 bits / 10 bytes).
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

    /// Advance the cursor by `n` bytes without reading.
    pub fn skip(&mut self, n: usize) -> Result<()> {
        self.check_remaining(n)?;
        self.position += n;
        Ok(())
    }

    /// Returns the full underlying data slice (independent of cursor position).
    pub fn data(&self) -> &'a [u8] {
        self.data
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_u32() {
        let data = 0x12345678u32.to_le_bytes();
        let mut r = ByteReader::new(&data);
        assert_eq!(r.read_u32().unwrap(), 0x12345678);
    }

    #[test]
    fn test_read_varint() {
        let data = [0xAC, 0x02];
        let mut r = ByteReader::new(&data);
        assert_eq!(r.read_uvarint32().unwrap(), 300);
    }

    #[test]
    fn test_read_bytes() {
        let data = [1, 2, 3, 4, 5];
        let mut r = ByteReader::new(&data);
        let bytes = r.read_bytes(3).unwrap();
        assert_eq!(bytes, &[1, 2, 3]);
        assert_eq!(r.remaining(), 2);
    }

    #[test]
    fn test_overflow() {
        let data = [1];
        let mut r = ByteReader::new(&data);
        r.read_u8().unwrap();
        assert!(r.read_u8().is_err());
    }
}

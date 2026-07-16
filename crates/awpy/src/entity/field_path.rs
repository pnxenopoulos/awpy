use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::sync::LazyLock;

use crate::error::Result;
use crate::io::BitReader;

/// Represents a path to a field within a serializer hierarchy.
///
/// Each component is an index into the serializer's fields array at that
/// nesting level. For example, `[3, 0, 2]` means "field 3 → sub-serializer
/// field 0 → sub-serializer field 2".
#[derive(Debug, Clone, Copy)]
pub struct FieldPath {
    /// Component indices (up to 7 levels of nesting).
    pub data: [u8; 7],
    /// Index of the deepest active component (0-based).
    pub last: usize,
    /// Set to `true` by the `field_path_encode_finish` op to signal end-of-list.
    pub finished: bool,
}

impl Default for FieldPath {
    fn default() -> Self {
        // data[0] starts at 255 (i.e. -1 unsigned). The first field path
        // operation always calls `plus_one` which increments it to 0,
        // producing a valid field index.
        Self {
            data: [255, 0, 0, 0, 0, 0, 0],
            last: 0,
            finished: false,
        }
    }
}

impl FieldPath {
    fn inc_at(&mut self, i: usize, v: i32) {
        self.data[i] = ((self.data[i] as i32 + v) & 0xFF) as u8;
    }

    fn inc_last(&mut self, v: i32) {
        self.inc_at(self.last, v);
    }

    fn push(&mut self, v: i32) {
        self.last += 1;
        self.data[self.last] = (v & 0xFF) as u8;
    }

    fn pop(&mut self, n: usize) {
        for _ in 0..n {
            self.data[self.last] = 0;
            self.last -= 1;
        }
    }

    pub fn get(&self, index: usize) -> usize {
        self.data[index] as usize
    }

    /// Pack the field path into a single u64 key.
    /// Layout: bits [0..56) = data[0..7], bits [56..59) = last (3 bits, max value 6).
    #[inline]
    pub fn pack(&self) -> u64 {
        let mut buf = [0u8; 8];
        buf[..7].copy_from_slice(&self.data);
        buf[7] = self.last as u8;
        u64::from_le_bytes(buf)
    }

    /// Unpack a u64 key back into a FieldPath.
    #[inline]
    pub fn unpack(key: u64) -> FieldPath {
        let buf = key.to_le_bytes();
        let mut data = [0u8; 7];
        data.copy_from_slice(&buf[..7]);
        FieldPath {
            data,
            last: buf[7] as usize,
            finished: false,
        }
    }
}

type FieldOp = fn(&mut FieldPath, &mut BitReader) -> Result<()>;

fn plus_one(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    Ok(())
}

fn plus_two(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_last(2);
    Ok(())
}

fn plus_three(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_last(3);
    Ok(())
}

fn plus_four(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_last(4);
    Ok(())
}

fn plus_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvarfp()? as i32 + 5);
    Ok(())
}

fn push_one_left_delta_zero_right_zero(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.push(0);
    Ok(())
}

fn push_one_left_delta_zero_right_non_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_one_left_delta_one_right_zero(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(0);
    Ok(())
}

fn push_one_left_delta_one_right_non_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_one_left_delta_n_right_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvarfp()? as i32);
    fp.push(0);
    Ok(())
}

fn push_one_left_delta_n_right_non_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvarfp()? as i32 + 2);
    fp.push(br.read_ubitvarfp()? as i32 + 1);
    Ok(())
}

fn push_one_left_delta_n_right_non_zero_pack6_bits(
    fp: &mut FieldPath,
    br: &mut BitReader,
) -> Result<()> {
    fp.inc_last(br.read_bits(3)? as i32 + 2);
    fp.push(br.read_bits(3)? as i32 + 1);
    Ok(())
}

fn push_one_left_delta_n_right_non_zero_pack8_bits(
    fp: &mut FieldPath,
    br: &mut BitReader,
) -> Result<()> {
    fp.inc_last(br.read_bits(4)? as i32 + 2);
    fp.push(br.read_bits(4)? as i32 + 1);
    Ok(())
}

fn push_two_left_delta_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_two_left_delta_one(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_two_left_delta_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvar()? as i32 + 2);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_two_pack5_left_delta_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_two_pack5_left_delta_one(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_two_pack5_left_delta_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvar()? as i32 + 2);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_three_left_delta_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_three_left_delta_one(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_three_left_delta_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvar()? as i32 + 2);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    fp.push(br.read_ubitvarfp()? as i32);
    Ok(())
}

fn push_three_pack5_left_delta_zero(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_three_pack5_left_delta_one(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(1);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_three_pack5_left_delta_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.inc_last(br.read_ubitvar()? as i32 + 2);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    fp.push(br.read_bits(5)? as i32);
    Ok(())
}

fn push_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    let n = br.read_ubitvar()? as usize;
    fp.inc_last(br.read_ubitvar()? as i32);
    for _ in 0..n {
        fp.push(br.read_ubitvarfp()? as i32);
    }
    Ok(())
}

fn push_n_and_non_topographical(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    for i in 0..=fp.last {
        if br.read_bool()? {
            fp.inc_at(i, br.read_varint32()? + 1);
        }
    }
    let n = br.read_ubitvar()? as usize;
    for _ in 0..n {
        fp.push(br.read_ubitvarfp()? as i32);
    }
    Ok(())
}

fn pop_one_plus_one(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.pop(1);
    fp.inc_last(1);
    Ok(())
}

fn pop_one_plus_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(1);
    fp.inc_last(br.read_ubitvarfp()? as i32 + 1);
    Ok(())
}

fn pop_all_but_one_plus_one(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.pop(fp.last);
    fp.inc_last(1);
    Ok(())
}

fn pop_all_but_one_plus_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(fp.last);
    fp.inc_last(br.read_ubitvarfp()? as i32 + 1);
    Ok(())
}

fn pop_all_but_one_plus_n_pack3_bits(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(fp.last);
    fp.inc_last(br.read_bits(3)? as i32 + 1);
    Ok(())
}

fn pop_all_but_one_plus_n_pack6_bits(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(fp.last);
    fp.inc_last(br.read_bits(6)? as i32 + 1);
    Ok(())
}

fn pop_n_plus_one(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(br.read_ubitvarfp()? as usize);
    fp.inc_last(1);
    Ok(())
}

fn pop_n_plus_n(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(br.read_ubitvarfp()? as usize);
    fp.inc_last(br.read_varint32()?);
    Ok(())
}

fn pop_n_and_non_topographical(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    fp.pop(br.read_ubitvarfp()? as usize);
    for i in 0..=fp.last {
        if br.read_bool()? {
            fp.inc_at(i, br.read_varint32()?);
        }
    }
    Ok(())
}

fn non_topo_complex(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    for i in 0..=fp.last {
        if br.read_bool()? {
            fp.inc_at(i, br.read_varint32()?);
        }
    }
    Ok(())
}

fn non_topo_penultimate_plus_one(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.inc_at(fp.last - 1, 1);
    Ok(())
}

fn non_topo_complex_pack4_bits(fp: &mut FieldPath, br: &mut BitReader) -> Result<()> {
    for i in 0..=fp.last {
        if br.read_bool()? {
            fp.inc_at(i, br.read_bits(4)? as i32 - 7);
        }
    }
    Ok(())
}

fn field_path_encode_finish(fp: &mut FieldPath, _br: &mut BitReader) -> Result<()> {
    fp.finished = true;
    Ok(())
}

struct FieldOpDescriptor {
    weight: usize,
    op: FieldOp,
}

/// Valve-defined Huffman weights for field path delta operations.
///
/// Each entry pairs a weight (empirical frequency) with a field-path
/// mutation function. These are assembled into a Huffman tree at startup
/// (see [`build_fieldop_hierarchy`]) so that common operations like
/// `plus_one` use fewer bits on the wire.
const FIELDOP_DESCRIPTORS: &[FieldOpDescriptor] = &[
    FieldOpDescriptor {
        weight: 36271,
        op: plus_one,
    },
    FieldOpDescriptor {
        weight: 10334,
        op: plus_two,
    },
    FieldOpDescriptor {
        weight: 1375,
        op: plus_three,
    },
    FieldOpDescriptor {
        weight: 646,
        op: plus_four,
    },
    FieldOpDescriptor {
        weight: 4128,
        op: plus_n,
    },
    FieldOpDescriptor {
        weight: 35,
        op: push_one_left_delta_zero_right_zero,
    },
    FieldOpDescriptor {
        weight: 3,
        op: push_one_left_delta_zero_right_non_zero,
    },
    FieldOpDescriptor {
        weight: 521,
        op: push_one_left_delta_one_right_zero,
    },
    FieldOpDescriptor {
        weight: 2942,
        op: push_one_left_delta_one_right_non_zero,
    },
    FieldOpDescriptor {
        weight: 560,
        op: push_one_left_delta_n_right_zero,
    },
    FieldOpDescriptor {
        weight: 471,
        op: push_one_left_delta_n_right_non_zero,
    },
    FieldOpDescriptor {
        weight: 10530,
        op: push_one_left_delta_n_right_non_zero_pack6_bits,
    },
    FieldOpDescriptor {
        weight: 251,
        op: push_one_left_delta_n_right_non_zero_pack8_bits,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_left_delta_zero,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_pack5_left_delta_zero,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_left_delta_zero,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_pack5_left_delta_zero,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_left_delta_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_pack5_left_delta_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_left_delta_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_pack5_left_delta_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_left_delta_n,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_two_pack5_left_delta_n,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_left_delta_n,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_three_pack5_left_delta_n,
    },
    FieldOpDescriptor {
        weight: 1,
        op: push_n,
    },
    FieldOpDescriptor {
        weight: 310,
        op: push_n_and_non_topographical,
    },
    FieldOpDescriptor {
        weight: 2,
        op: pop_one_plus_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: pop_one_plus_n,
    },
    FieldOpDescriptor {
        weight: 1837,
        op: pop_all_but_one_plus_one,
    },
    FieldOpDescriptor {
        weight: 149,
        op: pop_all_but_one_plus_n,
    },
    FieldOpDescriptor {
        weight: 300,
        op: pop_all_but_one_plus_n_pack3_bits,
    },
    FieldOpDescriptor {
        weight: 634,
        op: pop_all_but_one_plus_n_pack6_bits,
    },
    FieldOpDescriptor {
        weight: 1,
        op: pop_n_plus_one,
    },
    FieldOpDescriptor {
        weight: 1,
        op: pop_n_plus_n,
    },
    FieldOpDescriptor {
        weight: 1,
        op: pop_n_and_non_topographical,
    },
    FieldOpDescriptor {
        weight: 76,
        op: non_topo_complex,
    },
    FieldOpDescriptor {
        weight: 271,
        op: non_topo_penultimate_plus_one,
    },
    FieldOpDescriptor {
        weight: 99,
        op: non_topo_complex_pack4_bits,
    },
    FieldOpDescriptor {
        weight: 25474,
        op: field_path_encode_finish,
    },
];

#[derive(Debug)]
enum Node {
    Leaf {
        weight: usize,
        num: usize,
        op: FieldOp,
    },
    Branch {
        weight: usize,
        num: usize,
        left: Box<Node>,
        right: Box<Node>,
    },
}

impl Node {
    fn weight(&self) -> usize {
        match self {
            Self::Leaf { weight, .. } => *weight,
            Self::Branch { weight, .. } => *weight,
        }
    }

    fn num(&self) -> usize {
        match self {
            Self::Leaf { num, .. } => *num,
            Self::Branch { num, .. } => *num,
        }
    }
}

// Ordering is inverted (other vs self) so BinaryHeap acts as a min-heap.
impl Ord for Node {
    fn cmp(&self, other: &Self) -> Ordering {
        if self.weight() == other.weight() {
            self.num().cmp(&other.num())
        } else {
            other.weight().cmp(&self.weight())
        }
    }
}

impl PartialOrd for Node {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for Node {
    fn eq(&self, other: &Self) -> bool {
        self.weight() == other.weight() && self.num() == other.num()
    }
}

impl Eq for Node {}

/// Build a Huffman tree from the weighted operation descriptors.
fn build_fieldop_hierarchy() -> Node {
    let mut heap = BinaryHeap::with_capacity(FIELDOP_DESCRIPTORS.len());
    let mut num = 0;

    for desc in FIELDOP_DESCRIPTORS {
        heap.push(Node::Leaf {
            weight: desc.weight,
            num,
            op: desc.op,
        });
        num += 1;
    }

    while heap.len() > 1 {
        let left = heap.pop().unwrap();
        let right = heap.pop().unwrap();
        heap.push(Node::Branch {
            weight: left.weight() + right.weight(),
            num,
            left: Box::new(left),
            right: Box::new(right),
        });
        num += 1;
    }

    heap.pop().unwrap()
}

static FIELDOP_HIERARCHY: LazyLock<Node> = LazyLock::new(build_fieldop_hierarchy);

/// Read field paths from a bit reader using the Huffman-coded encoding.
/// Clears and fills the provided buffer with decoded field paths.
pub fn read_field_paths(br: &mut BitReader, buf: &mut Vec<FieldPath>) -> Result<()> {
    buf.clear();
    let mut fp = FieldPath::default();
    let mut node: &Node = &FIELDOP_HIERARCHY;

    loop {
        let next = if br.read_bool()? {
            match node {
                Node::Branch { right, .. } => right.as_ref(),
                _ => unreachable!(),
            }
        } else {
            match node {
                Node::Branch { left, .. } => left.as_ref(),
                _ => unreachable!(),
            }
        };

        node = if let Node::Leaf { op, .. } = next {
            op(&mut fp, br)?;
            if fp.finished {
                return Ok(());
            }
            buf.push(fp);
            &FIELDOP_HIERARCHY
        } else {
            next
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── FieldPath basics ──

    #[test]
    fn default_values() {
        let fp = FieldPath::default();
        assert_eq!(fp.data[0], 255);
        assert_eq!(fp.last, 0);
        assert!(!fp.finished);
    }

    #[test]
    fn get_returns_data() {
        let fp = FieldPath::default();
        assert_eq!(fp.get(0), 255);
        assert_eq!(fp.get(1), 0);
    }

    #[test]
    fn pack_unpack_default_roundtrip() {
        let fp = FieldPath::default();
        let key = fp.pack();
        let fp2 = FieldPath::unpack(key);
        assert_eq!(fp.data, fp2.data);
        assert_eq!(fp.last, fp2.last);
    }

    #[test]
    fn pack_unpack_custom_roundtrip() {
        let fp = FieldPath {
            data: [1, 2, 3, 4, 5, 6, 7],
            last: 3,
            ..Default::default()
        };
        let key = fp.pack();
        let fp2 = FieldPath::unpack(key);
        assert_eq!(fp.data, fp2.data);
        assert_eq!(fp.last, fp2.last);
    }

    #[test]
    fn pack_unpack_max_last() {
        let fp = FieldPath {
            last: 6,
            ..Default::default()
        };
        let key = fp.pack();
        let fp2 = FieldPath::unpack(key);
        assert_eq!(fp2.last, 6);
    }

    // ── Private operations ──

    #[test]
    fn inc_at_wraps() {
        let mut fp = FieldPath::default();
        // data[0] is 255, incrementing by 1 should wrap to 0
        fp.inc_at(0, 1);
        assert_eq!(fp.data[0], 0);
    }

    #[test]
    fn push_pop_sequence() {
        let mut fp = FieldPath::default();
        assert_eq!(fp.last, 0);
        fp.push(42);
        assert_eq!(fp.last, 1);
        assert_eq!(fp.data[1], 42);
        fp.pop(1);
        assert_eq!(fp.last, 0);
        assert_eq!(fp.data[1], 0);
    }

    #[test]
    fn inc_last_modifies_current() {
        let mut fp = FieldPath {
            data: [10, 0, 0, 0, 0, 0, 0],
            last: 0,
            finished: false,
        };
        fp.inc_last(5);
        assert_eq!(fp.data[0], 15);
    }

    #[test]
    fn plus_one_field_op() {
        let mut fp = FieldPath {
            data: [10, 0, 0, 0, 0, 0, 0],
            last: 0,
            finished: false,
        };
        let data = [0u8; 1];
        let mut br = BitReader::new(&data);
        plus_one(&mut fp, &mut br).unwrap();
        assert_eq!(fp.data[0], 11);
    }

    #[test]
    fn field_path_encode_finish_sets_finished() {
        let mut fp = FieldPath::default();
        let data = [0u8; 1];
        let mut br = BitReader::new(&data);
        field_path_encode_finish(&mut fp, &mut br).unwrap();
        assert!(fp.finished);
    }
}

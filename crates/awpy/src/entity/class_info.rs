use awpy_proto::proto::CDemoClassInfo;

/// A single entity class entry.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ClassEntry {
    pub class_id: i32,
    pub network_name: String,
    pub table_name: String,
}

/// Parsed class info from DEM_ClassInfo. Maps class IDs to network names.
#[derive(Debug, Clone)]
pub struct ClassInfo {
    pub classes: Vec<ClassEntry>,
    /// Number of bits needed to encode a class_id.
    pub bits: usize,
    /// O(1) lookup table: index is class_id, value is index into `classes`.
    lookup: Vec<Option<usize>>,
}

impl ClassInfo {
    /// Create an empty `ClassInfo` (used for tests / default initialization).
    pub fn empty() -> Self {
        ClassInfo {
            classes: Vec::new(),
            bits: 1,
            lookup: Vec::new(),
        }
    }

    /// Parse a `CDemoClassInfo` protobuf message into a [`ClassInfo`].
    pub fn parse(cmd: CDemoClassInfo) -> Self {
        let classes: Vec<ClassEntry> = cmd
            .classes
            .into_iter()
            .map(|c| ClassEntry {
                class_id: c.class_id.unwrap_or(0),
                network_name: c.network_name.unwrap_or_default(),
                table_name: c.table_name.unwrap_or_default(),
            })
            .collect();

        // Compute the minimum number of bits needed to represent the largest
        // class_id (ceiling of log2). The entity system reads this many bits
        // from the bitstream when decoding a DELTA_CREATE header.
        let max_id = classes.iter().map(|c| c.class_id).max().unwrap_or(0) as u32;
        let bits = if max_id == 0 {
            1
        } else {
            32 - max_id.leading_zeros() as usize
        };

        // Build flat lookup table indexed by class_id.
        let mut lookup = vec![None; max_id as usize + 1];
        for (i, c) in classes.iter().enumerate() {
            if c.class_id >= 0 {
                lookup[c.class_id as usize] = Some(i);
            }
        }

        ClassInfo {
            classes,
            bits,
            lookup,
        }
    }

    /// Look up a class entry by its numeric ID. O(1).
    pub fn by_id(&self, class_id: i32) -> Option<&ClassEntry> {
        let idx = *self.lookup.get(class_id as usize)?.as_ref()?;
        Some(&self.classes[idx])
    }

    /// Shorthand to get the network name for a class ID.
    pub fn name_by_id(&self, class_id: i32) -> Option<&str> {
        self.by_id(class_id).map(|c| c.network_name.as_str())
    }

    /// The numeric class ID for a network class name (linear scan). Intended for
    /// one-time resolution of a handful of target classes so that per-entity,
    /// per-tick checks can compare a `class_id` instead of the `class_name`
    /// string.
    pub fn id_of(&self, network_name: &str) -> Option<i32> {
        self.classes
            .iter()
            .find(|c| c.network_name == network_name)
            .map(|c| c.class_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use awpy_proto::proto::c_demo_class_info;

    fn make_class_info(ids: &[(i32, &str)]) -> ClassInfo {
        let cmd = CDemoClassInfo {
            classes: ids
                .iter()
                .map(|(id, name)| c_demo_class_info::ClassT {
                    class_id: Some(*id),
                    network_name: Some(name.to_string()),
                    table_name: Some(String::new()),
                })
                .collect(),
        };
        ClassInfo::parse(cmd)
    }

    #[test]
    fn empty_classes_bits_is_1() {
        let ci = make_class_info(&[]);
        assert_eq!(ci.bits, 1);
    }

    #[test]
    fn single_class_id_0_bits_is_1() {
        let ci = make_class_info(&[(0, "A")]);
        assert_eq!(ci.bits, 1);
    }

    #[test]
    fn max_id_10_bits_is_4() {
        let ci = make_class_info(&[(0, "A"), (10, "B")]);
        assert_eq!(ci.bits, 4);
    }

    #[test]
    fn max_id_8_bits_is_4() {
        let ci = make_class_info(&[(8, "A")]);
        assert_eq!(ci.bits, 4);
    }

    #[test]
    fn max_id_255_bits_is_8() {
        let ci = make_class_info(&[(255, "A")]);
        assert_eq!(ci.bits, 8);
    }

    #[test]
    fn by_id_found() {
        let ci = make_class_info(&[(5, "Hero"), (10, "Creep")]);
        let entry = ci.by_id(10).unwrap();
        assert_eq!(entry.network_name, "Creep");
    }

    #[test]
    fn by_id_not_found() {
        let ci = make_class_info(&[(5, "Hero")]);
        assert!(ci.by_id(99).is_none());
    }

    #[test]
    fn name_by_id_returns_correct_name() {
        let ci = make_class_info(&[(1, "Player"), (2, "NPC")]);
        assert_eq!(ci.name_by_id(1), Some("Player"));
        assert_eq!(ci.name_by_id(99), None);
    }
}

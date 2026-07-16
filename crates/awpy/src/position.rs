//! World-coordinate helpers for Source 2's split position storage.
//!
//! Networked entities in Source 2 do not transmit a full world position
//! every tick. Each position is split across two networked fields:
//!
//! - an integer **cell index** (`m_cellX`, `m_cellY`, `m_cellZ`) identifying
//!   which fixed-size cell of the world the entity is currently in, and
//! - a quantized **offset** (`m_vecOrigin.m_vecX`, etc.) describing where
//!   inside that cell the entity sits, bounded to `[0, CELL_SIZE)`.
//!
//! The true world position (in Hammer units, the same coordinate space used
//! by Valve's level editor and `.vmap` data) is reconstructed via
//! [`cell_to_world`]. Reading the offset alone gives a sawtooth signal that
//! resets every time the entity crosses a cell boundary, not a usable
//! coordinate. See [`Entity::world_position`](crate::Entity::world_position)
//! for the typical entity-side combine.

/// Number of bits used by Source 2 to address a position within a cell.
///
/// The on-the-wire offset is quantized into a `2^CELL_BITS` window, so cells
/// are `CELL_SIZE` Hammer units wide on each axis.
pub const CELL_BITS: u32 = 9;

/// Edge length of a single cell in Hammer units (`2^CELL_BITS`).
pub const CELL_SIZE: f32 = (1u32 << CELL_BITS) as f32;

/// Half the addressable world extent in Hammer units.
///
/// Source 2's cell grid is centred on the world origin, so cell 0 starts at
/// `-WORLD_HALF` and cell indices run upward from there. This constant is the
/// shift applied in [`cell_to_world`] to translate cell-relative addresses
/// back to centred world coordinates.
pub const WORLD_HALF: f32 = 16384.0;

/// Combine a cell index and an in-cell offset into a world coordinate.
///
/// Applies the standard Source 2 transform `cell * CELL_SIZE - WORLD_HALF +
/// offset` along a single axis. Operate on each axis independently to
/// recover a full `[x, y, z]` world position; see
/// [`Entity::world_position`](crate::Entity::world_position) for the typical
/// entity-side combine that does this for all three axes at once.
pub fn cell_to_world(cell: i32, offset: f32) -> f32 {
    (cell as f32) * CELL_SIZE - WORLD_HALF + offset
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constants_match_source2_layout() {
        assert_eq!(CELL_BITS, 9);
        assert_eq!(CELL_SIZE, 512.0);
        assert_eq!(WORLD_HALF, 16384.0);
    }

    #[test]
    fn world_origin_maps_to_centre_of_cell_32() {
        // Cell 32 is the cell that contains the world origin (0): it starts
        // at `32 * 512 - 16384 = 0` and ends just before `+512`.
        assert_eq!(cell_to_world(32, 0.0), 0.0);
        assert_eq!(cell_to_world(32, 256.0), 256.0);
    }

    #[test]
    fn cell_zero_is_negative_world_half() {
        assert_eq!(cell_to_world(0, 0.0), -WORLD_HALF);
        assert_eq!(cell_to_world(0, 1.0), -WORLD_HALF + 1.0);
    }

    #[test]
    fn adjacent_cells_differ_by_cell_size() {
        let a = cell_to_world(32, 511.0);
        let b = cell_to_world(33, 0.0);
        // The sawtooth: a tiny offset step across a cell boundary jumps from
        // (cell, ~CELL_SIZE) to (cell+1, ~0), but the *world* delta is 1.0.
        assert!((b - a - 1.0).abs() < 1e-3);
    }
}

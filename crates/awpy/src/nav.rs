//! Navigation mesh (`.nav`) parsing and area queries.
//!
//! CS2 ships a navigation mesh for each map: a set of convex polygonal *areas*
//! that tile the walkable surface, wired together by *connections* that record
//! which area you can step into from which edge. Bots path over this graph, and
//! it's a compact stand-in for "where on the map is this" without the full
//! collision geometry.
//!
//! `awpy-data` publishes the raw `.nav` files (as extracted from the game); this
//! module parses one and answers the questions you'd actually ask of it: which
//! area contains a world point, and the shortest area-to-area path across the
//! connection graph.
//!
//! # Format
//!
//! The parser handles the Source 2 `.nav` format, versions 30–36 (CS2 currently
//! ships version 36), following the layout documented by [ValveResourceFormat].
//! Areas are identified by numeric `area_id`. Version 36 wraps the areas in
//! embedded KV3 documents; these carry no area data (they're empty placeholders
//! in shipped navs), so we skip over them. Older CS:GO-era navs use a different
//! layout and are not supported.
//!
//! [ValveResourceFormat]: https://github.com/ValveResourceFormat/ValveResourceFormat/tree/master/ValveResourceFormat/NavMesh
//!
//! Coordinates are Hammer units, Z-up — the same frame as
//! [`Entity::world_position`](crate::Entity::world_position) and the demo
//! world-position columns, so entity positions can be passed in directly.
//!
//! ```no_run
//! use awpy::nav::{Nav, PathWeight};
//!
//! let nav = Nav::from_file("de_dust2.nav".as_ref()).unwrap();
//!
//! // Which area is a world point standing in?
//! let area = nav.find_area([-1500.0, 900.0, 60.0]);
//!
//! // Shortest walk between two areas, weighted by real distance.
//! if let (Some(a), Some(b)) = (area, nav.find_area([1200.0, 2500.0, 100.0])) {
//!     let path = nav.find_path(a, b, PathWeight::Distance);
//!     println!("{} areas along the path", path.len());
//! }
//! ```

use std::collections::{BinaryHeap, HashMap, HashSet};
use std::path::Path;

use crate::error::{Error, Result};

/// Magic number at the start of a `.nav` file.
const MAGIC: u32 = 0xFEED_FACE;
/// Lowest nav-mesh version this parser understands.
const MIN_VERSION: u32 = 30;
/// Highest nav-mesh version this parser understands.
const MAX_VERSION: u32 = 36;

type Vec3 = [f32; 3];

/// A single walkable area in the navigation mesh.
///
/// An area is a convex polygon (the [`corners`](NavArea::corners)) plus the set
/// of neighbouring areas you can move into from it ([`connections`](NavArea::connections)).
#[derive(Clone, Debug)]
pub struct NavArea {
    /// Unique identifier for the area within its mesh.
    pub area_id: u32,
    /// Index of the collision hull this area was generated for.
    pub hull_index: u8,
    /// Dynamic attribute flags (bomb-target, defuse, etc.); engine-defined bitset.
    pub dynamic_attribute_flags: i64,
    /// Polygon corners, in order, as `[x, y, z]` Hammer-unit positions.
    pub corners: Vec<Vec3>,
    /// Area IDs reachable directly from this area (may repeat across edges).
    pub connections: Vec<u32>,
    /// Ladder IDs whose top touches this area.
    pub ladders_above: Vec<u32>,
    /// Ladder IDs whose bottom touches this area.
    pub ladders_below: Vec<u32>,
}

impl NavArea {
    /// Geometric center of the polygon (mean of its corners), `[x, y, z]`.
    pub fn centroid(&self) -> Vec3 {
        if self.corners.is_empty() {
            return [0.0, 0.0, 0.0];
        }
        let n = self.corners.len() as f32;
        let mut c = [0.0f32; 3];
        for p in &self.corners {
            c[0] += p[0];
            c[1] += p[1];
            c[2] += p[2];
        }
        [c[0] / n, c[1] / n, c[2] / n]
    }

    /// 2D area of the polygon (in the XY plane), via the shoelace formula.
    pub fn size(&self) -> f32 {
        let n = self.corners.len();
        if n < 3 {
            return 0.0;
        }
        let mut sum = 0.0f32;
        for i in 0..n {
            let a = self.corners[i];
            let b = self.corners[(i + 1) % n];
            sum += a[0] * b[1] - b[0] * a[1];
        }
        sum.abs() / 2.0
    }

    /// Does the polygon contain `(x, y)` in the XY plane? (Ignores Z.)
    ///
    /// Standard even-odd ray-cast point-in-polygon test; points exactly on an
    /// edge may resolve either way.
    pub fn contains_xy(&self, x: f32, y: f32) -> bool {
        let n = self.corners.len();
        if n < 3 {
            return false;
        }
        let mut inside = false;
        let mut j = n - 1;
        for i in 0..n {
            let (xi, yi) = (self.corners[i][0], self.corners[i][1]);
            let (xj, yj) = (self.corners[j][0], self.corners[j][1]);
            let intersects = ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if intersects {
                inside = !inside;
            }
            j = i;
        }
        inside
    }
}

/// How to weight edges when searching for a path.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum PathWeight {
    /// Every edge costs 1 — minimizes the number of areas traversed.
    Hops,
    /// Edge cost is the 3D distance between the two areas' centroids —
    /// approximates real travel distance. This is the default.
    #[default]
    Distance,
    /// Edge cost is the sum of the two areas' 2D sizes, so crossing large areas
    /// costs more and paths tend to hug smaller, tighter areas.
    Size,
}

/// A parsed navigation mesh: its areas and the connection graph over them.
#[derive(Clone, Debug)]
pub struct Nav {
    /// Major format version (30–35).
    pub version: u32,
    /// Sub-version of the format.
    pub sub_version: u32,
    /// Whether the mesh has been analyzed (bot-navigation data generated).
    pub is_analyzed: bool,
    /// Areas in file order.
    pub areas: Vec<NavArea>,
    /// `area_id` → index into [`areas`](Nav::areas).
    index: HashMap<u32, usize>,
}

impl Nav {
    /// Parse a navigation mesh from raw `.nav` bytes.
    pub fn from_bytes(data: &[u8]) -> Result<Nav> {
        let mut r = Reader::new(data);

        let magic = r.u32()?;
        if magic != MAGIC {
            return Err(parse(format!(
                "bad magic: {magic:#010X}, expected {MAGIC:#010X}"
            )));
        }
        let version = r.u32()?;
        if !(MIN_VERSION..=MAX_VERSION).contains(&version) {
            return Err(parse(format!(
                "unsupported nav version {version} (supported: {MIN_VERSION}-{MAX_VERSION})"
            )));
        }
        let sub_version = r.u32()?;
        let unk1 = r.u32()?;
        let is_analyzed = unk1 & 0x1 != 0;

        // Version 36 embeds a (placeholder) KV3 document here; skip past it.
        if version >= 36 {
            skip_kv3(&mut r)?;
        }

        // Version 31+ hoists all polygon corners into a shared table; each area
        // then references a polygon by index. Earlier versions inline corners.
        let polygons = if version >= 31 {
            Some(read_polygons(&mut r, version)?)
        } else {
            None
        };

        if version >= 32 {
            r.skip(4)?; // unknown
        }

        // Version 35+ has a table of named markers: a count, then that many
        // (null-terminated ASCII string + 48-byte record) entries. Shipped navs
        // usually have zero, but read the count so a non-empty table doesn't
        // desync the parse.
        if version >= 35 {
            let count = r.u32()?;
            for _ in 0..count {
                r.skip_cstring()?;
                r.skip(48)?;
            }
        }

        // Version 36 embeds a second (placeholder) KV3 document before the areas.
        if version >= 36 {
            skip_kv3(&mut r)?;
        }

        let area_count = r.u32()? as usize;
        let mut areas = Vec::with_capacity(area_count);
        let mut index = HashMap::with_capacity(area_count);
        for _ in 0..area_count {
            let area = read_area(&mut r, version, polygons.as_deref())?;
            index.insert(area.area_id, areas.len());
            areas.push(area);
        }

        Ok(Nav {
            version,
            sub_version,
            is_analyzed,
            areas,
            index,
        })
    }

    /// Load and parse a navigation mesh from a `.nav` file.
    pub fn from_file(path: &Path) -> Result<Nav> {
        Nav::from_bytes(&std::fs::read(path)?)
    }

    /// Build a mesh directly from a list of areas, constructing the
    /// `area_id → index` lookup from them.
    ///
    /// For programmatic or synthetic navs (e.g. tests, or a mesh assembled from
    /// another source). Version fields are `0` and `is_analyzed` is `false`; if
    /// two areas share an ID the last one wins in the lookup.
    pub fn from_areas(areas: Vec<NavArea>) -> Nav {
        let mut index = HashMap::with_capacity(areas.len());
        for (i, a) in areas.iter().enumerate() {
            index.insert(a.area_id, i);
        }
        Nav {
            version: 0,
            sub_version: 0,
            is_analyzed: false,
            areas,
            index,
        }
    }

    /// Number of areas in the mesh.
    pub fn area_count(&self) -> usize {
        self.areas.len()
    }

    /// Look up an area by its ID.
    pub fn area(&self, area_id: u32) -> Option<&NavArea> {
        self.index.get(&area_id).map(|&i| &self.areas[i])
    }

    /// The area containing world point `p`, or `None` if the point is over no
    /// area.
    ///
    /// Several areas can overlap in the XY plane (stacked floors, bridges over
    /// tunnels), so among all areas whose polygon contains `(x, y)` this returns
    /// the one whose centroid height is closest to `p`'s Z — i.e. the floor the
    /// point is actually standing on.
    pub fn find_area(&self, p: Vec3) -> Option<u32> {
        let mut best: Option<(u32, f32)> = None;
        for area in &self.areas {
            if area.contains_xy(p[0], p[1]) {
                let dz = (area.centroid()[2] - p[2]).abs();
                if best.is_none_or(|(_, best_dz)| dz < best_dz) {
                    best = Some((area.area_id, dz));
                }
            }
        }
        best.map(|(id, _)| id)
    }

    /// Neighbouring area IDs reachable directly from `area_id`, de-duplicated.
    ///
    /// Returns an empty vector if the area has no connections or does not exist.
    pub fn neighbors(&self, area_id: u32) -> Vec<u32> {
        let Some(area) = self.area(area_id) else {
            return Vec::new();
        };
        let mut seen = Vec::new();
        for &c in &area.connections {
            if !seen.contains(&c) {
                seen.push(c);
            }
        }
        seen
    }

    /// Shortest path from `start` to `end` across the connection graph.
    ///
    /// Returns the sequence of area IDs from `start` to `end` inclusive, or an
    /// empty vector if either area is unknown or no path connects them. `start
    /// == end` yields `[start]`. Connections are directional, matching the mesh.
    ///
    /// `weight` selects how edges are costed (see [`PathWeight`]).
    pub fn find_path(&self, start: u32, end: u32, weight: PathWeight) -> Vec<u32> {
        if self.area(start).is_none() || self.area(end).is_none() {
            return Vec::new();
        }
        if start == end {
            return vec![start];
        }

        // Dijkstra over area IDs. Costs are f64 so distance/size weights compose
        // cleanly; the heap is a min-heap via `Reverse`-style ordering in `HeapItem`.
        let mut dist: HashMap<u32, f64> = HashMap::new();
        let mut prev: HashMap<u32, u32> = HashMap::new();
        let mut heap: BinaryHeap<HeapItem> = BinaryHeap::new();

        dist.insert(start, 0.0);
        heap.push(HeapItem {
            cost: 0.0,
            area: start,
        });

        while let Some(HeapItem { cost, area }) = heap.pop() {
            if area == end {
                break;
            }
            // Stale heap entry (a shorter route to `area` was already settled).
            if cost > *dist.get(&area).unwrap_or(&f64::INFINITY) {
                continue;
            }
            for next in self.neighbors(area) {
                let step = self.edge_cost(area, next, weight);
                let nd = cost + step;
                if nd < *dist.get(&next).unwrap_or(&f64::INFINITY) {
                    dist.insert(next, nd);
                    prev.insert(next, area);
                    heap.push(HeapItem {
                        cost: nd,
                        area: next,
                    });
                }
            }
        }

        if !dist.contains_key(&end) {
            return Vec::new();
        }
        // Walk predecessors back from `end` to `start`, then reverse.
        let mut path = vec![end];
        let mut cur = end;
        while cur != start {
            match prev.get(&cur) {
                Some(&p) => {
                    path.push(p);
                    cur = p;
                }
                None => return Vec::new(),
            }
        }
        path.reverse();
        path
    }

    /// Shortest travel cost from the nearest of `sources` to every reachable
    /// area, as an `area_id → cost` map.
    ///
    /// A multi-source Dijkstra over the connection graph: every source starts at
    /// cost 0, so each area's entry is the cost of reaching it from whichever
    /// source is closest. Areas in `blocked` are impassable — never settled and
    /// never traversed through — which is how a caller routes around denied space
    /// (e.g. a burning molotov). Unreachable areas are simply absent from the
    /// map, and unknown or blocked source IDs are ignored.
    ///
    /// `weight` selects how edges are costed (see [`PathWeight`]).
    pub fn multi_source_distances(
        &self,
        sources: &[u32],
        weight: PathWeight,
        blocked: &HashSet<u32>,
    ) -> HashMap<u32, f64> {
        let mut dist: HashMap<u32, f64> = HashMap::new();
        let mut heap: BinaryHeap<HeapItem> = BinaryHeap::new();
        for &s in sources {
            if self.area(s).is_none() || blocked.contains(&s) {
                continue;
            }
            // First time we see this source, seed it at 0; duplicates are skipped
            // (the entry already exists) so we don't push it onto the heap twice.
            if dist.insert(s, 0.0).is_none() {
                heap.push(HeapItem { cost: 0.0, area: s });
            }
        }

        while let Some(HeapItem { cost, area }) = heap.pop() {
            // Stale heap entry (a shorter route to `area` was already settled).
            if cost > *dist.get(&area).unwrap_or(&f64::INFINITY) {
                continue;
            }
            for next in self.neighbors(area) {
                if blocked.contains(&next) {
                    continue;
                }
                let nd = cost + self.edge_cost(area, next, weight);
                if nd < *dist.get(&next).unwrap_or(&f64::INFINITY) {
                    dist.insert(next, nd);
                    heap.push(HeapItem {
                        cost: nd,
                        area: next,
                    });
                }
            }
        }
        dist
    }

    /// Cost of stepping from `a` to `b` under `weight`.
    fn edge_cost(&self, a: u32, b: u32, weight: PathWeight) -> f64 {
        match weight {
            PathWeight::Hops => 1.0,
            PathWeight::Distance => {
                let (ca, cb) = match (self.area(a), self.area(b)) {
                    (Some(a), Some(b)) => (a.centroid(), b.centroid()),
                    _ => return 1.0,
                };
                let dx = f64::from(ca[0] - cb[0]);
                let dy = f64::from(ca[1] - cb[1]);
                let dz = f64::from(ca[2] - cb[2]);
                (dx * dx + dy * dy + dz * dz).sqrt()
            }
            PathWeight::Size => {
                let sa = self.area(a).map_or(0.0, NavArea::size);
                let sb = self.area(b).map_or(0.0, NavArea::size);
                let sa = f64::from(sa);
                let sb = f64::from(sb);
                sa + sb
            }
        }
    }
}

/// Min-heap entry for Dijkstra: ordered so the smallest cost pops first.
struct HeapItem {
    cost: f64,
    area: u32,
}

impl PartialEq for HeapItem {
    fn eq(&self, other: &Self) -> bool {
        self.cost == other.cost
    }
}
impl Eq for HeapItem {}
impl Ord for HeapItem {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        // Reversed so `BinaryHeap` (a max-heap) yields the minimum cost. Costs
        // are finite and non-NaN, so `total_cmp` gives a valid total order.
        other.cost.total_cmp(&self.cost)
    }
}
impl PartialOrd for HeapItem {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

/// Read the shared polygon table (version 31+): a corner pool, then polygons
/// that index into it. Returns each polygon as its list of corner positions.
fn read_polygons(r: &mut Reader, version: u32) -> Result<Vec<Vec<Vec3>>> {
    let corner_count = r.u32()? as usize;
    let mut corners = Vec::with_capacity(corner_count);
    for _ in 0..corner_count {
        corners.push(r.vec3()?);
    }

    let polygon_count = r.u32()? as usize;
    let mut polygons = Vec::with_capacity(polygon_count);
    for _ in 0..polygon_count {
        let n = r.u8()? as usize;
        let mut poly = Vec::with_capacity(n);
        for _ in 0..n {
            let ci = r.u32()? as usize;
            let corner = *corners
                .get(ci)
                .ok_or_else(|| parse(format!("polygon corner index {ci} out of range")))?;
            poly.push(corner);
        }
        if version >= 35 {
            r.skip(4)?; // unknown per-polygon field
        }
        polygons.push(poly);
    }
    Ok(polygons)
}

/// Read a single area record.
fn read_area(r: &mut Reader, version: u32, polygons: Option<&[Vec<Vec3>]>) -> Result<NavArea> {
    let area_id = r.u32()?;
    let dynamic_attribute_flags = r.i64()?;
    let hull_index = r.u8()?;

    let corners = match polygons {
        Some(polys) if version >= 31 => {
            let pi = r.u32()? as usize;
            polys
                .get(pi)
                .ok_or_else(|| parse(format!("area polygon index {pi} out of range")))?
                .clone()
        }
        _ => {
            let corner_count = r.u32()? as usize;
            let mut corners = Vec::with_capacity(corner_count);
            for _ in 0..corner_count {
                corners.push(r.vec3()?);
            }
            corners
        }
    };

    r.skip(4)?; // almost always 0

    // One connection list per polygon edge (i.e. per corner).
    let mut connections = Vec::new();
    for _ in 0..corners.len() {
        let count = r.u32()? as usize;
        for _ in 0..count {
            let neighbor = r.u32()?;
            let _edge_id = r.u32()?;
            connections.push(neighbor);
        }
    }

    // Legacy hiding-spot count (u8) + legacy encounter-path count (u32); the
    // records themselves are absent in analyzed CS2 navs, so skip the counts.
    r.skip(5)?;

    let ladders_above = read_ids(r)?;
    let ladders_below = read_ids(r)?;

    Ok(NavArea {
        area_id,
        hull_index,
        dynamic_attribute_flags,
        corners,
        connections,
        ladders_above,
        ladders_below,
    })
}

/// Read a `u32` count followed by that many `u32` IDs.
fn read_ids(r: &mut Reader) -> Result<Vec<u32>> {
    let count = r.u32()? as usize;
    let mut ids = Vec::with_capacity(count);
    for _ in 0..count {
        ids.push(r.u32()?);
    }
    Ok(ids)
}

/// Skip over an embedded KV3 binary document (version 36 wraps areas in these).
///
/// We never need the KV3 *contents*, only to advance past the document to reach
/// the nav data after it. That takes just the container header: it records the
/// on-disk size of each data buffer, so the total length is computable without
/// decompressing anything. Shipped nav KV3 blocks are empty placeholders
/// (uncompressed, no blocks or blobs); anything more exotic is rejected rather
/// than silently mis-skipped.
///
/// Layout per [ValveResourceFormat's `BinaryKV3`]; only the header fields that
/// contribute to the on-disk length are read, the rest are stepped over.
///
/// [ValveResourceFormat's `BinaryKV3`]: https://github.com/ValveResourceFormat/ValveResourceFormat/blob/master/ValveResourceFormat/Resource/ResourceTypes/BinaryKV3.cs
fn skip_kv3(r: &mut Reader) -> Result<()> {
    const MAGIC0: u32 = 0x0356_4B56;

    // Align KV3 documents to an 8-byte boundary.
    r.align8();
    let magic = r.u32()?;
    if magic == MAGIC0 {
        return Err(parse("KV3 v0 document not supported"));
    }
    // Later magics are "\x01/\x02/…3VK": high 3 bytes 0x4B5633, low byte = version.
    let version = magic & 0xFF;
    if magic & 0xFFFF_FF00 != 0x4B56_3300 || !(1..=5).contains(&version) {
        return Err(parse(format!("unsupported KV3 signature {magic:#010X}")));
    }
    if version == 1 {
        return Err(parse("KV3 v1 document not supported"));
    }

    r.skip(16)?; // format GUID
    let method = r.u32()?; // 0 = uncompressed, 1 = LZ4, 2 = ZSTD
    r.skip(2 + 2)?; // compression dictionary id + frame size
    r.skip(4 * 4)?; // countBytes1/4/8 + countTypes
    r.skip(2 + 2)?; // countObjects + countArrays
    let size_unc_total = r.i32()?;
    let size_cmp_total = r.i32()?;
    let n_blocks = r.i32()?;
    let n_blobs = r.i32()?;

    let mut size_block_compressed = 0i64;
    if version >= 4 {
        r.skip(4)?; // countBytes2
        size_block_compressed = i64::from(r.i32()?);
    }

    // On-disk size of the two data buffers. v5 splits them out explicitly; for
    // an uncompressed buffer the on-disk bytes equal its uncompressed size.
    let (unc1, cmp1, unc2, cmp2);
    if version >= 5 {
        unc1 = r.i32()?;
        cmp1 = r.i32()?;
        unc2 = r.i32()?;
        cmp2 = r.i32()?;
        r.skip(4 * 8)?; // eight trailing buffer-2 count fields
    } else {
        unc1 = size_unc_total;
        cmp1 = size_cmp_total;
        unc2 = 0;
        cmp2 = 0;
    }

    if method > 2 {
        return Err(parse(format!(
            "unsupported KV3 compression method {method}"
        )));
    }
    // Nav KV3 blocks are empty; block/blob data would need decompression to size.
    if n_blocks != 0 || n_blobs != 0 {
        return Err(parse(format!(
            "KV3 document with block/blob data unsupported (blocks={n_blocks}, blobs={n_blobs})"
        )));
    }

    let on_disk = |unc: i32, cmp: i32| i64::from(if method == 0 { unc } else { cmp });
    let body = on_disk(unc1, cmp1) + on_disk(unc2, cmp2) + size_block_compressed;
    let body = usize::try_from(body).map_err(|_| parse("negative KV3 body size"))?;
    r.skip(body)
}

fn parse(context: impl Into<String>) -> Error {
    Error::Parse {
        context: format!("nav: {context}", context = context.into()),
    }
}

/// A little-endian, bounds-checked cursor over a byte slice.
struct Reader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn new(data: &'a [u8]) -> Reader<'a> {
        Reader { data, pos: 0 }
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        let end = self
            .pos
            .checked_add(n)
            .ok_or_else(|| parse("length overflow"))?;
        let slice = self
            .data
            .get(self.pos..end)
            .ok_or_else(|| parse("unexpected end of data"))?;
        self.pos = end;
        Ok(slice)
    }

    fn skip(&mut self, n: usize) -> Result<()> {
        self.take(n).map(|_| ())
    }

    /// Advance to the next 8-byte boundary (KV3 documents are so aligned).
    fn align8(&mut self) {
        self.pos = (self.pos + 7) & !7;
    }

    /// Skip a null-terminated byte string, including its terminator.
    fn skip_cstring(&mut self) -> Result<()> {
        while self.u8()? != 0 {}
        Ok(())
    }

    fn u8(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }

    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }

    fn i32(&mut self) -> Result<i32> {
        Ok(i32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }

    fn i64(&mut self) -> Result<i64> {
        Ok(i64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }

    fn f32(&mut self) -> Result<f32> {
        Ok(f32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }

    fn vec3(&mut self) -> Result<Vec3> {
        Ok([self.f32()?, self.f32()?, self.f32()?])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Encode a minimal version-35 nav with `areas`, where each area is
    /// `(area_id, square corners, connections)`. Squares are axis-aligned unit
    /// quads so point-in-polygon is easy to reason about.
    fn encode_nav(areas: &[(u32, [Vec3; 4], &[u32])]) -> Vec<u8> {
        encode_nav_version(35, areas)
    }

    /// Emit a minimal empty KV3 v5 document (uncompressed, 9 bytes of body),
    /// matching the placeholder blocks in shipped version-36 navs.
    fn push_kv3(b: &mut Vec<u8>) {
        while !b.len().is_multiple_of(8) {
            b.push(0);
        }
        let pu32 = |b: &mut Vec<u8>, v: u32| b.extend_from_slice(&v.to_le_bytes());
        let pi32 = |b: &mut Vec<u8>, v: i32| b.extend_from_slice(&v.to_le_bytes());
        pu32(b, 0x4B56_3305); // MAGIC5
        b.extend_from_slice(&[0u8; 16]); // format GUID
        pu32(b, 0); // method = uncompressed
        b.extend_from_slice(&[0u8; 4]); // dict id + frame size
        b.extend_from_slice(&[0u8; 16]); // countBytes1/4/8 + countTypes
        b.extend_from_slice(&[0u8; 4]); // countObjects + countArrays
        pi32(b, 9); // size_uncompressed_total
        pi32(b, 0); // size_compressed_total
        pi32(b, 0); // n_blocks
        pi32(b, 0); // n_blobs
        b.extend_from_slice(&[0u8; 4]); // countBytes2 (v>=4)
        pi32(b, 0); // size_block_compressed (v>=4)
        pi32(b, 4); // uncompressed buffer 1 (v>=5)
        pi32(b, 0); // compressed buffer 1
        pi32(b, 5); // uncompressed buffer 2
        pi32(b, 0); // compressed buffer 2
        b.extend_from_slice(&[0u8; 32]); // eight trailing count fields
        b.extend_from_slice(&[0u8; 9]); // the 4 + 5 bytes of buffer body
    }

    fn encode_nav_version(version: u32, areas: &[(u32, [Vec3; 4], &[u32])]) -> Vec<u8> {
        let mut b = Vec::new();
        let push_u32 = |b: &mut Vec<u8>, v: u32| b.extend_from_slice(&v.to_le_bytes());
        let push_i64 = |b: &mut Vec<u8>, v: i64| b.extend_from_slice(&v.to_le_bytes());
        let push_f32 = |b: &mut Vec<u8>, v: f32| b.extend_from_slice(&v.to_le_bytes());

        push_u32(&mut b, MAGIC);
        push_u32(&mut b, version);
        push_u32(&mut b, 1); // sub_version
        push_u32(&mut b, 1); // unk1 -> is_analyzed

        if version >= 36 {
            push_kv3(&mut b); // KV3Unknown1
        }

        // Polygon table: one 4-corner polygon per area.
        let total_corners: u32 = areas.len() as u32 * 4;
        push_u32(&mut b, total_corners);
        for (_, corners, _) in areas {
            for c in corners {
                push_f32(&mut b, c[0]);
                push_f32(&mut b, c[1]);
                push_f32(&mut b, c[2]);
            }
        }
        push_u32(&mut b, areas.len() as u32); // polygon_count
        for (i, _) in areas.iter().enumerate() {
            b.push(4); // corner count
            for k in 0..4u32 {
                push_u32(&mut b, i as u32 * 4 + k);
            }
            if version >= 35 {
                push_u32(&mut b, 0); // per-polygon unk
            }
        }

        if version >= 32 {
            push_u32(&mut b, 0); // unk2
        }
        if version >= 35 {
            push_u32(&mut b, 0); // string-table count = 0
        }
        if version >= 36 {
            push_kv3(&mut b); // KV3Unknown2
        }

        push_u32(&mut b, areas.len() as u32); // area_count
        for (i, (area_id, _, conns)) in areas.iter().enumerate() {
            push_u32(&mut b, *area_id);
            push_i64(&mut b, 0); // dynamic_attribute_flags
            b.push(0); // hull_index
            push_u32(&mut b, i as u32); // polygon_index
            push_u32(&mut b, 0); // skip
            // Connections: put them all on the first edge, none on the others.
            push_u32(&mut b, conns.len() as u32);
            for &c in *conns {
                push_u32(&mut b, c); // neighbor area id
                push_u32(&mut b, 0); // edge id
            }
            for _ in 1..4 {
                push_u32(&mut b, 0); // no connections on remaining edges
            }
            b.extend_from_slice(&[0u8; 5]); // legacy hiding/encounter counts
            push_u32(&mut b, 0); // ladders_above count
            push_u32(&mut b, 0); // ladders_below count
        }
        b
    }

    fn square(x: f32, y: f32, z: f32) -> [Vec3; 4] {
        [
            [x, y, z],
            [x + 1.0, y, z],
            [x + 1.0, y + 1.0, z],
            [x, y + 1.0, z],
        ]
    }

    #[test]
    fn parses_header_and_areas() {
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2]),
            (2, square(1.0, 0.0, 0.0), &[1]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.version, 35);
        assert_eq!(nav.sub_version, 1);
        assert!(nav.is_analyzed);
        assert_eq!(nav.area_count(), 2);
        assert_eq!(nav.area(1).unwrap().corners.len(), 4);
        assert_eq!(nav.neighbors(1), vec![2]);
    }

    #[test]
    fn parses_v36_with_embedded_kv3() {
        // Version 36 wraps the areas in two empty KV3 documents; parsing must
        // skip past them and still read areas + connections correctly.
        let bytes = encode_nav_version(
            36,
            &[
                (1, square(0.0, 0.0, 0.0), &[2]),
                (2, square(1.0, 0.0, 0.0), &[1]),
            ],
        );
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.version, 36);
        assert_eq!(nav.area_count(), 2);
        assert_eq!(nav.neighbors(1), vec![2]);
        assert_eq!(nav.find_area([0.5, 0.5, 0.0]), Some(1));
        assert_eq!(nav.find_path(1, 2, PathWeight::Distance), vec![1, 2]);
    }

    #[test]
    fn centroid_and_size() {
        let bytes = encode_nav(&[(1, square(0.0, 0.0, 5.0), &[])]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        let area = nav.area(1).unwrap();
        assert_eq!(area.centroid(), [0.5, 0.5, 5.0]);
        assert!((area.size() - 1.0).abs() < 1e-6);
    }

    #[test]
    fn find_area_picks_containing_polygon() {
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[]),
            (2, square(10.0, 10.0, 0.0), &[]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.find_area([0.5, 0.5, 0.0]), Some(1));
        assert_eq!(nav.find_area([10.5, 10.5, 0.0]), Some(2));
        assert_eq!(nav.find_area([100.0, 100.0, 0.0]), None);
    }

    #[test]
    fn find_area_disambiguates_by_height() {
        // Two areas overlapping in XY at different heights (a bridge over a floor).
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[]),
            (2, square(0.0, 0.0, 100.0), &[]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.find_area([0.5, 0.5, 5.0]), Some(1));
        assert_eq!(nav.find_area([0.5, 0.5, 95.0]), Some(2));
    }

    #[test]
    fn find_path_across_chain() {
        // 1 -> 2 -> 3 chain of adjacent squares.
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2]),
            (2, square(1.0, 0.0, 0.0), &[1, 3]),
            (3, square(2.0, 0.0, 0.0), &[2]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.find_path(1, 3, PathWeight::Distance), vec![1, 2, 3]);
        assert_eq!(nav.find_path(1, 1, PathWeight::Hops), vec![1]);
        assert_eq!(nav.find_path(3, 1, PathWeight::Hops), vec![3, 2, 1]);
    }

    #[test]
    fn multi_source_distances_picks_nearest_source() {
        // 1 -> 2 -> 3 -> 4 chain; sources at both ends. Each interior area takes
        // the distance to whichever end is nearer.
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2]),
            (2, square(1.0, 0.0, 0.0), &[1, 3]),
            (3, square(2.0, 0.0, 0.0), &[2, 4]),
            (4, square(3.0, 0.0, 0.0), &[3]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        let d = nav.multi_source_distances(&[1, 4], PathWeight::Hops, &HashSet::new());
        assert_eq!(d[&1], 0.0);
        assert_eq!(d[&4], 0.0);
        assert_eq!(d[&2], 1.0);
        assert_eq!(d[&3], 1.0);
    }

    #[test]
    fn multi_source_distances_respects_blocked() {
        // 1 -> 2 -> 3; blocking 2 cuts 3 off from a source at 1.
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2]),
            (2, square(1.0, 0.0, 0.0), &[1, 3]),
            (3, square(2.0, 0.0, 0.0), &[2]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        let blocked: HashSet<u32> = [2u32].into_iter().collect();
        let d = nav.multi_source_distances(&[1], PathWeight::Hops, &blocked);
        assert!(d.contains_key(&1));
        assert!(!d.contains_key(&2));
        assert!(!d.contains_key(&3));
    }

    #[test]
    fn find_path_no_route_is_empty() {
        // 1 -> 2, and an isolated 3.
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2]),
            (2, square(1.0, 0.0, 0.0), &[1]),
            (3, square(5.0, 0.0, 0.0), &[]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert!(nav.find_path(1, 3, PathWeight::Distance).is_empty());
        assert!(nav.find_path(1, 99, PathWeight::Distance).is_empty());
    }

    #[test]
    fn find_path_prefers_shorter_distance() {
        // 1 connects to 2 (far) and 3 (near); both reach 4. Distance weighting
        // should route 1 -> 3 -> 4, not 1 -> 2 -> 4.
        let bytes = encode_nav(&[
            (1, square(0.0, 0.0, 0.0), &[2, 3]),
            (2, square(0.0, 100.0, 0.0), &[4]),
            (3, square(1.0, 0.0, 0.0), &[4]),
            (4, square(2.0, 0.0, 0.0), &[]),
        ]);
        let nav = Nav::from_bytes(&bytes).unwrap();
        assert_eq!(nav.find_path(1, 4, PathWeight::Distance), vec![1, 3, 4]);
    }

    #[test]
    fn rejects_bad_magic() {
        let err = Nav::from_bytes(&[0u8; 32]).unwrap_err();
        assert!(matches!(err, Error::Parse { .. }));
    }

    #[test]
    fn rejects_unsupported_version() {
        let mut b = Vec::new();
        b.extend_from_slice(&MAGIC.to_le_bytes());
        b.extend_from_slice(&20u32.to_le_bytes()); // too old
        b.extend_from_slice(&[0u8; 8]);
        assert!(matches!(Nav::from_bytes(&b), Err(Error::Parse { .. })));
    }

    #[test]
    fn rejects_truncated_data() {
        let bytes = encode_nav(&[(1, square(0.0, 0.0, 0.0), &[2])]);
        assert!(Nav::from_bytes(&bytes[..bytes.len() - 4]).is_err());
    }

    /// Loads a real `.nav` (set `AWPY_NAV_FILE`), parses it, and exercises the
    /// queries. Ignored by default; run with `--ignored --nocapture`.
    #[test]
    #[ignore = "requires AWPY_NAV_FILE to point at a real .nav file"]
    fn load_real_nav() {
        let path = std::env::var("AWPY_NAV_FILE").unwrap();
        let nav = Nav::from_file(Path::new(&path)).unwrap();
        assert!(nav.area_count() > 100);
        println!(
            "v{}.{} analyzed={} areas={}",
            nav.version,
            nav.sub_version,
            nav.is_analyzed,
            nav.area_count()
        );

        // Every connection should point at a real area.
        let mut dangling = 0;
        for area in &nav.areas {
            for &c in &area.connections {
                if nav.area(c).is_none() {
                    dangling += 1;
                }
            }
        }
        println!("dangling connections: {dangling}");

        // A point at some area's centroid should resolve back to that area.
        let a0 = &nav.areas[0];
        let c = a0.centroid();
        let found = nav.find_area(c);
        println!("centroid of area {} -> find_area {:?}", a0.area_id, found);
        assert!(found.is_some());
    }
}

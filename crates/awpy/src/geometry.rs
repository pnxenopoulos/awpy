//! Map collision geometry and line-of-sight queries.
//!
//! `awpy-data` extracts each map's `world_physics` collision mesh — reduced to
//! the *visual* occluders (clip brushes, sky, and see-through surfaces removed),
//! deduplicated, and stored as a compact indexed triangle mesh. This module
//! loads that mesh and answers visibility queries: given two world points, is
//! the straight segment between them unobstructed?
//!
//! Coordinates are Hammer units, Z-up — the same frame as
//! [`Entity::world_position`](crate::Entity::world_position), so entity
//! positions can be passed in directly.
//!
//! Ray casts are accelerated by a bounding-volume hierarchy (BVH) over the
//! triangles, so a query is `O(log n)` in the triangle count rather than
//! `O(n)`.
//!
//! ```
//! use awpy::geometry::{Mesh, VisibilityMesh};
//!
//! // A single wall quad in the x = 0 plane, spanning y,z in [-10, 10].
//! let mesh = Mesh {
//!     vertices: vec![
//!         [0.0, -10.0, -10.0],
//!         [0.0, 10.0, -10.0],
//!         [0.0, 10.0, 10.0],
//!         [0.0, -10.0, 10.0],
//!     ],
//!     triangles: vec![[0, 1, 2], [0, 2, 3]],
//! };
//! let vis = VisibilityMesh::build(mesh);
//!
//! // Opposite sides of the wall: blocked.
//! assert!(!vis.is_visible([-5.0, 0.0, 0.0], [5.0, 0.0, 0.0]));
//! // Same side: clear.
//! assert!(vis.is_visible([-5.0, 0.0, 0.0], [-5.0, 5.0, 0.0]));
//! ```

use std::path::Path;

use crate::error::{Error, Result};

/// Magic bytes at the start of an awpy `.mesh` file.
const MAGIC: &[u8; 4] = b"AWMH";
/// Mesh format version this loader understands.
const FORMAT_VERSION: u32 = 1;

/// Maximum triangles in a BVH leaf before it is split.
const LEAF_SIZE: usize = 4;
/// Segment fraction ignored at each endpoint, so a point resting on a surface
/// doesn't count as occluding the segment that starts or ends there.
const SEG_EPS: f32 = 1e-4;
/// Determinant below which a ray is treated as parallel to a triangle.
const PARALLEL_EPS: f32 = 1e-8;

type Vec3 = [f32; 3];

#[inline]
fn sub(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

#[inline]
fn dot(a: Vec3, b: Vec3) -> f32 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

#[inline]
fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

/// An axis-aligned bounding box.
#[derive(Clone, Copy, Debug)]
struct Aabb {
    min: Vec3,
    max: Vec3,
}

impl Aabb {
    /// An inverted (empty) box that grows to fit whatever is added to it.
    const EMPTY: Aabb = Aabb {
        min: [f32::INFINITY; 3],
        max: [f32::NEG_INFINITY; 3],
    };

    #[inline]
    fn expand(&mut self, p: Vec3) {
        for (a, &c) in p.iter().enumerate() {
            self.min[a] = self.min[a].min(c);
            self.max[a] = self.max[a].max(c);
        }
    }

    #[inline]
    fn union(&self, other: &Aabb) -> Aabb {
        let mut out = *self;
        out.expand(other.min);
        out.expand(other.max);
        out
    }

    #[inline]
    fn centroid(&self) -> Vec3 {
        [
            0.5 * (self.min[0] + self.max[0]),
            0.5 * (self.min[1] + self.max[1]),
            0.5 * (self.min[2] + self.max[2]),
        ]
    }

    /// Axis (0=x, 1=y, 2=z) along which the box is widest.
    #[inline]
    fn longest_axis(&self) -> usize {
        let ext = [
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        ];
        if ext[0] >= ext[1] && ext[0] >= ext[2] {
            0
        } else if ext[1] >= ext[2] {
            1
        } else {
            2
        }
    }

    /// Does the ray `origin + t*dir` intersect this box for some `t` in
    /// `[t0, t1]`? Uses the branchless slab test; `dir` components of zero are
    /// handled correctly via IEEE infinities.
    #[inline]
    #[allow(clippy::needless_range_loop)]
    fn hit(&self, origin: Vec3, dir: Vec3, t0: f32, t1: f32) -> bool {
        let mut tmin = t0;
        let mut tmax = t1;
        for a in 0..3 {
            let inv = 1.0 / dir[a];
            let mut ta = (self.min[a] - origin[a]) * inv;
            let mut tb = (self.max[a] - origin[a]) * inv;
            if inv < 0.0 {
                std::mem::swap(&mut ta, &mut tb);
            }
            tmin = tmin.max(ta);
            tmax = tmax.min(tb);
            if tmax < tmin {
                return false;
            }
        }
        true
    }
}

/// An indexed triangle mesh in Hammer units (Z-up).
#[derive(Clone, Debug, Default)]
pub struct Mesh {
    /// Vertex positions.
    pub vertices: Vec<Vec3>,
    /// Triangles, as triples of indices into [`vertices`](Mesh::vertices).
    pub triangles: Vec<[u32; 3]>,
}

impl Mesh {
    /// Parse a mesh from the compact awpy `.mesh` byte layout.
    ///
    /// Layout (little-endian): `b"AWMH"`, `version: u32`, `n_verts: u32`,
    /// `n_tris: u32`, then `n_verts * 3` `f32` positions and `n_tris * 3`
    /// `u32` indices.
    pub fn from_bytes(data: &[u8]) -> Result<Mesh> {
        let parse = |context: &str| Error::Parse {
            context: format!("mesh: {context}"),
        };
        if data.len() < 16 {
            return Err(parse("truncated header"));
        }
        if &data[0..4] != MAGIC {
            return Err(parse("bad magic (expected AWMH)"));
        }
        let read_u32 = |off: usize| u32::from_le_bytes(data[off..off + 4].try_into().unwrap());
        let version = read_u32(4);
        if version != FORMAT_VERSION {
            return Err(parse(&format!("unsupported version {version}")));
        }
        let n_verts = read_u32(8) as usize;
        let n_tris = read_u32(12) as usize;

        let verts_bytes = n_verts * 12;
        let tris_bytes = n_tris * 12;
        if data.len() < 16 + verts_bytes + tris_bytes {
            return Err(parse("truncated body"));
        }

        let mut vertices = Vec::with_capacity(n_verts);
        let mut off = 16;
        for _ in 0..n_verts {
            let x = f32::from_le_bytes(data[off..off + 4].try_into().unwrap());
            let y = f32::from_le_bytes(data[off + 4..off + 8].try_into().unwrap());
            let z = f32::from_le_bytes(data[off + 8..off + 12].try_into().unwrap());
            vertices.push([x, y, z]);
            off += 12;
        }

        let mut triangles = Vec::with_capacity(n_tris);
        for _ in 0..n_tris {
            let a = u32::from_le_bytes(data[off..off + 4].try_into().unwrap());
            let b = u32::from_le_bytes(data[off + 4..off + 8].try_into().unwrap());
            let c = u32::from_le_bytes(data[off + 8..off + 12].try_into().unwrap());
            if a as usize >= n_verts || b as usize >= n_verts || c as usize >= n_verts {
                return Err(parse("triangle index out of range"));
            }
            triangles.push([a, b, c]);
            off += 12;
        }

        Ok(Mesh {
            vertices,
            triangles,
        })
    }

    /// Load a mesh from an awpy `.mesh` file.
    pub fn from_file(path: &Path) -> Result<Mesh> {
        Mesh::from_bytes(&std::fs::read(path)?)
    }
}

/// A BVH node. Leaves store a run of triangles in the reordered index array;
/// internal nodes store their two child indices.
#[derive(Clone, Copy, Debug)]
struct BvhNode {
    aabb: Aabb,
    /// Leaf: first triangle in `order`. Internal: unused.
    start: u32,
    /// Number of triangles in a leaf; `0` marks an internal node.
    count: u32,
    /// Internal: left child index in `nodes`.
    left: u32,
    /// Internal: right child index in `nodes`.
    right: u32,
}

impl BvhNode {
    #[inline]
    fn is_leaf(&self) -> bool {
        self.count > 0
    }
}

/// A [`Mesh`] with a BVH built over it, ready for visibility queries.
pub struct VisibilityMesh {
    vertices: Vec<Vec3>,
    triangles: Vec<[u32; 3]>,
    nodes: Vec<BvhNode>,
    /// Triangle indices, reordered so each leaf owns a contiguous run.
    order: Vec<u32>,
}

impl VisibilityMesh {
    /// Load a mesh file and build its BVH.
    pub fn from_file(path: &Path) -> Result<VisibilityMesh> {
        Ok(VisibilityMesh::build(Mesh::from_file(path)?))
    }

    /// Number of triangles in the mesh.
    pub fn triangle_count(&self) -> usize {
        self.triangles.len()
    }

    /// Build a BVH over `mesh` using top-down median/midpoint splits.
    pub fn build(mesh: Mesh) -> VisibilityMesh {
        let Mesh {
            vertices,
            triangles,
        } = mesh;
        let n = triangles.len();

        // Per-triangle bounds and centroids, computed once.
        let mut tri_aabb = Vec::with_capacity(n);
        let mut centroid = Vec::with_capacity(n);
        for t in &triangles {
            let mut bb = Aabb::EMPTY;
            bb.expand(vertices[t[0] as usize]);
            bb.expand(vertices[t[1] as usize]);
            bb.expand(vertices[t[2] as usize]);
            centroid.push(bb.centroid());
            tri_aabb.push(bb);
        }

        let mut order: Vec<u32> = (0..n as u32).collect();
        let mut nodes = Vec::new();
        if n > 0 {
            build_recursive(&mut nodes, &mut order, 0, n, &centroid, &tri_aabb);
        }

        VisibilityMesh {
            vertices,
            triangles,
            nodes,
            order,
        }
    }

    /// Is the straight segment from `a` to `b` clear of geometry?
    pub fn is_visible(&self, a: Vec3, b: Vec3) -> bool {
        !self.is_occluded(a, b)
    }

    /// Does any triangle block the segment from `a` to `b`?
    pub fn is_occluded(&self, a: Vec3, b: Vec3) -> bool {
        if self.nodes.is_empty() {
            return false;
        }
        let dir = sub(b, a);
        if dir == [0.0, 0.0, 0.0] {
            return false;
        }

        // Iterative traversal; a small stack easily covers realistic depths.
        let mut stack: Vec<u32> = Vec::with_capacity(64);
        stack.push(0);
        while let Some(ni) = stack.pop() {
            let node = self.nodes[ni as usize];
            if !node.aabb.hit(a, dir, 0.0, 1.0) {
                continue;
            }
            if node.is_leaf() {
                let lo = node.start as usize;
                let hi = lo + node.count as usize;
                for &ti in &self.order[lo..hi] {
                    let t = self.triangles[ti as usize];
                    let (v0, v1, v2) = (
                        self.vertices[t[0] as usize],
                        self.vertices[t[1] as usize],
                        self.vertices[t[2] as usize],
                    );
                    if let Some(u) = moller_trumbore(a, dir, v0, v1, v2)
                        && u > SEG_EPS
                        && u < 1.0 - SEG_EPS
                    {
                        return true;
                    }
                }
            } else {
                stack.push(node.left);
                stack.push(node.right);
            }
        }
        false
    }
}

/// Möller–Trumbore ray/triangle intersection (two-sided). Returns the ray
/// parameter `t` (as a fraction of `dir`) of the hit, if any.
#[inline]
fn moller_trumbore(origin: Vec3, dir: Vec3, v0: Vec3, v1: Vec3, v2: Vec3) -> Option<f32> {
    let e1 = sub(v1, v0);
    let e2 = sub(v2, v0);
    let p = cross(dir, e2);
    let det = dot(e1, p);
    if det.abs() < PARALLEL_EPS {
        return None;
    }
    let inv_det = 1.0 / det;
    let s = sub(origin, v0);
    let u = dot(s, p) * inv_det;
    if !(0.0..=1.0).contains(&u) {
        return None;
    }
    let q = cross(s, e1);
    let v = dot(dir, q) * inv_det;
    if v < 0.0 || u + v > 1.0 {
        return None;
    }
    Some(dot(e2, q) * inv_det)
}

/// Recursively build BVH nodes over `order[start..end]`, returning the index
/// of the created node. Reorders `order` in place so each leaf is contiguous.
fn build_recursive(
    nodes: &mut Vec<BvhNode>,
    order: &mut [u32],
    start: usize,
    end: usize,
    centroid: &[Vec3],
    tri_aabb: &[Aabb],
) -> u32 {
    let mut bounds = Aabb::EMPTY;
    for &ti in &order[start..end] {
        bounds = bounds.union(&tri_aabb[ti as usize]);
    }

    let node_idx = nodes.len() as u32;
    nodes.push(BvhNode {
        aabb: bounds,
        start: start as u32,
        count: (end - start) as u32,
        left: 0,
        right: 0,
    });

    if end - start <= LEAF_SIZE {
        return node_idx;
    }

    // Split at the midpoint of the centroid bounds along their longest axis.
    let mut cbounds = Aabb::EMPTY;
    for &ti in &order[start..end] {
        cbounds.expand(centroid[ti as usize]);
    }
    let axis = cbounds.longest_axis();
    let split = 0.5 * (cbounds.min[axis] + cbounds.max[axis]);

    let mut mid = start
        + partition_by(&mut order[start..end], |ti| {
            centroid[ti as usize][axis] < split
        });

    // Degenerate split (all on one side): fall back to the median.
    if mid == start || mid == end {
        order[start..end].sort_unstable_by(|&a, &b| {
            centroid[a as usize][axis]
                .partial_cmp(&centroid[b as usize][axis])
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        mid = start + (end - start) / 2;
    }

    let left = build_recursive(nodes, order, start, mid, centroid, tri_aabb);
    let right = build_recursive(nodes, order, mid, end, centroid, tri_aabb);
    let node = &mut nodes[node_idx as usize];
    node.left = left;
    node.right = right;
    node.count = 0; // now an internal node
    node_idx
}

/// In-place partition: move elements satisfying `pred` to the front, returning
/// how many there are.
fn partition_by<F: Fn(u32) -> bool>(slice: &mut [u32], pred: F) -> usize {
    let mut i = 0;
    for j in 0..slice.len() {
        if pred(slice[j]) {
            slice.swap(i, j);
            i += 1;
        }
    }
    i
}

#[cfg(test)]
mod tests {
    use super::*;

    /// One wall quad in the x = 0 plane, spanning y,z in [-10, 10].
    fn wall() -> Mesh {
        Mesh {
            vertices: vec![
                [0.0, -10.0, -10.0],
                [0.0, 10.0, -10.0],
                [0.0, 10.0, 10.0],
                [0.0, -10.0, 10.0],
            ],
            triangles: vec![[0, 1, 2], [0, 2, 3]],
        }
    }

    #[test]
    fn segment_through_wall_is_occluded() {
        let vis = VisibilityMesh::build(wall());
        assert!(vis.is_occluded([-5.0, 0.0, 0.0], [5.0, 0.0, 0.0]));
        assert!(!vis.is_visible([-5.0, 0.0, 0.0], [5.0, 0.0, 0.0]));
    }

    #[test]
    fn segment_on_same_side_is_visible() {
        let vis = VisibilityMesh::build(wall());
        assert!(vis.is_visible([-5.0, 0.0, 0.0], [-5.0, 5.0, 0.0]));
    }

    #[test]
    fn segment_misses_wall_bounds() {
        let vis = VisibilityMesh::build(wall());
        // Crosses x = 0 but well outside the quad's y,z extent.
        assert!(vis.is_visible([-5.0, 50.0, 0.0], [5.0, 50.0, 0.0]));
    }

    #[test]
    fn endpoints_on_surface_do_not_self_occlude() {
        let vis = VisibilityMesh::build(wall());
        // A segment that ends on the wall plane should still be visible.
        assert!(vis.is_visible([-5.0, 0.0, 0.0], [0.0, 0.0, 0.0]));
    }

    /// A wall tiled into many quads, so the BVH has internal nodes (not just a
    /// single leaf). Guards the child-index wiring in the traversal.
    fn tiled_wall(n: u32) -> Mesh {
        let mut vertices = Vec::new();
        let mut triangles = Vec::new();
        let step = 100.0 / n as f32;
        for i in 0..n {
            for j in 0..n {
                let (y0, z0) = (i as f32 * step, j as f32 * step);
                let (y1, z1) = (y0 + step, z0 + step);
                let base = vertices.len() as u32;
                vertices.push([0.0, y0, z0]);
                vertices.push([0.0, y1, z0]);
                vertices.push([0.0, y1, z1]);
                vertices.push([0.0, y0, z1]);
                triangles.push([base, base + 1, base + 2]);
                triangles.push([base, base + 2, base + 3]);
            }
        }
        Mesh {
            vertices,
            triangles,
        }
    }

    #[test]
    fn traversal_visits_both_children() {
        let vis = VisibilityMesh::build(tiled_wall(10)); // 200 triangles
        assert!(vis.triangle_count() > LEAF_SIZE);
        // Through the tiled region (y,z in [0,100]): occluded.
        assert!(vis.is_occluded([-5.0, 55.0, 55.0], [5.0, 55.0, 55.0]));
        assert!(vis.is_occluded([-5.0, 5.0, 95.0], [5.0, 5.0, 95.0]));
        // Past the tiled region: clear.
        assert!(vis.is_visible([-5.0, 150.0, 55.0], [5.0, 150.0, 55.0]));
    }

    #[test]
    fn empty_mesh_never_occludes() {
        let vis = VisibilityMesh::build(Mesh::default());
        assert_eq!(vis.triangle_count(), 0);
        assert!(vis.is_visible([0.0, 0.0, 0.0], [100.0, 100.0, 100.0]));
    }

    #[test]
    fn round_trip_bytes() {
        let mesh = wall();
        // Hand-encode the format and read it back.
        let mut bytes = Vec::new();
        bytes.extend_from_slice(MAGIC);
        bytes.extend_from_slice(&FORMAT_VERSION.to_le_bytes());
        bytes.extend_from_slice(&(mesh.vertices.len() as u32).to_le_bytes());
        bytes.extend_from_slice(&(mesh.triangles.len() as u32).to_le_bytes());
        for v in &mesh.vertices {
            for c in v {
                bytes.extend_from_slice(&c.to_le_bytes());
            }
        }
        for t in &mesh.triangles {
            for i in t {
                bytes.extend_from_slice(&i.to_le_bytes());
            }
        }

        let loaded = Mesh::from_bytes(&bytes).unwrap();
        assert_eq!(loaded.vertices.len(), 4);
        assert_eq!(loaded.triangles, mesh.triangles);
    }

    #[test]
    fn bad_magic_is_rejected() {
        let err = Mesh::from_bytes(&[0u8; 16]).unwrap_err();
        assert!(matches!(err, Error::Parse { .. }));
    }

    #[test]
    fn out_of_range_index_is_rejected() {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(MAGIC);
        bytes.extend_from_slice(&FORMAT_VERSION.to_le_bytes());
        bytes.extend_from_slice(&1u32.to_le_bytes()); // 1 vertex
        bytes.extend_from_slice(&1u32.to_le_bytes()); // 1 triangle
        bytes.extend_from_slice(&[0u8; 12]); // one vertex at origin
        bytes.extend_from_slice(&0u32.to_le_bytes());
        bytes.extend_from_slice(&0u32.to_le_bytes());
        bytes.extend_from_slice(&5u32.to_le_bytes()); // index 5 out of range
        assert!(Mesh::from_bytes(&bytes).is_err());
    }

    /// Loads a real `.mesh` (set `AWPY_GEOMETRY_MESH`), builds the BVH, and
    /// benchmarks queries. Ignored by default; run with `--ignored --nocapture`
    /// to validate against extracted map data and see timings.
    #[test]
    #[ignore = "requires AWPY_GEOMETRY_MESH to point at a real .mesh file"]
    fn load_real_mesh() {
        use std::time::Instant;

        let path = std::env::var("AWPY_GEOMETRY_MESH").unwrap();
        let mesh = Mesh::from_file(Path::new(&path)).unwrap();
        assert!(mesh.triangles.len() > 10_000);

        // Bounds, for generating in-map query points.
        let mut bb = Aabb::EMPTY;
        for &v in &mesh.vertices {
            bb.expand(v);
        }

        let t0 = Instant::now();
        let vis = VisibilityMesh::build(mesh);
        let build = t0.elapsed();

        // Pseudo-random segment endpoints within the map bounds (LCG, no deps).
        let mut seed: u64 = 0x9e37_79b9_7f4a_7c15;
        let mut rnd = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            (seed >> 33) as f32 / (1u32 << 31) as f32
        };
        let point = |r: &mut dyn FnMut() -> f32| {
            [
                bb.min[0] + r() * (bb.max[0] - bb.min[0]),
                bb.min[1] + r() * (bb.max[1] - bb.min[1]),
                bb.min[2] + r() * (bb.max[2] - bb.min[2]),
            ]
        };

        let n = 100_000;
        let t1 = Instant::now();
        let mut occluded = 0usize;
        for _ in 0..n {
            let a = point(&mut rnd);
            let b = point(&mut rnd);
            if vis.is_occluded(a, b) {
                occluded += 1;
            }
        }
        let elapsed = t1.elapsed();

        println!(
            "tris={} build={:?} queries={} ({:.1}% occluded) total={:?} ({:.2} µs/query)",
            vis.triangle_count(),
            build,
            n,
            100.0 * occluded as f32 / n as f32,
            elapsed,
            elapsed.as_secs_f64() * 1e6 / n as f64,
        );
        assert!(vis.is_visible([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]));
    }

    /// Compares occlusion answers between a reference mesh
    /// (`AWPY_GEOMETRY_MESH`) and a candidate (`AWPY_GEOMETRY_MESH_B`, e.g. a
    /// decimated version) over random rays. Ignored by default.
    #[test]
    #[ignore = "requires AWPY_GEOMETRY_MESH and AWPY_GEOMETRY_MESH_B"]
    fn compare_meshes() {
        let ref_mesh =
            Mesh::from_file(Path::new(&std::env::var("AWPY_GEOMETRY_MESH").unwrap())).unwrap();
        let mut bb = Aabb::EMPTY;
        for &v in &ref_mesh.vertices {
            bb.expand(v);
        }
        let a = VisibilityMesh::build(ref_mesh);
        let b =
            VisibilityMesh::from_file(Path::new(&std::env::var("AWPY_GEOMETRY_MESH_B").unwrap()))
                .unwrap();

        let mut seed: u64 = 0x1234_5678_9abc_def0;
        let mut rnd = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            (seed >> 33) as f32 / (1u32 << 31) as f32
        };
        let point = |r: &mut dyn FnMut() -> f32| {
            [
                bb.min[0] + r() * (bb.max[0] - bb.min[0]),
                bb.min[1] + r() * (bb.max[1] - bb.min[1]),
                bb.min[2] + r() * (bb.max[2] - bb.min[2]),
            ]
        };

        let n = 200_000;
        let (mut disagree, mut occ_a, mut occ_b) = (0usize, 0usize, 0usize);
        for _ in 0..n {
            let (p, q) = (point(&mut rnd), point(&mut rnd));
            let (oa, ob) = (a.is_occluded(p, q), b.is_occluded(p, q));
            occ_a += oa as usize;
            occ_b += ob as usize;
            disagree += (oa != ob) as usize;
        }
        println!(
            "ref tris={} cand tris={} ({:.0}%) | disagree {:.2}% | occ ref {:.1}% cand {:.1}%",
            a.triangle_count(),
            b.triangle_count(),
            100.0 * b.triangle_count() as f32 / a.triangle_count() as f32,
            100.0 * disagree as f32 / n as f32,
            100.0 * occ_a as f32 / n as f32,
            100.0 * occ_b as f32 / n as f32,
        );
    }
}

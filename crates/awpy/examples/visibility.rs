//! Test line-of-sight visibility between two world points against a map mesh.
//!
//! The mesh is one of the compact `AWMH` `.mesh` files produced by awpy-data
//! (unzip a map from `geometry.zip`). Coordinates are Hammer units, Z-up — the
//! same frame as demo world positions, so you can paste entity positions in
//! directly.
//!
//! Usage:
//!   cargo run --release --example visibility -- <mesh>                     # stats + bounds
//!   cargo run --release --example visibility -- <mesh> ax ay az bx by bz   # is A->B clear?
//!
//! Example (de_inferno):
//!   cargo run --release --example visibility -- de_inferno.mesh \
//!       1258.04 455.47 181.22  -158.62 819.09 103.73

use std::path::Path;
use std::time::Instant;

use awpy::geometry::{Mesh, VisibilityMesh};

fn parse_coord(s: &str) -> f32 {
    s.parse().unwrap_or_else(|_| {
        eprintln!("error: '{s}' is not a number");
        std::process::exit(2);
    })
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 && args.len() != 8 {
        eprintln!(
            "usage:\n  \
             visibility <mesh>                      # triangle count + bounds\n  \
             visibility <mesh> ax ay az bx by bz    # is the segment A->B clear?"
        );
        std::process::exit(2);
    }

    let path = &args[1];
    let mesh = match Mesh::from_file(Path::new(path)) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("error: could not load {path}: {e}");
            std::process::exit(1);
        }
    };

    // Bounding box, so you know the coordinate range points must fall in.
    let (mut lo, mut hi) = ([f32::INFINITY; 3], [f32::NEG_INFINITY; 3]);
    for v in &mesh.vertices {
        for k in 0..3 {
            lo[k] = lo[k].min(v[k]);
            hi[k] = hi[k].max(v[k]);
        }
    }
    let (verts, tris) = (mesh.vertices.len(), mesh.triangles.len());

    let t0 = Instant::now();
    let vis = VisibilityMesh::build(mesh);
    let build = t0.elapsed();

    println!("mesh:   {path}");
    println!("geom:   {verts} verts, {tris} tris  (BVH built in {build:.1?})");
    println!(
        "bounds: x [{:.0}, {:.0}]   y [{:.0}, {:.0}]   z [{:.0}, {:.0}]",
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]
    );

    if args.len() == 2 {
        println!("\nPick two points inside those bounds, then:");
        println!("  cargo run --release --example visibility -- {path} ax ay az bx by bz");
        return;
    }

    let a = [
        parse_coord(&args[2]),
        parse_coord(&args[3]),
        parse_coord(&args[4]),
    ];
    let b = [
        parse_coord(&args[5]),
        parse_coord(&args[6]),
        parse_coord(&args[7]),
    ];

    let t1 = Instant::now();
    let visible = vis.is_visible(a, b);
    let q = t1.elapsed();

    println!("\nA {a:?}");
    println!("B {b:?}");
    println!(
        "line of sight: {}   (query {q:.2?})",
        if visible {
            "VISIBLE — clear"
        } else {
            "BLOCKED — occluded"
        }
    );
}

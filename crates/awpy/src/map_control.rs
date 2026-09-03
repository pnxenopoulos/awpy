//! Map control: how much of the map each team holds at a single moment.
//!
//! *Map control* turns a snapshot of player positions into a partition of the
//! navigation mesh: every walkable [`NavArea`](crate::nav::NavArea) is labelled
//! [`Control::Ct`], [`Control::T`], [`Control::Contested`] (both teams hold it),
//! or [`Control::Neutral`] (neither does). Aggregated and weighted by area size,
//! that yields a single, interpretable "fraction of the map controlled" per
//! team — and its signed difference, [`MapControl::net_control`], is a compact
//! momentum series you can plot over a round.
//!
//! Three models are offered, because "control" means more than one thing:
//!
//! - [`raycast_control`] — *what a team could see.* An area is controlled by a
//!   side if any living, un-blinded player on it has line of sight to the area (a
//!   ray through the map's collision [`VisibilityMesh`]), **in any direction**.
//!   Active smoke clouds are passed as [`Occluder`] spheres and block the rays
//!   through them; blinded players (caught in a flash) project no vision. An area
//!   seen by both sides is contested.
//!
//! - [`vision_control`] — *what a team can actually see right now.* The same
//!   rays, additionally restricted to each player's field of view: within
//!   [`Params::fov`] / 2 degrees of their [`Observer::yaw`] (default 90°, CS2's
//!   own FOV). A player watching one angle no longer holds the space behind them,
//!   so this reports a good deal less control than [`raycast_control`].
//!
//! - [`reachability_control`] — *what space a team can take first.* A
//!   multi-source shortest-path search over the nav graph gives, for every area,
//!   the travel distance from the nearest player of each side; whichever side can
//!   arrive first owns it, a near-tie is contested, and unreachable space is
//!   neutral. Burning infernos are passed as [`Occluder`] spheres and mark the
//!   areas under them impassable, so paths route around denied ground.
//!
//! All three take feet positions in Hammer units (Z-up) — the frame of the demo's
//! world-position columns — and return the same [`MapControl`], so a caller can
//! compute and compare them from one snapshot.
//!
//! ```no_run
//! use awpy::geometry::VisibilityMesh;
//! use awpy::map_control::{vision_control, Observer, Params, Team};
//! use awpy::nav::Nav;
//!
//! let nav = Nav::from_file("de_inferno.nav".as_ref()).unwrap();
//! let mesh = VisibilityMesh::from_file("de_inferno.mesh".as_ref()).unwrap();
//! // `yaw` is where the player is looking, which `vision_control` needs for the
//! // field-of-view cone; `None` leaves them unrestricted.
//! let observers = vec![
//!     Observer {
//!         pos: [-1200.0, 500.0, 100.0],
//!         team: Team::Ct,
//!         crouched: false,
//!         blind: false,
//!         yaw: Some(180.0),
//!     },
//!     Observer {
//!         pos: [1500.0, 2500.0, 130.0],
//!         team: Team::T,
//!         crouched: false,
//!         blind: false,
//!         yaw: Some(0.0),
//!     },
//! ];
//! let mc = vision_control(&nav, &mesh, &observers, &[], &Params::default());
//! println!("CT holds {:.0}% of the map", 100.0 * mc.ct_fraction);
//! ```

use std::collections::HashSet;

use crate::geometry::VisibilityMesh;
use crate::nav::{Nav, NavArea, PathWeight};

type Vec3 = [f32; 3];

#[inline]
fn sub(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

#[inline]
fn dot(a: Vec3, b: Vec3) -> f32 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

/// Which side a player is on. (The unassigned / spectator teams don't hold map
/// control, so callers filter them out before building [`Observer`]s.)
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Team {
    /// Counter-Terrorists.
    Ct,
    /// Terrorists.
    T,
}

/// The control label assigned to one navigation area.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Control {
    /// Held by the Counter-Terrorists alone.
    Ct,
    /// Held by the Terrorists alone.
    T,
    /// Held by both sides at once.
    Contested,
    /// Held by neither side.
    Neutral,
}

impl Control {
    /// Classify an area from whether each side holds it. Both → contested,
    /// one → that side, neither → neutral.
    #[inline]
    fn from_holds(ct: bool, t: bool) -> Control {
        match (ct, t) {
            (true, true) => Control::Contested,
            (true, false) => Control::Ct,
            (false, true) => Control::T,
            (false, false) => Control::Neutral,
        }
    }

    /// Lower-case string label (`"ct"`, `"t"`, `"contested"`, `"neutral"`).
    pub fn as_str(self) -> &'static str {
        match self {
            Control::Ct => "ct",
            Control::T => "t",
            Control::Contested => "contested",
            Control::Neutral => "neutral",
        }
    }
}

/// One player's contribution to map control: a feet position and their side,
/// plus the state that changes what they contribute.
#[derive(Clone, Copy, Debug)]
pub struct Observer {
    /// Feet position `[x, y, z]` in Hammer units (Z-up).
    pub pos: Vec3,
    /// Which side the player is on.
    pub team: Team,
    /// Whether the player is crouched (lowers their eye height for vision).
    pub crouched: bool,
    /// Whether the player is currently blinded by a flash. A blinded player
    /// projects no vision (ignored by [`raycast_control`] and [`vision_control`])
    /// but still occupies space (counted by [`reachability_control`]).
    pub blind: bool,
    /// Where the player is looking: eye-angle yaw in degrees, measured the way
    /// the demo reports it (0° = +x, increasing counter-clockwise).
    ///
    /// Only [`vision_control`] uses this, to restrict what the player sees to
    /// their field of view. `None` means the direction is unknown, in which case
    /// no field-of-view limit is applied and the player sees in every direction —
    /// the same treatment [`raycast_control`] always gives.
    pub yaw: Option<f32>,
}

/// A spherical region that affects control: a smoke cloud (blocks the rays cast
/// by [`raycast_control`] and [`vision_control`]) or a burning inferno (blocks movement in
/// [`reachability_control`]). Callers place and size the sphere — e.g. a smoke
/// centred a little above where it landed, a molotov at the fire's footprint.
#[derive(Clone, Copy, Debug)]
pub struct Occluder {
    /// Sphere centre `[x, y, z]` in Hammer units.
    pub center: Vec3,
    /// Sphere radius in Hammer units.
    pub radius: f32,
}

/// Tunable parameters shared by the three models (see field docs for the
/// defaults; each model ignores the ones that don't apply to it).
#[derive(Clone, Copy, Debug)]
pub struct Params {
    /// Eye height above the feet for a standing player, in Hammer units
    /// (default `64.0`). Vision rays start here, not at the floor.
    pub eye_height: f32,
    /// Eye height above the feet for a crouched player (default `46.0`).
    pub crouch_eye_height: f32,
    /// Height above an area's floor at which vision *targets* it, in Hammer units
    /// (default `46.0`). Modelling "would I see a player standing on this tile"
    /// (chest height) rather than the floor itself, which low cover often hides.
    pub target_height: f32,
    /// Optional cap on vision range, in Hammer units (default `None`, i.e.
    /// unbounded). When set, an area farther than this from every one of a side's
    /// players is not counted as seen, even with clear line of sight.
    pub max_distance: Option<f32>,
    /// Reachability tie band, in Hammer units of travel distance (default
    /// `200.0`). When the two sides' travel distances to an area differ by no
    /// more than this, the area is contested rather than awarded to the nearer
    /// side.
    pub contest_margin: f64,
    /// Horizontal field of view in degrees, used only by [`vision_control`]
    /// (default `90.0`, matching CS2's default FOV). An area counts as seen only
    /// if it falls within `fov / 2` either side of where the player is looking.
    ///
    /// A value of `360.0` or more removes the limit, making [`vision_control`]
    /// equivalent to [`raycast_control`].
    pub fov: f32,
}

impl Default for Params {
    fn default() -> Params {
        Params {
            eye_height: 64.0,
            crouch_eye_height: 46.0,
            target_height: 46.0,
            max_distance: None,
            contest_margin: 200.0,
            fov: 90.0,
        }
    }
}

impl Params {
    /// The eye position of an observer (feet raised by the standing or crouched
    /// eye height).
    #[inline]
    fn eye(&self, o: &Observer) -> Vec3 {
        let h = if o.crouched {
            self.crouch_eye_height
        } else {
            self.eye_height
        };
        [o.pos[0], o.pos[1], o.pos[2] + h]
    }
}

/// The control label for one navigation area.
#[derive(Clone, Copy, Debug)]
pub struct AreaControl {
    /// The area's ID in the [`Nav`].
    pub area_id: u32,
    /// The area's overall label.
    pub control: Control,
    /// Whether the CT side holds the area (alone or contested).
    pub ct: bool,
    /// Whether the T side holds the area (alone or contested).
    pub t: bool,
}

/// The map-control partition for one snapshot: a label per area, plus
/// size-weighted summary fractions.
///
/// The four fractions weight each area by its 2D [`size`](crate::nav::NavArea::size)
/// and sum to 1 (a map with no area is all-neutral). [`net_control`](Self::net_control)
/// is `ct_fraction - t_fraction`.
#[derive(Clone, Debug)]
pub struct MapControl {
    /// Per-area labels, in the nav's area order.
    pub areas: Vec<AreaControl>,
    /// Fraction of the map (by area) the CT side holds alone.
    pub ct_fraction: f32,
    /// Fraction of the map (by area) the T side holds alone.
    pub t_fraction: f32,
    /// Fraction of the map (by area) both sides hold at once.
    pub contested_fraction: f32,
    /// Fraction of the map (by area) neither side holds.
    pub neutral_fraction: f32,
    /// `ct_fraction - t_fraction`: a signed measure of who controls more.
    pub net_control: f32,
}

/// Does the segment `a`–`b` pass within `radius` of `center`? (Closest-point
/// test between the segment and the sphere centre.)
#[inline]
fn segment_hits_sphere(a: Vec3, b: Vec3, center: Vec3, radius: f32) -> bool {
    let ab = sub(b, a);
    let len2 = dot(ab, ab);
    // Parameter of the closest point on the segment, clamped to `[0, 1]`.
    let t = if len2 <= f32::EPSILON {
        0.0
    } else {
        (dot(sub(center, a), ab) / len2).clamp(0.0, 1.0)
    };
    let closest = [a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t];
    let d = sub(closest, center);
    dot(d, d) <= radius * radius
}

/// One player's viewpoint: where their eyes are, and (for the field-of-view
/// model) where they are looking.
#[derive(Clone, Copy, Debug)]
struct Eye {
    pos: Vec3,
    yaw: Option<f32>,
}

/// Is `target` within `half_cos` of where an eye at `eye` is looking?
///
/// `half_cos` is the cosine of half the field of view, precomputed once so this
/// costs a dot product per area rather than a trig call. The test is **horizontal
/// only** — it compares yaw against the bearing to the target and ignores pitch,
/// because a player's vertical view is a function of their aspect ratio and the
/// demo's yaw is the direction that actually matters for map coverage.
fn within_fov(eye: &Eye, target: Vec3, half_cos: f32) -> bool {
    let Some(yaw) = eye.yaw else {
        // Direction unknown: apply no limit rather than silently dropping the
        // player's contribution.
        return true;
    };
    let (dx, dy) = (target[0] - eye.pos[0], target[1] - eye.pos[1]);
    let len_sq = dx * dx + dy * dy;
    if len_sq <= f32::EPSILON {
        // Standing on the area: nothing to aim at.
        return true;
    }
    let (rad, len) = (yaw.to_radians(), len_sq.sqrt());
    // Facing vector from the demo's yaw convention: 0° = +x, counter-clockwise.
    let cos_angle = (rad.cos() * dx + rad.sin() * dy) / len;
    cos_angle >= half_cos
}

/// Can any of `eyes` see `target`: within the field of view (when one is given),
/// clear line of sight through the mesh, not cut by a smoke, and within the
/// optional range cap?
fn any_sees(
    eyes: &[Eye],
    target: Vec3,
    mesh: &VisibilityMesh,
    smokes: &[Occluder],
    params: &Params,
    half_cos: Option<f32>,
) -> bool {
    eyes.iter().any(|eye| {
        // Cheap rejections first: the FOV cone and the range cap are both a few
        // arithmetic ops, while the mesh query walks a BVH.
        if let Some(half_cos) = half_cos
            && !within_fov(eye, target, half_cos)
        {
            return false;
        }
        if let Some(max) = params.max_distance {
            let d = sub(target, eye.pos);
            if dot(d, d) > max * max {
                return false;
            }
        }
        mesh.is_visible(eye.pos, target)
            && !smokes
                .iter()
                .any(|s| segment_hits_sphere(eye.pos, target, s.center, s.radius))
    })
}

/// Shared body of [`raycast_control`] and [`vision_control`]: the two differ only
/// in whether a field-of-view cone is applied.
///
/// `fov` is the cone width in degrees, or `None` for no limit.
fn line_of_sight_control(
    nav: &Nav,
    mesh: &VisibilityMesh,
    observers: &[Observer],
    smokes: &[Occluder],
    params: &Params,
    fov: Option<f32>,
) -> MapControl {
    // A field of view of 360° or wider constrains nothing, so skip the test.
    let half_cos = fov
        .filter(|f| *f < 360.0)
        .map(|f| (f.to_radians() / 2.0).cos());

    // A blinded player sees nothing, so only sighted players project vision.
    let eyes = |team: Team| -> Vec<Eye> {
        observers
            .iter()
            .filter(|o| o.team == team && !o.blind)
            .map(|o| Eye {
                pos: params.eye(o),
                yaw: o.yaw,
            })
            .collect()
    };
    let ct_eyes = eyes(Team::Ct);
    let t_eyes = eyes(Team::T);

    let holds = nav
        .areas
        .iter()
        .map(|a| {
            let target = {
                let c = a.centroid();
                [c[0], c[1], c[2] + params.target_height]
            };
            let ct = any_sees(&ct_eyes, target, mesh, smokes, params, half_cos);
            let t = any_sees(&t_eyes, target, mesh, smokes, params, half_cos);
            (a.area_id, ct, t)
        })
        .collect();
    assemble(nav, holds)
}

/// Assemble a [`MapControl`] from per-area holds, weighting the summary by area
/// size.
fn assemble(nav: &Nav, holds: Vec<(u32, bool, bool)>) -> MapControl {
    let mut areas = Vec::with_capacity(holds.len());
    let (mut ct, mut t, mut contested, mut neutral, mut total) = (0.0f32, 0.0, 0.0, 0.0, 0.0);
    for (area_id, hct, ht) in holds {
        let size = nav.area(area_id).map_or(0.0, NavArea::size);
        total += size;
        let control = Control::from_holds(hct, ht);
        match control {
            Control::Ct => ct += size,
            Control::T => t += size,
            Control::Contested => contested += size,
            Control::Neutral => neutral += size,
        }
        areas.push(AreaControl {
            area_id,
            control,
            ct: hct,
            t: ht,
        });
    }
    let denom = if total > 0.0 { total } else { 1.0 };
    MapControl {
        areas,
        ct_fraction: ct / denom,
        t_fraction: t / denom,
        contested_fraction: contested / denom,
        neutral_fraction: neutral / denom,
        net_control: (ct - t) / denom,
    }
}

/// Raycast map control: an area is held by a side if any of its living,
/// un-blinded players has line of sight to the area **in any direction** —
/// through the collision mesh, unbroken by an active smoke, within
/// [`Params::max_distance`].
///
/// This is the "what could a team see if they spun on the spot" model. It ignores
/// where players are actually looking; for the narrower model that respects each
/// player's field of view, see [`vision_control`].
///
/// `smokes` are the active smoke clouds as [`Occluder`] spheres; pass an empty
/// slice for none. See the [module docs](self) for the full model.
pub fn raycast_control(
    nav: &Nav,
    mesh: &VisibilityMesh,
    observers: &[Observer],
    smokes: &[Occluder],
    params: &Params,
) -> MapControl {
    line_of_sight_control(nav, mesh, observers, smokes, params, None)
}

/// Vision map control: like [`raycast_control`], but an area only counts if it
/// also falls inside the player's **field of view** — within
/// [`Params::fov`] / 2 degrees either side of their [`Observer::yaw`]
/// (default 90°, CS2's own FOV).
///
/// This is the stricter, more literal reading of "what a team can see": a player
/// watching one angle does not simultaneously hold the space behind them. Expect
/// noticeably smaller fractions than [`raycast_control`] on the same snapshot.
///
/// The cone is horizontal — yaw against the bearing to each area, ignoring pitch.
/// An observer whose `yaw` is `None` has no direction to test against, so no limit
/// is applied to them.
///
/// `smokes` are the active smoke clouds as [`Occluder`] spheres; pass an empty
/// slice for none. See the [module docs](self) for the full model.
pub fn vision_control(
    nav: &Nav,
    mesh: &VisibilityMesh,
    observers: &[Observer],
    smokes: &[Occluder],
    params: &Params,
) -> MapControl {
    line_of_sight_control(nav, mesh, observers, smokes, params, Some(params.fov))
}

/// Reachability-based map control: each area is awarded to whichever side's
/// nearest player can travel to it first over the nav graph; a near-tie (within
/// [`Params::contest_margin`]) is contested, and space unreachable by both is
/// neutral.
///
/// `fires` are active infernos as [`Occluder`] spheres: any area whose centroid
/// falls inside one is impassable, so it is neutral and paths route around it.
/// Pass an empty slice for none. Blinded players still occupy space, so they
/// count here. See the [module docs](self) for the full model.
pub fn reachability_control(
    nav: &Nav,
    observers: &[Observer],
    fires: &[Occluder],
    params: &Params,
) -> MapControl {
    // Areas denied by fire: centroid inside any inferno sphere.
    let blocked: HashSet<u32> = nav
        .areas
        .iter()
        .filter(|a| {
            let c = a.centroid();
            fires.iter().any(|f| {
                let d = sub(c, f.center);
                dot(d, d) <= f.radius * f.radius
            })
        })
        .map(|a| a.area_id)
        .collect();

    // Each side's sources: the area each of its players is standing in.
    let sources = |team: Team| -> Vec<u32> {
        observers
            .iter()
            .filter(|o| o.team == team)
            .filter_map(|o| nav.find_area(o.pos))
            .collect()
    };
    let d_ct = nav.multi_source_distances(&sources(Team::Ct), PathWeight::Distance, &blocked);
    let d_t = nav.multi_source_distances(&sources(Team::T), PathWeight::Distance, &blocked);

    let holds = nav
        .areas
        .iter()
        .map(|a| {
            if blocked.contains(&a.area_id) {
                return (a.area_id, false, false);
            }
            let (ct, t) = match (d_ct.get(&a.area_id), d_t.get(&a.area_id)) {
                (Some(&dc), Some(&dt)) => {
                    if (dc - dt).abs() <= params.contest_margin {
                        (true, true) // near-tie: contested
                    } else {
                        (dc < dt, dt < dc)
                    }
                }
                (Some(_), None) => (true, false),
                (None, Some(_)) => (false, true),
                (None, None) => (false, false),
            };
            (a.area_id, ct, t)
        })
        .collect();
    assemble(nav, holds)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::Mesh;
    use crate::nav::NavArea;

    /// A unit square area at `(x, y)` on the floor plane `z`, connected to
    /// `conns`.
    fn area(id: u32, x: f32, y: f32, z: f32, conns: &[u32]) -> NavArea {
        NavArea {
            area_id: id,
            hull_index: 0,
            dynamic_attribute_flags: 0,
            corners: vec![
                [x, y, z],
                [x + 1.0, y, z],
                [x + 1.0, y + 1.0, z],
                [x, y + 1.0, z],
            ],
            connections: conns.to_vec(),
            ladders_above: vec![],
            ladders_below: vec![],
        }
    }

    /// An observer with no known facing, so no field-of-view limit applies.
    fn obs(pos: Vec3, team: Team) -> Observer {
        Observer {
            pos,
            team,
            crouched: false,
            blind: false,
            yaw: None,
        }
    }

    /// An observer looking along `yaw` degrees (0 = +x, counter-clockwise).
    fn obs_facing(pos: Vec3, team: Team, yaw: f32) -> Observer {
        Observer {
            yaw: Some(yaw),
            ..obs(pos, team)
        }
    }

    fn label(mc: &MapControl, id: u32) -> Control {
        mc.areas.iter().find(|a| a.area_id == id).unwrap().control
    }

    /// A tall wall quad in the plane `x = x0`, spanning a wide y,z extent, so it
    /// occludes any near-horizontal ray crossing `x = x0`.
    fn wall(x0: f32) -> Mesh {
        Mesh {
            vertices: vec![
                [x0, -1000.0, -100.0],
                [x0, 1000.0, -100.0],
                [x0, 1000.0, 300.0],
                [x0, -1000.0, 300.0],
            ],
            triangles: vec![[0, 1, 2], [0, 2, 3]],
        }
    }

    #[test]
    fn raycast_open_map_partitions_by_side() {
        // Three areas in a row on an empty map (no geometry). A CT sits on the
        // left area, a T on the right; with clear sightlines every area is seen
        // by both, so all are contested.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[]),
            area(2, 100.0, 0.0, 0.0, &[]),
            area(3, 200.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let observers = vec![
            obs([0.5, 0.5, 0.0], Team::Ct),
            obs([200.5, 0.5, 0.0], Team::T),
        ];
        let mc = raycast_control(&nav, &mesh, &observers, &[], &Params::default());
        assert_eq!(label(&mc, 1), Control::Contested);
        assert_eq!(label(&mc, 2), Control::Contested);
        assert_eq!(label(&mc, 3), Control::Contested);
        assert!((mc.contested_fraction - 1.0).abs() < 1e-5);
        assert!(mc.net_control.abs() < 1e-5);
    }

    #[test]
    fn raycast_wall_splits_control() {
        // A wall at x = 50 between a CT (left) and a T (right). Each sees only
        // its own side; the areas nearest each player are that side's, and the
        // far side is out of sight.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[]),   // left, near CT
            area(2, 100.0, 0.0, 0.0, &[]), // right, near T
        ]);
        let mesh = VisibilityMesh::build(wall(50.0));
        let observers = vec![
            obs([0.5, 0.5, 0.0], Team::Ct),
            obs([100.5, 0.5, 0.0], Team::T),
        ];
        let mc = raycast_control(&nav, &mesh, &observers, &[], &Params::default());
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 2), Control::T);
    }

    #[test]
    fn raycast_smoke_blocks_sightline() {
        // Open map, CT and T on opposite ends (would both see the middle area).
        // A smoke over the middle area cuts every crossing sightline, so the
        // middle becomes each side's own near area only where they still reach.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[]),
            area(2, 100.0, 0.0, 0.0, &[]),
            area(3, 200.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let observers = vec![
            obs([0.5, 0.5, 0.0], Team::Ct),
            obs([200.5, 0.5, 0.0], Team::T),
        ];
        // Smoke centred on the middle area, big enough to swallow it.
        let smokes = [Occluder {
            center: [100.5, 0.5, 40.0],
            radius: 80.0,
        }];
        let mc = raycast_control(&nav, &mesh, &observers, &smokes, &Params::default());
        // The middle area is smoked off from both distant players, but each
        // player still stands in / sees their own end.
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 3), Control::T);
        // The middle is no longer contested by the two ends (the smoke cut both
        // long sightlines to it).
        assert_ne!(label(&mc, 2), Control::Contested);
    }

    #[test]
    fn raycast_blind_player_sees_nothing() {
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[]),
            area(2, 100.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let mut ct = obs([0.5, 0.5, 0.0], Team::Ct);
        ct.blind = true;
        let mc = raycast_control(&nav, &mesh, &[ct], &[], &Params::default());
        // A fully blinded lone CT projects no vision, so nothing is controlled.
        assert!((mc.neutral_fraction - 1.0).abs() < 1e-5);
    }

    #[test]
    fn vision_only_covers_the_arc_a_player_faces() {
        // Five areas in a row, the CT standing on the middle one. Facing +x, the
        // areas to their left are behind them and must not count as seen.
        let nav = Nav::from_areas(vec![
            area(1, -200.0, 0.0, 0.0, &[]),
            area(2, -100.0, 0.0, 0.0, &[]),
            area(3, 0.0, 0.0, 0.0, &[]),
            area(4, 100.0, 0.0, 0.0, &[]),
            area(5, 200.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let facing_pos_x = vec![obs_facing([0.5, 0.5, 0.0], Team::Ct, 0.0)];
        let mc = vision_control(&nav, &mesh, &facing_pos_x, &[], &Params::default());

        // Ahead: seen. Behind: not.
        assert_eq!(label(&mc, 4), Control::Ct);
        assert_eq!(label(&mc, 5), Control::Ct);
        assert_eq!(label(&mc, 1), Control::Neutral);
        assert_eq!(label(&mc, 2), Control::Neutral);

        // Turning around flips exactly which half is held.
        let facing_neg_x = vec![obs_facing([0.5, 0.5, 0.0], Team::Ct, 180.0)];
        let mc = vision_control(&nav, &mesh, &facing_neg_x, &[], &Params::default());
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 2), Control::Ct);
        assert_eq!(label(&mc, 4), Control::Neutral);
        assert_eq!(label(&mc, 5), Control::Neutral);
    }

    #[test]
    fn vision_holds_less_than_raycast() {
        // The distinguishing property of the two models: on the same snapshot, a
        // 90-degree cone can only ever see a subset of what an unrestricted ray
        // cast sees.
        let nav = Nav::from_areas(vec![
            area(1, -200.0, 0.0, 0.0, &[]),
            area(2, -100.0, 0.0, 0.0, &[]),
            area(3, 0.0, 0.0, 0.0, &[]),
            area(4, 100.0, 0.0, 0.0, &[]),
            area(5, 200.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let observers = vec![obs_facing([0.5, 0.5, 0.0], Team::Ct, 0.0)];

        let raycast = raycast_control(&nav, &mesh, &observers, &[], &Params::default());
        let vision = vision_control(&nav, &mesh, &observers, &[], &Params::default());
        assert!(
            vision.ct_fraction < raycast.ct_fraction,
            "vision {} should hold less than raycast {}",
            vision.ct_fraction,
            raycast.ct_fraction
        );
        // Raycast sees the whole row from the middle; vision only the near half.
        assert!((raycast.ct_fraction - 1.0).abs() < 1e-5);
    }

    #[test]
    fn a_full_circle_fov_matches_raycast() {
        // 360 degrees is no constraint at all, so the two models must agree —
        // the property that lets `fov` interpolate between them.
        let nav = Nav::from_areas(vec![
            area(1, -100.0, 0.0, 0.0, &[]),
            area(2, 0.0, 0.0, 0.0, &[]),
            area(3, 100.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let observers = vec![obs_facing([0.5, 0.5, 0.0], Team::Ct, 0.0)];
        let params = Params {
            fov: 360.0,
            ..Params::default()
        };
        let vision = vision_control(&nav, &mesh, &observers, &[], &params);
        let raycast = raycast_control(&nav, &mesh, &observers, &[], &Params::default());
        assert_eq!(vision.ct_fraction, raycast.ct_fraction);
    }

    #[test]
    fn an_unknown_facing_is_unrestricted() {
        // With no yaw there is no cone to test against, so the player is not
        // silently dropped — they behave as they do under raycast.
        let nav = Nav::from_areas(vec![
            area(1, -100.0, 0.0, 0.0, &[]),
            area(2, 0.0, 0.0, 0.0, &[]),
            area(3, 100.0, 0.0, 0.0, &[]),
        ]);
        let mesh = VisibilityMesh::build(Mesh::default());
        let observers = vec![obs([0.5, 0.5, 0.0], Team::Ct)]; // yaw: None
        let vision = vision_control(&nav, &mesh, &observers, &[], &Params::default());
        assert_eq!(label(&vision, 1), Control::Ct);
        assert_eq!(label(&vision, 3), Control::Ct);
    }

    #[test]
    fn vision_still_respects_walls_and_smokes() {
        // The FOV cone is an extra filter, not a replacement: geometry and smokes
        // must still cut a sightline that is within the arc.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[]),
            area(2, 100.0, 0.0, 0.0, &[]),
        ]);
        let observers = vec![obs_facing([0.5, 0.5, 0.0], Team::Ct, 0.0)];

        // A wall between them, well within the arc.
        let walled = VisibilityMesh::build(wall(50.0));
        let mc = vision_control(&nav, &walled, &observers, &[], &Params::default());
        assert_eq!(label(&mc, 2), Control::Neutral);

        // No wall, but a smoke on the line.
        let open = VisibilityMesh::build(Mesh::default());
        let smoke = [Occluder {
            center: [50.0, 0.5, 46.0],
            radius: 60.0,
        }];
        let mc = vision_control(&nav, &open, &observers, &smoke, &Params::default());
        assert_eq!(label(&mc, 2), Control::Neutral);
    }

    #[test]
    fn reachability_awards_nearest_side() {
        // 1 - 2 - 3 - 4 - 5 chain. CT stands in area 1, T in area 5. Areas fall
        // to whichever side reaches them first; the exact middle is contested.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[2]),
            area(2, 100.0, 0.0, 0.0, &[1, 3]),
            area(3, 200.0, 0.0, 0.0, &[2, 4]),
            area(4, 300.0, 0.0, 0.0, &[3, 5]),
            area(5, 400.0, 0.0, 0.0, &[4]),
        ]);
        let observers = vec![
            obs([0.5, 0.5, 0.0], Team::Ct),
            obs([400.5, 0.5, 0.0], Team::T),
        ];
        // Tight tie band so only the true midpoint ties.
        let params = Params {
            contest_margin: 1.0,
            ..Params::default()
        };
        let mc = reachability_control(&nav, &observers, &[], &params);
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 2), Control::Ct);
        assert_eq!(label(&mc, 3), Control::Contested); // equidistant
        assert_eq!(label(&mc, 4), Control::T);
        assert_eq!(label(&mc, 5), Control::T);
    }

    #[test]
    fn reachability_fire_denies_area() {
        // 1 - 2 - 3 chain, CT in area 1, T in area 3. A fire on area 2 blocks the
        // only path between them: area 2 is neutral (denied) and cuts each side
        // off from the far end.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[2]),
            area(2, 100.0, 0.0, 0.0, &[1, 3]),
            area(3, 200.0, 0.0, 0.0, &[2]),
        ]);
        let observers = vec![
            obs([0.5, 0.5, 0.0], Team::Ct),
            obs([200.5, 0.5, 0.0], Team::T),
        ];
        let fires = [Occluder {
            center: [100.5, 0.5, 0.0],
            radius: 10.0,
        }];
        let mc = reachability_control(&nav, &observers, &fires, &Params::default());
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 2), Control::Neutral); // burning: denied to both
        assert_eq!(label(&mc, 3), Control::T);
    }

    #[test]
    fn reachability_one_sided_when_enemy_absent() {
        // With only CT players, every reachable area is CT-controlled.
        let nav = Nav::from_areas(vec![
            area(1, 0.0, 0.0, 0.0, &[2]),
            area(2, 100.0, 0.0, 0.0, &[1]),
        ]);
        let observers = vec![obs([0.5, 0.5, 0.0], Team::Ct)];
        let mc = reachability_control(&nav, &observers, &[], &Params::default());
        assert_eq!(label(&mc, 1), Control::Ct);
        assert_eq!(label(&mc, 2), Control::Ct);
        assert!((mc.ct_fraction - 1.0).abs() < 1e-5);
    }

    #[test]
    fn segment_sphere_hit_and_miss() {
        // Segment along x through the origin: a sphere at the origin is hit, one
        // far off the line is missed.
        assert!(segment_hits_sphere(
            [-10.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            1.0
        ));
        assert!(!segment_hits_sphere(
            [-10.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [0.0, 50.0, 0.0],
            1.0
        ));
    }
}

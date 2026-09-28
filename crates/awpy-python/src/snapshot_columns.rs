//! Owned column accumulation for snapshot callbacks.
use awpy::PlayerState;
use polars::prelude::*;

// Keep storage, appending, and output order in one schema declaration.
macro_rules! snapshot_columns {
    ($($field:ident: $ty:ty),+ $(,)?) => {
        #[derive(Default)]
        pub struct SnapshotColumns { $($field: Vec<$ty>),+ }

        impl SnapshotColumns {
            pub fn with_capacity(capacity: usize) -> Self {
                Self { $($field: Vec::with_capacity(capacity)),+ }
            }

            pub fn push(&mut self, state: PlayerState) {
                $(self.$field.push(state.$field);)+
            }

            pub fn append(&mut self, mut other: Self) {
                $(self.$field.append(&mut other.$field);)+
            }

            pub fn into_frame(self) -> PolarsResult<DataFrame> {
                DataFrame::new(self.tick.len(), vec![
                    $(Column::new(stringify!($field).into(), self.$field)),+
                ])
            }
        }
    };
}

snapshot_columns! {
    tick: i32,
    steamid: Option<u64>,
    name: Option<String>,
    side: Option<&'static str>,
    x: Option<f32>,
    y: Option<f32>,
    z: Option<f32>,
    velocity_x: Option<f32>,
    velocity_y: Option<f32>,
    velocity_z: Option<f32>,
    velocity: Option<f32>,
    pitch: f32,
    yaw: f32,
    health: i32,
    armor: i32,
    has_helmet: bool,
    has_defuser: bool,
    has_bomb: bool,
    active_weapon: Option<&'static str>,
    primary_weapon: Option<&'static str>,
    secondary_weapon: Option<&'static str>,
    fire_grenades: i32,
    smoke_grenades: i32,
    he_grenades: i32,
    flashbangs: i32,
    decoy_grenades: i32,
    equipment_value: i32,
    equipment_value_round_start: i32,
    money: i32,
    is_crouched: bool,
    is_walking: bool,
    is_jumping: bool,
    is_in_bomb_zone: bool,
    is_scoped: bool,
    is_defusing: bool,
    is_blinded: bool,
    flash_duration: f32,
    inventory: String,
}

impl Extend<PlayerState> for SnapshotColumns {
    fn extend<T: IntoIterator<Item = PlayerState>>(&mut self, rows: T) {
        for row in rows {
            self.push(row);
        }
    }
}

impl FromIterator<PlayerState> for SnapshotColumns {
    fn from_iter<T: IntoIterator<Item = PlayerState>>(rows: T) -> Self {
        let rows = rows.into_iter();
        let mut columns = Self::with_capacity(rows.size_hint().0);
        columns.extend(rows);
        columns
    }
}

//! Weapon entity class → canonical name and inventory slot.
//!
//! CS2 networks each held item as its own entity whose `class_name` identifies
//! the weapon (e.g. `CAK47`, `CDEagle`, `CHEGrenade`). The class prefixes are
//! inconsistent (`CAK47` vs `CWeaponAWP` vs `CDEagle`), so this module maps them
//! to the short names used elsewhere in awpy (matching the `weapon` key of
//! `player_death` / `weapon_fire` events, e.g. `ak47`, `awp`, `usp_silencer`)
//! and to the loadout [`WeaponSlot`] used by the economy columns of
//! [`Parser::snapshot`](crate::demo::Parser::snapshot).

/// The loadout slot a weapon occupies.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WeaponSlot {
    /// Rifles, SMGs, shotguns, snipers, and machine guns.
    Primary,
    /// Pistols.
    Secondary,
    /// Knife (and other melee).
    Melee,
    /// Thrown grenades (HE, flash, smoke, molotov/incendiary, decoy).
    Grenade,
    /// The bomb.
    C4,
    /// The zeus/taser and other utility that is neither a primary nor a pistol.
    Equipment,
}

/// The canonical short name and loadout slot for a weapon.
#[derive(Debug, Clone, Copy)]
pub struct WeaponInfo {
    pub name: &'static str,
    pub slot: WeaponSlot,
}

use WeaponSlot::*;

/// `(entity class name, short name, slot)` for every CS2 weapon entity.
const WEAPONS: &[(&str, &str, WeaponSlot)] = &[
    // Rifles / SMGs / shotguns / snipers / LMGs.
    ("CAK47", "ak47", Primary),
    ("CWeaponAug", "aug", Primary),
    ("CWeaponAWP", "awp", Primary),
    ("CWeaponBizon", "bizon", Primary),
    ("CWeaponFamas", "famas", Primary),
    ("CWeaponG3SG1", "g3sg1", Primary),
    ("CWeaponGalilAR", "galilar", Primary),
    ("CWeaponM249", "m249", Primary),
    ("CWeaponM4A1", "m4a1", Primary),
    ("CWeaponM4A1Silencer", "m4a1_silencer", Primary),
    ("CWeaponMAC10", "mac10", Primary),
    ("CWeaponMag7", "mag7", Primary),
    ("CWeaponMP5SD", "mp5sd", Primary),
    ("CWeaponMP7", "mp7", Primary),
    ("CWeaponMP9", "mp9", Primary),
    ("CWeaponNegev", "negev", Primary),
    ("CWeaponNOVA", "nova", Primary),
    ("CWeaponP90", "p90", Primary),
    ("CWeaponSawedoff", "sawedoff", Primary),
    ("CWeaponSCAR20", "scar20", Primary),
    ("CWeaponSG556", "sg556", Primary),
    ("CWeaponSSG08", "ssg08", Primary),
    ("CWeaponUMP45", "ump45", Primary),
    ("CWeaponXM1014", "xm1014", Primary),
    // Pistols.
    ("CDEagle", "deagle", Secondary),
    ("CWeaponCZ75a", "cz75a", Secondary),
    ("CWeaponElite", "elite", Secondary),
    ("CWeaponFiveSeven", "fiveseven", Secondary),
    ("CWeaponGlock", "glock", Secondary),
    ("CWeaponHKP2000", "hkp2000", Secondary),
    ("CWeaponP250", "p250", Secondary),
    ("CWeaponRevolver", "revolver", Secondary),
    ("CWeaponTec9", "tec9", Secondary),
    ("CWeaponUSPSilencer", "usp_silencer", Secondary),
    // Melee.
    ("CKnife", "knife", Melee),
    // Utility.
    ("CWeaponTaser", "taser", Equipment),
    ("CC4", "c4", C4),
    // Grenades.
    ("CHEGrenade", "hegrenade", Grenade),
    ("CFlashbang", "flashbang", Grenade),
    ("CSmokeGrenade", "smokegrenade", Grenade),
    ("CMolotovGrenade", "molotov", Grenade),
    ("CIncendiaryGrenade", "incendiary", Grenade),
    ("CDecoyGrenade", "decoy", Grenade),
];

/// Every known weapon entity class name — for building an entity filter that
/// captures held weapons, so a loadout can be read from a filtered decode.
/// (`CKnife*` skin variants are matched by prefix in [`weapon_info`] and can't
/// be enumerated, but the base `CKnife` is included.)
pub fn weapon_classes() -> impl Iterator<Item = &'static str> {
    WEAPONS.iter().map(|(class, ..)| *class)
}

/// The canonical name and slot for a weapon entity's class name, if recognized.
///
/// Falls back to treating any unrecognized `CKnife*` variant as a knife, since
/// knife skins can carry a class name other than the base `CKnife`.
pub fn weapon_info(class_name: &str) -> Option<WeaponInfo> {
    if let Some(&(_, name, slot)) = WEAPONS.iter().find(|(class, ..)| *class == class_name) {
        return Some(WeaponInfo { name, slot });
    }
    if class_name.starts_with("CKnife") {
        return Some(WeaponInfo {
            name: "knife",
            slot: WeaponSlot::Melee,
        });
    }
    None
}

/// `(projectile class, grenade type)` for thrown grenades in flight — the
/// entities the [`grenades`](crate::demo::Parser::grenades) trajectory dataset
/// follows. Distinct from the held-grenade entities in [`WEAPONS`] (a thrown HE
/// is `CHEGrenadeProjectile`, not `CHEGrenade`).
const GRENADE_PROJECTILES: &[(&str, &str)] = &[
    ("CSmokeGrenadeProjectile", "smoke"),
    ("CHEGrenadeProjectile", "he"),
    ("CFlashbangProjectile", "flashbang"),
    ("CMolotovProjectile", "molotov"),
    ("CDecoyProjectile", "decoy"),
    ("CBaseCSGrenadeProjectile", "grenade"),
];

/// Every thrown-grenade projectile entity class, for building a projectile
/// filter or tracker.
pub fn grenade_projectile_classes() -> impl Iterator<Item = &'static str> {
    GRENADE_PROJECTILES.iter().map(|(class, ..)| *class)
}

/// Grenade-type label for a projectile class, or `None` if it isn't one.
pub fn grenade_type(class: &str) -> Option<&'static str> {
    GRENADE_PROJECTILES
        .iter()
        .find(|(c, _)| *c == class)
        .map(|(_, t)| *t)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maps_known_weapons() {
        assert_eq!(weapon_info("CAK47").unwrap().name, "ak47");
        assert_eq!(weapon_info("CAK47").unwrap().slot, WeaponSlot::Primary);
        assert_eq!(weapon_info("CDEagle").unwrap().slot, WeaponSlot::Secondary);
        assert_eq!(weapon_info("CHEGrenade").unwrap().slot, WeaponSlot::Grenade);
        assert_eq!(weapon_info("CC4").unwrap().slot, WeaponSlot::C4);
        assert_eq!(
            weapon_info("CWeaponTaser").unwrap().slot,
            WeaponSlot::Equipment
        );
    }

    #[test]
    fn knife_variants_fall_back_to_knife() {
        assert_eq!(weapon_info("CKnife").unwrap().name, "knife");
        assert_eq!(weapon_info("CKnifeGG").unwrap().name, "knife");
    }

    #[test]
    fn unknown_class_is_none() {
        assert!(weapon_info("CWorld").is_none());
        assert!(weapon_info("CCSPlayerPawn").is_none());
    }
}

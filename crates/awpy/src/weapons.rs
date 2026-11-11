//! Weapon names and inventory slots.
//!
//! CS2 uses shared entity classes for some weapon variants. Entity-based
//! collection checks the item-definition index and subclass token to identify
//! these variants. Class names provide a fallback when both fields are absent
//! or unknown. Names use the short event labels, such as `ak47` and
//! `usp_silencer`. [`WeaponSlot`] identifies the inventory slot.

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

/// Return the class default name and slot, if the class is known.
///
/// A shared class does not identify the exact weapon variant. Snapshot and
/// inventory collection also check item-definition and subclass fields.
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

/// A weapon variant within a shared network class.
struct WeaponVariant {
    definition: u32,
    subclass: u32,
    name: &'static str,
}

// Subclass tokens are MurmurHash2 hashes of decimal item-definition IDs,
// with seed 0x31415926. Keep these constants out of the per-entity path.
const PISTOLS: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 1,
        subclass: 628_863_847,
        name: "deagle",
    },
    WeaponVariant {
        definition: 64,
        subclass: 966_714_057,
        name: "revolver",
    },
];
const RIFLES: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 16,
        subclass: 2_746_029_779,
        name: "m4a1",
    },
    WeaponVariant {
        definition: 60,
        subclass: 4_152_478_990,
        name: "m4a1_silencer",
    },
];
const STARTING_PISTOLS: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 32,
        subclass: 1_721_431_921,
        name: "hkp2000",
    },
    WeaponVariant {
        definition: 61,
        subclass: 2_343_690_088,
        name: "usp_silencer",
    },
];
/// The MP7 and MP5-SD can share the MP7 network class.
const SMGS: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 33,
        subclass: 10_406_947,
        name: "mp7",
    },
    WeaponVariant {
        definition: 23,
        subclass: 45_975_715,
        name: "mp5sd",
    },
];
/// The P250 and CZ75-Auto fill the same loadout slot.
const AUTO_PISTOLS: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 36,
        subclass: 1_573_262_270,
        name: "p250",
    },
    WeaponVariant {
        definition: 63,
        subclass: 3_464_182_751,
        name: "cz75a",
    },
];
/// The Five-SeveN and Tec-9 fill the same loadout slot.
const SLOT_PISTOLS: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 3,
        subclass: 3_661_698_933,
        name: "fiveseven",
    },
    WeaponVariant {
        definition: 30,
        subclass: 884_934_217,
        name: "tec9",
    },
];
/// Knives share one network class; the item definition names the model.
/// Names follow the CS2 item names without the `weapon_` prefix.
const KNIVES: &[WeaponVariant] = &[
    WeaponVariant {
        definition: 41,
        subclass: 338_620_472,
        name: "knifegg",
    },
    WeaponVariant {
        definition: 42,
        subclass: 294_910_436,
        name: "knife",
    },
    WeaponVariant {
        definition: 59,
        subclass: 1_058_568_214,
        name: "knife_t",
    },
    WeaponVariant {
        definition: 80,
        subclass: 839_540_137,
        name: "knife_ghost",
    },
    WeaponVariant {
        definition: 500,
        subclass: 3_933_374_535,
        name: "bayonet",
    },
    WeaponVariant {
        definition: 503,
        subclass: 3_787_235_507,
        name: "knife_css",
    },
    WeaponVariant {
        definition: 505,
        subclass: 4_046_390_180,
        name: "knife_flip",
    },
    WeaponVariant {
        definition: 506,
        subclass: 2_047_704_618,
        name: "knife_gut",
    },
    WeaponVariant {
        definition: 507,
        subclass: 1_731_408_398,
        name: "knife_karambit",
    },
    WeaponVariant {
        definition: 508,
        subclass: 1_638_561_588,
        name: "knife_m9_bayonet",
    },
    WeaponVariant {
        definition: 509,
        subclass: 2_282_479_884,
        name: "knife_tactical",
    },
    WeaponVariant {
        definition: 512,
        subclass: 3_412_259_219,
        name: "knife_falchion",
    },
    WeaponVariant {
        definition: 514,
        subclass: 2_511_498_851,
        name: "knife_survival_bowie",
    },
    WeaponVariant {
        definition: 515,
        subclass: 1_353_709_123,
        name: "knife_butterfly",
    },
    WeaponVariant {
        definition: 516,
        subclass: 4_269_888_884,
        name: "knife_push",
    },
    WeaponVariant {
        definition: 517,
        subclass: 1_105_782_941,
        name: "knife_cord",
    },
    WeaponVariant {
        definition: 518,
        subclass: 275_962_944,
        name: "knife_canis",
    },
    WeaponVariant {
        definition: 519,
        subclass: 1_338_637_359,
        name: "knife_ursus",
    },
    WeaponVariant {
        definition: 520,
        subclass: 3_230_445_913,
        name: "knife_gypsy_jackknife",
    },
    WeaponVariant {
        definition: 521,
        subclass: 3_206_681_373,
        name: "knife_outdoor",
    },
    WeaponVariant {
        definition: 522,
        subclass: 2_595_277_776,
        name: "knife_stiletto",
    },
    WeaponVariant {
        definition: 523,
        subclass: 4_029_975_521,
        name: "knife_widowmaker",
    },
    WeaponVariant {
        definition: 525,
        subclass: 365_028_728,
        name: "knife_skeleton",
    },
    WeaponVariant {
        definition: 526,
        subclass: 3_845_286_452,
        name: "knife_kukri",
    },
];

/// Field keys and the class fallback for one weapon class.
struct WeaponIdentity {
    fallback: WeaponInfo,
    variants: &'static [WeaponVariant],
    definition: Option<u64>,
    subclass: Option<u64>,
}

impl WeaponIdentity {
    fn variants(class: &str) -> &'static [WeaponVariant] {
        match class {
            "CDEagle" | "CWeaponRevolver" => PISTOLS,
            "CWeaponM4A1" | "CWeaponM4A1Silencer" => RIFLES,
            "CWeaponHKP2000" | "CWeaponUSPSilencer" => STARTING_PISTOLS,
            "CWeaponMP7" | "CWeaponMP5SD" => SMGS,
            "CWeaponP250" | "CWeaponCZ75a" => AUTO_PISTOLS,
            "CWeaponFiveSeven" | "CWeaponTec9" => SLOT_PISTOLS,
            knife if knife.starts_with("CKnife") => KNIVES,
            _ => &[],
        }
    }

    fn info(&self, entity: &crate::entity::Entity) -> WeaponInfo {
        // Use an item ID only within this class's weapon family. If it is
        // absent, zero, or unknown, try the subclass token before the class.
        let definition = entity.get_u64(self.definition);
        let variant = self
            .variants
            .iter()
            .find(|v| definition == Some(u64::from(v.definition)))
            .or_else(|| {
                let subclass = entity.get_u64(self.subclass);
                self.variants
                    .iter()
                    .find(|v| subclass == Some(u64::from(v.subclass)))
            });
        WeaponInfo {
            name: variant.map_or(self.fallback.name, |v| v.name),
            slot: self.fallback.slot,
        }
    }
}

/// Resolve weapon identities with field keys cached once per parser pass.
pub(crate) struct WeaponResolver {
    classes: std::collections::HashMap<i32, WeaponIdentity>,
}

impl WeaponResolver {
    pub(crate) fn new(ctx: &crate::demo::Context) -> Self {
        let classes = ctx
            .class_info()
            .classes()
            .iter()
            .filter_map(|class| {
                let fallback = weapon_info(&class.network_name)?;
                let variants = WeaponIdentity::variants(&class.network_name);
                let serializer = ctx.serializers().get(&class.network_name);
                let key = |path| serializer.and_then(|s| s.resolve_field_key(path));
                Some((
                    class.class_id,
                    WeaponIdentity {
                        fallback,
                        variants,
                        definition: (!variants.is_empty())
                            .then(|| key("m_AttributeManager.m_Item.m_iItemDefinitionIndex"))
                            .flatten(),
                        subclass: (!variants.is_empty())
                            .then(|| key("m_nSubclassID"))
                            .flatten(),
                    },
                ))
            })
            .collect();
        Self { classes }
    }

    pub(crate) fn info(&self, entity: &crate::entity::Entity) -> Option<WeaponInfo> {
        self.classes
            .get(&entity.class_id)
            .map(|keys| keys.info(entity))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entity_info(class: &str, definition: Option<u32>, subclass: Option<u32>) -> WeaponInfo {
        let mut entity =
            crate::entity::Entity::from_fields(1, 0, 0, class, true, Default::default()).unwrap();
        if let Some(value) = definition {
            entity
                .fields
                .insert(0, crate::entity::FieldValue::U32(value));
        }
        if let Some(value) = subclass {
            entity
                .fields
                .insert(1, crate::entity::FieldValue::U32(value));
        }
        WeaponIdentity {
            fallback: weapon_info(class).unwrap(),
            variants: WeaponIdentity::variants(class),
            definition: Some(0),
            subclass: Some(1),
        }
        .info(&entity)
    }

    #[test]
    fn shared_classes_resolve_each_item_definition() {
        for (class, variants, slot) in [
            ("CDEagle", PISTOLS, Secondary),
            ("CWeaponM4A1", RIFLES, Primary),
            ("CWeaponHKP2000", STARTING_PISTOLS, Secondary),
            ("CKnife", KNIVES, Melee),
            ("CWeaponMP7", SMGS, Primary),
            ("CWeaponP250", AUTO_PISTOLS, Secondary),
            ("CWeaponFiveSeven", SLOT_PISTOLS, Secondary),
        ] {
            for variant in variants {
                let info = entity_info(class, Some(variant.definition), None);
                assert_eq!(info.name, variant.name);
                assert_eq!(info.slot, slot);
            }
        }
    }

    #[test]
    fn subclass_resolves_variants_without_an_item_definition() {
        for (class, variants) in [
            ("CDEagle", PISTOLS),
            ("CWeaponM4A1", RIFLES),
            ("CWeaponHKP2000", STARTING_PISTOLS),
            ("CKnife", KNIVES),
            ("CWeaponMP7", SMGS),
            ("CWeaponP250", AUTO_PISTOLS),
            ("CWeaponFiveSeven", SLOT_PISTOLS),
        ] {
            for variant in variants {
                for definition in [None, Some(0), Some(u32::MAX)] {
                    assert_eq!(
                        entity_info(class, definition, Some(variant.subclass)).name,
                        variant.name
                    );
                }
            }
        }
    }

    #[test]
    fn valid_item_definition_takes_priority_over_subclass() {
        assert_eq!(
            entity_info("CDEagle", Some(64), Some(628_863_847)).name,
            "revolver"
        );
        assert_eq!(
            entity_info("CDEagle", Some(1), Some(966_714_057)).name,
            "deagle"
        );
    }

    #[test]
    fn missing_unknown_and_foreign_ids_keep_the_class_fallback() {
        for class in [
            "CDEagle",
            "CWeaponM4A1",
            "CWeaponHKP2000",
            "CWeaponRevolver",
            "CWeaponM4A1Silencer",
            "CWeaponUSPSilencer",
            "CAK47",
            "CKnifeGG",
        ] {
            for (definition, subclass) in [
                (None, None),
                (Some(0), Some(0)),
                (Some(u32::MAX), Some(u32::MAX)),
            ] {
                assert_eq!(
                    entity_info(class, definition, subclass).name,
                    weapon_info(class).unwrap().name
                );
            }
        }
        assert_eq!(
            entity_info("CDEagle", Some(60), Some(4_152_478_990)).name,
            "deagle"
        );
        assert_eq!(
            entity_info("CAK47", Some(64), Some(966_714_057)).name,
            "ak47"
        );
        assert_eq!(
            entity_info("CKnifeGG", Some(64), Some(966_714_057)).name,
            "knife"
        );
    }

    #[test]
    fn legacy_variant_class_names_accept_identity_fields() {
        assert_eq!(entity_info("CWeaponRevolver", Some(1), None).name, "deagle");
        assert_eq!(
            entity_info("CWeaponM4A1Silencer", None, Some(2_746_029_779)).name,
            "m4a1"
        );
        assert_eq!(
            entity_info("CWeaponUSPSilencer", Some(32), None).name,
            "hkp2000"
        );
    }

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

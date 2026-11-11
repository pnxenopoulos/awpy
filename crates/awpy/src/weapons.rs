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

/// The weapon classes that hold more than one variant (Deagle / Revolver, M4A4 / M4A1-S,
/// P2000 / USP-S). Their item-definition fields are what tells the variants apart.
pub(crate) const VARIANT_CLASSES: &[&str] = &[
    "CDEagle",
    "CWeaponRevolver",
    "CWeaponM4A1",
    "CWeaponM4A1Silencer",
    "CWeaponHKP2000",
    "CWeaponUSPSilencer",
];

/// Field paths that identify a variant on [`VARIANT_CLASSES`] entities.
pub(crate) const VARIANT_FIELDS: [&str; 2] = [
    "m_AttributeManager.m_Item.m_iItemDefinitionIndex",
    "m_nSubclassID",
];

/// Variant pairs on [`VARIANT_CLASSES`]. `player_hurt` reports either member
/// under the first member's name.
const DAMAGE_AMBIGUOUS: [&[WeaponVariant]; 3] = [PISTOLS, RIFLES, STARTING_PISTOLS];

/// The static name of a variant-class weapon (`usp_silencer`, `m4a1`, ...), if `name` is one.
pub(crate) fn variant_name(name: &str) -> Option<&'static str> {
    DAMAGE_AMBIGUOUS
        .iter()
        .flat_map(|pair| pair.iter())
        .map(|variant| variant.name)
        .find(|n| *n == name)
}

/// The specific weapon an ambiguous `player_hurt` label can represent.
pub(crate) fn damage_weapon_variant(event_weapon: &str) -> Option<&'static str> {
    DAMAGE_AMBIGUOUS
        .iter()
        .find(|pair| pair[0].name == event_weapon)
        .map(|pair| pair[1].name)
}

/// Refine an ambiguous event label only with evidence for its specific variant.
pub(crate) fn refine_damage_weapon(event_weapon: &mut String, observed: &str) {
    if let Some(variant) = damage_weapon_variant(event_weapon)
        && variant == observed
    {
        variant.clone_into(event_weapon);
    }
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

const fn variant(definition: u32, subclass: u32, name: &'static str) -> WeaponVariant {
    WeaponVariant {
        definition,
        subclass,
        name,
    }
}

// Subclass tokens are MurmurHash2 hashes of decimal item-definition IDs,
// with seed 0x31415926. Keep these constants out of the per-entity path.
const PISTOLS: &[WeaponVariant] = &[
    variant(1, 628_863_847, "deagle"),
    variant(64, 966_714_057, "revolver"),
];
const RIFLES: &[WeaponVariant] = &[
    variant(16, 2_746_029_779, "m4a1"),
    variant(60, 4_152_478_990, "m4a1_silencer"),
];
const STARTING_PISTOLS: &[WeaponVariant] = &[
    variant(32, 1_721_431_921, "hkp2000"),
    variant(61, 2_343_690_088, "usp_silencer"),
];
/// The MP7 and MP5-SD can share the MP7 network class.
const SMGS: &[WeaponVariant] = &[
    variant(33, 10_406_947, "mp7"),
    variant(23, 45_975_715, "mp5sd"),
];
/// Some demos carry a CZ75-Auto in the P250 network class.
const P250_VARIANTS: &[WeaponVariant] = &[
    variant(36, 1_573_262_270, "p250"),
    variant(63, 3_464_182_751, "cz75a"),
];
/// Knives share one network class; the item definition names the model.
/// Names follow the CS2 item names without the `weapon_` prefix.
const KNIVES: &[WeaponVariant] = &[
    variant(41, 338_620_472, "knifegg"),
    variant(42, 294_910_436, "knife"),
    variant(59, 1_058_568_214, "knife_t"),
    variant(80, 839_540_137, "knife_ghost"),
    variant(500, 3_933_374_535, "bayonet"),
    variant(503, 3_787_235_507, "knife_css"),
    variant(505, 4_046_390_180, "knife_flip"),
    variant(506, 2_047_704_618, "knife_gut"),
    variant(507, 1_731_408_398, "knife_karambit"),
    variant(508, 1_638_561_588, "knife_m9_bayonet"),
    variant(509, 2_282_479_884, "knife_tactical"),
    variant(512, 3_412_259_219, "knife_falchion"),
    variant(514, 2_511_498_851, "knife_survival_bowie"),
    variant(515, 1_353_709_123, "knife_butterfly"),
    variant(516, 4_269_888_884, "knife_push"),
    variant(517, 1_105_782_941, "knife_cord"),
    variant(518, 275_962_944, "knife_canis"),
    variant(519, 1_338_637_359, "knife_ursus"),
    variant(520, 3_230_445_913, "knife_gypsy_jackknife"),
    variant(521, 3_206_681_373, "knife_outdoor"),
    variant(522, 2_595_277_776, "knife_stiletto"),
    variant(523, 4_029_975_521, "knife_widowmaker"),
    variant(525, 365_028_728, "knife_skeleton"),
    variant(526, 3_845_286_452, "knife_kukri"),
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
            "CWeaponP250" => P250_VARIANTS,
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
                let key = |path| {
                    serializer
                        .filter(|_| !variants.is_empty())
                        .and_then(|s| s.resolve_field_key(path))
                };
                let [definition, subclass] = VARIANT_FIELDS.map(key);
                Some((
                    class.class_id,
                    WeaponIdentity {
                        fallback,
                        variants,
                        definition,
                        subclass,
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

    fn refined_damage_weapon(event_weapon: &str, observed: &str) -> String {
        let mut name = event_weapon.to_owned();
        refine_damage_weapon(&mut name, observed);
        name
    }

    #[test]
    fn damage_name_refines_an_ambiguous_label() {
        for (event, variant) in [
            ("hkp2000", "usp_silencer"),
            ("m4a1", "m4a1_silencer"),
            ("deagle", "revolver"),
        ] {
            assert_eq!(refined_damage_weapon(event, variant), variant);
        }
    }

    #[test]
    fn damage_name_preserves_explicit_variants() {
        for (event, observed) in [
            ("revolver", "deagle"),
            ("m4a1_silencer", "m4a1"),
            ("usp_silencer", "hkp2000"),
        ] {
            assert_eq!(refined_damage_weapon(event, observed), event);
        }
    }

    #[test]
    fn damage_name_preserves_labels_without_matching_evidence() {
        for (event, observed) in [
            ("m4a1", "m4a1"),
            ("m4a1", "knife"),
            ("deagle", "usp_silencer"),
            ("hegrenade", "usp_silencer"),
            ("inferno", "m4a1_silencer"),
            ("planted_c4", "hkp2000"),
            ("world", "revolver"),
            ("knife", "revolver"),
        ] {
            assert_eq!(refined_damage_weapon(event, observed), event);
        }
    }

    #[test]
    fn shared_classes_resolve_each_item_definition() {
        for (class, variants, slot) in [
            ("CDEagle", PISTOLS, Secondary),
            ("CWeaponM4A1", RIFLES, Primary),
            ("CWeaponHKP2000", STARTING_PISTOLS, Secondary),
            ("CKnife", KNIVES, Melee),
            ("CWeaponMP7", SMGS, Primary),
            ("CWeaponP250", P250_VARIANTS, Secondary),
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
            ("CWeaponP250", P250_VARIANTS),
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
    fn dedicated_pistol_classes_ignore_foreign_item_definitions() {
        for (class, definition, subclass, name) in [
            ("CWeaponCZ75a", 36, 1_573_262_270, "cz75a"),
            ("CWeaponFiveSeven", 30, 884_934_217, "fiveseven"),
            ("CWeaponTec9", 3, 3_661_698_933, "tec9"),
        ] {
            assert_eq!(
                entity_info(class, Some(definition), Some(subclass)).name,
                name
            );
        }
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

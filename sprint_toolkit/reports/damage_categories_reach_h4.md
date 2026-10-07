# Damage categories: Halo Reach and Halo 4 (player weapons, AI/vehicle guns, armour)

Generated 2026-10-07 from the baseline maps (E:\HaloBaselines, every campaign map; Reach m10-m70_bonus, H4 m10_crash-m90_sacrifice). Data: `sprint_toolkit/damage_categories_reach_h4.json`. Read-only survey, nothing was patched.

## How it was read
- Weapon tags: the `tag` values of every card under halo.json Player Modifiers -> Specific Weapon Modifier (per-game dict, nearest-earlier fallback), kept only where the tag exists in a map. Grenades come from the grenade list (Reach matg Grenades 0x444, H4 `globals\grenade_list` gggl).
- Effects: every tagRef in the Assembly plugin (ReachMCC/Halo4MCC first, then Reach/Halo4) followed from weap -> proj / effe -> jpt!, recursively (proj -> detonation projectile, effe -> parts). Zero-damage jpt! (camera shake, trigger_melee) are left out.
- Names: jpt! General / Specific Damage (Reach 0x70/0x74, H4 0x94/0x98) resolved with the dynamic offset, **re-derived on every map: +4747 on all ten Reach maps, +6841 on all eight H4 maps** (voted against the kits' armor_vs_damage.csv names). Cross-check: with those names, **all 432 Reach and all 500 H4 damage-table [0] multipliers equal the kit CSV value for the same (group, armour) pair.** The table is identical on every map of a game.
- `category` = the Specific Damage name when it is itself a damage group (e.g. `sniper`), else the General Damage name. `primary_category` skips `collision` (a projectile's physical knock) and the shared generic `melee`, prefers impact > detonation > attached > supercombine, uncharged before charged; melee weapons take their strongest hit.

---
## Halo Reach

Damage groups in table [0]: `melee`, `all`, `sniper`, `plasma_turret`, `bullet_slow`, `bullet_fast`, `bullet_turret`, `needle`, `plasma_slow`, `plasma_fast`, `laser`, `explosion_small`, `explosion_large`, `collision`, `cutting`, `burning`, `emp`, `no_damage`

Families from halo.json NOT in this game's maps: SMG, Brute Plasma Rifle, Battle Rifle, Brute Shot, Beam Rifle, Covenant Carbine, Sentinel Beam, Sentinel Eliminator Beam, Mauler, Flamethrower, Missile Pod, Claymore Grenade, Firebomb Grenade, Storm Rifle, Scattershot, LightRifle, Suppressor, Boltshot, Railgun, Sticky Detonator, Binary Rifle, Incineration Cannon, Pulse Grenade

### Player weapons by primary category

| Category | Weapons |
|---|---|
| `bullet_fast` | DMR |
| `bullet_slow` | Assault Rifle, Pistol, Shotgun, SAW |
| `bullet_turret` | Machine Gun |
| `cutting` | Energy Blade |
| `explosion_large` | Rocket Launcher, Flak Cannon |
| `explosion_small` | Frag Grenade, Plasma Grenade, Gravity Hammer, Grenade Launcher, Plasma Launcher |
| `laser` | Spartan Laser |
| `melee` | Target Locator |
| `needle` | Needler, Needle Rifle |
| `plasma_fast` | Concussion Rifle, Focus Rifle, Plasma Repeater |
| `plasma_slow` | Plasma Pistol, Plasma Rifle, Spike Rifle |
| `plasma_turret` | Plasma Cannon |
| `sniper` | Sniper Rifle |

### Per weapon: every damaging effect

| Weapon | weap / projectile | Primary | Other categories it deals (role) |
|---|---|---|---|
| Assault Rifle | `assault_rifle` | `bullet_slow` | `bullet_slow` (impact, 6.788); `melee` (melee, 79) |
| Pistol | `magnum` | `bullet_slow` | `bullet_slow` (impact, 17.5); `melee` (melee, 79) |
| Plasma Pistol | `plasma_pistol` | `plasma_slow` | `plasma_slow` (impact, 16); `plasma_slow` (detonation_charged, 36); `emp` (impact_charged, 200); `melee` (melee, 79) |
| Plasma Rifle | `plasma_rifle` | `plasma_slow` | `plasma_slow` (impact, 10); `melee` (melee, 79) |
| Needler | `needler` | `needle` | `explosion_small` (supercombine_attached, 350); `needle` (impact, 6); `explosion_small` (supercombine, 40); `melee` (melee, 79) |
| Sniper Rifle | `sniper_rifle` | `sniper` | `sniper` (impact, 80); `melee` (melee, 79) |
| Rocket Launcher | `rocket_launcher` | `explosion_large` | `explosion_large` (detonation, 240); `collision` (impact, 200); `melee` (melee, 79) |
| Shotgun | `shotgun` | `bullet_slow` | `bullet_slow` (impact, 10); `melee` (melee, 79) |
| Flak Cannon | `flak_cannon` | `explosion_large` | `explosion_large` (detonation, 60); `collision` (impact, 100); `melee` (melee, 79) |
| Energy Blade | `energy_sword` | `cutting` | `melee` (melee, 79); `cutting` (melee, 250) |
| Frag Grenade | `frag_grenade` | `explosion_small` | `explosion_small` (attached_detonation, 3000); `explosion_small` (detonation, 160); `collision` (impact, 2) |
| Plasma Grenade | `plasma_grenade` | `explosion_small` | `explosion_small` (attached_detonation, 350); `explosion_small` (attached_detonation, 3000); `explosion_small` (detonation, 250); `collision` (impact, 2) |
| Spike Rifle | `spike_rifle` | `plasma_slow` | `plasma_slow` (impact, 9); `melee` (melee, 79) |
| Gravity Hammer | `gravity_hammer` | `explosion_small` | `melee` (melee, 79); `collision` (melee, 150); `explosion_small` (effect_damage, 160) |
| Spartan Laser | `spartan_laser` | `laser` | `laser` (detonation, 40); `laser` (impact, 100); `melee` (melee, 79) |
| Machine Gun | `machinegun_turret` +3 variant(s) | `bullet_turret` | `bullet_turret` (impact, 10); `bullet_turret` (impact, 8) |
| Plasma Cannon | `plasma_turret` +1 variant(s) | `plasma_turret` | `plasma_turret` (impact, 11.5) |
| Concussion Rifle | `concussion_rifle` | `plasma_fast` | `plasma_fast` (detonation, 21.5); `collision` (impact, 21.5); `melee` (melee, 79) |
| DMR | `dmr` | `bullet_fast` | `bullet_fast` (impact, 17.5); `melee` (melee, 79) |
| Focus Rifle | `focus_rifle` | `plasma_fast` | `plasma_fast` (impact, 3); `melee` (melee, 79) |
| Grenade Launcher | `grenade_launcher` | `explosion_small` | `explosion_small` (detonation, 180); `collision` (impact, 25); `explosion_small` (effect_damage, 180); `emp` (supercombine, 100); `melee` (melee, 79) |
| Needle Rifle | `needle_rifle` | `needle` | `explosion_small` (supercombine_attached, 350); `needle` (impact, 6); `explosion_small` (supercombine, 40); `melee` (melee, 79) |
| Plasma Launcher | `plasma_launcher` | `explosion_small` | `explosion_small` (attached_detonation, 300); `explosion_small` (detonation, 175); `collision` (impact, 2); `melee` (melee, 79) |
| Plasma Repeater | `plasma_repeater` | `plasma_fast` | `plasma_fast` (impact, 7); `melee` (melee, 79) |
| Target Locator | `target_laser` | `melee` | `melee` (melee, 79) |
| SAW | `saw` | `bullet_slow` | `bullet_slow` (impact, 7.5); `melee` (melee, 79) |

### AI-only and vehicle weapons (they hit the player through the same rows)

| Category | Weapons |
|---|---|
| `bullet_turret` | falcon_chin_gun, falcon_machinegun, pelican_chin_gun, scorpion_anti_infantry, anti_infantry_turret |
| `explosion_large` | hunter_fuel_rod, banshee_bomb_launcher, cov_anti_air_cannon, shade_anti_air_cannon, shade_flak_cannon, wraith_mortar, falcon_grenade_launcher (+emp, explosion_small), scorpion_cannon, warthog_rocket_pod |
| `explosion_small` | revenant_plasma_turret, warthog_gauss |
| `laser` | anti_air_cannon |
| `plasma_turret` | banshee_dual_cannon (+explosion_large), ghost_dual_cannon, phantom_chin_gun, shade_plasma_cannon, wraith_anti_infantry |
| `sniper` | sniper_rifle_june |

### Armour names (damage table [0]) and who wears them

Users come from each bipd/vehi hlmt: Model Materials -> Global Material Index (bodies), Damage Sections with a Shield Global Material (shields; `engineer overshield` = the Engineer-buff section, `armour lock` = the armour-lock sections). Material -> armour follows the matg Materials parent chain. A `shield` section only proves the hlmt has one; whether the species actually spawns with shield vitality is the character's call (e.g. Grunts/Jackals/Hunters carry a dormant `shield` section).

| Class | Armour name | In table [0] | Users (object, part [material]) |
|---|---|---|---|
| Shields | `energy` | yes (18 groups) | - |
| Shields | `energy_shield_thin` | yes (18 groups) | bfg: body [energy_shield_thin_cov], shield [energy_shield_thin_cov]; brute: armour lock [energy_shield_thin_hum_spartan], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin]; brute_chieftain: armour lock [energy_shield_thin_hum_spartan], chieftain armour [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite]; bugger: engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; elite: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; elite_ai: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thi ... |
| Shields | `energy_shield_thick` | yes (18 groups) | anti_infantry_turret: shield [energy_shield_thick_hum]; cov_squad_drop_pod: body [energy_shield_thick_cov]; hunter: shield [energy_shield_thick_cov]; seraph: body [energy_shield_thick_cov]; seraph_in_atmosphere: body [energy_shield_thick_cov] |
| Shields | `energy_shield_solid` | yes (18 groups) | seraph: shield [energy_shield_solid]; seraph_in_atmosphere: shield [energy_shield_solid]; space_phantom: shield [energy_shield_solid] |
| Shields | `energy_shield_invulnerable` | yes (18 groups) | brute: armour lock [energy_shield_invulnerable]; brute_chieftain: armour lock [energy_shield_invulnerable]; elite: armour lock [energy_shield_invulnerable]; elite_ai: armour lock [energy_shield_invulnerable]; elite_no_recharge: armour lock [energy_shield_invulnerable]; hologram_elite: body [energy_hologram]; hologram_jackal: body [energy_hologram]; hologram_spartan: body [energy_hologram]; spartan_jorge: armour lock [energy_shield_invulnerable]; spartans: armour lock [energy_shield_invulnerable]; spartans_ai: armour lock [energy_shield_invulnerable]; spartans_female_ai: armour lock [energy_shield_invulnerable] |
| Shields | `energy_shield_thin_player` | **no row** | brute: armour lock [energy_shield_thin_hum_spartan], engineer overshield [energy_shield_thin_cov_elite]; brute_chieftain: armour lock [energy_shield_thin_hum_spartan], chieftain armour [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite]; bugger: engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; elite: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; elite_ai: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; elite_no_recharge: armour lock [energy_shield ... |
| Armour | `hard_metal_thin` | yes (18 groups) | anti_infantry_turret: body [hard_metal_thin_hum_object]; cargo_truck: body [hard_metal_thin_hum_warthog]; cart_electric: body [hard_metal_thin_hum]; drop_pod_elite: body [hard_metal_thin_cov_banshee]; elite: body [hard_metal_thin_cov_elite]; elite_ai: body [hard_metal_thin_cov_elite]; elite_no_recharge: body [hard_metal_thin_cov_elite]; engineer: body [hard_metal_thin_for]; ghost: body [hard_metal_thin_cov_ghost]; mongoose: body [hard_metal_thin_hum]; oni_ext_security_camera: body [hard_metal_thin_hum]; phantom: body [hard_metal_thin_cov]; space_banshee: body [hard_metal_thin_cov_banshee]; spartan_jorge: body [hard_metal_thin_hum_spartan]; spartans: body [hard_metal_thin_hum_spartan]; sparta ... |
| Armour | `hard_metal_thin_player` | **no row** | elite: body [hard_metal_thin_cov_elite]; elite_ai: body [hard_metal_thin_cov_elite]; elite_no_recharge: body [hard_metal_thin_cov_elite]; spartan_jorge: body [hard_metal_thin_hum_spartan]; spartans: body [hard_metal_thin_hum_spartan]; spartans_ai: body [hard_metal_thin_hum_spartan]; spartans_female_ai: body [hard_metal_thin_hum_spartan]; spartans_unshielded: body [hard_metal_thin_hum_spartan] |
| Flesh | `soft` | yes (18 groups) | - |
| Flesh | `soft_organic` | yes (18 groups) | brute: body [soft_organic_flesh]; brute_chieftain: body [soft_organic_flesh]; civilian_female: body [soft_organic_flesh]; civilian_male: body [soft_organic_flesh]; engineer: body [soft_organic_flesh_grunt]; grunt: body [soft_organic_flesh_grunt]; halsey: body [soft_organic_flesh]; hunter: body [soft_organic_flesh_hunter]; jackal: body [soft_organic_flesh_jackal]; marine: body [soft_organic_flesh]; marine_female: body [soft_organic_flesh_human]; mule: body [soft_organic_flesh]; null: body [soft_organic_flesh]; reach_moa: body [soft_organic_flesh] |
| Flesh | `soft_inorganic` | yes (18 groups) | cart_electric: body [soft_inorganic_vinyl_hum]; grunt: body [hard_metal_thin_cov_grunt]; military_truck: body [soft_inorganic_vinyl_hum_warthog] |
| Flesh | `soft_organic_flesh_hunter` | **no row** | hunter: body [soft_organic_flesh_hunter] |
| Brute hide | `tough_organic` | yes (18 groups) | bugger: body [tough_organic_flesh_bugger]; mule: body [tough_organic_bone], body [tough_organic_flesh_mule]; vent_cover_emitter: body [tough_organic_wood] |
| Vehicles + Hunter plates | `hard_metal_thick` | yes (18 groups) | anti_air_cannon: body [hard_metal_thick]; banshee: body [hard_metal_thick_cov_banshee]; bed_long: body [hard_metal_thick_hum_chassis], body [hard_metal_thick_hum_hollow_huge]; bed_small: body [hard_metal_thick_hum_chassis], body [hard_metal_thick_hum_hollow_huge]; cargo_truck: body [hard_metal_thick_hum_chassis]; cart_electric: body [hard_metal_thick_hum_chassis]; chin_gun: body [hard_metal_thick_cov]; corvette_ball_turret: body [hard_metal_thick_cov]; falcon: body [hard_metal_thick_hum]; falcon_chin_gun: body [hard_metal_thick]; falcon_sensor: body [hard_metal_thick]; falcon_side_grenade_left: body [hard_metal_thick_hum]; falcon_side_grenade_right: body [hard_metal_thick_hum]; falcon_side_g ... |
| Vehicles + Hunter plates | `hard_metal_solid` | yes (18 groups) | beam_turret: body [hard_metal_solid_cov]; bfg: body [hard_metal_solid_cov]; cov_squad_drop_pod: body [hard_metal_solid_cov]; hunter: body [hard_metal_solid_cov_hunter]; pelican_chin_gun: body [hard_metal_solid]; phantom: body [hard_metal_solid_cov_phantom]; phantom_chin_gun: body [hard_metal_solid_cov_phantom]; scorpion: body [hard_metal_solid_hum]; scorpion_anti_infantry: body [hard_metal_solid_hum]; scorpion_cannon: body [hard_metal_solid_hum]; tuning_fork: body [hard_metal_solid_cov_phantom]; tuning_fork_turret: body [hard_metal_solid_cov_phantom]; wraith: body [hard_metal_solid_cov_wraith]; wraith_anti_infantry: body [hard_metal_solid_cov_wraith]; wraith_mortar: body [hard_metal_solid_co ... |
| other | `material` | yes (18 groups) | anti_air_cannon: shield [default_material]; civilian_male: body [default_material]; cortana: body [default_material]; corvette_cannon: body [default_material]; keyes: body [default_material]; poa_cannon: body [default_material]; sara: body [default_material] |
| other | `liquid` | yes (18 groups) | - |
| other | `tough` | yes (18 groups) | - |
| other | `tough_inorganic` | yes (18 groups) | cart_electric: body [tough_inorganic_plastic_hum]; marine: body [tough_inorganic_armor_hum]; warthog_troop: body [tough_inorganic] |
| other | `hard` | yes (18 groups) | cargo_truck: body [tough_inorganic_rubber_hum_tire]; cart_electric: body [tough_inorganic_rubber_hum_tire]; forklift: body [tough_inorganic_rubber_hum_tire_civilian]; military_truck: body [tough_inorganic_rubber_hum_tire]; mongoose: body [tough_inorganic_rubber_hum_tire_mongoose]; pickup: body [tough_inorganic_rubber_hum_tire]; reflection_lighting_test: body [hard]; warthog: body [tough_inorganic_rubber_hum_tire] |
| other | `hard_metal_invulnerable` | yes (18 groups) | - |
| other | `hard_terrain` | yes (18 groups) | - |
| other | `brittle` | yes (18 groups) | - |
| other | `brittle_glass` | yes (18 groups) | cargo_truck: body [brittle_glass_hum]; falcon: body [brittle_glass_hum_warthog]; security_camera_interior: body [brittle_glass_hum]; truck_cab_large: body [brittle_glass_hum]; warthog: body [brittle_glass_hum_warthog] |
| other | `brittle_elec` | yes (18 groups) | bfg: body [brittle_elec_cov]; oni_ext_security_camera: body [brittle_elec_hum]; phantom_chin_gun: body [brittle_elec_cov] |
| other | `brittle_mech` | yes (18 groups) | ghost: body [brittle_mech_cov]; scorpion: body [brittle_mech_hum_engine_scorpion]; wraith: body [brittle_mech_cov] |
| other | `brittle_explosive` | yes (18 groups) | - |
| other | `scarab` | **no row** | main_turret: body [hard_metal_thick_cov_scarab] |

### Player material (open question 1)

Player biped `objects\characters\spartans\spartans`:
- body: matg Materials[80] `hard_metal_thin_hum_spartan`, parent chain `hard_metal_thin_hum_spartan` -> `hard_metal_thin_hum` -> `hard_metal_thin`, General Armor `hard_metal_thin` (inherited from `hard_metal_thin`), Specific Armor `hard_metal_thin_player`
- shield: matg Materials[185] `energy_shield_thin_hum_spartan`, parent chain `energy_shield_thin_hum_spartan` -> `energy_shield_thin_hum` -> `energy_shield_thin`, General Armor `energy_shield_thin` (inherited from `energy_shield_thin`), Specific Armor `energy_shield_thin_player`
Elite biped `objects\characters\elite\elite`:
- body: matg Materials[93] `hard_metal_thin_cov_elite`, General `hard_metal_thin`, Specific `hard_metal_thin_player`
- shield: matg Materials[187] `energy_shield_thin_cov_elite`, General `energy_shield_thin`, Specific `energy_shield_thin_player`

Other users of the player's materials (anything keyed on these entries changes them too):
- `hard_metal_thin_hum_spartan`: spartan_jorge (bipd) body, spartans (bipd) body, spartans_ai (bipd) body, spartans_female_ai (bipd) body, spartans_unshielded (bipd) body
- `energy_shield_thin_hum_spartan`: brute (bipd) armour lock, brute_chieftain (bipd) armour lock, spartan_jorge (bipd) armour lock, spartan_jorge (bipd) shield, spartans (bipd) armour lock, spartans (bipd) shield, spartans_ai (bipd) armour lock, spartans_ai (bipd) shield, spartans_female_ai (bipd) armour lock, spartans_female_ai (bipd) shield

Specific Armor names set on materials vs rows in table [0]: `soft_organic_flesh_hunter` **no rows**, `hard_metal_thin_player` **no rows**, `scarab` **no rows**, `energy_shield_thin_player` **no rows**

Candidate specific-armour keys (existing stringids, not used as an armour name anywhere in matg):
- `hard_metal_thin_hum_spartan` = stringid 0x57e (matg Materials[80].Name)
- `energy_shield_thin_hum_spartan` = stringid 0x646 (matg Materials[185].Name)

---
## Halo 4

Damage groups in table [0]: `melee`, `all`, `sniper`, `plasma_turret`, `bullet_slow`, `plasma_slow`, `bullet_fast`, `plasma_fast`, `bullet_turret`, `bullet_turret_mech`, `explosion_small`, `explosion_small_old`, `explosion_large`, `collision`, `cutting`, `burning`, `emp`, `laser`, `no_damage`, `needle`

Families from halo.json NOT in this game's maps: Plasma Rifle, SMG, Brute Plasma Rifle, Brute Shot, Sentinel Eliminator Beam, Mauler, Spike Rifle, Flamethrower, Missile Pod, Claymore Grenade, Firebomb Grenade, Grenade Launcher, Needle Rifle, Plasma Launcher, Plasma Repeater

### Player weapons by primary category

| Category | Weapons |
|---|---|
| `bullet_fast` | Battle Rifle, DMR, SAW |
| `bullet_slow` | Assault Rifle, Pistol, Shotgun, Scattershot, Boltshot |
| `bullet_turret` | Machine Gun |
| `cutting` | Energy Blade |
| `explosion_large` | Rocket Launcher, Flak Cannon, Incineration Cannon |
| `explosion_small` | Frag Grenade, Plasma Grenade, Gravity Hammer, Sticky Detonator, Pulse Grenade |
| `laser` | Sentinel Beam, Spartan Laser |
| `melee` | Target Locator |
| `needle` | Needler, Railgun |
| `plasma_fast` | Covenant Carbine, Concussion Rifle, Focus Rifle, Storm Rifle, LightRifle, Suppressor |
| `plasma_slow` | Plasma Pistol |
| `plasma_turret` | Plasma Cannon |
| `sniper` | Sniper Rifle, Beam Rifle, Binary Rifle |

### Per weapon: every damaging effect

| Weapon | weap / projectile | Primary | Other categories it deals (role) |
|---|---|---|---|
| Assault Rifle | `storm_assault_rifle` | `bullet_slow` | `bullet_slow` (impact, 7.5); `melee` (melee, 70) |
| Pistol | `storm_magnum` | `bullet_slow` | `bullet_slow` (impact, 15); `melee` (melee, 70) |
| Plasma Pistol | `storm_plasma_pistol` +1 variant(s) | `plasma_slow` | `plasma_slow` (impact, 14); `plasma_slow` (detonation_charged, 36); `emp` (impact_charged, 200); `melee` (melee, 70) |
| Needler | `storm_needler` | `needle` | `explosion_small` (supercombine_attached, 350); `needle` (impact, 6); `explosion_small` (supercombine, 40); `melee` (melee, 70) |
| Sniper Rifle | `storm_sniper_rifle` | `sniper` | `sniper` (impact, 80); `melee` (melee, 70) |
| Rocket Launcher | `storm_rocket_launcher` | `explosion_large` | `explosion_large` (detonation, 240); `collision` (impact, 200); `melee` (melee, 70) |
| Shotgun | `storm_shotgun` | `bullet_slow` | `bullet_slow` (impact, 10.5); `melee` (melee, 70) |
| Battle Rifle | `storm_br` | `bullet_fast` | `bullet_fast` (impact, 5.8333); `melee` (melee, 70) |
| Beam Rifle | `storm_beam_rifle` | `sniper` | `plasma_fast/sniper` (impact, 80); `melee` (melee, 70) |
| Covenant Carbine | `storm_covenant_carbine` | `plasma_fast` | `plasma_fast` (impact, 10); `melee` (melee, 70) |
| Flak Cannon | `storm_fuel_rod_cannon` | `explosion_large` | `explosion_large` (detonation, 60); `collision` (impact, 100); `melee` (melee, 70) |
| Sentinel Beam | `storm_sentinel_beam` | `laser` | `laser` (impact, 3); `melee` (melee, 70) |
| Energy Blade | `storm_energy_sword` +1 variant(s) | `cutting` | `melee` (melee, 70); `cutting` (melee, 250) |
| Frag Grenade | `storm_frag_grenade` | `explosion_small` | `explosion_small` (attached_detonation, 3000); `explosion_small` (detonation, 180); `collision` (impact, 2) |
| Plasma Grenade | `storm_plasma_grenade` | `explosion_small` | `explosion_small` (attached_detonation, 350); `explosion_small` (attached_detonation, 3000); `explosion_small` (detonation, 250); `collision` (impact, 2) |
| Gravity Hammer | `storm_gravity_hammer` | `explosion_small` | `melee` (melee, 70); `collision` (melee, 150); `explosion_small` (effect_damage, 200) |
| Spartan Laser | `storm_spartan_laser` | `laser` | `laser` (detonation, 40); `laser` (impact, 100); `melee` (melee, 70) |
| Machine Gun | `storm_machinegun_turret` +2 variant(s) | `bullet_turret` | `bullet_turret` (impact, 10); `bullet_turret` (impact, 8.5) |
| Plasma Cannon | `storm_plasma_turret` +1 variant(s) | `plasma_turret` | `plasma_turret` (impact, 11.5) |
| Concussion Rifle | `storm_concussion_rifle` | `plasma_fast` | `plasma_fast` (detonation, 21.5); `collision` (impact, 21.5); `melee` (melee, 70) |
| DMR | `storm_dmr` | `bullet_fast` | `bullet_fast` (impact, 17.5); `melee` (melee, 70) |
| Focus Rifle | `focus_rifle` | `plasma_fast` | `plasma_fast` (impact, 3); `melee` (melee, 70) |
| Target Locator | `target_laser` | `melee` | `melee` (melee, 70) |
| Storm Rifle | `storm_assault_carbine` | `plasma_fast` | `plasma_fast` (impact, 8); `melee` (melee, 70) |
| SAW | `storm_lmg` | `bullet_fast` | `bullet_fast` (impact, 7.5); `melee` (melee, 70) |
| Scattershot | `storm_spread_gun` +1 variant(s) | `bullet_slow` | `explosion_small` (supercombine_attached, 250); `bullet_slow` (impact, 12); `explosion_small` (supercombine, 40); `melee` (melee, 70) |
| LightRifle | `storm_forerunner_rifle` +1 variant(s) | `plasma_fast` | `plasma_fast` (impact, 5.3333); `plasma_fast` (impact, 23.5); `melee` (melee, 70) |
| Suppressor | `storm_forerunner_smg` +2 variant(s) | `plasma_fast` | `plasma_fast` (impact, 6.25); `melee` (melee, 70) |
| Boltshot | `storm_stasis_pistol` +1 variant(s) | `bullet_slow` | `bullet_slow` (impact, 7.5); `bullet_slow` (impact_charged, 10); `melee` (melee, 70) |
| Railgun | `storm_rail_gun_pve` | `needle` | `explosion_small` (detonation, 180); `needle` (impact, 120); `melee` (melee, 70) |
| Sticky Detonator | `storm_sticky_detonator_pve` | `explosion_small` | `explosion_small` (attached_detonation, 500); `collision` (impact, 5); `explosion_small` (supercombine, 500); `melee` (melee, 70) |
| Binary Rifle | `storm_forerunner_sniper_rifle` +1 variant(s) | `sniper` | `sniper` (impact, 129); `melee` (melee, 70) |
| Incineration Cannon | `storm_forerunner_incineration_launcher` +1 variant(s) | `explosion_large` | `explosion_large` (detonation, 240); `explosion_large` (detonation, 120); `collision` (impact, 200); `melee` (melee, 70) |
| Pulse Grenade | `storm_energy_drain_grenade` | `explosion_small` | `explosion_small` (attached_detonation, 3000); `None` (effect_damage, 0.33); `explosion_small` (effect_damage, 120); `explosion_small` (effect_damage, 140); `collision` (impact, 20); `collision` (impact, 2) |

### AI-only and vehicle weapons (they hit the player through the same rows)

| Category | Weapons |
|---|---|
| `bullet_slow` | storm_auto_turret/weapon, storm_auto_turret/weapon_knight, storm_auto_turret/weapon_pve |
| `bullet_turret` | bishop_turret, pelican_chaingun, storm_pelican_side_turret, storm_pelican_side_turret_mirror, storm_scorpion_anti_infantry |
| `bullet_turret_mech` | mech_main_gun_campaign |
| `explosion_large` | storm_storm_hunter_fuel_rod, mech_rocket_launcher, storm_banshee_bomb_launcher, storm_wraith_mortar, storm_didact_ship_beam, storm_infinity_turret, storm_mammoth_rocket_turret_pod, storm_pelican_cannon, storm_scorpion_cannon, storm_warthogrocket_pod, storm_missile_battery, cruise_missile_self_destruct_weapon, hunter_lmg |
| `explosion_small` | storm_broadsword_missile, storm_mammoth_main_gun, storm_warthoggauss, storm_asteroid_gun15cm, storm_asteroid_gun15cm_m60 |
| `laser` | storm_broadsword_gatling_gun, storm_pelican_gauss, storm_unsc_artillery |
| `plasma_fast` | storm_lich_main_gun, storm_anti_infantry_beam, storm_anti_infantry_beam_m90, storm_bishop_beam |
| `plasma_slow` | storm_pawn_head, storm_burst_pistol |
| `plasma_turret` | storm_banshee_dual_cannon (+explosion_large), storm_ghost_dual_cannon, storm_ghost_dual_cannon_m30, storm_phantom_chin_gun, storm_phantom_chin_gun_dogfight, storm_wraith_anti_infantry, storm_shade_plasma_cannon, storm_anti_vehicle_turret_plasma_cannon, storm_tracer_turret |
| `sniper` | storm_pawnsniper_head |

### Armour names (damage table [0]) and who wears them

Users come from each bipd/vehi hlmt: Model Materials -> Global Material Index (bodies), Damage Sections with a Shield Global Material (shields; `engineer overshield` = the Engineer-buff section, `armour lock` = the armour-lock sections). Material -> armour follows the matg Materials parent chain. A `shield` section only proves the hlmt has one; whether the species actually spawns with shield vitality is the character's call (e.g. Grunts/Jackals/Hunters carry a dormant `shield` section).

| Class | Armour name | In table [0] | Users (object, part [material]) |
|---|---|---|---|
| Shields | `energy` | yes (20 groups) | - |
| Shields | `energy_shield_thin` | yes (20 groups) | storm_bishop: shield [energy_shield_thin_for]; storm_broadsword: shield [energy_shield_thin_hum_spartan]; storm_campaign_mantis: shield [energy_shield_thin]; storm_elite_ai: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; storm_hunter: engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin]; storm_jackal: engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin]; storm_knight: shield [energy_shield_thin_for]; storm_masterchief: shield [energy_shield_thin_hum_spartan]; storm_spartans_ai: armour lock [energy_shield_thin_hum_spartan], shield [energy_shield_thin_hu ... |
| Shields | `energy_shield_thick` | yes (20 groups) | bishop_turret: shield [energy_shield_thick_hum]; cov_squad_drop_pod: body [energy_shield_thick_cov] |
| Shields | `energy_shield_solid` | yes (20 groups) | storm_lich: body [energy_shield_solid] |
| Shields | `energy_shield_invulnerable` | yes (20 groups) | storm_elite_ai: armour lock [energy_shield_invulnerable]; storm_hologram_storm_masterchief: body [energy_hologram], shield [energy_hologram]; storm_spartans_ai: armour lock [energy_shield_invulnerable] |
| Shields | `energy_shield_thin_player` | **no row** | storm_broadsword: shield [energy_shield_thin_hum_spartan]; storm_elite_ai: armour lock [energy_shield_thin_cov_elite], engineer overshield [energy_shield_thin_cov_elite], shield [energy_shield_thin_cov_elite]; storm_hunter: engineer overshield [energy_shield_thin_cov_elite]; storm_jackal: engineer overshield [energy_shield_thin_cov_elite]; storm_masterchief: shield [energy_shield_thin_hum_spartan]; storm_spartans_ai: armour lock [energy_shield_thin_hum_spartan], shield [energy_shield_thin_hum_spartan] |
| Armour | `hard_metal_thin` | yes (20 groups) | bishop_turret: body [hard_metal_thin_hum_object]; drop_pod_elite: body [hard_metal_thin_cov_banshee]; storm_anti_infantry_turret: body [hard_metal_thin_cov_ghost]; storm_anti_infantry_turret_m90: body [hard_metal_thin_cov_ghost]; storm_bishop: body [hard_metal_thin_for]; storm_elite_ai: body [hard_metal_thin_cov_elite]; storm_ghost: body [hard_metal_thin_cov_ghost]; storm_ghost_infinite_boost: body [hard_metal_thin_cov_ghost]; storm_knight: body [hard_metal_thin_for]; storm_masterchief: body [hard_metal_thin_hum_spartan]; storm_mongoose: body [hard_metal_thin_hum]; storm_pawn: body [hard_metal_thin_for]; storm_phantom: body [hard_metal_thin_cov]; storm_sentinel: body [hard_metal_thin_for]; s ... |
| Armour | `hard_metal_thin_player` | **no row** | storm_elite_ai: body [hard_metal_thin_cov_elite]; storm_masterchief: body [hard_metal_thin_hum_spartan]; storm_spartans_ai: body [hard_metal_thin_hum_spartan] |
| Flesh | `soft` | yes (20 groups) | - |
| Flesh | `soft_organic` | yes (20 groups) | null: body [soft_organic_flesh]; storm_civilian_female: body [soft_organic_flesh_human]; storm_civilian_male: body [soft_organic_flesh_human]; storm_del_rio: body [soft_organic_flesh]; storm_grunt: body [soft_organic_flesh_grunt]; storm_hunter: body [soft_organic_flesh_hunter]; storm_jackal: body [soft_organic_flesh_jackal]; storm_lasky: body [soft_organic_flesh]; storm_librarian: body [soft_organic_flesh]; storm_marine: body [soft_organic_flesh]; storm_marine_m60: body [soft_organic_flesh]; storm_tillson: body [soft_organic_cloth_hum], body [soft_organic_flesh_human] |
| Flesh | `soft_inorganic` | yes (20 groups) | storm_grunt: body [hard_metal_thin_cov_grunt] |
| Flesh | `soft_organic_flesh_hunter` | **no row** | storm_hunter: body [soft_organic_flesh_hunter] |
| Brute hide | `tough_organic` | yes (20 groups) | - |
| Vehicles + Hunter plates | `hard_metal_thick` | yes (20 groups) | machinegun: body [hard_metal_thick_hum]; plasma_turret_mounted: body [hard_metal_thick_cov]; plasma_turret_mounted_nodetach: body [hard_metal_thick_cov]; plasma_turret_mounted_phantom: body [hard_metal_thick_cov]; plasma_turret_watchtower_mounted: body [hard_metal_thick_cov]; storm_anti_infantry_turret: body [hard_metal_thick_cov_shade]; storm_anti_infantry_turret_m90: body [hard_metal_thick_cov_shade]; storm_anti_vehicle_turret: body [hard_metal_thick_cov_shade]; storm_asteroid_gun: body [hard_metal_thick]; storm_asteroid_gun_m60: body [hard_metal_thick]; storm_banshee: body [hard_metal_thick_cov_banshee]; storm_campaign_mantis: body [hard_metal_thick_hum]; storm_hunter: body [hard_metal_th ... |
| Vehicles + Hunter plates | `hard_metal_solid` | yes (20 groups) | cov_squad_drop_pod: body [hard_metal_solid_cov]; storm_broadsword: body [hard_metal_solid_hum_longsword]; storm_drop_pod_medium_four_doors: body [hard_metal_solid_cov]; storm_drop_pod_small: body [hard_metal_solid_cov]; storm_hunter: body [hard_metal_solid_cov_hunter]; storm_lich: body [hard_metal_solid_cov_phantom]; storm_lich_main_gun: body [hard_metal_solid_cov_phantom]; storm_pelican: body [hard_metal_solid_hum_pelican]; storm_pelican_cannon: body [hard_metal_solid_hum_pelican]; storm_phantom: body [hard_metal_solid_cov_phantom]; storm_phantom_chin_gun: body [hard_metal_solid_cov_phantom]; storm_phantom_chin_gun_dogfight: body [hard_metal_solid_cov_phantom]; storm_scorpion: body [hard_me ... |
| other | `material` | yes (20 groups) | cruise_missile_model: body [default_material]; storm_cortana: body [default_material]; storm_didact: body [default_material]; storm_lich: body [default_material]; storm_unsc_artillery: shield [default_material] |
| other | `liquid` | yes (20 groups) | - |
| other | `tough` | yes (20 groups) | - |
| other | `tough_inorganic` | yes (20 groups) | - |
| other | `hard` | yes (20 groups) | storm_mongoose: body [tough_inorganic_rubber_hum_tire_mongoose]; storm_warthog: body [tough_inorganic_rubber_hum_tire] |
| other | `hard_metal_invulnerable` | yes (20 groups) | storm_scorpion_anti_infantry: body [hard_metal_invulnerable] |
| other | `hard_terrain` | yes (20 groups) | - |
| other | `brittle` | yes (20 groups) | - |
| other | `brittle_glass` | yes (20 groups) | storm_warthog: body [brittle_glass_hum_warthog] |
| other | `brittle_elec` | yes (20 groups) | storm_lich_main_gun: body [brittle_elec_cov]; storm_phantom_chin_gun: body [brittle_elec_cov]; storm_phantom_chin_gun_dogfight: body [brittle_elec_cov] |
| other | `brittle_elec_hum_env` | yes (20 groups) | - |
| other | `brittle_mech` | yes (20 groups) | - |
| other | `brittle_explosive` | yes (20 groups) | cruise_missile_model: body [brittle_explosive_cov]; unsc_missile: body [brittle_explosive_hum] |

### Player material (open question 1)

Player biped `objects\characters\storm_masterchief\storm_masterchief`:
- body: matg Materials[80] `hard_metal_thin_hum_spartan`, parent chain `hard_metal_thin_hum_spartan` -> `hard_metal_thin_hum` -> `hard_metal_thin`, General Armor `hard_metal_thin` (inherited from `hard_metal_thin`), Specific Armor `hard_metal_thin_player`
- shield: matg Materials[185] `energy_shield_thin_hum_spartan`, parent chain `energy_shield_thin_hum_spartan` -> `energy_shield_thin_hum` -> `energy_shield_thin`, General Armor `energy_shield_thin` (inherited from `energy_shield_thin`), Specific Armor `energy_shield_thin_player`
Elite biped `objects\characters\storm_elite_ai\storm_elite_ai`:
- body: matg Materials[93] `hard_metal_thin_cov_elite`, General `hard_metal_thin`, Specific `hard_metal_thin_player`
- shield: matg Materials[187] `energy_shield_thin_cov_elite`, General `energy_shield_thin`, Specific `energy_shield_thin_player`

Other users of the player's materials (anything keyed on these entries changes them too):
- `hard_metal_thin_hum_spartan`: storm_masterchief (bipd) body, storm_spartans_ai (bipd) body
- `energy_shield_thin_hum_spartan`: storm_broadsword (vehi) shield, storm_masterchief (bipd) shield, storm_spartans_ai (bipd) armour lock, storm_spartans_ai (bipd) shield
- `energy_hologram`: storm_hologram_storm_masterchief (bipd) body, storm_hologram_storm_masterchief (bipd) shield

Specific Armor names set on materials vs rows in table [0]: `soft_organic_flesh_hunter` **no rows**, `hard_metal_thin_player` **no rows**, `scarab` **no rows**, `energy_shield_thin_player` **no rows**

Candidate specific-armour keys (existing stringids, not used as an armour name anywhere in matg):
- `hard_metal_thin_hum_spartan` = stringid 0x6ed (matg Materials[80].Name)
- `energy_shield_thin_hum_spartan` = stringid 0x7b5 (matg Materials[185].Name)
- `energy_hologram` = stringid 0x7cf (matg Materials[199].Name)

---
## Findings and traps

- **The player's materials are their own entries, but every armour key on them is shared with the Elites.** Reach and H4 alike: Spartan body = Materials[80] `hard_metal_thin_hum_spartan`, shield = [185] `energy_shield_thin_hum_spartan`; Elite body [93] `hard_metal_thin_cov_elite`, shield [187] `energy_shield_thin_cov_elite`. None of the four has its own General Armor: they inherit `hard_metal_thin` / `energy_shield_thin` from the parent chain. All four carry the SAME Specific Armor `hard_metal_thin_player` / `energy_shield_thin_player`, a leftover of H3, and **table [0] has no row for either** (the kit CSVs, tilted included, have no `_player` rows for Reach/H4). So writing `_player` rows would hit Elites (and, for the shield, every Engineer overshield, which uses the Elite shield material) as well.
- **Player-only route:** give materials 80 and 185 a new Specific Armor (their own name stringids are the obvious keys: Reach 0x57e / 0x646, H4 0x6ed / 0x7b5, unused as armour names), then add rows under that name. Only one Specific Armor per material, so the switch drops `_player` from them, which is harmless because nothing reads it. Caveat: material 80/185 are not player-exclusive. Reach: all Noble AI Spartans (spartans_ai, Jorge, female) and the Brute/Chieftain armour-lock sections use 185; H4: storm_spartans_ai and the Broadsword shield. For a strictly player-only key, clone the material into a new matg Materials entry (block growth) and repoint the player hlmt's Global Material Index / Shield Global Material Index.
- **Brutes in Reach are not `tough_organic`.** The Reach Brute and Chieftain bodies use `soft_organic_flesh` (index 12 -> `soft_organic`); their power armour is a damage section with the `energy_shield_thin` shield material (Chieftain: `armor_shield`, Elite shield material). `hard_metal_thin_cov_brute` -> `tough_organic` exists but no Brute hlmt uses it. H4 has no Brutes; nothing in the H4 campaign wears `tough_organic`. The "Brutes take half" line in tilt_explained.md is wrong for Reach.
- **Hunter plates are `hard_metal_thick` + `hard_metal_solid`**, the same rows as Ghost/Banshee/Wraith/Phantom hulls, so a "vs Hunter plates" card is a "vs vehicles" card. Hunter flesh carries the Specific Armor `soft_organic_flesh_hunter`, which has no row in either game (general `soft_organic` applies).
- **Knights, Crawlers, Watchers and the H4 Sentinel share `hard_metal_thin` with the player and the Elites**; Knight/Watcher shields are `energy_shield_thin_for` -> `energy_shield_thin`. So "vs Armour" and "vs Shields" in H4 cover Elites, Prometheans and the player at once.
- **Every projectile weapon's direct hit is `collision`** on rockets, grenades, flak/fuel rod, concussion rifle, plasma launcher, sticky detonator, incineration cannon (proj Impact Damage); the real damage is the detonation. The Gravity Hammer's swing jpt! is also `collision` (150); its blast is `explosion_small`.
- Reach `plasma_turret` and `bullet_turret` are their own groups (Plasma Cannon, Ghost, Shade, Wraith AI gun; MG turret, Warthog/Falcon guns). H4 adds `bullet_turret_mech` (Mantis) and `explosion_small_old` (no weapon found using it).
- Charged shots: the Plasma Pistol overcharge is `plasma_slow` (detonation) + `emp` (impact 200) in both games; the Boltshot charge stays `bullet_slow`.
- Needler / Needle Rifle / H4 Scattershot: impact `needle` (Scattershot `bullet_slow`), supercombine and attached-supercombine `explosion_small`.
- H4 Headshot Damage Multiplier (jpt! 0x30) is **0.0 on every jpt! reached** (303 reads): nothing uses it, headshots follow the engine default.
- The baselines carry the user's ports: Reach m20 has the SAW (`objects\weapons\rifle\saw\saw`, `bullet_slow`), H4 m30_cryptum the Focus Rifle (`plasma_fast`). The H4 SAW card points at the native `storm_lmg` (`bullet_fast`).
- Stringid trap confirmed: the damage-group ids are dynamic below 0x800, so the stock `resolve_stringid` (dynamic only from 0x800) misnames them; a handful are static (`melee`, `all`, `sniper`, `plasma_turret`, `energy` and the section name `shield`). Adjacent offsets (+-1) score almost as well against a name list because the dynamic names are consecutive; verify with the CSV values, not just names.
- Target Locator: only its melee was found; the airstrike damage lives behind the `airs` tag, which was not followed.

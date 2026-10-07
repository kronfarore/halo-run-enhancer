# Damage categories: Halo 1, Halo 2, Halo 3, ODST

Every player weapon sorted into the damage category its hits use, for the planned "Effective" cards (damage category x armour class). Data: `sprint_toolkit/damage_categories_h1_odst.json` (per-effect jpt! paths, roles, general/specific ids, armour users, table [0] multipliers).

**Category** = the damage group a jpt! names (General Damage), with `/specific` when it also names a Specific Damage. Halo 1 has no groups: its category is the Halo 2 group of the same weapon (analogy).

Method: all campaign baseline maps per game, plus live maps for ports. Graph weap -> barrels/triggers -> proj -> impact / detonation / attached / super-detonation / detonation-effect parts -> jpt!, plus the weap's melee slots. Firing, misfire, response, charging and clang jpt!s, and none/no_damage groups, are left out.

Stringid trap, solved generally: in H3/ODST every id ABOVE the map's static tail (`str_tbl_count - strip`, 697 on 010_jungle) is dynamic and sits at `idx + STATIC_TOTAL - (count - strip)` (2187 H3, 2671 ODST), the same rule `resolve_stringid` applies only from 0x800 up. The per-map offset varies a lot: H3 1258-2061, ODST 1682-2537 (010_jungle 1490 and sc110 1857 match tilt_explained.md). All names were checked against the kits' armor_vs_damage CSVs. ODST also misreads a few STATIC ids (see ODST).

## Halo 1

### Player weapons: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_fast` | Battle Rifle (port) | - |
| `bullet_fast/sniper` | Sniper Rifle | - |
| `bullet_slow` | Assault Rifle, Pistol, SMG (port) | - |
| `bullet_slow/kill_flood` | Shotgun | - |
| `bullet_vehicle` | SAW (port) | - |
| `burning` | Flamethrower | - |
| `cutting` | Energy Blade (port) | - |
| `emp` | - | Plasma Pistol (charged_impact) |
| `explosion_attached` | - | Plasma Grenade (attached) |
| `explosion_large` | Rocket Launcher, Flak Cannon (Fuel Rod Gun) | - |
| `explosion_small` | Frag Grenade, Plasma Grenade | Needler (supercombine) |
| `plasma_fast/anti_flood` | Sentinel Beam (port) | - |
| `plasma_slow` | Plasma Pistol, Plasma Rifle, Needler | - |
| `melee` | - | 14 weapons' melee |

### AI weapons and vehicle guns: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_vehicle` | Warthog chaingun, Scorpion cannon + MG | - |
| `burning` | Gravity rifle (cut MP weapon) | - |
| `explosion_large` | Hunter fuel rod cannon, Wraith mortar | Banshee gun (bolts + fuel rod) (explosion), Scorpion cannon + MG (explosion) |
| `explosion_small` | Plasma cannon (unlisted, in every map) | - |
| `plasma_fast/anti_flood` | Sentinel beam (AI Sentinel) | - |
| `plasma_slow` | Plasma lancer (test, 1 map) | - |
| `plasma_vehicle` | Ghost gun, Banshee gun (bolts + fuel rod), Shade turret, Dropship gun | Plasma cannon (unlisted, in every map) (impact) |
| `melee` | Sprint (invisible sprint weapon) | Plasma cannon (unlisted, in every map) (melee), Plasma lancer (test, 1 map) (melee) |

### Halo 1 per-weapon notable material modifiers (non-1.0, main hit)

| Weapon | jpt! | Category enum | Damage | Notable modifiers |
|---|---|---|---|---|
| Assault Rifle (impact) | `bullet` | Bullet | 10/10 | Elite Energy Shield 0.7, Jackal Energy Shield 0, Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 0.65, Flood Carrier Form 0.65, Metal (Thick) 0.25, Engineer 0.6 |
| Pistol (impact) | `bullet` | Bullet | 25/25 | Elite Energy Shield 0.8, Cyborg 1.5, Jackal Energy Shield 0, Hunter Armor 0.2, Flood Combat Form 1.5, Flood Carrier Form 1.5, Sentinel 0.2, Metal (Thick) 0.25, Engineer 2 |
| Plasma Pistol (impact) | `bolt` | Plasma | 10/16 | Elite Energy Shield 2, Cyborg Energy Shield 0.6, Cyborg 0.6, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |
| Plasma Pistol (charged_impact) | `charged bolt` | Plasma | 70/70 | Elite Energy Shield 1.5, Cyborg 0.6, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 4, Armored Human 0.2, Human 0.2, Metal (Thick) 0.25 |
| Plasma Rifle (impact) | `bolt` | Plasma | 10/12 | Elite Energy Shield 2, Cyborg Energy Shield 2, Cyborg 0.5, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |
| Needler (supercombine) | `explosion` | Grenade | 40/60 | Elite Energy Shield 4, Jackal Energy Shield 1.5, Hunter Armor 0.2, Hunter Skin 0.5, Flood Combat Form 2, Flood Carrier Form 4, Sentinel 4 |
| Needler (attached) | `detonation damage` | Bullet | 10/10 | Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 1.2, Flood Carrier Form 1.2, Sentinel 0, Metal (Thick) 0.25, Engineer 0.6 |
| Sniper Rifle (impact) | `sniper bullet` | Sniper | 101/101 | Elite Energy Shield 2, Jackal Energy Shield 0, Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 0.05, Flood Carrier Form 0.05, Sentinel 0.2, Metal (Thick) 0, Engineer 0.2 |
| Rocket Launcher (explosion) | `explosion` | High Explosive | 80/300 | Flood Combat Form 2, Flood Carrier Form 4, Sentinel 0.4 |
| Shotgun (impact) | `pellet` | Shotgun | 8/18 | Cyborg Energy Shield 0.5, Jackal Energy Shield 0, Hunter Armor 0.2, Flood Combat Form 1.5, Flood Carrier Form 1.75, Sentinel 0.5, Metal (Thick) 0.25 |
| Flak Cannon (Fuel Rod Gun) (explosion) | `explosion` | High Explosive | 40/75 | Hunter Armor 0, Hunter Skin 0, Flood Combat Form 2, Flood Carrier Form 4 |
| Flak Cannon (Fuel Rod Gun) (explosion) | `grunt explosion` | High Explosive | 40/75 | Hunter Armor 0, Hunter Skin 0, Flood Combat Form 2, Flood Carrier Form 4 |
| Flamethrower (explosion) | `explosion` | Flame | 10/12 | Elite Energy Shield 0.2, Jackal Energy Shield 0.1, Hunter Armor 0.5, Sentinel 0.5, Metal (Thick) 0.3 |
| Flamethrower (impact) | `impact damage` | Flame | 18/20 | Elite Energy Shield 0.5, Jackal Energy Shield 0.5, Hunter Armor 0.5, Sentinel 0.5, Metal (Thick) 0.3 |
| Energy Blade (port) (impact) | `lunge strike` | Plasma | 151/151 | Sentinel 2 |
| Sentinel Beam (port) (impact) | `beam` | Plasma | 4.64/4.64 | Elite Energy Shield 2, Cyborg Energy Shield 2, Cyborg 0.5, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |
| SAW (port) (impact) | `bullet` | Bullet | 7.5/7.5 | Elite Energy Shield 0.7, Jackal Energy Shield 0, Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 0.65, Flood Carrier Form 0.65, Metal (Thick) 0.25, Engineer 0.6 |
| SMG (port) (impact) | `bullet` | Bullet | 5/5 | Elite Energy Shield 0.7, Jackal Energy Shield 0, Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 0.65, Flood Carrier Form 0.65, Metal (Thick) 0.25, Engineer 0.6 |
| Battle Rifle (port) (impact) | `bullet` | Bullet | 6/6 | Cyborg 1.5, Jackal Energy Shield 0, Hunter Armor 0.2, Flood Combat Form 1.5, Flood Carrier Form 1.5, Sentinel 0.2, Metal (Thick) 0.25, Engineer 2 |
| Frag Grenade (explosion) | `explosion` | Grenade | 80/120 | Hunter Armor 0.25, Hunter Skin 0.5, Flood Combat Form 2, Flood Carrier Form 4, Sentinel 0.4 |
| Plasma Grenade (explosion) | `explosion` | Grenade | 80/120 | Elite Energy Shield 4, Jackal Energy Shield 1.5, Hunter Armor 0.25, Hunter Skin 0.5, Flood Combat Form 2, Flood Carrier Form 4, Sentinel 4 |
| Plasma Grenade (attached) | `attached` | Grenade | 80/120 | Elite Energy Shield 4, Hunter Armor 0.2, Sentinel 4, Metal (Thick) 0 |
| Hunter fuel rod cannon (explosion) | `explosion` | High Explosive | 40/75 | Hunter Armor 0, Hunter Skin 0, Flood Combat Form 2, Flood Carrier Form 4 |
| Sentinel beam (AI Sentinel) (impact) | `beam` | Bullet | 1/1 | Sentinel 0, Metal (Thick) 0.25 |
| Ghost gun (impact) | `ghost bolt` | Mounted Weapon | 10/10 | Elite Energy Shield 2, Cyborg Energy Shield 2, Cyborg 0.5, Jackal Energy Shield 2, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |
| Banshee gun (bolts + fuel rod) (impact) | `banshee bolt` | Mounted Weapon | 10/10 | Elite Energy Shield 2, Cyborg Energy Shield 2, Cyborg 0.5, Jackal Energy Shield 2, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |
| Banshee gun (bolts + fuel rod) (explosion) | `fuel rod explosion` | High Explosive | 40/75 | Elite Energy Shield 2, Elite 2, Grunt 2, Jackal 2, Jackal Energy Shield 0, Hunter Skin 2, Flood Combat Form 2, Flood Carrier Form 4, Sentinel 2, Engineer 2 |
| Shade turret (impact) | `bolt` | Mounted Weapon | 8/12 | Elite Energy Shield 3, Cyborg Energy Shield 1.5, Cyborg 1.5, Elite 0.7, Grunt 0.7, Jackal 0.7, Jackal Energy Shield 3, Hunter Armor 0.4, Hunter Skin 0.4, Sentinel 4, Metal (Thick) 0.25 |
| Dropship gun (impact) | `bolt` | Mounted Weapon | 8/12 | Elite Energy Shield 3, Cyborg Energy Shield 1.5, Cyborg 1.5, Elite 0.7, Grunt 0.7, Jackal 0.7, Jackal Energy Shield 3, Hunter Armor 0.4, Hunter Skin 0.4, Sentinel 4, Metal (Thick) 0.25 |
| Wraith mortar (explosion) | `explosion` | Mounted Weapon | 50/90 | Hunter Armor 0.2, Flood Combat Form 2, Flood Carrier Form 4 |
| Warthog chaingun (impact) | `bullet` | Mounted Weapon | 16/16 | Jackal Energy Shield 0, Hunter Armor 0.5, Hunter Skin 0.5, Metal (Thick) 0.25 |
| Scorpion cannon + MG (explosion) | `shell explosion` | Mounted Weapon | 80/351 | Flood Combat Form 2, Flood Carrier Form 4, Sentinel 0.4 |
| Scorpion cannon + MG (impact) | `bullet` | Mounted Weapon | 10/10 | Elite Energy Shield 0.7, Jackal Energy Shield 0.7, Hunter Armor 0.5, Hunter Skin 0.5, Flood Combat Form 0.65, Flood Carrier Form 0.65, Metal (Thick) 0.25, Engineer 0.6 |
| Plasma cannon (unlisted, in every map) (explosion) | `plasma_cannon_explosion` | High Explosive | 60/85 | Flood Combat Form 2, Flood Carrier Form 4 |
| Plasma cannon (unlisted, in every map) (impact) | `impact damage` | Flame | 20/28 | Elite Energy Shield 0.5, Jackal Energy Shield 0.5, Hunter Armor 0.5, Sentinel 0.5, Metal (Thick) 0.3 |
| Gravity rifle (cut MP weapon) (explosion) | `explosion` | Flame | 10/12 | Elite Energy Shield 0.2, Jackal Energy Shield 0.1, Hunter Armor 0.5, Sentinel 0.5, Metal (Thick) 0.3 |
| Gravity rifle (cut MP weapon) (impact) | `impact damage` | Flame | 18/20 | Elite Energy Shield 0.5, Jackal Energy Shield 0.5, Hunter Armor 0.5, Sentinel 0.5, Metal (Thick) 0.3 |
| Plasma lancer (test, 1 map) (impact) | `bolt` | Plasma | 10/12 | Elite Energy Shield 2, Cyborg Energy Shield 2, Cyborg 0.5, Hunter Armor 0.5, Hunter Skin 0.5, Sentinel 2, Metal (Thick) 0.25 |

Player melee (`weapons\*\melee`, Melee category) is the same profile for every weapon: Flood/Sentinel 0.2, Cyborg 1.4 (see tilt_explained.md).

### Armour: class -> armour -> users

| Class | Armour | Users |
|---|---|---|
| Shields | `Cyborg Energy Shield (jpt! column "Cyborg Energy Shield")` | cyborg, cyborg_cinematic, cyborg_unarmed |
| Shields | `Elite Energy Shield (jpt! column "Elite Energy Shield")` | elite, elite special, elite special cinematic, sentinel |
| Shields (Jackal hand shield) | `Jackal Energy Shield (jpt! column "Jackal Energy Shield")` | jackal, jackal major |
| Armour | `Cyborg Armor (jpt! column "Cyborg")` | cyborg, cyborg_cinematic, cyborg_unarmed |
| Armour | `Elite (jpt! column "Elite")` | elite, elite special, elite special cinematic |
| Armour | `Human Armor (jpt! column "Armored Human")` | captain, captain_fatigues, captain_fatigues_unarmed, captain_ingame, marine, marine unarmed, marine_armored, marine_armored_sniper, marine_armored_unarmed, marine_plasma_rifle, marine_suicidal, prone_1, sitting_1, sitting_2 |
| Flesh | `Engineer Skin (jpt! column "Engineer")` | engineer |
| Flesh | `Grunt (jpt! column "Grunt")` | grunt, grunt specops |
| Flesh | `Human Skin (jpt! column "Human")` | captain, captain_fatigues, captain_fatigues_unarmed, captain_ingame, crewman, marine, marine unarmed, marine_armored, marine_armored_sniper, marine_armored_unarmed, marine_plasma_rifle, marine_suicidal, prone_1, sitting_1, sitting_2 |
| Flesh | `Jackal (jpt! column "Jackal")` | jackal, jackal major |
| Flood | `Flood Carrier Form (jpt! column "Flood Carrier Form")` | floodcarrier, floodcombat elite, floodcombat_human |
| Flood | `Flood Combat Form (jpt! column "Flood Combat Form")` | flood_captain, flood_infection, flood_infection nopop, floodcarrier, floodcombat elite, floodcombat_human |
| Hunter plates | `Hunter Armor (jpt! column "Hunter Armor")` | hunter |
| Hunter plates | `Hunter Shield (jpt! column "Hunter Shield")` | hunter |
| Hunter plates | `Hunter Skin (jpt! column "Hunter Skin")` | hunter |
| Vehicles | `Glass (jpt! column "Glass")` | cryotube, lifepod, lifepod_docked, lifepod_entry, warthog |
| Vehicles | `Metal (Hollow) (jpt! column "Metal (Hollow)")` | b30_falling_box, c gun turret, cryotube, lifepod_entry |
| Vehicles | `Metal (Thick) (jpt! column "Metal (Thick)")` | banshee, banshee_cinematic, banshee_oldplayback, c_dropship, ghost, pelican, scorpion, warthog, wraith |
| Vehicles | `Metal (Thin) (jpt! column "Metal (Thin)")` | cd_gun, chair pilot, chair pod, engineer, lifepod, lifepod_atmosphere_entry, lifepod_docked |
| Vehicles | `Rubber (jpt! column "Rubber")` | ghost, scorpion, warthog |
| other (Sentinel) | `Sentinel (jpt! column "Sentinel")` | sentinel |
| other (Monitor) | `Monitor (jpt! column "Monitor")` | monitor, monitor_no_light |
| other | `Dirt (jpt! column "Dirt")` | invisible damage detector, pelican |
| other | `Force Field (jpt! column "Force Field")` | cortana, halo_enhanced |

### Player armour

- Shield: `Cyborg Energy Shield`; body: `Cyborg Armor` (jpt! column "Cyborg"). Both columns are the player's own in every jpt!, so an H1 card can scale them without touching any enemy.

### Surprises and traps

- No damage groups: the "category" here is the Halo 2 group of the same weapon (analogy); the jpt! enum `Category` (0x1C6) is recorded as `h1_category` and is NOT the same thing (energy sword = Plasma, needler attached detonation = Bullet, sentinel beam = Plasma, AI Sentinel beam = Bullet, plasma cannon impact = Flame).
- The Plasma Pistol's charged shot is `weapons\plasma rifle\charged bolt` (lives in the plasma rifle folder). Mapped to `emp` by analogy with H2/H3, but in Halo 1 it is just a 70-damage plasma hit with its own per-material floats.
- Needler impact damage is ZERO; needles hurt only through the attached detonation (`detonation damage`, Bullet category) and the supercombine `explosion` (Grenade category).
- Shared jpt!s player <-> AI: the Fuel Rod explosion is also the Hunter cannon's (`hunter fuel rod`) and the Plasma Rifle bolt the plasma lancer's; AI-only: the Shade turret bolt (`c gun turret\bolt`) is also the dropship gun's. The Banshee fuel-rod bomb has its own copy (`vehicles\banshee\fuel rod explosion`, 2x vs flesh and Elite).
- The cut gravity rifle reuses both flamethrower jpt!s (impact + explosion). The invisible Sprint weapon's melee is `weapons\flag\melee` (80 damage).
- Elites and Sentinels share the `Elite Energy Shield` column (Sentinel coll shield = Elite Energy Shield, 80 vitality), so an "Effective vs Shields" card that scales that column also hits Sentinels. The player's two columns (Cyborg Energy Shield / Cyborg) are used by the player bipeds only.
- The SAW port bullet is mapped to bullet_vehicle because that is what the Halo 2 SAW port uses; the Halo 3/ODST SAW uses bullet_slow -- the ports disagree.
- Non-melee jpt!s shared by a player weapon and an AI/vehicle weapon: `explosion` (Flamethrower, Gravity rifle (cut MP weapon)); `impact damage` (Flamethrower, Gravity rifle (cut MP weapon)); `explosion` (Flak Cannon (Fuel Rod Gun), Hunter fuel rod cannon); `bolt` (Plasma Rifle, Plasma lancer (test, 1 map))

## Halo 2

### Player weapons: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `(no data: empty stub)` | Gravity Hammer | - |
| `bullet_fast` | Battle Rifle | Brute Shot (impact) |
| `bullet_fast/sniper` | Sniper Rifle | - |
| `bullet_slow` | Pistol (Magnum), SMG | - |
| `bullet_slow/kill_flood` | Shotgun | - |
| `bullet_vehicle` | SAW (port) | - |
| `cutting` | Energy Blade | Brute Shot (melee) |
| `emp` | - | Plasma Pistol (charged_impact) |
| `explosion_attached` | - | Needler (supercombine_attached), Plasma Grenade (attached) |
| `explosion_large` | Rocket Launcher, Flak Cannon (Fuel Rod Gun), Scarab gun (handheld, 07a cheat weapon) | - |
| `explosion_largw` | - | Flak Cannon (Fuel Rod Gun) (explosion) |
| `explosion_small` | Brute Shot, Frag Grenade, Plasma Grenade | Needler (supercombine) |
| `plasma_fast` | Covenant Carbine | - |
| `plasma_fast/anti_flood` | Sentinel Beam, Sentinel Eliminator Beam | - |
| `plasma_fast/sniper` | Beam Rifle | - |
| `plasma_slow` | Plasma Pistol, Plasma Rifle, Brute Plasma Rifle, Needler | - |
| `plasma_slow/anti_flood` | Sentinel Welder (Sentinel Beam card) | - |
| `plasma_vehicle` | - | Scarab gun (handheld, 07a cheat weapon) (impact) |
| `melee` | - | 17 weapons' melee |

### AI weapons and vehicle guns: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_vehicle` | Warthog chaingun, Scorpion cannon + MG, Human AP turret, Pelican chin gun, GPMG (cut weapon, SAW port donor) | Warthog gauss (impact) |
| `explosion_large` | Sentinel Enforcer rocket, Wraith mortar, Pelican rocket pod, Scarab main gun, Covenant gun tower mortar | Banshee gun (bolts + bomb) (explosion), Scorpion cannon + MG (explosion) |
| `explosion_large/anti_flood` | - | Sentinel Enforcer rocket (explosion) |
| `explosion_small` | Warthog gauss | - |
| `plasma_fast/anti_flood` | Sentinel Enforcer beam | - |
| `plasma_slow/anti_flood` | Sentinel Enforcer needler | - |
| `plasma_vehicle` | Hunter assault cannon, Prophet gravity cannon (Regret throne), Ghost gun, Banshee gun (bolts + bomb), Wraith gunner turret, Shade turret (plasma_cannon), Spectre turret, Phantom turret, Covenant AP turret (big needler), Creep turret, Scarab AA gun | Scarab main gun (impact) |
| `melee` | - | GPMG (cut weapon, SAW port donor) (melee), Scarab main gun (melee) |

### Armour: class -> armour -> users

| Class | Armour | Users |
|---|---|---|
| Shields | `energy_shield_invincible` | brute_tartarus |
| Shields | `energy_shield_thick` | jackal |
| Shields | `energy_shield_thin` | c_turret_ap, dervish, elite, elite_ranger, floodcombat_elite, heretic, heretic_leader, heretic_leader_hologram, heretic_leader_hologram_cinematic, hunter, masterchief, prophet_regret, sentinel_aggressor, sentinel_aggressor_halo1 |
| Armour | `hard_metal_thin` | dervish, elite, elite_ranger, h_turret_mp, heretic, heretic_leader, marine, marine_female, marine_massive, masterchief, plasma_cannon, prophet_regret, sentinel_aggressor, sentinel_aggressor_halo1, sentinel_enforcer |
| Flesh | `soft_inorganic` | grunt, heretic_grunt |
| Flesh | `soft_organic` | bugger, crewman, grunt, heretic_grunt, hunter, jackal, lord_hood, marine, marine_female, marine_massive, miranda, prophet_mercy, prophet_regret, prophet_truth, regret_holo |
| Flesh (Hunter flesh) | `soft_organic_flesh_hunter *(specific, on: soft_organic_flesh_hunter)*` | hunter |
| Brute hide | `tough_organic` | brute |
| Brute hide | `tough_organic_flesh_brute_tartarus` | brute_tartarus |
| Flood | `hard_floodflesh` | flood_juggernaut |
| Flood | `tough_floodflesh` | flood_infection, flood_juggernaut, floodcarrier, floodcombat_elite, floodcombat_human |
| Vehicles | `brittle_elec` | banshee, creep, ghost, phantom, sentinel_constructor, sentinel_emitter, wraith |
| Vehicles | `brittle_glass` | pelican, warthog |
| Vehicles | `brittle_mech` | minigun, wraith |
| Vehicles | `hard_metal_solid` | cannon, cannon_mp, hunter, insertion_pod, pelican, phantom, scorpion, sentinel_emitter, wraith |
| Vehicles | `hard_metal_thick` | banshee, c_turret_ap, chaingun, chin_gun, cov_guntower_turret, creep, gauss, ghost, gravity_throne, gravity_throne_no_flare, h_turret_ap, minigun, mortar, mortar_mp, plasma_turret, scarab_rear_gun, scarab_side_gun, scarab_upper_gun, sentinel_enforcer, side_gun, spectre, warthog, wraith |
| Vehicles | `tough_inorganic` | warthog |
| other (Sentinel) | `sentinel *(specific, on: hard_metal_thick_for_sentinel, hard_metal_thick_for_sentinel_aggressor, hard_metal_thin_for_sentinel, hard_metal_thin_for_sentinel_aggressor)*` | sentinel_aggressor, sentinel_aggressor_halo1 |
| other (Sentinel) | `sentinel_enforcer *(specific, on: hard_metal_thin_for_sentinel_enforcer)*` | sentinel_enforcer |
| other | `energy` | plug_absorber |
| other | `energy_holo` | cortana, heretic_leader_hologram, heretic_leader_hologram_cinematic |

Rows with no biped/vehicle user found: `brittle`, `brittle_explosive`, `hard`, `hard_metal_solid_for_cable`, `hard_terrain`, `liquid`, `liquid_thick`, `liquid_thin`, `material`, `soft`, `soft_terrain`, `tough`, `tough_terrain`.

### Player armour

- Shield: `energy_shield_thin_hum_masterchief (Arbiter: energy_shield_thin_cov_elite)` -> general `energy_shield_thin`, specific `None`
- Body: `hard_metal_thin_hum_masterchief (Arbiter: hard_metal_thin_cov_elite)` -> general `hard_metal_thin`, specific `None`
- Shared: Elites (shield + armour + flesh), Sentinels (shield), Hunters/Prophet (shield row), Marines (armour row)

### Table [0] multipliers for the categories above (general row / specific row; - = no row = 1)

| Category | energy_shield_thin | energy_shield_thick | hard_metal_thin | soft_organic | soft_inorganic | tough_organic | tough_floodflesh | soft_organic_flesh_hunter | hard_metal_thick | hard_metal_solid | sentinel |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bullet_fast` | 1 | 0 | 1 | 1 | 1 | 1 | 0.5 | 2 | 0.5 | 0 | 1 |
| `bullet_fast/sniper` | 1 / 2 | 0 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.5 / 1 | 2 / 4 | 0.5 / 1 | 0 / 1 | 1 / 1 |
| `bullet_slow` | 1 | 0 | 1 | 1 | 1 | 0.5 | 1.25 | 2 | 0.25 | 0 | 1 |
| `bullet_slow/kill_flood` | 1 / 1 | 0 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.5 / 1 | 1.25 / 2 | 2 / 1 | 0.25 / 1 | 0 / 1 | 1 / 1 |
| `bullet_vehicle` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.5 | 1 | 1 | 0.5 | 1 |
| `cutting` | 1 | 0 | 1 | 2 | 2 | 1 | 4 | 1 | 0.25 | 0 | 1 |
| `emp` | 500 | 500 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 500 |
| `explosion_attached` | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 |
| `explosion_large` | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `explosion_large/anti_flood` | 0.5 / 1 | 0.5 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 6 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| `explosion_largw` | - | - | - | - | - | - | - | - | - | - | - |
| `explosion_small` | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0.25 | 1 |
| `melee` | 1 | 0 | 1 | 1 | 1 | 1 | 0.25 | 1 | 0.25 | 0 | 1 |
| `plasma_fast` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.5 | 2 | 0.25 | 0 | 2 |
| `plasma_fast/anti_flood` | 1 / 1 | 0.5 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.5 / 6 | 2 / 1 | 0.25 / 1 | 0 / 1 | 2 / 1 |
| `plasma_fast/sniper` | 1 / 2 | 0.5 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.5 / 1 | 2 / 4 | 0.25 / 1 | 0 / 1 | 2 / 1 |
| `plasma_slow` | 1.5 | 1 | 0.35 | 1 | 1 | 0.5 | 0.5 | 2 | 0.1 | 0 | 4 |
| `plasma_slow/anti_flood` | 1.5 / 1 | 1 / 1 | 0.35 / 1 | 1 / 1 | 1 / 1 | 0.5 / 1 | 0.5 / 6 | 2 / 1 | 0.1 / 1 | 0 / 1 | 4 / 1 |
| `plasma_vehicle` | 1 | 1 | 1 | 1 | 1 | 1 | 0.5 | 1 | 1 | 0.5 | 2 |

### Surprises and traps

- Flak Cannon (Fuel Rod) explosion `flak_explosion` names the general group **`explosion_largw`** (typo, resolved directly from the H2 string table). No damage-table row has that name, so the fuel-rod splash ignores armour (every multiplier = 1, incl. shields where explosion_large is 0.5). Its impact `flak_impact` is a correct explosion_large.
- Brute Shot melee is `slice_melee` = **cutting** (the bayonet), not melee.
- The SAW port (and the cut gpmg donor) fire bullet_vehicle: the SAW bullet shares the turret/Pelican chin-gun row (gpmg literally uses h_turret_ap_bullet).
- Sniper Rifle: its Lunge Melee slot points at `smash_melee_response` (group none) -- no lunge damage.
- Hunter assault cannon, Prophet gravity cannon and both Scarab guns impact as **plasma_vehicle** (the Hunter detonation `hunter_particle_cannon_shake` is no_damage). The handheld Scarab gun (cheat weapon) shares the Scarab jpt!s.
- Every Sentinel weapon carries the anti_flood specific (beam / eliminator plasma_fast, welder + enforcer needler plasma_slow, enforcer rocket explosion_large).
- Plasma Pistol `Charging Damage Effect` (plasma_pistol_overcharged) reads general/specific "0" -- a rumble/charge effect, excluded. The Gravity Hammer weap tag is an empty stub in the campaign maps (no references at all).
- Melee: strike/smash_melee are general `melee` (no specific); the damage table also has `sentinel_melee`, `kill_flood` and a `null` group.
- Non-melee jpt!s shared by a player weapon and an AI/vehicle weapon: `hunter_particle_cannon_component` (Hunter assault cannon, Prophet gravity cannon (Regret throne), Scarab AA gun, Scarab gun (handheld, 07a cheat weapon), Scarab main gun); `sentinel_eliminator_beam` (Sentinel Eliminator Beam, Sentinel Enforcer beam); `rocket_launcher_explosion` (Pelican rocket pod, Rocket Launcher, Sentinel Enforcer rocket); `rocket_launcher_impact` (Rocket Launcher, Sentinel Enforcer rocket); `scarab_main_gun_pulse` (Scarab gun (handheld, 07a cheat weapon), Scarab main gun)

## Halo 3

### Player weapons: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_fast` | Battle Rifle, Machine Gun (turret) | - |
| `bullet_fast/sniper` | Sniper Rifle | - |
| `bullet_slow` | Assault Rifle, Pistol (Magnum), SMG, Spike Rifle, SAW (port) | Spike Grenade (claymore_grenade) (child_impact) |
| `bullet_slow/anti_flood` | Mauler | - |
| `bullet_slow/kill_flood` | Shotgun | - |
| `burning/anti_flood` | Flamethrower, Firebomb Grenade | - |
| `collision/anti_flood` | - | Gravity Hammer (melee_lunge) |
| `cutting/anti_flood` | Energy Blade | Brute Shot (melee), Missile Pod (melee), Sentinel Beam (melee) |
| `emp` | - | Plasma Pistol (charged_impact) |
| `explosion_attached` | - | Needler (supercombine_attached), Plasma Grenade (attached), Spike Grenade (claymore_grenade) (attached) |
| `explosion_large` | Rocket Launcher, Flak Cannon (Fuel Rod Gun), Missile Pod | Frag Grenade (boarding), Plasma Grenade (boarding), Spike Grenade (claymore_grenade) (boarding) |
| `explosion_small` | Brute Shot, Gravity Hammer, Frag Grenade, Plasma Grenade, Spike Grenade (claymore_grenade) | Needler (supercombine) |
| `laser` | Spartan Laser | - |
| `plasma_fast` | Covenant Carbine | - |
| `plasma_fast/anti_flood` | Sentinel Beam | - |
| `plasma_fast/sniper` | Beam Rifle | - |
| `plasma_slow` | Plasma Pistol, Plasma Rifle, Needler | - |
| `plasma_vehicle` | Plasma Cannon (turret) | - |
| `melee/anti_flood` | - | 19 weapons' melee |

### AI weapons and vehicle guns: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_slow` | Flood pure-form ranged spikes | - |
| `bullet_vehicle` | Warthog chaingun, Scorpion gunner MG, Hornet (missiles + MG) | - |
| `explosion_large` | Scarab main gun, Scarab head turret, Wraith mortar, Scorpion cannon, Pelican rocket pod | Banshee gun (bolts + bomb) (explosion), Hornet (missiles + MG) (explosion) |
| `explosion_small` | Chopper gun, AA Wraith turret, Warthog gauss | - |
| `plasma_fast/anti_flood` | Auto-turret beam (equipment), Monitor beam (Guilty Spark) | - |
| `plasma_slow/anti_flood` | Sentinel welder (AI) | - |
| `plasma_vehicle` | Hunter assault cannon, Ghost gun, Banshee gun (bolts + bomb), Prowler gun (mauler vehicle), Wraith gunner turret, Shade turret, Phantom turret | - |
| `melee/anti_flood` | - | Scarab head turret (melee), Scarab main gun (melee) |

### Armour: class -> armour -> users

| Class | Armour | Users |
|---|---|---|
| Shields | `energy_shield_invincible_monitor` | monitor |
| Shields | `energy_shield_thick` | jackal, plasma_cannon |
| Shields | `energy_shield_thin` | brute, brute_chieftain, brute_jumppack, dervish, dervish_ai, elite, elite_sp, floodcombat_elite, masterchief, monitor, sentinel_aggressor |
| Shields | `energy_shield_thin_player *(specific, on: energy_shield_thin_cov_elite, energy_shield_thin_hum_masterchief)*` | dervish, dervish_ai, elite, elite_sp, floodcombat_elite, masterchief |
| Armour | `hard_metal_thin` | brute_chieftain, brute_jumppack, civilian_fem, dervish, dervish_ai, elite, elite_sp, hunter, marine, marine_female, marine_johnson_boss, masterchief, odst, sentinel_aggressor, worker |
| Armour | `hard_metal_thin_player *(specific, on: hard_metal_thin_cov_elite, hard_metal_thin_hum_masterchief)*` | dervish, dervish_ai, elite, elite_sp, masterchief |
| Flesh | `soft_inorganic` | grunt, mongoose, warthog |
| Flesh | `soft_organic` | bugger, civilian_fem, crewman, grunt, hunter, jackal, lord_hood, marine, marine_female, marine_johnson_boss, miranda, odst, worker |
| Flesh (Hunter flesh) | `soft_organic_flesh_hunter *(specific, on: soft_organic_flesh_hunter, soft_organic_flesh_scarab)*` | hunter |
| Brute hide | `tough_organic` | brute, brute_chieftain, brute_jumppack |
| Flood | `hard_floodflesh` | flood_tank |
| Flood | `soft_floodflesh` | flood_infection, flood_ranged, flood_tank, floodcombat_brute, floodcombat_human |
| Flood | `tough_floodflesh` | flood_ranged, flood_stalker, floodcarrier, floodcombat_brute, floodcombat_elite, floodcombat_human |
| Vehicles | `brittle_elec` | phantom |
| Vehicles | `brittle_glass` | mongoose, warthog |
| Vehicles | `hard_metal_solid` | cannon, hunter, pelican, phantom, scorpion, wraith |
| Vehicles | `hard_metal_thick` | anti_air, anti_infantry, banshee, banshee_ambient, brute_chopper, chaingun, chin_gun, chin_gun_friendly, gauss, ghost, gravity_throne_holo, hornet, machinegun_turret, mauler, mongoose, mortar, phantom, plasma_cannon, scorpion, shade, troop, warthog, wraith |
| Vehicles | `tough_inorganic` | mongoose, warthog |
| other (Sentinel) | `sentinel *(specific, on: hard_metal_thick_for_sentinel, hard_metal_thick_for_sentinel_aggressor, hard_metal_thin_for_sentinel, hard_metal_thin_for_sentinel_aggressor)*` | sentinel_aggressor |
| other | `energy_holo` | cortana, cortana_near_death |
| other | `infection *(specific, on: soft_floodflesh_infection, tough_floodflesh_infectionform)*` | flood_infection, floodcombat_elite |

Rows with no biped/vehicle user found: `brittle`, `brittle_explosive`, `brittle_flood`, `brittle_mech`, `energy`, `energy_shield_invincible`, `energy_shield_solid`, `energy_shield_solid_melee`, `hard`, `hard_metal_invulnerable`, `hard_terrain`, `liquid`, `liquid_thick`, `liquid_thin`, `material`, `soft`, `soft_terrain`, `tough`, `tough_terrain`.

### Player armour

- Shield: `energy_shield_thin_hum_masterchief` -> general `energy_shield_thin`, specific `energy_shield_thin_player`
- Body: `hard_metal_thin_hum_masterchief` -> general `hard_metal_thin`, specific `hard_metal_thin_player`
- Shared: The _player SPECIFIC rows are also on energy_shield_thin_cov_elite / hard_metal_thin_cov_elite, so Elites, the Arbiter and Flood-Elite shields use them too. Brutes use energy_shield_thin (energy_shield_thin_cov) WITHOUT the _player row.

### Table [0] multipliers for the categories above (general row / specific row; - = no row = 1)

| Category | energy_shield_thin | energy_shield_thick | hard_metal_thin | soft_organic | soft_inorganic | tough_organic | tough_floodflesh | soft_floodflesh | soft_organic_flesh_hunter | hard_metal_thick | hard_metal_solid | sentinel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `bullet_fast` | 1 | 0 | 1 | 1 | 1 | 1 | 0.25 | 2 | 2 | 0.5 | 0 | - |
| `bullet_fast/sniper` | 1 / - | 0 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / - | 2 / 0.5 | 2 / - | 0.5 / 0.5 | 0 / - | - / - |
| `bullet_slow` | 1 | 0 | 1 | 1 | 1 | 0.5 | 1 | 1 | 2 | 0.25 | 0 | - |
| `bullet_slow/anti_flood` | 1 / - | 0 / - | 1 / - | 1 / - | 1 / - | 0.5 / - | 1 / 2 | 1 / 2 | 2 / - | 0.25 / - | 0 / - | - / - |
| `bullet_slow/kill_flood` | 1 / - | 0 / - | 1 / - | 1 / - | 1 / - | 0.5 / - | 1 / - | 1 / - | 2 / - | 0.25 / - | 0 / - | - / - |
| `bullet_vehicle` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.5 | 1 | - | 1 | 0.5 | - |
| `burning/anti_flood` | 2 / - | 1 / - | 1 / - | 2 / - | 1 / - | 2 / - | 2 / 2 | 2 / 2 | - / - | 1 / - | 0 / - | - / - |
| `collision/anti_flood` | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / 2 | 2 / 2 | - / - | 0.75 / - | 0.5 / - | - / - |
| `cutting/anti_flood` | 1 / - | 1 / - | 1 / - | 2 / - | 2 / - | 1 / - | 2 / 2 | 2 / 2 | - / - | 0.25 / - | 0 / - | - / - |
| `emp` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | - | 0.001 | 0.001 | - |
| `explosion_attached` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | - | 1 | 0.25 | - |
| `explosion_large` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 2 | - | 1 | 1 | - |
| `explosion_small` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | - | 1 | 0.25 | - |
| `laser` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 2 | - | 1 | 0.5 | - |
| `melee/anti_flood` | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 2 / 2 | 2 / 2 | - / - | 0.25 / - | 0 / - | - / - |
| `plasma_fast` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.25 | 2 | 2 | 0.25 | 0 | 2 |
| `plasma_fast/anti_flood` | 1 / - | 0.5 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / 2 | 2 / 2 | 2 / - | 0.25 / - | 0 / - | 2 / - |
| `plasma_fast/sniper` | 1 / - | 0.5 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / - | 2 / 0.5 | 2 / - | 0.25 / 0.5 | 0 / - | 2 / - |
| `plasma_slow` | 1.5 | 1 | 0.35 | 1 | 1 | 0.5 | 1 | 1 | 2 | 0.1 | 0 | 4 |
| `plasma_slow/anti_flood` | 1.5 / - | 1 / - | 0.35 / - | 1 / - | 1 / - | 0.5 / - | 1 / 2 | 1 / 2 | 2 / - | 0.1 / - | 0 / - | 4 / - |
| `plasma_vehicle` | 1 | 1 | 1 | 1 | 1 | 1 | 0.5 | 1 | - | 0.5 | 0.5 | 2 |

### Surprises and traps

- Shotgun specific **`kill_flood`** has NO row in the Halo 3 table (H2 had one) -- the specific is dead, the shotgun is plain bullet_slow.
- Every player melee (strike/smash/cut/dash/slice/crush) carries the **anti_flood** specific; flamethrower and firebomb (burning) too, so "Effective vs Flood" for melee/fire is already a specific row.
- Gravity Hammer: its weap tagrefs only reach smash_melee (melee) and crush_melee (**collision**/anti_flood, lunge); the AoE that matters, `gravity_hammer_explosion` = explosion_small, is fired by the swing effect and is reached by no weap/proj tagref (added by hand).
- Brute Shot, Missile Pod and Sentinel Beam melee = `slice_melee` = **cutting**/anti_flood.
- Spartan Laser is the only `laser` weapon; its beam is a DETONATION (not impact) damage.
- Mauler (excavator) shard carries anti_flood; Spike Rifle does not.
- Spike grenade (claymore_grenade): the blast is explosion_small, the spikes are child projectiles that impact as bullet_slow.
- Grenade BOARDING explosions are explosion_large (H2: explosion_small).
- Machine-gun turret = bullet_fast (not bullet_vehicle); the Warthog chaingun and Scorpion/Hornet MGs are bullet_vehicle.
- Hunter cannon = plasma_vehicle (as in H2); Flood pure-form spikes = bullet_slow; the AI auto-turret beam and Guilty Spark's beam share the Sentinel Beam row (plasma_fast/anti_flood).
- Infection-form pop/shield-zap jpt!s name `small_explosion` (not explosion_small) -- no table row, multiplier 1.
- Wraith mortar shockwave jpt! names static id 0x146, which reads "0" -- no table row.
- The `_player` rows: on the Elite materials too (Elites/Arbiter use them), and in table [0] only `no_damage` has one -- the compensating rows (bullets x4 vs energy_shield_thin_player, plasma x3 vs hard_metal_thin_player) are in table [1], the native Tilt table only. Outside Tilt the player = Elite in every damage group.
- Hunter plates have no row of their own in Halo 2/3: they are hard_metal_solid (shared with Scorpion, Wraith, Pelican, Phantom); an "Effective vs Hunter plates" card would hit those vehicles too. Hunter flesh has the specific `soft_organic_flesh_hunter` row.
- Non-melee jpt!s shared by a player weapon and an AI/vehicle weapon: `sentinel_gun_impact` (Monitor beam (Guilty Spark), Sentinel Beam)

## Halo 3: ODST

### Player weapons: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_fast` | Machine Gun (turret) | - |
| `bullet_fast/sniper` | Sniper Rifle | - |
| `bullet_fast_h3` | Battle Rifle | - |
| `bullet_slow` | Assault Rifle, Pistol (Magnum), SMG, Spike Rifle, SAW (port), Automag (ODST pistol), Silenced SMG (ODST) | Spike Grenade (claymore_grenade) (child_impact) |
| `bullet_slow/anti_flood` | Mauler | - |
| `bullet_slow/kill_flood` | Shotgun | - |
| `burning/anti_flood` | Flamethrower, Firebomb Grenade | - |
| `collision/anti_flood` | - | Gravity Hammer (melee_lunge) |
| `cutting/anti_flood` | Energy Blade | Brute Shot (melee), Missile Pod (melee), Sentinel Beam (melee) |
| `emp` | - | Plasma Pistol (charged_impact) |
| `explosion_attached` | - | Needler (supercombine_attached), Plasma Grenade (attached), Spike Grenade (claymore_grenade) (attached) |
| `explosion_large` | Rocket Launcher, Flak Cannon (Fuel Rod Gun), Missile Pod | Frag Grenade (boarding), Plasma Grenade (boarding), Spike Grenade (claymore_grenade) (boarding) |
| `explosion_small` | Brute Shot, Gravity Hammer, Frag Grenade, Plasma Grenade, Spike Grenade (claymore_grenade) | Needler (supercombine) |
| `laser` | Spartan Laser | - |
| `plasma_fast` | Covenant Carbine | - |
| `plasma_fast/anti_flood` | Sentinel Beam | - |
| `plasma_fast/sniper` | Beam Rifle | - |
| `plasma_slow` | Plasma Pistol, Plasma Rifle, Needler, Brute Plasma Rifle (plasma_rifle_red) | - |
| `plasma_vehicle` | Plasma Cannon (turret) | - |
| `melee/anti_flood` | - | 21 weapons' melee |

### AI weapons and vehicle guns: category -> weapons

| Category | Main hit of | Also used by (role) |
|---|---|---|
| `bullet_slow` | Flood pure-form ranged spikes | - |
| `bullet_vehicle` | Warthog chaingun, Scorpion gunner MG, Hornet (missiles + MG) | - |
| `explosion_large` | Scarab main gun, Scarab head turret, Wraith mortar, Scorpion cannon, Pelican rocket pod, Hunter fuel rod cannon (ODST) | Banshee gun (bolts + bomb) (explosion), Hornet (missiles + MG) (explosion) |
| `explosion_small` | Chopper gun, AA Wraith turret, Warthog gauss | - |
| `plasma_fast/anti_flood` | Auto-turret beam (equipment) | - |
| `plasma_vehicle` | Hunter assault cannon, Ghost gun, Banshee gun (bolts + bomb), Prowler gun (mauler vehicle), Wraith gunner turret, Shade turret, Phantom turret | - |
| `melee/anti_flood` | - | Scarab head turret (melee), Scarab main gun (melee) |

### Armour: class -> armour -> users

| Class | Armour | Users |
|---|---|---|
| Shields | `energy_shield_thick` | jackal, plasma_cannon |
| Shields | `energy_shield_thin` | brute, brute_chieftain, brute_jumppack, bugger, elite, elite_lite, engineer, engineer_cin, engineer_freeform, engineer_freeform_cin, floodcombat_brute, floodcombat_elite, monitor_editor, mp_odst_oni_op_player, mp_odst_recon, odst, odst_oni_op, odst_oni_op_player, odst_recon, olifaunt, sentinel_aggressor |
| Shields | `energy_shield_thin_player *(specific, on: energy_shield_thin_cov_elite, energy_shield_thin_hum_masterchief, energy_shield_thin_hum_recon)*` | elite, elite_lite, floodcombat_elite, mp_odst_oni_op_player, mp_odst_recon, odst, odst_oni_op, odst_oni_op_player, odst_recon |
| Armour | `hard_metal_thin` | brute_chieftain, brute_jumppack, elite, elite_lite, engineer, engineer_cin, engineer_freeform, engineer_recharge_station, hunter, hunter_flak, marine, marine_female, marine_lite, monitor_editor, odst_cine, sentinel_aggressor |
| Armour | `hard_metal_thin_player *(specific, on: hard_metal_thin_cov_elite, hard_metal_thin_hum_masterchief)*` | elite, elite_lite |
| Flesh | `soft_inorganic` | grunt, mongoose, mongoose_snow, warthog, warthog_gauss, warthog_snow |
| Flesh | `soft_organic` | bugger, engineer, engineer_cin, engineer_freeform, grunt, hunter, hunter_flak, jackal, marine, marine_female, marine_lite, odst, odst_cine |
| Flesh (Hunter flesh) | `soft_organic_flesh_hunter *(specific, on: soft_organic_flesh_hunter, soft_organic_flesh_scarab)*` | hunter, hunter_flak |
| Brute hide | `tough_organic` | brute, brute_chieftain, brute_jumppack, mp_odst_oni_op_player, mp_odst_recon, odst_oni_op, odst_oni_op_player, odst_recon |
| Flood | `hard_floodflesh` | flood_tank |
| Flood | `soft_floodflesh` | flood_ranged, flood_tank, floodcombat_brute, floodcombat_civilian, floodcombat_human, floodcombat_odst |
| Flood | `tough_floodflesh` | flood_ranged, flood_stalker, floodcarrier, floodcombat_brute, floodcombat_civilian, floodcombat_elite, floodcombat_human, floodcombat_odst |
| Hunter plates | `hunter *(specific, on: hard_metal_solid_cov_hunter, hard_metal_thick_cov_hunter)*` | hunter, hunter_flak |
| Vehicles | `brittle_elec` | phantom, phantom_dropship |
| Vehicles | `brittle_glass` | mongoose, mongoose_snow, warthog, warthog_gauss, warthog_snow |
| Vehicles | `hard_metal_solid` | cannon, cannon_snow, hunter, hunter_flak, pelican, pelican_police, phantom, phantom_dropship, scorpion, scorpion_snow, wraith, wraith_anti_air, wraith_park |
| Vehicles | `hard_metal_thick` | anti_air, anti_infantry, anti_infantry_snow, banshee, brute_chopper, chaingun, chaingun_snow, chin_gun, chin_gun_friendly, chin_gun_searchlight, gauss, gauss_snow, ghost, ghost_snow, hornet, hornet_lite, machinegun_turret, mauler, mongoose, mongoose_snow, mortar, phantom, phantom_dropship, plasma_cannon ... |
| Vehicles | `tough_inorganic` | mongoose, mongoose_snow, warthog, warthog_gauss, warthog_snow |
| other (Sentinel) | `sentinel *(specific, on: hard_metal_thick_for_sentinel, hard_metal_thick_for_sentinel_aggressor, hard_metal_thin_for_sentinel, hard_metal_thin_for_sentinel_aggressor)*` | sentinel_aggressor |
| other | `infection *(specific, on: soft_floodflesh_infection, tough_floodflesh_infectionform)*` | floodcombat_elite |

Rows with no biped/vehicle user found: `brittle`, `brittle_explosive`, `brittle_flood`, `brittle_mech`, `energy`, `energy_holo`, `energy_shield_invincible`, `energy_shield_invincible_monitor`, `energy_shield_solid`, `energy_shield_solid_melee`, `hard`, `hard_metal_invulnerable`, `hard_terrain`, `liquid`, `liquid_thick`, `liquid_thin`, `material`, `soft`, `soft_terrain`, `tough`, `tough_terrain`.

### Player armour

- Shield: `energy_shield_thin_hum_recon` -> general `energy_shield_thin`, specific `energy_shield_thin_player`
- Body: `tough_organic_flesh` -> general `tough_organic`, specific `None`
- Shared: Shield: Elites (energy_shield_thin_cov_elite carries the same _player specific). Body: the ODST player bipeds (odst_recon, odst_oni_op[_player], mp_odst_*) use tough_organic_flesh, i.e. the BRUTE HIDE row, not hard_metal_thin; hard_metal_thin_player is left to Elites only.

### Table [0] multipliers for the categories above (general row / specific row; - = no row = 1)

| Category | energy_shield_thin | energy_shield_thick | hard_metal_thin | soft_organic | soft_inorganic | tough_organic | tough_floodflesh | soft_floodflesh | soft_organic_flesh_hunter | hunter | hard_metal_thick | hard_metal_solid | sentinel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `bullet_fast` | 0.5 | 0 | 1 | 1 | 1 | 1 | 0.25 | 2 | 2 | - | 0.5 | 0 | - |
| `bullet_fast/sniper` | 0.5 / - | 0 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / - | 2 / 0.5 | 2 / - | - / - | 0.5 / 0.5 | 0 / - | - / - |
| `bullet_fast_h3` | 1 | 0 | 1 | 1 | 1 | 1 | 0.25 | 2 | 2 | - | 0.5 | 0 | - |
| `bullet_slow` | 0.5 | 0 | 1 | 1 | 1 | 0.5 | 1 | 1 | 2 | - | 0.25 | 0 | - |
| `bullet_slow/anti_flood` | 0.5 / - | 0 / - | 1 / - | 1 / - | 1 / - | 0.5 / - | 1 / 2 | 1 / 2 | 2 / - | - / - | 0.25 / - | 0 / - | - / - |
| `bullet_slow/kill_flood` | 0.5 / - | 0 / - | 1 / - | 1 / - | 1 / - | 0.5 / - | 1 / - | 1 / - | 2 / - | - / - | 0.25 / - | 0 / - | - / - |
| `bullet_vehicle` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.5 | 1 | - | - | 1 | 0.5 | - |
| `burning/anti_flood` | 2 / - | 1 / - | 1 / - | 2 / - | 1 / - | 2 / - | 2 / 2 | 2 / 2 | - / - | - / - | 1 / - | 0 / - | - / - |
| `collision/anti_flood` | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / 2 | 2 / 2 | - / - | - / - | 0.75 / - | 0.5 / - | - / - |
| `cutting/anti_flood` | 1 / - | 1 / - | 1 / - | 2 / - | 2 / - | 1 / - | 2 / 2 | 2 / 2 | - / - | - / - | 0.25 / - | 0 / - | - / - |
| `emp` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0.001 | 0.001 | - |
| `explosion_attached` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | - | - | 1 | 0.25 | - |
| `explosion_large` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 2 | - | - | 1 | 1 | - |
| `explosion_small` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 1 | - | - | 1 | 0.25 | - |
| `laser` | 0.5 | 0.5 | 0.5 | 1 | 1 | 1 | 1 | 2 | - | - | 1 | 0.5 | - |
| `melee/anti_flood` | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 1 / - | 2 / 2 | 2 / 2 | - / - | - / - | 0.25 / - | 0 / - | - / - |
| `plasma_fast` | 1 | 0.5 | 1 | 1 | 1 | 1 | 0.25 | 2 | 2 | - | 0.25 | 0 | 2 |
| `plasma_fast/anti_flood` | 1 / - | 0.5 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / 2 | 2 / 2 | 2 / - | - / - | 0.25 / - | 0 / - | 2 / - |
| `plasma_fast/sniper` | 1 / - | 0.5 / - | 1 / - | 1 / - | 1 / - | 1 / - | 0.25 / - | 2 / 0.5 | 2 / - | - / - | 0.25 / 0.5 | 0 / - | 2 / - |
| `plasma_slow` | 1.5 | 1 | 0.35 | 1 | 1 | 0.5 | 1 | 1 | 2 | - | 0.1 | 0 | 4 |
| `plasma_vehicle` | 0.75 | 1 | 1 | 1 | 1 | 1 | 0.5 | 1 | - | 0.1 | 0.5 | 0.5 | 2 |

### Surprises and traps

- Same tags as Halo 3 except: Battle Rifle uses its own group **`bullet_fast_h3`**; Automag/Silenced SMG are plain bullet_slow (the ODST harshness is the table: bullet_slow vs energy_shield_thin 0.5).
- The ODST player BODY is `tough_organic` (Brute hide), not hard_metal_thin -- an "Effective vs Brute hide" card would hit the player too.
- ODST gives Hunter plates a `hunter` specific armour (on hard_metal_solid_cov_hunter / hard_metal_thick_cov_hunter), but table [0] has only ONE `hunter` row: plasma_vehicle 0.1. `scarab` / `sentinel_enforcer` specifics exist on materials but have no row (H3 and ODST).
- The `_player` specific is on energy_shield_thin_hum_recon AND energy_shield_thin_cov_elite; table [0] has no _player row except no_damage.
- Hunter fuel-rod cannon variant (`hunter_flak_cannon\flak_cannon`) = explosion_large; the plasma one = plasma_vehicle.
- Shotgun kill_flood specific: no row (dead), as in Halo 3.
- TRAP: in ODST `resolve_stringid` also misreads STATIC ids on some maps -- `all`, `infection`, `sniper`, `none` came back as `datamine_uploading`, `top_medals`, `guide_can_not_view_hq_file_share_in_game`, `round_score`; corrected here.


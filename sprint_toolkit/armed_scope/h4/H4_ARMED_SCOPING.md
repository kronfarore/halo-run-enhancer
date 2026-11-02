# Halo 4 "Armed: <weapon>" scoping -- full notes (2026-11-02, read-only)

Sources: E:\HaloBaselines\halo4\maps (all 8 missions, opened with halo_patch.open_map, never saved);
kit ai\generic.character via ttk_common.flatten('H4EK', ...). Raw dumps: h4\data\census_*.json,
graph_*.json; views: view1.txt (census), view2.txt / s2b_*.txt (graphs, overlays, weapon flags,
cells), matrix.txt (weapon x species), agg.txt (palette / firing coverage), var.txt (Jackal model
variants, shipped cell weapons), last.txt (graph siblings, null generic rows, Spartan AI graph).

## 1. Units (spawn points + designer/templated cell counts), _ts_units on all 8 maps
| level | Grunt | Jackal | Elite | Knight | Crawler | Watcher | Marine | Spartan AI | protected (veh/script) |
|---|---|---|---|---|---|---|---|---|---|
| Dawn m10 | 133+48 | 45+4 | 38+26 | - | - | - | - | - | 56 of 293 |
| Requiem m020 | 98+65 | 37+22 | 42+5 | - | - | - | - | - | 140 of 309 |
| Forerunner m30 | 93 | 18 | 39 | 54 | 127+4 | 27+5 | - | - | 19 of 213 |
| Infinity m60 | 149 | 58+1 | 60 | 51 | 151 | 16 | 7 | 25 | 64 of 352 |
| Reclaimer m40 | 151+6 | 61+10 | 109 | 5+2 | 17+16 | - | 49 | 14 | 150 of 411 |
| Shutdown m70 | 71 | 30 | 42+4 | 46 | 76 | 27 | 22 | 17 | 50 of 232 |
| Composer m80 | 99+43 | 55+30 | 107+35 | - | - | - | 43+11 | - | 102 of 447 |
| Midnight m90 | - | - | - | 9+41 | 1+90 | 0+15 | - | - | 0 of 48 |
Plus "inherit" spawn points (char -1, take the cell's): 1..264 per map (Midnight 264).
- Spawn point: char +0x2E, weapon +0x30, secondary +0x32, actor variant +0x40 -- index into the scnr
  Weapon Palette (0x1BC/0x10). -1 = default (char General Properties Initial Primary, else bipd
  Weapons block). Writing a spawn point needs no growth.
- Cell Initial Weapon element 0x8: Difficulty Flags u16 +0x0, Weapon Type Index +0x4, Chance +0x6.
  Several elements = per-actor roll. Cells that name a character always carry >=1 weapon element
  (cells with no char are spawn-point containers).
- SHARED ARRAYS: Character Type / Initial Weapon arrays are shared by pointer (max users per array:
  Requiem 68/32, Midnight 46/25, Composer 32/17, Dawn 16/15). Memory's "H4 has no shared cell
  blocks" is wrong for these sub-arrays -> _ts_unshare_cells is required.
- TWINS: 0-53 squads per map have BOTH designer and templated cells; pointers never equal, bytes
  rarely equal. Composer's TEMPLATED weapon arrays are stale (Grunts: energy sword + shotgun, storm
  rifle/carbine; Jackals: shotgun/AR; all Difficulty Flags 0) while the DESIGNER twins carry the
  real loadout (plasma pistol 0xF / needler 0xC). Which twin the engine reads is UNKNOWN; write both.
- Slack: 1915-2374 zero runs >=4 KB per map, 8-10 MB total, max run 47-63 KB -> unsharing and
  graph growth fit easily (_h3_reserve H4 rule).

## 2. Weapons / residency
- Every pool weapon of halo.json Missions (26 cards) is IN the Weapon Palette of all 8 maps
  (palettes 31-41 entries; dz_enhancer lists == palette). Focus Rifle (only H4 port) is in the
  palette on m30 only.
- dz_enhancer is switched on in EVERY scenario zone set on all 8 maps (14/14 .. 30/30), and every
  palette weapon's whole pooled tag closure is resident in every zone set (0 gaps). Character
  residency still varies (Grunt 11/14 sets on Dawn, Knight 4/17 on Shutdown) -- irrelevant to the
  weapon, which is resident everywhere the unit can be.
- A weapon not in the palette cannot be indexed (no slot); adding a palette row is block growth AND
  the closure would be unresident (pool-bit writing crashes H4) -> skip, as H2 does.
- So, unlike Reach, residency is solved by the dz_enhancer rebuilds. Must re-check after any rebuild
  that drops dz_enhancer from a zone set.

## 3. Firing data (ai\generic Weapons Properties 0x204/0xCC, Firing Pattern 0x210/0x1C)
- Kit: 89 WP / 100 FP rows. In a map, rows whose weapon is absent are NULLED (ref -1) but keep their
  data (Reclaimer: 33 null WP rows, 44 null FP rows, 4 patterns each) -> a missing entry can be made
  by REPOINTING a null row (no growth).
- Live entry for every pool card on every map EXCEPT Sticky Detonator (storm_sticky_detonator_pve:
  no row in kit or any map) and the Focus Rifle port (no row; ai_firing_profiles.json has no
  'Halo 4' key).
- Species own rows: storm_jackal (beam, carbine, needler, pp; FP pp), storm_grunt_imperial/space/
  ultra (pp), storm_jackal_major (pp), *_m40 stimuli (needler, pp), bishop (pawnhead). Shipped
  Grunt Imperials carry needlers (no own row) -> per-weapon fallback to the parent is likely, not
  proven. Plugin: Engage "Default Combat/Firing Range" is used "if we don't know how to use our
  weapon" -> behaviour without a row = UNKNOWN (fires with defaults or not at all).

## 4. Animation (graphs identical on every map; sibling jmads storm_jackal18 / elite_ai13 /
knight17 / marine0,3,14 hold full Modes copies with 0-7 anims -- role UNKNOWN)
combat-mode lookup per pool weapon (type = own type, any = class 'any' type, NOTYPE = class there
but neither, NOCLS = class missing):
| weapon (class:name) | Grunt | Jackal | Elite | Knight | Crawler | Marine/Spartan |
|---|---|---|---|---|---|---|
| AR/BR/Beam/Carbine/Shotgun/Sniper/Suppressor (rifle) | type | any/type | any/type | any | NOTYPE (smg,ab only) | any/type |
| Storm Rifle ac, Concussion con, DMR, LightRifle frr, SAW lmg, Binary ab, Railgun rg, Scattershot spd | NOTYPE | any | any/type | any/type | NOTYPE (ab type) | any/type |
| pistols (Magnum hp, Boltshot fbp, Needler, PP, Sticky sd) | any/type | any | any/type | any | any | any/type |
| Flak fr, Incineration fri, Rocket rl, Laser sl (missile) | any/type | NOCLS | any/type | NOCLS (rl via Weapon List rl->rifle) | NOCLS | any/type |
| Energy Blade (sword, meleeOnly) | NOCLS | NOCLS | type | NOCLS | NOCLS | NOCLS |
| Gravity Hammer (hammer, meleeOnly) | NOCLS | NOCLS | any (1 action, 4 overlays: hollow) | NOCLS | NOCLS | NOCLS |
Other modes: Grunt rifle exists ONLY in combat (crouch/flee/patrol/asleep/berserk have no rifle;
flee = any+pistol, Retreat Backup Weapon = plasma pistol -> H2 flee-drop risk). Jackal flee =
dual js + pistol only (Backup pp). Elite has no flee mode. Knight: combat/suppress only.
Watcher graph has no weapon classes (activator/protector pings) -> NOT armable. Crawler: weapons are
head guns (_pawnhead), no hands -> NOT armable. Hunter: no weapon classes.
Weapon List block (name -> class) is the engine's class redirect: Knight ('rl','rifle') lets the
missile-class rocket/incineration_knight use rifle:rl; Elite ('pr','spr' -> pistol).
Teach options, all map-level, sorted blocks (sort="true"): (a) Grunt: add an 'any' type to combat
rifle (copy of 'ar', Sets shared by pointer) -- 1 element of 0x14; (b) Jackal/Knight missile:
Weapon List row (name, rifle) + a rifle type of that name, or a missile class copy; (c) flee/crouch
class copies as in H2. Growth fits the slack. Kit route (rebuild 8 maps) not needed.

## 5. Shields / melee
- Jackal arm shield = hlmt Variants child object (minor*/major* -> jackal_shield[_major]; sniper*,
  ranger*, minor_no_shield -> none). Two-handed Jackal: spawn point Actor Variant +0x40 =
  'minor_no_shield' (string present on Dawn). Cells have NO actor-variant field -> cell Jackals keep
  the char's rolled variant (shield) unless the cell's char is moved to storm_jackal_ranger/sniper.
  Shipped: storm_jackal + covenant carbine on Reclaimer (front_jackal_sq, grav_lift_sq) with NO
  variant -> Bungie ships shield + rifle.
- Sword/hammer: meleeOnly; WP rows exist (sword, hammer). Only Elites have the classes; hammer
  set is a stub. Restrict sword to Elite, hammer to none (or Elite after a test).

## 6. Recommended route
Port h2_enemy_weapons' shape to H4: arm spawn points directly; cells: unshare arrays, write both
twins; skip protected; skip weapons absent from the palette (none today); Jackal two-handed ->
'minor_no_shield' on spawn points; firing rows for Sticky/Focus by repointing a null generic row
(ai_firing_profile --from-map rows). Eligible species: Grunt, Jackal, Elite, Knight + Marine/Spartan
ally card. Effort: module ~1-1.5 days (reuse _TS_LAYOUT/_ts_units/_ts_unshare_cells), Grunt
rifle-any teach + Jackal flee teach ~0.5 day, enhancer wiring per hand-off.

## Unknowns (game only)
U1 which cell twin is read; U2 does a type-less class fall back (Grunt + DMR/SAW/Storm Rifle), or a
class-less weapon fall to mode 'any' (Jackal/Knight + rocket); U3 fire without a firing row (Sticky,
Focus Rifle); U4 do Weapon List rows work as a teach; U5 Grunt/Jackal flee drop (Backup Weapon);
U6 Jackal shield + rifle look; U7 graph siblings matter; U8 own-row fallback to ai\generic
(storm_jackal row list); U9 Elite hammer usability.
Smallest test: ONE map (Composer, has designer twins + all three Covenant species + Marines),
hand-staged copy: Grunts -> DMR in combat spawn points, Grunt designer twin -> SAW / templated
twin -> Storm Rifle (U1), Jackals spawn points -> Rocket (U2) and DMR + minor_no_shield (U6),
Elites -> Sticky Detonator (U3), one Elite -> hammer (U9); watch fire, hold, flee.

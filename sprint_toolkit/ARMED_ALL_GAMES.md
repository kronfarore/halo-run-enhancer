# Armed cards in every game (Halo 3, ODST, Reach, Halo 4)

Armed cards ("Armed: <weapon>": each pick moves 10% more of an enemy type onto a weapon) exist
for Halo 1 (`h1_enemy_weapons.py`) and Halo 2 (`h2_enemy_weapons.py`, `H2_ARMED_HANDOFF.md`).
The user wants them in every game (2026-11-02). This note is the plan and the record; the
measured scoping lives in `armed_scope/` (one folder per engine family, with the scripts that
produced it).

## User decisions (2026-11-02)

1. **Game order**: Halo 3 -> ODST -> Reach -> Halo 4. Start ONLY on Halo 3.
2. **Assume every weapon is always loaded and every species exists on every map.** No
   residency gate in the Armed pass.
3. **Species residency** comes from the Halo 1 trick: a character that names the next one, so
   one entry makes every species resident (`sprint_toolkit/h1_all_enemies.py`, the slot chain;
   `VARIANT_RECIPE.md`). Hopefully it works in every game; it is its own work item per game.

## Per game: what the scoping measured (read-only, 2026-11-02)

| | units | weapons | AI firing data | animation gaps | test |
|---|---|---|---|---|---|
| Halo 3 | fire-team +0xA / location +0x2A; no shared arrays | all pool weapons in every palette | all but the SAW | Grunt: sword, hammer, flamethrower, missile pod; Jackal / Drone: missile, support, sword, hammer, turret classes; Marine: Brute Shot, sword, hammer, Sentinel Beam, plasma cannon, missile pod, machine gun | 010 |
| ODST | cells share weapon arrays (121 of 266), 135 empty arrays | Machine Gun absent from 5 palettes | all but the SAW | as Halo 3 | sc100 |
| Reach | 87% of cells share their array; spawn points with character -1 carry their own weapon (+0x34), missed by `_ts_units` | all in every palette | all 23 stock; SAW none | Grunt: rifle without an `any` type, rifle only in combat; Jackal / Skirmisher: no missile; Bugger: pistol only | m52, then m10 |
| Halo 4 | spawn point weapon +0x30; cell arrays shared (up to 68 users); designer / templated twins disagree -- write both | all in every palette | all but Sticky Detonator and Focus Rifle (repoint a nulled row) | Grunt: no type for Storm Rifle / DMR / SAW / ...; Jackal / Knight: no missile class | staged Composer |

Common to all: sword is Elite-only (hammer Elite / Brute); Hunters, Engineers, Crawlers,
Watchers, Flood infection forms / carriers are not armable; fleeing Grunts and Jackals only
have pistol animations (Halo 2's flee-drop risk); Jackals need a no-shield variant for
two-handed weapons, which cells cannot carry.

Notes: `armed_scope/h3_odst/NOTES_armed_h3_odst.txt`, `armed_scope/reach/NOTES.md`,
`armed_scope/h4/H4_ARMED_SCOPING.md`.

## Halo 3 route (BUILT 2026-11-02, offline-verified, not booted)

`h3_enemy_weapons.py` (tool root) on the shape of `h2_enemy_weapons.py`: deterministic per
unit, every unit of a carded type (allied ones too), the Ally card = friendly Marines; only
species x weapon pairs the animation gate allows; run in `apply_run` after the skulls. Enhancer
wiring as for Halo 2 (`ARMED_ENEMIES`, `ARMED_OPTIONS`, spec builder). Teaching missing classes
waits for the first boot.

Built: `h3_enemy_weapons.py` (the gate replays sapien's `unit_can_use_weapon` on the map's own
graphs, raw string ids; `shieldless` found by index when no location uses it), enhancer
`H3_ARMED_ENEMIES` / options `h3_enemy_weapon_cards` (on) + `h3_armed_all_weapons` (off) in the
Halo 3 map-patching box, `_h3_enemy_weapons_spec`, `apply_run(h3_enemy_weapons=)` after the Halo 2
pass. Dry runs: 010 / 030 / 050 / 100 gate verdicts match the scoping; 010 at 100% puts every
Grunt (BR), Jackal (AR, 97 locations shieldless) and Brute (shotgun) location on its card weapon.

Firing data (user 2026-11-02): the ODST Magnum, Silenced SMG and Brute Plasma Rifle borrow the
Magnum's, SMG's and Plasma Rifle's ai\generic rows (`FIRING_DONORS`, `borrow_firing`: the rows
copied with the weapon renamed, the blocks relocated into partition slack). The SAW stays OUT
of Halo 3 Armed cards (`EXCLUDED`, enhancer and pass) until Halo 3's weapon ports.

First boot: `sprint_toolkit/h3_armed_test.py` builds `010_jungle_armed_test.map` from the
baseline (`h3_armed_test.cmd deploy | restore`): the first hostile squads (sq_jw_u_cov_01,
sq_jw_u_grunts_01, ~50-65 wu from the start) carry Grunt + BR / ODST Magnum / Rocket / Hammer
(refused, forced), Jackal + AR (shieldless) / BR (shield kept) / Rocket (refused, forced),
Brute + Brute Plasma Rifle / Silenced SMG; the start Marines (sq_training, sq_johnson_marines)
Silenced SMG / Brute Shot (refused, forced); god shield, carbine x1000 as every profile's
secondary, run x2.

Boot 1 (2026-11-03): Grunts held + fired BR / ODST Magnum / Rocket; Brutes the Brute Plasma
Rifle / Silenced SMG; Marines the Silenced SMG. REFUSED = UNARMED (the Hammer Grunt, the Brute
Shot Marine): the gate's "never hand out a refused pair" is right. The first Jackals met had their
vanilla weapons and shields (unclear which squad) -> v2 deals the three Jackal cases to EVERY
Jackal in 010 (`all_jackals`). No Grunt / Jackal weapon drop seen yet.

Boot 2 (2026-11-03): every Jackal case right -- AR Jackals shieldless, a shielded Jackal holds
the Battle Rifle, Rocket Jackals (refused) unarmed.

TEACHING (user 2026-11-03: "teach enemies to wield every weapon, the only exception is the two
melee weapons for now"): `h3_enemy_weapons.teach` runs inside the Armed pass for every pair the
gate refuses: a Weapon List row (the weapon's NAME -> a donor weapon's class, `TEACH_DONORS` by
kind: heavy -> Rocket Launcher's class, rifle -> Assault Rifle's, pistol -> Plasma Pistol's, falling
back down the list) in every graph of the species, only where that class has an `any` type with
`idle`. `NOT_TAUGHT` = Energy Sword, Gravity Hammer; the enhancer offers those cards only for
Elites and Brutes. Dry runs 010 / 030 / 050 / 100: every species present on the level holds every
weapon but the two melee weapons (Jackal / Drone heavies and turrets via the rifle class, Grunt
flamethrower / missile pod and Marine Brute Shot / Sentinel Beam / turrets via the missile class).
What is still refused is species ABSENT from the level (no graphs) -- the residency work item.
Test v3 deployed: the taught weapons (Grunt flamethrower / missile pod, Jackal rocket / Brute Shot /
machine gun turret / Spartan Laser on every Jackal, Marine Brute Shot / machine gun turret / plasma
cannon / Sentinel Beam).

Boot 3 (2026-11-04): Marines held the taught Brute Shot / Sentinel Beam, everything else came
out unarmed (Grunt flamethrower / missile pod, Jackal rocket / laser / turret; Jackal Brute Shot
worked). CAUSE: every stock Weapon List is SORTED by the weapon-name string id and the game
binary-searches it; the taught rows were appended, and a binary search over the test map's lists
predicts exactly the rows that worked. `teach` now rewrites the whole list sorted. v3b deployed.

Boot 4 (2026-11-04): every taught weapon held (Marines, Grunts, Jackals), Jackal Spartan Laser
/ Rocket Launcher look right, but turrets and the Brute Shot pointed at the sky: a weapon's grip
is built for its OWN class's pose, and they were held through the Rocket Launcher's. Fix: THE
POSE step (`_pose_plan`) -- a donor of the weapon's own native class that the species holds
lends its pose: Weapon List row to the donor's class plus, where that class has no `any` type, a
copy of the donor's TYPE entry under the weapon's name (shared animation pointers, as the game's
own Grunt Plasma Cannon / Machine Gun Turret entries). Types are sorted + binary-searched too
(every mode / class / type / action block in 010 is sorted), so `_grow_sorted` inserts in order.
Mounted (`_integrated`) / undeployed turret weapons are no donors (seated gunner pose). Result:
Grunt Flamethrower / Missile Pod in its Machine Gun Turret pose, Marine turrets in its Flamethrower
pose. NO matching pose exists for: the Brute Shot / Sentinel Beam on Marines (still the Rocket
Launcher's), turrets and the Brute Shot on Jackals / Drones (still the rifle's). v3c deployed.

Boot 5 (2026-11-05): Marine turrets right in the copied Flamethrower pose; still wrong: Marine Brute
Shot, Grunt turrets (Flamethrower / Missile Pod in the Grunt turret pose), Jackal turrets + Brute Shot.
The Sentinel Beam looks fine on Marines in the same borrowed pose -> the WEAPON MODEL decides. A unit
attaches a weapon at the marker its biped's Preferred Gun Node names (Brute right_hand_brute, Marine
right_hand_marine, Jackal left_hand_jackal, Grunt none) and at the weapon's ORIGIN without one; the
Brute Shot / Missile Pod carry a right_hand_brute marker rolled 90 deg, the turrets are built for the
turret pose. No weapon in any Halo 3 level has Grunt / Jackal / Marine grips (only vehicles), so
`grip()` COMPUTES one: for GRIP_FIX weapons (Brute Shot, Missile Pod, Machine Gun Turret, Plasma
Cannon, Flamethrower) taught across classes, a marker named GRIP_NAME[species] placed so the weapon's
off-hand marker lands where the donor's does in the hand (M = L_weapon * inverse(L_donor), node chain
to node 0), marker groups grown sorted; Grunt / Drone / female Marine bipeds get that Preferred Gun
Node. Marines keep the turret pose step (POSE_OK). v4 deployed: Grunt Flamethrower / Missile Pod
(rocket pose + grip), Grunt Machine Gun Turret NATIVE (control), every Jackal Brute Shot / turrets
(rifle pose + grip), Marine Brute Shot (rocket pose + grip) and Machine Gun Turret (confirmed pose).
If the grips come out mirrored / rotated the quaternion convention is the suspect (inverse it).

Boot 6 (2026-11-05): Marine Brute Shot RIGHT with the off-hand grip. Grunt turrets diagonal, Jackal
weapons sideways at face height (muzzle left). Cause: the GRIP_FIX weapons' ROOT nodes are rotated
against the object origin (Machine Gun Turret / Flamethrower pitched ~50 deg, Plasma Cannon ~95,
Brute Shot / Missile Pod on two axes, their 'body' child rolled 90 -- exactly Bungie's
right_hand_brute rotation), every rifle's root is unrotated; the off-hand comparison also mixes
conventions (Jackals hold the gun in the other hand; the Rocket Launcher has no plain left_hand for
Grunts). `GRIP_STYLE`: Marines keep 'offhand'; Grunts / Jackals / Drones get the BODY FRAME grip
(`_body_frame`: node 0's frame, or its 'body' child's) = held like a rifle. v5 deployed.

Boot 7 (2026-11-06): body-frame grips right for Grunt Flamethrower / Missile Pod and Jackal Brute
Shot / Machine Gun Turret / Flamethrower. Still wrong: the NATIVE Grunt Machine Gun Turret (Halo 3's own
Grunt turret pose holds it up) and the Jackal Plasma Cannon (backwards: its muzzle sits at -X). Fixes:
`REPOSE` (Grunt Machine Gun Turret / Plasma Cannon taught anyway: rocket pose + grip) and `_body_frame`
turns toward the primary_trigger direction with the smallest rotation (no change for the others; the
Plasma Cannon turns ~150 deg about Y). v6 deployed.

Boot 8 (2026-11-06): Grunt Machine Gun Turret and Jackal Plasma Cannon right. **HALO 3 ARMED CONFIRMED:**
every species on the level holds every weapon but the two melee weapons, pointed right. Live 010 restored.
Carry into ODST / Reach / Halo 4: refused weapon = unarmed; animation blocks + Weapon Lists + marker groups
are sorted and binary-searched; teach via a same-class pose donor where the species has one, else a
cross-class donor + a computed grip marker (Preferred Gun Node; off-hand alignment for Marines, body
frame turned to the muzzle for the rest); Jackals go shieldless with two-handed weapons.

## ODST route (BUILT 2026-11-06, offline-verified, first boot staged)

The Halo 3 module serves ODST: `h3_enemy_weapons.bind('Halo 3: ODST')` switches its tag offsets
(LAYOUTS: squads +0x3B8/0x6C, palettes +0x3E8 / +0x13C, weap class / name +0x3EC / +0x3F0, flags
+0x19C, ai\generic +0x198 / +0x1A4, biped Preferred Gun Node +0x1B4; jmad and render models as Halo 3)
and `_arm_cells` writes CELLS: a cell of a carded type draws once, its Initial Weapon array is copied
when shared / given an element when empty, every element names the weapon; a spawn point with its
own weapon draws for itself; Jackal spawn points of an all-Jackal cell take 'shieldless' (a cell's
units past its spawn points keep the shield). ODST story characters never armed (NEVER_WORDS).
Teaching, grips, REPOSE and borrowed firing data as Halo 3. Enhancer: ARMED_ENEMIES / ARMED_OPTIONS
'Halo 3: ODST' (odst_enemy_weapon_cards on, odst_armed_all_weapons off, in the ODST box),
_h3_enemy_weapons_spec for both games; apply_run passes game=. Dry run sc120 (all weapons, every
species): 673 cells armed (56 shared arrays copied, 1 empty filled), only the two melee weapons
refused, every pool weapon has firing data. Offers: every ODST mission. Halo 3 unchanged (010).
First boot: Kizingo Boulevard (sc120; Mombasa Streets h100 is the hub, user 2026-11-06), staged by
`sprint_toolkit/odst_armed_test.py` (+ `.cmd`): 18 enemy cells (6-61 wu) carry Grunt AR /
Flamethrower / Plasma Cannon, Jackal Rocket (shieldless) / Brute Shot / Plasma Cannon, Brute Silenced
SMG, Drone Rocket / Brute Shot; 6 Marine cells Brute Shot / Plasma Cannon / Silenced SMG; god shield,
Carbine x1000, run x2.

ODST boot 1 (2026-11-07): Brute Silenced SMG right, Drone Rocket Launcher good enough; Marine Brute
Shot FLOATED in front of the hands (the Halo 3 'offhand' grip: ODST's Rocket Launcher puts its Marine
off-hand elsewhere) and the Marine Plasma Cannon pointed up (the flamethrower pose with no grip: its
root ~95 deg against the flamethrower's ~50 -- never covered by the Halo 3 boots, whose Marine turret
check was the Machine Gun Turret). No Grunt / Jackal met early, no Marine SMG seen, nothing unarmed.
Fix: the 'body' grip is now M = B_weapon * inverse(F_donor), F = the donor's root + body frame when its
root is rotated (identity for rifles and the Rocket Launcher: the confirmed grips unchanged); a
same-class pose gets that grip too when the roots differ > POSE_GRIP_DEG; GRIP_STYLE per game (ODST
Marines 'body'). Test v2 deals the cases to EVERY hostile / friendly cell of sc120.

ODST boot 2 (2026-11-07): right -- Marine Brute Shot, Jackal Brute Shot WHERE shieldless, Grunt AR /
Flamethrower / Plasma Cannon, Drone Brute Shot / Rocket Launcher; nothing unarmed. Wrong: Marine Plasma
Cannon floated in front (direction right: the grip took the flamethrower's root POSITION -> now the
donor's rotation, the weapon's own root position); plenty of Jackals kept the shield (formation /
extra Jackals never read a spawn point's variant). The CHARACTER picks the model variant (char
Variants +0x54: jackal 'minor', major 'major', sniper 'sniper'): `_Shieldless` copies the Jackal
character's root over a SPARE palette character (unused by every squad, no character's parent /
major; Firefight survival characters first) with one Variants element naming 'shieldless' (jackal
model variant 1), and every two-handed Jackal cell's Character Type points at that clone. Also:
squads SHARE cell blocks (sc120: ~62 distinct hostile cells behind 673 references) -- one draw per
cell now. v3 deployed (every distinct cell dealt, 2-7 units per case).

ODST boot 3 (2026-11-07): Marine Silenced SMG normal; Marine Plasma Cannon now IN the hands but aiming up;
Jackal Plasma Cannon / Rocket Launcher held right -- some still shielded. Bungie's Sniper Jackals have no
spawn-point variant and the same biped, so the CHARACTER's variant does pick the look; the shielded ones
are the cell's MAJOR UPGRADE (char Major Character +0x44: jackal -> jackal_major). The clone's Major
Character now names the major's own shieldless clone (none when that cannot be made). The turret-pose
donor's root rotation enters inverted (the pitch as stored aimed up). v4 deployed.

ODST boots 4-6 (2026-11-08/09): every Jackal shieldless (clone + major clone); the Marine Plasma Cannon
pointed up with the flamethrower root pitch as stored, down inverted, FORWARD with no pitch at all (a
turret-pose donor adds none; the weapon's own root position). **ODST ARMED CONFIRMED (6 boots).** Live
sc120 restored. Carry into Reach / Halo 4 on top of the Halo 3 rules: squads share cell blocks (one draw
per cell); the character picks the model variant, Major Upgrades swap to the Major Character; spare
palette characters can be cloned at patch time.

## Open questions only the game answers (first boot per game)

- a refused weapon: unarmed, or the character's default?
- a weapon with no firing data (SAW, Sticky): held but silent?
- Halo 4: which twin cell is read?
- shielded Jackal holding a rifle; Grunts / Jackals fleeing with a rifle.

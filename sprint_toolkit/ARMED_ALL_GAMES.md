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

## Open questions only the game answers (first boot per game)

- a refused weapon: unarmed, or the character's default?
- a weapon with no firing data (SAW, Sticky): held but silent?
- Halo 4: which twin cell is read?
- shielded Jackal holding a rifle; Grunts / Jackals fleeing with a rifle.

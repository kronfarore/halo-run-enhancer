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

## Open questions only the game answers (first boot per game)

- a refused weapon: unarmed, or the character's default?
- a weapon with no firing data (SAW, Sticky): held but silent?
- Halo 4: which twin cell is read?
- shielded Jackal holding a rifle; Grunts / Jackals fleeing with a rifle.

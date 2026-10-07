# Halo 1: every missing weapon (plan, 2026-10-06)

The user's master list (`tool\Halo Weapons Spreadsheet (CE - Infinite).ods`, Sheet2) marks
25 weapons missing from Halo 1. The aim is to attempt all of them, Halo 1 first. Rules:

- **One weapon per session**, handed over with the prompt at the end of this file.
- **Sequential at the start.** The next weapon starts only when the previous one is DONE
  (definition below). Parallel sessions come later, once phase 0's reservations and
  per-weapon configs make them safe.
- A finding from one port is an OBSERVATION until a second port confirms it
  (memory port-findings-are-observations). Each session writes what it found into PORTING.md.

Done so far: SAW (from Halo 4), Energy Sword, Fuel Rod and Sentinel Beam (restored, the
last a full Halo 3 port). Their recipes are in PORTING.md. Phase 0 (setup) is DONE
(2026-10-07): next is the SMG pilot, with the prompt at the end of this file.

## Phase 0: DONE (2026-10-07)

What phase 0 set up, and how a weapon session uses it. Do not re-plan it; use it.

### 0.1 Capacity: all 25 fit in every map (the user decides any policy)

Measured on the ten built maps (2026-10-06 builds; HCEEK, live and E:\HaloBaselines copies
identical) against MCC classic's REAL limits (sources: HCEEK `tool.exe` disassembly,
c20.reclaimers.net, Invader's scenario definition; full report in this session's notes):

| limit | value | where we are (10 maps) |
|---|---|---|
| tag space (tag data + largest BSP) | **64 MiB** (tool: "tags are %.2fM too large"; every BSP ends at 0x54000000) -- not CE's 23 MiB | 17.9-19.2 MiB |
| vertex buffers (models + largest BSP's vertices) | **64 MiB** (tool: "vbuf are %.2fM too large"; the game side assumed the same) | 18.5-23.7 MiB, **a10 highest** |
| tag count | 65,535 | 3,963-4,836 |
| file size | 2 GiB (c20); tool has no 384 MiB check | 220.6-298.4 MiB |
| weapons palette / weapon placements / object names | 256 / **128** / 640 (Invader; tool enforcement assumed) | 41-42 after 25 / **d40 90 now, 115 after 25** / b40 460 |

Per-weapon cost, measured from each port's tag closure in the built maps (what the stock
2026-08-19 kit build did not already have):

| port | tags | tag data | model verts | bitmaps | sounds | map file |
|---|---|---|---|---|---|---|
| Sentinel Beam | 31 | 97 KB | 0.50 MB | 0.35 MB | 0.26 MB | +1.2 MB |
| SAW | 24 | 158 KB (322 KB if it shared nothing) | 1.35 MB | 3.33 MB | 0.48 MB | +5.3 MB |
| Fuel Rod | 48 | 136 KB | 0.25 MB | 1.55 MB | 0.49 MB | +2.4 MB |
| Energy Sword | 30 | 112 KB | 0.01 MB | 0.01 MB | 1.1 MB | +1.2 MB |

**Result:** even at the worst case (25 SAW-sized ports, sharing nothing) every map fits:
the binding limit is the 64 MiB VERTEX BUFFER on **a10** (23.7 -> ~55.9 MiB, 8 MiB left;
~31 SAW-sized models in total). Tag space has room for ~145 worst-case ports. The second
tightest is **d40's weapon placement block** (115 of 128 after 25: the resident-only
placement costs one each). Note: `E:\HaloBackups\ek-build-h1\previous` ALREADY carries the
Sentinel Beam (its difference to today is the all-enemies Marine chain), so it cannot
measure a port's growth; the measurement above walks each port's closure instead.

**DECIDED (user, 2026-10-07): every port stays resident in ALL TEN maps** (palette entry +
resident-only placement in every scenario, `palette_levels` = all ten). Not "resident only
where offerable": the enhancer can then give any port anywhere (starting weapons, offers,
Armed cards, a run carrying it level to level). Revisit only if a map over 384 MiB fails to
load or a10's vertex buffer gets tight -- switching is just a config's `palette_levels`.

Still open:
- **384 MiB file size**: Custom Edition's old cap. MCC's limit is 2 GiB by c20, but no map
  over 384 MiB has been booted; five maps (a10, d40, b40, c40, c10) would pass it after 25
  SAW-sized ports. The first port that pushes one over is the boot that settles it.
- If margin is ever wanted: leaner models (fewer LODs: vertex buffer
  is the tight one); shared sounds/bitmaps; recycle unused d40 palette/placement entries.
- Cheap improvement: `h1_rebuild_all.py` could record tool's own "total tag size / vbuf
  size (free)" lines per build -- exact numbers instead of estimates.

### 0.2 Per-weapon configs: `sprint_toolkit/ports_h1/<key>.py`

One file per weapon, a dict `PORT` (docs in `ports_h1/__init__.py`). The five pipeline
scripts read their SECTION of every config; a session edits only its weapon's file:

| section | read by |
|---|---|
| `model` | h1_h3_weapon_model.py (H3 geometry, bitmaps, shaders) |
| `retarget` | h1_fp_retarget.py (H3 FP animations onto the H1 arms) |
| `pickable` | h1_pickable_weapons.py (the weapon tag and everything it edits) |
| `sounds` | h1_port_sounds.py (H3 audio -> tags + bank manifest) |
| `catalog` | make_port_catalog_h1_ports.py |
| `firing_profile` | ai_firing_profile.py --port <key> (step 11) |
| `test` | h1_port_test_map.py (the dry test map) |
| `backup` | port_backup.py --game h1 (extras; the rest is derived) |

Plus `order`, `name` (halo.json's), `source`, `status`, `reservations`, `yardstick`
(`pick` / `reason` filled at step 4a, `candidates` from 0.4). `sentinel_beam.py` is the
complete example of a full Halo 3 port. The 25 weapons have STUBS (reservations, yardstick
candidates, the step-11 source); `python -c "import ports_h1; print(ports_h1.check_reservations())"`
must print `[]`.

Proof (2026-10-07): the old scripts' `--write` (model, retarget x3, pickable, sounds x3,
catalog) were run, then the config-driven ones; a SHA-1 snapshot of every file they write
(4,147 files: HCEEK tags weapons/sound/ui/characters/levels, data weapons/sound,
port_sounds\halo1, the catalog, ai_firing_profiles.json) is identical between the two
runs except the two Sentinel Beam bitmaps -- and those differ run-to-run with the OLD
scripts too: `tool bitmaps` writes a garbage `base_address` pointer (and the header
checksum); the pixel data is identical. `ai_firing_profile.py --port saw|sentinel_beam`
reproduces ai_firing_profiles.json byte for byte. The kit was then put back to its exact
pre-session state (0 of 4,147 files differ).
OBSERVATION (Sentinel Beam, not isolated): regenerating `weapons\sentinel beam\fp\fp.gbxmodel`
with `tool model` gives LOD node counts 6 where every backup and the shipped build have 0;
the tested 0-version was restored. The next session that rebuilds the beam's FP model
should check the FP model in game (moving parts) or keep the backup.

Reservation-aware writers: `h1_pickable_weapons.message_index` writes the pair at the
port's reserved index (pads with empty lines, refuses a slot holding other text);
`h1_hud_sheet.put_twins(..., index=)`, `add_msg_icon.py <png> <name> <index>`,
`h1_add_reticle.py <sheet> <h3 idx> <name> <index>`; make_hud refuses an icon that is not at
its reserved index. Parallel sessions: the indices cannot collide, but two sessions writing
the SAME shared tag at the same moment still race (read-modify-write) -- run the shared-tag
writers (messages, icon/reticle sheets, cyborg labels, scenarios) one session at a time.

### 0.3 Reservations

Read from the live HCEEK tags on 2026-10-07: `hud_item_messages` had 53 entries (47/48 SAW,
49/50 sword, 51/52 Sentinel Beam; the fuel rod uses the stock 46), `hud_msg_icons` and its
`_r` twin 30 sequences (25 SAW, 27 sword, 28 fuel rod, 29 beam), `hud_reticles` / `_r` 19
(17 sword, 18 beam). Labels in use anywhere in the kit's animation and weapon tags: `''`,
ar b c-needler cannon cg f fb fixed fr ft gt gun hp ne pb pc pp pr rl sb sg sr sw unarmed and
the digsite 99* set -- none of those is reserved below. Reticle reservations are only used
if the port brings its own reticle.

| # | weapon (catalog name) | config | messages | icon | reticle | label <- taught from | sound folder | weapon folder |
|---|---|---|---|---|---|---|---|---|
| A1 | SMG | smg | 53/54 | 30 | 19 | sm <- ar | sound\weapons\smg_port | weapons\smg |
| A2 | Battle Rifle | battle_rifle | 55/56 | 31 | 20 | br <- ar | sound\weapons\battle_rifle_port | weapons\battle rifle |
| A3 | Covenant Carbine | covenant_carbine | 57/58 | 32 | 21 | cc <- ar | sound\weapons\covenant_carbine_port | weapons\covenant carbine |
| A4 | Beam Rifle | beam_rifle | 59/60 | 33 | 22 | bm <- sr | sound\weapons\beam_rifle_port | weapons\beam rifle |
| A5 | Spike Rifle (Brute Spiker) | brute_spiker | 61/62 | 34 | 23 | sk <- hp | sound\weapons\spiker_port | weapons\spiker |
| A6 | Mauler (Brute Mauler) | brute_mauler | 63/64 | 35 | 24 | ml <- sg | sound\weapons\mauler_port | weapons\mauler |
| A7 | Brute Shot | brute_shot | 65/66 | 36 | 25 | bs <- rl | sound\weapons\brute_shot_port | weapons\brute shot |
| A8 | Spartan Laser | spartan_laser | 67/68 | 37 | 26 | sl <- rl | sound\weapons\spartan_laser_port | weapons\spartan laser |
| A9 | Gravity Hammer | gravity_hammer | 69/70 | 38 | 27 | gh <- f | sound\weapons\gravity_hammer_port | weapons\gravity hammer |
| B1 | DMR | dmr | 71/72 | 39 | 28 | dm <- ar | sound\weapons\dmr_port | weapons\dmr |
| B2 | Needle Rifle | needle_rifle | 73/74 | 40 | 29 | nr <- pr | sound\weapons\needle_rifle_port | weapons\needle rifle |
| B3 | Plasma Repeater | plasma_repeater | 75/76 | 41 | 30 | rp <- pr | sound\weapons\plasma_repeater_port | weapons\plasma repeater |
| B4 | Grenade Launcher | grenade_launcher | 77/78 | 42 | 31 | gl <- sg | sound\weapons\grenade_launcher_port | weapons\grenade launcher |
| B5 | Concussion Rifle | concussion_rifle | 79/80 | 43 | 32 | cr <- pr | sound\weapons\concussion_rifle_port | weapons\concussion rifle |
| B6 | Plasma Launcher | plasma_launcher | 81/82 | 44 | 33 | pl <- rl | sound\weapons\plasma_launcher_port | weapons\plasma launcher |
| B7 | Focus Rifle | focus_rifle | 83/84 | 45 | 34 | fo <- sr | sound\weapons\focus_rifle_port | weapons\focus rifle |
| C1 | Storm Rifle | storm_rifle | 85/86 | 46 | 35 | st <- pr | sound\weapons\storm_rifle_port | weapons\storm rifle |
| C2 | Suppressor | suppressor | 87/88 | 47 | 36 | su <- ar | sound\weapons\suppressor_port | weapons\suppressor |
| C3 | Boltshot | boltshot | 89/90 | 48 | 37 | bo <- pp | sound\weapons\boltshot_port | weapons\boltshot |
| C4 | LightRifle | lightrifle | 91/92 | 49 | 38 | lr <- ar | sound\weapons\light_rifle_port | weapons\light rifle |
| C5 | Scattershot | scattershot | 93/94 | 50 | 39 | ss <- sg | sound\weapons\scattershot_port | weapons\scattershot |
| C6 | Binary Rifle | binary_rifle | 95/96 | 51 | 40 | bi <- sr | sound\weapons\binary_rifle_port | weapons\binary rifle |
| C7 | Railgun | railgun | 97/98 | 52 | 41 | rg <- rl | sound\weapons\railgun_port | weapons\railgun |
| C8 | Sticky Detonator | sticky_detonator | 99/100 | 53 | 42 | sd <- hp | sound\weapons\sticky_detonator_port | weapons\sticky detonator |
| C9 | Incineration Cannon | incineration_cannon | 101/102 | 54 | 43 | ic <- pc | sound\weapons\incineration_cannon_port | weapons\incineration cannon |

The "taught from" label is a PROPOSAL for the third-person pose class (H1 has rifle /
pistol / missile / plasmacannon / flamethrower); a session may change it (its config).
The catalog name is exactly halo.json's (`Spike Rifle`, `Mauler`, `LightRifle`).

### 0.4 Yardstick candidates (PROPOSALS -- the user picks at step 4a)

Each candidate exists in BOTH the source game's kit and HCEEK (checked by listing the
kits; each port's .weapon + projectile exported and classified). Halo 4 has NO Plasma
Rifle and NO Flamethrower (but has an AI-only `pistol\storm_sentinel_beam` on its
Sentinels); Reach has NO Flamethrower and NO Sentinel Beam; Halo 3 has all of Halo 1's.
The restored Energy Sword and Fuel Rod keep Bungie's own Halo 1 numbers (only their
BALANCED rows were derived), so they are clean yardsticks; the Sentinel Beam's Halo 1
numbers are themselves derived -- a ratio against it chains two derivations.
No port has a true DIRECT yardstick (Brutes, Knights, Skirmishers, Crawlers are not in
Halo 1; the Elite / Marine links point back at the provisional).

| # | weapon | source tag (kit-relative) | provisional | alternatives | direct | step-5b peers | why |
|---|---|---|---|---|---|---|---|
| A1 | SMG | H3 rifle\smg\smg | Assault Rifle | Pistol; Plasma Rifle | none | AR, Plasma Rifle, Needler | magazine full-auto bullet, projectile like H3's AR (lacks dual wield) |
| A2 | Battle Rifle | H3 rifle\battle_rifle\battle_rifle | Pistol | Assault Rifle; Sniper Rifle | none | Pistol, AR, Sniper | magazine, 2x scope, instant bullet = the magnum's role (lacks 3-round burst) |
| A3 | Covenant Carbine | H3 rifle\covenant_carbine\covenant_carbine | Pistol | Needler; Sniper Rifle | none | Pistol, Sniper, Needler | semi-auto 18, 2x zoom, instant slug: the Covenant precision rifle |
| A4 | Beam Rifle | H3 rifle\beam_rifle\beam_rifle | Sniper Rifle | Plasma Pistol (heat + battery); Sentinel Beam | none | Sniper | instant beam, two zooms, heat-limited + battery |
| A5 | Brute Spiker | H3 rifle\spike_rifle\spike_rifle | Needler | Assault Rifle | none | AR, Needler, Plasma Rifle | magazine 40 auto, slow arcing projectile = the needler's family (lacks dual wield, blades) |
| A6 | Brute Mauler | H3 pistol\excavator\excavator | Shotgun | Pistol | none | Shotgun, Energy Sword, Flamethrower | 5 rounds, instant pellets, 8 wu: a one-hand shotgun |
| A7 | Brute Shot | H3 support_low\brute_shot\brute_shot | Rocket Launcher | Fuel Rod; Frag Grenade | none | RL, Fuel Rod | magazine 6, explosive grenade (lacks the bounce arc, blade melee) |
| A8 | Spartan Laser | H3 support_high\spartan_laser\spartan_laser | Sniper Rifle | Rocket Launcher; Sentinel Beam | none | RL, Sniper, Fuel Rod | instant beam, one huge shot, battery (lacks charge-up: fuel rod precedent) |
| A9 | Gravity Hammer | H3 melee\gravity_hammer\gravity_hammer | Energy Sword | any H1 melee | none | Energy Sword, Shotgun | melee with energy per swing (lacks the area knockback) |
| B1 | DMR | Reach rifle\dmr\dmr | Pistol | Sniper Rifle | none | Pistol, Sniper | semi-auto 15, 3x zoom, near-instant = the magnum's role |
| B2 | Needle Rifle | Reach rifle\needle_rifle\needle_rifle | Needler | Pistol; Sniper Rifle | none | Pistol, Needler, Sniper | semi-auto needles, 2x zoom, supercombine like the needler |
| B3 | Plasma Repeater | Reach rifle\plasma_repeater\plasma_repeater | Plasma Rifle | Plasma Pistol | (Elite = the provisional) | Plasma Rifle, AR, Needler | heat automatic plasma, rate falls with heat (lacks manual vent) |
| B4 | Grenade Launcher | Reach rifle\grenade_launcher\grenade_launcher | Rocket Launcher | Frag Grenade; Fuel Rod | none | RL, Fuel Rod | 1-round bouncing grenade (lacks hold-to-detonate, EMP) |
| B5 | Concussion Rifle | Reach rifle\concussion_rifle\concussion_rifle | Fuel Rod | Rocket Launcher; Plasma Grenade | none | Fuel Rod, RL, Plasma Rifle | magazine 6 explosive plasma; Reach's fuel rod is a magazine weapon too |
| B6 | Plasma Launcher | Reach support_high\plasma_launcher\plasma_launcher | Fuel Rod | Plasma Grenade; Rocket Launcher | none | RL, Fuel Rod | charge-to-fire explosive plasma, heat + battery (lacks multi-bolt, lock-on, stick) |
| B7 | Focus Rifle | Reach rifle\focus_rifle\focus_rifle | Plasma Rifle | Sniper Rifle; Plasma Pistol | none | Sniper, Sentinel Beam | continuous beam on heat + battery; Reach has no Sentinel Beam |
| C1 | Storm Rifle | H4 rifle\storm_assault_carbine\... | Plasma Pistol | Assault Rifle; Needler | none | Plasma Rifle, AR, Needler | heat automatic plasma; H4 has no Plasma Rifle |
| C2 | Suppressor | H4 rifle\storm_forerunner_smg\... | Assault Rifle | Needler; Sentinel Beam (H4 AI-only) | none | AR, Plasma Rifle, Needler | magazine 48 auto, decelerating hardlight bolt |
| C3 | Boltshot | H4 pistol\storm_stasis_pistol\... | Pistol (bolt) + Shotgun (charged) | Plasma Pistol | none | Pistol, Plasma Pistol, Shotgun | two modes = a ratio per mode (charged blast approximated) |
| C4 | LightRifle | H4 rifle\storm_forerunner_rifle\... | Pistol | Sniper Rifle; Assault Rifle | none | Pistol, Sniper | magazine 36, 3x zoom precision (lacks the scoped/unscoped mode switch) |
| C5 | Scattershot | H4 rifle\storm_spread_gun\... | Shotgun | Energy Sword | none | Shotgun, Energy Sword, Flamethrower | 6 pellets, close range (lacks ricochet) |
| C6 | Binary Rifle | H4 rifle\storm_forerunner_sniper_rifle\... | Sniper Rifle | Rocket Launcher | none | Sniper | magazine 2, two zooms, one-hit kill |
| C7 | Railgun | H4 rifle\storm_rail_gun\... | Rocket Launcher | Fuel Rod (charge); Sniper Rifle | none | RL, Sniper, Fuel Rod | 1 round, 0.75 s charge, impact + explosion |
| C8 | Sticky Detonator | H4 pistol\storm_sticky_detonator\... | Rocket Launcher | Plasma Grenade; Fuel Rod | none | RL, Fuel Rod | arcing sticky explosive (remote detonation approximated) |
| C9 | Incineration Cannon | H4 support_high\storm_forerunner_incineration_launcher\... | Rocket Launcher | Fuel Rod | none | RL, Fuel Rod | rocket-launcher type, 1 round, explosive, 1.8x zoom (cluster approximated) |

Source-kit yardstick paths: H3EK / HREK `objects\weapons\pistol\magnum\magnum`,
`rifle\assault_rifle`, `rifle\shotgun`, `rifle\sniper_rifle`,
`support_high\rocket_launcher`, `pistol\plasma_pistol`, `rifle\plasma_rifle`,
`pistol\needler`, `support_high\flak_cannon` (fuel rod), H3 `melee\energy_blade` / Reach
`melee\energy_sword`, H3 `turret\flamethrower`, H3 `support_low\sentinel_gun`; H4EK the
`storm_` versions (`pistol\storm_magnum`, `rifle\storm_assault_rifle`, ...,
`support_high\storm_fuel_rod_cannon`, `melee\energy_sword`). Grenades: `objects\weapons\grenade\
(storm_)frag_grenade` / `(storm_)plasma_grenade` .projectile.

### 0.5 Test staging: `h1_port_test_map.py`

    python h1_port_test_map.py <key> [--level a30] [--rounds L,T] [--grunt <actv>] [--elite <actv>] [--god] [--stage]
    python h1_port_test_map.py --restore <level>

Temporarily (scenario copied, ALWAYS restored): the weapon resident in that level if it is
not yet (palette + the SAW's resident-only placement), every SPAWN profile's primary =
the port (rounds: flag, config `test.rounds`, else the first magazine full), the asked-for
actor variants in the palette; single-level build -> `HCEEK\maps\port_test\<level>.map`;
the normal level rebuilt. On the copy: Grunts / Elites swapped
(`h1_enemy_test_map.swap_actors`), optional god shield. `--stage` backs the LIVE map up to
`E:\HaloBackups\h1_port_test\<level>.map` (never over a backup of its own staged copy:
`stage.json` records it) and puts the copy live. Non-spawn profiles skipped: every level's
`sprint_profile`, a10's bridge0/bridge1/weapon_insert. Verified 2026-10-07 on c40 (beam +
Sentinels): both spawn profiles name the beam in the BUILT copy, 6 Grunt entries swapped,
the kit c40 rebuilt byte-identical, the live c40 staged and restored to its exact hash.

### 0.6 Catalog + Armed (step 11)

`make_port_catalog_h1_ports.py [key ...] [--dry]` writes each config's `catalog.entry`;
for a port it derives `weap`, `fp_animations` and `requires` (`proj <own projectile>`)
from `pickable` when not given; it KEEPS every key the enhancer session added (tag_map,
card_map, skip_cards, ammo, ...) and checks balance rows / balance_desc / the donor name.
`make_port_catalog_h1_restored.py` is now a wrapper for the three restored entries.
Re-running it leaves weapon_ports_catalog.json byte-identical.

`ai_firing_profile.py --port <key> [--dry]` runs the config's `firing_profile`:
`carried` (nothing to write), `same_game` (donor_weapon + `set` fields), `source` (the
source game's ai\generic, now for Halo 3/ODST and Reach too, besides Halo 4; Halo 3's
per-weapon inner firing patterns are read when the pattern block has no entry). Every
stub's source was verified to have an ai\generic entry -- EXCEPT the Railgun and the Sticky
Detonator (none in any Halo 4 campaign map): their sessions choose a Halo 1 stand-in.

### 0.7 Backup

`port_backup.py --game h1` derives from the configs: each weapon's weapon and sound
folders (tags + data), the shared tags its `pickable` section edits in place (+
`.before_pickable`): actor variants (`drops`), effects (`death_drop`), scenarios
(`palette_levels`), plus the message list / icon + reticle sheets / cyborg animations; and
the scripts incl. `ports_h1/*.py`. Nothing the old hand lists carried was lost (checked).

### The phase-0 brief (as planned 2026-10-06; results above)

1. **Capacity.** Every port is made resident in all ten maps (palette entry plus one
   resident-only placement; memory h1-weapon-into-map). Measure each map's tag/meta size
   against Halo 1's limits, and the growth per port (the Sentinel Beam's delta from today's
   rebuild is a sample). Decide whether all 25 can be resident everywhere, or whether some
   are only resident where the enhancer can offer them.
2. **Reservations** (a table in this file), so sessions never collide and can later run in
   parallel:
   - pickup message indices in `ui\hud\hud_item_messages`;
   - `hud_msg_icons` sequence;
   - `hud_reticles` sequence;
   - the two-letter cyborg animation label (taught from the closest stock label);
   - the sound folder `sound\weapons\<x>_port`;
   - the catalog name (halo.json's name for the weapon).
2b. **Yardstick candidates** (a second table in this file). PROVISIONAL ONLY: the final
   pick is made with the user at the start of each weapon's session (step 4a below). Per
   weapon:
   - the ratio-rule yardstick (step 4: H1 value = H1 yardstick x source port / source
     yardstick), which must exist in BOTH the source game and Halo 1, sharing the port's
     role and damage type (bullet / plasma, hitscan / projectile, magazine / heat-battery);
   - at least one alternative;
   - any DIRECT yardstick (the same weapon or its user existing in both games, as the
     Sentinel was for the Sentinel Beam);
   - the step-5b role peers;
   - one line of why.
   Halo 1's candidates: Pistol, Assault Rifle, Shotgun, Sniper Rifle, Rocket Launcher,
   Plasma Pistol, Plasma Rifle, Needler, Flamethrower, plus the restored Energy Sword,
   Fuel Rod and Sentinel Beam.
   Why it matters: on the Sentinel Beam the plasma-rifle yardstick gave 10.4 per round, the
   Sentinel literally 1.0, the Sentinel by time-to-kill-the-player 4.64, and the per-second
   form 11.6.
3. **Per-weapon configs.** Today the H3-source pipeline keeps each weapon in a WEAPONS dict
   inside five scripts: h1_h3_weapon_model, h1_fp_retarget, h1_pickable_weapons,
   h1_port_sounds and make_port_catalog_h1_restored. Move each weapon into its own file
   (`ports_h1/<weapon>.py` or `.json`) that the scripts load, so sessions stop editing
   shared code.
4. **A generic test-staging tool.** It puts the weapon in the player's hands at the start
   of a chosen test map, plus the enemies that matter for it (h1_enemy_test_map.py
   already swaps the enemies). This replaces the SAW-only saw_scenario.py.
5. **A catalog writer for ports** (the restored entries' writer, generalized), plus the
   Armed-card firing-profile step (PORTING step 11).
6. **Backup:** port_backup.py --game h1 lists each new weapon's folders from its config,
   automatically.

## The order

The pipeline decides the order. Halo 3's first-person arm skeleton IS Halo 1's, so
`h1_fp_retarget.py` brings Halo 3 animations across whole, and Halo 3 also has the
cleanest geometry, bitmap and sound extraction (h3_rm_to_jms, h1_h3_weapon_model,
h1_port_sounds). Every weapon that exists in Halo 3 comes FROM Halo 3, Halo 2's included.
Reach and Halo 4 arms differ: those weapons go the SAW way (the source mesh on a Halo 1
donor's skeleton, the donor's animations retimed) until a session proves a retarget.

Each wave starts with a PILOT: the weapon that exercises the most of the pipeline in its
simplest form, used to fix and generalize the tools before the rest of the wave.

### Wave A: Halo 3 source, retarget pipeline (9)

| # | weapon | new things it tests |
|---|---|---|
| A1 | **SMG** (pilot) | the first plain magazine gun on this pipeline: reload, ammo pickup (step 6), magazine HUD meter |
| A2 | Battle Rifle | burst fire, zoom + scope HUD (memory halo-zoom-ui) |
| A3 | Covenant Carbine | zoom on a Covenant weapon, its own projectile |
| A4 | Beam Rifle | heat + zoom (Sentinel Beam heat lessons, tick-quantised rate) |
| A5 | Brute Spiker | the blades' melee, a slow projectile |
| A6 | Brute Mauler | a pellet spread (the shotgun as yardstick) |
| A7 | Brute Shot | a bouncing grenade projectile + its explosion (step 3: own chain) |
| A8 | Spartan Laser | a charge-up shot (the fuel rod's charge lessons), a beam visual (the Sentinel Beam's contrail lessons) |
| A9 | Gravity Hammer | a melee weapon with energy (the Energy Sword's recipe; aging per swing) |

### Wave B: Reach source, SAW route (7)

The pilot first PROVES the route from Reach (geometry: the Foundry route, memory
reach-port-foundry-render-model; animations: a Halo 1 donor's).

| # | weapon | new things it tests |
|---|---|---|
| B1 | **DMR** (pilot) | the Reach pipeline end to end; scope zoom |
| B2 | Needle Rifle | needles + supercombine (the needler as yardstick) |
| B3 | Plasma Repeater | heat with venting |
| B4 | Grenade Launcher | an arcing grenade; the EMP alt-fire approximated |
| B5 | Concussion Rifle | a splash push projectile |
| B6 | Plasma Launcher | a charge; lock-on approximated (guidance) |
| B7 | Focus Rifle | a beam + zoom (the H4 kit's Focus Rifle and the Sentinel Beam) |

### Wave C: Halo 4 source, the SAW's own route (9)

The SAW proved Halo 4 to Halo 1 (saw_to_jms.py, saw_port_values.py, h1_saw_sounds.py), but
those tools are SAW-hardwired: the pilot generalizes them.

| # | weapon | new things it tests |
|---|---|---|
| C1 | **Storm Rifle** (pilot) | generalizing the SAW tools; heat |
| C2 | Suppressor | an automatic, a fast projectile |
| C3 | Boltshot | a charged secondary shot, approximated |
| C4 | LightRifle | burst + zoom |
| C5 | Scattershot | bouncing pellets |
| C6 | Binary Rifle | a charge + zoom, one-shot balance |
| C7 | Railgun | a charge shot |
| C8 | Sticky Detonator | remote detonation approximated |
| C9 | Incineration Cannon | a cluster explosion |

A mechanic Halo 1 does not have (lock-on, remote detonation, EMP, bouncing projectiles...)
is APPROXIMATED as closely as the engine allows, never skipped (user, 2026-10-07). E.g.
lock-on -> strong projectile guidance/magnetism; remote detonation -> a sticky projectile on
a long fuse or a detonation triggered by a second shot. The session records the
approximation and what it does not reproduce.

## Definition of done, per weapon

All of PORTING.md's "What ported actually means", steps 1-11, plus:

- **step 4a, confirm the yardstick, WITH THE USER, before any tag number is written:**
  - run the ratio rule with the provisional yardstick and its alternatives (and any direct
    yardstick) side by side, per value: damage per round AND per second, rate, heat /
    battery, range, aim assist;
  - show the time to kill each gives (h1_role_compare.py);
  - the user picks; record the pick and the reason in the weapon's config and PORTING
    notes. The session never decides it alone.
- **step 5b:** the h1_role_compare.py set, with balanced values the user picked;
- **in every map:** palette entry plus resident-only placement in all ten scenarios,
  checked on the BUILT maps;
- **tested in game:** a dry test map first, then enemy behaviour (Armed card);
- **records:** catalog entry plus a hand-off to the enhancer session (cards, skip_cards,
  tag_map); PORTING notes; memory; port_backup --game h1.

The full ten-map rebuild + ship happens at the END of each weapon, on the user's go.

## Hand-off prompt for a weapon session

> Port the <WEAPON> into Halo 1 (H1_PORT_PLAN.md, wave <X>, #<n>). Source: <game>.
> Read sprint_toolkit/H1_PORT_PLAN.md (phase 0 results first), PORTING.md (Halo 1 sections +
> steps 0-11) and memory h1-pickable-sword-fuelrod / h1-weapon-into-map / h1-port-phase0 first.
> Your weapon's config is sprint_toolkit/ports_h1/<key>.py: its reservations (message pair,
> icon, reticle, label, sound and weapon folders) are fixed -- use them; edit only that
> file, never another weapon's or the shared scripts' tables. Before writing any numbers, do
> step 4a: lay out the provisional yardstick and its alternatives side by side (per value:
> damage per round AND per second, rate, heat / battery, range, aim assist; time to kill
> with h1_role_compare.py) and let me pick; record the pick and reason in the config.
> Test on a single map first with h1_port_test_map.py (no full rebuild until I say so).
> When done: catalog entry (make_port_catalog_h1_ports.py), firing profile
> (ai_firing_profile.py --port <key>), enhancer hand-off, PORTING notes, memory,
> port_backup.py --game h1 -- and add what this weapon taught to the plan.

### The SMG pilot (wave A1), filled in

> Port the SMG into Halo 1 (H1_PORT_PLAN.md, wave A, #A1, the PILOT of the Halo 3
> retarget pipeline). Source: Halo 3, `objects\weapons\rifle\smg\smg` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md (phase 0 results first), PORTING.md ("What ported
> actually means" steps 0-11 and 5b, the Halo 1 sections, "Halo 1: the Sentinel Beam, a full
> HALO 3 port") and memory h1-port-phase0, h1-pickable-sword-fuelrod, h1-weapon-into-map,
> halo1-starting-weapons-placed, halo-port-own-messages, h1-fmod-bank-sounds,
> port-findings-are-observations, shared-worktree-commits.
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Candidates (ports_h1/smg.py, yardstick.candidates): provisional ASSAULT RIFLE (magazine
> full-auto bullet; H3's SMG and AR both fire non-instant bullets), alternatives PISTOL and
> PLASMA RIFLE, no direct yardstick (H3 Marines carry the SMG, H1 Marines carry the AR -- the
> provisional). Read the H3EK SMG, AR, magnum and plasma rifle tags and the Halo 1 ones; put
> the ratio-rule result of each candidate side by side per value (damage per round AND per
> second, rate of fire, magazine / reserve, reload time, error / spread, range / velocity,
> aim assist, melee) and the time to kill each gives against the step-5b peers (Assault
> Rifle, Plasma Rifle, Needler) with h1_role_compare.py (add an 'smg' set). I pick; record
> the pick and the reason in ports_h1/smg.py yardstick['pick'] / ['reason'] and PORTING.
>
> Reserved (ports_h1/smg.py; do not take any other number): pickup messages 53/54
> ("Picked up an SMG" / "Picked up %d rounds for SMG"); hud_msg_icons sequence 30 (and its
> _r twin); hud_reticles sequence 19 (+ _r) if it brings Halo 3's SMG reticle; animation
> label `sm`, taught to characters\cyborg from `ar`; sounds under
> `sound\weapons\smg_port` (never under sound\sfx); weapon folder `weapons\smg`; catalog
> name `SMG` (halo.json's).
>
> Build it as the Sentinel Beam was built, but fill ports_h1/smg.py instead of editing the
> scripts: `model` (h1_h3_weapon_model.py smg), `retarget` (h1_fp_retarget.py smg --list /
> --preview / --write, then tool animations, fp_render check), `pickable`
> (h1_pickable_weapons.py --write; a `template` copy of the Halo 1 Assault Rifle is the
> natural start), `sounds` (h1_port_sounds.py smg), `test`, `catalog`. What the SMG tests
> for the first time on this pipeline: a plain MAGAZINE gun -- reload animations and their
> timing (step 9), the ammo pickup (step 6: which Halo 1 item tops it up), the magazine HUD
> meter (step 7, ammo_meter.py; Halo 1's meter runs 0..255, step = 255 // N). Fix and
> generalize the tools as you go; that is what a pilot is for. Dual wield is a mechanic
> Halo 1 lacks: approximate or record what is not reproduced.
>
> Residency: palette entry + resident-only placement in all ten scenarios
> (`palette_levels`), checked on the BUILT maps. Capacity is not a concern (phase 0.1).
> Test on one map with `python h1_port_test_map.py smg --level <map> --stage` (it backs the
> live map up to E:\HaloBackups\h1_port_test and `--restore <map>` puts it back), then the
> enemy test (Armed card): `ai_firing_profile.py --port smg` (Halo 3's ai\generic SMG
> entry, 010_jungle, verified) and a map with Grunts/Elites armed with it.
> No full ten-map rebuild until I say so. When done: catalog entry
> (make_port_catalog_h1_ports.py smg), enhancer hand-off to the "Halo enhancer project"
> session (cards, skip_cards, tag_map, card_map -- never edit the enhancer's files without
> telling it), PORTING notes, memory, `python port_backup.py --game h1`, and add what the
> pilot taught (and every tool you generalized) to H1_PORT_PLAN.md before wave A2 starts.

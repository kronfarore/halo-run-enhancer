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
(2026-10-07). The SMG pilot (A1) is DONE and tested (2026-10-07; its ten-map rebuild waits
for the user's go): read "Pilot A1: what wave A inherits" below before A2. A2 (Battle
Rifle) and A3 (Covenant Carbine, 2026-10-08) are DONE and tested too -- the ten-map
rebuild is BATCHED for all three (user's go). A4 (Beam Rifle, 2026-10-08) is DONE and tested
too (batched with them); read "A4: what the Beam Rifle taught" before A5. A5 (Spike Rifle,
2026-10-08) is DONE and tested too (batched); read "A5: what the Spike Rifle taught" before A6.

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

## Pilot A1: what wave A inherits (SMG, 2026-10-07)

PORTING.md "Halo 1: the SMG, the wave-A pilot" is the full record; `ports_h1/smg.py` is the
complete example of a MAGAZINE port (sentinel_beam.py stays the heat/battery one). A wave-A
session copies smg.py's shape and changes the numbers.

**Step 4a's numbers:** `h3_weapon_values.py <weapon>=<fp graph> ...` (the Halo 3 side,
per value, FP frames included) + `h1_role_compare.py <set>` (the Halo 1 side, time to kill;
candidate rows). Sound targets: `h1_stock_sound_levels.py "<stock sound tail>" ...`.

**Run order** (one weapon, nothing else rewritten -- `--only`):
model -> retarget `--write` + `tool animations` -> sounds `--write` -> icon (`make_icon.py`,
`add_msg_icon.py <png> <name> <reserved>`) -> `h1_pickable_weapons.py --only <key> --write`
(always AFTER tool animations: it re-applies the FP sound cues) -> catalog -> firing profile
-> `..\port_sounds.py --write` -> `port_refs_audit.py --game "Halo 1" --map <kit test copy>`
-> `port_field_audit.py --port <key>` (list 2 = 0) -> test maps.

**Test sequence that worked (4 boots):** 1 dry default (`h1_port_test_map.py <key>
--stage`), 2 the fixes, 3 dry BALANCED (`--balanced`: the patcher's own pass on the copy,
spawning with the balanced magazine), 4 Armed (`--armed grunt,elite`: the enhancer's own
pass at 100%). `--restore <level>` after. Never `--keep-kit-map` on a staging run without
rebuilding the normal level after (the pilot did it once).

**Decided with the user, now RULES for wave A** (PORTING "Balance"):
- default = the source game's own numbers; balanced = the ratio rows;
- a degenerate near-zero bound: scale it by its sibling bound's ratio;
- DUAL-WIELD CARRY RULE: x1.5 on the carry-limit ratio of a source-dual-wieldable port;
- balanced ammo pickup: the source game's pickup : initial ratio on the balanced initial;
- a missing Halo 3 mechanic is approximated in BOTH versions (the SMG's barrel climb:
  +1.6 deg full-bloom cone, through the ratio for balanced);
- dual wield itself: deferred (not reproduced, recorded).

**Things every wave-A weapon must check (observations from the pilot):**
- dual-wieldable source = TWO resource groups in the FP graph: the (group, member) fix is
  in h3_fp_pose; compare `--list` frame counts with the graph's own;
- RATE CAP: every rate 15..30 has fired 15/s (SMG 15 and 22.5, beam 30). A port above 15/s
  must be measured; the user accepted the SMG's lower balanced dps rather than move damage;
- a port label nobody carries ('sm', 'br', 'cc' ...): `firing_profile` needs
  `donor_weapon` or it gets no Armed card (closing check 8 catches it);
- the FP rig starts from the SMG's view_offset (-0.0225, 0, -0.0225), the user's pick,
  and is tuned per weapon (the beam's offset was its own);
- the template's muzzle flash: drop off-axis sprites the source lacks, judge size in game;
- a Halo 3 reticle: `reticle_thicken` 1 from the start;
- an automatic's fire sound: `shots` from the source's fire loop + release tail;
- balanced reload/swap: `anims` + a stretched reload (`stretch`, `extra_sounds`,
  `anim_sounds`) -- the patcher does the rest.

## A2: what the Battle Rifle taught (2026-10-07) -- read before A3 (the Carbine)

PORTING.md "Halo 1: the Battle Rifle, wave A2" is the full record; `ports_h1/battle_rifle.py`
is the example of a ZOOMED, BURST, PISTOL-TEMPLATE port. Everything in "Pilot A1" still
holds; the BR added:

**Test sequence (user rules):** dry default -> fixes -> dry `--balanced` -> `--armed
grunt,elite` (which now IMPLIES `--balanced --god`). A choice between mechanisms can go
in ONE boot: `--secondary <test-only tag>` puts a variant on every spawn's secondary.
**Before close-out (user):** check EVERY step: port_field_audit lists 2 AND 3 (decide each
list-3 line), a full field diff of the port against its TEMPLATE (every difference traced
to a decision), kit_tag_diff on the last writes, `port_sound_refs --map <test copy>` with
NO 'BORROW' (the template's ammo-pickup sound, item collision sound and casing eject are
easy to miss; a borrow the user keeps goes in the config's `sound_keeps` and prints KEEP), port_refs_audit, 5b on the BUILT port (a `(port)` row in the role set).

**Zoom = Halo 3's scope, ALWAYS (user: the standard procedure).** `hud['scope'] = {'chud':
<H3 chud>, 'out': <mask tag>, 'size': 1024, 'span': ..., 'aspect': 4/3, 'alpha':
'outside'}`: the chud's zoom-only widgets baked into the screen-effect mask (h1_h3_scope),
the donor's zoom crosshairs dropped, Halo 1's outside-the-lens blur kept (every stock
zoom has it). Size: Halo 1 draws ~1.09 px a texel at 1080p, so span = 369-unit ring x
size / wanted texels -- compute it from the chud's own ring, not the BR's numbers. Never
a convolution radius of 0 (it smears). Check every new chud: widgets not drawn black
(custom colour A != 0) cannot be a mask (the tool warns) -- a Covenant scope may be
coloured: then it needs crosshair overlays instead (not built yet). OBSERVATIONS from one
weapon at one resolution.

**Template choice drives hidden layouts.** The pistol template's ONE object function fed
both the muzzle-flash light and (once repointed) the on-gun counter -- constant glow.
Inspect the template's object functions / attachments / A-D exports whenever a port
changes an export (`obje_functions`, `attachment_scales` copy the AR's layout).

**Burst (Halo 1 has none):** charge 1 tick + discharge + spew; rounds ~ spew ticks /
spacing + 2 (5 at 0.2 s / 15/s, 3 at 0.15 s / 10/s); `does_not_repeat_automatically`
= a burst a pull; a CHARGE as recovery delays the first round. Observations from one
port. No burst-cycle balance row (the player's tapping sets it).

**On-gun counter:** model `numeric` (Halo 1's numeric chicago shader, the AR's), digit
place = shader permutation, the value = OUT A, limit = magazine (+ schi balance rows).

**For A3, the Covenant Carbine (reuses the zoom):** yardstick candidates pistol
(provisional), needler, sniper. Its chud is `ui\chud\carbine` (checked 2026-10-07): the
scope widgets (carbine_scope ring with extend border + mirrors, four carbine_scope_elements
pieces, two `blip`s (check their animation data), a `carbine_distortion` layer) are all colour 0 = black, BUT
their zoom-only state is on the parent COLLECTION, not on each widget -- h1_h3_scope reads
only the widget's own state and would bake NOTHING: extend `widgets()` to inherit the
collection's state first; decide the blips (a mask is static) and
the distortion layer (a refraction effect, no Halo 1 mask equivalent) with the user.
Semi-automatic 18-round magazine (no burst: Halo 3 rate, `does_not_repeat_automatically`
for its latch trigger); its own slug projectile; reticle hud_reticles #4. Template: the
yardstick's weapon unless the role table says otherwise -- then inspect its functions.

## A3: what the Covenant Carbine taught (2026-10-08) -- read before A4 (the Beam Rifle)

PORTING.md "Halo 1: the Covenant Carbine, wave A3" is the full record;
`ports_h1/covenant_carbine.py` is the example of a SEMI-AUTO, COVENANT-LOOK, METER port.
Everything in "Pilot A1" and "A2" still holds; the Carbine added:

**THE ARMED WDM RULE (user, now a RULE for every Armed port):** Weapon Damage Modifier =
base x (yardstick player dps / port player dps), default AND balanced
(`firing_profile['wdm_rule']`: base = the WDM of the carriers it fires from, the dps from
h1_role_compare 5b). Halo 3 profiles carry no WDM. Applied to the SMG and BR too. The
enhancer must list Balanced ports in the Armed spec (`balanced`) -- handed off.
**Measurement runs** (when a number must be felt, not computed): `h1_port_test_map
--grunt/--elite <actv>` (every Grunt/Elite one variant) + `--armed elite --mortal`
(balanced, no god); the user's stopwatch (time to die x5) is the instrument --
`h1_vitality_live.py` is too slow at its moved-triple step (fix before use).

**Close-out tool:** `h1_port_template_diff.py <key>` = the full field diff of every tag
against what it was copied from (pairs from the config; Halo 1's kit_tag_diff) -- it found
the Carbine's orphan shader. port_field_audit now reads shaders and HUD flag blocks.

**Step 4a:** show the DAMAGE TYPE against Halo 1's materials (`h1_role_compare` rows with
`damage_tags` of another weapon): Halo 3's `plasma_fast` has no shield bonus, so the
Carbine kept a bullet table + Halo 3's differences. Check `h3_weapon_values`' damage group,
then the Halo 3 globals damage table (out/h3_export/_g.txt).

**Scope (standard, h1_h3_scope):** collection state inherited; `per_widget` (drop / scale /
blur / blur_inside); animated widgets at scale 0 need a scale; DISTORTION widgets become
Halo 1 blur only by decision; the BR's span/aspect were NOT general -- the Carbine needed
x0.8 aspect and 80% size: preview first (`h1_h3_scope.py <chud> --port <key> --screen
out.png` = the mask as Halo 1 draws it), then 2 variants in ONE boot (`h1_scope_variant.py
<key> b --aspect ..` + `--secondary`, `--clean` after; a test-only copy: weapon + HUD + mask under `<weapon dir>\test`, deleted after).
**Halo 3 meter shaders on the gun** (`meter_map` / `meter_value`): `h1_h3_weapon_model`
`meters` -- channels SWAP, gamma-spaced steps -> `steps` (rank remap), the AR's function
layout for the out that drives them. Any H3 shader with meter_* parameters is one.
**Glow:** thin illum lines need `illum_dilate` (no bloom in Halo 1) and often a set `glow`.
**Covenant look on a bullet template:** `sound_effects` `copy_from` (the plasma pistol's
green fire effect), bullet `attachments_from` + `material_responses_from`, the muzzle
light by `fields` (attachments.0). Screen flash: Halo 3's shielded response
(H1_SCREEN_FLASH.md, the screen-flash session).
**Semi-auto rate:** the player's tapping sets it (~3.8/s default, ~6.5/s balanced
measured) -- the 15/s cap observation stays untested.

**For A4, the Beam Rifle:** yardstick candidates Sniper Rifle (provisional; Halo 3's beam
rifle = the sniper's 80 damage, 1200 wu/s, range 500, aim 1/10 4/14 -- only the rate 0.4 vs
0.7 s, heat 0.7 a shot, age 0.1 = 10 shots a battery and the damage group `plasma_fast` vs
`bullet_fast` differ), Plasma Pistol (heat + battery), Sentinel Beam (H1 derived). Its
chud `ui\chud\beam_rifle` (checked 2026-10-08): zoom state 6 (lvl 1 AND 2), and TWO
widget sets (scale 1.2 and 0.85 -- most likely fullscreen vs splitscreen: `widgets()` does
not read resolution/screen states yet, filter before baking); in-scope HEAT and BATTERY
meters (`meter gradient`, animated) and flash widgets -- a mask is static: decide them with
the user (drop, or Halo 1 HUD meters); a `distortion and blur` layer again. Heat: the
Sentinel Beam's lessons (PORTING "Halo 1: the Sentinel Beam"); two zoom levels.

## A4: what the Beam Rifle taught (2026-10-08) -- read before A5 (the Spike Rifle)

PORTING.md "Halo 1: the Beam Rifle, wave A4" is the full record; `ports_h1/beam_rifle.py` is
the example of a HEAT + BATTERY port on a template that is NOT its yardstick, and of GLOW.
Everything in "Pilot A1", "A2" and "A3" still holds; the Beam Rifle added:

**Run 4b BEFORE BOOT 1 (rule now)** -- and decide every FLAGS line of list 3 by flag NAME (the
audit cannot compare them across games; the beam rifle's 'magnetize only when zoomed' was found
only in the final check).
**4b itself:** `port_field_audit.py --port <key>` lists 2-5 and
`h1_port_template_diff.py <key>` before the first test, not at close-out. When the template
is not the yardstick, list 5 holds the yardstick's flags the template lacks (the sniper's
`use error when unzoomed` cost a boot) and the template diff shows behaviour the template
brought along (the bolt's material RESPONSES turned overpenetration into 'disappear').
Copy only what you need from a donor (`material_effects_from`, not `material_responses_from`).

**Step 4a:** `h3_weapon_values.py` prints heat, the CAMPAIGN battery (Halo 3 has a campaign
age field beside the multiplayer one -- the beam rifle 0.05 vs 0.1) and zoom; Halo 1 has ONE
heat loss where Halo 3 has two -- show both, judge in game (`h1_scope_variant.py --field`
puts any weapon field on the test secondary). `h1_role_compare` `heat_sim` waits out
overheats for a tapped weapon. Halo 1 enemies DO carry some weapons the plan said they do not
(sniper: Flood combat Elite, armoured Marines): list the carriers before choosing a donor.

**Look (observations, PORTING):** render the FP pose coloured by material (`fp_material_view.py
<key> [--illum <H3 bitmap>]`) before guessing
which material glows (Halo 3 shader templates encode the blend mode: `_..._1_0_1` additive);
GLOW = additive chicago + a texture with falloff (Halo 3's own mask where it has one) +
glow cards for small pieces (`glow_shaders`, `glow_cards`); never lights / lens flares /
attachments for first-person looks (they draw at the hidden third-person gun); impact colour
= the projectile's change colour; a muzzle light belongs in the firing effect; a Halo 3
`*_first_person_fire` sound is only a layer -- mix it with the shot; a borrowed contrail may
carry wind physics. Scope: `h1_h3_scope` bakes the FULLSCREEN widget set (window state).

**Step 11:** `donor_variant` in the firing profile pins one carrier for every slot.
**New user rule** (enhancer session, every Armed card): Grunts with a two-handed weapon fire
at half rate (heavy support excepted); Jackals with one lose the arm shield -- for A5 the
enhancer's classification decides; check it is in place before the Armed boot.
**Older ports' BORROWs: CLOSED 2026-10-08** (own drop/ammo/overheat where the source game has
one; the rest the user KEPT on purpose -- `sound_keeps` in ports_h1/<key>.py, printed KEEP by
port_sound_refs). Rule unchanged: a new port closes with NO 'BORROW'; a KEEP needs the user.

**For A5, the Spike Rifle:** yardstick candidates Needler (provisional) and Assault Rifle. It is
DUAL-WIELDABLE: two resource groups in the FP graph (Pilot A1), the DUAL-WIELD CARRY RULE x1.5,
and the 15/s cap observation if its rate exceeds it. A slow ARCING spike (gravity) -- Halo 1's
projectiles have air gravity: compare the drop. A blade melee (Halo 3's spiker blades): its
melee damage tag; no lunge. Its chud and reticle: check for meter shaders on the gun (the
Carbine's `meters`) and for any additive / luminous material (render the FP pose by material
FIRST). Template: the yardstick's weapon unless the role table says otherwise -- then run 4b and
the template diff before boot 1.

## A5: what the Spike Rifle taught (2026-10-08) -- read before A6 (the Mauler)

PORTING.md "Halo 1: the Spike Rifle, wave A5" is the full record; `ports_h1/brute_spiker.py`
is the example of a DUAL-WIELDABLE automatic with a PHYSICAL projectile (arc, ricochet, a stuck
spike) and of the GLOW SPOT recipe. Everything in "Pilot A1" to "A4" still holds; the Spiker
added:

**New user rules:**
- THE HIT-EFFECT RULE v2 (PORTING Balance, closing check 9): the port's shield-hit effect on
  the player (its projectile's response for material #22) keeps the donor's load up to 3.5
  rounds/s, above x (3.5 / rate)^3.19, size-scaled -- `h1_hit_effect_load.py`, `bullet.
  impact_thin` {'materials': [22], 'thin': {}, 'rate': max(default, balanced)}. A pellet weapon
  counts pellets x rate (the tool does): CHECK the Mauler's number with the user.
- FLASHLIGHT sound: the game's own when the source has none (port_sound_refs prints KEEP).
- ARMED TEST: Jackals ride the FIRST DROPSHIP (`DROPSHIP_JACKALS` in h1_port_test_map; a30 =
  lz_search/far_grunt). Another level needs its entry first.

**Process (observations):**
- 4b + the template diff BEFORE boot 1 caught the AR bullet's timer-on-first-bounce (it would
  have killed every ricochet). Read the TEMPLATE's projectile detonation block for any port whose
  projectile bounces, sticks or rests.
- Glow: run `fp_material_view.py <key> --illum <H3 illum> --threshold 16 --texels 24` FIRST
  (exact coverage, the lit texels drawn on the pose) and decode each Halo 3 shader's
  self_illum_color / intensity (BGRA bytes in the function data). Tiny lights = `glow_spots`.
- A Halo 3 MODEL PARTICLE (stuck spikes, shell casings...) becomes a projectile / object model
  via `h3_rm_to_jms.convert_particle_model` + `extra_models`.
- The H3 export cache is keyed by PATH now (generic names like fx\projectile.effect collided).

**For A6, the Mauler (`pistol\excavator\excavator`):** yardstick candidates Shotgun
(provisional) and Pistol. Halo 3: 5 rounds, WHOLE-magazine reload (55 fr; the shotgun loads
shell by shell -- a reload-style difference to approximate or keep), fire recovery 0.75 s
(shotgun 1.0), 7 damage a pellet with a 1.5 LOWER bound (falloff -- read the damage effect's
range; the shotgun 10 / 3), range 8 (shotgun 6), aim 8/7 16/7, both bullet_slow, `cut_melee`
(the Spiker's blade), dual-wieldable (carry rule x1.5, two resource groups). The barrel's error
fields read 0 and projectiles per shot 1 in h3_weapon_values -- find the PELLET count and spread
(barrel distribution / a second block) before the ratio table. One-handed: `hands` 'one' (Armed
rule: no Grunt half rate, Jackals keep the shield). Hit-effect rule: pellets x rate.

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
| A1 | **SMG** (pilot) -- DONE 2026-10-07 | the first plain magazine gun on this pipeline: reload, ammo pickup (step 6), magazine HUD meter |
| A2 | **Battle Rifle** -- DONE 2026-10-07 | burst fire, zoom + scope HUD (memory halo-zoom-ui) -- see "A2: what the Battle Rifle taught" |
| A3 | **Covenant Carbine** -- DONE 2026-10-08 | zoom on a Covenant weapon, its own projectile -- see "A3: what the Carbine taught" |
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
**BATCHED (user, 2026-10-07):** the rebuild waits until a few more weapons are built (in
other sessions); then, for every port in the batch: residency on all ten BUILT maps,
`port_refs_audit.py` + `port_sound_refs.py --game "Halo 1"` on the deployed maps, and the
spawn check in game. The SMG (done, tested on a30) is the first in that batch.

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

### The Battle Rifle (wave A2), filled in

> Port the Battle Rifle into Halo 1 (H1_PORT_PLAN.md, wave A, #A2). Source: Halo 3,
> `objects\weapons\rifle\battle_rifle\battle_rifle` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md ("Phase 0: DONE" and "Pilot A1: what wave A inherits"
> first), PORTING.md ("What ported actually means" steps 0-11 and 5b, the Halo 1 sections,
> "Halo 1: the SMG, the wave-A pilot") and memory h1-smg-pilot, h1-port-phase0,
> halo-zoom-ui-reach-unwired, h1-weapon-into-map, halo-port-own-messages, h1-fmod-bank-sounds,
> port-findings-are-observations, shared-worktree-commits. `ports_h1/smg.py` is the complete
> magazine-port example: copy its shape into `ports_h1/battle_rifle.py` and edit only that file.
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Wave-A rule: DEFAULT = Halo 3's own numbers, BALANCED = the ratio rows -- so the pick sets
> the balanced build. Candidates (battle_rifle.py, yardstick.candidates): provisional PISTOL
> (magazine, scoped, precision mid-range -- the magnum's role), alternatives ASSAULT RIFLE
> (the SMG's yardstick; a magazine bullet gun) and SNIPER RIFLE (scoped precision), no
> direct yardstick. Lay them side by side per value (damage per round AND per second, rate
> and burst timing, magazine / reserve, reload, error / spread, range / velocity, zoom, aim
> assist, melee) with `h3_weapon_values.py` (H3 side) and `h1_role_compare.py` (add a
> 'battle_rifle' set; time to kill vs the peers Pistol, Assault Rifle, Sniper Rifle). I pick;
> record it in yardstick['pick'] / ['reason'] and PORTING.
>
> Reserved (do not take any other number): pickup messages 55/56 ("Picked up a battle rifle"
> / "Picked up %d rounds for battle rifle"); hud_msg_icons 30 is the SMG's -- yours is 31
> (+ _r twin); hud_reticles 20 (+ _r, `reticle_thicken` 1 from the start); label `br`,
> taught to characters\cyborg from `ar`; sounds under `sound\weapons\battle_rifle_port`
> (never under sound\sfx); weapon folder `weapons\battle rifle`; catalog name `Battle Rifle`.
>
> What the BR tests first on this pipeline:
> - **the 3-round BURST** -- Halo 1 has no burst trigger: APPROXIMATE it (never skip) and
>   record what it does not reproduce. Mind the pilot's 15/s RATE CAP observation (every
>   rate 15..30 fired 15/s): Halo 3's burst spacing is faster than one round per two ticks,
>   so measure what Halo 1 really fires before choosing (e.g. 3 projectiles per shot with a
>   small spread vs. a capped auto burst); lay the options out for me;
> - **ZOOM + scope HUD**: Halo 1's own zoom (the pistol's 2x is the model), and the scope
>   overlay / reticle while zoomed (memory halo-zoom-ui-reach-unwired);
> - NOT dual-wieldable in Halo 3: expect ONE resource group in the FP graph (compare
>   `--list` frame counts with the graph's own), and no dual-wield carry rule.
>
> Run order, test sequence and closing checks: exactly "Pilot A1" (model -> retarget +
> tool animations -> sounds -> icon -> `h1_pickable_weapons.py --only battle_rifle --write`
> -> catalog -> firing profile -> port_sounds -> refs + field audits -> test maps). The FP
> rig starts from the SMG's view_offset (-0.0225, 0, -0.0225). Step 11: `br` has no carrier,
> so `firing_profile` needs a `donor_weapon` (as smg.py has) or there is no Armed card.
> Test with `h1_port_test_map.py battle_rifle --stage` (dry default, fixes, `--balanced`,
> `--armed grunt,elite`), `--restore <level>` after.
> NO ten-map rebuild: it is BATCHED (the SMG and this weapon go in the same batch, on my
> go). When done: catalog entry, enhancer hand-off to the "Halo enhancer project" session,
> PORTING notes, memory, `python port_backup.py --game h1`, and what the BR taught (burst,
> zoom) added to the plan before A3 (the Covenant Carbine, which reuses the zoom work).

### The Covenant Carbine (wave A3), filled in

> Port the Covenant Carbine into Halo 1 (H1_PORT_PLAN.md, wave A, #A3). Source: Halo 3,
> `objects\weapons\rifle\covenant_carbine\covenant_carbine` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md ("Phase 0: DONE", "Pilot A1: what wave A inherits" and
> "A2: what the Battle Rifle taught" first -- its last paragraph is written for THIS weapon),
> PORTING.md ("What ported actually means" steps 0-11 and 5b, the Halo 1 sections, "Halo 1:
> the SMG, the wave-A pilot", "Halo 1: the Battle Rifle, wave A2") and memory
> h1-battle-rifle-port, h1-armed-test-balanced-god, h1-smg-pilot, h1-port-phase0,
> halo-zoom-ui-reach-unwired, h1-weapon-into-map, halo-port-own-messages, h1-fmod-bank-sounds,
> port-findings-are-observations, shared-worktree-commits. `ports_h1/battle_rifle.py` is the
> example of a zoomed, pistol-template port: copy its shape into
> `ports_h1/covenant_carbine.py` and edit only that file (plus any shared tool you generalize,
> e.g. h1_h3_scope.py).
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Wave-A rule: DEFAULT = Halo 3's own numbers, BALANCED = the ratio rows. Candidates
> (covenant_carbine.py, yardstick.candidates): provisional PISTOL (semi-auto magazine, 2x
> zoom, instant slug -- the precision mid-range role; the BR's pick), alternatives NEEDLER
> (the Covenant magazine weapon) and SNIPER RIFLE, no direct yardstick (Elites carry it in
> Halo 3; Halo 1's Elites carry plasma weapons). Lay them side by side per value (damage
> per round AND per second, rate, magazine / reserve, reload, error / spread, range /
> velocity, zoom, aim assist, melee) with `h3_weapon_values.py` and `h1_role_compare.py` (a
> 'covenant_carbine' set; time to kill vs Pistol, Sniper Rifle, Needler, and the BR as a
> port peer). Damage type matters here: Halo 3's carbine slug vs Halo 1's material table
> (shields / Elite armour) -- show it. I pick; record it in yardstick['pick'] / ['reason']
> and PORTING. Template: the yardstick's weapon unless the role table says otherwise -- then
> inspect its object functions / attachments / A-D exports (the BR's pistol-template trap).
>
> Reserved (do not take any other number): pickup messages 57/58 ("Picked up a covenant
> carbine" / "Picked up %d rounds for covenant carbine"); hud_msg_icons 32 (+ _r twin);
> hud_reticles 21 (+ _r, `reticle_thicken` 1; the source reticle is Halo 3's hud_reticles
> #4); label `cc`, taught to characters\cyborg from `ar`; sounds under
> `sound\weapons\covenant_carbine_port` (never under sound\sfx); weapon folder
> `weapons\covenant carbine`; catalog name `Covenant Carbine`.
>
> What the Carbine tests first:
> - **the scope from a COLLECTION-state chud** (`ui\chud\carbine`): its scope widgets are
>   black (mask-able) but their zoom-only state sits on the parent collection, so
>   h1_h3_scope.widgets() must inherit the collection's state first or it bakes nothing.
>   Decide WITH me: the two `blip`s (a mask is static -- check their animation data) and
>   the `carbine_distortion` layer (a refraction effect Halo 1 has no mask equivalent for:
>   approximate or drop, recorded). Zoom = Halo 3's scope, always; keep Halo 1's
>   outside-the-lens blur; compute the span from this chud's own ring;
> - a COVENANT magazine weapon: semi-auto 18 rounds (`does_not_repeat_automatically` for its
>   latch trigger, Halo 3's rate -- mind the 15/s cap observation), its own slug projectile
>   and damage effect (step 3), the ammo pickup (step 6: which Halo 1 item tops up a
>   Covenant magazine weapon -- lay the options out);
> - not dual-wieldable: one resource group expected in the FP graph (check `--list`).
>
> Step 11: `cc` has no carrier, so `firing_profile` needs a `donor_weapon` (as smg.py /
> battle_rifle.py have) or there is no Armed card; Halo 3's ai\generic carbine entry
> (010_jungle) is verified. Run order and closing checks: "Pilot A1" + the BR's close-out
> list (port_field_audit lists 2 AND 3, full field diff against the template, kit_tag_diff,
> port_sound_refs with NO 'BORROW', port_refs_audit, 5b on the built port). The FP rig starts
> from the BR's view_offset (-0.0225, 0, -0.0125). Test with
> `h1_port_test_map.py covenant_carbine --stage`: dry default, fixes, `--balanced`, then
> `--armed grunt,elite` (implies balanced + god); `--restore <level>` after.
> NO ten-map rebuild: BATCHED with the SMG and the BR, on my go. When done: catalog entry,
> enhancer hand-off to the "Halo enhancer project" session, PORTING notes, memory,
> `python port_backup.py --game h1`, and what the Carbine taught added to the plan before
> A4 (the Beam Rifle: heat + zoom, the Sentinel Beam's heat lessons).

### The Beam Rifle (wave A4), filled in

> Port the Beam Rifle into Halo 1 (H1_PORT_PLAN.md, wave A, #A4). Source: Halo 3,
> `objects\weapons\rifle\beam_rifle\beam_rifle` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md ("Phase 0: DONE", "Pilot A1", "A2: what the Battle
> Rifle taught" and "A3: what the Covenant Carbine taught" first -- its last paragraph is
> written for THIS weapon), PORTING.md ("What ported actually means" steps 0-11 and 5b, the
> Halo 1 sections, "Halo 1: the Sentinel Beam" (heat), "Halo 1: the SMG", "the Battle
> Rifle", "the Covenant Carbine", and "Balance" incl. the ARMED WDM RULE) and memory
> h1-covenant-carbine-port, h1-battle-rifle-port, h1-armed-test-balanced-god,
> h1-smg-pilot, h1-port-phase0, halo-zoom-ui-reach-unwired, h1-weapon-into-map,
> halo-port-own-messages, h1-fmod-bank-sounds, port-findings-are-observations,
> shared-worktree-commits. `ports_h1/covenant_carbine.py` is the example of a zoomed,
> Covenant-look port; `ports_h1/sentinel_beam.py` the heat/battery one: copy their shape
> into `ports_h1/beam_rifle.py` and edit only that file (plus any shared tool you
> generalize, e.g. h1_h3_scope.py).
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Wave-A rule: DEFAULT = Halo 3's own numbers, BALANCED = the ratio rows. Candidates:
> provisional SNIPER RIFLE (Halo 3's beam rifle shares its damage, speed, range and aim;
> differs in rate, heat + battery and damage group), alternatives PLASMA PISTOL (heat +
> battery) and SENTINEL BEAM (Halo 1's numbers are derived: a chained ratio). Lay them
> side by side per value (damage per round AND per second, rate, heat per shot / shots to
> overheat / vent, battery, error, range / velocity, zoom levels, aim assist, melee) with
> `h3_weapon_values.py` and `h1_role_compare.py` (a 'beam_rifle' set with a sustained-fire
> table; time to kill vs Sniper, Plasma Pistol, Sentinel Beam). Damage type: Halo 3's
> `plasma_fast` vs the sniper bullet's materials (Flood 0.05!) -- show it. I pick; record
> it in yardstick['pick'] / ['reason'] and PORTING. Template: the yardstick's weapon unless
> the role table says otherwise -- then inspect its object functions / attachments / A-D
> exports (heat display, battery: the BR's template trap).
>
> Reserved: pickup messages 59/60; hud_msg_icons 33 (+ _r twin); hud_reticles 22 (+ _r,
> `reticle_thicken` 1); label `bm` taught to characters\cyborg from `sr`; sounds under
> `sound\weapons\beam_rifle_port` (never under sound\sfx); weapon folder
> `weapons\beam rifle`; catalog name `Beam Rifle`.
>
> What the Beam Rifle tests first:
> - the scope from `ui\chud\beam_rifle`: TWO widget sets (scale 1.2 / 0.85, likely
>   fullscreen vs splitscreen -- filter by screen state in h1_h3_scope before baking), two
>   zoom levels (state 6), in-scope HEAT and BATTERY meters + flash widgets (a mask is
>   static: decide WITH me), a `distortion and blur` layer (the Carbine's blur_inside
>   rule). Variants in ONE boot (`--secondary`) for size / shape;
> - HEAT + BATTERY on a Halo 1 weapon (the Sentinel Beam's lessons: heat cools only while
>   not firing; the tick-quantised rate); the overheat looping sound;
> - any Halo 3 meter shader on the gun (`meters`, channels swap, gamma steps).
>
> Step 11: `bm` has no carrier: `firing_profile` needs a `donor_weapon` (choose with me:
> no Halo 1 enemy carries the sniper) AND a `wdm_rule` (the ARMED WDM RULE). Run order and
> closing checks: "Pilot A1" + the BR's close-out list (port_field_audit lists 2 AND 3,
> full field diff against the template, kit_tag_diff, port_sound_refs with NO 'BORROW',
> port_refs_audit, 5b on the built port). FP rig from the BR's view_offset (-0.0225, 0,
> -0.0125). Test with `h1_port_test_map.py beam_rifle --stage`: dry default, fixes,
> `--balanced`, then `--armed grunt,elite` (implies balanced + god); `--restore <level>`.
> NO ten-map rebuild: BATCHED with the SMG, BR and Carbine, on my go. When done: catalog
> entry, enhancer hand-off to the "Halo enhancer project" session, PORTING notes, memory,
> `python port_backup.py --game h1`, and what the Beam Rifle taught added to the plan
> before A5 (the Brute Spiker).

### The Spike Rifle (wave A5), filled in

> Port the Spike Rifle (Brute Spiker) into Halo 1 (H1_PORT_PLAN.md, wave A, #A5). Source:
> Halo 3, `objects\weapons\rifle\spike_rifle\spike_rifle` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md ("Phase 0: DONE", "Pilot A1", "A2", "A3" and "A4: what
> the Beam Rifle taught" first -- its last paragraph is written for THIS weapon), PORTING.md
> ("What ported actually means" steps 0-11 and 5b, the Halo 1 sections -- the SMG (dual-wield
> rules), the Covenant Carbine and the Beam Rifle (4b before boot 1, glow) -- and "Balance"
> incl. the DUAL-WIELD CARRY RULE and the ARMED WDM RULE) and memory h1-beam-rifle-port,
> h1-covenant-carbine-port, h1-smg-pilot, h1-armed-test-balanced-god, h1-port-phase0,
> h1-weapon-into-map, halo-port-own-messages, h1-fmod-bank-sounds,
> port-findings-are-observations, shared-worktree-commits. `ports_h1/smg.py` is the example
> of a dual-wieldable automatic, `ports_h1/beam_rifle.py` of a template that is not the
> yardstick and of glow: copy their shape into `ports_h1/brute_spiker.py` and edit only that
> file (plus any shared tool you generalize).
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Wave-A rule: DEFAULT = Halo 3's own numbers, BALANCED = the ratio rows. Candidates:
> provisional NEEDLER, alternative ASSAULT RIFLE. Lay them side by side per value (damage per
> round AND per second, rate, magazine / carry, reload, error, velocity / gravity / range,
> aim assist, melee) with `h3_weapon_values.py` and `h1_role_compare.py` (a 'brute_spiker'
> set; time to kill vs Needler, AR, Plasma Rifle). Damage type against Halo 1's materials.
> I pick; record it in yardstick['pick'] / ['reason'] and PORTING. Then run step 4b
> (`port_field_audit.py --port brute_spiker`) and `h1_port_template_diff.py` BEFORE boot 1.
>
> Reserved: pickup messages 61/62; hud_msg_icons 34 (+ _r twin); hud_reticles 23 (+ _r,
> `reticle_thicken` 1); label `sk` taught to characters\cyborg from `hp`; sounds under
> `sound\weapons\spiker_port` (never under sound\sfx); weapon folder `weapons\spiker`;
> catalog name `Spike Rifle`.
>
> What the Spike Rifle tests first: dual wield (two resource groups; carry rule x1.5); an
> arcing spike (gravity) against Halo 1's projectile physics; the blade melee; any luminous /
> additive material (render the FP pose by material first). Before the Armed boot: check the
> enhancer's new Armed rule (Grunts: two-handed = half rate; Jackals: no arm shield) is in
> place and how it classifies the spiker.
>
> Step 11: list Halo 1's carriers of the chosen donor weapon first; `firing_profile` needs a
> `donor_weapon` (+ `donor_variant` if one carrier should serve every slot) AND a `wdm_rule`.
> Test with `h1_port_test_map.py brute_spiker --stage`: dry default, fixes, `--balanced`, then
> `--armed grunt,jackal,elite` (implies balanced + god; `--grunt <jackal variant>` when the
> level has no Jackals); `--restore <level>`. NO ten-map rebuild: BATCHED with the SMG, BR,
> Carbine and Beam Rifle, on my go. When done: catalog entry, enhancer hand-off to the "Halo
> enhancer project" session, PORTING notes, memory, `python port_backup.py --game h1`, and
> what the Spike Rifle taught added to the plan before A6 (the Brute Mauler).

### The Mauler (wave A6), filled in

> Port the Mauler (Brute Mauler) into Halo 1 (H1_PORT_PLAN.md, wave A, #A6). Source: Halo 3,
> `objects\weapons\pistol\excavator\excavator` (H3EK).
> Read sprint_toolkit/H1_PORT_PLAN.md ("Phase 0: DONE", "Pilot A1", "A2", "A3", "A4" and "A5: what
> the Spike Rifle taught" first -- its last paragraph is written for THIS weapon), PORTING.md
> ("What ported actually means" steps 0-11 and 5b, closing checks 1-9, the Halo 1 sections -- the
> SMG (dual-wield rules) and the Spike Rifle (blade melee, physical projectiles, glow spots, the
> hit-effect rule) -- and "Balance" incl. the DUAL-WIELD CARRY RULE, the ARMED WDM RULE and THE
> HIT-EFFECT RULE) and memory h1-spike-rifle-port, h1-beam-rifle-port, h1-smg-pilot,
> h1-armed-test-balanced-god, h1-hit-effect-rule, port-flashlight-sound-rule, h1-port-phase0,
> h1-weapon-into-map, halo-port-own-messages, h1-fmod-bank-sounds,
> port-findings-are-observations, shared-worktree-commits. `ports_h1/brute_spiker.py` is the
> example of a dual-wieldable one-hander with a blade; copy its shape into
> `ports_h1/brute_mauler.py` and edit only that file (plus any shared tool you generalize).
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Wave-A rule: DEFAULT = Halo 3's own numbers, BALANCED = the ratio rows. Candidates:
> provisional SHOTGUN, alternative PISTOL. First find the Mauler's PELLET count and spread
> (h3_weapon_values shows projectiles per shot 1 and error 0 -- they live elsewhere). Lay them
> side by side per value (damage per pellet AND per shot, falloff lower bound and its range,
> rate / fire recovery, magazine / carry, reload (whole magazine vs the shotgun's shell by
> shell), spread, velocity / range, aim assist, melee) with `h3_weapon_values.py` and
> `h1_role_compare.py` (a 'brute_mauler' set; time to kill vs Shotgun, Pistol, Energy Sword).
> Damage type against Halo 1's materials. I pick; record it in yardstick['pick'] / ['reason']
> and PORTING. Then run step 4b (`port_field_audit.py --port brute_mauler`) and
> `h1_port_template_diff.py` BEFORE boot 1.
>
> Reserved: pickup messages 63/64; hud_msg_icons 35 (+ _r twin); hud_reticles 24 (+ _r,
> `reticle_thicken` 1); label `ml` taught to characters\cyborg from `sg`; sounds under
> `sound\weapons\mauler_port` (never under sound\sfx); weapon folder `weapons\mauler`; catalog
> name `Mauler`.
>
> What the Mauler tests first: a ONE-HANDED pellet weapon (two resource groups; carry rule
> x1.5; the 3P pose class -- `sg` is two-handed: check the label against the Spiker's `hp`);
> the whole-magazine reload against Halo 1's shotgun reload; damage falloff; the blade melee
> (cut_melee); glow (`fp_material_view --illum --texels` first); the hit-effect rule with
> pellets. Before the Armed boot: the enhancer's `hands` for the Mauler ('one').
>
> Step 11: list Halo 1's carriers of the chosen donor weapon first; `firing_profile` needs a
> `donor_weapon` (+ `donor_variant` if one carrier should serve every slot) AND a `wdm_rule`.
> Test with `h1_port_test_map.py brute_mauler --stage`: dry default, fixes, `--balanced`, then
> `--armed grunt,jackal,elite` (implies balanced + god; Jackals ride the first dropship on
> a30); `--restore <level>`. NO ten-map rebuild: BATCHED with the SMG, BR, Carbine, Beam Rifle
> and Spike Rifle, on my go. When done: catalog entry, enhancer hand-off to the "Halo enhancer
> project" session, PORTING notes, memory, `python port_backup.py --game h1`, and what the
> Mauler taught added to the plan before A7 (the Brute Shot).

# Halo 2: every missing weapon (plan, 2026-10-20)

The user's master list (`tool\Halo Weapons Spreadsheet (CE - Infinite).ods`, Sheet2, re-read
2026-10-20) marks **20 weapons missing from Halo 2**, plus the **Gravity Hammer** marked 'y'
(it exists, but only as Tartarus's; it needs work). Halo 1's port plan (H1_PORT_PLAN.md, all 25
done 2026-10-17) is the template; this file is its Halo 2 counterpart. Rules (user, 2026-10-20):

- **One weapon per session**, handed over with the prompt at the end of this file.
- **The PILOT = the Assault Rifle (Halo 3 source), run ALONE first**; then parallel sessions,
  scaled up slowly ("start with a single weapon and then slowly scale the parallel session
  number up").
- **Residency: every port in ALL 13 campaign levels, 01b_spacestation included** (its old test
  is backed up; 01b may be used for tests -- memory halo2-do-not-test-on-01b, LIFTED).
- A mechanic Halo 2 lacks is **APPROXIMATED, never skipped** (record what is lost).
- Each weapon's **YARDSTICK is decided WITH the user at its step 4a** (phase 0 only proposes).
- A finding from one port is an **OBSERVATION until a second port confirms it** (memory
  port-findings-are-observations).
- Tests in **CLASSIC** (a rebuilt Halo 2 map is a classic-side build; memory halo2-loose-tag-format).

Done before this plan: the **SAW** (Halo 4 source on the cut GPMG, 2026-09-23/24; PORTING.md
"## Halo 2"). Phase 0 (this setup) is **DONE (2026-10-20)**; next: the AR pilot (A1).

## Phase 0: DONE (2026-10-20)

What phase 0 set up, and how a weapon session uses it. Do not re-plan it; use it. The research
notes behind each section are kept in `sprint_toolkit\h2_phase0\` (fp_skeletons, ai_armed,
yardsticks -- each with its commands and scratch scripts).

### 0.1 Capacity + residency

**Halo 2's limits, read from tool.exe itself** (H2EK `tool.exe` is 32-bit; its tag block
definitions carry the maximum counts -- `scenario_weapon_block` and friends -- and its cache
build the size check):

| limit | value | where we are (13 levels) |
|---|---|---|
| tag data ("total tag size") | **NO cap for a campaign cache** -- tool's only check (`### TAG DATA SIZE EXCEEDS MAXIMUM FOR THIS CACHE FILE TYPE`, 0x6D4D4D) is armed with 0x3200000 = 50 MiB for one shared cache type only; campaign builds set -1 | 35.6 (08a) - 75.4 MiB (07a) |
| weapon PLACEMENTS per scenario | **128** (MAXIMUM_WEAPON_DATUMS_PER_SCENARIO) | **01b 128 = AT the cap**, 06a 121, 04a 109, 04b 88 ... 08b 30 |
| weapon PALETTE per scenario | 256 | 20 (04b, 08a) - 33 (01b) |
| equipment placements / palette | 256 / 256 | (not used by ports) |
| file size | not checked by tool; MCC loads 491-802 MiB maps today | 491 (08a) - 802 MiB (08b) |
| MCC runtime (tag memory, geometry / texture caches) | UNKNOWN -- the size test map below is staged for a boot | |

Per level (tool's own lines, the 2026-10-05 builds; `h2_size_test_map.py`'s parser):

| level | tags MiB | geometry | bitmaps | sounds | file MiB | placements | palette |
|---|---|---|---|---|---|---|---|
| 01b_spacestation | 46.5 | 59.1 | 99.1 | 329.4 | 647.6 | **128** | 33 |
| 03a_oldmombasa | 39.7 | 69.7 | 104.8 | 343.3 | 651.8 | 71 | 27 |
| 03b_newmombasa | 35.9 | 65.8 | 106.2 | 372.9 | 678.6 | 47 | 24 |
| 04a_gasgiant | 41.1 | 41.2 | 81.9 | 316.3 | 504.9 | 109 | 23 |
| 04b_floodlab | 39.7 | 59.2 | 81.5 | 388.2 | 602.0 | 88 | 20 |
| 05a_deltaapproach | 35.8 | 54.9 | 96.8 | 329.0 | 620.9 | 57 | 23 |
| 05b_deltatowers | 37.3 | 42.1 | 93.5 | 341.8 | 614.7 | 76 | 22 |
| 06a_sentinelwalls | 46.0 | 62.5 | 99.7 | 342.1 | 653.3 | 121 | 23 |
| 06b_floodzone | 46.0 | 62.2 | 96.8 | 379.3 | 652.0 | 43 | 22 |
| **07a_highcharity** | **75.4** | **80.1** | 99.8 | 393.1 | 751.6 | 38 | 23 |
| 07b_forerunnership | 42.9 | 44.3 | 84.9 | 337.7 | 534.5 | 49 | 22 |
| 08a_deltacliffs | 35.6 | 46.3 | 82.6 | 268.0 | 491.3 | 54 | 20 |
| **08b_deltacontrol** | 51.8 | 63.6 | 106.0 | **498.4** | **802.5** | 30 | 24 |

**RESIDENCY MECHANISM -- DECIDED AND PROVED: a PALETTE ENTRY in each level's
`scenario_weapons_resource`, NO placement.** Halo 2 splits placements out of the scenario into
resource tags tool stomps the scenario with, so the weapons resource is the authority (memory
halo2-loose-tag-format). Found on the way: someone (the 2026-10-01..04 Sapien work) already gave
EVERY level a palette entry + one not-automatic placement (flags 0x101) for every weapon in the
game -- the SAW and the GPMG included -- which is why the SAW is resident in all 13 shipped maps
(08b has no SAW starting profile and still carries it). Halo 1's "palette entry + one
resident-only placement" cannot scale here: 01b is AT tool's 128-placement cap. So the question
was whether a palette entry ALONE builds a weapon in -- Halo 1 never proved it (memory
h1-weapon-into-map, "unproven"). **Proved 2026-10-20** (`h2_size_test_map.py build --level 07a
--count 21`): 21 stand-in ports added to 07a's weapons palette with NO placement -> all 21 weapon
tags resident in the built map. The starting-profile route (the SAW's first test, h2_saw_place.py)
also pulls a weapon in, but profiles are the enhancer's (halo_patch arms profiles 0/1) and are
not "every level". The enhancer only needs the TAG resident: its Halo 2 placer
(`halo_patch._h2_place_at_markers` / `_h2_palette`) appends its own CACHE palette entry for any
resident weapon. `h2_port_residency.py <key> --write` adds the entry to all 13; `--check <maps>`
verifies built maps; `--show` lists palettes / placements.

**Stand-ins: the SAW, 21 times.** `h2_size_test_map.py make --count 21` copies the SAW's OWN 29
tags (weapon, model, 3 render models, collision, 3 bitmaps + 2 shaders, projectile, 2 damage
effects, firing effect, HUD + 5 HUD bitmaps, both species' FP graphs, 6 sounds; 11.2 MB of
source tags) under `objects\weapons\sz_NN\saw` etc. with same-length paths, each copy's
references checked through tool. **TRAP, measured: tool DE-DUPLICATES identical resource data.**
Byte-copies added 20.2 MiB of geometry + 34.1 MiB of bitmaps to tool's counts and only 0.3 MiB to
the file; one moved vertex / pixel per stand-in still left most of it shared (+17 MiB). So
`distinct` re-imports every stand-in from its own JMS (every vertex moved n/1000 of a unit) and
TIFFs (every pixel's low bits = n) -- the cost of real ports, nothing shared:

| level (21 distinct stand-ins, palette only) | tags MiB | geometry | bitmaps | sounds | file MiB | resident |
|---|---|---|---|---|---|---|
| 07a_highcharity (most tag data + geometry) | 75.4 -> 75.7 | 80.1 -> 100.3 | 99.8 -> 130.4 | 393.1 -> 398.5 | **751.6 -> 795.6** | 21 / 21 + SAW |
| 08b_deltacontrol (largest file) | 51.8 -> 52.1 | 63.6 -> 83.8 | 106.0 -> 136.6 | 498.4 -> 503.7 | **802.5 -> 846.4** | 21 / 21 + SAW |
| 01b_spacestation (128-placement cap) | 46.5 -> 46.7 | 59.1 -> 79.3 | 99.1 -> 129.7 | 329.4 -> 334.8 | **647.6 -> 691.6** | 21 / 21 + SAW |

**Per SAW-sized port: ~2.1 MiB of file** (44.0 MiB for 21 on all three), of which tag data is
only ~0.015 MiB; geometry ~1 MiB, bitmaps ~1.5 MiB counted. tool reported NO limit and NO error
on any of the builds (01b included, at 128 placements + 21 palette-only weapons; 01b's palette 54
of 256). **So capacity is not a concern on tool's side: all 21 fit in every level.** What stays
unknown is MCC's RUNTIME: **staged for the user's boot (2026-10-20 17:12, CLASSIC)** -- the live
`08b_deltacontrol` (846 MiB) and `07a_highcharity` (796 MiB) are these test builds (21 stand-ins
resident, never placed; the level must load and play as normal). Restore:
`python h2_port_test_map.py size_test --restore 08b_deltacontrol` (and `07a_highcharity`); the
real maps are in E:\HaloBackups\h2_port_test. The stand-ins stay in the kit until then
(`h2_size_test_map.py clean` removes every one: out\h2_size_test.json lists its 735 files);
results per run in out\h2_size_test_runs.json.

### 0.2 Per-weapon configs: `sprint_toolkit/ports_h2/<key>.py`

One file per weapon, a dict `PORT` (docs in `ports_h2/__init__.py`). The SAW's eighteen
`h2_saw_*.py` steps are now **config-driven tools** reading their SECTION of a config; a session
edits only its weapon's file:

| section | step | tool (`python <tool> <key> ...`) |
|---|---|---|
| `geometry` | 1 | `h2_port_geometry.py` -- source mesh -> H2 JMS on the donor skeleton (+ `--render`); reader `h4_dump` (the SAW's); a Halo 3 / Reach reader is the wave pilot's to add |
| `textures` | 2 | `h2_port_textures.py` -- maps -> bitmaps (normal -> HEIGHT bump), seeded tags, shaders |
| `weapon` | 3 | `h2_port_weapon.py` -- clone + wire the own weapon / projectile / damage / firing effect |
| `numbers` | 4 | `h2_port_numbers.py` -- the source's own values (h2_tagfield) |
| `yardstick_fields` | 4b | the SAW's `h2_saw_yardstick.py` (one-time, guarded). NEW PORTS: clone the weapon from its YARDSTICK donor where the block shape allows (Halo 1's convention), so 4b mostly vanishes |
| `collision` | 5 | `h2_port_collision.py` -- the donor's authored hull scaled per axis |
| `meter` | 7 | `h2_port_meter.py` -- tick art (blue = the CELL's threshold), the HUD clone, the backpack icon |
| `hud_plate` | 7 | `h2_port_hud_plate.py` -- the symbol painted into the background plate |
| `reticle` | 7 | `h2_port_reticle.py` -- the source crosshair as its own one-image bitmap |
| `scope` | 7 | `h2_port_scope.py` -- blank scope widgets (a non-zooming port) |
| `glyph` | 8 | `h2_port_glyph.py` -- the pickup icon at the RESERVED codepoint, 8 fonts |
| `messages` | 8 | `h2_port_messages.py <key>` -- own lines (every language) + repoint, ANY prefix length |
| `animations` | 9 | `h2_port_animations.py` -- own FP graphs per species + their sounds |
| `retime` | 9 | `h2_anim_retime.py` (generic already; the config records the runs) |
| `sounds` | 10 | `h2_port_sounds.py` -- own sounds, classic Opus, volume marker, repoints |
| `residency` | - | `h2_port_residency.py` -- palette entry in all 13 levels |
| `test` | - | `h2_port_test_map.py` -- the dry test map (0.6) |
| `catalog` | - | `make_port_catalog_h2.py <key>` -- the 'Halo 2' catalog entry |
| `firing_profile` | 11 | the AI source (0.5) |
| `backup` | - | `port_backup.py --game h2` (derived from every config) |

Plus `order`, `wave`, `name` (the catalog's), `source`, `source_tag`, `status`, `reservations`,
`donor`, `yardstick`. `saw.py` is the complete example; the 21 others are STUBS (reservations,
the proposed donor, yardstick candidates, the AI source). `python -c "import ports_h2;
print(ports_h2.check_reservations())"` must print `[]`.
The old `h2_saw_*.py` names stay as thin wrappers (`h2_saw_textures.py` == `h2_port_textures.py
saw`); `h2_saw_messages.py` (the localization .bin blanking) is RETIRED -- `h2_port_messages.py`
replaced it on 2026-09-29 and the GPMG's lines were restored then; `h2_saw_place.py` is
superseded by `h2_port_test_map.py`; `h2_saw_group_fix.py` (a one-off built-map patch) is kept
for the record.

**THE MESSAGE-PREFIX TRAP IS GONE.** `h2_stringid.py` renames string ids of ANY length: a string
id field in an H2 loose tag holds a 24-bit string index in its low bytes and the LENGTH in its
high byte (`f9 0d 00 0b`), the strings pooled unterminated in field order; the tool rewrites the
length bytes + the pooled run and tool's export must read exactly the renamed fields changed.
Verified on gpmg.weapon copies: `gpmg -> ar2` (shorter), `gpmg -> incin2 -> gpmg` (longer, round
trip byte-identical). In game: not yet booted (the AR pilot's `ar2` is the first) -- an
observation until then; a same-length prefix still uses the in-place overwrite.

**PROOF (2026-10-20): the SAW regenerates from its config.** Step 1 alone first: `h2_port_geometry.py
saw` rewrote all three JMS (world, Chief FP, Dervish FP -- the Dervish nudge (0, 0, -0.75) recovered
from the shipped files, it was recorded nowhere) BYTE-IDENTICAL; `make_port_catalog_h2.py saw
--write` left weapon_ports_catalog.json BYTE-IDENTICAL. Then the whole pipeline,
`h2_port_tool_proof.py --tag sawp1` (log out\h2_proof_sawp1.log): the OLD h2_saw_*.py scripts and
the NEW tools each ran every step on the SAW from the same kit state -- geometry, `tool render` x3,
textures (decode + import + shaders), weapon, numbers, collision, meter + backpack, HUD plate,
reticle, scope, glyph (8 fonts), messages (all 9 languages + `new-strings`), animations, sounds (a
full re-import: rmtree, foley mixes, Opus, gain), catalog -- over 1,364 snapshotted H2EK files:
- **every file the Python steps write is BYTE-IDENTICAL** to what ships (weapon, projectile, damage
  effects, firing effect, HUD definition, both FP graphs, the six re-imported sounds, the fonts,
  hud_messages tag + every .txt, the catalog, every JMS and TIFF);
- **12 files differ, and only those `tool.exe` writes** (8 bitmap imports, 3 render models, the
  collision model) -- old vs new AND each against the shipped: TOOL'S RUN-TO-RUN NOISE, checked one
  by one with `h2_tool_noise_check.py` (regenerated again, kit copies compared through tool's own
  exports): every bitmap's PIXELS identical (export-bitmap-tga), every tag's XML identical apart from
  the import stamps (`import date`, `import time`, `modification date`); the bytes are the header
  checksum (0x28) and those stamps, and in a bitmap a stored pointer at its tail (Halo 1's
  `base_address` noise, the same thing);
- **the kit restored exactly**: pre vs end 0 added / 0 removed / 0 changed.
The old scripts' two expected failures, recorded: h2_saw_textures stops at its shader repoint (a
finished port has no turret path left to repoint -- the new tool checks first); the old catalog
writer looked for its table beside itself (the catalog proof above covers it). Not in the proof, by
design: `h2_anim_retime` (re-running it resamples an already-retimed graph through tool, which can
truncate a tag) and the one-time guarded `h2_saw_yardstick`.
The proof tool's later form (`--rev <commit>`: that commit's toolkit extracted and run against
today's) checked on commit 06d3c25: `--tag revchk --rev HEAD --steps weapon,numbers,messages,
animations,catalog` -> old vs new, pre vs new and pre vs end all 0 / 0 / 0.

### 0.8 Backup

`port_backup.py --game h2` now derives everything from the configs (each port's owned folders,
its HUD + HUD bitmaps + their TIFFs, all 13 weapons resources + scenarios, hud_messages tag + every
.txt, the eight fonts, the scripts incl. ports_h2/*.py): phase 0's ->
`F:\HaloPortBackups\2026-10-20_h2-port-phase0` (336 files, 237.6 MB). The proofs' pre-run kit
copies are on E: (`E:\HaloBackups\h2_proof_<tag>_pre`, ~300 MB each: delete old ones freely once a
later proof passed).

### 0.3 Reservations

Read from H2EK on 2026-10-20: `hud_messages` prefixes in use: ps pr bpr pp cc di be bs fc br nd
mp rl sg smg sn sen_b sen_g sen_n bo ob fl fg pg ovs atc gpmg ssmg saw2; the eight English HUD
fonts map U+E100..U+E13D (the SAW owns E13D) and U+E13E..U+E153 are free in all eight; no
`ui\hud\<key>`, HUD bitmap `<key>_*`, `sound\weapons\<key>_port` or weapon folder below exists
(only Bungie's `melee\gravity_hammer`, Tartarus's -- the hammer port gets its own folder).
Halo 2 needs NO sheet indices: a port's reticle, meter, plate, backpack and blank scope are its
OWN one-image bitmaps (the SAW's rule), so nothing in a shared sheet can move.

| # | weapon (catalog name) | config | msg prefix | glyph | weapon folder (objects\weapons\...) | HUD (`ui\hud\<key>`, bitmaps `<key>_*`) | sound folder |
|---|---|---|---|---|---|---|---|
| - | SAW | saw | saw2 | E13D | rifle\saw | saw / saw_* | sound\weapons\saw_port |
| A1 | Assault Rifle | assault_rifle | ar2 | E13E | rifle\assault_rifle | assault_rifle | assault_rifle_port |
| A2 | Spartan Laser | spartan_laser | spl2 | E13F | support_high\spartan_laser | spartan_laser | spartan_laser_port |
| A3 | Spike Rifle | brute_spiker | spk2 | E140 | rifle\spike_rifle | brute_spiker | brute_spiker_port |
| A4 | Mauler | brute_mauler | mau2 | E141 | pistol\excavator | brute_mauler | brute_mauler_port |
| A5 | Gravity Hammer | gravity_hammer | gh2 | E142 | melee\gravity_hammer_port | gravity_hammer | gravity_hammer_port |
| B1 | DMR | dmr | dmr2 | E143 | rifle\dmr | dmr | dmr_port |
| B2 | Needle Rifle | needle_rifle | nr2 | E144 | rifle\needle_rifle | needle_rifle | needle_rifle_port |
| B3 | Plasma Repeater | plasma_repeater | rp2 | E145 | rifle\plasma_repeater | plasma_repeater | plasma_repeater_port |
| B4 | Grenade Launcher | grenade_launcher | gl2 | E146 | rifle\grenade_launcher | grenade_launcher | grenade_launcher_port |
| B5 | Concussion Rifle | concussion_rifle | cr2 | E147 | rifle\concussion_rifle | concussion_rifle | concussion_rifle_port |
| B6 | Plasma Launcher | plasma_launcher | pl2 | E148 | support_high\plasma_launcher | plasma_launcher | plasma_launcher_port |
| B7 | Focus Rifle | focus_rifle | fo2 | E149 | rifle\focus_rifle | focus_rifle | focus_rifle_port |
| C1 | Storm Rifle | storm_rifle | st2 | E14A | rifle\storm_rifle | storm_rifle | storm_rifle_port |
| C2 | Suppressor | suppressor | su2 | E14B | rifle\suppressor | suppressor | suppressor_port |
| C3 | Boltshot | boltshot | bsh2 | E14C | pistol\boltshot | boltshot | boltshot_port |
| C4 | LightRifle | lightrifle | lr2 | E14D | rifle\light_rifle | lightrifle | lightrifle_port |
| C5 | Scattershot | scattershot | ss2 | E14E | rifle\scattershot | scattershot | scattershot_port |
| C6 | Binary Rifle | binary_rifle | bi2 | E14F | rifle\binary_rifle | binary_rifle | binary_rifle_port |
| C7 | Railgun | railgun | rg2 | E150 | support_high\railgun | railgun | railgun_port |
| C8 | Sticky Detonator | sticky_detonator | sd2 | E151 | pistol\sticky_detonator | sticky_detonator | sticky_detonator_port |
| C9 | Incineration Cannon | incineration_cannon | ic2 | E152 | support_high\incineration_cannon | incineration_cannon | incineration_cannon_port |

Each also reserves its effects folder (`effects\objects\weapons\<class>\<folder>`) and its FP
graph folder in BOTH species (`objects\characters\{masterchief,dervish}\fp\weapons\<class>\fp_<folder>`).
The third-person LABEL (`weapon name` / `weapon class`, which the characters' 3P graphs key on)
is not reserved: Halo 2 ports reuse a stock label (the SAW keeps the GPMG's `rifle` / `sr`);
teaching a NEW label to every 3P graph is the Halo 1 route and a pilot's decision.

### 0.4 Both first-person species: masterchief AND dervish (measured)

Every Halo 2 weapon names one FP MODEL and one FP GRAPH per species (PORTING "A weapon has one
first-person MODEL per species"). The arm skeletons, measured from Bungie's own JMS
(`tool extract-render-data`) and every kit's graphs (h2_phase0\h2_phase0_fp_skeletons.md):

| source | onto H2 masterchief (37 arm nodes) | onto H2 dervish (31: no middle finger) |
|---|---|---|
| **Halo 3** | **IDENTICAL** (37/37 names, parents, graph order; max 0.0002 units) -- copy node-for-node | **IDENTICAL** (H3 `dervish\fp\fp` and `elite\fp_arms` = H2's, 0.0000); H3 ships a dervish FP graph for 24 of 25 FP weapons (not fp_smg_silenced) -- copy node-for-node |
| **Reach** | same 37 nodes, bone lengths 0.0%, + 10 helpers (pedestal, aim_pitch, aim_yaw, humerus, radius, handguard); the model frame turned 90 deg about z; right-hand fingers 0.08-0.30 off | Reach `elite\fp\fp` = H2 dervish + the same 10; elite FP graphs for every Reach weapon -- copy by name below `base`, drop the helpers |
| **Halo 4** | different rig (80 nodes, bent rest pose, other bone axes; shoulders -25.0%, upper arm -10.7%, forearm +7.1%) -- IK RE-SOLVE (as Halo 1's C1) | NO elite FP in H4EK -- IK re-solve onto the 4-digit hand, or the SAW route (a donor's H2 dervish graph retimed) |

So: the arm chains of the two species are the same (shoulders +-9.399, upper arm 10.25, forearm
10.89 -- exactly Halo 1's numbers); only the hands differ, so finger animation is not transferable
between species. The weapon attaches through the GRAPH (`gun` = local root, child of `r_hand`),
not the `right_hand` marker. Weapon nodes map 1:1 by name (H2 JMS `frame gun`; graphs `gun`;
Reach/H4 `b_gun`); a port graph lists its source's weapon nodes (H3 AR adds `switch`). The
dervish arms JMS is version **8209** (h2_jms reads 8210 only). Open: whether the source streams use
H2's quaternion sign convention; how H2's tool imports source animations (JMA path untested); the
SAW route stays available for any port.

### 0.5 AI: Halo 2's firing data and the Armed cards

(h2_phase0\h2_phase0_ai_armed.md, with every offset.) **Halo 2 HAS a shared `ai\generic`
character** (`H2EK\tags\ai\generic.character`; elite, grunt, brute, jackal and marine name it as
parent). Firing data is looked up by the weapon's tag reference in two blocks: **Weapons
Properties** (char +0xCC, element 0xCC, weapon ref at +0x4: ranges, burst, special fire, drop,
accuracy per difficulty) and **Firing Pattern Properties** (char +0xD4, element 0x10, weapon at
+0x0; patterns at +0x8, 0x40 each, two per weapon; Weapon Damage Modifier at pattern +0x30). The
field names are Halo 3's, so a source entry copies across by name. Stock `ai\generic`: 40 weapons
properties, 38 firing patterns; **the SAW has none** (enemies have no firing data for it today).
Which weapon an enemy spawns with comes from the squad's weapon indices into the weapon palette.

**Source entries** (ai_firing_entry.py on 010_jungle / m10 / m020, re-checked): 20 of the 21 have
one (the H3 AR included; the Railgun under its campaign tag `storm_rail_gun_pve`); **only the
Sticky Detonator has none** -- its session picks a Halo 2 stand-in. Recorded per config
(`firing_profile`).

**The Armed cards are Halo 1-only today** (`halo_enhancer.armed_cards` / `_h1_enemy_weapons_spec`
return nothing for other games; `halo_patch.py:9872` gates on Halo 1; `ai_firing_profiles.json`
has only 'Halo 1'; `ai_firing_profile.py` writes Halo 1 actor variants only). Split of work:
- **a port session** can: append the port's entry to Halo 2's `ai\generic` (a new block-append
  tool for character tags -- the wave-A pilot or a dedicated session builds it, h2_loosetag's
  insert_element is the base), extend ai_firing_profile.py to a Halo 2 destination, write the
  catalog entry, check the enemies' 3P graphs cover the label;
- **the enhancer session ("Halo enhancer project")** must add: Halo 2 Armed cards + the enemy
  list, a patch pass rewriting squad / starting-location weapon indices by share (the
  Thunderstorm code `_TS_LAYOUT['Halo 2']` / `_TsWeapons` already does this shape), Balanced
  switching of the AI values, its catalog keys via port_catalog_keys.py. **Never edit the
  enhancer's files without telling that session.** Open: per-weapon vs per-block parent
  fallback; what an enemy does with a weapon its graph does not cover.

### 0.6 Parallel machinery (H2EK)

- **THE H2 KIT LOCK** (`kit_lock.py`, kit='h2' -> `H2EK\.port_kit.lock`, token KIT_LOCK_TOKEN_H2,
  `python kit_lock.py --kit h2 status | run --owner X -- cmd | release --force`). Taken inside:
  h2_rebuild_all, h2_port_test_map (build / stage / restore), h2_size_test_map, h2_port_snapshot,
  h2_port_tool_proof, h2_port_residency --write. The SHARED RECORDS (weapon_ports_catalog.json,
  ai_firing_profiles.json, port_sounds) are one file for all games: their writers
  (make_port_catalog_h2 --write included) take the HALO 1 lock. Verified 2026-10-20: contention
  (B waited 9 s for A), child re-entry, the H1 lock independent. (39487c0)
- **SHARED H2 tags a port step writes** (one session at a time -- run them under `kit_lock.py
  --kit h2 run`): `hud_messages` (h2_port_messages --write), the eight fonts (h2_port_glyph
  --write), Bungie's HUD bitmap FOLDERS (`tool bitmaps <folder>` re-imports every bitmap in the
  folder: meters, backgrounds, crosshairs, scope_masks, new_hud), the 13 weapons resources
  (h2_port_residency --write).
- **THE TEST MAP, one level per session** -- `h2_port_test_map.py <key> --level <L> [--stage]`
  / `--restore <L>` / `--status`: the level's first two Player Starting Profiles armed with the
  port (or `--profiles`), the port's palette entry ensured, every OTHER port not 'done'
  NEUTRALISED in the temporary resource (its palette entry renamed to a stock weapon -- a broken
  in-progress port never fails your build), tool build -> `H2EK\h2_maps_win64_dx11\port_test\`,
  scenario + resource + the kit's own .map put back byte-identical; `--stage` backs the live map
  up to `E:\HaloBackups\h2_port_test` (never over its own staged copy) and records the OWNER in
  stage.json (another port's level is refused, --force overrides).
- **DONE-ONLY PROOFS** -- `h2_port_snapshot.py snap/backup/diff/restore` (SHA-1 of every H2EK file
  the pipeline writes; a port not 'done' and the size-test stand-ins are never hashed, backed up
  or restored) and `h2_port_tool_proof.py --tag X --rev <commit before the change> [--steps ...]` (the toolkit
  at --rev extracted to a temporary copy and run against today's, kit put back from the backup;
  the narrowed form = --steps naming the steps that use the changed tool).
- **SHIPPING BUILDS LEAVE NON-DONE PORTS OUT** -- `h2_rebuild_all.py` holds the H2 lock, renames
  every not-done port's palette entry for a shipping build (put back after; `--no-ship` keeps
  them), and fails a level whose built map misses a done port's weapon tag.
- `h2_tagref.references` wrote ONE fixed temp XML (two sessions could read each other's export,
  and a failed export returned the previous tag's references): per-process and removed first
  since phase 0 (h2_tagfield already was). The HUD steps still use fixed %TEMP% names
  (`_h2meter`, `_ret_`, `_scope_hud.xml` ...): they are shared-folder steps anyway (rule 4).

### 0.7 Yardstick candidates (PROPOSALS -- the user picks at step 4a) and the waves

(h2_phase0\h2_phase0_yardsticks.md has the full tables: the 21 rows, Halo 2's stock weapons
with class / trigger / blocks, the donors.) The practical gate is the halo.json CARD list: a
yardstick needs a card in BOTH games. **New against Halo 1: Halo 2 has an SMG, a Battle Rifle,
a Brute Shot, a Carbine and a Beam Rifle, and Halo 4 has a carded BR, Carbine and Beam Rifle**,
so several ports get closer yardsticks than they had into Halo 1.

| # | weapon | provisional | alternatives | direct | step-5b peers (H2) |
|---|---|---|---|---|---|
| A1 | Assault Rifle | **SMG** (one hop: H3 SMG <-> H2 SMG) | Battle Rifle; Plasma Rifle | none | SMG, BR, Plasma Rifle, Brute Plasma Rifle, SAW |
| A2 | Spartan Laser | Rocket Launcher (H1 pick) | Beam Rifle; Sniper; Sentinel Beam | none | RL, Beam Rifle, Sniper, Fuel Rod |
| A3 | Spike Rifle | **SMG** (both dual-wield) | Needler; Plasma Rifle | none | SMG, Needler, Brute Plasma Rifle, Plasma Rifle |
| A4 | Mauler | Shotgun | Pistol | none | Shotgun, Sword, Magnum |
| A5 | Gravity Hammer | Energy Blade | H2's Tartarus hammer (a boss's numbers: show, do not default) | H2 hammer (Tartarus) | Sword, Shotgun |
| B1 | DMR | Sniper Rifle (H1 pick) | **BR via Halo 4** (2 hops, H4's scale); Pistol | none | BR, Magnum, Sniper, Carbine |
| B2 | Needle Rifle | Needler | Pistol; Sniper | none | Carbine, Needler, BR |
| B3 | Plasma Repeater | Plasma Rifle | Plasma Pistol | Elite (Plasma Rifle in both) | Plasma Rifle, Brute PR, SMG, Needler |
| B4 | Grenade Launcher | Frag Grenade + RL for the holes | RL; Fuel Rod | none | Brute Shot, RL, Fuel Rod |
| B5 | Concussion Rifle | Fuel Rod (both 5-round magazines in Reach and H2) | RL; Plasma Grenade | none | Fuel Rod, RL, Brute Shot |
| B6 | Plasma Launcher | Plasma Grenade + RL | Fuel Rod; RL | none | RL, Fuel Rod, Brute Shot |
| B7 | Focus Rifle | Plasma Rifle | Sentinel Beam via Halo 4; Sniper; Plasma Pistol | none | Sentinel Beam, Beam Rifle, Sniper |
| C1 | Storm Rifle | Plasma Pistol | Needler; Carbine (H4 storm_covenant_carbine); Sentinel Beam | none | Plasma Rifle, Brute PR, SMG, Needler |
| C2 | Suppressor | SMG via the SAW's chain (H4 AR > H3 AR, H3 SMG > H2 SMG) | Needler; Sentinel Beam | none | SMG, Plasma Rifle, Needler, SAW |
| C3 | Boltshot | Pistol (bolt) + Shotgun (blast) | Plasma Pistol | none | Magnum, Plasma Pistol, Shotgun, Mauler |
| C4 | LightRifle | **Battle Rifle** (one hop: H4 storm_br <-> H2 BR) | Pistol (H1 pick); Carbine; Sniper | none | BR, Carbine, Magnum, Sniper, DMR |
| C5 | Scattershot | Shotgun | Sword | none | Shotgun, Sword, Mauler |
| C6 | Binary Rifle | Sniper Rifle | Beam Rifle (heat: magazine ratios degenerate); RL | none | Sniper, Beam Rifle, Spartan Laser |
| C7 | Railgun | Rocket Launcher | Fuel Rod; Sniper; Beam Rifle | none | RL, Sniper, Fuel Rod, Spartan Laser |
| C8 | Sticky Detonator | Plasma Grenade + RL | RL; Fuel Rod | none | Brute Shot, RL, Fuel Rod |
| C9 | Incineration Cannon | Rocket Launcher | Fuel Rod | none | RL, Fuel Rod |

**Donors** (the Halo 2 tag a port's weapon is cloned from; each config's `donor`, proposed): the
same BLOCK SHAPE matters most (magazines 0/1, barrels 1/2 -- a block insert is the expensive byte
edit; trigger type, charge, heat, zoom and flags are plain fields). smg: AR, Spiker, Suppressor;
battle_rifle: DMR, LightRifle; shotgun: Mauler, Scattershot; plasma_rifle: Repeater, Storm Rifle;
plasma_pistol: Plasma Launcher, Boltshot (+ a magazine element); brute_shot: Grenade Launcher,
Sticky Detonator; rocket_launcher: Railgun, Incineration Cannon; one each: beam_rifle (Spartan
Laser), covenant_carbine (Needle Rifle), sentinel_aggressor_beam (Focus Rifle), flak_cannon
(Concussion Rifle), sniper_rifle (Binary Rifle), energy_blade (the hammer). Halo 2's triggers:
Spew, Latch, Latch-Autofire, Charge, Latch-Zoom, Latch-Rocketlauncher -- NOT spew-charge (Spartan
Laser), latch-tether (GL), double-latch-tether (Sticky), charge-with-magazine (Railgun): those four
are approximations to test. The Gravity Hammer "fix" is a FULL PORT: Halo 2's hammer tag is
Tartarus's stub (no triggers / FP model / anims / HUD / messages / player damage; his damage lives
in `tartarus_hammer_*`), so a NEW player tag goes beside it (cloned from energy_blade, Bungie's
H2 hammer model reusable, FP animations + damage from Halo 3) and Tartarus's stays untouched.

## The order

The pipeline decides it. **Halo 3's FP arms ARE Halo 2's for both species**, so wave A can
bring its source's own FP animations onto masterchief AND dervish (no retimed donor) -- that is
what the PILOT proves. Reach copies by name (wave B's pilot proves it); Halo 4 needs the arms
re-solved (wave C's pilot; the SAW route -- a donor's H2 graphs retimed -- is the fallback for
any port, the dervish especially).

### Wave A: Halo 3 source (5)

| # | weapon | new things it tests |
|---|---|---|
| A1 | **Assault Rifle** (PILOT, ALONE) | the Halo 3 source end to end: H3 render model -> H2 JMS, H3 FP animations onto BOTH species (node-for-node), an H3 FP graph in an H2 jmad, H3 sounds (FMOD) into H2, the length-aware message prefix (`ar2`) in game, palette-only residency in all 13 levels, the first port of the generalized tools |
| A2 | Spartan Laser | a charge-to-fire beam (Charge trigger, untested on a player weapon), battery + heat |
| A3 | Spike Rifle | dual wield (Halo 2 HAS it -- keep the flag), a slow projectile, blade melee |
| A4 | Mauler | pellets, one-handed + dual wield |
| A5 | Gravity Hammer | a new player tag beside Tartarus's, melee + energy per swing, the area blast |

### Wave B: Reach source (7), pilot DMR

B1 DMR (pilot: the Reach reader, copy-by-name arms, zoom), B2 Needle Rifle, B3 Plasma Repeater,
B4 Grenade Launcher, B5 Concussion Rifle, B6 Plasma Launcher, B7 Focus Rifle.

### Wave C: Halo 4 source (9), pilot Storm Rifle

C1 Storm Rifle (pilot: the IK re-solve for masterchief, the dervish route), C2 Suppressor,
C3 Boltshot, C4 LightRifle (latch-zoom secondary barrel: the scoped mode), C5 Scattershot,
C6 Binary Rifle, C7 Railgun, C8 Sticky Detonator (no AI entry), C9 Incineration Cannon.

## Definition of done, per weapon

All of PORTING.md's steps 1-11 (the Halo 2 section's pipeline), plus:
- **step 4a, the yardstick WITH THE USER** before any tag number is written (the ratio rule per
  value -- damage per round AND per second, rate, magazine / heat / battery, range, aim assist --
  for the provisional and its alternatives side by side, the time to kill each gives; the user
  picks; recorded in the config's `yardstick` and PORTING);
- **step 5b**: the step-5b peers compared with the balanced values the user picked;
- **both species**: an FP model + graph for masterchief AND dervish, each checked in game
  (a Chief level and an Arbiter level, e.g. 03a + 04a);
- **in every level**: `h2_port_residency.py <key> --write` (all 13, 01b included) and
  `--check` on the built maps;
- **tested in game, CLASSIC**: the dry test map first (`h2_port_test_map.py --stage`), then enemy
  behaviour when the Armed side exists (0.5);
- **records**: the catalog entry (`make_port_catalog_h2.py <key> --write`), the enhancer hand-off
  (cards, Armed), PORTING notes, memory, `port_backup.py --game h2`, the config `status` 'done',
  and what the weapon taught written into this plan.

The full 13-level rebuild + ship happens on the user's go, BATCHED (as Halo 1's waves):
`h2_rebuild_all.py --include-01b` (leaves non-done ports out by itself), then
`h2_port_residency.py --check` on the shipped maps and the size limits (0.1).

## Running ports in parallel (the Halo 1 rules, Halo 2's machinery)

Sequential at the start: the AR pilot ALONE; then pairs, scaled up slowly. Each port's OWN work
(its config, folders, models, graphs, sounds) is parallel by design (0.3). Rules for the sessions
(in each parallel prompt's preface) -- Halo 1's, unchanged in spirit:
1. Edit only your own config and folders. A SHARED script you must change: small change -> the
   narrowed proof (`h2_port_tool_proof.py --tag X --rev <the commit before> --steps <the
   steps using it>`) -> commit at once by path (`kit_commit.py`). The other session's
   uncommitted edits in that file: stop and ask the user.
2. Never edit another port's config while it is in progress. 2b. REWORK of a DONE port: set its
   status 'rework' first (proofs skip it), 'done' after.
3. One test level per session (`--level` on every h2_port_test_map run; stage.json owner).
4. Shared H2 tags (hud_messages, fonts, the HUD bitmap folders, the weapons resources): one
   session at a time, under `kit_lock.py --kit h2 run`.
5. Records: your own "<#>: what <weapon> taught" section, PORTING section and memory file;
   MEMORY.md and this plan edited with one small Edit each (re-read first). The NEXT prompts are
   written by the coordinating session.
6. If a script says `kit lock: WAITING`, let it wait; never `release --force` a running holder.

## Hand-off prompt for a weapon session

> Port the <WEAPON> into Halo 2 (H2_PORT_PLAN.md, wave <X>, #<n>). Source: <game>, `<tag>`.
> Read sprint_toolkit/H2_PORT_PLAN.md (phase 0 first), PORTING.md "## Halo 2" (the SAW's
> pipeline) and memory h2-port-phase0, halo2-weapon-port-donor, halo2-loose-tag-format,
> port-findings-are-observations, shared-worktree-commits first. Your config is
> sprint_toolkit/ports_h2/<key>.py: its reservations are fixed -- use them; edit only that file.
> Set its status to 'in progress'. Step 4a first: lay out the provisional yardstick and its
> alternatives side by side and let me pick. Test on one level with h2_port_test_map.py. When
> done: residency (all 13), catalog entry, enhancer hand-off, PORTING, memory, port_backup
> --game h2, status 'done', and add what the weapon taught to this plan.

### The Assault Rifle pilot (wave A1), filled in

> Port the ASSAULT RIFLE into Halo 2 (H2_PORT_PLAN.md, wave A, #A1, the PILOT of the Halo 2 port
> pipeline -- it runs ALONE; no other port session at the same time). Source: Halo 3,
> `objects\weapons\rifle\assault_rifle\assault_rifle` (H3EK; the AR also exists in Halo 1 -- the
> user chose the Halo 3 source on 2026-10-20).
> Read sprint_toolkit/H2_PORT_PLAN.md (Phase 0 first, all of it), PORTING.md "## Halo 2" (the
> SAW's pipeline, end to end, and "Halo 2 ports from here on: phase 0"), the Halo 1 wave-A pilot's
> Halo 3 tooling (H1_PORT_PLAN.md "Pilot A1: what wave A inherits"; PORTING "Halo 1: the SMG, the
> wave-A pilot": h3_rm_to_jms / h1_h3_weapon_model / h1_fp_retarget / h3_anim_decode /
> h1_port_sounds), sprint_toolkit/h2_phase0/*.md, and memory h2-port-phase0,
> halo2-weapon-port-donor, halo2-loose-tag-format, halo2-modding-toolchain, halo-port-own-messages,
> port-findings-are-observations, shared-worktree-commits.
>
> Your config is sprint_toolkit/ports_h2/assault_rifle.py (a stub): set `'status': 'in progress'`
> first (one small commit), fill its sections as you build, and edit no other port's config.
> Reserved (use exactly these): message prefix `ar2` (`ar2_pickup` ...; the first prefix whose
> length differs from its donor's -- h2_stringid renames it, verified by tool; confirm in game),
> pickup glyph U+E13E (DECIMAL 57662 for `tool replace-font-char`), weapon folder
> `objects\weapons\rifle\assault_rifle`, effects `effects\objects\weapons\rifle\assault_rifle`, FP
> graphs `objects\characters\{masterchief,dervish}\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle`,
> HUD `ui\hud\assault_rifle` + bitmaps `assault_rifle_*` (meter, bkd, reticle, backpack, blank),
> sounds `sound\weapons\assault_rifle_port`, catalog name `Assault Rifle`.
>
> START WITH STEP 4a, before any tag number is written: the yardstick, decided WITH me.
> Candidates (the config's yardstick.candidates): provisional the SMG (one hop: Halo 3 SMG <->
> Halo 2 SMG; balance_SMG_Halo3_to_Halo2.json exists), alternatives the Battle Rifle and the Plasma
> Rifle, no direct yardstick (Halo 2 has no AR). Read the H3EK AR / SMG / BR / plasma rifle and the
> H2EK SMG / BR / plasma rifle tags; put each candidate's ratio-rule result side by side per value
> (damage per round AND per second, rate, magazine / reserve -- watch the carry: H2 SMG 240 vs H3 AR
> 384, and the AR is not dual-wieldable --, reload, error / spread, velocity / range, aim assist,
> melee) and the time to kill against the step-5b peers (SMG, BR, Plasma Rifle, Brute Plasma Rifle,
> SAW). I pick; record it in yardstick['pick'] / ['reason'] and PORTING.
>
> What the pilot builds for the first time -- generalize the tools as you go, that is what a pilot
> is for, each shared-tool change proven (`h2_port_tool_proof.py --tag X --rev <commit> --steps <step>`: the
> SAW must stay byte-identical) and committed at once by path:
> 1. GEOMETRY from Halo 3: a `kind: 'h3'` reader in h2_port_geometry.py (H3 render model -> H2
>    JMS 8210). DECIDE THE SKELETON: Halo 3's FP arms ARE Halo 2's for both species (0.4), so the AR
>    can carry its OWN FP node set (gun, magazine, ophandle, safety, switch) and its OWN Halo 3
>    animations -- or the SAW route (the mesh on a donor's skeleton -- the H2 SMG's gun /
>    charging_handle / magazine / stock -- and the donor's graphs retimed). Prefer the own route;
>    record why if it fails.
> 2. FIRST-PERSON ANIMATIONS onto BOTH species: H3's masterchief AND dervish fp_assault_rifle graphs
>    into Halo 2 graphs (node-for-node; the H2 codec-3 writer in h2_anim.py / h2_anim_retime.py, or
>    tool `fp-model-animations` from exported JMA -- untested; the dervish arms JMS is version 8209).
>    Checked in game on a Chief level (03a) AND an Arbiter level (04a).
> 3. TEXTURES from Halo 3 (`kind: 'h3'` in h2_port_textures.py; a Halo 3 normal map -> a Halo 2
>    HEIGHT bump, seeded tags), SOUNDS from Halo 3 (Halo 1's h1_port_sounds found the H3 FMOD audio;
>    Halo 2 imports classic Opus, h2_port_sounds.py), the HUD (meter for 32 rounds, the plate, the
>    reticle from H3's chud), the glyph, the messages.
> 4. The weapon tag: donor PROPOSED = H2 `objects\weapons\rifle\smg\smg` (spew, 1 magazine / 1
>    trigger / 1 barrel, ammo HUD; clear `can be dual wielded`) -- the yardstick's own tag, so step 4b
>    mostly vanishes. Dual wield is n/a (the AR never had it).
> 5. RESIDENCY in all 13 levels, 01b included: `h2_port_residency.py assault_rifle --write`
>    (palette entry only; 01b is at the 128-placement cap), `--check` on built maps.
> 6. AI (step 11): Halo 3's ai\generic AR entry exists (010_jungle). Halo 2's `ai\generic` needs a
>    block-append tool for character tags (0.5: Weapons Properties + Firing Pattern Properties) --
>    build it or record it as deferred; the Halo 2 ARMED CARDS are the enhancer session's to add
>    (tell the "Halo enhancer project" session what the port needs; never edit its files).
> Tests: `python h2_port_test_map.py assault_rifle --level 03a --stage` (CLASSIC; restore with
> `--restore 03a`), then 04a for the Arbiter; exhaust map data before asking me for a boot. No
> full 13-level rebuild until I say so. When done: catalog entry (`make_port_catalog_h2.py
> assault_rifle --write`, which you generalize for the AR's table), the enhancer hand-off, PORTING
> notes, memory, `python port_backup.py --game h2`, status 'done', and "A1: what the Assault Rifle
> taught" in H2_PORT_PLAN.md (every tool you generalized, every observation) before wave A2 starts.

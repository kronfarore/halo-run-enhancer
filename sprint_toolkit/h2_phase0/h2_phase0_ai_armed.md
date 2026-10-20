# Halo 2 ports, phase 0 deliverable 0.5: AI firing data + the Armed card

Read-only research, 2026-10-20. Nothing in the repo or any kit was edited, nothing was built
and nothing was committed. Scratch: `<scratchpad>\aiarm\` (the H2EK XML exports, exp.py, cmp.py).
Paths below are relative to `tool\` unless absolute.

## 1. Where a Halo 2 enemy gets its firing behaviour for a weapon

**Halo 2 has a shared `ai\generic` character, built like Halo 3's.** H2EK:
`F:\SteamLibrary\steamapps\common\H2EK\tags\ai\generic.character` (plus `ai\generic_turret`).
Every species character exported has `parent character = ai\generic`:
elite, grunt, brute, jackal, marine (`objects\characters\<sp>\ai\<sp>.character`).
Majors chain one level further (elite_major -> elite -> ai\generic, grunt_major -> grunt).

Firing data is keyed by **weapon tag reference** inside the character, in two blocks:

| block (H2MCC Assembly plugin `Plugins\Halo2MCC\char.xml`) | offset | elem | weapon ref |
|---|---|---|---|
| Weapons Properties | char +0xCC | 0xCC | +0x4 (8-byte tagref, datum at elem+0x8) |
| ... its own inner Firing Patterns | elem +0xBC | 0x40 | -- |
| Firing Pattern Properties | char +0xD4 | 0x10 | +0x0 (datum at elem+0x4) |
| ... Firing Patterns | elem +0x8 | 0x40 | -- |

Halo 2 tagRefs are 8 bytes, datum at +0x4 (halo_patch.py:835-853, `_tagref_datum`); H3+ are 16
bytes, datum +0xC. `ai_firing_profile.build` reads `ref + 0xC` (sprint_toolkit\ai_firing_profile.py:94)
-- WRONG for Halo 2 as written.

Weapons Properties fields (H2MCC plugin offsets inside the 0xCC element):
`Weapons Flags` 0x0 (Bursting Inhibits Movement / Must Crouch To Shoot / Extended Safe-To-Save),
`Weapon` 0x4, `Maximum Firing Range` 0xC, `Minimum Firing Range` 0x10, `Normal Combat Range` 0x14 (rangef),
`Bombardment Range` 0x1C, `Maximum Special Target Distance` 0x20, `Timid Combat Range` 0x24,
`Aggressive Combat Range` 0x2C, `Super-Ballistic Range` 0x34, `Ballistic Firing Bounds` 0x38,
`Ballistic Fraction Bounds` 0x40, `First Burst Delay Time` 0x48 (rangef), `Surprise Delay Time` 0x50,
`Surprise Fire-Wildly Time` 0x54, `Death Fire-Wildly Chance` 0x58, `Death Fire-Wildly Time` 0x5C,
`Custom Stand/Crouch Gun Offset` 0x60/0x6C, `Special-Fire Mode` 0x78 (enum16), `Special-Fire Situation` 0x7A,
`Special-Fire Chance` 0x7C, `Special-Fire Delay` 0x80, `Special Damage Modifier` 0x84,
`Special Projectile Error` 0x88, `Drop Weapon Loaded` 0x8C (rangef), `Drop Weapon Ammo` 0x94 (range16),
`Normal/Heroic/Legendary Accuracy Bounds` 0x98/0xA4/0xB0 + `... Accuracy Time` 0xA0/0xAC/0xB8,
`Firing Patterns` 0xBC, `Weapon Melee Damage` 0xC4.

Firing Patterns element (0x40, both blocks): `Rate Of Fire` 0x0, `Target Tracking` 0x4,
`Target Leading` 0x8, `Burst Origin Radius` 0xC, `Burst Origin Angle` 0x10, `Burst Return Length` 0x14,
`Burst Return Angle` 0x1C, `Burst Duration` 0x20, `Burst Separation` 0x28, `Weapon Damage Modifier` 0x30,
`Projectile Error` 0x34, `Burst Angular Velocity` 0x38, `Maximum Error Angle` 0x3C.
Two patterns per weapon (H2EK names them `inaccurate` / `really accurate`); the accuracy bounds
blend from pattern 0 to pattern 1 over the accuracy time, per difficulty.

In the H2EK tag (XML export) the per-weapon patterns sit in the top-level `firing pattern
properties` block; the Weapons Properties elements show no inner `firing patterns` (the export
omits empty blocks, so the inner block is empty in stock tags).

**Field names match Halo 3 exactly** (cmp.py: all 48 Weapons Properties names and the 15 Firing
Pattern Properties names are identical between Halo2MCC and Halo3MCC char.xml). Reach / Halo 4 lack
the inner block (their pattern fields live only in Firing Pattern Properties) and H4 adds
`Blocked Shot Count`, `Maximum Extreme Target Distance` (no H2 home). So a SOURCE -> H2 copy is a
name-for-name copy of BOTH patterns -- no averaging (H1 needed it; H2 keeps two).

Stock contents of `ai\generic` (H2EK): Weapons Properties 40 entries, Firing Pattern Properties 38.
Infantry weapons with entries: battle_rifle, shotgun, smg, beam_rifle, flak_cannon (fuel rod),
plasma_pistol, needler, magnum, rocket_launcher, brute_shot, energy_blade, brute_plasma_rifle,
covenant_carbine, sniper_rifle, plasma_rifle, sentinel beams; disintegrator in props only.
**The Halo 2 SAW port (`objects\weapons\rifle\saw\saw`) has NO entry** -- no AI firing data today.

Per-species overrides are sparse: `elite.character` own Weapons Properties = spectre plasma_turret
only, own Firing Pattern Properties = needler only; `grunt` = plasma_pistol; `jackal` = plasma_pistol;
`marine` = chaingun_turret + gauss_turret; `brute` = none. So almost every infantry weapon resolves
on `ai\generic`. (Grunts carry needlers / fuel rods while their own block names only the plasma
pistol, so the engine must fall back to the parent PER WEAPON -- inferred, not measured.)

Weapon tag's own AI fields (H2 `weap`, BR export): `AI scariness` (4.0), `switch-to from ai msg`
(br_swap_ai), `weapon class` / `weapon name` string ids (`rifle` / `br`: the animation labels the
AI's biped graph must have), barrel `firing noise`, `prediction type`. No firing-pattern data on the
weapon. The H2 SAW: class `rifle`, name `sr`, `saw2_swap_ai`.

Which weapon an H2 enemy SPAWNS with is the scenario's, not the character's: squad
Initial Weapon / Initial Secondary = int16 indices into the scnr Weapon Palette
(halo_patch.py:2731-2732 `_TS_LAYOUT['Halo 2']`: squads at scnr +0x160 elem 0x74 (halo_patch.py:1977),
squad char +0x36, weap +0x3C / +0x3E; starting locations +0x48 elem 0x64, char +0x20,
weap +0x22 / +0x24; weapon palette scnr +0x98 elem 0x28 (halo_patch.py:3777)).

## 2. The Armed card today: Halo 1 only

- Cards are synthesized, not in halo.json: `armed_card` halo_enhancer.py:4187 (tag
  `scnr enemy weapons\<enemy>`, `'games': ['Halo 1']`, target field `Weapon share %`, step +0.1),
  `armed_cards` halo_enhancer.py:4223 -- **first line returns [] unless game == 'Halo 1'**
  (halo_enhancer.py:4227). Enemy list `H1_ARMED_ENEMIES` halo_enhancer.py:3950.
- Card picks -> `armed_picks` halo_enhancer.py:9127-9141 -> `_h1_enemy_weapons_spec`
  halo_enhancer.py:5727 (returns None unless self.game == 'Halo 1', :5730) -> patcher
  `h1_enemy_weapons=` halo_enhancer.py:9444 -> halo_patch.py:9872 gate `game == 'Halo 1'` ->
  `h1_enemy_weapons.apply` (actv slots: source variant + weapon + donor firing block
  actv 0x74-0x15F, 0x1D8-0x1E3). `_port_actv_carriers` halo_patch.py:9594/9893 also Halo 1 only.
- Weapon eligibility: `h1_used_weapons` halo_enhancer.py:4173 -> `h1_enemy_weapons.used_weapons`
  (h1_enemy_weapons.py:182) = carried weapons + every key of `ai_firing_profiles.json['Halo 1']`
  (`profiles()` h1_enemy_weapons.py:161 reads `GAME = 'Halo 1'`, :46).
- Options: `h1_enemy_weapon_cards`, `h1_armed_all_weapons` (halo_enhancer.py:424, 1036-1041, 11933-11950).
- **ai_firing_profiles.json has only a 'Halo 1' key** (27 profiles, incl. `weapons\saw\saw`). No
  Halo 2 entry; the H2 SAW has no profile and no Armed card.
- **weapon_ports_catalog.json 'Halo 2'**: one entry, SAW: keys `weapon, source ('Halo 4'), donor ('SMG'),
  default_on, desc, fp_animations ('objects\characters\*\fp\weapons\rifle\fp_saw\fp_saw'),
  anims {'reload': 0.851562}, balance` (40 rows). No `weap`, `requires`, `hands`, `tag_map`,
  `actor_flags` etc. (`weap_path` derives the tag from the balance rows, weapon_ports.py:62).
  Written by sprint_toolkit\make_port_catalog_h2.py (SAW-specific: PORT_TAGS table, one balance json).
- `ai_firing_profile.py` (sprint_toolkit\ai_firing_profile.py): sources H4/H3/ODST/Reach
  (SOURCES :65-71); the DESTINATION is hard-wired to Halo 1: plugin `actv` (:83), field window
  0x74-0x160 / 0x1D8-0x1E4 (:127), pattern AVERAGING (:110-121), `from_config` loads `ports_h1`
  only (:236) and `save('Halo 1', ...)` (:280). `--to-game` exists but only changes the json key;
  it still reads the H1 actv plugin. Writes a JSON profile; it never writes a tag or a map.
  No support for writing an H2 character Weapons Properties / Firing Pattern Properties entry.
- `ai_firing_entry.py` / `ai_firing_search.py`: read-only readers of a source map's ai\generic, built
  on `build(write=False)`; they print H1 actv names/offsets but the values are the source's.
  They work as-is for checking a source weapon (used below).
- `h1_teach_weapon.py`: H1 antr only. Halo 2 analogue (does the AI biped's jmad carry the port's
  `weapon class`/`weapon name`) has no tool.

## 3. Source ai\generic entries for the 21 source weapons (RE-CHECKED, all 21)

Re-ran `sprint_toolkit\ai_firing_entry.py` on the same maps the H1 configs use (compiled MCC
maps, not the EK tag folders): Halo 3 `halo3\maps\010_jungle.map`, Reach `haloreach\maps\m10.map`,
Halo 4 `halo4\maps\m020.map`. "#p/#f" = Weapons Properties / Firing Pattern Properties index.

| source | weapon tag | entry | H1 config agrees |
|---|---|---|---|
| H3 | rifle\assault_rifle\assault_rifle | YES #8/#8 | (no H1 port; SAW/SMG used it as donor) |
| H3 | support_high\spartan_laser\spartan_laser | YES #14/#14 | spartan_laser.py source |
| H3 | rifle\spike_rifle\spike_rifle | YES #2/#2 | brute_spiker.py |
| H3 | pistol\excavator\excavator | YES #17/#12 | brute_mauler.py |
| H3 | melee\gravity_hammer\gravity_hammer | YES #19/#18 | gravity_hammer.py |
| Reach | rifle\dmr\dmr | YES #2/#2 | dmr.py |
| Reach | rifle\grenade_launcher\grenade_launcher | YES #8/#7 | grenade_launcher.py |
| Reach | rifle\needle_rifle\needle_rifle | YES #12/#12 | needle_rifle.py |
| Reach | rifle\focus_rifle\focus_rifle | YES #5/#5 | focus_rifle.py |
| Reach | support_high\plasma_launcher\plasma_launcher | YES #14/#14 | plasma_launcher.py |
| Reach | rifle\plasma_repeater\plasma_repeater | YES #16/#16 | plasma_repeater.py |
| Reach | rifle\concussion_rifle\concussion_rifle | YES #1/#1 | concussion_rifle.py |
| H4 | pistol\storm_sticky_detonator\storm_sticky_detonator | **NO** | sticky_detonator.py: same_game stand-in (rocket launcher carriers) |
| H4 | rifle\storm_rail_gun\storm_rail_gun_pve | YES #37/#37 | railgun.py: source, the **_pve** tag |
| H4 | rifle\storm_assault_carbine\storm_assault_carbine | YES #15/#15 | storm_rifle.py |
| H4 | pistol\storm_stasis_pistol\storm_stasis_pistol | YES #21/#21 | boltshot.py |
| H4 | rifle\storm_forerunner_smg\storm_forerunner_smg | YES #22/#22 | suppressor.py |
| H4 | rifle\storm_spread_gun\storm_spread_gun | YES #18/#18 | scattershot.py |
| H4 | rifle\storm_forerunner_rifle\storm_forerunner_rifle | YES #16/#16 | lightrifle.py |
| H4 | support_high\storm_forerunner_incineration_launcher\... | YES #30/#30 | incineration_cannon.py |
| H4 | rifle\storm_forerunner_sniper_rifle\storm_forerunner_sniper_rifle | YES #26/#26 | binary_rifle.py |

CORRECTION to the brief: the **Railgun is NOT entry-less** -- phase 0 searched the MP tag; C7 found
`storm_rail_gun_pve` in nine H4 campaign maps (ai_firing_search.py docstring; railgun.py uses it). Only the
**Sticky Detonator** has none (MP tag re-checked here; railgun/sticky configs record the _pve search).
For Halo 2 the Sticky Detonator needs a same-game stand-in (H2 rocket_launcher entry is the
analogue of H1's choice). The H3 Assault Rifle has no Halo 2 counterpart weapon; its entry exists.

Each ports_h1\<key>.py `firing_profile` also carries the H1-only parts (donor_weapon = an H1 tag,
wdm_rule, balanced_set, species_skill, actor_flags `--set 0xOFF` = actv offsets). Reusable for H2:
`from_game`, `from_map`, `from_weapon`. Not reusable: every `set`/`balanced_set` offset (actv),
`donor_weapon` paths, WDM bases (H1 yardsticks).

## 4. What a Halo 2 Armed card needs: enhancer side vs port session

### Port session can do itself (no enhancer file touched)
1. **AI firing data at TAG level** -- the H2-native route: append the port's element to
   `ai\generic`'s Weapons Properties AND Firing Pattern Properties in H2EK (copy of the source's
   entry, names 1:1, both patterns), then rebuild the levels (h2_rebuild_all.py). Every character
   then fires the port wherever it gets it -- no enhancer-side firing copy, unlike Halo 1's actv slots.
   Needs a NEW tool (H2 tag block-append for `char`; `h2_tagfield.set_field` only edits existing
   elements; `h2_loosetag.insert_element` is scenario-oriented and untested on char). Or Guerilla.
   A weapon-specific species override goes in that species' own char block (same layout).
2. A Halo 2 reader of the SOURCE entry: `ai_firing_entry.py` works now; a write-capable H2 variant
   of `ai_firing_profile.py` (new mode, or a new script) -- `ai_firing_profile.py` is a sprint_toolkit
   tool the port sessions already own (ports_h1 sessions wrote it), so extending it for a `--to-game
   "Halo 2"` destination (plugin `char`, H2 8-byte tagref, no averaging) is port-session work. Keep
   `ai_firing_profiles.json` writes to a new 'Halo 2' key only, under kit_lock.
3. Catalog: the 'Halo 2' entries (weap, fp_animations, anims, balance, requires) via a new
   make_port_catalog_h2_ports.py (make_port_catalog_h2.py is SAW-only). The enhancer's OWN keys
   (hands, tag_map, card_map, skip_cards, card_donors, trigger_index, actor_flags) go through
   `sprint_toolkit\port_catalog_keys.py` (OWNED tuple :32) -- it is game-agnostic (`--game "Halo 2"`)
   but is the ENHANCER's channel (lock owner 'enhancer').
4. Animation coverage check: the AI biped graphs (elite/grunt/brute/jackal/marine .model_animation_graph)
   must hold the port's `weapon class` / `weapon name`, else unknown behaviour (H1: spawns the default
   weapon). No H2 tool yet (h1_teach_weapon.py analogue).
5. Palette presence: the port must be in each level's scnr Weapon Palette for a squad weapon index
   to point at it (h2_saw_place.py places the SAW via the player starting profile -- NOT the palette).

### Needs the enhancer (tell the 'Halo enhancer project' session)
1. `armed_cards` / `armed_card` for 'Halo 2' (halo_enhancer.py:4227 gate, `'games': ['Halo 1']` :4201),
   an `H2_ARMED_ENEMIES` list (Grunt, Jackal, Elite, Brute, Flood?, Marine through Ally), and the
   eligibility test (no `h1_used_weapons` equivalent: H2 would be 'has an ai\generic entry or is
   carried').
2. `_h1_enemy_weapons_spec` (halo_enhancer.py:5727, gate :5730) + patcher gate halo_patch.py:9872:
   a Halo 2 pass that rewrites squad / starting-location weapon indices (+0x3C/+0x3E, +0x22/+0x24) by
   share -- the Thunderstorm code already does this shape (`_TS_LAYOUT['Halo 2']`, `_TsWeapons`
   halo_patch.py:3102-3135) -- plus adding the port to the Weapon Palette if missing.
3. If the AI firing data is NOT built into the tags (route 1 above), the enhancer would have to append
   char block elements in the compiled map -- H2 block growth in a cache file, much harder; route 1
   avoids it.
4. Balanced / WDM rule, drop rule, species skill: the H1 rules write actv fields per slot; in H2 they
   would be values in the ai\generic entry (tag-level, port session) -- unless Balanced must switch them
   at patch time, which is enhancer work (H2 map field writes on char Firing Patterns).

## Could NOT determine (needs a boot or more research)
- Whether H2 looks up a weapon's firing data per weapon up the parent chain (inferred from Grunts
  carrying needlers with only a plasma-pistol entry of their own) or block-wise.
- What an H2 AI does with a weapon whose class/name its animation graph lacks.
- Whether the inner Weapons Properties `Firing Patterns` (+0xBC) or the top-level Firing Pattern
  Properties wins when both exist (Halo 3's rule per ai_firing_profile: the pattern block first,
  inner as fallback) -- stock H2 tags only use the top-level block.
- Whether a scnr Weapon Palette append survives the H2 scenario-resource stomp at build time
  (see memory halo2-loose-tag-format) -- not checked.
- I did not re-check the source entries against the EK tag folders (H3EK/HREK/H4EK ai\generic);
  the tooling and this check read the compiled MCC maps.

# Halo 2 Armed cards: hand-off to the "Halo enhancer project" session (2026-10-20)

Written by the Halo 2 Armed-cards session (H2_PORT_PLAN.md 0.5b). `halo_enhancer.py` and
`halo_patch.py` were NOT edited: everything below that touches them is yours. The port side is
done and committed; the interface is one module call and one spec dict.

## What the port side delivers (done)

1. **Firing data in the kit tag.** `sprint_toolkit/h2_ai_firing.py` appends / replaces a weapon's
   entries in H2EK `ai\generic.character` (Weapons Properties + Firing Pattern Properties, both
   patterns), export-checked; `python sprint_toolkit/ai_firing_profile.py --h2-port <key>` runs it
   from the port's config (`ports_h2/<key>.py` `firing_profile`: source entry by name over a
   same-game `donor_weapon`). Every character (elite / grunt / brute / jackal / marine / flood all
   parent `ai\generic`) then fires the port wherever a squad hands it over -- **no patch-time
   firing copy** (Halo 1's actv slots have no Halo 2 counterpart to build). It rides every rebuilt
   level. First entry: the SAW (`objects\weapons\rifle\saw\saw`).
2. **The record.** `ai_firing_profiles.json['Halo 2'][<weapon tag>]`: source, donor, the values
   written (`props`, `patterns` [2]) -- and the place for Balanced rows (below).
3. **The patch pass, as a module: `h2_enemy_weapons.py` (tool root).**
   `h2_enemy_weapons.apply(m, halo_patch_module, spec, registry)` -> result rows, with
   `spec = {'cards': {<enemy type>: {<weapon tag>: share, ...}, ...}, 'balanced': [<weapon tag>, ...]}`.
   - Arming: every squad unit (squad +0x3C/+0x3E, starting location +0x22/+0x24 -> scnr Weapon
     Palette +0x98/0x28) whose character belongs to a carded type draws a deterministic number
     (map name + field address: co-op partners and re-patches agree); below the sum of the
     shares it takes the weapon whose interval holds it (above 100 % the shares count by weight,
     as Halo 1), secondary -1. Protected units = `halo_patch._ts_units` (vehicle-bound /
     script-loaded) keep theirs. A location with weapon -1 inherits its squad's draw.
   - A weapon missing from the level's weapon palette is reported (`skip`), never added (ports
     are resident in all 13 levels by H2_PORT_PLAN 0.1; stock weapons may be absent).
   - Enemy types (`ENEMY_CHARS`): Grunt (grunt, heretic_grunt), Jackal, Elite (elite, heretic),
     Brute, Flood Combat Form (floodcombat_elite / _human), **Marine** (the Ally twin). Left out:
     Tartarus, the Heretic leader, Johnson boss, councilors, Hunters, Sentinels, Drones, story
     characters.
   - Balanced: for a weapon in `spec['balanced']` the profile's `balanced_props` {field: value} /
     `balanced_patterns` [{..}, {..}] (Assembly Halo 2 `char` names) are written over the map's
     `ai\generic` entry (fixed-size writes). No port has Balanced AI rows yet (the SAW: none).
   - `eligible_weapons()` (below) = the weapons with firing data in Halo 2.

## What the enhancer needs to add (yours)

1. **Cards**: `armed_cards` (halo_enhancer.py ~4227, `game != 'Halo 1'` gate) and `armed_card`
   (`'games': ['Halo 1']`) for Halo 2: enemy list `H2_ARMED_ENEMIES = ('Grunt', 'Jackal',
   'Elite', 'Brute', 'Flood Combat Form')` + the Marine Ally twin (memory halo-always-ally-card);
   card tag `scnr enemy weapons\<enemy>`, field `Weapon share %`, step +0.1 as Halo 1.
   **Eligibility** = `h2_enemy_weapons.eligible_weapons()` (stock infantry weapons with an
   ai\generic entry + every port recorded in `ai_firing_profiles.json['Halo 2']`) instead of
   `h1_used_weapons`; a port only while ports are offered on the level (your existing `_is_port`
   rule). Grenades / equipment / sprint excluded as Halo 1.
2. **Spec + gate**: an `_h2_enemy_weapons_spec(armed_picks)` beside `_h1_enemy_weapons_spec`
   (~5727): `{'cards': {enemy: {weapon tag: share}}, 'balanced': self._balanced_port_weapons()}`,
   passed to the patcher (e.g. `h2_enemy_weapons=`), and in `halo_patch.apply_run` next to the
   Halo 1 gate (~9872), AFTER the skulls (Thunderstorm decides who is what first, as Halo 1):
   `if h2_enemy_weapons and game == 'Halo 2': results.extend(h2_enemy_weapons_module.apply(m,
   sys.modules[__name__], h2_enemy_weapons, registry))`.
3. **Options**: `h1_enemy_weapon_cards` / `h1_armed_all_weapons` are Halo 1-named; reuse or add
   Halo 2 twins -- your call.
4. **Catalog keys** (`port_catalog_keys.py --game "Halo 2"`, your channel): none needed for the
   cards themselves; `weapon_ports.weap_path(p)` must resolve the SAW (its catalog entry has
   `balance` rows -> `objects\weapons\rifle\saw\saw`).

## Open (decide with the user)

- **Two-handed rule** (Halo 1: Grunts fire two-handed weapons at half rate, Jackals lose the
  shield): Halo 2 looks firing data up per weapon on `ai\generic`; a Grunt-only rate needs a
  Grunt override entry (grunt.character's own Firing Pattern Properties, same layout -- h2_ai_firing
  can write it with `--tag`) or a patch-time write. Not built.
- **WDM rule** (Halo 1: WDM = base x yardstick dps / port dps): Halo 2's stock patterns carry WDM 0
  (37 of 38; the Sentinel beam 0.57), i.e. 'unmodified' -- the SAW took Halo 4's 0.75 by name. The
  rule's base for Halo 2 needs a measurement (what 0 means against 0.75) before it applies.
- **Species skill rule**: every Halo 2 species inherits `ai\generic`'s accuracy; per-species skill
  would need species override entries. Not built.
- **3P animation**: the SAW's 3P label is the sniper's (`sr`, a GPMG leftover under rework); what a
  species without that set does with it -- see the in-game result in H2_PORT_PLAN 0.5b.

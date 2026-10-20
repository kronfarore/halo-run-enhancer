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
   - **Jackals + two-handed** (user, 2026-10-20): a Jackal unit handed a two-handed weapon
     (not class pistol, not dual-wieldable -- Halo 2's SMG is class 'rifle' but dual-wields)
     becomes `jackal_sniper` (the same biped, variant 'shieldless', with the rifle set). Every
     level that fields Jackals has it in its palette; elsewhere the row says it kept the shield.
   - **Grunt teach** (seen in game 2026-10-20: Grunts never carried the SAW -- their graph has no
     'rifle' class, so they spawn with the biped default): every mode of
     `objects\characters\grunt\grunt` holding the 'missile' class (the fuel rod's two-handed
     set) gets a copy labelled with the weapon's class, child data SHARED by pointer, in sorted
     string-id order (these are binary-searched 'sort' blocks), plus the Weapon List pairs tool
     writes (`(rl, rifle)`). Heretic Grunts use the same graph. Grunts hold a rifle like a fuel rod.
   - **Grunt half rate** (the Halo 1 rule): every Grunt character in the map gets its own Firing
     Pattern Properties entry for each two-handed, non-'missile' weapon handed to Grunts =
     ai\generic's patterns at half rate (the pattern's rate, or the barrel's rounds per second
     where the pattern says 0); the SAW 20 -> 10. Other weapons resolve on ai\generic as before.
   - **Balanced**: for a weapon in `spec['balanced']` the profile's `balanced_props` /
     `balanced_patterns` (Assembly Halo 2 `char` names) are written over the map's `ai\generic`
     entry BEFORE the Grunt copies (so those carry them too). THE WDM RULE (user, 2026-10-20):
     default = the source game's own WDM, BALANCED = it x `BALANCED_BASELINE['Halo 2']['damage']`
     (0.84; a source 0 counts as 1.0) -- written by ai_firing_profile --h2-port (SAW 0.75 / 0.63).
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

## Open

- **Species skill rule** (Halo 1: per-species accuracy scaling): every Halo 2 species inherits
  `ai\generic`'s accuracy; a per-species skill needs species override entries like the Grunt
  half rate's. Not built; the user has not asked for it in Halo 2.
- **God shield on port tests** (Halo 1 rule): h2_port_test_map has none yet.

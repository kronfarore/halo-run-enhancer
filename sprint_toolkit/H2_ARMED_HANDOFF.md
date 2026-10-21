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
     as Halo 1), secondary -1. EVERY unit of the type is armed, dropship / vehicle / script-loaded
     squads too (test 3: Jackals in the early scripted spawns kept their stock weapon and shield
     while the first version skipped `halo_patch._ts_units`' protected units -- that protection is
     for SPECIES that cannot ride, not for weapons). A location with weapon -1 inherits its squad's draw.
   - A weapon missing from the level's weapon palette is reported (`skip`), never added (ports
     are resident in all 13 levels by H2_PORT_PLAN 0.1; stock weapons may be absent).
   - Enemy types (`ENEMY_CHARS`): Grunt (grunt, heretic_grunt), Jackal, Elite (elite, heretic),
     Brute, **Bugger** (Drones: hand-held weapons in Halo 2), Flood Combat Form (floodcombat_elite /
     _human), **Marine** (the Ally twin). Left out: Tartarus, the Heretic leader, Johnson boss,
     councilors, Hunters, Sentinels, story characters.
   - **Jackals + two-handed** (user, 2026-10-20): a Jackal handed a two-handed weapon (not class
     pistol, not dual-wieldable -- Halo 2's SMG is class 'rifle' but dual-wields) spawns WITHOUT
     its arm shield: its starting location's **Actor Variant Name** (+0x30, string id) =
     'shieldless', the jackal model's own variant -- exactly what Bungie does for an ordinary
     'jackal' location on 03a (and 21 jackal_sniper ones). The character stays the ordinary
     Jackal. (Test 2 switched them to jackal_sniper instead: those fired but did not visibly aim --
     its SNIPER STYLE: suppressing fire, no cover peek / investigate / surprise. Kit twin
     characters were tried next and dropped: tool keeps no palette entry a squad does not use.)
     A squad has no variant field, so a squad's draw reaches its Jackals through its locations.
   - **The teach** (`TEACH`): a Halo 2 unit refuses a weapon whose class its graph lacks (SAW
     Grunts spawned with their default: the Grunt graph is any / missile / pistol / unarmed) and
     drops it in a mode without the class -- fleeing Grunts and Jackals drew their Retreat
     'backup weapon' (a plasma pistol): their 'flee' mode is pistol-only. Every mode of the
     enemy's graph lacking the weapon's class but holding a donor class gets a copy of the donor
     labelled with the class (children SHARED by pointer, sorted string-id order -- binary-searched
     'sort' blocks -- plus the Weapon List pairs tool writes). Donors: Grunt 'missile' (the fuel
     rod's two-handed set) then 'pistol'; Jackal and Drone 'pistol'. Elites and Brutes already
     hold every class. On 07a for a rifle: Grunt 9 modes (flee included), Jackal flee, Drone patrol.
   - **Brute type teach** (`TEACH_TYPE`, user 2026-10-21: Brutes hold a two-handed weapon like
     the Brute Shot): the Brute graph has the classes, but its rifle 'any' set is the one-handed
     carry. Every Brute mode holding both the weapon's class and 'support' gets, in the weapon's
     class, a weapon TYPE labelled with the weapon's NAME (type lookup is by weapon name) = a copy
     of support 'any' (the whole Brute Shot set), children shared, sorted; the Weapon List gets
     (name, class). A name that already has a type (the shotgun's sg) keeps it. NOTE: the SAW's
     weapon name is still the sniper rifle's 'sr' (a GPMG leftover under rework), so a Brute with
     a sniper rifle would take the Brute Shot set too until the rework renames it.
   - **Grunt half rate** (the Halo 1 rule): every Grunt character in the map gets its own Firing
     Pattern Properties entry for each two-handed, non-'missile' weapon handed to Grunts =
     ai\generic's patterns at half rate (the pattern's rate, or the barrel's rounds per second
     where the pattern says 0); the SAW 20 -> 10. Other weapons resolve on ai\generic as before.
   - **Species skill** (the Halo 1 rule, Halo 2 form, 2026-10-20): Halo 2 has no per-species aim
     block; a species' skill is its own Weapons Properties entry for its signature weapon. The
     Grunt's own plasma pistol vs ai\generic's: accuracy bounds x0.25-0.5, accuracy time x3-6,
     surprise delay x3, surprise fire-wildly x1.5; the Jackal's: surprise delay x2. Every Grunt /
     Jackal character gets its own entry for each weapon handed to that species = ai\generic's
     with those fields scaled (a 0 in the species' entry is skipped; bounds capped at 1).
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

## Seen in game, for the enhancer to know

- Test 1 (03a): Elites and Jackals carried and fired the SAW, Grunts did not (-> the teach).
- Test 2 (03a): every type fired; Jackals switched to jackal_sniper did not visibly aim (-> the
  location variant); fleeing Grunts / Jackals dropped the SAW for a plasma pistol (-> the flee teach).
- Test 3 (03a): Elites and Grunts good; Jackals in early scripted spawns kept shield + stock
  weapon (-> every unit armed).
- Test 4 (07a): Brutes and Drones carry and fire it; Brutes should use the Brute Shot set (->
  the type teach).
- Test 5 (07a): the Brute type teach; the test layout (below) -- PASSED (user, 2026-10-21:
  'Armed test passes completely now').
- Flee test (03a, the level's own Elite-led squads, `--no-replace`): pending.

## Test tooling

- **Test layout** (user, 2026-10-21): `h2_port_test_map.py <key> --level L --armed TYPES --stage`
  first turns the squads nearest the player start (on foot) into the tested types, round robin,
  2 squads each (squad + location characters; location variants cleared), then runs the Armed
  pass -- every type at once, no walking through the level. `--no-replace` keeps the level's own.
  TEST ONLY: the enhancer does not do this.

- **Cheat** (user, 2026-10-21, every Armed test): the Covenant Carbine as the starting profiles'
  secondary (36 / 360), its carbine_slug damage x1000, and the player's matg run / sneak speed +
  acceleration x2. No Marine carries the Carbine, so allies do not clear the test enemies.
- **God shield**: h2_port_test_map now sets it on every test (player models masterchief /
  dervish: body + shield 1e6, no stun; `--mortal` turns it off) -- test-map only, not enhancer.

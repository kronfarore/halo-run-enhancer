# Variant Recipe: every enemy on every level, and cards that spawn them

Built for Halo 1 on 2026-10-06. This file records the whole machinery, from the first
census to the cards, so another game can follow it. Weapon ports have their own recipe
in `PORTING.md`; this one is about **characters**.

The result in Halo 1:
- all 40 enemy actor variants, their 9 majors and 13 Marine variants are built into all
  ten campaign maps;
- seven **Incursion** cards and one **Friend Marines** card turn 10% of a level's enemies
  into another species per pick, for the rest of the run.

Status: residency was confirmed in game (a10 tests v1 and v2). The cards were verified
offline on baseline copies only and are **untested in game**.

---

## 0. The pieces at a glance

| step | what | tool |
|---|---|---|
| 1 | census: which variants exist, which level lacks which, what limits apply | scratch census, then `h1_all_enemies.py plan` |
| 2 | residency plan: anchors + palette appends (+ chain for extras) | `h1_all_enemies.py plan` -> `h1_all_enemies_plan.json` |
| 3 | test map: one level built, enemies swapped in, played | `h1_all_enemies.py test`, `h1_all_enemies_test.cmd` |
| 4 | make it permanent: kit edit + rebuild + verify | `h1_all_enemies.py apply`, `h1_rebuild_all.py`, `h1_all_enemies.py verify` |
| 5 | tier ladder per species | `h1_species_swap.CARDS`, `tier_of` |
| 6 | patch-time pass | `h1_species_swap.apply` (root of the tool folder) |
| 7 | patch order inside `halo_patch.apply_run` | ladder -> swap -> Betrayal/Schism -> Armed -> cards |
| 8 | cards + enhancer wiring | `halo.json`, `halo_enhancer.py` |
| 9 | offline verification | `h1_species_swap_check.py` |

---

## 1. Census: what decides feasibility

Measure these four things before designing anything. All four were read from the
patcher's baselines (`E:\HaloBaselines\halo1\maps`), never from the live maps, which
carry a patched run.

1. **The variant list.** Every enemy actor variant in the game (H1: `actv`; H2+: `char`).
   Separate the *roots* (variants nothing names as its Major Variant) from the *majors*.
   A major travels with its minor, so it costs nothing. H1 has 40 roots and 9 majors.
   - **Promotions are real spawns.** "Never placed" is not "never seen". Hunter major and
     Sentinel major appear only by promotion: the squad's Major Upgrade (H1 squad +0x80:
     Normal/Few/Many/None/All) promotes the minor into its Major Variant. Before cutting a
     variant as unused, check whether something promotes into it.
2. **Memory limit.** H1 tag memory runs from 0x50000000 to 0x54000000 (64 MiB). Proof:
   every structure BSP's load address plus its size ends at exactly 0x54000000. The worst
   level with everything added was about 16.5 MB of tag data plus a 5.6 MB BSP.
   **Memory was not the limit.**
3. **The real limit: the actor palette.** H1 caps it at 64 entries, and `tool` APPENDS
   every child scenario's palette to the parent's, with no de-duplication. Read the
   palette size from the BUILT map, not the kit scenario.
   - The 20 enhancer slots already use 20 entries.
   - Adding the missing variants to the palette alone fell short on all ten levels.
4. **What makes a tag resident.** H1 builds into the map every tag the scenario reaches
   by any tagref chain. Adding a tag to a FINISHED map crashed the level
   (`h1_variants.add_tags`, 2026-10-02), so **residency is a kit + rebuild job**. Later
   games add zone sets / resource pools on top: see `reach-weapon-residency-pools`,
   `halo3-weapon-residency` and `h1-weapon-into-map` in memory.

The per-level gain in tag data (0.02 MB on c40 up to 4 MB on a10) came from a tagref
closure scan: every 32-bit value in a tag's meta that equals a tag id. It is crude but
good enough for a size estimate.

---

## 2. Residency: three ways to get a tag built in

The build tool includes anything a tagref reaches. Three routes, cheapest first.

### 2a. Slot anchors (no palette cost)
The 20 enhancer slots (`characters\enhancer\slot NN`, `h1_variant_slots.py`) are SHARED
kit tags in every level's palette. Their **Major Variant** ref is free until the patcher
fills a slot. Point each slot's Major Variant at one root, and that root is in every map.
- The patcher's `fill_slot` overwrites the ref later. The tag stays in the map regardless.
- The anchor set is GLOBAL (the slots are shared), so choose it to fit the worst levels:
  `make_plan` picks the 20 greedily, minimising the summed and then the worst shortfall.

### 2b. Palette appends
Each level's remaining missing roots are APPENDED to its kit scenario's Actor Palette
(`h1_loosetag.insert_block_element`, a 16-byte actv tagref). Appending moves no existing
index. Two levels ended exactly at 64 (a50, d40).

### 2c. The chain (unlimited, one slot)
When the palette is full, one slot's Major Variant heads a **chain of kit COPIES**. Each
copy names the next as its Major Variant, and the last names the slot's old anchor.
Slot 20 carries the 13 Marine variants this way (`characters\marine\anchor\...`,
`characters\marine_armored\anchor\...`).
- Copies stay under their species folder, so species wildcards (`characters\marine*`)
  still reach them.
- **Trap:** a copy's Major Variant is the chain, not a promotion. Whoever spawns a copy
  must first set its +0x24 to the real major, recorded in the plan as `chain_major`
  (`h1_species_swap.Swapper.resolve` does this).
- Why not empty unused child-scenario palettes instead (as was done for c20/d20
  cinema)? `a50_cinema` turned out to have a live encounter on one of its 16 entries.
  The chain needs no Guerilla work and has no size limit.

### 2d. The plan file
`sprint_toolkit/h1_all_enemies_plan.json` is the record: roots, majors, anchors,
per-level palette adds, built palette sizes, chain, chain sources, chain majors.
- **Never `plan --replan` after the rebuild.** `make_plan` reads presence from
  `h1_actv_index.json`, and a re-index of the new maps shows every enemy everywhere.

---

## 3. The test map (one level, before touching all ten)

`h1_all_enemies.py test --level a10` backs up the kit files (`*.before_allenemies`),
applies the plan for that level only, builds it (`h1_rebuild_all.py --maps a10
--no-ship`), copies the build out, and **puts the kit back**. Map-side edits then go on
the copy:
- slot palette entries are repointed at the anchors, so all 40 roots are in the palette;
- every Covenant squad is repointed by a species-interleaved cycle;
- the player gets a god shield (`h1_enemy_test_map`'s).

`h1_all_enemies_test.cmd deploy|restore [level]` swaps the test map in and out. The
live map is kept as `<level>.map.pre_allenemies`. `--factions` builds v2;
`--reuse-build` skips the kit build when `HCEEK\maps\<level>.map` already is one.

**What the two boots proved (user, 2026-10-06):**
1. **v1:** the map loads, every species spawns and acts, the map grew by 17 MB. But
   there was **no infighting**: Flood, Covenant and Sentinels mixed inside one encounter
   fought as one side.
2. **v2:** one faction per encounter, with the encounter's Team Index (+0x24) set
   explicitly (Covenant 3 / Flood 4 / Sentinel 5). Factions FIGHT, and Hunters are fine.

**=> In H1 the team is decided per ENCOUNTER.** Any mixing feature has to convert whole
encounters to get infighting.

Two hygiene lessons from the tests:
- Place the species under test somewhere it is MET. v1's Hunters went to a scripted
  tutorial actor (`cryo_bane`, invulnerable, then `ai_erase`d) and to two Normal actors
  behind a door, and were never seen. See the `halo-test-enemy-placement` memory.
- Say what each test rules out before asking for a boot (`halo-in-game-test-budget`).

---

## 4. Making it permanent

```
python h1_all_enemies.py apply        # kit for good; pre-feature kit copied to E:\HaloBackups\kit-h1-before-allenemies
python h1_rebuild_all.py              # all ten: build, check, ship as baseline + live (previous -> E:\HaloBackups\ek-build-h1\previous)
python h1_all_enemies.py verify --map E:\HaloBaselines\halo1\maps\c40.map   # 62/62 resident
```
- `h1_rebuild_all` refuses a level with fewer than 20 slots. It builds `classic none 1`.
  Anniversary graphics are irrelevant: every enhancer H1 build is classic.
- Check a level that never had the species for its biped, animations and model, not
  just the actv (Marines on c40/d40: `bipd`, `antr`, `mod2` all present).
- Co-op partners need the new maps.

---

## 5. The tier ladder

Each replaced actor is ranked 1-4 by its own variant (`tier_of`) and becomes the same
tier of the card's species (`CARDS`). Where a tier lists several variants, the replaced
actor's WEAPON carries over if one of them carries it; otherwise one is drawn (seeded).

| species | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Grunt | minor | major | spec-ops needler | spec-ops fuel rod |
| Jackal | minor | major | major | major |
| Elite | minor | major | spec-ops, stealth | commander, stealth major sword |
| Hunter | hunter | hunter | hunter major | hunter major |
| Sentinel | sentinel / defensive | major | shielded | shielded major |
| Flood Infection | infection x5 | infection x10 | carrier | two carriers |
| Flood Combat | Human (AR, pistol, plasma pistol, needler, plasma rifle) | Elite (any armed form) | Human: rocket, sniper, shotgun | Elite / stealth: Flak Cannon (fuel rod), Energy Sword |
| Human (ally) | Marine | armoured Marine | armoured sniper / shotgun major | armoured majors |

Ranking a REPLACED actor (`tier_of`):
- **Grunt:** minor 1, major 2, spec-ops 3, spec-ops fuel rod 4.
- **Jackal:** minor 1, major 2.
- **Elite:** minor 1, major 2, spec-ops / stealth 3, commander / stealth major 4.
- **Hunter:** 3, major 4.
- **Sentinel:** 1, major 2, shielded 3, shielded major 4.
- **Flood (user's rule):** infection 1, carrier 2, combat Human 3, combat Elite / stealth 4.

Design notes the user settled:
- Flood is TWO cards: Infection and Combat.
- Counts are multiplied for infection forms (x5 / x10) and carriers (x2), on the squad's
  Normal and Insane counts, with **no extra starting locations**. H1 has never been
  tested with more actors than starting locations: watch the first boot.
- Unarmed Flood Human forms never count as "basic".
- The Flood Human sniper rifle is kept even though it needs a slot.
- Variants no level ships (Flood Elite with fuel rod or sword, Flood Human with a sniper
  rifle) are built in a slot by `h1_enemy_weapons.Level.clone`. It picks a firing donor
  from the whole-game index and teaches the antr label (`taught 'fr' (from 'pr')`).

---

## 6. The patch-time pass (`h1_species_swap.apply`)

Input: `[{'name', 'species', 'share'}]`, one per active card. `share` is the operator
applied to 0 (+0.1 per pick).

1. **Count the level** on the HIGHEST difficulty: placed enemy squads' Insane counts
   (`enemy_count.h1_squads`).
2. **Eligible encounters:** every placed squad is a plain enemy (no allies, bosses,
   vehicle or turret drivers); no squad is seated by script (`bound`); not a set piece;
   not converted by an earlier card. The weight is the Insane count of squads not
   already of the card's species.
3. **Set pieces** (`setpiece_names`): an ai name anywhere in the argument tree of a call
   whose name contains `command_list`, `vehicle`, `attach`, `detach`, `teleport`,
   `animation` or `set_team`. The compiled H1 scripts keep the function names and the ai
   args' source text in Script String Data (scnr 0x488).
   - Arguments nest: `(vehicle_load_magic v "B-driver" (list_get (ai_actors x/p1) 0))`,
     so walk call groups recursively.
   - Do NOT flag `magic` (`ai_magically_see_encounter` names nearly every encounter),
     `ai_erase` (area cleanup), `ai_braindead`, damage / vitality / drop-item calls. Any
     species takes those.
4. **Draw:** shuffle the eligible encounters with `random.Random(scenario tag name + '|' +
   card name)`. Co-op machines must agree, so never seed from a file name. Take an
   encounter while it brings the total closer to the share.
5. **Convert:** set the encounter's team (Covenant 3, Flood 4, Sentinel 5, Human 2).
   Then repoint every squad's actor type, and EACH starting-location override on its own
   (an infection squad can carry combat-form overrides; a bug found on c20).
6. **Palette entries,** in this order:
   1. an entry already naming the variant;
   2. an entry no squad or override uses any more (`_used_entries`). This includes
      entries a Thunderstorm / Downpour emptied, and the residency-only appends from §2b.
      Recycled entries are claimed, so they are not reused twice;
   3. an append, while the palette is under 64;
   4. a free slot (`fill_slot` with the variant's own weapon and major, aliased);
   5. otherwise the actor keeps its variant, and the log says so.
7. **Shared Level:** the pass builds `h1_enemy_weapons.Level` and leaves it on
   `m._h1_level`. The Armed pass reuses it (`rescan()` re-reads the spawns), so slots and
   aliases are shared and `m.actv_alias` covers both.

---

## 7. Patch order (`halo_patch.apply_run`)

```
weapon ports / difficulty baseline / weapon swaps
skulls loop: Eyepatch, Tilt, Fog, Famine, Assassins(default)   -- Betrayal / Schism only RECORDED
Thunderstorm / Downpour ladder                                  -- who is what
species swap (h1_species_swap)                                  -- who is what, part 2
Betrayal, Schism                                                -- who fights for whom
Assassins (camo_after_ladder option)
Armed cards / first-weapon replacement (h1_enemy_weapons)       -- what they carry
port actv carriers
plan loop: every card op (Spawn Count, stats, colours); species_swap ops skipped (done)
```
- **Betrayal** flips all-human encounters, so Friend Marines' converted encounters turn
  against the player like any Marines. Checked on a10.
- **Schism** flips allied non-human encounters, so Sentinels a card brings into c10/c20
  (allied by script) turn too. Checked on c20.
- Betrayal and Schism were moved after the ladder for every game. The ladder never
  touches humans or allied Sentinels, so nothing else changes.
- The Betrayal skip for `Friend ` cards exempts `species_swap` ops, as it does
  `squad_count`.

---

## 8. Cards and the enhancer

**`halo.json`** (inserted as TEXT so the hand formatting survives):
- **Where:** `Enemy modifiers > General modifiers > <Species> Incursion` (seven cards),
  and `Friend modifiers > Friend Marines`.
- **Why General:** per-species cards are offered only where that species already fights,
  which is the opposite of what an Incursion card is for.
- **Card keys:** `"game": ["Halo 1"]`, `"tag": {"Halo 1": "actv characters\\*"}`,
  `"swap_enemy": [mission enemy names]`.
- **Target:** `{ "step": "+0.1", "field": "Incursion", "species_swap": "<key>", "min": 0,
  "harder_when": "increased" }`. The Friend card uses `"side": "ally"` and
  `"easier_when"`. Direction keys follow the step (validator check 6).

**`halo_enhancer.py`:**
- `ModifierDatabase._build_mod` keeps `swap_enemy` on the card dict. **Trap:** unknown card keys are DROPPED at
  load, so a new card-level key needs adding there.
- **Plan op:** `'species_swap': t.get('species_swap')`.
- **Value text:** the level's enemy total, beside the `squad_count` case.
- **Offers:** `active_run_mods(run_state)` collects every locked-in card;
  `swapped_in_enemies` returns the species of active Incursion cards; and
  `get_enemy_modifiers(..., added=)` and `armed_cards(..., added=)` treat those species
  as fighting on every level. So Hunter cards appear on a10 once Hunter Incursion is in
  the run (12 new offers), and Armed Jackal cards once Jackal Incursion is.
- **apply_run** gets `h1_levels` (the clone donor index needs the ten level files).
- `validate_halo_json.py` and `deadcards.py` list `species_swap` among the
  non-field target keys.

---

## 9. Verification

```
python h1_species_swap_check.py eligible --levels a10,c40
python h1_species_swap_check.py dry --levels a50,d40 --cards hunter,elite,flood combat --share 0.2 --together
python h1_species_swap_check.py e2e --level a10 --cards "flood combat,human" --skulls betrayal
python h1_species_swap_check.py e2e --level c20 --cards "sentinel,flood infection" --skulls schism
python validate_halo_json.py
```
The e2e run patches a temp COPY through `apply_run` with an Armed card and prints the
written map's teams. Nothing touches the live maps.

Known shape of the results:
- a30 and b40 field mostly dropship- or vehicle-seated encounters, so few are eligible
  there.
- Stacked cards saturate. At 20% each, eight cards exceed 100%, and the later cards in
  `ORDER` find nothing left.

---

## 10. Carrying this to another game: checklist

Each answer below was a fixed fact in H1. Find the game's own before building.

1. **Variant unit:** H1 `actv` in the scenario Actor Palette; H2+ `char` in the
   Character Palette. Promotions: H1 Major Variant + squad Major Upgrade; later games
   use the char's variants / rank fields.
2. **Residency rule:** what makes a tag built in, and is runtime residency per zone set?
   H2 loads by zone; H3 / ODST / Reach / H4 use designer zones and resource pools
   (`reach-weapon-residency-pools`, `h3-import-weapon-recipe`). A whole-map tag closure
   is not enough there.
3. **Limits:** palette caps, tag memory (find the BSP load end, as in §1), per-zone
   budgets.
4. **Free anchor refs:** is there a slot-like tag every level carries, with a spare
   reference to the same tag class? Without one, look for any tag with a chainable
   self-class ref, which is what made §2c possible.
5. **Team granularity:** H1 = encounter (+0x24). From the memory census: H2 squad Team
   field (`enemy_count` H2_TEAM), H3 squad team (Betrayal had no per-fire-team team, so
   010's opening squad kept Johnson), ODST / Reach / H4 squads with cells. Decide
   whole-unit conversion from that.
6. **Squad readers already exist** for all six games in `enemy_count.py` (counts,
   scripts, vehicle-seated squads, allies, bosses). Reuse them.
7. **Ladders:** Thunderstorm / Downpour already define per-faction species ladders
   (`halo_patch._TS_FAMILIES`). Tier ladders inside a species need the game's own rank
   variants.
8. **Script set pieces:** H1 keeps function names in Script String Data. H3 / ODST /
   Reach / H4 compiled trees are read structurally (`enemy_count._is_call`, H4 hsdt per
   tag). Port `setpiece_names` per game.
9. **Count past locations:** H3, ODST, Reach and H4 spawn a count past their starting
   locations (confirmed for Spawn Count). H1 and H2 are untested.
10. **Weapons on new species:** H1 has the Armed machinery (slots, donors, antr label
    teaching). Other games need their own route; Thunderstorm already draws weapons from
    the species' loadout.
11. **Test as here:** one level, the species interleaved, teams set, a god shield, a
    deploy/restore `.cmd`, then the kit pass and a full rebuild.

---

## 11. Open / untested
- The cards themselves in game (all eight), including Infection x5 / x10 without extra
  starting locations.
- Marine chain copies spawning with their fixed majors.
- A palette grown past 64 at patch time (appends stop at 64; Armed's own
  `palette_index` may still append beyond it).
- Skull versions of the cards (user: later, "to the extreme").

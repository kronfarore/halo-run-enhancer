# Equipment upgrade lines (plan, 2026-11-27)

A run carries its players' items from game to game. Today an item is "the same item" in
the next game only when both games use the same NAME. This plan groups the Halo 1/2
abilities, the Halo 3/ODST equipment and the Reach/Halo 4 armour abilities into LINES:
an item in a line becomes that line's item in the next game, keeping or refunding the
picks spent on it.

Nothing here is built yet. Every decision below is settled. "User" marks the user's
calls (2026-11-27), "Plan" marks calls made while planning, from the code.

---

## 1. Decisions

1. **A line is one item across games** (user). Entering a new game, a held item of a line
   is replaced by the line's item for that game, with that game's cards.
2. **Two built-in lines, always on, not editable** (user): **Sprint** and **Camo**. They are
   shown read-only at the top of the Options table.
3. **All other lines** live on a new Options page, behind a master switch
   **"Use equipment upgrade lines"** (default off), in an editable table pre-filled with
   the defaults in section 2 (user).
4. **Refunds** (user): an option **"Refund equipment picks when an item upgrades"**
   (default off) with a **share** (default 50 %, 10-100 % in steps of 10). It applies to
   every line change, built-in lines included.
5. **What is refunded** (plan): per player and line, the picks spent on the line's cards
   that applied in the game being left and do NOT apply in the new game ("stranded"
   picks). A card that keeps working in the new game keeps its picks and is not refunded:
   Active Camouflage Reach -> Halo 4 refunds nothing, because the same cards continue.
6. **Rounding** (user): to the nearest whole pick, halves up. At 50 %: 1 -> 1, 2 -> 1,
   3 -> 2, 4 -> 2, 5 -> 3 (at 50 % this equals rounding up). At 30 %: 4 picks = 1.2 -> 1.
7. **The refinement round** (user): for each refunded pick, three random cards of the NEW
   item are offered and the player takes one. No enemy card, no Other slot. A player
   spends all refunded picks of one item, then moves to their next upgraded item, then
   player 2 takes their turn.
8. **Gaps** (plan, from the table's "-" cells): in a game where the line has no item, the
   player keeps the item, it does nothing there, and it continues at the next game that
   has one. That transition is where its refund happens.
9. **One line per item; one item per cell, with one exception** (user): the Decoy line's
   Halo 3 / ODST cell holds Jammer AND Superflare. A player holding both gets ONE
   Hologram; their refunds add up.
10. **Items in no line** (plan) behave exactly as today: kept, dormant where their game
    lacks them, no refund.
11. **Offers** (plan): today a held item is offered to nobody (`drop_weapons_taken`). With
    lines, holding ANY item of a line keeps EVERY item of that line out of every offer,
    for both players.
12. **A denied item counts as "-"** (plan): an item an Option switches off in that game
    (e.g. `remove_superflare_jammer`) leaves the line with no item there.
13. **Direction** (plan): the arsenal always shows the current game's item of the line,
    including when the game is changed by hand or backwards. Refunds happen only when
    "Next level" enters a later game, once per player, line and game.
14. **Unspent refunds lapse** (plan) when the run enters the following game. A history
    note records them.
15. **In the refinement round** (plan) a card's Blacklist button works as elsewhere: it
    blacklists the card and draws a replacement. There is no Reroll. An item with fewer
    than three valid cards offers what it has. With none, its refund lapses, with a note.
16. **The run cannot be saved mid-refinement** (plan), like any other unfinished round.

---

## 2. The default lines

| Line | Halo 1 | Halo 2 | Halo 3 | ODST | Reach | Halo 4 |
|---|---|---|---|---|---|---|
| **Sprint** (built in) | ⚡ Sprint | ⚡ Sprint | - | - | Sprint | Sprint |
| **Camo** (built in) | 👁 Camo | 👁 Camo | Invisibility | Invisibility | Active Camouflage | Active Camouflage |
| Overshield | 🛡 Overshield | 🛡 Overshield | Invincibility | Invincibility | Armor Lock | - |
| Regeneration | ✚ Regeneration | ✚ Regeneration | Regenerator | Regenerator | - | Regeneration Field |
| Shield | - | - | Bubble Shield | Bubble Shield | Drop Shield | - |
| Cover | - | - | Instant Cover | Instant Cover | - | Hardlight Shield |
| Mobility | - | - | Grav Lift | Grav Lift | Jet Pack | Jet Pack |
| Decoy | - | - | Jammer + Superflare | Jammer + Superflare | Hologram | Hologram |
| Turret | - | - | Auto Turret | Auto Turret | - | Auto Turret |

- **No line:** Power Drain, Trip Mine (Halo 3 / ODST); Promethean Vision, Thruster Pack
  (Halo 4). Reach has no Evade item in halo.json.
- **Your settings switch Jammer and Superflare off** (`remove_superflare_jammer`), so the
  Decoy line starts at Hologram until they are switched back on (decision 12).
- **Names are exact halo.json names.** The four Halo 1/2 entries are the pseudo-items in
  `ABILITY_ITEMS`.

---

## 3. How it works today (measured 2026-11-27)

- **Items are carried by exact name.** `player*_weapons` is never rewritten at a game change
  (`on_next_level` -> `on_game_changed` -> `_reset_for_new_round`). A run has no game field;
  the game comes from the mission.
- **An item whose game lacks it goes dormant.** Each subsystem filters it out on its own:
  cards (`_game_ok`, `_weapon_fielded`), placement (`eqip_tag_for` -> None), abilities
  (`_sprint_spec` only for Halo 1/2).
- **Same names are already one item:** the 11 Halo 3 items into ODST (`game_inherits`);
  Active Camouflage / Hologram / Jet Pack Reach -> Halo 4; Auto Turret Halo 3/ODST ->
  Halo 4; Sprint Reach -> Halo 4 (gated by `h4_sprint_mode`).
- **No equivalence table exists.** The only cross-name link is Halo 4's `holder` mode
  (`get_player_modifiers_filtered`): a player holding `⚡ Sprint` is offered Halo 4 Sprint
  cards.
- **Picks are not a currency.** A card's count is derived on every patch from
  `run_state.rounds` by `collect_effects` (halo_patch). Signed counts already work
  (Weapon Identity's inverted half is -1).
- **Weapon upgrades** (`weapon_upgrades`, `unlocked_offer_items`, `_grant_weapon`) ADD the
  upgrade next to the base. Lines REPLACE instead, so they are a separate mechanism.
- **The ability cards** (Sprint Speed / Duration / Cooldown / enable, Overshield Strength,
  Regeneration Amount / Speed, Camo Duration / Cooldown) are General Modifiers tied to
  their ability through the target's `sprint` marker (`ABILITY_CARD_PARAMS`). All nine are
  `"game": "Halo 1"`.

---

## 4. Phase 0: bugs to fix first (found while planning)

**DONE 2026-11-27, commit 26bdac5** (one commit; every check below ran in memory, not
booted). None of the 11 saved runs is affected by #2 or #4.

1. **Regeneration Field is not equipment.**
   - Cause: no Halo 4 mission lists it, so `is_equipment` (any mission's `equipment` list)
     is False.
   - Effect: it is offered as a gun through the map pool, its five cards never reach the
     draft, and it is never placed.
   - Fix: `is_equipment` is also true for every key of halo.json's `Equipment` section.
   - Check: in a Halo 4 offer pool and in the starting-equipment spec, its cards are
     drafted and the placer places it (marker_placement_audit).
2. **Equipment cards' blacklist labels collide.**
   - Cause: `get_mod_label` has no equipment branch, so "Recharge" of Sprint, Jet Pack and
     Active Camouflage all become `General: Recharge`.
   - Fix: add an equipment branch, `<item>: <card>`.
   - Migration in `RunState.from_dict`: a saved `General: <card>` whose card is no General
     card is rewritten to `<item>: <card>` for every item a player holds that has that
     card.
3. **`MagnitudeEditorDialog._remove_effect` ignores `equipment`** when matching. Removing
   one item's card also removes same-named cards of other items. Fix: compare `equipment`
   too.
4. **The patch path ignores Options gates.**
   - Cause: `requires_config` and card-level `ignore` are checked only for offers
     (`filter_blacklisted`). Existing picks keep patching, e.g. Reach Sprint picks write
     Halo 4 sprint fields with `h4_sprint_mode` off.
   - Fix: `on_patch_map` marks such picks excluded, as it does for `_game_ok`.
   - Also: `map_equip_mod` must not synthesize Map Presence for an item none of whose
     cards pass `_config_ok` in that game.
5. **The nine ability cards are Halo 1 only**, yet Halo 2 runs the same four abilities.
   - Measured: all 13 Halo 2 baselines carry the script's tuning globals; `os_body` and
     `medi_heal` are absent but unused by Halo 2's path.
   - Fix: `"game": ["Halo 1", "Halo 2"]` on all nine, edited textually (json_spans), then
     `validate_halo_json.py`.
   - Check: in memory on all 13 Halo 2 baselines, every card writes its global
     (`_apply_sprint` rows).

---

## 5. Data model

**Phase 1 DONE 2026-11-27** (halo_enhancer.py, after `denied_equipment`; check:
`python sprint_toolkit/equipment_lines_check.py`, all passing). As built:
- A cell with no key follows `game_inherits` (ODST follows Halo 3); an explicit `[]` is a
  gap. The defaults leave ODST out.
- `CONFIG['equipment_lines']` is filled with the defaults at import, so settings and run
  snapshots hold a concrete table.
- Every lookup takes the database: `active_lines(db)`, `line_of(db, item)`,
  `line_stage(db, line, game)`, `line_cards(db, line, game)`; plus `line_item_off`,
  `line_card_key`, `line_game_items`, `validate_lines`, `refund_picks`.
- "Switched off" (decision 12) covers: denied equipment, an ability outside Halo 1/2 or
  with `sprint_feature` off, and equipment whose every card there is config-gated (Halo 4
  Sprint with `h4_sprint_mode` off).
- Measured: no Reach card of Camo, Mobility, Decoy or Sprint (restore) is stranded in
  Halo 4; Halo 1 and Halo 2 hold the same ability cards; Halo 3 and ODST the same
  equipment cards.
- A run saved without the keys loads with `equipment_lines_enabled` and
  `equipment_refund_enabled` off (`RunState.from_dict`).

**Code** (halo_enhancer.py):
- `BUILTIN_LINES`: the Sprint and Camo rows, as `{name, stages: {game: [item, ...]}}`.

**CONFIG keys**, all in `OPTION_KEYS`, so they reach settings.json and every saved run's
`options` snapshot:

| Key | Default | Meaning |
|---|---|---|
| `equipment_lines_enabled` | `False` | table lines active |
| `equipment_lines` | the seven non-built-in rows of section 2 | `[{name, stages: {game: [items]}}]` |
| `equipment_refund_enabled` | `False` | refunds on |
| `equipment_refund_percent` | `50` | refund share |

**Lookups** (pure functions, unit-checked):
- `active_lines()`: built-in rows, plus table rows when enabled.
- `line_of(item)`: the line and the games the item stands in.
- `line_stage(line, game)`: the cell's items, minus items denied in that game.
- `line_cards(line, game)`: the cards of the line's items that apply in a game. Equipment
  cards come from the `Equipment` section through `_game_ok`; ability cards come through
  `ABILITY_CARD_PARAMS`.

**Validation**, on load and on Save in Options:
- An unknown item name is dropped, with a warning row in the dialog.
- An item already used by an earlier line, or by a built-in line, is dropped from the
  later one.
- An empty line is removed.

**RunState** (saved in .run; loaded defensively with `data.get(...) or default`):
- `line_log`: a list of `{player, line, game, from: [items], to: item | None, stranded,
  refund}`, one entry per transition done. It drives the "once per player / line / game"
  rule (decision 13) and the arsenal tooltip.
- `pending_refinement`: `{player: [{line, item, game, picks}]}`, refunds not yet spent.

**Rounds:** each refinement pick is one round.
- `{'kind': 'refinement', 'game': G, 'player1': {'weapon': <new item>, 'mod': <card>,
  'gained_weapon': None, 'refinement': {'line': name}}, 'player2': {'weapon': ...,
  'mod': None, ...}}`.
- Enemy, Other, boss and skull slots are `None`.
- Both player dicts are always present (`update_history` needs them).
- The card counts +1 through `collect_effects`' ordinary path: no new branch.

---

## 6. Transitions (entering a new game)

**Hooks:**
- The game-change branch of `on_next_level` runs transitions with refunds.
- `on_game_changed` (a manual change) runs the rename only.

**For each player and each active line they hold:**
1. **Find the cell.** `stage = line_stage(line, new game)`. If it is empty, nothing
   happens: the item stays and is dormant.
2. **Rename.** Replace every held item of that line with the stage's first item; two held
   items of one line collapse into one. If the item is already that item, nothing
   happens.
3. **Refund** (Next level only, option on, no `line_log` entry yet for player, line and
   game):
   - The previous game is the game being left. If the line had a gap, it is the last
     earlier game where the line had an item.
   - `stranded` = the player's picks (from `collect_effects` over the rounds so far) on
     `line_cards(line, previous game)` that are not in `line_cards(line, new game)`.
   - `refund = round_half_up(stranded * percent / 100)`.
   - If the refund is above 0, append it to `pending_refinement[player]`.
4. **Log.** Append to `line_log`, and lapse the previous game's unspent
   `pending_refinement` entries with a history note.

**Worked example (Camo line, refunds at 50 %):**

| Transition | Item | Cards | Stranded | Refund | Then |
|---|---|---|---|---|---|
| Halo 1 -> Halo 2 | `👁 Camo` stays (same item) | Halo 1/2 cards continue (Phase 0 #5) | 0 | - | - |
| Halo 2 -> Halo 3 | becomes `Invisibility` | 3 Camo Duration picks don't apply | 3 | 2 | 2 refinement picks of Invisibility cards |
| ODST | stays `Invisibility` | inherited | 0 | - | - |
| ODST -> Reach | becomes `Active Camouflage` | Invisibility picks don't apply in Reach | Invisibility picks | 50 % of them | - |
| Reach -> Halo 4 | stays `Active Camouflage` | its cards cover Halo 4 | 0 | - | - |

**Sprint line:** `⚡ Sprint` sits out Halo 3 and ODST (dormant), then becomes `Sprint` at
Reach. The refund is computed there from the Halo 1/2 picks.

---

## 7. The refinement round

- **Button:** "♻ EQUIPMENT REFINEMENT" next to "🧬 WEAPON IDENTITY", enabled while
  `pending_refinement` holds picks for the current game.
- **Recommended step:** `recommended_kind(0)` returns `refinement` while refunds are
  pending. After the round, the button re-arms with today's first-level step (New Anything
  / New Equipment / New Weapon / Generate).
- **Order:**
  1. Player 1's upgraded items, in table order (built-in lines first), all picks of one
     item before the next.
  2. Then player 2, in the same order.
  3. A player with nothing pending is skipped.
- **One offer:**
  - Header, e.g. "Player 1 · Camo -> Invisibility · refund pick 2 of 3".
  - Three distinct cards of the new item, drawn by `_weighted_pick` from
    `get_equipment_modifiers_filtered(item, blacklist, game)` (saturated and blacklisted
    cards are already excluded).
  - Clicking a card records the round and moves on.
- **Round walkers:** every walker the planning survey listed is reviewed. `refinement`
  rounds are left OUT of:
  - the death penalty `len(rounds)`;
  - the levels' `rounds` / `rounds_total`;
  - `_update_special_counters` and `_update_weapon_card_misses`.

  They are counted IN:
  - `collect_effects`, `_round_mods`, `_card_picks`, `_this_round_keys`;
  - `_remove_effect`, `update_history` / `_round_summary` (shown as "♻ Refinement").
- **Saving:** `_mid_picking_round` is true while the round is unfinished.

---

## 8. Other rules

- **Offers:** `drop_weapons_taken` and every offer pool (`_anything_offer_pool`,
  `_equipment_offer_pool`, `RunEnhancer._new_equipment_pool`, `ability_offer_pool`) treat
  all items of a held line as taken. The H1/H2 one-ability-per-player and per-run rules
  stay.
- **Halo 4 `holder` mode:** "holds `⚡ Sprint`" becomes "holds the Sprint line". Outside
  `off`, a player who came from Halo 1/2 is a holder. The renamed Reach / Halo 4 `Sprint`
  already counts as equipment.
- **Starting equipment / placement:** unchanged code. It reads the renamed arsenal names,
  so a renamed item is placed like a freshly drafted one.
- **Display:**
  - The arsenal shows the current item.
  - Its tooltip shows the line and where it came from, e.g. "Camo line: 👁 Camo (Halo 1) ->
    Invisibility (Halo 3)".
  - A dormant item is marked "(inactive in <game>)".
- **History:** transitions and lapsed refunds appear as lines in the run history.

---

## 9. Options page "Equipment lines"

A new navigation page after "Loadout", with two group boxes.

**"Equipment upgrade lines"**
- Checkbox "Use equipment upgrade lines" (`equipment_lines_enabled`).
- Table: columns are Line, Halo 1, Halo 2, Halo 3, ODST, Reach, Halo 4; one row per line.
  - The Sprint and Camo rows are greyed and read-only, always shown.
  - Each cell is a button showing its items ("-" when empty, "Jammer + Superflare" for
    two). It opens a checklist of that game's items.
  - The checklist lists the union of the game's `level_equipment` lists, plus the four
    ability items for Halo 1/2.
  - An item already used in another row is disabled there.
  - The ODST cell follows the Halo 3 cell until it is edited.
- Buttons: Add line, Remove line, Restore defaults.
- Validation warnings in a label under the table (section 5).

**"Refunds"**
- Checkbox "Refund equipment picks when an item upgrades" (`equipment_refund_enabled`).
- Spin box "Refund share" (10-100 %, steps of 10, `equipment_refund_percent`).
- The tooltip, in player terms, explains the rounding and the refinement round.

**Wiring:** CONFIG defaults, `OPTION_KEYS`, the widgets, and `values()` entries. The table
value is the JSON list. A run saved before these keys existed keeps everything off.

---

## 10. Phases and checks

| Phase | Work | Done when |
|---|---|---|
| 0 | Section 4's five fixes | each fix's check passes; marker_placement_audit Halo 4 still 9/9 equipment |
| 1 | `BUILTIN_LINES`, CONFIG, validation, lookups | a script asserts every default item exists in its game (halo.json lists or `ABILITY_ITEMS`), no item is in two lines, and `line_cards` returns the expected cards per game |
| 2 | Transitions (rename, dormant, `line_log`), offer rule, display | scripted RunState walk H1 -> H4 (no GUI): arsenal names per game match the table, including gaps, merges and denied items |
| 3 | Refunds, `pending_refinement`, refinement round, walkers, save guard | same walk with refunds at 50 %: refund counts match section 6, refinement rounds raise card counts in `collect_effects`, death penalty and level round counts unchanged, .run save -> load round trip, an old run loads with everything off |
| 4 | Options page | offscreen dialog build: table defaults, read-only built-in rows, a cell with two items, validation warnings, values round trip into CONFIG |
| 5 | Docs + memory | this file updated with results; memory note |

Each phase is one commit or more on master, pushed (the standing rule).

**In-game:** the mechanism is run-side (names, rounds, counts), so map patches are
unchanged except Phase 0 #4 and #5. One boot per affected game is enough:
- a Halo 2 level with an ability card (Phase 0 #5);
- Halo 4 with `h4_sprint_mode` off after a Reach Sprint pick (Phase 0 #4).

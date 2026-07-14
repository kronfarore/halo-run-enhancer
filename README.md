# Halo Run Enhancer

A GUI tool for co-op Halo: The Master Chief Collection runs. It rolls tied
modifier pairs each round, lets two players draft them turn-by-turn, and then
**patches the chosen effects directly into the game's `.map` files** (Halo 1 and
Halo 2, with Halo 3 support in progress), resolving fields through the Assembly
plugin definitions — no recompilation, just byte edits.

## Installation & running

1. Install Python 3.8+.
2. `pip install -r requirements.txt`
3. `python halo_enhancer.py`

`halo.json` (the modifier database) auto-loads from the application folder.
Map and plugin locations are read from the config (`assembly_plugins_dir`,
`plugin_subdirs_by_game`, `map_game_folder`).

## How a run works

1. **Weapon selection** — each player picks a starting weapon (exclusive: the two
   players never get the same one).
2. **Rounds** — every round generates **3 pairs** for the current player. A pair
   ties a **positive** player effect to a **negative** enemy effect: taking the
   buff means taking the debuff. Player 1 drafts first, then Player 2.
3. **The 3rd slot** — a pair may also carry one of these (mutually exclusive):
   * 🎲 **Wildcard** — a bonus "friend" effect (chance set by *Wildcard chance*).
   * ☠ **Boss** — on boss levels, every pair carries a guaranteed boss-tuning card.
   * 🜂 **Exhaust** — see below.
4. **New weapons** — a pair can instead offer a new weapon (chance set by
   *New weapon chance*) rather than a positive modifier.
5. **Reroll / Blacklist** — any card can be rerolled individually, or blacklisted
   so it never appears again this run.
6. Effects accumulate across the whole run (a roguelike escalation): everything
   picked so far is re-applied to each map you patch.

### Exhausts (one-map debuffs)

An **Exhaust** is a negative effect drawn into the 3rd slot with a per-pair
chance (*Exhaust chance*, default 10%, non-boss levels only). Unlike normal
effects it is **active for only one map**:

* It's drawn from negatives **not already active**, so it never overlaps an
  existing debuff.
* It is bound to the mission it was rolled in and is patched into that map only.
  Once you move to a different mission it's dropped automatically.
* **Compensation:** the player who picked it gets one **no-negative choice** next
  round — one of their three pairs comes with no enemy debuff ("✦ NO ENEMY BUFF").

## The patcher (magnitude editor)

"Patch to map" opens the magnitude editor: every selected effect with its
tunable fields. For each field you type an **operator** that transforms the
vanilla value; the vanilla value(s) for the current difficulty are shown on the
right for reference.

### Operators

| Input        | Meaning                          |
|--------------|----------------------------------|
| `=5` or `5`  | set to 5                         |
| `+5`         | add 5                            |
| `-0.3`       | subtract 0.3                     |
| `*1.2`       | multiply by 1.2                  |
| `x1.2`       | multiply by 1.2 (same as `*`)    |

Both `.` and `,` work as the decimal separator (`x1,5` = ×1.5). Angles are
edited in degrees. Empty fields are left untouched.

The post-patch summary reports three buckets:

* **Applied** — a real byte change was written.
* **Skipped** — a deliberate no-op (e.g. a scope already present, a weapon whose
  swap rate rounds to zero, an H2-only field on an H1 map). Skips never trigger
  a save.
* **Failed** — an edit that should have landed but didn't (field not found, tag
  absent, etc.).

**Debug mode** adds a `⤓ field` button to each field (patch just that one field
onto the live map, incrementally) and a `＋ field` / `🔍 ADD MOD` control for
injecting arbitrary fields/effects.

## The `.bak` file — read this

The first time you patch a map, the tool writes a one-time **`<map>.bak`** — a
pristine copy of the original, untouched map. This backup is important:

* **Patching is idempotent.** Every full patch rebuilds the map **from the
  `.bak` baseline** and re-applies the current effect set. So re-patching a map
  never double-applies (a `×1.5` applied twice stays `×1.5`, not `×2.25`), and
  dropping an effect (e.g. a spent Exhaust) cleanly removes it — the baseline
  restores the original bytes and only the remaining effects go back in.
* **Do not delete the `.bak`.** It is the canonical original. Deleting it makes
  the current (patched) map the new baseline, permanently baking in whatever is
  there. To fully restore a map to vanilla, copy its `.bak` back over the `.map`.
* **Manual edits are not preserved.** Any change you make to a `.map` outside
  this tool (e.g. in Assembly) after its `.bak` exists will be discarded on the
  next full patch, because the patch starts from the baseline. The one exception
  is the debug `⤓ field` button, which patches the live file incrementally.
* A patch that writes nothing (all Skipped/Failed) leaves the map and `.bak`
  untouched — so a failed patch never corrupts state, and a pending Exhaust stays
  pending until a patch actually succeeds.

## Options

| Option | Effect |
|---|---|
| **Target difficulty** | Which difficulty's values the tool reads/tunes (Easy/Normal/Heroic/Legendary tiers). |
| **Cross-game only** | Drop mods that only exist in one game. Forces boss removal on while set. |
| **Remove boss mods** | Suppress the guaranteed Boss card on boss levels. |
| **Wildcard chance** | Per-pair chance of a Wildcard in the 3rd slot. |
| **Exhaust chance** | Per-pair chance of a one-map Exhaust (non-boss 3rd slot). 0 disables. |
| **New weapon chance** | Per-pair chance a pair offers a new weapon. |
| **Combine Heretic Leader & holograms** | On patch, Heretic Leader cards tune the leader and his decoy holograms together. |
| **Set starting weapons / Zoom UI** | Patch player starting loadout; add a scope overlay to scopeless weapons. |
| **Debug mode** | Expose per-field patching and the add-mod tools. |

Runs can be saved and loaded; a saved run restores the options it was played with.

## Credits

* **Halo 3 base maps** — the Halo 3 campaign maps used for Halo 3 support are the
  cutscene-free rebuilds from **"Halo 3 Cortana Begone" by TacoUpgrade**
  ([Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3567825314)).
  Verified to differ from the stock maps only by the removal of the Cortana
  cutscene scripting (plus the unavoidable rebuild reindexing), so they patch
  identically to vanilla.
* **Tag/field definitions** — this tool resolves map fields through the Assembly
  plugin XML from [XboxChaos/Assembly](https://github.com/XboxChaos/Assembly).

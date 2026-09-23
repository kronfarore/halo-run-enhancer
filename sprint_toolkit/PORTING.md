# Porting a weapon into another Halo game

The reusable recipe, written from the two ports that are finished: the Halo 4 **SAW**
into **Halo 1** and into **Halo 3**. Tool names still say `saw_` because it was the first
one; they take the weapon as an argument.

Source weapons come from **H4EK** (`F:\SteamLibrary\steamapps\common\H4EK`), which is the
only kit that ships real source tags for every weapon.

---

## What "ported" actually means

A port is not done when it appears in game. Nine things have to be true, and Halo 3
quietly shipped without the last three until the user caught it:

| # | step | H1 | H3 |
|---|------|----|----|
| 1 | geometry: first-person AND world model, on the target's skeleton | done | done |
| 2 | textures / shaders | done | done |
| 3 | its own projectile + damage effect, so numbers do not leak to the donor | done | done |
| 4 | numbers: the source game's values in the tags | done | done |
| 5 | balance rows, with per-game field coverage audited | done | done |
| 6 | ammo pickup: which item tops it up (a port has none of its own) | done | n/a |
| 7 | ammo meter / HUD readout sized for the port's magazine | done | done |
| 8 | pickup icon, and the HUD schematic beside the ammo | done | done |
| 9 | reload and swap animation timing | done | done |

Step 6 is a **port detail, not a general option**: a port inherits the donor's pickup
item, and the dropdown only re-points it when several weapons share one. Halo 4 has no
ammo pickups at all.

---

## Halo 1

Everything runs through `saw_build.py`, which does the whole thing and always restores
the scenario even when the build fails:

    python saw_build.py --scale 1.0 [--skip-bitmaps] [--no-deploy]

What it chains, and what each piece is for:

1. `tool bitmaps weapons\saw\bitmaps` — TIFs are already in the HCEEK data tree.
   Source pixels come from `h4_bitmap.py`, because **H4EK's own exporters fail**
   ("rasterizer\invalid"); decode the tag directly. The pixel blob follows its u32 size
   (= mip chain + 8) and that value also appears earlier in the chunk header — **take the
   last match**. Plain linear DXT, no byte swap.
2. `saw_shaders.py` — shader_model tags. **A Halo 1 shader needs a multipurpose map** or
   the weapon renders white: R = reflection mask, G = self-illum, B unused, A white. Take
   R from H4's control map.
3. `saw_to_jms.py <rm.xml> <out> [scale]` — H4 render_model to JMS on the **donor's
   skeleton**, so the donor's animations drive it. See *Reading H4 geometry* below.
4. `tool model weapons\saw\fp` and `weapons\saw` — gbxmodels.
5. `make_icon.py` + `add_msg_icon.py` + `saw_weapon.py` — see step 8 below.
6. `saw_scenario.py` — puts the weapon in the test map's spawn profiles. On a10 use only
   the three spawn profiles; the others drive mechanisms.
7. `tool build-cache-file levels\a10\a10 classic none 1` — **must be `classic`**;
   read_write/remastered corrupts, and a human weapon forces classic anyway.
8. `saw_scenario.py --restore` — always.
9. deploy; the original stays as `a10.map.before_saw`.

**Step 7, the ammo meter.** `ammo_meter.py <N> <tag base>` renders the tick art for any
magazine. The readout is two `weapon_hud_interface` elements on loaded ammo: a STATIC
silhouette sheet and a METER sheet whose **luminance is the tick's threshold** and alpha
is the shape. The engine meter runs **0..255, not the AR art's 0..240** — threshold of
tick k is `step * k` with `step = 255 // N`, which is also the element's
`alpha_multiplier`. Getting that wrong fills two ticks per round and tops out early.

**Step 8, the pickup icon.** The icon is `weapon_hud_interface`
`messaging_information.sequence_index` into the **shared** sheet
`ui\hud\bitmaps\combined\hud_msg_icons`. `make_icon.py` renders one from the weapon's own
JMS in the stock style (outline 235 grey a~230 over fill 79 grey a~59); `add_msg_icon.py`
**appends** a new bitmap and sequence so stock indices are untouched, and is idempotent
from its own backup of the stock tag.

**Step 9, animation timing.** Multipliers are `balanced_frames / BUILT_frames`, not a raw
ratio. `port_anim_measure.py` measures frame counts and reproduces the table, which is
what makes it trustworthy for other games.

---

## Halo 3

Halo 3 has no single orchestrator; the order is:

    h3_make_saw.py          clone the donor weapon, projectile, effects
    h3_saw_wire_model.py    fp model
    h3_saw_world_model.py   world model      (h3_saw_world_revert.py undoes it)
    h3_saw_textures.py      bitmaps + shaders
    h3_saw_chud.py          clone the donor chud and repoint the weapon at it
    h3_meter_art.py         the ammo meter art          (step 7)
    h3_chud_sequence.py     which sprite that chud draws (step 7)
    h3_weapon_glyph.py      the pickup icon glyph        (step 8)
    h3_weapon_schematic.py  the HUD schematic            (step 8)
    h3_saw_pickup_icon.py   the weapon's five message string ids (step 8)
    h3_mcc_localization.py  the strings the game ACTUALLY shows  (step 8)
    h3_saw_animations.py    retime reload / ready         (step 9)
    h3_build_map.py         build
    h3_saw_deploy.py        install + baseline, and --check
    h3_apply_saw_numbers.py balance rows onto the map

### The traps, each of which cost a build

* **`tool build-cache-file` exits 0 when it crashes.** Two arguments, scenario and `pc`,
  and **backslashes** in the scenario path. Always build through `h3_build_map.py`, which
  demands the success string *and* an advanced mtime. See `h3-build-cache-file-trap`.
* **The cache builder deduplicates identical blocks.** A byte-identical clone shares its
  donor's blocks, so the clone must DIFFER before the build. `h3_saw_deploy.py --check`
  proves ownership from map data — run it after every build.
* **Run the tag tools for real.** `h3_saw_chud.py` had only ever been run dry once, so
  the weapon still pointed at the AR's chud.
* **`h3_apply_saw_numbers.py` restores from the baseline first.** Animation scaling is not
  idempotent; without the restore, "originals" silently keeps the balanced frame count.
* **`apply_field`'s `index` addresses the OUTERMOST block.** For chud Sequence Index that
  means index 0 silently rewrites a different widget. Use `h3_chud_sequence.py`.

### Step 7, the ammo meter

`ui\chud\bitmaps\ballistic_meters` is a sheet of sprites, each a **grid of ticks whose
cols x rows equals the magazine**, and the **blue channel is the tick's threshold**. The
largest Halo 3 ships is 60, so a bigger magazine needs a sprite drawn. Two rules, both
learned from in-game artefacts:

* **Blue is a property of the CELL, not the tick.** It runs as an unbroken staircase
  across the whole sprite; a gap left at 0 means "still loaded" and leaves an outline on
  spent ticks. Fill the field first, stamp the art over it without touching blue.
* **Pad downward and rightward**, the way Bungie does: the band boundary is the next
  tick's first row.

### Step 8, the icons

Read `mcc-localization-overrides-tags` **first**. The prompt's icon is a **character
inside the message string**, and MCC takes that string from
`data\UI\Localization\<LANG>_Halo3.bin`, a loose file — not from the map. The weapon tag's
**five** string ids (`pickup`, `swap`, `picked up`, `switch-to`, `switch-to from ai`)
choose which entry; the localization file supplies its text and glyph. Patch both.

Glyph and schematic are drawn from the port's **own geometry**, not by hand — see
`h3_weapon_glyph.py`, which documents the model-XML traps. The glyph box **is** the
on-screen size; borrow a shipped glyph's exact dimensions.

### Step 9, animation timing

`h3_saw_animations.py` retimes by NAME and clones **both** graphs the weapon references
(masterchief and dervish — fixing one leaves the other shared). Build at the **longest**
timing needed, because the patcher can only shorten. See `h3-animation-format` for the
format and its three traps.

---

## Reading H4 source data

    tool export-tag-to-xml <ABSOLUTE tag path> <out.xml>

Relative paths fail with "not located in the tags directory structure". Three things
about the render_model XML cost time every time they are rediscovered:

* positions are **compressed to 0..1** and need expanding through the compression bounds;
* `position bounds 0` and `1` are **six floats paired per axis**, not min then max — the
  tell is that the middle pair comes out symmetric, which is the weapon's width;
* `raw indices` is a triangle **STRIP**; read as a list it draws a discus.

`extract-import-info` fails on H4 tags — there are no original source files to recover.

---

## Balance

    balance_compare.py "<weapon>" "<source game>" "<target game>"

Reads every card-reachable field from the **pristine baselines** in both games and gives
the ratio per field; `balance_port.py` turns that into the port's balance rows.
`port_coverage.py`, `port_field_matrix.py` and `port_gap_check.py` audit which fields a
game actually exposes, so a missing row is a known gap rather than an oversight.

Ports carry their ORIGINAL numbers by default; the balance option swaps in the derived
values, and damage moves by the same ratio.

---

## Dependencies

`port_env.py` puts the vendored Reclaimer stack under `pylibs/` on `sys.path` — pure
Python, no compiler. Import it before anything from `reclaimer`.

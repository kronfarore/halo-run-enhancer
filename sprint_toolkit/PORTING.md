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

**The rule for the TEXT: blank it, do not rename it.** A port has no lines of its own, so
rewording one means taking a live weapon's — and that weapon is then wrong for the rest of
the game. The lines that matter carry a SYMBOL rather than a name (the pickup prompt is
`<button> to pick up <glyph>`), and those are already right for any weapon, because they
never say what it is. So:

* a line that would have to be **borrowed** is blanked — filled with SPACES, which keeps
  the entry, its offset and the file's length, and shows as nothing;
* a line that carries only a symbol is **left alone**;
* a line the port genuinely OWNS may be reworded. That is the Halo 2 case below: the cut
  donor came with its own three lines and nothing else uses them.

Blanking by terminating the string early does NOT work — the freed bytes become new
entries and renumber every string after them. That is the "CARNAGE REPORT" failure.

### Step 9, animation timing

`h3_saw_animations.py` retimes by NAME and clones **both** graphs the weapon references
(masterchief and dervish — fixing one leaves the other shared). Build at the **longest**
timing needed, because the patcher can only shorten. See `h3-animation-format` for the
format and its three traps.

---

## Halo 2

The donor is `objects\weapons
ifle\gpmg`, a **cut** Bungie LMG that is in no
scenario's palette but still owns its own first-person model, HUD and the full set of
pickup message string ids. Nothing live has to be hijacked -- the ceiling the Halo 3 port
ran into does not exist here. See `halo2-weapon-port-donor`.

    tool extract-render-data <render_model>     Bungie's ORIGINAL .jms, unzipped from the tag
    saw_to_jms_h2.py <storm_lmg_rm.xml>         H4 geometry onto the donor's skeleton
    h2_jms_preview.py <out.png> <jms...>        look before importing
    tool render objects\weapons
ifle\saw       and \sawp_saw
    h2_tagref.py <tag> --set <class> <old> <new>  repoint a reference (model, weapon, ...)

### Step 1, geometry

Halo 2 is the **easiest of the three** to read, because `extract-render-data` hands back
the source: the tags still carry the zipped .jms, where `extract-import-info` finds
nothing on H4's. So the skeleton, rest pose, markers and material strings are Bungie's
own file rather than something reconstructed from a tag dump.

* **JMS 8210 is not JMS 8200.** Reclaimer writes Halo 1's, and only that, so `write_jms`
  cannot be aimed at Halo 2: nodes carry a parent index instead of child/sibling links,
  triangles name only a material, and there is **no REGIONS section at all** -- region and
  permutation are parsed out of the material's second line, `(1) base gun`. `h2_jms.py`
  implements the format and proves it, writing all four extracted files back byte for byte.
* **Node translations are absolute**, not parent-relative as in Halo 1.
* **JMS v is 1 - the tag's v.** Measured against the donor, not assumed.
* Place the mesh by the donor's `right_hand` marker: the H4 weapons are authored with
  their root bone ON the grip, so the two grips then coincide and the hand the animation
  drives is right by construction. Scale is settled by the grip-to-foregrip span -- for
  the SAW into the GPMG that came out at 1.0, and the left hand landed within half a unit
  without moving a marker.
* **Halo 2 fires from the barrel marker the weapon tag names**, and for the GPMG that is
  `primary_trigger`, not a `muzzle_flash` -- there is no muzzle marker in the file at all.
  It sits 32 units out, past the end of a shorter gun, so it has to be moved or the flash
  hangs in mid air.

`tool render` reports far fewer triangles than it was given (13836 -> 8361 for the SAW).
That is welding, not loss: the surface area is **98.4%** of what went in, and the shape
is whole. Check the area, not the count.

### Step 2, textures and shaders

`h2_saw_textures.py` decodes the Halo 4 maps, imports them and repoints the shaders.

* **A Halo 2 bump map is a HEIGHT map**, not a normal map (`usage = height map`,
  `bump height 4.0`). Halo 4's is tangent-space normals, so it has to be integrated back
  into a height field -- Poisson, solved with an FFT, then high-passed, because an atlas
  is dozens of unconnected islands and the solution drifts between them.
* **Seed each .bitmap tag from a Bungie one.** The import keeps a tag's settings and
  there is no way to set `usage` short of editing bytes, so a bump map created from
  nothing is silently wrong. FORMAT is not inherited -- tool picks it from the content.
* `p8-bump` is gone from H2EK's tool; bumps come out `x8r8g8b8`, 11 MB at 2048x1024, so
  import the bump at **512x256**. Save the colour plate as RGB: an 8-bit 'L' TIFF
  imports without a word of complaint.
* **Measure the relief against the game.** Straight integration gave half Halo 2's slope
  (std 8/12 per channel against the SMG's 21/27); a gain of 2.2 brings it to 14/22. The
  tool prints both every run.
* `tex_bump` cannot self-illuminate. For a glowing part, clone a shader that already
  uses `tex_bump_illum` -- the shotgun's lit sight uses one map as both base and
  self-illum, which is exactly a weapon's display panel.

`h4_bitmap.py`'s pixel finder had a real bug, fixed here: the marker before the pixels is
the mip chain **+8 for dxt1, +0 for a single-mip dxt5 and +16 for dxn**, and searching
only for +8 put the SAW's normal map 196 bytes late -- mid block, decoding to noise while
still consuming the file to its last byte, so the arithmetic looked perfect. Candidates
are now decoded and the quietest wins.

### Steps 3 and 4, ownership and numbers

`h2_saw_weapon.py` then `h2_saw_numbers.py`.

The cut GPMG borrows the Warthog turret's ammunition, so its projectile and both damage
effects are shared with `h_turret_ap.weapon`, a live weapon on real maps -- tuning the
port through them retunes the Warthog. Clone the projectile and both damage effects; the
melee effects and the pickup sound stay shared, as they do in the Halo 1 and Halo 3
ports, so a melee balance row would move every weapon in the game.

**Numbers need `h2_tagfield.py`, and the Assembly plugins cannot help.** They give cache
offsets; the weapon's root struct is 0x31C bytes in a cache and 0x5F4 on disk, and the
difference is not a conversion -- solving it for the wider references, blocks and string
ids has no whole-number answer, so the loose struct holds editor data the cache does not.
Instead each field's offset is FOUND: read what tool says the field is, list every place
in its own element whose bytes decode to that, write a probe into each and export again;
the offset is where that field alone changed. Distinctive values resolve in one or two
tries, and the answers are cached.

Four things that bite:

* **Angles are stored in radians and printed in degrees.** Searching for the 1.0 tool
  prints finds nothing; 0.0174533 finds it exactly.
* **A field name is not unique.** tool flattens a block's nested structs into one list,
  so `barrels` prints two "minimum error" fields and two "error angle"s -- the live ones
  are the second. Take the wrong one and the spread lands in the rate of fire.
* **A field reading zero cannot be found at all**, because padding reads zero too. Say so
  rather than guess.
* **Probe into a COPY.** A probe lands wherever the search says, and sooner or later that
  is a string id length or a block count, which stops the tag loading. Probing the real
  tag destroyed one when an interrupted run could not write its restore back.

### Steps 6 and 7, ammo pickup and the HUD readout

**Step 6 is n/a in Halo 2**, as in Halo 3: there are no ammo items, you top up from
dropped weapons. A Halo 2 weapon's nested `magazines` block is the physical magazine
thrown out during a reload, not a pickup -- the SMG and shotgun use it, the GPMG does not.

**Step 7.** `h2_saw_meter.py`. Halo 2 draws the ammo readout as ONE bitmap of tick art,
revealed as the magazine empties, so the tick count is purely a property of the art.
Bungie's, measured:

    battle_rifle_meter  197x34   2 rows of 18 = 36   tick 6px wide, row pitch 17
    smg_meter           198x42   3 rows of 20 = 60   tick 6px wide, row pitch 14

The tick is **6 pixels wide in both**; the magazine changes the rows and their spacing.
Keep the donor's canvas so the widget does not move, lift the tick sprite and the cyan to
green ramp out of the donor's own meter, and only the row pitch changes.

Give the port its **own HUD**: clone the donor's `new_hud_definition` and repoint the
weapon at it, so the donor's stays as Bungie left it.

### A borrowed effect brings its own conventions

Worth knowing before borrowing any effect. The port's muzzle flash sat above the muzzle,
and the marker was not at fault -- it measured 0.07 units off the centre of the barrel
opening. Bungie's SMG carries its barrel marker **1.40 units BELOW its own bore**, so the
SMG's firing effect is authored to draw that far above where it is emitted. Hung off a
marker that is actually on the bore, it floats. Measure the donor's marker against the
donor's bore, and adopt the difference.

### Editing tags

There is no XML importer, so tag edits are byte edits. A tag reference is 16 bytes with
the class 4CC REVERSED, and the path is pooled elsewhere -- and since the file is laid
out in strict field order, a struct's paths are interleaved with its child blocks, so
which record owns which string cannot be recovered from the bytes alone. `h2_tagref.py`
therefore edits **by class and current path**, refuses anything ambiguous, and re-exports
with tool.exe afterwards to prove the list changed in exactly one place, restoring the
file if it did not.

`tool verify-tag-load` proves nothing: it is silent for a good tag AND for one that does
not exist.

---

## The icon supply, and why it has to grow

A port needs a pickup glyph, and taking a shipped weapon's is only tolerable once. There
are a limited number of icons and a great many more weapons to port, so the list has to be
extensible or the whole pipeline has a ceiling built into it. This should have been
settled at the end of the Halo 3 port and was not.

What is established, for Halo 3:

* **The official build path cannot add one.** `tool font-package` takes codepoints from a
  name table compiled into tool.exe — alphabetical from 0xE112 — and a tif whose name is
  not in that table aborts the run. The set of names is fixed at the tool.
* **The container is not fixed.** `font_package_icon.bin` is four fonts and four character
  map tables, each an array of 8-byte entries (u16 codepoint, u16 font index, u32 glyph
  offset), at 0xC000-spaced blocks holding 92, 64, 69 and 66 entries — in blocks with room
  for thousands. The glyph payload is a codec `h3_font_codec.py` reads and writes exactly,
  in both directions, across all 73895 shipped glyphs.
* **Bungie grew it themselves.** The alphabetical block starts at 0xE112, and `automag`
  (0xE144) and `golf_club` (0xE145) sit past its end, out of alphabetical order — appended
  after the fact. The highest codepoint any font declares is 0xE151.

So growing the list means writing the container instead of asking the tool to: append the
glyph payload, add an 8-byte character map entry, and bump the font header's glyph count
and highest codepoint. What is NOT yet established is where each table's entry count lives
and whether lookup needs the entries sorted. Both have to be answered before a glyph can
be ADDED rather than replaced.

Until that is done a port REPLACES a codepoint, and the second port fights the first over
the same slot. Treat the current icon as borrowed, not solved.

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

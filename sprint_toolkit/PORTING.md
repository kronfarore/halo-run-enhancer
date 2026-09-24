# Porting a weapon into another Halo game

The reusable recipe, written from the two ports that are finished: the Halo 4 **SAW**
into **Halo 1** and into **Halo 3**. Tool names still say `saw_` because it was the first
one; they take the weapon as an argument.

Source weapons come from **H4EK** (`F:\SteamLibrary\steamapps\common\H4EK`), which is the
only kit that ships real source tags for every weapon.

---

## Outlined ammo ticks: always the same cause

Recorded here because it has now cost a fix in two games, and the WRONG fix was tried
first in the second one. If spent ticks keep a lit rim that travels with the full/empty
boundary as the magazine drains:

**The threshold channel is a property of the CELL, not of the tick, and it must cover
every pixel.** Halo 1, 2 and 3 all light a meter pixel by comparing a channel of the art
against the ammo level (Halo 1 luminance, Halo 2 and 3 blue), and Bungie's own art carries
that value across the blank gaps too -- `battle_rifle_meter` has ZERO zero-blue pixels.
Paint it only where a tick is opaque and every gap reads 0, which means "still loaded";
the HUD samples filtered, so each tick's rim mixes its own threshold with the 0 beside it
and keeps drawing after the tick has emptied.

Lay the threshold field down FIRST as a continuous staircase over the whole bitmap, then
stamp the tick art over it without touching that channel.

**It is not an alpha problem, so do not hard-edge the art.** That was tried in Halo 2 and
changed nothing, because Bungie's ticks are softly antialiased (alpha 9..137) and always
were. Hard edges only throw the antialiasing away.

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

**Check the dump before you trust it.** The H4 render model can be exported more than once
and the exports are NOT interchangeable: the SAW's full dump is 10736 vertices in four
parts, a sparser one is 7916 in two, and the render method indices mean different things in
each -- part 0 is a twelve-index decal sheet in one and the entire gun in the other. Feed
the wrong one in and the part map drops the body, keeps a seven-index scrap, and builds a
**two-triangle weapon** without a single error from any tool in the chain. The converter now
refuses anything under a thousand triangles. Keep the dump somewhere durable, too: this one
was living in %TEMP%.

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

**Blue is the threshold, and it is a property of the CELL -- in Halo 2 as well.** This is
the same rule the Halo 3 meter needed, and it was re-learnt the hard way here. A Halo 2
meter tick carries red 0, a constant green, and BLUE counting down 254..4 across the ticks
in order; the engine lights a pixel while its blue is above the level. Bungie's field is
continuous -- `battle_rifle_meter` has **zero** zero-blue pixels, reading 11 columns of
254 then 11 of 246, and two bands of 17 rows -- so the blank gap between two ticks carries
the same threshold as the tick beside it.

Paint blue only where a tick is opaque and every gap is 0, which means "still loaded"; the
HUD samples filtered, each tick's rim mixes its own threshold with the 0 next to it, and
every SPENT tick keeps an outline that travels with the full/empty boundary. **It is not an
alpha problem.** Bungie's ticks are softly antialiased (alpha 9..137), so hard-edging the
art fixes nothing -- that was tried first, and the outlines came back unchanged.

### The HUD's own weapon symbol

Not a glyph, and not the `backpack` widget (that is the small stowed icon at the left of
the group). The big symbol beside the ammo is painted into
`ui\hud\bitmaps\new_hud\backgrounds\<weapon>_bkd`, a 206x38 plate per weapon, which is
why a port wearing the donor's plate shows the donor's gun whatever else is fixed.

There is no empty plate, so rebuild one: the silhouette sits in x 105..190, y 5..33, and
the background behind it is a smooth gradient, so interpolate each row between the pixels
either side of the box. (Averaging other weapons' plates together instead leaves the seams
of whatever each one covered.)

**The gradient is the symbol's own, and this is the part to get right** -- it is what makes
a ported symbol look drawn rather than pasted. The symbol carries a green ramp stretched
across ITS OWN bounding box, from about 225 at whatever row the weapon starts on to about 7
at the row it ends on, with blue held near constant at 215. The shotgun proves it belongs to
the symbol and not to the plate: its drawing spans rows 4..24 and ramps 218..14 over exactly
that, while the plate underneath is running 189..22.

Do NOT sample the donor row by row. The plate's own green is 222 at the top, so every
background pixel there passes for symbol and the port's top few rows come out plate
coloured -- a symbol that fades out exactly where it should be brightest. Take the two ENDS
of the donor's ramp and stretch them over the port's own extent instead.

In game it reads as a slow gradient that changes suddenly right at the top. That is not a
second effect: green only overtakes blue in the last few rows, so the shape is blue almost
all the way up and then turns cyan and white.

Then draw the port's weapon the way Bungie draws theirs, which is worth looking at before
writing any code:

* the symbol is **flat**, a hard bright cyan silhouette -- not a shaded picture of the gun.
  Shading the port's by its own geometry gives a dim mottled shape that sinks into the
  plate;
* the colour is a **vertical gradient** down the box, green at the top through cyan to blue
  at the bottom, so take one colour per ROW out of the donor;
* **alpha tells you nothing** about what is symbol and what is plate -- it is 190 or above
  across the whole image. Green plus blue separates them, the plate being flat dark green;
* every shipped symbol **fills the box top to bottom**, so fit the width and then stretch
  vertically to fill. A long weapon drawn to one scale sits in a band across the middle and
  comes out flat green, because that is where the gradient is;
* close the one-pixel holes. A 13836-triangle gun at 29 rows breaks into slivers, and a
  sliver reads as a scratch, not a gun.

Only image 0 is written. Stacking all four of the donor's images into one colour plate
makes tool import a single 206x152 bitmap, and the widget asks for sequence 0 at every
screen size anyway.

### The crosshair, which ports across

The port wears the donor's reticle, and a donor picked for its skeleton has no reason to
have a suitable one -- the Halo 2 SAW came out with the cut GPMG's broken circle and tick
marks, which reads as a scope sight.

**Halo 4's reticle is fully specified in H4EK's tags, so it can be ported rather than
approximated.** Each weapon has `ui\hud\weapons\<race>\<weapon>\<weapon>.cui_screen`,
whose widgets name their bitmap and carry `prop_left/top/width/height`, `prop_bitmap_flipx/y`
and `prop_opacity` -- an exact layout in HUD units. The SAW's is four mirrored copies of
`img_saw_quarter` (an L bracket, 32x32 at +-4 / +-36) plus four 8x8 ticks at 55% opacity.
Decode the bitmaps with `h4_bitmap.py`, mirror and place them at Halo 4's own offsets, and
scale the whole thing so it fills the footprint the donor's reticle filled.

Keep the TARGET game's colour convention: Halo 2 reticles are flat blue with the shape in
the alpha and the widget's shader tints them (green for a friendly, grey for an
invincible target), so the H4 art supplies coverage only.

Give the port its **own one-image bitmap** rather than a sequence in the shared sheet, so
no other weapon's reticle can move. That changes the widget's sequence index to 0 -- three
widgets (`crosshair`, `crosshair_friendly`, `crosshair_invincible`) x fullscreen,
halfscreen and quarterscreen, nine `char integer` fields.

Size it against the donor's SHAPE, not its box. The donor reticle is usually a circle
inscribed in its image; a bracket frame drawn to the same footprint reaches into the
corners, which the circle never does, and reads far bigger on screen. The Halo 2 SAW needed
0.6 of the donor's footprint. Shrink the ART inside the image rather than the image, and no
widget geometry changes.

**The scope widgets DO draw, whatever the flags say.** A HUD cloned from a zooming weapon
carries `scope_mask`, the four bracket crosshairs, `2x` and `distance_meter`, and every one
is gated on `[Y] unit flags` = *unit is zoomed* while the port's `magnification levels` is
0 -- so by the tag's own logic none of them can appear. In game they still did. Do not argue
with it: give them a blank bitmap (one transparent image) and set all three sequence indices
on each to 0. The widgets stay in the tag, drawing nothing, which needs no structural edit
to a loose tag and re-exports as proof.

### Step 5, collision

`tool collision` on the render mesh asserts in `reduce_collision_geometry.cpp`
(`next_edge_index != edge_index`): a Halo 2 hull has to be closed, convex-ish and simple,
and a weapon's render mesh is none of those. **Do not try to build one from the port's
geometry.**

What works is `tool extract-collision-data <donor>`, which unzips Bungie's own authored
hull out of the donor tag exactly as `extract-render-data` unzips the render source, and
then scaling it. Every property that makes it compile is kept and only the size changes.
Scale it **per axis**, each axis's ratio of the two render meshes clamped to [1.0, 1.25],
and about the hull's own centre so it does not drift off the grip: one factor big enough
for the port's width would otherwise stretch the hull a third of a gun past the muzzle.
The port then owns its collision tag, which matters the moment the donor is restored.

### A borrowed effect brings its own conventions

Worth knowing before borrowing any effect. The port's muzzle flash sat above the muzzle,
and the marker was not at fault -- it measured 0.07 units off the centre of the barrel
opening. Bungie's SMG carries its barrel marker **1.40 units BELOW its own bore**, so the
SMG's firing effect is authored to draw that far above where it is emitted. Hung off a
marker that is actually on the bore, it floats. Measure the donor's marker against the
donor's bore, and adopt the difference.

### Step 9, animation: what Halo 2 will not do

Clone the graphs (**both** -- the weapon names one per player species) and repoint the
weapon, so retiming the port cannot retime the weapon it was cloned from.

**Fix the sounds; they are the audible half.** The graph's `snd!` references are the
donor's, so the port reloads with the donor's noises. Point them at the balance donor's
equivalents one for one.

**The tag-side `reload time` is a TRAP, and this is TESTED.** The magazines block has
`reload time` and `chamber time`, and seven shipped Halo 2 weapons carry a non-zero one (the
rocket launcher 5.0s against a 3.7s animation), which makes it look exactly like the
lengthening control. The user tested it in game: it does nothing for the player -- most
likely an AI reload timer. Do not spend a build on it.

**Retiming used to only SHORTEN, and does not any more.** `halo3_reload` rewrites an
animation's frame count and its event frames and leaves the data alone, so there were no
frames past the end to stretch into. Halo 2's codec 3 is now decoded (`h2_anim.py`) and the
data can be rebuilt at any length (`h2_anim_retime.py`), which is what the SAW's 72-frame
reload needed to become its own 128.

    python h2_anim_retime.py <graph> reloads 128 --write

THE FORMAT, for codec 3 -- verified to the byte on 355 animations across every character
graph H2EK ships, so it is a rule and not a sample:

* the blob is NOT pointed at from the element. It sits in the child data immediately after
  the animation's pooled NAME, which has no terminator; the element's +0x34 gives its size;
* a 32-byte header whose two offsets are `32 + 8b` and `+ 12c`, delimiting two tables of
  STATIC poses -- b packed i16 quaternions, c float triples. **This is why size does not
  track frame count**: it tracks how many nodes MOVE, and b swings from 1 to 33;
* then a 52-byte sub-header: a codec byte at +0x04 and, at +0x05/+0x06, R and T -- the
  nodes with an animated rotation and an animated translation -- then `A = 32 + R*f*8`,
  `B = A + T*f*12` and the three strides f*8, f*12, f*4;
* then the animation TWICE. `[0,A)` is R x f packed quaternions, `[A,B)` is T x f float3
  translations followed by a 32-byte TRAILER, and the tail is a 32-byte HEADER plus R x f
  FLOAT quaternions and T x f translations. Both halves are node-major: all of one node's
  frames, then the next.

**The 32 bytes are at the END of the compressed half and the START of the uncompressed one**,
and getting that backwards costs a build: it shifts every quaternion by four frames and
`build-cache-file` asserts in `uncompressed_static_data_codec.h` on
`node < header->total_rotated_nodes`. Two measurements settle which way round it is -- the
packed quaternions read as unit-length more often from offset 0 than from 32, and, because
the two halves hold the SAME rotations, comparing them node by node gives a mean error three
times lower at 0. The uncompressed half's 32 bytes are a real header: (codec 2, R, T, 0),
its own A and B, its own three strides, all of which must be rewritten.

**Not every length works, and the rule is not known.** The SAW's reload rebuilds at 128 and
144 and builds clean; 73 does not, and neither did any length tried on `ready`, `moving` or
`overlays`. A "multiple of 16" rule fitted the first seven results and was then falsified by
testing it. So the retimer does not pretend to a rule -- it offers `--check`, which copies the
graph to a scratch tag and runs `tool model-animation-reset-compression`. That exercises the
same codecs in seconds and asserts the same way, so a bad rebuild costs a few seconds rather
than a three-minute build. **Always --check before building.**



The second copy is the uncompressed source the kit keeps so it can recompress without a
re-import, which is exactly what `model-animation-reset-compression` does. **Rewrite both**,
or the next recompression undoes the work.

**The tail's 32 bytes are a HEADER, not a preamble** -- (codec 2, R, T, 0) then its own A
and B and its own strides. Leaving it describing the old length is not a silent error:
`build-cache-file` asserts in `uncompressed_static_data_codec.h` on
`node < header->total_rotated_nodes`. The compressed half's 32 bytes, by contrast, are data.

Resample with the ENDS PINNED -- new frame t reads old position `t*(f-1)/(new-1)` -- so the
first and last poses are the animator's exactly and only the middle is interpolated. Align
the sign of each quaternion pair before interpolating: q and -q are the same rotation, and
without that the interpolation takes the long way round and a limb swings through the body
between two otherwise fine frames.

STILL OPEN: **codecs 4, 6 and 8** (put_away, sprint, throw_grenade, pitch_and_turn) are
undecoded -- no reload uses them. And **event frames are not scaled yet**: the sound and
effect keys live in child blocks and matching each chunk to its animation in a loose tag
has not been done. It does not bite on a reload whose only key is at frame 1, which is
frame 1 at any length, but check before reusing.

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

**The tables are bounded** — `h3_font_package.py --bounds` proves it and exits non-zero if
it ever stops adding up. The file is five regions of 0xC000: region 0 is the package and
font headers, and each of the other four opens with two u32s that bound everything in it.

    +0x00   (entry count << 16) | table offset in the block, always 8
    +0x04   (glyph data size << 16) | glyph data offset in the block

So the character map is exactly `count` entries at `block + 8`, and the payloads follow at
`block + data offset`. A glyph's own offset is relative to the BLOCK, not to the data —
the first one equals the data offset exactly, which is what gives it away — and the last
ends at data offset + data size.

Within a table the entries form per-font RUNS, each ascending by codepoint, and one font's
runs may span blocks: fixedsys-hud's 144 glyphs are 34 + 69 + 41 across blocks 2, 3 and 4.
Summed per font they come to exactly the counts the font headers declare — 24, 98, 144, 24,
290 in all. Nothing is scattered and nothing needs a heuristic.

### Adding a glyph

Everything needed is now known:

1. append the payload in a block that has room — used extent is data offset + data size,
   and against the 0xC000 block that leaves **288, 32, 1088 and 5688 bytes** free in blocks
   1 to 4, so block 4 will take several icons as it stands;
2. insert an 8-byte entry into that block's table, inside the right font's run and in
   ascending codepoint order;
3. that insertion pushes the glyph data along by 8, so **every offset in that block moves
   by 8**, and the block's own two u32s move with it;
4. bump the font header's glyph count at +0x13C, and its highest codepoint at +0x138 if the
   new one is higher.

`h3_font_add.py` does it, and `h3_weapon_glyph.py` calls it whenever the codepoint it is
asked for does not exist yet. The SAW now owns **0xE06A** in all three resolutions, and
0xE128, which it used to borrow, is byte-identical to Bungie's again.

**The rule, which cost two goes to get right: a new entry goes in its SORTED position.**
A font's entries are not one run — `fixedsys-hud`'s live in a dozen blocks — but they must
read as ONE ascending list across the package. Inserting after whichever run had room keeps
that run ascending and breaks the font: 0xE151 after the run ending 0xE069 made the font
read `... 0xE069, 0xE151, 0xE070 ...`, and a lookup that assumes a sorted list stops
finding things. The x1 package was fine because there it landed above the font's highest,
so one package of three was right and two were not — and the pickup and ally-trade prompts
drew no icon at all while the player's inventory icon, which is not a font glyph, kept
working. That is the shape of the bug to expect here.

So: insert sorted, and when the block a codepoint sorts into has no room, change the
CODEPOINT rather than the place. `h3_font_add.add()` refuses to return a package whose font
no longer ascends. 0xE06A was chosen because it is free in all three packages AND sorts
into a block with room in all three — confirmed in game.

### Halo 2 is easier, and needs no codec at all

H2EK ships **`tool replace-font-char <font> <tiff> <utf16>`**, so Bungie's own encoder
draws the pixels and the payload format never has to be understood — which matters,
because the SHIPPED payloads do not decode with the Halo 3 codec even though that tool
writes with it. The 2004 data is in some older form; what the tool writes today is what
the engine reads today.

What it will NOT do is add a codepoint. An unmapped one resolves to the font's notdef
glyph and `replace-font-char` replaces THAT — one command and every unmapped character in
the game becomes a SAW. So `h2_font_add.py` creates the entry first: append a 16-byte
record to the glyph table, push every payload along by 16 and bump every absolute offset
with it, point the codepoint's slot in the character map at the new index, and raise the
glyph count. The character map being indexed by codepoint is what makes this easier than
Halo 3 — no table to insert into, no order to keep.

Two traps, one run each:

* **the codepoint argument is DECIMAL.** `0xE13D` is read as 0, and the tool silently
  rewrites the notdef glyph while reporting "replaced char 0" and the notdef's size — the
  only sign anything went wrong;
* the font has to be edited where tool.exe can reach it, so copy it into H2EK, edit, copy
  back.

`h2_saw_glyph.py` drives the pair over all eight English fonts and refuses any font where
a shipped glyph moved. The SAW owns **0xE13D**, free in all of them, with 195 more above
it for the ports after this one.

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

## Open, and deliberately so

* **The crosshair is not ported in Halo 1 or Halo 3 yet.** Only Halo 2's is. The method is
  in "The crosshair, which ports across" above and is game-agnostic -- H4EK specifies the
  layout, so the same read applies -- but both earlier ports still wear their donor's
  reticle. Do these once the Halo 2 port is finished.
* **Codecs 4, 6 and 8 of the Halo 2 animation format** are undecoded, so `ready`,
  `put_away`, `sprint` and `throw_grenade` cannot be retimed in most graphs. Codec 3, which
  every reload uses, is done.

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

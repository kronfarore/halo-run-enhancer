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

The donor is `objects\weapons\rifle\gpmg`, a **cut** Bungie LMG that is in no scenario's
palette but still owns its own first-person model, HUD and the full set of pickup message
string ids. Nothing live has to be hijacked -- the ceiling the Halo 3 port ran into does not
exist here. See `halo2-weapon-port-donor`.

Halo 2 is the easiest of the three to READ (the kit hands back Bungie's own source for
geometry and collision) and the hardest to WRITE: there is no XML importer, so every tag
edit is a byte edit, and the animation format had to be decoded before the reload could be
retimed.

### The pipeline, end to end

Each of these is one script, and each proves its own work before it keeps it.

    saw_to_jms_h2.py <storm_lmg_rm.xml>            1. geometry onto the donor's skeleton
    tool render objects\weapons\rifle\saw          and \saw\fp_saw
    h2_saw_textures.py                             2. skin, bump maps, shaders
    h2_saw_weapon.py                               3. its own weapon, projectile, effects
    h2_saw_numbers.py                              4. the balance numbers
    h2_saw_collision.py --write                    5. its own collision hull
    h2_saw_meter.py                                7. a 72-round ammo meter
    h2_saw_hud_plate.py --write                       the HUD's weapon symbol
    h2_saw_reticle.py --write                         the crosshair, ported from H4
    h2_saw_scope.py --write                           blank the scope widgets
    h2_saw_glyph.py --write                        8. a pickup icon of its own
    h2_saw_messages.py                                the pickup prompts
    h2_saw_animations.py --force                   9. its own animation graphs
    h2_anim_retime.py <graph> reloads 128 --write     and its own reload length
    h2_saw_place.py --level <name> --build --deploy   put it in the player's hands

Two tools underneath all of it:

    h2_tagref.py   <tag> --set <class> <old> <new>   repoint a reference
    h2_tagfield.py <tag> --set "<field>" <value>     change a number

### Step 1, geometry

`tool extract-render-data <render_model>` unzips Bungie's ORIGINAL .jms out of the tag, so
the skeleton, rest pose, markers and material strings are the authored file rather than
something reconstructed from a tag dump. (H4's `extract-import-info` finds nothing, which is
why the other two ports work harder here.)

* **JMS 8210 is not JMS 8200.** Reclaimer writes Halo 1's and only that, so `write_jms`
  cannot be aimed at Halo 2: nodes carry a parent index instead of child/sibling links,
  triangles name only a material, and there is **no REGIONS section at all** -- region and
  permutation are parsed out of the material's second line, `(1) base gun`. `h2_jms.py`
  implements it and proves it by writing all four extracted files back byte for byte.
* **Node translations are absolute**, not parent-relative as in Halo 1.
* **JMS v is 1 - the tag's v**, measured against the donor rather than assumed.
* Anchor the mesh on the donor's `right_hand` marker: the H4 weapons are authored with the
  root bone ON the grip, so the two grips coincide and the hand the animation drives is
  right by construction. Scale is settled by the grip-to-foregrip span; for the SAW into the
  GPMG that came out at 1.0, with the left hand landing within half a unit unaided.
* **Halo 2 fires from the barrel marker the weapon tag names**, and for the GPMG that is
  `primary_trigger`, not a `muzzle_flash` -- there is no muzzle marker in the file at all.
  It sits 32 units out, past the end of a shorter gun, so it has to be moved.

**Check the dump before you trust it.** The H4 render model can be exported more than once
and the exports are NOT interchangeable: the SAW's full dump is 10736 vertices in four parts,
a sparser one is 7916 in two, and the render method indices mean different things in each --
part 0 is a twelve-index decal sheet in one and the entire gun in the other. Feed the wrong
one in and the part map drops the body, keeps a seven-index scrap, and builds a
**two-triangle weapon** without a single error from any tool in the chain. The converter now
refuses anything under a thousand triangles. Keep the dump somewhere durable: this one was
living in `%TEMP%`.

`tool render` reports far fewer triangles than it was given (13836 -> 8361 for the SAW). That
is welding, not loss: the surface area is 98.4% of what went in. Check the area, not the
count.

### Step 2, textures and shaders

`h2_saw_textures.py` decodes the Halo 4 maps, imports them and repoints the shaders.

* **A Halo 2 bump map is a HEIGHT map**, not a normal map (`usage = height map`, bump height
  4.0). Halo 4's is tangent-space normals, so it has to be integrated back into heights --
  Poisson/FFT, then a high pass, then a gain fitted against Bungie's own slope statistics.
* The p8-bump format is gone in MCC; x8r8g8b8 is what imports.
* **h4_bitmap's pixel offset depends on the format**: the marker is chain+8 for dxt1,
  chain+0 for a single-mip dxt5, and **chain+16 for dxn**. Score the result for roughness
  rather than trusting the first offset that decodes.

### Step 3, what the port must OWN

A port that shares a tag with a live weapon changes that weapon when it is tuned. Clone and
repoint: the projectile, both damage effects, the firing effect, and the animation graphs.

**Borrowed effects bring their own conventions, and their own owners.** Two caught here:

* the GPMG fires the WARTHOG CHAINGUN's muzzle flash, smoke and casings, with the turret's
  muzzle light, at 20 rounds a second. The port takes the SMG's firing effect instead;
* the projectile kept `effects\materials\objects\weapons\warthog_chaingun`, the turret's
  IMPACT set, which reads in game as an uncharacteristic fireball on every wall hit. That is
  a separate reference from the firing effect and has to be repointed separately.

**A borrowed effect is authored around its donor's marker.** The port's muzzle flash sat
above the muzzle and the marker was not at fault -- it measured 0.07 units off the centre of
the barrel opening. Bungie's SMG carries its barrel marker **1.40 units BELOW its own bore**,
so the effect is drawn that far above where it is emitted. Measure the donor's marker against
the donor's bore and adopt the difference (the GPMG's own is 3.72, so the number is per
weapon, not per game).

### Step 4, the numbers

`h2_tagfield.py`. The Assembly plugins cannot be used: they give offsets in the CACHE layout
and a loose tag is laid out differently (the weapon's root struct is 0x31C in a cache and
0x5F4 on disk, and no arithmetic gets from one to the other). So the offset is FOUND and the
finding is PROVED -- read what tool.exe reports, list every place in the tag whose bytes
decode to that, probe each **into a copy**, and keep the one where that field changed and
nothing else did. Results cache in `h2_tagfield_offsets.json`.

* **Angles are RADIANS in the file and DEGREES in the export.** Searching for the 1.0 that
  tool prints for a minimum error finds nothing; 0.0174533 finds it on the nose.
* **A field reading zero cannot be found this way** -- padding reads zero too. Locate it in a
  tag of the same group that has a non-zero one, and apply the same offset WITHIN the block
  element. (The element layout is shared; the absolute offset is not.)
* Probe into a copy, never the tag. An interrupted probe once left `saw.weapon` unloadable.

### Step 5, collision

`tool collision` on the render mesh asserts in `reduce_collision_geometry.cpp`
(`next_edge_index != edge_index`): a Halo 2 hull has to be closed, convex-ish and simple, and
a weapon's render mesh is none of those. **Do not try to build one from the port's geometry.**

What works is `tool extract-collision-data <donor>`, which unzips Bungie's own authored hull
out of the donor tag exactly as `extract-render-data` unzips the render source, and then
scaling it. Every property that makes it compile is kept and only the size changes. Scale it
**per axis**, each axis's ratio of the two render meshes clamped to [1.0, 1.25], about the
hull's own centre so it does not drift off the grip: one factor big enough for the port's
width would otherwise stretch the hull a third of a gun past the muzzle. The SAW came out
[1.0, 1.25, 1.11] -- wider and taller than the GPMG, but shorter.

### Steps 6 and 7, ammo and the HUD

**Step 6 is n/a in Halo 2**, as in Halo 3: there are no ammo items, you top up from dropped
weapons. A weapon's nested `magazines` block is the physical magazine thrown out during a
reload, not a pickup.

**The ammo meter.** Halo 2 draws the readout as ONE bitmap of tick art, revealed as the
magazine empties, so the tick count is purely a property of the art. Bungie's, measured:

    battle_rifle_meter  197x34   2 rows of 18 = 36   tick 6px wide, row pitch 17
    smg_meter           198x42   3 rows of 20 = 60   tick 6px wide, row pitch 14

The tick is 6 pixels wide in both; the magazine changes the rows and their spacing. Keep the
donor's canvas so the widget does not move. **And blue is the threshold, and a property of
the CELL** -- see the rule at the top of this file, which cost a fix in two games.

**The HUD's own weapon symbol** is not a glyph, and not the `backpack` widget (that is the
small stowed icon at the left of the group). The big symbol beside the ammo is painted into
`ui\hud\bitmaps\new_hud\backgrounds\<weapon>_bkd`, a 206x38 plate per weapon, which is why a
port wearing the donor's plate shows the donor's gun whatever else is fixed.

There is no empty plate, so rebuild one: the silhouette sits in x 105..190, y 5..33, and the
background behind it is a smooth gradient, so interpolate each row between the pixels either
side of the box. (Averaging other weapons' plates together instead leaves the seams of
whatever each one covered.) Then draw the port's weapon the way Bungie draws theirs:

* the symbol is **flat**, a hard bright cyan silhouette, not a shaded picture of the gun.
  Shading it by its own geometry gives a dim mottled shape that sinks into the plate;
* **the gradient belongs to the SYMBOL, not the plate**, and this is the part that makes it
  look drawn rather than pasted. It runs from about 225 at whatever row the weapon starts on
  to about 7 at the row it ends on, with blue near constant at 215. The shotgun proves it:
  its drawing spans rows 4..24 and ramps 218..14 over exactly that, while the plate underneath
  runs 189..22. Take the two ENDS of the donor's ramp and stretch them over the port's own
  extent. Do NOT sample the donor row by row -- the plate's own green is 222 at the top, so
  every background pixel there passes for symbol and the port's top comes out plate coloured,
  a symbol that fades exactly where it should be brightest;
* **alpha tells you nothing** about what is symbol and what is plate -- it is 190 or above
  across the whole image. Green plus blue separates them, the plate being flat dark green;
* every shipped symbol **fills the box top to bottom**, so fit the width and then stretch
  vertically to fill;
* close the one-pixel holes: a 13836-triangle gun at 29 rows breaks into slivers, and a sliver
  reads as a scratch, not a gun.

Write only image 0. Stacking all four of the donor's images into one colour plate makes tool
import a single 206x152 bitmap, and the widget asks for sequence 0 at every screen size anyway.

**The crosshair ports across from Halo 4.** The port otherwise wears the donor's, and a donor
picked for its skeleton has no reason to have a suitable one -- the SAW came out with the cut
GPMG's broken circle and tick marks, which reads as a scope sight. H4EK specifies the real one
exactly: `ui\hud\weapons\<race>\<weapon>\<weapon>.cui_screen` names each widget's bitmap and
carries `prop_left/top/width/height`, `prop_bitmap_flipx/y` and `prop_opacity`. The SAW's is
four mirrored copies of `img_saw_quarter` (an L bracket, 32x32 at +-4 / +-36) plus four 8x8
ticks at 55% opacity. Decode with `h4_bitmap.py`, mirror and place at Halo 4's own offsets.

Keep the TARGET game's colour convention: Halo 2 reticles are flat blue with the shape in the
alpha and the widget's shader tints them (green for a friendly, grey for an invincible
target), so the H4 art supplies coverage only. Give the port its **own one-image bitmap**
rather than a sequence in the shared sheet, so no other weapon's reticle can move -- which
changes the widget's sequence index to 0 on three widgets x three screen sizes.

Size it against the donor's SHAPE, not its box: the donor is a circle inscribed in its image,
and a bracket frame drawn to the same footprint reaches into corners the circle never touches.
0.6 of the footprint was right for the SAW.

**The scope widgets DO draw, whatever the flags say.** A HUD cloned from a zooming weapon
carries `scope_mask`, four bracket crosshairs, `2x` and `distance_meter`, all gated on
`[Y] unit flags` = *unit is zoomed* while the port's `magnification levels` is 0 -- so by the
tag's own logic none can appear, and in game they did. Do not argue with it: give them a blank
bitmap (one transparent image) and set all three sequence indices on each to 0.

### Step 8, the icons and the text

See "The icon supply" below for the general rule. In Halo 2 specifically:

* `tool replace-font-char <font> <tiff> <utf16>` writes the glyph, so the codec never has to
  be cracked -- but **the codepoint argument is DECIMAL**. Hex is read as 0 and silently
  rewrites the notdef glyph, which turns every unmapped character in the game into a SAW;
* the tool will not ADD a codepoint, so `h2_font_add.py` creates the entry first;
* eight English fonts draw HUD text and all eight need the glyph;
* **MCC reads `data\UI\Localization\<LANG>_Halo2.bin`, not the map.** The index is (hash,
  offset) pairs, NOT ordinal like Halo 3, so patch by CONTENT: find the line, pad with SPACES
  never NUL, and keep the length, entry count and offsets invariant;
* the prompt sets are INTERLEAVED, not one set per weapon. Getting "picked up" right does not
  mean "take from ally" is right; check each.

### Step 9, ANIMATION

The long one. A port inherits the donor's animation graph, which means it inherits the
donor's reload -- the SAW reloaded at the sniper rifle's 2.4 seconds instead of its own 4.3 --
and, until Halo 2's animation format was decoded, that could not be changed. It can now.

#### Own the graphs, and fix the sounds

Clone **both** graphs (a weapon names one per player species) and repoint the weapon, so
retiming the port cannot retime the weapon it was cloned from. Then fix the `snd!` references:
they are the donor's, so the port reloads with the donor's noises. Point them at the balance
donor's equivalents one for one -- the SAW took the SMG's reload, ready, melee and posing.

#### The format, codec 3

Verified to the byte on **355 animations across every character graph H2EK ships**, so it is
a rule rather than a sample.

Finding the data: the blob is NOT pointed at from the element. It sits in the child data
immediately after the animation's pooled NAME, which has no terminator, so find the name and
step past it; the element's `+0x34` gives its length.

    element   +0x13 node count   +0x14 frame count   +0x34 frame data size
              +0x50 tail size    +0x54 B

    blob      32-byte header: (1, b, c, 1), then X = 32 + 8b and Y = X + 12c
              table A   b packed i16 quaternions   STATIC rotations
              table B   c float3                   STATIC translations
              52-byte sub-header:
                  +0x04 codec, +0x05 R, +0x06 T   R/T = nodes with an ANIMATED rotation
                  +0x10 A = 32 + R*f*8            or translation
                  +0x14 B = A + T*f*12
                  +0x18 f*8, +0x1C f*12, +0x20 f*4
              [0,A)   R x f packed i16 quaternions
              [A,B)   T x f float3 translations, then a 32-byte TRAILER
              [B,end) a 32-byte HEADER (codec 2, R, T, its own A, B, strides), then
                      R x f FLOAT quaternions and T x f float3 translations

Both halves are node-major: all of one node's frames, then the next node's.

**Size does not track frame count, it tracks how many nodes MOVE** -- b swings from 1 to 33
between animations. Believing otherwise is what made this look keyframe-compressed for a
while; it is not, it is full frame.

**The 32 bytes are at the END of the compressed half and the START of the uncompressed one.**
Getting that backwards shifts every quaternion by four frames and `build-cache-file` asserts
in `uncompressed_static_data_codec.h` on `node < header->total_rotated_nodes`. Two
measurements settle it: the packed quaternions read as unit-length more often from offset 0
than from 32, and -- decisively, since both halves hold the same rotations -- comparing them
node by node gives a mean error three times lower at 0.

Codecs 4, 6 and 8 (`put_away`, `sprint`, `throw_grenade`, `pitch_and_turn`) are undecoded. No
reload uses them.

#### What recompression does, and why it is needed

`tool model-animation-reset-compression` rebuilds the compressed half from the uncompressed
one -- but only for the animations it judges worth recompressing. Three in-game results pin
it down, after two wrong readings on the way:

    resampled data, not recompressed   the reload jerked at its start and its end
    the same, recompressed             smooth and correct
    ZEROS, recompressed                FROZEN: the hands held one pose throughout

Zeros surviving says tool did not replace them; the same data going jerky-to-smooth says it
did. So the compressed half is a PLACEHOLDER that this side need not understand, but it must
not be degenerate or it will be kept. Write a quantisation of the resampled uncompressed data
and let Bungie's compressor do the compressing.

**It TRUNCATES THE TAG IT IS GIVEN TO 64 BYTES WHEN IT ASSERTS**, and leaves a `tool.exe`
running that holds the file open -- later writes fail with "Device or resource busy", further
runs return nothing, and on the user's desktop a crash dialog waits to be dismissed. It
destroyed two graphs before that was understood. **Never point it at a real tag**: write to a
scratch tag, run there, copy back only a whole result, and kill the hung process on failure.
Keep failing attempts few; each one costs the person at the keyboard a dialog.

#### Retiming

`h2_anim_retime.py <graph> reloads <frames> --write`. Rewrite the uncompressed half, fill the
compressed half, hand it to tool.exe, and write only what comes back whole. Resample with the
ENDS PINNED -- new frame t reads old position `t*(f-1)/(new-1)` -- so the first and last poses
are the animator's exactly. Align the sign of each quaternion pair before blending.

**Nodes that do not move are sampled, not blended.** Interpolating a node made of nothing but
float noise is wrong on its own terms: `_qlerp` normalises, which erases the noise. The
threshold is measured, not picked -- across the two reload graphs the nodes fall into two
populations with nothing between them (Dervish: seven at ~1e-7 and one at 1.2e-4; Chief:
nothing below 1.1e-2), so 1e-3 sits in the gap with two orders of magnitude of margin.

**Not every graph accepts interpolated TRANSLATIONS.** The Chief's retimes with everything
interpolated; the Dervish's asserts, and it is the translations it objects to -- hold the
rotations and interpolate the translations and it asserts, do the reverse and it recompresses.
It is not the translation data, which is numerically identical in the two graphs. What differs
is how the whole animation scores once they are interpolated. So **ask rather than guess**:
build the best version, offer it, fall back to held translations only if refused, and report
which was used.

Ruled out on the way, one run each, so none of it is repeated:

    the graph itself        untouched recompresses, and so does an identity retime
    the length              96, 128 and 144 assert, and 36 does too -- not per-frame deltas
    the trailer             clearing it instead of copying it asserts
    the placeholder         tiling the original compressed bytes asserts; only ZEROS pass,
                            and they pass by being SKIPPED, which is the frozen weapon
    one of a pair           retiming both byte-identical reloads asserts
    still nodes             holding all eight of the Dervish's non-moving rotations asserts
    per-axis                holding a node's still axes and blending its moving one is
                            refused on BOTH graphs, including the one that takes plain
                            blending -- a mixture is worse than either
    per-node                blending only the nodes that visibly move is refused as well

**Held translations step, and every species' graph must still be the same length.** Sampling
means the position advances in steps, and a fractional ratio steps raggedly: 72 to 128
alternates one- and two-frame holds, which in game reads as the weapon jittering rather than
settling at the end of the reload. A whole multiple (72 to 144) evens it out -- and costs that
species a different reload duration, which is worse than the jitter. Nor can the reload card
even them up afterwards: `halo3_reload.scale_reload` rewrites the FRAME COUNT and never the
data, so shortening 144 to 128 plays 128 of 144 frames and truncates the tail, which is where
the weapon settles.

**Event frames are not scaled yet.** The sound and effect keys live in child blocks and
matching each chunk to its animation in a loose tag has not been done. It does not bite on a
reload whose only key is at frame 1, which is frame 1 at any length.

#### How long the reload should be

Measured from each kit's own first-person graphs (frames at 30fps):

    H4 SAW 128   H4 AR 68   H3 AR 58   H3 SMG 50   H2 SMG 50

    H4 -> H3 via the assault rifle   58/68 = 0.853
    H3 -> H2 via the SMG             50/50 = 1.000
    balanced Halo 2 reload           109 frames, 3.64s

Build the tag at the SAW's **own 128** (4.27s), because the card can only shorten, and let the
Reload Time card take it to 109 -- the same multiplier the Halo 3 port arrived at
independently, which is a good check on the chain.

#### A weapon has one first-person MODEL per species

Not just one set of animations: the `first person` block holds an element for each, and each
names its own model. A port starts with both pointing at the same one, so two rigs that hold
the weapon differently -- 42-node Spartan, 36-node Elite -- get the same position in the view.
Build a second model at its own offset (`saw_to_jms_h2.py --fp-sub=NAME --fp-nudge=x,y,z`),
clone the `.model` tag, point it at the new render model, and retarget that ONE entry, which
needs an `nth=` aware reference edit because the two paths are identical until one changes.

The two graphs are NOT interchangeable, so a species whose graph will not retime keeps the
donor's length; it cannot borrow the other's.

### Editing tags

There is no XML importer, so tag edits are byte edits. A tag reference is 16 bytes with the
class 4CC REVERSED, and the path is pooled elsewhere -- and since the file is laid out in
strict FIELD order, a struct's paths are interleaved with its child blocks, so which record
owns which string cannot be recovered from the bytes alone. `h2_tagref.py` therefore edits
**by class and current path**, refuses anything ambiguous, and re-exports with tool.exe
afterwards to prove the list changed in exactly one place, restoring the file if it did not.

**Write the length field BEFORE the string.** A record is not necessarily before the string it
names -- in a HUD the last scope widget's record sits two kilobytes past the first pooled path
-- so replacing a path with a shorter one moves that record out from under its own offset. Do
the lengths first, which cannot move anything, then the strings from the end backwards.

`tool verify-tag-load` proves nothing: it is silent for a good tag AND for one that does not
exist.

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
  game-agnostic -- H4EK specifies the layout, so the same read applies -- but both earlier
  ports still wear their donor's reticle.
* **Codecs 4, 6 and 8 of the Halo 2 animation format** are undecoded, so `ready`,
  `put_away`, `sprint` and `throw_grenade` cannot be retimed. Codec 3, which every reload
  uses, is done.
* **Halo 2 animation EVENT frames are not scaled** when an animation is retimed. It does
  not bite on a reload whose only key is at frame 1, but a weapon with a mid-reload key
  needs this first.
* **Whether shortening truncates.** `scale_reload` rewrites the frame count and not the
  data, so a shortened animation should play the first N frames and cut the tail -- where a
  reload settles. Read from the code, never seen in game, and it applies to the Halo 3 port
  as much as to Halo 2. One look with a Reload Time card applied would settle it.
* **Halo 2 collision is the donor's hull, scaled.** Good enough for a similar weapon; a port
  whose shape differs a lot from its donor's would want a real hull, and `tool collision`
  will not build one from a render mesh.

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

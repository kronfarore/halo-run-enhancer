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

**Step 3 is TWO things, and the Halo 1 SAW shipped with only one of them** (found
2026-10-02). `saw_port_values.py` wrote the port's own numbers into
`weapons\saw\bullet` (proj + jpt!), but the weapon tag's trigger was a copy of the
Assault Rifle's and still named `weapons\assault rifle\bullet`. So the built SAW fired
the DONOR's bullet, the port's own bullet tags were orphans the cache never compiled,
every SAW projectile/damage balance row pointed at a tag that was not in the map, and
editing the AR's bullet moved the SAW with it. Cloning the tags is not enough: the
trigger has to name them (`saw_weapon.py` does it now). Melee is left on the donor's
tag on purpose -- only Halo 1 has per-weapon melee damage, so sharing it is harmless.
After fixing the wiring the maps that carry the port must be REBUILT; until then the
deployed map still has the old reference.

Step 6 is a **port detail, not a general option**: a port inherits the donor's pickup
item, and the dropdown only re-points it when several weapons share one. Halo 4 has no
ammo pickups at all.

---

## Halo 1

Everything runs through `saw_build.py`, which does the whole thing and always restores
the scenario even when the build fails:

    python saw_build.py [--map a10] --scale 1.0 [--skip-bitmaps] [--no-deploy]

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
6. `saw_port_values.py --write` — **step 4**: the port's own Halo 4 numbers into its
   Halo 1 tags, so the map ships the SAW and the patcher applies the balance on top.
   Both halves read the same `balance_SAW_Halo4_to_Halo1.json`, one taking `original`
   and the other `balanced`, so they cannot drift. **Assembly's units are not
   Reclaimer's**: angles are degrees in the table and RADIANS in the tag, velocities
   are units per tick in the table and per SECOND in the tag. The tool proves every
   path and factor against the Assault Rifle before it writes, and refuses if one
   stops reproducing the donor — which is how the velocity factor was caught
   inverted during its reconstruction.
7. `saw_scenario.py --map <map>` — puts the weapon in that map's spawn profiles.
   **Only the spawns.** a10 has six profiles and three of them drive mechanisms (the
   sprint mod's invisible weapon, the bridge pistols, a weapon insert); handing one
   the SAW breaks the level. That cannot be read off the tag, so it is recorded per
   map and an unknown map is REFUSED with its profiles printed.
8. `tool build-cache-file levels\<map>\<map> classic none 1` — **must be `classic`**;
   read_write/remastered corrupts, and a human weapon forces classic anyway.
9. `saw_scenario.py --restore` — always.
10. deploy; the original stays as `<map>.map.before_saw`.

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

**THE TEXT RULE BELOW IS SUPERSEDED for Halo 3 and ODST** -- both ports now bring
their own lines (see **Step 8, the text**), so nothing is borrowed and nothing has to
be blanked. It still describes Halo 2 and Halo 1, which have not been converted, and
it remains the right rule for any line a port does NOT own.

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

## Halo 3: ODST

ODST is the same engine and measures out almost identically to Halo 3: the Assault
Rifle's first-person and world **skeletons are byte-identical** between the two kits
(node list, default transforms, every marker), its projectile and damage effect tags are
byte-identical files, and its reload is the same 58 frames. So the whole Halo 3 pipeline
runs against it — `h3_kit.py` selects the kit from `PORT_EK`, and every tool asks it:

    set PORT_EK=odst

and the balance comes out the same to the last decimal (velocity 75, magazine 72,
reload ×0.851562). That is not a copy: ODST is measured from its own tags and lands
there because its Assault Rifle is Halo 3's.

### The pipeline, end to end

Every tool takes the kit from `PORT_EK`, so set it once:

    set PORT_EK=odst

    h3_make_saw.py          clone the weapon, projectile, damage effect   (step 3)
    saw_to_jms_h3.py        the JMS, from ODST's OWN skeleton XML x2      (step 1)
    tool render <dir> final both models -- fp and saw_3p
    h3_saw_textures.py      bitmaps + shaders, BOTH model folders         (step 2)
    tool render <dir> final AGAIN: a shader that arrives after a render is not in it
    h3_saw_world_model.py   world model, hlmt, weapon -> hlmt             (step 1)
    h3_saw_wire_model.py    fp model                                      (step 1)
    h3_region_name.py       'default' -> 'standard' on all FOUR models -- LAST, because
                            the two wiring steps re-render
    h3_saw_tag_numbers.py   the port's own H4 numbers into its tags       (step 4)
    h3_saw_chud.py          clone the chud, low-ammo 18                   (step 7)
    h3_sprite_box.py        give a spare sprite a REAL box on blank canvas (steps 7, 8)
    h3_meter_art.py         the 72-tick meter, sprite 1                   (step 7)
    h3_chud_sequence.py     point the chud at meter 1 and schematic 10
    h3_weapon_schematic.py  the schematic, sprite 10                      (step 8)
    h3_weapon_glyph.py      the pickup glyph, 0xE04A                      (step 8)
    h3_port_messages.py     its own messages, all languages, --repoint    (step 8)
    h3_saw_animations.py    retime reload/ready on the odst_recon graph   (step 9)
    make_port_catalog_odst.py --write                                     (step 5)
    <place it in Sapien AND give it a starting profile>
    odst_ek_build.py --build sc150
    h3_chunk_check.py       NINE chunks, all backed -- before any launch
    h3_saw_deploy.py --install [--baseline]

Scale is **1.0**, and the two skeleton XMLs come from ODST's own Assault Rifle
(`fp_assault_rifle.render_model` and `assault_rifle.render_model`) -- byte-identical to
Halo 3's, but export them from the kit you are building in.

### THE STEP THAT GETS IT INTO THE MAP

**Place the weapon in Sapien AND give it a Player Starting Profile. The placement alone
is not enough — confirmed in game.** The first rebuild, with a Sapien placement only,
produced no geometry; adding the profile produced all of it.

This is the single most expensive thing to rediscover, because **a build that gathers no
geometry still produces every tag and reads as success**: the weapon, both render models,
the animation graph, the projectile and the HUD are all present and correct in the map,
and there is simply nothing to draw. `tool` says nothing about it — no error, no warning,
not one mention of the tag in a 134 KB log.

So always, before spending a launch:

    h3_chunk_check.py sc150 --game "Halo 3: ODST" "rifle\saw"

Nine rows, all backed (fp model, world model, animation graph, 2 bitmaps, 4 shaders).
No rows means the scenario edit did not reach the build, whatever the build reported.

Residency then needs nothing: `tool` marks the port `X` in GLOBAL by itself, exactly as
it does for a stock weapon, so there is no `--load-always` fold.

### Editing the scenario by hand does NOT work, and here is why

Three headless routes were tried and all three produced tags with zero geometry — a
profile slot, a real weapon-palette entry, and a real placement pointed at it. Each was a
valid edit that parsed and read back. What Sapien and Guerilla write is evidently more
than a path: the equipment work reached the same conclusion in its own words, that a
hand-made entry lacks "the position, BSP attachment, folder and unique ID" Sapien writes.

**And the scenario tag's weapon palette is not the one that counts.** `tool` states it:

    WARNING (group_postprocessing 'levels\atlas\sc150\sc150.scenario')
    'scenario_weapon_block' referenced by resource
    'levels\atlas\sc150\resources\sc150.scenario_weapons_resource'
    that is about to be stomped over isn't empty!

Fifteen blocks — weapons, vehicles, equipment, scenery, decals, trigger volumes and more
— live in `resources\<level>.scenario_*_resource` and STOMP the copy inside the
`.scenario` at build time. sc150's scenario tag lists 23 weapons; the resource lists the
17 the map really has. This is very likely what `h3-import-weapon-recipe` recorded as a
Guerilla palette entry getting "neither geometry nor residency": the edit was discarded
before it could do anything. `odst_saw_place.py` reads the real palette and placements.

### What ODST does NOT share with Halo 3

* **One animation graph, not two.** Halo 3's Assault Rifle names the Master Chief's and
  the Dervish's; ODST's names `odst_recon` twice, so there is one graph to clone and the
  repoint rewrites both references to it.
* **The HUD sheets have no free slots.** `ballistic_meters` has 18 sequences with one
  free (a two-row box) and `weapon_scematics` has 27 whose three spare ones are 8x8
  stubs. Halo 3 took the automag's schematic, which is free there because the automag
  never appears in Halo 3 — in ODST it is the starting pistol.
  Both sheets stop using canvas around y=400 and no sequence covers the ~100 blank rows
  below, so `h3_sprite_box.py` gives a spare sequence a REAL box down there. Nothing is
  taken from a weapon that is in the game. Two traps: the sprite records are **not
  4-aligned**, and while an edge is a pixel count over the sheet size and can be rebuilt
  exactly, a **registration point can be a half pixel**, so it must be read from the tag.
* **Five fonts, not four.** ODST inserted `fixedsys-pda13`, so its HUD font is index 3
  where Halo 3's is 2 (both have 144 glyphs, which is how to tell). Its packages are also
  ~50 KB larger and packed differently, so Halo 3's codepoint sorts into a full ODST
  block. The port takes **0xE04A**, one of only six that fit.
* **Assembly's ODST `chdt` plugin renames things.** `Low Ammo Loaded Threshold` is
  `Low Clip Cutoff` (same offset), and `Widget Collections` is `HUD Widgets`. Asking for
  the Halo 3 name returns None for both weapons, and `None == None` reads as "the clone
  owns its blocks" — a deduplication check that silently always passes.
* **ODST has ammo pickups** where Halo 3 has none: its Assault Rifle references
  `objects\powerups\assault_rifle_ammo`, so the port inherits one as built.

### Step 6, the ammo pickup: DONE, and it is the second game to have it

ODST HAS ammo pickups where Halo 3 has none, so the port gets the same dropdown Halo 1
has. The layout was MEASURED rather than assumed: a magazine element is 20 bytes --
`Rounds` i16 at +0, then the equipment tag reference at **+4** (its group 4CC reads
`piqe`, eqip backwards), whose datum sits at +0x10. So `ref_offset` is 4 and the patcher
writes at `ref_offset + 0xC` as it does everywhere.

Eight items, read off a built map: assault rifle, battle rifle, needler, pistol, rocket
launcher, shotgun, SMG and sniper rifle ammo. Each records which of the 11 missions
carries it, because pickup items are PER MAP; a mission that lacks one is not an error,
the patcher falls back to the item the port was built with.

**One patcher bug had to be fixed for this to work anywhere but Halo 1.**
`_tag_id_by_name` walked Halo 1's tag index and reached for `m.tag_count`, which no
Halo 3-era map object has -- so it raised AttributeError rather than returning a datum,
and the ammo step was quietly Halo-1-only. Halo 3 and later already carry each tag's
`ident` in the parsed tag table, so it asks that first.

### Step 8 in ODST: DONE, and it owns its lines

The port brings its own five messages rather than taking a weapon's -- see
**Step 8, the text** below, which is the general method for every game. Confirmed in
game: its own glyph on three prompts and "Picked up a SAW" on the confirmation, in all
twelve languages.

Its GLYPH is its own too, at **0xE04A**. ODST needs a different codepoint AND a
different font index from Halo 3: its packages hold FIVE fonts (it inserted
`fixedsys-pda13`), so the HUD font is index 3 rather than 2, and they are ~50 KB larger
and packed differently, so Halo 3's 0xE06A sorts into a full block. Six codepoints fit;
this takes the first.

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

## Halo Reach

**COMPLETE 2026-09-30 -- all nine steps built and confirmed in game** on m20: world model
held, dropped and ally-held; first person; own HUD icon and 72-tick meter with the low-ammo
flash at 18; pickup icon on the ground and on trade; reload and ready retimed with their
events; muzzle flash on the barrel. The status table and what stays open are at the end of
the Reach sections ("Reach port status").

*Scoped 2026-09-29:* Reach was expected to be ODST-adjacent. It is
not: it is the *Halo 2* shape of first person laid over a Halo 3 era toolchain, and the
two halves of the port that usually cost the most -- the models and the icon -- move in
opposite directions. Everything below is measured from HREK and the live game, not
assumed from the other kits.

### The kit

    set PORT_EK=reach

`h3_kit.py` knows HREK, so the Halo 3 tools resolve against it -- tags, data, tool,
the `haloreach` game folder for the live font packages, and the HUD font index. Anything
that genuinely DIFFERS per kit now goes through `h3_kit.per_kit()`, which **refuses** for
a kit whose value has not been measured instead of quietly handing back Halo 3's. That is
deliberate: a silent fallback is how the ODST balance table returned nothing, how the
ammo step became Halo 1 only, and how a HUD check passed by comparing None to None.

`F:\SteamLibrary\steamapps\common\HREK` is a full kit: `tool.exe`, `sapien.exe`,
`Foundation.exe` (Guerilla's replacement), 305 verbs. It already has a build/install
pipeline in `reach_ek_build.py`, and `reach_place.py` already knows how to append
placements and grow a palette -- both confirmed in game on m20.

Two verb signatures differ from Halo 3 and will silently do the wrong thing:

    build-cache-file <scenario> <platform> <target-language> ...   (Halo 3: two args)
    render <source-directory> <final-or-draft>                     (Halo 3: one arg)

Missions are `m10 m20 m30 m35 m45 m50 m52 m60 m70 m70_bonus`. The kit also carries `m05`
and `m70_a`, which the game does not run -- the same trap `reach_ek_build.py` already
avoids by taking its list from halo.json.

### What is CHEAPER than ODST

**One render model, not two.** Reach has no per-weapon first-person render model. There
is a single shared arms model, `objects\characters\spartans\fp\fp.render_model`, and the
weapon's `first person` block pairs the weapon's OWN WORLD MODEL with a per-species
animation graph. Read straight out of the Assault Rifle's tag references:

    model  objects\weapons\rifle\assault_rifle\assault_rifle
    jmad   objects\characters\spartans\fp\weapons\rifle\fp_assault_rifle
    model  objects\weapons\rifle\assault_rifle\assault_rifle      <- the SAME model
    jmad   objects\characters\elite\fp\weapons\rifle\fp_assault_rifle

So step 1 builds one model instead of fp + world, and the whole `h3_saw_wire_model.py` /
`h3_saw_world_model.py` split collapses. It also means the region-name trap
(`'default'` vs `'standard'`) applies to ONE model, not four.

**The icon is nearly free, and that is the surprise.** Step 8's glyph half cost Halo 3 a
cracked codec. Reach needs none of it:

* `haloreach\maps\fonts\font_package_icon*.bin` ships LOOSE in the game folder, exactly
  as Halo 3's does -- so a glyph shows up with **no map rebuild**;
* the format is identical. `h3_font_package.py`'s block reader parses all four 0xC000
  regions of Reach's package with every bound sane, and **`h3_font_codec.decode` decodes
  all 353 Reach glyphs with zero failures** (Halo 3: 291, also zero). The opcode stream is
  the same one.
* there is room: **24,208 free bytes** in the last block and **229 unused private-use
  codepoints** below 0xE160 (Reach uses 0xE006..0xE143 across 6 fonts).

So `h3_weapon_glyph.py` should reach Reach on a kit switch rather than a rewrite.

**The HUD font is index 3 -- measured, not deduced.** The package header NAMES its fonts,
which settles a question that cost time in Halo 3 and ODST. Reach's six, in order:

    0  icon\fixedsys-9            3  icon\fixedsys_hud-15     <- the HUD font
    1  icon\fixedsys_ui-title     4  icon\fixedsys_ui-15
    2  icon\fixedsys_hud-number   5  icon\fixedsys_ui-16

Halo 3's four are `fixedsys-9`, `fixedsys-ui`, `fixedsys-hud`, `fixedsys-term`, so its HUD
font is 2 -- and Reach's index 2 is `hud-number`, a SEPARATE face for the ammo counter that
Halo 3 does not have. Carrying Halo 3's 2 across would put the glyph in the digits font.

**Step 8's text half ports outright.** HREK has the same three verbs as H3EK and H3ODSTEK
-- `extract-unicode-strings`, `strings`, `strings-localized` -- and the same string list
at the same path, `tags\ui\hud\hud_messages.multilingual_unicode_string_list`. So
`h3_port_messages.py` applies, **including the CRLF trap**, which will empty every other
pickup prompt in the game if the source is read in text mode. Read it with `newline=''`.

### What is MORE EXPENSIVE than ODST

**Step 9 doubles -- against ODST, not against Halo 3.** Reach names TWO first-person
animation graphs, Spartan and Elite, and they are not interchangeable: a species whose
graph will not retime keeps the donor's length and cannot borrow the other's. Both must
be retimed or the Elite rig (Firefight, and m70_bonus) holds a differently-timed weapon.

Halo 3 is the same shape -- it names the Master Chief's and the Dervish's -- so this is
ODST, naming `odst_recon` twice and needing one clone, that is the outlier. **All three
games keep these graphs in the CHARACTER tree**, at
`objects\characters\<who>\fp\weapons\rifle\fp_assault_rifle`; that is not a Reach
difference. What Reach does not have is the per-weapon fp RENDER MODEL that sits beside
the world one in Halo 3 and ODST.

**The kit ships no model or icon SOURCE.** `data\objects\weapons\` is empty, and the
`data\ui\font_icons\*` folders the font settings name are empty too. So
`build_fonts_icon.bat` would rebuild the icon package as BLANKS -- never run it. Edit the
package in place the way `h3_weapon_glyph.py` does, which moves no offsets.

### Step 1, the model: JMS WORKS, and it is the Halo 3 JMS

**Resolved 2026-09-29 by rendering one.** Reach's `tool render` accepts a **version 8200
JMS** -- the exact file the Halo 3 port already produces. The Halo 3 SAW's own
`saw\render\saw.jms` was dropped into HREK unchanged and rendered, and it produced a
1,199,333-byte `jmstest.render_model` with 5 nodes, 5 marker groups, compression info and
real geometry. The only complaints were `unable to find shader 'saw_body'`, because the
shaders were not copied with it.

So step 1 is a KIT SWITCH, not a new importer. FBX and the `import <sidecar-file>` route
exist -- seven `*.sidecar.xml` tests ship under `data\objects\test` -- and are not needed.

Three things about the Reach toolchain that the test turned up:

* **`tool.exe` wants ABSOLUTE paths** for `export-tag-to-xml`, and says
  "Input tag path is not located in the tags directory structure" for the relative path
  H3EK accepts. `render` takes the relative source directory as usual.
* **Reach's skeleton nodes are prefixed `b_`** -- `b_gun`, `b_magazine`, `b_ophandle`,
  `b_safety`, `b_switch` where Halo 3 has `gun`, `magazine`, `ophandle`, `safety`,
  `switch`. Same five, same shape. The JMS template is built FROM the exported skeleton,
  so the names come along on their own; this matters only if one is ever hardcoded.
* **Sixteen marker groups, and the hands are per species**: `left_hand_spartan_fp`,
  `left_hand_elite_fp`, `left_hand_spartan`, `left_hand_elite`, `left_hand_marine`, and
  the right-hand set. The port's model must carry all of them or a Marine or an Elite
  holds it wrong. Halo 3's AR has five marker groups.

#### The region-name trap does NOT apply to Reach

`h3_region_name.py` exists because `tool render` names the region and permutation
**'default'** while every Halo 3 stock weapon says **'standard'**, and the mismatch makes
the world model render as thin air. Measured, both ends of that comparison:

    Halo 3   assault_rifle.render_model   region 'standard' / permutation 'standard'
    Reach    assault_rifle.render_model   region 'default'  / permutation 'default'

Reach's stock convention is the one `tool render` already writes, so the names match and
the rename step drops out. (Variant COUNT is not the mechanism and is not the check --
both games' AR models carry zero variants. The check is the stock region NAME.) Worth
one look the first time a SAW is dropped in front of an ally, but there is nothing to do
up front.

### The pipeline so far

    set PORT_EK=reach

    h3_make_saw.py --write        weapon, projectile, damage effect      (step 3)
    tool export-tag-to-xml        the AR's render_model, ABSOLUTE paths
    saw_to_jms_h3.py <xml> <lmg_rm.xml> 1.0     ONE JMS, the world skeleton  (step 1)
    tool render objects\weapons\rifle\saw final
    <clone two shaders>           saw_body, saw_display                   (step 2, part)
    tool render ... final         AGAIN: a shader that arrives after a render is not in it
    reach_saw_wire_model.py --write   hlmt + BOTH mode refs               (step 1)
    reach_saw_textures.py --write     the H4 skin into both shaders       (step 2)
    tool render ... final             a THIRD time, for the same reason
    balance_port.py SAW "Assault Rifle" "Halo 4" "Halo Reach"           (the table)
    reach_saw_tag_numbers.py --write  the H4 numbers into the tags        (step 4)

Six tags, every chunk tree spanning its file, every reference resolving:

    saw.weapon       37051 bytes, 24 refs      saw.model         23789, 10 refs
    ...bullet.projectile 24411, 10 refs        ...damage_effect   6850,  4 refs
    saw_body.shader  13596, 7 refs             saw_display.shader 9293,  4 refs

**Steps 1, 2, 3 and 4 are done.** The port has its own geometry, its own skin, its own
bullet and damage effect, and its own numbers: magazine 72, 216 carried, velocity 300,
damage 7.5, against the Assault Rifle's 32 / 160 / 3000 / 5.834.

The balance table came straight out of `balance_port.py` on ONE hop, because the Assault
Rifle exists in both games -- 53 rows, 47 balanced, only 2 with no target. Reach's
Assault Rifle is exactly TWICE Halo 4's on velocity (3000 against 1500), a clean game
scale, so Reach needs no `_mgvel` anchor the way Halo 3 did.

There is no XML IMPORTER -- HREK exports tags and cannot read them back -- so step 4 is
byte edits found by a signature of adjacent values that must match exactly once. What
makes that safe is that `export-tag-to-xml` names every field, so each tag is exported
again afterwards and the named fields read back. Two things it caught immediately: a
rounded float literal (6.788) packs to different bytes than the stored one and matched
NOTHING, and `damage upper bound` is a `real bounds` field that exports as one value,
`7.5,7.5`, so its halves are read by index.

THREE THINGS THE HALO 3 TOOLS DID NOT SURVIVE UNCHANGED, all now handled:

* **`h3tag` reads Reach tags as they are.** The chunk format is identical -- the
  Assault Rifle's weapon parses 37111 of 37111 bytes and decodes all 24 references. That
  is the whole tag-editing layer carried over for free.
* **The XML export is a DIFFERENT SCHEMA.** Halo 3 wraps a block's elements in
  `<block name="nodes" value="node,5">`; Reach has no `<block>` tag anywhere in the
  file and instead writes a self-closing `<field name="nodes" value="5" type="block"/>`
  with the elements following as SIBLINGS. Read as Halo 3 this yields nothing, and the
  skeleton comes back empty.
* **Block indices are NAMES.** Halo 3 writes `node,3`, Reach writes `b_ophandle`, and
  `NONE` for no link -- so an index has to be resolved against the names already read.

And one that would have been silent: Reach's nodes are `b_`-prefixed, so the H4 bone map
keyed on `gun` and `magazine` matched nothing and fell back to node 0, welding the
magazine to the body. It raises now instead.

All 16 marker groups come across, per-species hands included. 10736 verts, 13836 tris.

### A dangling reference that is REACH'S, not the port's

`saw_body.shader` points at `objects\weapons\boneyard\battle_rifle\bitmaps\battle_rifle_illum`,
which does not exist. So does the STOCK `assault_rifle_composite.shader` it was cloned
from -- HREK ships no `objects\weapons\boneyard` folder at all. `tool render` does not
complain and the model builds. Inherited, not introduced; do not go looking for it
twice.

### Step 5, the catalog: the simplest of the four

`make_port_catalog_reach.py` -- 45 balance rows, none of them pointing at a donor or a
shared tag. Reach needs less special handling than any other game:

* **no Machine Gun detour.** Bullet speed is measured against the Assault Rifle, which
  Reach runs at exactly twice Halo 4's, so there is no `_mgvel` table.
* **no `MEASURED` step.** ODST needs six rows read straight off the donor's tags for
  fields no card can reach there; all six are card-reachable in Reach.
* **one PORT_TAGS entry serves two classes**, because the damage effect shares the
  projectile's path.

Dropped: the three MELEE rows, which point at `globals\damage_effects\strike_melee` and
would retune the whole sandbox. `anims` ships ABSENT, as Halo 3's does and unlike
ODST's -- the port shares the Assault Rifle's graphs, so retiming would retime the
Assault Rifle for both species.

**The 320 / 288 question is answered, and it was arithmetic.** The tag's `rounds total
maximum` is the RESERVE PLUS THE MAGAZINE: Reach's Assault Rifle reads 320 in the tag,
288 through the plugin's "Rounds Inventory Maximum" and 32 loaded, and 288 + 32 = 320.
So the port's is 216 + 72 = 288 -- which is the number `h3_saw_tag_numbers.py` writes
for Halo 3, reached from the other end. The catalog derives the balanced total the
same way, because nothing in Reach recomputes it.

### Step 6, the ammo pickup: DONE, and Reach has THREE where ODST has eight

MEASURED on a built m20, not assumed: the Magazines/Magazines element is 20 bytes with
`Rounds` i16 at +0 and the equipment reference's 4CC ('piqe') at +4, so `ref_offset` is
4 and the patcher writes the datum at +0xC from there -- identical to ODST.

Reach consolidated its pickups. Reading every eqip tag off all ten missions gives one
generic `ammo_box` plus `rocket_launcher_ammo` and `sniper_rifle_ammo`, and all three are
on ALL TEN missions -- so unlike Halo 1 and ODST there is no per-map `maps` key to carry.
Everything else in Reach's eqip list is an armour ability, a grenade or a health pack.

### Step 9: the graphs are UN-SHARED, the retiming is not done

`h3_saw_animations.py --write --clone-only` clones both species graphs to
`objects\weapons\rifle\saw\fp\fp_saw_{spartans,elite}` and repoints the weapon. The path
shape is identical to Halo 3's, so `_graph()` builds them unchanged.

**Retiming fails, and this is the real cost of Reach's step 9.** `h3_anim_decode` reads
Reach's frame data past the end of the buffer:

    struct.error: unpack_from requires a buffer of at least 7784 bytes ...
                  (actual buffer size is 7704)

So Reach's animation layout is NOT Halo 3's, and decoding it is its own job -- the same
size as the Halo 3 and Halo 2 codec work. `--clone-only` exists for exactly this: the
port keeps the Assault Rifle's timing but no longer SHARES it, so whenever the format is
cracked the retime cannot reach a live weapon.

### Step 7, the HUD: DONE, and it CANNOT wait for the rebuild

Reach's chud has no meter -- it draws ammo as a NUMBER -- so step 7 is only the
`low ammo loaded threshold`, 8 of 32 on the Assault Rifle, which a port holding 72 would
inherit and cry low at a ninth of its magazine. A quarter of 72 is **18**.

**It must happen BEFORE the build, not after.** The cache builder deduplicates identical
block data, so a byte-identical chud clone comes out of the build SHARING the Assault
Rifle's blocks -- Halo 3 measured exactly that, and writing one moved the other. Writing
the threshold into the TAG is what makes the two differ and keeps them apart. Deferring
it until after a rebuild does not work: it would need another rebuild.

`h3_saw_chud.py` already had the locator and it works on Reach unchanged: the chud's root
struct is the FIRST `bdat`, and the threshold triple sits at its `tgbl` payload + 0x14.
A raw byte search does not work (8 appears 85 times as a long; `(8,0,0)` still matches 45
times, and no `tgst` chunk starts with those longs) -- which is why the chunk-tree route
is the answer and not a nicety.

Validated across Reach's own weapons, and the last two are the proof:

    assault_rifle (8,0,0)   dmr (3,0,0)     magnum (3,0,0)    shotgun (2,0,0)
    sniper_rifle  (1,0,0)   needle_rifle (5,0,0)   spike_rifle (10,0,0)
    plasma_rifle  (0,0,20)  focus_rifle  (0,0,20)   <- BATTERY weapons

The third member is `low battery threshold` and only the energy weapons use it, which is
what confirms the triple is (loaded, reserve, battery) rather than a coincidence.

Done: `ui\chud\saw` holds 18, the Assault Rifle still holds 8, and the weapon is repointed.

### Step 8: DONE -- the glyph is in, and the port has its own lines

The icon renders from the port's own mesh at all three resolutions (155x44, 310x88,
465x132) and the codec is Halo 3's, unchanged. It did not FIT anywhere, which is what
`h3_font_grow.py` exists for; see the glyph-ceiling section. Reach's codepoint is
**0xE150**, above the 0xE143 its HUD font tops out at in all three packages, because an
appended block goes at the END of the file.

**The glyph is LIVE.** The packages are loose files in `haloreach\maps\fonts`, so it is
already there with no rebuild. The MESSAGES are in the map's string list and are not.

`h3_port_messages.py` ran against HREK unchanged -- same three verbs, same list path.
**Reach has SEVEN lines where Halo 3 and ODST have five**, adding `saw_switch_to` ("Out
of ammo / Press ... to switch to") and `saw_swap_ai` (taking an ally's weapon). All
eleven non-English languages got them, 4 localized and 3 English fallback each -- the
same split as ODST, because the prompts carry only an icon while the confirmation and the
two ammo lines name the weapon.

The list went 298,702 -> 319,253 bytes and the weapon's five message ids are repointed.
**The CRLF trap did not fire**, and the proof is two numbers: `tool` reported 702 english
strings rather than a small delta, and the count of unpointed (-1) words came out at TWO,
below the THREE the shipped list already carries.
### What is NOT done

Step 7 (above), step 8's glyph placement and its messages, and step 9's retiming. The
messages themselves are untried: `h3_port_messages.py` refuses until the glyph codepoint
is settled, which is correct -- a message pointing at a codepoint with no glyph is a
blank box.

### The unknown still worth measuring

1. residency. Reach is the one game where a placed weapon can be inert because its tag's
   bit is clear in the first zone set's pool. A fresh EK build pools what the scenario
   references, so this should be a no-op for a built map -- but it is the standing HALF /
   LATE audit in `reach_pools.py`, and it is the first thing to check if the SAW spawns
   as nothing.

### Where it goes in

Reach has no equivalent of ODST's "placement alone is not enough" finding yet, because
the ODST result came from a starting profile and Reach's starting profiles are a
different shape -- named per difficulty, per co-op and per area, with the armor-ability
reference at +0x54 marking a player profile. Expect to place it in Sapien AND wire a
profile, and expect that to be the step that costs a rebuild to learn.

---

## Step 8, the text: A PORT BRINGS ITS OWN LINES

**This replaces every borrow, and it is the general answer.** Read it before the
per-game notes below, which now only record what each game still needs.

The old method took a live weapon's five message ids and edited its text. It never
generalised: the donor has to be a weapon that never appears, Halo 3 only had one
(the automag, which is ODST's STARTING PISTOL), and every remaining candidate is itself
a future port. Hijacking also reaches OUTSIDE the map, into a localization file shared
by every install of that game.

The Editing Kits could do this all along. The verbs, per kit:

| game | extract | import | tool |
|---|---|---|---|
| Halo 3, ODST | `extract-unicode-strings <list>` | `strings <dir>` **+** `strings-localized <dir>` | `h3_port_messages.py` |
| Halo 2 | `extract-unicode-strings <list>` | `new-strings <dir>` (all languages at once) | `h2_port_messages.py` |
| Halo 1 | — (Reclaimer reads the tag) | — (Reclaimer writes it) | `h1_port_messages.py` |

The source is UTF-16, a `[Strings]` header and one `name = "text"` per line, with icons
as NAMED MACROS (`&assault_rifle`, `&button_action_weapon_primary`). There are 39 macros
and no `&saw`, because the table lives inside `tool` rather than in a tag -- which does
not matter, because a **literal private-use character** works in its place.

So: clone the donor's lines, rename the prefix, swap its icon macro for the port's own
codepoint, re-import. `h3_port_messages.py` does it, and `--repoint` renames whichever
donor prefix the weapon actually carries, so one command converts a hijacking port into
an owning one.

### THE THREE TRAPS, all of which bit

* **CRLF.** The extracted source is CRLF and reading it in TEXT mode collapses that to
  LF. Written back, `tool` reads the whole vanilla body as ONE malformed entry, imports
  only the lines you appended, and leaves every pre-existing string with **english offset
  -1** -- text still in the blob, no pointer to it. In game that is every weapon's pickup
  prompt showing NO TEXT AT ALL, while the port's shows correctly. Measured: 479 of 487.
  Read with `newline=''`.
* **`extract-unicode-strings` reports only the DELTA after an import.** Re-extracting
  returns 8 entries and looks exactly like catastrophic data loss. It is not.
* **Do not delete the tag first.** It does make every string "new", and it discards the
  eleven other languages. It was only ever a workaround for the CRLF bug.

### Languages

`--languages` clones the port's lines into each `data_XX` source. The split is the icon
and it falls out of the data: the four PROMPT lines carry the icon macro and name no
weapon, so the localized text is cloned verbatim with only the icon swapped -- right in
every language, no translation. `picked_up` and the two ammo lines DO name the weapon,
and a name cannot be substituted into a translated sentence safely (the differing span
between two weapons' lines comes out as `'assau`, `n Assault`, half a Chinese word), so
those three take the English line. Result on both Halo 3 and ODST: no missing offset in
any of the twelve languages.

### Where each game stands

**All four now own their lines.** None takes anything from a live weapon, and the two
edits that reached OUTSIDE the map -- into localization files shared by every install of
their game -- have both been undone.

* **Halo 3: ODST** — done and confirmed in game. 487 entries, all twelve languages.
* **Halo 3** — done in the tags, needs a map rebuild. 475 entries, all twelve languages;
  repointed `am_*` → `saw_*`, and `h3_mcc_localization --restore` gave the automag its
  glyph back.
* **Halo 2** — done in the tags, needs a map rebuild. 332 → 339 entries in all NINE
  languages (its `new-strings` does every language in one pass); repointed `gpmg_*` →
  `saw2_*`, and `h2_saw_messages --restore` gave the cut GPMG its three lines back.
  **The prefix is four characters because H2 POOLS these ids with no terminators**, so a
  rename must not change length — the same trap `h2_tagref` documents for tag paths. The
  weapon comes out at exactly 3971 bytes, unchanged.
* **Halo 1** — done in the tags, needs a map rebuild. Its ICON was always owned (a new
  sequence appended to the shared sheet); the text was not. The engine reads the index
  AND the one after it, so a port needs a PAIR: appended at 47/48, weapon repointed from
  4. **Halo 1 is the only one where appending is trivially safe** — its list is addressed
  BY POSITION, so nothing before a new entry can move.

Each needs its map rebuilt before the change shows, ODST excepted.

### The localization .bin, for the record

It is no longer on the critical path -- the map's strings win once the list changes --
but it is not the black box the ODST notes first called it. **Its index is a table of
(hash, offset) pairs**, 7506 in Halo 2's English file, offsets monotonic; that is how
`h2_saw_messages.py` edits it safely. Its length must never change: shortened lines are
padded back with SPACES, never NULs, because a NUL ends the string early and everything
after it becomes a new entry -- which is how 21 phantom entries once turned Halo 3's
assault rifle pickup line into "CARNAGE REPORT".


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

**The source tag is `objects\weapons\rifle\storm_lmg\storm_lmg.render_model` in H4EK.**
The SAW is called the storm_lmg there, which is not guessable, and every port's geometry
comes out of it — all four converters take that export as `lmg_rm.xml`, and it has been
living in `%TEMP%`, one cleanup away from being the next thing rescued out of a
scratchpad. It is reproducible in one command:

    tool export-tag-to-xml <H4EK>\tags\objects\weapons\rifle\storm_lmg\storm_lmg.render_model %TEMP%\lmg_rm.xml

---

## Open, and deliberately so

* **The port's non-English confirmation lines are English.** The four prompt lines are
  properly localized in all twelve languages; `picked_up` and the two ammo lines fall back
  to English, because a weapon name cannot be substituted into a translated sentence
  safely. Fixing it needs a real translation per language, which is a content job.
* **The crosshair is not ported in Halo 1 or Halo 3 yet.** Only Halo 2's is. The method is
  game-agnostic -- H4EK specifies the layout, so the same read applies -- but both earlier
  ports still wear their donor's reticle. ODST inherits Halo 3's, so it is in the same
  position.
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

---

## What deploys, and what the toolkit is missing

Audited 2026-09-29, after a build died on a script that had never been in the repo.

### Only Halo 1 deploys on its own

    saw_build.py          DEPLOYS BY DEFAULT      --no-deploy to stop it
    h2_saw_place.py       only with --deploy
    h3_saw_deploy.py      only with --install     (Halo 3 and ODST, kit-switched)
    odst_ek_build.py      only with --install
    reach_ek_build.py     only with --install

Halo 1 is the odd one out: it is the oldest chain and predates the others. Everything
that writes a live map elsewhere -- the H4 test tools, `reach_place.py`,
`reach_keep_hud.py`, `h1_weapon_ring.py`, `h2_saw_glyph.py` -- backs the file up first
and is gated behind `--write`, `--deploy` or `--install`.

### Nine tools were lost with a scratchpad; one mattered

`port_backup.py`'s `SCRIPTS` list is the manifest of what a port's tooling consists of,
and it is the only record of what the session scratchpad held before df48675 promoted
21 tools out of it. It ran NINE names short and said so only as a count:

    saw_port_values.py      REBUILT -- it was step 4, and saw_build.py called it
    ammo_pickups_scan.py    h3_weapon_census.py     h3_tagtable_probe.py
    check_families.py       h3_verify_magazine.py   jms_add_colour.py
    saw_h3_bench.py         tagvals.py

Every one of the remaining eight is referenced by **nothing but the manifest** -- no
build chain calls any of them, so they were surveys, probes and benchmarks rather than
steps, and the four chains are complete without them. They are left in the manifest on
purpose: it is the record that they existed.

`port_backup.py` now NAMES a shortfall instead of printing `31 of 39`, which is the
thing that would have caught this the day it happened.

**RECOVERED 2026-09-30.** All eight were in the 2026-09-21 backups under
`F:\HaloPortBackups\*\scripts\` (one version each across every backup) and are back in
the toolkit. The manifest now checks complete for h1, h2 and reach.

---

## SCALE: it is 140 ports, and the pipeline is built for one

Counted 2026-09-29 with `port_matrix.py`, off the weapon spreadsheet, whose answer is in
the cell COLOURS and not in its text.

    56 weapons in the sheet
    45 SOURCEABLE -- they exist in at least one MCC game
    11 exist in no MCC game at all (Halo 5 / Infinite) and cannot be ported from anywhere

    Halo: CE       12 has, 33 missing      Halo 3: ODST   22 has, 23 missing
    Halo 2         18 has, 27 missing      Halo: Reach    23 has, 22 missing
    Halo 3         26 has, 19 missing      Halo 4         29 has, 16 missing

    140 port jobs to fill every gap.

**"MP only" counts as HAS IT.** If the tags are already in the game, a campaign
appearance is a placement and residency problem -- no geometry, no shaders, no
animations. Lumping those in with real ports overstates the work, so the matrix keeps
them apart.

### What the SAW cost, and why that does not multiply

One weapon into four games took the whole of this document. At that rate 140 is not a
project, it is a decade. But most of what it cost was PER GAME, not per weapon, and that
half is now done and amortises across every future port in that game:

* the kit selector, and `per_kit` refusing to guess;
* the tag format -- `h3tag` reads H3, ODST and Reach unchanged;
* the JMS version, and the two XML schemas the exporters use;
* the string verbs and the CRLF trap;
* the font package format, its codec, and the block-occupancy rule;
* the chud threshold locator;
* the balance machinery -- `balance_port.py` already derives a table for ANY weapon pair
  from the games' own tags, which is the one part that was general from the start.

### What actually multiplies, and therefore what has to become DATA

**77 of the 215 tools mention `saw` by name.** That is the whole problem in one number:
there is a SAW pipeline, not a port pipeline. Everything below is per WEAPON and is
currently a constant in a script:

    the donor            which weapon's skeleton and animations it inherits
    the source geometry  which H4/H3/H2 render_model, and its bone -> node map
    the markers          which of the donor's the port keeps and which it moves
    the tag names        saw, saw_bullet_h4_original_numbers, fp_saw_<species>
    the numbers          magazine, reserve, velocity, damage
    the icon             its codepoint, per game, per package
    the messages         its prefix and its lines

So the next step is a **port manifest**: one file per (weapon, target game) carrying
exactly those, and tools that read it instead of holding constants. Nothing about the
method changes -- the nine steps are right, and each one has now been proven in three
engines -- it is the same steps driven by data.

### The leverage, which is not evenly spread

    in 1 game: 16 weapons   <- 5 targets each, 80 of the 140 jobs
    in 2 games: 8      in 3: 5      in 4: 6      in 5: 1      in 6: 9

**Sixteen weapons account for more than half the work**, because a weapon that exists in
one game is missing from five. Extracting ONE of those well -- geometry, textures,
numbers -- pays off five times, and the Halo 4 set is most of them. That is the opposite
of the SAW's shape, which was one source and four targets, and it is the argument for
making the SOURCE side of the pipeline data-driven first.

The other end is nearly free: the nine weapons already in all six games need no ports at
all, and the H3 to ODST direction is byte-identical territory where a port is mostly a
copy.

---

## THE GLYPH CEILING: the first hard limit on how many weapons a game can take

Measured with `glyph_capacity.py`. A ported weapon needs a pickup icon, and from Halo 3
on that icon goes into `maps\fonts\font_package_icon*.bin`, which are FIXED SIZE. So
"how many weapons can this game accept" has a hard answer, and it is far below the
number of weapons there are to port:

    game        icons that still fit      weapons missing (port_matrix.py)
    Halo 3              4                         19
    Halo 3: ODST        1                         23
    Halo Reach          1                         22

**The space is not where it looks.** A package is a series of 0xC000 blocks, and each
font's glyphs are spread across them as ascending RUNS. A new glyph sorts into the run
its codepoint extends, so the only free space it can use is the tail of THAT block --
not the package's total. Reach's x1 has 25,616 free bytes and exactly 1,408 of them are
reachable by the HUD font. That is the difference between twelve more icons and one.

And **all three resolutions must take it**, so the ceiling is the smallest of them. x1 is
usually the binding one because it is the smallest file.

### Halo 1 has no ceiling, and that is the shape to copy

Halo 1 has no font package at all. Its pickup icon is a sequence in the shared
`hud_msg_icons` BITMAP, and `add_msg_icon.py` APPENDS a bitmap and a sequence, growing
the tag. Unbounded, and already proven. The later games' packages are the exception, not
the rule.

### Four ways out, cheapest and least risky first

1. **ONE SHARED GLYPH for every port.** A single "ported weapon" icon costs one slot in
   total instead of one per weapon, works today in every game, and needs no new format
   understanding. It is the only option that is free right now. The cost is that every
   port shows the same picture in its prompt.
2. **REPACK THE BLOCKS.** Redistribute each font's runs so the free space is reachable.
   Uses only the format already decoded and proven, no engine assumptions. Takes
   Halo 3 to 8, ODST to 22, Reach to 12.
3. **SMALLER ICON ART.** The SAW costs 726 bytes at x1 for 155x44. Halving that takes
   Halo 3 to 17 repacked, ODST to 19, Reach to 14 -- and it composes with (2).
4. **GROW THE PACKAGE.** The block count is not stored anywhere: every reader derives it
   from the FILE SIZE, and the shipped packages already vary from 4 blocks to 22. So
   appending a block is plausible and would remove the ceiling entirely. It is also the
   only option that needs an in-game test to trust, because nothing proves the engine
   sizes it the same way.

(2) and (3) together look sufficient for ODST and Reach and marginal for Halo 3; (4) is
the one that actually ends the problem. (1) is the fallback that unblocks porting
immediately if the others take time.

### (4) IS BUILT: `h3_font_grow.py`, and the ceiling is gone

Appending a block works. Done to all three of Reach's live packages, each gaining exactly
one block and exactly one codepoint:

    x1   245,760 -> 294,912 bytes    4 -> 5 blocks
    x2   589,824 -> 638,976         11 -> 12
    x3 1,130,496 -> 1,179,648       22 -> 23

    353 -> 354 entries in each, all 354 decode, nothing lost, font 3 still ascending.

**The best evidence is not that test -- it is ODST.** Halo 3 ships a FOUR-block,
245,760-byte x1; ODST ships a FIVE-block, 294,912-byte one. Same engine, same format,
and a grown Reach x1 is byte-for-byte that shape. The block count is stored nowhere: every
reader derives it by walking the file in 0xC000 steps and accepting what validates as a
block header. The walk IS the format.

**A new block goes at the END of the file**, and a font is one ascending list read across
the blocks in file order, so it can only carry codepoints above that font's highest.
Reach's HUD font tops out at 0xE143 in all three packages, so Reach's glyph is **0xE150**.
`grow()` refuses anything lower and `ordered()` proves the result.

Still needs ONE BOOT to trust: nothing in the bytes proves the ENGINE sizes the package
the way the readers do. If it does, there is no glyph ceiling in any of these games and
a port costs 48 KB of font package.

### The two bugs that were damaging packages, both fixed

The write path **wrote the file and then checked it**, so a failed check left the damage
on disk and only said "restore it". And it checked `fp.bounds`, which is FALSE on Reach's
SHIPPED package -- its `ui-16` header claims 98 glyphs where the tables hold 96 -- so
every Reach write wrote and then raised. That is what emptied x1 earlier, not the
insertion.

`h3_weapon_glyph.verify()` now runs BEFORE the write: nothing lost, exactly one codepoint
gained, and every glyph in the result decodes. A global "adds up" check cannot do that on
a file whose shipped header disagrees with its own tables -- diff against a pristine copy
instead.

### Two games still unmeasured

* **Halo 2** edits eight fonts in place under `h2_fonts` rather than using a package
  (`h2_font_add.py`), so its ceiling is a different measurement.
* **Halo 4's packages are not 0xC000-blocked** -- 327,680 is not a multiple of it, and
  the x3 tables do not sit where the others' do. It has FOUR resolution tiers rather than
  three. It needs its own reader before its ceiling can be stated, and it is a port
  target for 16 weapons.

**This is a restrictor, not a detail.** Nine steps can be automated and a manifest can
make the pipeline generic, and none of that matters if the eleventh weapon in a game has
nowhere to put its icon.

---

## GLYPH CAPACITY, ALL FIVE GAMES: NO CEILING (2026-09-30)

    Halo 1   the icon is a sequence in the hud_msg_icons BITMAP; add_msg_icon.py appends
    Halo 2   one font per file; h2_font_add.py appends a record + payload (+2,288 bytes per
             icon per font, 8 fonts). halo2.dll opens each font with CreateFileA (random
             access, 0x6f41e1) and reads glyphs by offset on demand -- no whole-file
             buffer, so no size cap. The only limit is 12 font FILES (the scan at
             0x6f3f70); ports add none. Already past the largest shipped size
             (handel_gothic-24 644,684 > 642,396) with the SAW drawing.
    Halo 3 / ODST / Reach   h3_font_repack.add_glyph: packages grow by whole blocks,
             confirmed in game on Reach (the section below).

## THE BLOCK INDEX -- and why "native range" was the wrong rule (2026-09-30)

**Supersedes the section below.** Right after the font headers, in the header region,
every icon package carries one pair of u32 keys PER BLOCK -- the first and last entry the
block holds -- with key = `font << 16 | codepoint`. It matches every block of all nine
shipped packages (Halo 3, ODST, Reach x x1/x2/x3) exactly, and nothing follows it. The
package is ONE list ascending by that key, cut first-fit into 0xC000 blocks; the index is
how the engine picks the block to search.

`h3_font_repack.py --selftest` rebuilds all nine shipped packages from their glyphs,
first-fit, and gets every file back BYTE FOR BYTE -- so this is exactly what the kits'
`tool font-package` does, and a package rebuilt with a new glyph sorted in is what the
official tool would have written.

What it re-explains:
  * Reach 0xE150 in an APPENDED block: the index did not list the block -> box.
  * Reach 0xE150 placed in block 4: block 4's range is font 5 only -> box. The "above
    the font's native top" explanation below was a coincidence of both.
  * Halo 3's 0xE06A and ODST's 0xE04A each became the LAST entry of an x2 block with the
    index left one codepoint short, so they could not draw at x2. FIXED with
    `h3_font_repack.py --fix-index --write`; all nine live indices now check.
  * h3_font_add / place / grow never touched the index. `h3_font_repack.add_glyph` is
    their replacement: rebuild around the new glyph, grow by whole blocks, rewrite the
    index. The capacity question then becomes the index's room in the header region
    (thousands of blocks) and free codepoints -- not bytes.

**Growth test, Reach, written to the live packages:** fonts 0-2 spread over the SHIPPED
block count, so the ENTIRE HUD font (every weapon icon, the SAW's included) sits in
blocks the package never had -- x1 4->7, x2 11->21, x3 22->41, every record identical.
FIRST BOOT: every weapon icon broke -- the test had left each font's OWN block range alone: the third u32 of a font's header triple is (blocks spanned << 16) | first block (all fonts, all nine packages). assemble() now rewrites it; test rewritten. SECOND BOOT: most icons GONE; a same-count --shift test then DREW -- so a count cap. The count is IN the file: header +0x410 = index offset, +0x414 = block count (all nine packages), read by haloreach.dll's glyph lookup at 0xcca68, which bsearches that many 8-byte index entries (blocks are then paged through an 8-slot cache). assemble() now writes +0x414. Third test: the real growth again, counts 7/21/41. **THIRD BOOT: ALL ICONS DRAW -- GROWTH CONFIRMED.** h3_weapon_glyph now calls h3_font_repack.add_glyph (any free codepoint, grows by whole blocks); add/place/grow and glyph_capacity are superseded. Checked in memory: 40 heavy icons took Reach x1 from 4 to 24 blocks, verify() clean. Icons normal = the engine reads grown packages. Every weapon icon broken = it caps at the
shipped count. Undo: `h3_font_repack.py --undo-growth-test haloreach`.

## THE CODEPOINT MUST BE INSIDE THE FONT'S NATIVE RANGE

Measured in game, Reach, 2026-09-29, and it corrects the glyph-ceiling plan.

The port's prompt drew a BOX while **"Picked up a SAW" on the same screen was correct**.
That one detail settles a lot: the string list, the weapon's message ids, the import and
the twelve languages all work, and ONLY the glyph lookup failed.

It failed at 0xE150 in an APPENDED block, and it failed at 0xE150 in an EXISTING block
that the engine was already reading. **So the block was never the problem.** What is wrong
with 0xE150 is that it is above 0xE143, where Reach's HUD font natively stops:

    halo3      HUD font 0xE006..0xE150 natively   added 0xE06A   INSIDE   works
    halo3odst  HUD font 0xE006..0xE150 natively   added 0xE04A   INSIDE   works
    haloreach  HUD font 0xE008..0xE143 natively   added 0xE150   ABOVE    box

Both precedents agree and neither was chosen on purpose -- they happened to be free in a
range that also happened to be inside. The font header's top-codepoint bound updates
correctly (0xE144 -> 0xE151) and the entry decodes, so nothing in the FILE is wrong. The
engine simply does not resolve an icon above the font's shipped top.

Reach's glyph is now **0xE052**: free, inside the range, and sorting into a block with
room in all three packages, whose boundaries differ completely. The packages are back to
their shipped sizes and block counts, 354 of 354 entries decode, and the messages were
re-imported so the tag holds 48 occurrences of U+E052 and none of U+E150.

### What this does to the ceiling

**A naive append cannot add a usable icon.** A font is one ascending list read across the
blocks in file order, so an appended block can only carry codepoints ABOVE the font's top
-- and those are exactly the ones the engine will not resolve. Growing the file is safe
(the text was undisturbed) and useless on its own.

What growth needs is a REPACK: rebuild the package with N+1 blocks and redistribute every
run, so the new block holds a mid-range slice and the ascending order still reads. Then
the binding constraint stops being bytes and becomes free IN-RANGE codepoints -- of which
Reach has 103 free in 0xE093..0xE143 alone and 229 below 0xE160.

So the ceiling is not 1, and it is not unbounded either:

    today, no repack        Halo 3 4, ODST 1, Reach 1
    repacked in place       Halo 3 8, ODST 22, Reach 12
    repacked AND grown      limited by free in-range codepoints, which is ~100+

The middle row needs no new format understanding. The bottom row needs a real repacker
and is the one that reaches 140.

---

## `tool render` STRIPS A LEADING `b_` FROM NODE NAMES

Reach only, and it is the whole of the empty first-person model and the weapon that
vanished when dropped.

Reach's skeleton is entirely b_-prefixed -- `b_gun`, `b_magazine`, `b_ophandle`,
`b_safety`, `b_switch`. The JMS declared exactly those, because the converter reads them
out of the Assault Rifle's own export. `tool render` then wrote a render model whose
nodes are called `gun`, `magazine`, `ophandle`, `safety`, `switch`.

    assault_rifle   parent node  NONE, b_gun, b_gun     first child  b_ophandle
    saw (before)    parent node  NONE, gun, gun         first child  magazine

**So nothing that ANIMATES the weapon could find its nodes.** The statically placed
weapon still drew, because bind pose needs no graph -- which is exactly what made this
look like a rendering fault rather than a naming one. First person was empty and a
dropped weapon vanished, and residency, the region name, the model wiring, the geometry
chunks and the compression bounds were all checked and all innocent.

The fix is to declare `b_b_gun` and let the strip leave `b_gun`. Confirmed: the render
model now reads b_gun / b_magazine / b_ophandle / b_safety / b_switch, all parented to
b_gun with a valid sibling chain. `saw_to_jms_h3.py` carries it as `NODE_PREFIX`, per
kit, because Halo 3 and ODST have unprefixed skeletons and there is nothing to protect.

This is the same shape as the region-name trap in Halo 3: `tool` rewrites a NAME on the
way in, the tag is otherwise perfect, and only the thing that looks the name up notices.
Whenever a ported model is silently wrong, compare its node and region names against the
donor's FIRST -- it is one export and a diff, and it is the cheapest check there is.

---

## `tool render` ALSO SORTS THE NODES, and the world graph indexes into them

The second half of the same trap, and it is what the eliminations below were closing in
on. Measured: `b_b_switch` comes out `b_switch` while `a_b_gun` is left alone, so the
strip is exactly a leading `b_` -- and the order that comes out is ALPHABETICAL on the
stripped name, whatever the JMS declares.

    donor        b_gun, b_switch, b_safety, b_magazine, b_ophandle
    alphabetical b_gun, b_magazine, b_ophandle, b_safety, b_switch

**The world animation graph carries its own 5-node skeleton and its animation data
indexes INTO it**, so a port whose nodes came out sorted has indices 1..4 permuted
against the graph that poses it. That is the whole of it:

    placed by the scenario   bind pose, no graph          DRAWS
    first person             the 52-node ARMS graph, and the weapon hangs off it by
                             MARKER rather than by node index               DRAWS
    held by an ally, dropped posed through the world graph                  NOTHING

Order cannot be asked for, so it is bought with a sort key and the key is renamed away.
`saw_to_jms_h3.py` emits `b_a_gun`, `b_b_switch`, `b_c_safety`, `b_d_magazine`,
`b_e_ophandle`; `tool` strips the `b_` and sorts on `a_gun`, `b_switch`, ... which IS the
donor's order; `reach_node_names.py` then renames `a_gun` to `b_gun` and so on. Every
rename is one character for one character, so each is an in-place byte swap with no chunk
length to propagate -- unlike Halo 3's region rename, which grows the file.

Run it after EVERY `tool render`, like the region rename in Halo 3. The port's nodes now
read b_gun, b_switch, b_safety, b_magazine, b_ophandle -- the donor's names in the
donor's order.

---
## THE WORLD MODEL: what has been ELIMINATED

After the `b_` fix, first person works and its animations look right. The WORLD model
still draws nothing -- on the ground and in an ally's hands. Both go through the same
render model, and the only thing between them is the model tag, so the search space is
small and most of it is now closed. Recorded so none of it is checked twice:

* **residency** -- `reach_pools.py m20 --audit`: 34 palette entries, 0 HALF-loaded, 0 not
  resident at start. The FULL CLOSURE is live, not just the weapon;
* **the geometry in the map** -- `h3_chunk_check`: `mode saw` 1 chunk, 1 backed, same as
  the Assault Rifle, plus both bitmaps and `saw_body`;
* **the model tag** -- `saw.model` exported to XML is IDENTICAL to the Assault Rifle's in
  all 99 fields except the render-model reference. Not the LOD distances, not the
  imposter policy, not the checksums;
* **the region and permutation names** -- both `default`/`default`, and every other field
  of the regions block matches: mesh index, mesh count, all four instance masks, the L1
  and L2 section group indices. This is where Halo 3's identical symptom lived, and it is
  not where Reach's does. `default` is universal across Reach's stock weapons;
* **the mesh format** -- same vertex type (skinned), same rigid node index (-1), same
  index buffer type (triangle strip), same mesh count, same runtime flags;
* **the compression bounds** -- same axis convention, comparable scale (1.05 m).

One real difference remains and its significance is unknown: **`tool render` emits the
nodes in a different ORDER than the donor's.** The Assault Rifle reads b_gun, b_switch,
b_safety, b_magazine, b_ophandle; the port reads b_gun, b_magazine, b_ophandle, b_safety,
b_switch -- alphabetical after the prefix strip. The hierarchy is equivalent (every node
is a child of b_gun, with a valid sibling chain) and the JMS declares the donor's own
links, so this is tool's own traversal, not lost data. It would matter only if a graph
addressed nodes by INDEX -- and the first-person graph is a clone of the donor's and
animates correctly, which argues it resolves by name.

The next step is the bisect Halo 3 used: point `saw.model`'s `mode` back at the Assault
Rifle's render model and rebuild. If a dropped weapon then draws as an Assault Rifle the
fault is inside the port's render model; if it still draws nothing the fault is in the
weapon or the model tag, and neither of those differs from the donor.

---

## THE BISECT ANSWERED: the fault is INSIDE the port's render model

With `saw.model` pointed at the DONOR's render model and everything else the port's own,
the result in game was:

    in your hands      the SAW      (first person reads the weapon's own `first person
                                    model`, which still points at the port's)
    dropped, on allies the ASSAULT RIFLE

So **the world path works and renders** -- it just will not render THIS render model,
while the first-person path renders the same tag happily. That halves the problem and
rules out the weapon tag, the model tag and how the object is built.

### What tool itself says about it

The port's render model carries three entries in its `errors` block that the donor's does
not. The first is the interesting one:

    no region/permutation found in material names, model will be a single region

and the string it comes from spells out why:

    'identical material/shader names found - assuming legacy parsing mode
     (single default region/permutation)'

Our materials are `saw_body` and `saw_display`, and the shaders are called `saw_body` and
`saw_display`, so `tool` decides this is an OLD JMS, gives up on parsing regions out of
the material names, and synthesises one. The donor gets no such comment: Bungie's models
came through the FBX/SIDECAR pipeline, where regions are a face collection -- the sample
sidecar in `data\objects\test` carries exactly that, a `regions` FaceCollection whose one
entry is `default`.

Both end up with one region called `default`, so it is not yet proven that legacy parsing
is the FAULT -- but it is the only difference `tool` itself flags, and it is the only
thing left that distinguishes how the two models were built.

### What the material syntax is NOT

`(default default) saw_body`, by analogy with the marker format that tool does document
(`marker '%s' has bad format - must be '(permutation region) name'`), is WRONG for
materials: the shader then fails to resolve entirely, the material comes out `invalid`,
and the legacy comment stays. Tried and reverted.

The other strings around it are the map to the real syntax, and they say a MAX material
name yields a `region_name` and a `permutation_name`, that a material name may contain a
material TYPE which can override one found in the shader name, and that the punctuation
set in play is `%#?!@*$^-&=.;)><|~({}[`. Reading those out properly is the next move,
and the alternative is to stop fighting the JMS path and use the sidecar importer the
donor was built with.

---

## THE LEGACY-REGION LEAD IS A RED HERRING

`no region/permutation found in material names` is what `tool` says about ANY JMS-built
model, including Halo 3's SAW, whose world model works. So it is a property of the JMS
path, not a fault -- and switching to the FBX/sidecar importer is therefore not
guaranteed to fix anything. Correcting the earlier recommendation.

Three material-name syntaxes were tried and all fail. `(default default) saw_body`, by
analogy with the marker format tool documents, and `saw_body default` both stop the
shader resolving; `default saw_body` and `default default saw_body` keep it resolving
(tool takes the LAST token as the shader) but the legacy comment stays. Whatever a
"multi-part material" is, it is not space- or paren-separated region and permutation.

## EVERY FIELD OF THE RENDER MODEL MATCHES THE DONOR

The bisect proved the fault is inside the port's render model. Every field that
`export-tag-to-xml` can show has now been compared against the Assault Rifle's and
agrees: regions and permutations and their names, every field of the permutation block,
node names, node order, node list checksum, marker groups and marker count, mesh count,
vertex type, rigid node index, index buffer type and index, vertex buffer index, PRT
vertex type, lighting policy, runtime flags, compression bounds, and the presence and
absence of every block in the tag. The counts that differ follow from having 2 materials
where the donor has 10.

So the difference is in the DATA, not the shape of the tag, and the XML cannot show it.

### The experiment that splits THAT in half

`tool export-render-model-mesh <render-model> <out>` writes the donor's own geometry as a
binary DirectX `.x` (2 MB for the Assault Rifle, plus its textures as DDS). Converting
that into a JMS and rendering it AS THE PORT'S MODEL separates the two remaining
suspects in one build:

    the donor's geometry, through our JMS pipeline, still does not draw in the world
      -> the JMS PIPELINE is the fault, and the FBX/sidecar importer is the answer

    it draws
      -> the pipeline is fine and OUR H4 GEOMETRY DATA is the fault -- tangents, normals
         or the skinning -- and the fix is in the converter, not the importer

That is worth doing before writing an FBX exporter, because it says whether the FBX
exporter is needed at all. The `.x` is binary (`xof 0303bin`), so it needs a reader; that
is a contained job against a documented format, unlike authoring binary FBX plus Bungie's
per-node property JSON, which is what the sidecar route actually requires.

---

## THE CONTROL FAILED, AND THAT FOUND IT: `<none>` IS TWO MATERIAL FLAGS IN REACH

The donor's OWN geometry, exported with `tool export-render-model-mesh` and wrapped on the
port's skeleton by `reach_donor_mesh.py`, drew nothing in the world either. So the fault
was never our H4 data: it was in how a JMS becomes a render model.

Comparing three render models side by side -- stock, a sidecar import of the kit's FBX
sample, and the JMS control -- one error appeared on BOTH JMS-built models and on
NEITHER of the others: `*unexpected material flags`, with tool's own explanation
`material 'none' is not a portal, but has flags that only make sense on portals`.

A JMS material is two lines. The shared converter writes the Halo 1/2 convention: the
shader name, then `<none>` for "no texture path". **Reach reads the second line as the MAX
material name**, and `<` and `>` are both in its flag character set
(`%#?!@*$^-&=.;)><|~({}[`, sitting next to portal, weatherpoly, seamsealer, soft_kill,
slip_surface). So every material came out named `none` and carrying two spurious
STRUCTURE flags.

`saw_to_jms_h3.py` now writes the shader name on both lines for Reach
(`MATERIAL_SECOND_LINE`), which is tool's benign legacy mode. Halo 1 keeps `<none>` --
correct there -- and Halo 3 and ODST are unchanged. The port's render model now carries
one error, a tangent warning of the same class as the stock model's; the flag errors AND
the legacy-region comment are gone.

### The sidecar route, measured on the way

`tool import <sidecar>` works in this kit: the shipped FBX sample imported in 15 s and
built a render model. It reads the GRANNY intermediate (.gr2), not the FBX directly. It is
not usable as a control as shipped, because its skeleton and markers content objects
point at .max/.gr2 files that do not ship, so the importer invents a skeleton from the
mesh objects and writes no markers. Re-running it overwrote the kit's own
`test_fbx_assault_rifle.render_model` with that degraded version; it is a test asset no
map references, and HREK.7z holds the original.

---

## WHERE THE REACH WORLD MODEL STANDS

The material-flag fix removed every error tool reports on a JMS-built model except a
tangent warning the stock model shares -- and the dropped / ally-held SAW still draws
nothing. That was the last difference the XML could show. The JMS path itself produces
something the world path rejects, and nothing visible says what.

### The sidecar route needs a Granny file, and the kit cannot make one

Measured: with the sample's `.gr2` removed, `tool import` reports "asset does not contain
any render geometry" and writes nothing. It does NOT convert FBX itself; the FBX is only
the artist's source, and the `.gr2` came from Bungie's Max/Maya exporter plugin, which
does not ship. `bin\tools\bonobo` is Foundation's plugin system, not an exporter.

What DOES ship is `granny2_x64.dll` with its full writer API (GrannyBeginMesh,
GrannyBeginSkeleton, GrannyBeginFileDataTreeWriting, ...), so a `.gr2` can in principle be
authored through ctypes. The importer also reads Bungie's per-node extended properties
(`bungie_face_region`, `bungie_object_type`, ...) -- the `.json` beside the sample mirrors
them -- so the file has to carry those too.

Three ways forward, recorded so the choice is not re-derived:

* author the `.gr2` ourselves against the kit's Granny DLL -- fully in the toolkit,
  largest and least certain;
* use the community Blender exporter that already writes Reach sidecar `.gr2` through that
  same DLL -- proven route, but an outside install and a manual export step;
* a hybrid inside the tag: keep the donor's Bungie-built render model and swap only its
  geometry for ours -- small if the cache builder rebuilds from the per-mesh raw blocks,
  and unproven that it does.

---

## REACH STEP 1, THE PROPER WAY: Foundry and the sidecar importer

The JMS path was ruled out by a control: the Assault Rifle's own geometry, pushed through
`tool render` from a JMS, draws nothing in the world either. Bungie's assets came through
FBX -> Granny `.gr2` -> sidecar -> `tool import`, and `tool` cannot make a `.gr2` itself --
with the sample's removed it finds no geometry at all. Foundry is the community exporter
that writes one.

### The install, on F:, with nothing on C:

    F:\Tools\blender-5.2.2-windows-x64\            portable Blender 5.2.2 LTS, 913 MB
        portable\                                settings live HERE, not in %APPDATA%
        portable\extensions\user_default\io_scene_foundry    Foundry 1.9.19
    F:\Tools\downloads\                           the two zips, both SHA-256 verified

Foundry needs Blender 5.2 or newer. It found HREK by itself. **Its `allow_tool_patches`
ships ON, which lets it modify HREK's tool.exe; it is switched OFF here**, and the export
refuses to run if it finds it back on.

### The pipeline

    blender --background --python reach_foundry_saw.py -- --build --export

Foundry imports the Assault Rifle's own MODEL TAG natively, which gives a scaffold it
built itself: the armature with the five b_ bones in the donor's order, a mesh object
carrying the region/permutation properties, all 20 markers, the scene set up as a model
asset. The script keeps all of that and swaps ONLY the mesh data for the SAW's, read from
the JMS `saw_to_jms_h3.py` already builds, then moves the four markers the SAW carries
elsewhere. The scale is Blender metres, 3.048 x world units, so a JMS coordinate goes in
x 0.03048.

(Foundry's own JMS import hands off to a second community add-on that is not installed.
Going through the donor's TAG avoids it, and gives a scaffold Foundry set up itself.)

The result: nodes `b_gun, b_switch, b_safety, b_magazine, b_ophandle` NATIVELY, in the
donor's order -- no strip, no sort, no rename trick -- region `default`, 16 marker groups,
and a single cosmetic `degenerate triangle` error from zero-area triangles already in the
source mesh.

### Foundry rewrites the MODEL tag -- and must not

Its export regenerates `saw.model` from what the scene holds, so it DROPS the collision,
physics and world-animation references the port borrows from the Assault Rifle and points
the imposter at a SAW imposter that does not exist. A dropped weapon on that model has no
physics body. It also writes an unreferenced `saw.scenery`. The script keeps `saw.model`
aside and puts it back after every export, and removes the scenery. What we take from
Foundry is the render model only.

The `.blend`, sidecar and `.gr2` files live in the kit beside the port's data:
`data\objects\weapons\rifle\saw\saw.blend`, `saw.sidecar.xml`, `export\models\*.gr2`.
Pre-Foundry tags are backed up at `E:\HaloBackups\reach_saw_prefoundry_20260930_0721`.

---

## CONFIRMED IN GAME, 2026-09-30: the Foundry render model fixes the world model

First person still works, and the SAW now draws when dropped AND in an ally's hands. So
the JMS importer really was the cause, and **for Reach, `tool render` from a JMS is dead as
a route for any weapon that can be dropped or carried** -- which is every weapon.

What that retires, kept in the repo only as the record of how it was found:

* `reach_node_names.py` and the `b_<key>_` sort key in `saw_to_jms_h3.py` -- workarounds
  for the JMS importer stripping `b_` and sorting nodes. Foundry emits the donor's names in
  the donor's order natively.
* `MATERIAL_SECOND_LINE` -- the `<none>` flag fix. Real, but not the cause.
* `reach_saw_bisect.py` and `reach_donor_mesh.py` -- the two controls. The bisect proved
  the fault was inside the render model; the donor-mesh control proved it was the JMS
  PIPELINE rather than our data. Both are reusable the next time a port model misbehaves.

`saw_to_jms_h3.py` still matters: it is how the H4 geometry gets out of Halo 4, and
`reach_foundry_saw.py` reads its JMS. Only the `tool render` step is replaced.

### Reach port status

**COMPLETE -- every step confirmed in game (2026-09-30).**

    1 geometry        DONE   through Foundry; first person, dropped and ally-held.
                             Markers: subtract the parent bone's length (see step 9 notes)
    2 textures        DONE
    3 own tags        DONE
    4 numbers         DONE
    5 catalog         DONE   45 rows, 3 ammo choices, fp_animations saw\fp_saw_* with
                             reload x1.0 (Reach AR = H4 AR = 68 frames, so built = balanced)
    6 ammo pickup     DONE
    7 HUD             DONE   own icon (text widget -> saw string), own 72-tick meter, low 18
    8 icon + text     DONE   glyph 0xE052 inside the font's native range, 7 lines x 12
    9 animations      DONE   reach_foundry_fp_retime.py: reload 128, ready 24, events scaled

**Still open for Reach, as scaling work rather than SAW work:**
  * ~~Glyph capacity~~ SOLVED 2026-09-30: packages grow (h3_font_repack.py, confirmed in
    game); see THE BLOCK INDEX.
  * **The Foundry scripts are SAW-specific** (paths, moved markers, frame targets). They
    are generalised with the NEXT port, which needs its own marker placement anyway.
  * **Starting profiles** never gave a Reach weapon; a non-issue, weapons are SPAWNED now.

---

## REACH STEP 7, THE REST: the HUD icon is TEXT, and the meter gets its own sheet

### The weapon icon

Reach's chud does not draw the weapon schematic from a bitmap. The `shematic` and
`shematic_backpack` widgets are TEXT widgets in the full-screen HUD message font, with
input string `assault_rifle` -- which is a line in `hud_messages`,
`assault_rifle = "&assault_rifle"`, expanded by tool to the Assault Rifle's glyph. So
`h3_port_messages.py` adds `saw = "<U+E052>"` (the same glyph the pickup prompt already
draws), to all twelve languages since it carries no words, and `h3_saw_chud.py` renames
both input strings to `saw`. The HUD and the backpack icon are then the SAW's.

### The ammo meter

The `meter` bitmap widget reads the raw `weapon ammo loaded` and draws
`ui\chud\bitmaps\ballistic_meters_2_rows`: ONE 320x48 a8r8g8b8 image plus a 160x24
mip, no sequences, Halo 3's encoding exactly -- blue is the per-tick threshold counting
down column by column (40/39, 38/37, ...), red 48 and green 2 on every tick, alpha the
shape. It is a 40-round meter: the Spike Rifle uses it whole, the Assault Rifle crops it
with manual texture coordinates 0,34,24,160. The shipped TGA exporter fails on it
(`rasterizer\invalid`); the pixels are RAW in the tag's 76,800-byte `tgda`, level 0
then the mip.

`reach_meter_art.py` writes a NEW tag, `saw_ballistic_meter`, cloned from the sheet so
format and mip chain are the shipped ones, and redraws its pixels in place: 72 ticks as
24 columns of 3, thresholds 72 -> 1 in the same column order, the shipped tick shape
scaled to the smaller cell. It points ONLY the SAW's meter widget at it and sets its
texture coordinates to 0,0,0,0 like the Spike Rifle's. The shared sheet and every other
chud are untouched.

---

## REACH STEP 9: the animations are COMPRESSED, and Foundry decodes them

Why `h3_anim_decode` over-read: Halo 3 stores first-person frames RAW in the uncompressed
block (16-byte quaternions), which is what made retiming arithmetic. Reach does not.
Across all 23 members of the SAW's graph `default_data` is 0, the bulk is in the
COMPRESSED block, and the uncompressed block is a flat 12 bytes per frame (108/9, 60/5,
1200/100) -- probably root motion. So every Halo 3 invariant fails and the decoder was
reading the wrong block. Retiming needs Reach's codec decoded.

**Foundry already decodes it**, through the kit's own ManagedBlam. Importing the Spartan
first-person arms (`objects\characters\spartans\fp\fp.render_model`) and then the graph
onto that armature (`reach_foundry_fp_probe.py`) loads 25 actions -- reload_full 0..60,
reload_empty 0..69, ready 0..21, put_away 0..6. So step 9 is a keyframe-scaling job in
Blender plus a sidecar export, like step 1, and needs no codec work.

What does NOT work, and why: importing the graph with no armature in the scene imports
nothing ("No armature found"); importing the WEAPON tag crashes in Foundry's material
node layout (`arrange`), which appears to need a live UI.

**DONE -- `reach_foundry_fp_retime.py`** (run inside the F: Blender, once per species,
`-- spartans --write` / `-- elite --write`). It imports the arms, adds the five weapon
b_ bones read from the graph's own skeleton (b_gun under r_hand), imports the graph onto
that rig, scales keys + handles about frame_start (reload_full/empty 128, ready 24), and
exports ALL animations -- the export rebuilds the graph from the scene, so exporting
one leaves a graph of one.

Three traps, all measured:
  * Foundry names the asset after the .blend's FOLDER: two species saved side by side in
    `saw\fp` both came out as `saw\fp\fp`. Each species gets its own folder,
    `saw\fp_saw_<sp>\fp_saw_<sp>`, and the weapon's jmad refs are repointed there.
  * Exported into NOTHING, the graph comes out with 0 sound references and its events in
    a separate frame_event_list. So the new path is SEEDED with the original graph first;
    the export then merges and keeps sounds/effects inline.
  * ...but the merge ALSO keeps the seed's inline event FRAMES: reload_full was 128 frames
    with its primary keyframe still at 34. `fix_events()` (also `--events` alone) sets
    them through Foundry's ManagedBlam AnimationTag, computed from the ORIGINAL graph so
    reruns cannot compound. Result, both species: reload_full 34/52/fx40 -> 74/113/87,
    reload_empty 34/62/fx30,48 -> 64/117/56,90. Sound events sit at 0 and stay there.
The originals stay in `saw\fp\` (plus `.before_retime` copies of them and of saw.weapon).

---

## Halo 4 as the TARGET -- the H4 port kit (started 2026-09-30)

Every earlier port carried the Halo 4 SAW OUT of Halo 4. This kit ports INTO it. First
weapon: **Reach's Focus Rifle**, chosen as an easy one. The master list of what each game
lacks is the user's spreadsheet (`Halo Weapons Spreadsheet (CE - Infinite).ods`, Sheet2).

### What H4EK is, measured

* **Import is sidecar/Granny only**: `tool import <sidecar>` -- no JMS verb at all. So the
  Foundry route the Reach SAW proved is not a workaround here, it is THE route.
* **No legacy shaders**: H4EK has no .shader tags and no shader.render_method_definition.
  Surfaces are `.material` tags on material shaders (`shaders\material_shaders\...`).
* **Leftovers are not a weapon**: H4EK carries `rifle\focus_rifle` -- but only feedback and
  impact effects, no weapon, model or graph. The same goes for other Reach-era folders
  (needle_rifle, plasma_repeater, plasma_rifle, spike_rifle). Check before assuming.
* **Weapons have no chud** (see halo4 scoping): the HUD is a `cusc` screen referenced from
  weap 0x4E0. First-person graphs live at
  `objects\characters\storm_fp\weapons\<cat>\fp_<name>\storm_fp_<name>`.
* **Residency is designer zones**: a port must be in the map's `dz_enhancer`, ticked in
  every zone set (Foundation), and an EK rebuild must be copied into
  `E:\HaloBaselines\halo4\maps` or the next enhancer patch discards it.

### The donors (first pass)

    geometry            the Focus Rifle's own, from HREK, through Foundry
    materials           the Beam Rifle's (Covenant, same family), bitmaps repointed
    behaviour + fx      storm_sentinel_beam -- a continuous plasma beam with heat, like the
                        Focus Rifle; H4EK ships its weapon, projectiles and fx, and only its
                        MODELS are null (why it can never be a pickup today)
    fp animation, HUD   the Beam Rifle (fp_beam_rifle, its cusc screen and scope). Reach's
                        own fp graph is built on Reach's arm skeleton and does not carry over

### Status

    1 geometry        DONE   h4_foundry_port.py --import (HREK) / --export (H4EK): render,
                             collision, physics, model; 14 nodes; 0 errors
    2 materials       DONE   h4_port_materials.py: metal/shell/rubber on the port's own
                             diffuse + normal + a control map built from Reach's diffuse
                             alpha; the glowing surfaces borrow the Beam Rifle's scope
                             material as a first pass. All 8 resolve in the render model.
    3 own tags        DONE   h4_make_port_weapon.py, v2 on the SENTINEL BEAM (first boot
                             of the Beam-Rifle-based tag: model fine, the weapon DID NOT
                             FIRE -- a single-shot sniper barrel fed a continuous beam).
                             Barrels -> the port's own beam copy; model, fp model, fp
                             graph and HUD set BY FIELD NAME through ManagedBlam
                             (h4_weapon_refs.py). The Sentinel Beam's tag actually names
                             the Focus Rifle's Reach paths -- in Halo 4 it IS the Focus
                             Rifle's weapon tag, missing its model.
    4 numbers         DONE   balance_port.py via the SNIPER RIFLE (user: a sniper that is a
                             laser); h4_tag_numbers.py bakes them by name, read back. The
                             copied friendly beam dealt ZERO damage: now 3.
    5 catalog         DONE   make_port_catalog_h4.py: 36 rows; heat + battery carried as the
                             port's own (the sniper has neither); Beam Damage MEASURED x1.0
                             (sniper round 80 in both); Shots Per Fire dropped (Reach 0 =
                             H4 minimum 1)
    6 ammo pickup     n/a    energy weapon
    7 HUD             BORROWED  the PLASMA PISTOL's cui_screen (battery % + heat); the
                             Beam Rifle's showed 10 shots for a 620-round battery. Scope UI
                             by the enhancer's graft at patch time
    8 icon + text     -      pickup message is still the Beam Rifle's (be_pickup); H4 font
                             packages are NOT 0xC000-blocked: a reader is needed
    9 animations      BORROWED  fp_beam_rifle, shared -- so no retime (it would retime
                             the Beam Rifle)

**First test: m30_cryptum** (user's choice). Add the Focus Rifle to m30's `dz_enhancer`,
tick that zone in the zone sets where it is tested (m30 has it in only 4 of 24), place it,
rebuild, install -- and copy the build to `E:\HaloBaselines\halo4\maps` or the next
enhancer patch rebuilds from the old one.

### Run order (every rebuild of the port)

    blender --background --python h4_foundry_port.py -- --import    (HREK)
    python h4_port_materials.py --write
    blender --background --python h4_foundry_port.py -- --export    (H4EK)
    python h4_reach_scope_art.py --write         scope bitmaps (once; boot 21)
    python h4_muzzle_recolor.py --write          own orange muzzle effect (boot 21)
    python h4_make_port_weapon.py --write        re-copies the donor weapon every time
                                                 (and the HUD: icon + Reach scope)
    blender --background --python h4_tag_numbers.py -- --write      so this comes LAST

**Second boot (2026-09-30):** ground model good, heat/overheat and battery WORK on the
Sentinel base; first-person model invisible but casting a SHADOW; no beam seen. Measured
against the Beam Rifle's render model: the port's parts carried part flag 16 "Draw Cull
Distance Medium" -- Reach's per-face "Draw Distance Mid", kept through Foundry. Halo 4
applies it to the first-person weapon; the Beam Rifle's body has none. --export now
resets it (all part flags 0). The beam's firing effect hangs off the fp model's markers,
so "no beam" may be the same cull -- the next boot separates that from a projectile fault.

**Third boot (2026-10-01):** unchanged -- fp invisible, no beam -- but DAMAGE LANDS, so the
projectile is fine and only drawing fails. The cull flag was not it. Diffing the .model
against the Beam Rifle's: Foundry wrote **zero variants** where every Bungie weapon has
one (`default` -> region `default` -> permutation `default`). The ground object draws its
render model directly; the first-person weapon and the effects on its markers go through
the variant. --export now adds it (add_default_variant, ManagedBlam).

**Fourth boot:** still invisible, still no beam -- the variant was not it either (kept: it
matches every Bungie weapon). Diffing the WEAPON tags flag by flag (ManagedBlam flags by
name) against the Beam Rifle's: the Sentinel Beam carries object flag **"extension of
parent"** -- its gun was part of the Sentinel's body. Held by the player, it draws as part
of the player, whose body first person never draws: invisible, shadow cast, beam effects
on its markers hidden, damage landing. h4_make_port_weapon.py clears it (h4_weapon_refs.py
`clear-flag:`). Lesson for every donor that was an NPC's built-in gun: diff the FLAGS.

**Fifth boot:** unchanged. A FULL field diff of the two weapon tags (not just flags) shows
more NPC-gun leftovers, now set to the Beam Rifle's by h4_make_port_weapon.py (`set:`):
object bounding radius 0 / offset 0 (Beam Rifle 0.3 / 0.215 -- the gun used its parent's
bounds), weapon ready 1st person animation playback scale 0 (1), weapon name `bb` and
class `pistol` (the fp graph is the Beam Rifle's `csr`, a rifle). If the sixth boot is
still invisible, the next test swaps the BEAM RIFLE's render model in as the fp model:
model fault vs weapon-tag fault in one boot.

**Boots 6-7 WITHOUT rebuilds** (h4_map_poke.py writes the built map in place): the
leftovers changed nothing; then the SWAP TEST -- the Beam Rifle's render model as the fp
model on the port's weapon -- DREW. So the weapon tag was fine and the model was not.
Ruled out at the desk, no boot: render-model geometry flags (the build sets 39 on both).

**THE TWO REAL CAUSES, found by data:**
  * **First person: the skeleton must map into the fp graph.** The port is animated by the
    DONOR's fp graph. All 14 of the Beam Rifle's render-model nodes are in fp_beam_rifle;
    of the Focus Rifle's 14 only b_gun is -- and Halo 4 does not draw a first-person model
    whose nodes do not map. --export now collapses the armature to b_gun (vertices to
    b_gun, markers re-parented at their world positions). Recipe rule: **a port borrowing
    an fp graph must use only node names that graph contains.**
  * **The beam: first person draws no third-person effect.** The right trigger fires
    barrel 0, the Sentinel's "enemy" barrel, whose firing effect bsh_firing has ONLY a 3p
    tracer -- an NPC gun is never seen from inside. Its damage landed, nothing showed.
    Repointed to the friendly firing effect (1p + 3p tracers).
Both need the eighth boot after a real rebuild.

**Boot 8 (rebuild): the FIRST-PERSON MODEL DRAWS** -- the skeleton was it. The beam still
did not. **Boot 9, poked (--beam-test): the port firing the Beam Rifle's projectile DREW
a beam.** So the weapon and model can show one, and the Sentinel's first-person tracer is
what never draws. Why: Halo 4 draws a player's beam from the PROJECTILE -- the Beam
Rifle's firing effect is a sound and a light, and its projectile carries the beam as an
object ATTACHMENT (fx\projectile). The Sentinel draws its beam as a 1p tracer in the
firing effect, a path no player ever exercised. h4_make_port_weapon.py now gives the
port's own projectile that attachment (h4_weapon_refs.py `add-attachment`). Recipe rule:
**a donor's visuals must be the kind the PLAYER path draws.**

**Boots 10-11:** the beam DRAWS (thin, end-on: it leaves the camera). Muzzle start: the
gun-origin barrel flag fires from the gun's WORLD position, which first person draws
elsewhere -- no visible help; not kept. "Draw in first person pass" on the Sentinel's
point-to-point tracer: no change. **The look:** H4 has NO beam_system tags; Bungie
converted the Focus Rifle's beam into the Sentinel's tracers -- a "cross" (two ribbons,
double-sided) where the Beam Rifle's streak is one thin "aligned ribbon". The port now
owns a copy of that tracer with point-to-point CLEARED, riding the projectile inside its
own copy of the Beam Rifle's projectile effect (fx\beam, fx\beam_projectile).

**The overheat jerk** (user's slow-motion video: the whole fp view shifts right ~2 frames
at the end of overheating). h4_fp_jump.py measured the Beam Rifle's graph, hands + gun
against the camera: overheating->o_h_exit 0.0010 (authored to join), but overheating->
overheated 0.0353 and overheated->o_h_exit 0.0350 -- the `overheated` hold is DISPLACED,
all base animations (not an overlay artifact), and no o_h_exit frame matches it (closest
0.031), so trimming frames could not fix it. h4_fp_graph.py writes the port's OWN graph
(storm_fp\weapons\rifle\fp_focus_rifle) with `overheated` as a still hold of
overheating's last frame (both hand-offs <=0.001), keeping the SHIPPED frame_event_list
(Foundry's round trip lost events: 25,224 vs 32,491 bytes). The Beam Rifle never
overheats in normal play, so nobody saw this.

**TRAP: Foundry's graph IMPORT rewrites the source graph's frame_event_list** -- it
changed the Beam Rifle's shipped one (32,491 -> 30,376 bytes). Restored from H4EK.7z
(bin\x64\7zr.exe e H4EK.7z <path>); h4_fp_jump.build_rig now keeps it byte for byte.
H4EK.7z is the clean source for ANY shipped H4 tag.

**Boot 12, both WRONG:** the unpinned Sentinel tracer drew NOTHING (its length runs along
the point-to-point profile; without two points it has none) -- back to the Beam Rifle's
streak. And the jerk STAYED with the `overheated` hold made still, followed by a FREEZE
(that still hold): so the jerk is BEFORE the hold, inside `overheating`. **The jolt:**
--detail overheating -> frame 44 kicks 0.0205 (~10x its neighbours), 45-49 drift back;
frames 27-37 are a deliberate fine shake. h4_fp_graph.py now smooths ONLY frames 44-46
(a line from 43 to 47; worst spike 0.0144 -> 0.0035) and leaves every other frame,
`overheated` included, as Bungie made it. Verified on the exported graph itself.
Method note: an animation glitch the user sees as "a jerk" can be a mismatched
HAND-OFF or a SPIKE inside one animation -- measure both, and use the user's ordering
(jerk-then-freeze) to tell which.

**User correction (boot 13): the jerk is "within the overheated animation when the heat
is vented".** `overheated` is internally clean (loop seam 0.0009) and `vent_*` too; the
jerk is the 0.035 hand-off overheated -> o_h_exit, which starts while heat still drains.
The still-hold of boot 12 froze the motion; the fix SHIFTS `overheated` as a whole (every
channel + overheating's last minus overheated's first), keeping its motion: joins
0.0000 / 0.0009, verified on the exported graph. The frame-44 jolt smoothing stays (a real
spike). Lesson: ask WHEN in the game state a glitch happens before choosing which seam.

**Boot 14: jerk still felt.** Not the overheat camera shake either (weap 0x330 nulled,
`--no-overheat-shake`: unchanged). The user's second video, frame-differenced: ONE frame
(56 of 124, ~52% heat) with BOTH hands and the rifle shifted -- not in the animation data
(the frame-44 jolt was right hand only; every hand-off <=0.001; b_camera_control never
moves). Diagnostic poke `--graph-pp`: the Plasma Pistol's fp graph, whose overheat chain is
used in normal play (it has b_gun, so the port's model still draws).

**The beam look, solved on paper:** the Sentinel's 3p tracer IS the Focus Rifle's beam
(center on energy_trail + two plasma layers: plasma_trail_a/b noise through a palette --
Reach's own textures, all present in H4 under fx\reach). Unpinning failed because its
LENGTH functions run on "profile position"; the Beam Rifle streak's run on "profile age".
h4_beam_look.py: own copy of the Sentinel tracer, the streak's length/offset/lifespan/
self-acceleration functions copied in field by field, palette -> Reach's
focus_rifle_plasma, point-to-point cleared; in an own copy of the streak's effect, attached
to the port's projectile. Z-510 (storm_anti_infantry_turret) = the same "bsh" point-to-point
mechanism, not usable for a player weapon.

**Boot 15 (rebuild):** the Plasma Pistol graph has NO pop -> the Beam Rifle chain. Its VENT
set (vent_enter/loop/exit, absent from the Plasma Pistol's; vent_enter steps 0.058) is now
LEFT OUT of the port graph (37 animations). The overheat shake (frames 27-37, +-0.005
alternating -- the Beam Rifle's, not the Focus Rifle's) damped by a 5-frame moving average:
0.0096 -> 0.0018. The beam: drew, "2-dimensional" and too long-lived -> n-gon tube, 6
sides (Reach's own 1p beam was an n-gon), profile lifespan 0.35..1.0 -> 0.175..0.5 s
(function data floats at +4/+8). Spawn point: each barrel's FIRST PERSON OFFSET (+x
forward, +y left, +z up) -- first-person only, unlike the gun-origin flag; starting guess
0.13,-0.05,-0.05, tuned without rebuilds via `h4_map_poke.py --fp-offset x,y,z`.

**Boot 16:** the pop SURVIVED dropping the vent set; the Plasma Pistol's overheat set also
lacks `o_h_exit` (overheated goes straight back to idle), so that is left out too. The
overheat damping is reverted (the user meant the shake WHILE FIRING). Offset tuned in game:
**0.03,-0.08,0.00**. Firing shake + muzzle flash tested by poke first: the per-shot
"Firing Damage" (barrel firing effect +0x54: camera shake + rumble + simulated input --
Reach's Focus Rifle had all three too) nulled, and the Suppressor's muzzle-flash-only
effect (storm_forerunner_smgxr_smg_firing_muzzle_flash, no shot sound) in each
barrel's "Optional Secondary Firing Effect" (+0x44).

**Boot 17:** pop still there. Dropping o_h_exit was a MISTAKE -- the Plasma Pistol HAS one
(an earlier name filter on heat/vent/overh missed it); restored. A full name diff of the
port graph against the Plasma Pistol's leaves three OVERLAYS only the Beam Rifle has:
flaps (1 frame), barrel_spin (21), accelration_screens (9), blended by weapon functions --
and the port's weapon exports `heat` as blend_weight / blend_weight_barrel. Heat crossing
a threshold mid-vent on a one-frame overlay = a one-frame pop at ~half heat. All three are
left out (34 animations). Lesson: compare graphs by the FULL name set, never a filtered one.

**THE POP, SOLVED (boot 19) -- by in-map bisection, no rebuilds** (h4_map_poke.py
--action-anim / --anim-flags / --loop-frame on the compiled graph, layout =
halo3_reload.LAYOUTS['Halo 4']). Steps: o_h_exit -> overheated: pop stays; overheated ->
idle: pop stays, but now visibly "right before the idle" = the END of `overheating`; the
"Disable Weapon Aim/1st Person" flag (0x18 vs the Plasma Pistol's 0x08): not it.
**Cause: `overheating`'s LOOP FRAME INDEX was 0** -- at its end the engine wraps to the
loop frame for ONE frame before the next state, and frame 0 is the pre-overheat pose.
The Plasma Pistol's is 16. Set to the last frame (58): pop gone. h4_fp_graph.py sets it
after export (set_loop_frames). The earlier removals (vent set, overlays) are harmless to
the Focus Rifle and kept; o_h_exit and Bungie's motion are intact.
**Method lesson:** when two graphs differ in behaviour, diff their COMPILED per-animation
fields (loop frame, playback flags, frame counts) in the built map -- not only names and
poses -- and bisect by poking one field per boot.

**Firing feedback + muzzle (kit):** per-shot response = the Assault Rifle's
(storm_assault_rifle_firing; the Sentinel's was too strong at 30/s, the Storm Rifle's too
weak); muzzle flash = the Storm Rifle's firing effect in the optional secondary slot
(needs primary_trigger + fx_vent, both on the model) until the Focus Rifle's own Reach
muzzle particles are ported.

### Step 7 / 8 in Halo 4: the HUD scope, the pickup lines, the pictogram (2026-10-02)

* **Scope:** the port's OWN copy of the Plasma Pistol's cui_screen (in a built map a screen
  is one shared tag -- grafting the shared one would scope the real Plasma Pistol), then
  AFTER EACH BUILD `h4_map_poke.py --scope`: the enhancer's in-game-proven
  `_apply_h4_scope` with the Beam Rifle's screen as donor.
* **Lines:** they live in `ui\strings\ingame` (not a hud_messages list), five ids like
  Halo 3's; the Sentinel base carried the Beam Rifle's `be_*`. `h4_port_messages.py`
  clones them as `fr_*` ("Focus Rifle"), English in every language (Halo 4's prompts NAME
  the weapon, so a translated line cannot be cloned safely); `tool strings` imports
  English, `strings-localized` reported 0 for the others (fallback). Only ingame.txt may
  sit in data\ui\strings when importing (the verb takes every .txt).
* **Pictogram:** Halo 4's icon packages are the Halo 3 container with **0x10000 blocks**
  (h3_font_repack rebuilds all four byte for byte with BLOCK = 0x10000); a glyph record
  has a **12-byte header** (u16 advance, size, width, height, 0, 12*res) over Halo 3's
  codec (408/408 decode exactly); x2-x4 are exact multiples; pickup pictograms are font 2
  (icon\fixedsys-hud). `h4_mesh_dump.py` + `h4_weapon_glyph.py` draw the port's side
  silhouette and add it at U+E1F6 (no Focus Rifle macro exists); the lines carry the
  literal character. Packages are loose: no rebuild for the glyph, one for the lines.

**Boot 20:** pickup prompt IN. Player-HUD icon NOT: the screen's `weapon_icon_text`
names a string id from `ui\strings\weapons` (`plasma_pistol_icon = "&plasma_pistol"` on the
copied screen) -> `focus_rifle_icon` (the port's glyph) added there and the screen
repointed (h4_hud_icon.py, run by h4_make_port_weapon.py after every screen copy).
Muzzle: the re-enabled Reach particles drew NOTHING (Bungie disabled them for a reason) --
back to the Storm Rifle's flash. Scope: the graft is the H4 BEAM RIFLE's (vector polyart,
19 assets); Reach's Focus Rifle scope is BITMAPS (scopes\beam_rifle_scope + meters +
overheat border) -- recreating it means a new H4 scope template on imported Reach bitmaps.

**Boot 21 -> the port's OWN Reach scope and an orange muzzle (kit, needs a rebuild):**

* **Reticle drift = the Beam Rifle scope's PARALLAX** (user: "always moves to the right
  ... returns to the centre when I don't move"). That template parks its art in four
  parallax containers driven by parallax listener -> expression `0+(a*10)` ->
  container prop_left/prop_top bindings. The port's own template has none of them.
  (`h4_map_poke.py --fp-offset 0,0,0` was poked into the boot-21 map as a control test:
  if the drift went with the old scope, the 0.03,-0.08,0 offset is innocent and stays.)
* **Reach's scope, read from its chud definition** (HREK ui\chud\focus_rifle):
  scope mask (a8, double sized, origin -1,-1, scale 1.2, mirrored both ways = the
  lower-right QUADRANT of a 2:1 mask, black at the bitmap's alpha); heat meter right
  (+435), battery meter left (-435), scale 1.19; meter frames (triple sized, origin 6.8,
  mirrored); reticle hud_reticles sequence 22. Units: 1152x640 chud, centred; double
  sized = 2 px a unit; ORIGIN is in half-extents of the bitmap. The meter bitmaps are
  horizontal arcs but stand upright in the frames: a quarter turn.
* **h4_reach_scope_art.py**: exports the Reach bitmaps (HREK `tool export-bitmap-tga`
  works off its "save directly" fallback), bakes mask + frames + reticle into ONE
  1920x1080 picture for the 1280x720 HUD, and turns the meters into Halo 4 meter bitmaps.
  **Halo 4's hud_meter reads R = A = shape, G = B = fill threshold (255 top -> 0 bottom)**,
  measured on the Beam Rifle's heat_bar/ammo_bar; Reach keeps the shape in A. Bitmap tags
  start as copies of the Beam Rifle's (import settings kept by `tool bitmaps`).
* **h4_reach_scope.py** (run by h4_make_port_weapon.py after each HUD copy): template =
  the Beam Rifle's minus every parallax binding, polyart hidden (prop_visible 0), its
  three bitmap widgets repointed (frame full screen, meters in the frames); then wires it
  into the port's HUD the way the Beam Rifle's HUD carries its own: a `template
  instantiations` row, one HUD component per template component (ti = that row) under an
  own transformation container in scope_container, zoom_decision/zoom_on_off + their two
  bindings + the "> 0" long comparison, the three sniper_zoom animations, and meter
  bindings weapon_data_reader.prop_charge -> ammo_animator, prop_heat -> shader_heat_bar.
  The HUD's own reticle fades out while zoomed (the Reach reticle is in the art).
  **`component indices` is SORTED BY STRING ID NUMBER** (ManagedBlam GetRawData of the
  name) and rebuilt. Cross-tag copies go field by field -- ManagedBlam's
  CopyElement/PasteAppendElement use the Windows clipboard and failed once in a kit run.
  The in-map graft (`--scope`) is no longer needed; it refuses an already-scoped HUD.
* **Muzzle colour:** REACH'S FOCUS RIFLE MUZZLE IS ORANGE (its effect's particle tints,
  read through HREK's ManagedBlam: (255,98,42) -> (255,92,0), sparks (255,200,72) ->
  (238,83,31); the firing light stays blue-violet). `h4_muzzle_recolor.py` copies the
  Storm Rifle flash and its 10 parts to focus_rifle\fx\muzzle, drops the Storm Rifle's
  fire SOUND part, moves every colour to Reach's orange (colour functions: byte 2 = colour
  count, a two-colour function's colours in u32 slots 0 and 3 -- Reach uses the same
  layout) and gives the six palette bitmaps own recoloured copies.

**Boot 22 (rebuild):** muzzle flash GOOD. Control test before it: barrel offset 0,0,0 in
the old map still drifted ("when looking around") -> the offset is innocent, the drift was
the Beam Rifle scope's parallax. Three faults, all mine:
* **No zoom, wrong heat:** h4_make_port_weapon.py re-copies the Sentinel Beam, and
  h4_tag_numbers.py (magnification levels 0 -> 2, heat values) was not run after it.
  h4_make_port_weapon.py now runs it as its LAST step.
* **Scope drawn all the time (side bars + a second reticle):** in a HUD, a TEMPLATE
  INSTANCE row's `type` is the template component's NAME (Bungie's Beam Rifle HUD,
  compiled: type sid == name sid on every ti=1 row), not its widget class. Written as
  the class, the rows were never tied to the zoom-faded container.
* **No dark lens mask:** prop_alpha_blend_mode 1 is ADDITIVE (the Beam Rifle's glowing
  polyart); its dark vignette leaves it UNSET.

**Boots 23-24:** zoom back, unzoomed fine; the user keeps the HUD's OWN reticle zoomed too
(Reach reticle out of the art, no fade -- the heat readout under it shows when zoomed).
* **Black block:** an EXPLICIT prop_alpha_blend_mode 0 drew the whole frame opaque.
  Bungie leaves the property UNSET on 1707 of 1727 HUD widgets sampled; unset != 0.
* **THE RETICLE DRIFT, found by a field diff of the weapon against the Beam Rifle and
  Plasma Pistol:** the Sentinel Beam (an ENEMY gun) carries aim assist modes with a 20 deg
  autoaim cone and a **20 deg DEVIATION ANGLE** -- how far Halo 4 lets the aim, and the
  reticle with it, leave the screen centre (Beam Rifle 0.4, Plasma Pistol 4). Not the
  scope's parallax (gone, drift unchanged), not the barrel offset (zeroed, unchanged).
  Both modes -> the Beam Rifle's; top-level deviation 0; zoomed aim speed 0.5 -> 1.
  LESSON: a weapon based on an AI gun inherits AI aim assist -- diff ALL of it.
* **Side meters stayed empty** with heat and battery (weapon_data_reader.prop_battery --
  prop_charge is the Plasma Pistol's OVERCHARGE) bound. Unsettled: an a8r8g8b8 bitmap tag
  holds the imported source AND the processed pixels, and `tool bitmaps` stores a TIFF
  pixel as bytes R,G,B,A while the game/decoder read B,G,R,A. Hidden (prop_visible 0) by
  the user's call; Reach's frames stay.

**Boot 25:** zoomed view visible. Three findings:
* **Scope art short of the screen edges:** Halo 4's HUD area is inset; Bungie's own dark
  vignette in the Beam Rifle scope is drawn 15% larger (scale 1.15 at -96,-54). The Reach
  art is now scaled 1.15 on a canvas 1.5x the HUD area, padded with the mask's dark edge
  (frame widget -320,-180 1920x1080).
* **Drift left (slight unzoomed, more with zoom):** without the weapon flag **strict
  deviation angle** Halo 4 raises the deviation to the AUTOAIM angle (plugin tooltip) --
  2 deg unzoomed, 1 in the modes; the Beam Rifle sets it. Set.
* **Gun still drawn when zoomed** (the pistol hides it): flag **hide FP weapon when in
  iron sights** ("for scoped weapons"), set like the Beam Rifle. h4_weapon_refs.py now
  takes '/name' for a TOP-LEVEL field ('/flags' = the weapon's own; a bare 'flags' finds
  item/object/flags first).
* Projectile origin when zoomed: the tag has ONE first-person offset per barrel, nothing
  per zoom level -- the beam starts at camera + offset in both states.

### CHECKLIST for a port that OVERHEATS (battery / heat weapons only)

The overheat pop is a **heat-weapon problem only**: it lives in a borrowed fp graph's
OVERHEAT chain (overheating -> overheated -> o_h_exit), which plays only on a weapon with
heat. Ballistic ports (the SAW in every game) never enter it. For any battery/heat port
that borrows a donor's fp graph -- above all a donor that does NOT overheat in normal
play (the Beam Rifle), whose overheat animations nobody ever saw:

1. Read each overheat-chain animation's **Loop Frame Index** in the compiled graph
   (`h4_map_poke.py` reads/pokes it: jmad Animations element +0x8). A NON-looping entry
   animation (overheating) with loop frame 0 shows its FIRST frame for one frame when it
   ends: a whole-rig pop. Set it to the last frame (h4_fp_graph.set_loop_frames).
2. Compare against a donor whose overheat chain IS used in play (the Plasma Pistol: loop
   frame 16, no pop) -- every compiled per-animation field, not just names and poses.
3. Bisect in the built map, one field per boot, before any rebuild.
4. Per-shot feedback at a heat weapon's fire rate (30/s for the Focus Rifle) multiplies:
   pick a firing damage response built for automatic fire (the Assault Rifle's here).

### Foundry across kits: the traps

* **The Microsoft Store Python virtualises %APPDATA%** for itself and every child. A
  Blender launched from it reads a DIFFERENT copy of Foundry's project list -- one without
  H4EK -- so ManagedBlam silently binds HREK, parses H4 tags with Reach's definitions
  (Reach paths as 'before' values, `hud screen reference` not found) and fails with "not
  rooted under the current directory". h4_weapon_refs.py / h4_tag_numbers.py register
  H4EK in whatever list their process sees, bind through an ABSOLUTE H4EK path, and
  refuse unless ManagedBlam is H4EK's.
* **Integer fields refuse "2.0"** and silently keep their value: whole numbers go in as
  integers.

* **One kit per Blender PROCESS.** Foundry binds one kit's ManagedBlam and needs a restart
  to switch, so import runs in the source kit and export in H4EK -- two processes.
  `foundry_setup.py -- --add <kit>` registers a kit (Foundry's own operator needs a UI).
* **Background mode divides by zero** laying out material node trees (UI scale 0). The
  scripts replace `arrange` with a no-op at runtime; Foundry's files are untouched.
* **`nwo.shader_to_material` cannot help**: it copies the Reach shaders into
  `tags\_temp` and fails to load the first one (H4EK cannot read them). The copies must be
  deleted afterwards -- they were.

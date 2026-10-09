# Explosion visual size following radius cards (investigation, 2026-10-09)

Problem: a radius card multiplies a damage effect's `Radius` / `Radius Max` (jpt!), but
the explosion's particles stay the same size, so after a few picks the visible blast and
the damage area no longer match. Investigation only: **no card or patcher change made.**

**Status 2026-10-09 (part 2): feasible in all six games on map data.** Halo 2 to Halo 4 proven offline end to end (write a copy, re-read, every other effect byte-identical); the step left per game is one in-game look (section 6). Implementation waits until the weapon port is done (user).

## 1. Cards that scale an explosion / area radius today

All write `Radius` + `Radius Max` on jpt! tags (one input, `group: "Radius"`) unless noted.

| Card | Games | Halo 1 jpt! |
|---|---|---|
| Needler > Explosion Radius | all | `weapons\needler\explosion` |
| Rocket Launcher > Radius | all | `weapons\rocket launcher\explosion` |
| Flak Cannon > Radius (H1 = Fuel Rod) | H1-H4 | `weapons\fuel rod gun\grunt explosion` |
| Frag Grenade > Radius | all | `weapons\frag grenade\explosion` |
| Plasma Grenade > Radius | all | `weapons\plasma grenade\explosion` |
| Sentinel > Explosion Radius | H1-H4 | `characters\sentinel\explosion & shock wave` |
| Flood Infection > Pop Radius | H1-H3 | `characters\flood_infection\body destroyed & nopop` |
| Flood Carrier > Pop Radius | H1-H3 | `characters\floodcarrier\bdoy destroyed` |
| Hunter > Hunter Radius, Flood Combat / Infection > Melee Radius | | melee: nothing drawn, out of scope |
| Brute Shot, Gravity Hammer (+ Tartarus, Chieftain), Spartan Laser Impact, Missile Pod, Claymore, Firebomb Burn, Power Drain (x2), Trip Mine, Sentinel Enforcer Rocket, Grunt Radius | H2-H3 / H3 / Reach | none |
| Concussion Rifle, Grenade Launcher, Needle Rifle, Plasma Launcher, Target Locator Explosion | Reach (+H4) | none |
| Scattershot, Railgun, Sticky Detonator, Incineration Cannon, Pulse Grenade, Watcher | H4 | none |
| Melee Radius (Elite, Brute, Bugger, Knight, Crawler, Human) | H2+ | none (no visual) |

Other radius fields, not explosions: Target Locator `Launch Radius` (airs), Drop Shield
healing `Radius`, Camo/Jammer `Noise/Flash Radius`, Thruster `Danger Radius`, AI
`Collateral Damage Radius`, Pure Form `Distance Damage` radii, Engineer `Shield Boost
Radius`, Knight Commander `Retreat Radius`. Only Drop Shield has a visual (the bubble).

## 2. Halo 1: what draws the explosion's size

Detonation effect (effe) per card, from the HEK tags (`F:\...\HCEEK\tags`), and who else
uses each visual tag (shipped tags only; digsite/port tags left out):

| jpt! | effect | particle_system (pctl) | light (ligh) | effect particles |
|---|---|---|---|---|
| needler explosion | `weapons\needler\effects\explosion` | own (1 user) | own | plasma electric bolts |
| rocket explosion | `weapons\rocket launcher\effects\rocket explosion` | **`frag grenade\effects\explosion med` (frag + rocket)** | **`frag grenade\explosion` (frag, rocket, 2 steam explosions, a10 lifepod, wraith burning)** | lens flare, gravel, drifting smoke |
| frag explosion | `weapons\frag grenade\effects\explosion` | **same `explosion med`** | **same light** + own `grenade quickflash` | drifting smoke |
| plasma grenade | `weapons\plasma grenade\effects\explosion` | own (1 user) | shared with energy sword detonation | none |
| fuel rod grunt explosion | `weapons\fuel rod gun\effects\grunt explosion` | **`hunter fuel rod explosion` (+ fuel rod explosion, Banshee x2)** | none | lens flare |
| sentinel explosion / shock wave | `characters\sentinel\effects\death` | none | none | flash, smoke (+ garbage bits) |
| floodcarrier pop | `characters\floodcarrier\effects\body destroyed` | own (+ engineer copy, not in campaign) | none | blood, skin burst, flare |
| infection pop | `characters\flood_infection\body destroyed` | none | none | none |

Decals (`grenade char`: 35 effects, `plasma burn large`: 30) are shared everywhere; leave
them unscaled.

Size fields (Assembly `Halo1` plugins; `Halo1MCC` effe is identical):
- **effe** `Events/Particles`: `Radius`, `Radius Max`, `Distribution Radius`(+`Max`).
  These live IN THE EFFECT (per effect), so they are safe to scale even when the particle
  tag is shared.
- **pctl** `Particle Types`: `Radius` (float); `Particle Types/Particle States`: `Scale`,
  `Scale Max` (rangef). SHARED tags.
- **ligh** root `Radius` (illumination falloff). Shared tags.

This is exactly the set the Brute Shot port scales (h1_pickable_weapons
`scaled_particle_system` / `own_explosion` `scale`, x0.55, confirmed in game), minus the
light.

**Patcher can write all of them at patch time.** halo_patch's generic writer takes any
class with a plugin, `block` paths (`Events/Particles`, `Particle Types/Particle States`),
`index: "all"` through nested blocks (`follow_all`), and a per-target `tag` override.
Verified read-only on a30, b30 and d40 with the patcher's own HaloMap + PluginRegistry:
`explosion med` Radius 1.5, Scale 0.01..0.03; frag effect particle Radius 2.0; frag light
Radius 10; needler pctl Radius 1.5; plasma grenade Scale 0.015; hunter fuel rod Radius 1.5.

**Shared-tag trap** (memory halo-shared-block-double-apply): frag and rocket share
`explosion med` AND the light. Rows for both on one shared tag compound (x1.2 x x1.2), and
one card would also resize the other weapon. The fuel rod's pctl is also the Banshee's.

## 3. Live editing

No live tag writer exists for Halo 1 (the live tools patch dll code or read objects).
It would take locating the map's tag data in the running MCC (tag index scan in
halo1.dll's heap) and writing the same offsets; new particles would pick it up. **Not
needed:** the radius cards themselves only apply at patch time, so visuals written in
the same patch stay in step with them.

## 4. Recommended mechanism (for the user to approve)

**Visual targets inside the radius card's own `group: "Radius"`**, gated `games:
["Halo 1"]`, each with a `tag` override. A group is one input and every member gets the
same op, so the visuals follow the radius multiplier exactly (stacking included) with
**no patcher code**. Example, Frag Grenade:

```json
{ "step": "*1.2", "field": "Radius",              "block": "Particles", "index": "all", "tag": {"Halo 1": "effe weapons\\frag grenade\\effects\\explosion"}, "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" },
{ "step": "*1.2", "field": "Radius Max",          "block": "Particles", "index": "all", "tag": {"Halo 1": "effe weapons\\frag grenade\\effects\\explosion"}, "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" },
{ "step": "*1.2", "field": "Distribution Radius Max", "block": "Particles", "index": "all", "tag": {"Halo 1": "effe weapons\\frag grenade\\effects\\explosion"}, "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" },
{ "step": "*1.2", "field": "Radius",    "block": "Particle Types",  "index": "all", "tag": {"Halo 1": "pctl <frag's OWN copy of explosion med>"}, "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" },
{ "step": "*1.2", "field": "Scale",     "block": "Particle States", "index": "all", "tag": "...same", "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" },
{ "step": "*1.2", "field": "Scale Max", "block": "Particle States", "index": "all", "tag": "...same", "group": "Radius", "games": ["Halo 1"], "easier_when": "increased" }
```

Shared tags need a one-time split in the Halo 1 rebuild (a ten-map rebuild, the user's
go), the same thing the Brute Shot port did for itself:
- rocket explosion -> own copy of `explosion med` (+ own copy of the frag light, if lights
  are scaled);
- fuel rod `grunt explosion` -> own copy of `hunter fuel rod explosion`.

Per weapon, what it touches:
- **No split needed:** Needler (effect particles + own pctl + own light), Plasma Grenade
  (own pctl; its light is shared with the sword -> skip the light), Sentinel (effect
  particles only), Flood Carrier (effect particles + own pctl), Infection (nothing drawn).
- **Split first:** Frag + Rocket (`explosion med`, light), Fuel Rod (pctl).
- Until a split lands, those three can still get the effect-local particle rows alone
  (smoke/flare/gravel follow; the main fireball does not).

Open points for the enhancer session / user:
- Validator check 6 wants a direction key per target; visual rows carry the card's.
- Confirm `_group_targets` + per-target `tag` on another class renders and applies as one
  row (the code reads that way; Firing Noise already uses `tag` across classes).
- Lights: include only on own copies; low visual value, optional.
- One test boot: a30, Frag Radius at x2, compare the fireball to the damage reach.

## 5. Halo 2 / 3 / ODST / Reach / 4 (full investigation, 2026-10-09 part 2)

Tools (all in sprint_toolkit):
- `explosion_fx_audit.py` -- card -> jpt! -> every referencing tag -> effects, over EVERY
  campaign map of each game (tagRef index: gen 3+ `[group][..][..][ident]`, owner = nearest
  tag base below; Halo 2 `[group][datum]`, exact tag sizes). Writes reports/explosion_fx_audit.*
  (the gen-3 owner guess sometimes names a bitmap/pixel-shader tag -- ignore those owners).
- `reports/explosion_fx_rule.txt` -- the per-card effect lists under the implementation rule
  (5d). Committed; the full audit json is regenerable (~25 min).
- `fx_visual_scale.py` -- the PROTOTYPE writer + verifier (not wired into the patcher).
- `fx_visual_test.py` / `fx_visual_test.cmd` -- the in-game test maps (section 6).

### 5a. What draws the size

Every game from Halo 2 on keeps particle systems INSIDE the effect (effe `Events/Particle
Systems/Emitters`). The two properties that set an explosion's size are **Particle Size
(world units)** and **Emission Radius (world units)**. Each is a *function property*: input /
range variable bytes + a dataRef to function data (+ on Halo 3/ODST/Reach/4 an inline
`Runtime m Constant Value` and flags). Layouts are read from the Assembly plugins.

Function data (all five games, colour functions aside): byte 0 = type, byte 1 = flags,
**floats at +4 and +8 = the output range**, the curve after them normalised. Scaling both
scales the output for every type -- Halo 3's GPU bake stores exactly those two numbers beside
the curve coefficients, which is the proof.

Halo 3 ONLY also bakes each emitter for the GPU (`Runtime GPU Properties` 0x2CC, 16 B rows;
`Runtime GPU Functions` 0x2D8, 64 B rows). Decoded over all 7076 size/scale entries of
040_voi with **0 mismatches**:
- GPU property row 1 = alpha, **row 2 = Particle Size**, row 6 = Particle Scale, row 7 = rotation;
- a constant property sits in col 0 of its row; a function property has col 0 = 0 and
  col 2 = function index << 17;
- a baked function row is `[type, ?, min, max, flags, coefficients...]` (a ranged function
  bakes two rows).
Emitter-level properties (emission radius, counts, velocity) are not baked -- CPU side.
ODST, Reach and Halo 4 MCC caches carry **no** baked GPU blocks (emitter tails probed).

Halo 4 additionally has an inline per-effect `Global Size Scale` (root 0x18) and a per
particle system `Size Scale`. (The 2026-09-28 equipment-icon test that "showed no change"
at x8 GSS is no evidence either way: Halo 4 never drew that icon at all.)

### 5b. The trap: everything is DEDUPLICATED

The caches share identical data between tags. Measured per map:

| game | function datarefs | distinct blobs | shared emitter / GPU blocks |
|---|---|---|---|
| Halo 2 (05b) | 14058 | 1874 | 149 emitter blocks |
| Halo 3 (040) | 63684 | 5750 | 1774 (emitter + GPU) |
| ODST (sc120) | 63306 | 5599 | 0 |
| Reach (m30) | 26370 | 3639 | 0 |
| Halo 4 (m10) | 90398 | 6190 | 0 |

An in-place edit of a function blob would resize every other effect in the map that shares
those bytes. So the writer is **copy on write**: each touched blob / GPU block gets a private
scaled copy and its dataRef / reflexive is repointed; an emitter block shared with an effect
outside the scaled set is copied first. New bytes go where the patcher already grows data:
gen 3+ through `halo_patch._h3_reserve` (zero runs; the rule confirmed in game on Reach m10 and
Halo 4 m70), Halo 2 appended at the end of the image like `Halo2Map.grow_blocks` (confirmed in
game). The patcher rebuilds every map from its pristine baseline, so copies never compound.

Space, ALL radius cards at once on one map: Halo 2 ~6 KB, ODST ~7 KB, Reach ~7 KB, Halo 4
~6 KB, Halo 3 ~89 KB (GPU blocks) against 172 KB of >=4 KB zero runs on 040_voi (largest 48
KB). A real run drafts a few radius cards, so the Halo 3 margin is comfortable, but the
implementation must fail soft (skip the visual, keep the damage) when slack runs out.

### 5c. Offline proof (fx_visual_scale.py, frag grenade x2 on a copy)

| game / map | emitters | copies | other property values byte-identical | scaled values exact |
|---|---|---|---|---|
| Halo 2 05b | 6 | 12 blobs | 14004 | 12 / 12 |
| Halo 3 040 | 17 | 4 emitter blocks, 13 blobs, 12 GPU blocks | 70400 | 36 / 36 |
| ODST sc120 | 18 | 13 blobs | 62982 | 36 / 36 |
| Reach m30 | 10 | 9 blobs | 26190 | 20 / 20 |
| Halo 4 m10 | 10 | 9 blobs (or 2 GSS floats) | 91481 | 20 / 20 |

Halo 3 after the write: the GPU bake is still consistent with the functions on all 7076
entries. The same checks pass on the five test levels (section 6).

### 5d. Which effects belong to a card (the implementation rule)

The projectile's OWN detonation fields (`Airborne Detonation Effect`, `Ground Detonation
Effect`, `Super Detonation`, `Detonation Started`) plus any effect that carries the jpt! as
a part. **Not** the projectile's material responses: from Reach on these name the GENERIC
per-surface `fx\material_effects\weapons\impact_explosion_medium\*` (and Halo 3's Spartan
Laser card reaches ~60 generic `impact_plasma_large\*` effects) that every explosive weapon
shares. The grenade's own detonation effects carry the fireball (5-8 particle systems);
the material effects are surface debris that stays at stock size.

Under that rule (reports/explosion_fx_rule.txt), cards with a drawn explosion:

| game | cards | own effects only | shared with another weapon (resizing leaks to it) |
|---|---|---|---|
| Halo 2 | 7 | 6 | Flak Cannon <- Banshee bomb |
| Halo 3 | 11 | 7 | Rocket <- Pelican rocket; Flak <- Banshee bomb; Plasma Grenade <- Flood "banger"; Missile Pod <- Hornet missile |
| ODST | 13 | 9 | Rocket, Flak, Missile Pod as Halo 3; the Hunter card reaches the flak detonation |
| Reach | 11 | 6 | Needler <-> Needle Rifle (one effect, TWO cards); Flak <- Hunter fuel rod, Banshee, Seraph, Shade; Frag <- AA / frigate turret rounds; Concussion <- Phantom chin gun |
| Halo 4 | 11 | 7 | Rocket <- missile battery; Frag <- Bishop turret round; Plasma <- pulse popup / active shield / Bishop; Concussion <- Phantom chin gun |

A shared effect cannot be split at cache level (that would mean adding tags), so per shared
card the choice is the user's: let the other weapon's blast grow too (cosmetic only -- its
damage is untouched), or leave that card's visual unscaled. Two cards on one effect (Reach
Needler / Needle Rifle) must not compound: take the larger multiplier, or one card owns it.
Melee-radius cards (no particle explosion) and the Gravity Hammer (Halo 3 fires its visual
from animation events, not a projectile) are out of scope.

## 6. In-game test (one boot per game, when the user chooses)

    fx_visual_test.cmd deploy h3      (h2 / h3 / odst / reach / h4)
    fx_visual_test.cmd restore h3

Builds `<level>_fxscale_test.map` from the CURRENT live map (a patched run stays patched;
deploy again after any re-patch) and swaps it in; the live map waits as
`<level>.map.pre_fxscale`. The frag grenade's own explosion is drawn **x3**; nothing else
changes (damage included). Halo 4 also draws the **plasma grenade x3 via Global Size Scale**,
so one boot compares both Halo 4 routes. Levels: Halo 2 03a_oldmombasa, Halo 3 010_jungle,
ODST sc100, Reach m10, Halo 4 m10_crash (frags early; Halo 2 01b avoided by rule). All five
builds were dry-run and verified on these levels, then removed.

What each outcome means:
- three times wider -> the route works in that engine;
- stock size -> the engine ignores what was written (Halo 3: the GPU rows or the function
  copies; Halo 4 plasma: GSS -- the frag's emitter route still stands);
- crash / no explosion -> a repointed copy is unreachable; the copy placement needs revisiting.
Halo 1 needs no new mechanism (plain fields, section 2); its test belongs with the shared-tag
split in the Halo 1 rebuild, after the port.

## 7. Implementation outline (after the port, with the enhancer session)

1. Per card and game, the list of effects to scale, generated from the audit under rule 5d
   and reviewed for the shared cases; the multiplier is the card's own Radius multiplier
   (the group's input), so visuals follow picks exactly.
2. Halo 1: plain rows (sections 2 + 4) after the shared-tag split.
3. Halo 2-4: a new emit pass in halo_patch calling the fx_visual_scale writer (copy on write,
   fail soft when there's no slack, Halo 3 GPU rows); Halo 4 through Global Size Scale if the
   test shows it works (one float per effect, no copies).
4. Two cards on one effect: the larger multiplier, not the product.

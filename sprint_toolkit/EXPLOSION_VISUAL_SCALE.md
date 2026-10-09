# Explosion visual size following radius cards (investigation, 2026-10-09)

Problem: a radius card multiplies a damage effect's `Radius` / `Radius Max` (jpt!), but
the explosion's particles stay the same size, so after a few picks the visible blast and
the damage area no longer match. Investigation only: **no card or patcher change made.**

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

## Later games

- **Halo 2 / Halo 3 / ODST / Reach:** particle systems live inline in the effe
  (`Particle Systems/Emitters`); `Particle Size`, `Particle Scale` and `Emission Radius`
  are function PROPERTIES (input/range variable + a `Function` dataref blob), and H3+
  also bake `Runtime GPU Properties/Functions` blocks that the GPU particles read. A plain
  field write does not reach them: it needs a function-blob scaler (constant / ranged
  function types) and a check that the GPU runtime blocks follow (or rewriting them too).
  Research item. Effect sharing between weapons must be audited per game as here.
- **Halo 4:** easiest of all: effe root `Global Size Scale` (0x18) and per particle
  system `Size Scale` ("multiplied by all size related fields"). One plain float per
  effect, the generic writer can do it with the same group mechanism. Needs a per-effect
  sharing audit and an in-game check that Global Size Scale isn't overridden at runtime.

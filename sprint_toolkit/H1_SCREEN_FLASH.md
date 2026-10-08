# Halo 1: the screen flash when the player is hit (investigation, 2026-10-08)

No tag or map edits made. Values read from the HCEEK source tags with
`h1_screen_flash_scan.py` (the live maps are built from these; no enhancer card writes a
flash field today -- `halo.json` has no Screen Flash / Maximum Intensity row).

## Where the flash lives

**Only in `damage_effect` (jpt!).** Every jpt! has one screen-flash struct; nothing else
in Halo 1 carries a player-damage flash:

| place checked | result |
|---|---|
| `globals\globals` (matg) | no flash field. Its damage refs are jpt! tags (`globals\falling`, `distance`, `vehicle_collision`, `vehicle_hit_environment`, `vehicle_killed_unit`, `flaming_death`) -- each with its own flash, listed below |
| `characters\cyborg\cyborg` coll, body | localized damage effect `characters\cyborg\localized damage`, area `effects\blood aoe human` -- both effe with a blood DECAL only, no jpt! part. Damaged/depleted/destroyed effects empty |
| cyborg coll, shield | damaged effect empty, depleted `characters\cyborg\cyborg shield depletion` (no parts), recharging empty |
| cyborg biped / unit | only `melee damage` (a jpt!: `characters\cyborg\melee`, the flash the player's VICTIM would see) |

**So there is no shielded / unshielded split in Halo 1.** One jpt! = one flash, whatever
the player's shield state. (Halo 3 splits it -- the ports took H3's *shielded* duration.)
That this also holds at RUNTIME (the engine doesn't e.g. suppress or scale it by shield
state) is not proven offline -- see test T1.

Layout (Halo1MCC plugin `jpt!.xml`): `Type` enum16 +0x24 (none, lighten, darken, max,
min, invert, tint), `Priority` enum16 +0x26 (low/medium/high), **`Duration`** float +0x34
(first of five `Duration`s in jpt! -> card `nth: 0`), `Fade Function` enum16 +0x38,
`Maximum Intensity` float +0x44, `Color` colorf ARGB +0x4C.

The plugin's blend formulas (C = colour, A = alpha, DST = framebuffer):
LIGHTEN `DST(1-A) + C`, DARKEN `DST(1-A) - C`, MAX `MAX[DST(1-C), (C-A)(1-DST)]`, ...
So **alpha washes the scene out, colour is added**: AR bullet (A 0, red) only adds red;
pistol (A 1, white) replaces the frame with white at the peak.

## The table (what the player sees per enemy weapon)

ARGB = Color. I = Maximum Intensity. Shield state: same row both ways (see above).

| source (who uses it) | jpt! tag | type | prio | dur | fade | I | ARGB | look |
|---|---|---|---|---|---|---|---|---|
| Grunt/Jackal/Elite plasma pistol | `weapons\plasma pistol\bolt` | lighten | med | 2.0 | very_late | 0.5 | .15 / 0 .94 .57 | long teal-green wash |
| Elite plasma rifle (also Marines) | `weapons\plasma rifle\bolt` | lighten | med | 2.0 | very_late | 0.6 | .15 / 0 .82 .92 | long cyan wash |
| plasma rifle charged bolt | `weapons\plasma rifle\charged bolt` | lighten | high | 3.0 | late | 0.5 | .15 / .13 1 .66 | 3 s green |
| Grunt/Elite needler | `weapons\needler\needle` | **max** | med | 0.1 | early | 0.6 | 1 / .97 .04 .80 | short pink |
| needle impact / detonation | `weapons\needler\impact damage`, `detonation damage` | max | med | 0.1 | early | 0 | same | short pink |
| needle supercombine | `weapons\needler\explosion` | lighten | high | 1.0 | linear | 0.7 | 0 / 1 0 1 | magenta |
| Spec-ops Grunt fuel rod, Hunter (`hunter fuel rod`) | `weapons\fuel rod gun\explosion` / `grunt explosion` | lighten | high | **0.0** | linear | 0.5 | 1 / 0 .99 .04 | **no flash (duration 0)** |
| Elite sword | `weapons\energy sword\melee` | lighten | high | 3.0 | late | 0.5 | .15 / .13 1 .66 | 3 s green |
| Elite melee | `characters\elite\elite melee` | lighten | high | 1.0 | linear | **0** | 0 / 1 .09 .11 | red |
| Hunter melee | `characters\hunter\melee` | lighten | high | 2.0 | linear | 0 | 0 / 1 .09 .11 | red, 2 s |
| Flood combat melee | `characters\floodcombat elite\melee`, `floodcombat_human\melee` | lighten | high | 0.7 | linear | 0 | red | red |
| Infection form melee | `characters\flood_infection\melee` | none | | | | | | none |
| Carrier / infection burst | `characters\floodcarrier\bdoy destroyed`, `flood_infection\body destroyed` | lighten | high/low | 0.9 / 0.3 | linear | 0 | 0 / .6 .6 0 | olive |
| Sentinel beam | `characters\sentinel\beam` | max | med | 0.1 | early | 0 | 1 / .97 .04 .80 | short pink |
| Sentinel death explosion | `characters\sentinel\explosion` | lighten | high | 1.0 | linear | 0.7 | 0 / 1 1 0 | yellow |
| Shade turret | `vehicles\c gun turret\bolt` | **tint** | med | 0.2 | linear | 0.6 | 0 / .18 1 .98 | cyan tint |
| Ghost / Banshee bolt | `vehicles\ghost\ghost bolt`, `vehicles\banshee\banshee bolt` | lighten | med | 2.0 | very_late | 0.6 | as plasma rifle | |
| Banshee fuel rod | `vehicles\banshee\fuel rod explosion` | lighten | high | 0.0 | linear | 0.5 | green | no flash |
| Wraith mortar | `vehicles\wraith\explosion` | lighten | high | 3.0 | late | 0.5 | .15 / .13 1 .66 | 3 s green |
| Flood/Marine AR, SMG port, SAW port | `weapons\assault rifle\bullet`, `smg\bullet`, `saw\bullet` | lighten | med | 0.1 | early | 0.2 | 0 / 1 0 0 | red blip |
| Flood/crew pistol | `weapons\pistol\bullet` | lighten | med | 0.4 | late | 0.8 | **1 / 1 1 1** | strong white |
| Flood/Marine shotgun | `weapons\shotgun\pellet` | lighten | low | 0.2 | late | 0.2 | .5 / 1 0 0 | red, washed |
| Sniper | `weapons\sniper rifle\sniper bullet` | lighten | low | 0.2 | late | 0.2 | .7 / 1 0 0 | red, washed |
| Rocket | `weapons\rocket launcher\explosion` | lighten | low | 0.0 | linear | 0.7 | 1 / 1 1 0 | no flash |
| Flamethrower | `weapons\flamethrower\impact damage` / `burning` / `explosion` | lighten | low | 0.1 / 0.3 / 0.1 | | 0.2 / 0.1 / 0.2 | orange | orange |
| Frag / plasma grenade | `weapons\frag grenade\explosion` / `plasma grenade\explosion` / `attached` | lighten | high | 1.0 / 1.0 / 2.0 | linear | 0.7 | 0 / 1 1 0 (frag), green (plasma) | |
| Warthog chaingun | `vehicles\warthog\bullet` | lighten | low | 0.2 | late | 0.8 | .7 / 1 1 1 | white |
| Scorpion MG / shell | `vehicles\scorpion\bullet` / `shell explosion` | lighten | med/high | 0.1 / 1.0 | | 0.2 / 0.7 | red / yellow | |
| weapon melee (all player weapons) | `weapons\*\melee` | lighten | med | 1.0 | linear | 0.2 | 0 / 1 .09 .11 | red |
| falling / vehicle hit / flaming death | `globals\falling`, `vehicle_collision`, `flaming_death` | lighten | low | 0.1 | early | 0 | .5 / 1 0 0 | red |
| **ports**: BR | `weapons\battle rifle\bullet` | lighten | med | **0.5** | **linear** | 0.8 | 1 / 1 1 1 | white (magnum colour, H3 timing) |
| **ports**: Carbine | `weapons\covenant carbine\slug` | lighten | med | 0.5 | linear | 0.8 | 1 / 1 1 1 | white |
| **ports**: Plasma Lancer | `weapons\plasma lancer\bolt` / `charged bolt` | as plasma rifle | | | | | | |
| **ports**: Sentinel Beam | `weapons\sentinel beam\beam` | lighten | med | 2.0 | very_late | 0.6 | as plasma rifle | |
| **ports**: Fuel Rod (Flak) | `weapons\plasma_cannon\impact damage` | lighten | low | 0.1 | early | 0.2 | .5 / 0 1 0 | green |

(Full list incl. digsite/levels: `h1_screen_flash_scan.py --all`; the ~100 trigger /
melee_response / shock-wave tags are type none.)

**Observations, not yet rules:**
- The "big" flashes are plasma (2-3 s very_late/late) and the pistol family (white, A 1).
  The BR and Carbine ports inherited the **pistol's colour/intensity** from their magnum
  template and only took duration/fade from Halo 3 -- so a Carbine hit reads as a white
  pistol flash, not a Covenant one.
- **Duration 0** on the fuel rod, rocket and Banshee fuel rod explosions: presumably no flash
  at all (unverified).
- **Maximum Intensity 0** on all character melees, Sentinel beam, needle impact, globals:
  c20 documents the field's default as 1, so 0 probably means "unset = full", not "off"
  (would explain why an Elite punch flashes red). Unverified -- T2.
- How the engine turns a hit into an intensity is not in the tags: whether it scales with
  damage dealt, with distance falloff of area damage, or is always Maximum Intensity, needs
  T3 (or disassembly of halo1.dll). Priority presumably decides which flash wins when two
  overlap.

## Runtime switches found

- `halo1.dll` contains the HaloScript globals **`rasterizer_screen_flashes`** ("toggles
  the display of screen flashes, such as those from a damage_effect or powerup") and
  `cheat_reflexive_damage_effects`. A global all-or-nothing off switch, if MCC honours it
  when set from a compiled level script (`(set rasterizer_screen_flashes false)` via the
  h1 script-tree tools). Note it also kills powerup flashes (camo/overshield pickup).

## Options to change it (none applied)

| # | option | how | what a test must confirm |
|---|---|---|---|
| A | **per weapon, by tag** | `halo.json` card rows on the jpt!: `Duration` (nth 0), `Maximum Intensity`, `Type` (enum: 0 = none), `Fade Function`. The patcher already writes float32/enum16 by plugin name; `Color` (colorf) is NOT in `halo_map.TYPE_FMT` -- recolouring needs 4 float writes at +0x4C (new support) | one weapon changed, e.g. plasma pistol bolt duration 2.0 -> 0.5: the flash shortens, nothing else does |
| B | **ports only**: decide their identity | BR/Carbine: keep white pistol flash, or Carbine -> plasma family colour, or take H3's UNSHIELDED duration. `ports_h1/<key>.py` `fields`, rebuild | only that port's hits change |
| C | **global scale (Enhancer option)** | Options -> "Screen flash strength" x and/or "duration" x: patch every jpt! with type != none in each H1 map at patch time (sweep like the skull tag sweeps); 0 = Type none. Needs the 0-intensity rule from T2 before scaling (0 x k = 0 would stay "full") | x0.5 visibly halves every flash; x0 removes all; melee rows behave like the others |
| D | **global off, script** | `(set rasterizer_screen_flashes false)` at level start | flashes gone AND whether powerup flashes go too; if MCC ignores it, nothing changes (then fall back to C x0) |
| E | **card (run modifier)** | a Player/Other card "Blinding hits" / "Steady eyes" scaling all enemy-weapon flashes (direction key: harder_when increased) -- built on C's sweep | as C, toggled per run |

## Tests (one boot can cover several)

- **T1 shield state**: take the same weapon (plasma pistol Grunt on a10) with shields
  full, then with shields down. Same flash -> confirms one-flash-per-jpt! at runtime too;
  different -> the engine scales by shield state and a card would need to know.
- **T2 intensity 0**: Elite melee (I 0) vs player-weapon melee from a Marine/Flood (I 0.2).
  Elite punch clearly stronger -> 0 = full (C must treat 0 as 1). Elite punch invisible ->
  0 = off.
- **T3 scaling**: frag grenade at the edge of its radius vs at your feet. Flash weaker at
  the edge -> intensity scales with damage/falloff; equal -> it is always Maximum Intensity.
- **T4 duration 0**: get hit by a fuel rod: no flash confirms duration 0 = none.

Related memory: halo-player-vitality-and-hud (coll = player pool), h1-port-phase0.

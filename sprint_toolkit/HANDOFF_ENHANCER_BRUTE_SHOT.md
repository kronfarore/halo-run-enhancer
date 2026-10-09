# Hand-off to the Halo enhancer session: Brute Shot (Halo 1 port A7), 2026-10-09

The port session could not reach the enhancer session at close-out, so this file carries the
hand-off. Delete it once the enhancer has acted on it.

**State.** Tested in game on 2026-10-09 (9 boots on a30) and confirmed by the user. The
ten-map rebuild is batched with the other wave-A ports and waits for the user's go.

The catalog entry `Brute Shot` (Halo 1) already exists:

| key | value |
|---|---|
| weap | `weapons\brute shot\brute shot` |
| donor | Rocket Launcher |
| balance rows | 15 (the Rocket Launcher ratio) |
| anims | reload x1.07, swap x0.85, with `anim_sounds` |
| hands | `heavy` (set by the enhancer, 4cb2653) |

The firing profile is in `ai_firing_profiles.json`: Halo 3's brute_shot profile over the Flood
rocket carriers, with WDM 0.26 by default and 0.49 balanced (the Armed WDM rule).

## 1. Cards (from the Rocket Launcher's Halo 1 cards)

| part | tag |
|---|---|
| projectile | `weapons\brute shot\grenade` (a rocket copy with NO impact damage) |
| explosion damage | `weapons\brute shot\explosion.damage_effect` |
| explosion effect | `weapons\brute shot\effects\grenade explosion.effect` (fires the explosion damage) |
| melee | `weapons\brute shot\melee.damage_effect` (a blade: slice_melee 90 as the mean) |
| HUD | `weapons\brute shot\brute shot.weapon_hud_interface` (Halo 3 pips, 6 in a row) |

The explosion damage is a copy of the rocket's: lower 26, upper 73/73, radius 0.3..1.1. It
keeps the rocket's material table, except `flood_combat_form` 1.0.

Differences from the rocket that matter for cards:
- No zoom (zoom levels 0), so skip the zoom cards.
- Semi-automatic latch fire, at 3.33/s default and 1.33/s balanced. The rocket fires at 0.5/s.
- Magazine 6, 18 at pickup, 18 at most.
- The grenade flies 16 -> 7 wu/s, with air gravity 0.05 and range 20. It bursts in mid-air at
  maximum range.
- Its detonation minimum velocity is 0 on purpose. In Halo 1 a nonzero minimum velocity
  DETONATES the projectile.

Please check the rocket's explosion and radius cards against the grenade. Map the explosion
damage effect and the melee by hand if name matching misses them.

## 2. New option (user, 2026-10-09)

**Covenant avoid friendly fire.** In the Armed test, two Halo 1 actor flags made Grunts, Jackals
and Elites noticeably more careful with explosives. The user's words: "not perfect, but they
try".

| flag | bit |
|---|---|
| avoid friends line of fire | `0x80000000` |
| crouch when in line of fire | `0x40000000` |

- Only Halo 1's human actors carry these flags (Marines, armored Marines, crewmen). No Covenant
  actor does.
- The flags sit on the ACTOR tag, i.e. per species (for example `characters\jackal\jackal
  minor.actor`, where the flags are its first long). They are not on a variant or a weapon.
- The user's decision: make it an enhancer OPTION, not a per-port change.
- A test-only implementation exists: `h1_port_test_map.actor_flags`. It sets the bits on every
  actor tag of the armed species in the built map.

## 3. Noted for later (user decisions; nothing to do now)

- **A grenade BOUNCE option** for the Brute Shot. Halo 3's grenade detonates on impact, and the
  port keeps that.
- **Explosion visuals that follow the radius cards:** see `EXPLOSION_VISUAL_SCALE.md`. This is
  parked until every weapon is ported to every game. The Brute Shot already has its own
  particle-system copy (`weapons\brute shot\effects\explosion med`, scaled x0.55), so it needs
  no shared-tag split.
- **The explosion screen flash is yellow** (lighten, 1 s, intensity 0.5). The user rejected
  blue because it reads as plasma.

# B4 Grenade Launcher into Halo 2 -- step 4a (yardstick), 2026-11-24

Reach = HREK `rifle\grenade_launcher\grenade_launcher` (h3_weapon_values --kit reach; the projectile, damage and
fuse values as Halo 1's B4 read them from HREK, ports_h1/grenade_launcher.py). Halo 2 = H2EK tags read through
ttk_halo2 (h2_gl_ttk_4a.py; scratch tag dumps). Time to kill: legendary, DIRECT hits = impact +
the full blast (the core), each part through its own Halo 2 damage group, shield first.

## What Halo 2 offers (read before any number)

| Reach mechanic | Halo 2 has | so |
|---|---|---|
| fuse 0.5 s after first bounce off ANY surface | `detonation timer starts`: immediately / after first bounce / when at rest / **after first bounce off any surface** (the Brute Shot uses it, 0.2 s) | Reach's own rule exists natively. Halo 1 lacked it (its fuse ran from rest -> the user's fuse-from-launch 1.2 s) |
| bounce, friction 0.42 | material responses `bounce` + parallel / perpendicular friction (frag 0.5 / 0.7) | Reach's 0.42 / 0.42 |
| rolls at 0-7 wu/s ('turn physical') | responses: impact/detonate, fizzle, overpenetrate, attach, bounce, ricochet/bounce dud. NO turn physical | lost: a slow bounce with friction stands in |
| detonate on units / steep fast hits | per-response flags (only / never against units) + angle and velocity bounds | Reach's rules as responses |
| hold to tether, release to detonate in flight | no tether. The PLASMA PISTOL's ONE trigger: latch-autofire, secondary action `charge` 0.6 s, secondary barrel 1 = the charged shot on release | the charged pair is NATIVE (no second trigger, as Halo 1 needed) |
| EMP 100 `emp` over 0.25 -> 2.5, shields only | matg group **`emp`**: every shield x500, sentinel x500, enforcer x50, metal x1, flesh 0. The PP overcharge = 1 `emp` (500 on a shield). Flag `only hurts shields` exists | Halo 2's own EMP group; with the flag it is shields only, as Reach's |
| EMP stalls vehicles | damage `side effect` enum: none / harmless / lethal to the unsuspecting / **emp**, plus an `emp radius` field. No stock tag uses them (PP overcharge: none, 0) | engine support UNKNOWN: one test (fire at a vehicle) tells; if dead, lost |

Halo 2's own grenade launcher, THE BRUTE SHOT: what it changes about Halo 1's pick. Halo 1 had no grenade
launcher, so the frag was the nearest family. In Halo 2 the Brute Shot is the role twin (explosion_small, latch,
`after first bounce off any surface` fuse, ballistic AI aim) and the DONOR. But it cannot be the ratio yardstick:
Reach has no Brute Shot. It stays a 5b peer -- and it hands back Reach's own fuse rule (above).

## Enemies (Halo 2, legendary) and groups

| | shield | body | explosion_small | collision | emp |
|---|---|---|---|---|---|
| Elite minor | 105 | 45 | shield x0.5, body x1 | x1 / x1 | shield x500 |
| Brute minor | - | 250 | x1 | x1 | 0 |
| Grunt minor | - | 40 | x1 | x1 | 0 |
| Jackal minor | hand shield | 60 | x1 | x1 | hand shield x500 |

Reach's groups by name exist in Halo 2: blast `explosion_small` (= the frag's and the Brute Shot's), impact `collision`.

## Values

| value | Reach (Original) | **Frag + RL holes (provisional, Halo 1's)** | Rocket Launcher | Flak Cannon (Fuel Rod) | H2 peers |
|---|---|---|---|---|---|
| blast | 0..180 over 0.75 -> 2.25 | **56.25..168.75** over 0.833 -> 1.75 (frag 150/160; lower by the sibling rule) | 56.25..150 over 1.0 -> 1.8 (200/240) | 120..270 over 0.75 -> 1.5 (90/60) | BS 25..50, RL 75..200, FR 40..90, frag 50..150 |
| impact | 25 collision | **18.75** (RL 150/200) | 18.75 | 25 (100/100) | BS 20, RL 150, FR 100 |
| fuse | 0.5 s after first bounce off any surface | **0.4 s** (frag 0.5 / 0.625), Reach's rule | Reach's (RL has no fuse) | Reach's | BS 0.2 any surface |
| arming | 0 | 0 | 0 | 0 | frag 1.5 |
| gravity / water | 0.7 / 0.75 | **0.778 / 1.0** (frag 1.0/0.9, 1.0/0.75) | Reach's | Reach's | BS 0.3, frag 1.0 |
| velocity | 12.5 -> 7.5 | **x1** (throw 10 in both) | 12.5 -> 9.4 (RL 20/16) | 12.5 -> 3.3 | BS 20 -> 10 |
| friction | 0.42 / 0.42 | 0.42 (Reach's; no ratio) | 0.42 | 0.42 | frag 0.5 / 0.7 |
| recovery | 0.5 s | **0.5** (RL 0.8/0.8) | 0.5 | 0.5 (0.4/0.4) | BS 0.3, RL 0.8, FR 0.4 |
| magazine | 1 / 8 / 16 | **1 / 8 / 16** (RL x1) | 1 / 8 / 16 | 1 / 8 / 16 | BS 4 / 12 / 16 |
| reload | 63 fr = 2.1 s | **2.72 s** (RL 5.0 / 3.87) | 2.72 | fuel rod ratio | BS 2.0, RL 5.0 |
| range | 100 | 100 (RL 175/175) | 100 | 100 | |
| error | 0.15, 0 -> 0.4 | Reach's (RL 0/0: degenerate) | Reach's | Reach's 0.15, 0 -> 0.4 x? | BS 0.25, 0.6 |
| autoaim / magnetism | 4/15, 8/15 | **4 / 11.25, 8 / 15** (RL 5/45 vs 5/60; 10/25 both) | same | 4/15 x FR | RL 5/45, 10/25 |
| melee | strike_melee | **smash_melee** (RL: Reach strike -> H2 smash) | smash | | BS slice (the blade: NOT kept) |
| shot pace (1-round mag) | 2.6 s | **3.22 s** | 3.22 | | |

Direct hits to kill, legendary (h2_gl_ttk_4a.py):

| | Elite minor | Brute minor | Grunt | Jackal |
|---|---|---|---|---|
| Reach (Original) | 2 (2.6 s) | 2 | 1 | 1 |
| Frag + RL holes | 2 (3.2 s) | 2 | 1 | 1 |
| Rocket Launcher | 2 | 2 | 1 | 1 |
| Flak Cannon | 2 | 2 | 1 | 1 |
| H2 Brute Shot | 3 | 4 | 1 | 1 |
| H2 Rocket | 2 | 1 | 1 | 1 |
| H2 frag (thrown) | 3 | 2 | 1 | 1 |

The candidates kill in the same hits; they differ in splash (Flak 270 is a rocket's blast) and the pace.
Recommended: the PROVISIONAL (Halo 1's pick): same damage family as the frag in both games.

## Hold-to-detonate + EMP (decide with the user)

A. **The plasma pistol's charged pair, native** (recommended): one trigger, tap = the bouncing grenade, held
   0.5 s + released = a contact-burst grenade: Reach's tethered blast (180 over 0.001 -> 1; balanced 168.75 over
   0.001 -> 0.78) + the EMP on Halo 2's `emp` group with `only hurts shields` (Original Reach's 100, Balanced 0.5
   by the PP overcharge ratio 1/200 -- both strip every shield in reach: an Elite's 105 needs 0.21), over
   0.25 -> 2.5 (balanced 0.28 -> 1.94). One charged hit kills an Elite minor (shield gone, blast on the body).
   LOST: detonating a grenade already in flight, rolling while held; the vehicle stall unless the engine honours
   `side effect emp` (one test). Charge cue: lights + sound scaled `primary_charged` (the Laser's way).
B. Every grenade carries the EMP, no hold. LOST: the choice; every shot strips shields (much stronger).
C. A dll tether (release detonates the grenade in flight): a large hunt, not researched; not recommended.

## Fuse (decide with the user)

1. **Reach's own rule** (recommended): 0.5 s after the first bounce off any surface (balanced 0.4), measured on
   boot 1; Halo 2 has the rule Halo 1 lacked.
2. Halo 1's pick: a fuse from launch 1.2 s (balanced 1.1).

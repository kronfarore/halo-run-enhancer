# B2 Needle Rifle into Halo 2 -- step 4a (yardstick), 2026-11-01

Reach = HREK `rifle\needle_rifle\needle_rifle` + its projectile and three damage effects (h3_weapon_values --kit
reach, reach_tags). Halo 2 = H2EK. Ratios: balance_port.py. DEFAULT = Reach's own numbers (boot 1, `--original`);
the pick = the BALANCED rows. Time to kill: legendary, body shots, ttk_halo2's vitality and damage table.

## The supercombine: no dll patch

Halo 2's projectile tag holds everything Halo 1 hard-coded. The needler's `super det. projectile count` is 7 IN THE
TAG, its own flag `has super combining explosion`, its own `super detonation`, `super detonation damage` and
`super attached detonation damage`. Reach's 3 is a plain field write. Only one stock projectile uses the field, so
no stock tag shows the engine honouring a value other than 7: boot 1 is the proof (3 needles must combine).

| | Halo 2 needler | Reach Needle Rifle | what happens to the port |
|---|---|---|---|
| count | 7 | 3 | field, 3 |
| impact | 1 | 6 (a headshot flag) | field + flag |
| detonation (ground + attached) | 2 + 2 | none | cleared, as Reach |
| area blast | 30-50, 0.2-0.5 wu | 10-40, 0.375-1.25 wu | own damage effect |
| attached blast | 400, no radius | 35-350, 0.375-1.25 wu | own damage effect |
| needle timer | 0.5-0.7 s | 0-4 s + `detonation max time if attached` | NO such flag in Halo 2: see the trap |
| minimum velocity | 3 | 9 | field |
| super det. time | no field | 0.05 s | LOST (the blast has no 0.05 s delay) |
| super det. object types | no field | biped only | LOST (it can combine on a vehicle: the stock needler does) |
| attach | default material, units and ground | bipeds only, bounce or detonate else | the table by name |

**TRAP, the same one Halo 1 hit.** At 4/s the third needle lands 0.5 s after the first, and Halo 2's stock timer is
0.5-0.7 s: the first needle can burst before the third arrives. The timer must outlive 2 shot intervals.

## What Halo 2's Carbine changes about Halo 1's pick

Halo 1 had no mid-range Covenant rifle, so the Needler was the only family. Halo 2's Carbine IS this weapon's slot
(semi-auto, 2x, Covenant). But it cannot be the yardstick: Reach has no Carbine, and the chain through Halo 3
(Needler Reach > H3, Carbine H3 > H2) breaks on the needle's own rows. It gives rate 1.75/s (the Carbine's 15 / 30
burst field), recovery 0, velocity 3,333, and no supercombine rows at all.

So the Needler stays for everything needle-shaped, and the Carbine answers one thing the Needler cannot: ACCURACY.
The Needler's 0.5-1.5 cone means nothing on a homing shot, so its ratio (0.75-1.0) would make a 2x rifle scatter
straight needles. Sniper and Pistol have no needle rows at all (Pistol: rate 0, spread 0.06-0.75, velocity 200).

## Values

| value | Reach (Original) | via Needler | recommended Balanced | Carbine, for scale |
|---|---|---|---|---|
| needle damage | 6 | 2 (the tool reads detonation only) | **3** (Halo 2's real needle: 1 + 2) | 11 |
| rate | 4/s, recovery 0.25 | 4 (max row inverts 2.67) | 4/s, recovery 0.25 | 2 shots, recovery 0.35 |
| magazine / initial / max | 21 / 63 / 105 | 26 / 79 / 105 | 26 / 78 / 105 | 18 / 36 / 90 |
| reload | 82 fr, 2.73 s | 119 fr, 3.98 s (64 / 44) | **82 fr** (the ratio doubles the Carbine's 2.3 s) | 2.3 s |
| error | 0.15-2, min 0 | 0.75-1.0, min 0.5 | **0.3-1.0, min 0** | 0.3-0.6 |
| zoom | 1 level 2x | none | 2x | 2x |
| velocity | 1500 | 818 | 818 | 400 |
| range / air damage | 250 / 40 | 231 / 40 | 231 / 40 | 40 / 40 |
| autoaim | 2.25 / 25 | 1.97 / 19.2 | 1.97 / 19.2 | 3 / 17 |
| magnetism | 5 / 25 | 2.81 / 19.2 | 2.81 / 19.2 | 6 / 21 |
| count | 3 | 3.5 | 3 | |
| timer (attached) | 4 s | 0.5-0.7 s | **1.5-2.1 s** (stock x 6/2 shot gaps, Halo 1's rule) | |
| minimum velocity | 9 | 3 | 3 | |
| attached / area | 350 / 40 | 400 / about 50 | 400 / 50 | |
| blast radius | 0.375-1.25 | 0.2-0.5 | 0.2-0.5 | |
| melee | strike_melee | strike_melee | Halo 2's strike_melee | |

## Time to kill (legendary)

| | Elite minor | Brute minor | Grunt | Jackal |
|---|---|---|---|---|
| **Supercombine, 3 needles, 400 + 50** | **0.50 s** | **0.50 s** | 0.50 s | 0.50 s |
| Supercombine, Original 3 x 6 + 350 + 40 | 0.50 s | 0.50 s | 0.50 s | 0.50 s |
| Weaker combine, 175 + 20 | 33 left | 50 left | 0.50 s | 0.50 s |
| Needles only, 3 at 4/s | 67 / 21.4 s | 167 / 56.2 s | 14 / 3.25 s | 40 / 12.2 s |
| Needles only, Original 6 | 34 / 10.7 s | 84 / 28.2 s | 7 / 1.5 s | 20 / 4.75 s |
| peer: stock Needler, no combine | 10.0 s | 25.1 s | 1.6 s | 5.75 s |
| peer: stock Needler, 7 needles combined | 0.75 s | 0.75 s | 0.75 s | 0.75 s |
| peer: Carbine, its LIVE barrel 1 (recovery 0.14 s; corrected after the pick) | 14 / 1.82 s | 23 / about 5.4 s | 4 / 0.42 s | 6 / 0.70 s |
| peer: Carbine as h2_role_compare prints it (barrel 0, idle: the user saw these at the pick) | 2.57 s | 6.53 s | 0.48 s | 0.90 s |
| peer: Battle Rifle | 3.15 s | 6.92 s | 0.79 s | 1.18 s |

Halo 2's needle group is `plasma_slow` (shields x1.5, Elite armour x0.35, Brute x0.5): Reach's `needle` group has no
Halo 2 row, so the needler's own effect carries it. The blast is `explosion_attached`, which ignores the Brute's
armour and takes shields at x0.5. Stock needle hits attach on shields too (default material).

The port's character is the same as Reach's: weak needle by needle, deadly on the third hit. A miss breaks the
count, and the combine rewards accuracy at range where the needler's homing never reached.

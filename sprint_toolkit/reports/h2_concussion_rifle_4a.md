# B5 Concussion Rifle into Halo 2 -- step 4a (yardstick), 2026-11-26

Reach = HREK `rifle\concussion_rifle\concussion_rifle` (h3_weapon_values --kit reach; the bolt and its two damage
effects by reach_tag_fields.py; Reach's yardsticks' projectiles and blasts the same way). Halo 2 = H2EK tags read
through ttk_halo2 (scratch dumps; h2_cr_ttk_4a.py for the damage table and the time to kill). Time to kill:
legendary, DIRECT hits = impact + the full blast (the core), each part through its own Halo 2 damage group, shield
first, a shot every ceil(recovery x 30) ticks, a reload after each full magazine.

## Reach's Concussion Rifle (Original = these numbers)

Latch, recovery 0.333 s (3/s), 6 / 18 / 30, six reloaded at once (100 fr, empty and full), error 0.15 min, 0.4 / 0.4,
NO zoom, autoaim 4 / 15, magnetism 8 / 15, melee strike_melee.
The bolt: 12 -> 16 wu/s over the acceleration range 6..15 wu, gravity 0.25 (air and water), range 100, MINIMUM
VELOCITY 11, timer 'immediately', collision radius 0.1, danger radius 0.5, flags oriented along velocity + AI ballistic
aiming. IMPACT 21.5 `collision` (accel 0.75, category high explosive) + BLAST 0..21.5 over 1 -> 2 wu (core 0.8,
`plasma_fast`, accel 2.5 = THE KNOCKBACK, detonates explosives) = 43 a direct hit, 129 a second.

## What Halo 2 offers (read before any number)

| Reach mechanic | Halo 2 has | so |
|---|---|---|
| bolt speeds up 12 -> 16 over 6..15 wu | projectile `acceleration range` (the H2 fuel rod: 15 -> 6.5 over 4.5..5 wu, the rocket 8 -> 20 over 0..20) | NATIVE. Halo 1 changed speed over the whole range (6-15 % late); Halo 2 has Reach's field |
| minimum velocity 11 | the same field (no stock H2 launcher uses it: fuel rod, rocket, Brute Shot 0) | the bolt never flies below 12 (it only speeds up), in Original AND Balanced (initial 12 in every candidate): the check passes. Watched on boot 1 |
| knockback 2.5 on the blast | `instantaneous acceleration` on every damage effect; the push is scaled by the hit object's own `acceleration scale` (Chief / Elite 1.2, Brute 1.1, Grunt / Jackal 1.5, Marine 1.35, Hunter 0.75) and, unless the flag `don't scale by distance` is set, by the distance. It needs damage > 0, but not much: the Gravity Hammer's wielder shove is 0.01 damage carrying 5.0 (A5, confirmed in game) | Reach's blast carries real damage, so the push applies as is. Halo 2's own pushes per Reach unit: plasma grenade 2.0 = 2.0, rocket 2.75 vs 3.0, fuel rod 2.25 vs 1.5 |
| `plasma_fast` blast, `collision` impact | both groups exist in Halo 2's matg by name | see "Damage groups": equal to Reach on Elite / Brute / Grunt / Jackal, NOT on Hunters and Flood |
| no zoom | the donor fuel rod has 1 level (2x) | zoom 0, the scope widgets blanked (the SAW's) |
| reload all six at once | latch magazine, `rounds reloaded` 6 | native |

## Halo 2's damage table (legendary targets; matg)

| group | Elite shield | Elite body | Brute | Grunt | Jackal hand shield | Hunter armour | Hunter skin | Flood combat | hard Flood |
|---|---|---|---|---|---|---|---|---|---|
| collision | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0.25 |
| **plasma_fast** | 1 | 1 | 1 | 1 | 0.5 | **0** | **2** | 0.5 | 0 |
| explosion_large | 0.5 | 1 | 1 | 1 | 0.5 | 1 | 1 | 1 | 0.25 |
| explosion_small | 0.5 | 1 | 1 | 1 | 0.5 | 0.25 | 1 | 1 | 0.25 |

Reach's plasma_fast (Halo 1's B5 reading of HREK): Elite shield 1, body 1, Jackal shield 0.5, Hunter armour
(hard_metal_thick) 0.25, skin 1 -- Halo 2's plasma_fast is Reach's on every species except the HUNTER (armour immune,
skin x2). Reach has no Flood. Halo 2's Hunter model uses `hard_metal_solid_cov_hunter` (plasma_fast 0).
Found in passing: Halo 2's own fuel rod blast names the group `explosion_largw` (Bungie's typo): no such group, so it
is x1 on everything (its impact is explosion_large).

## The yardsticks, both games

| | Reach | Halo 2 |
|---|---|---|
| Fuel Rod | impact 100 collision (accel 1) + 0..60 over 0.5 -> 2.25 (core 0.5, explosion_large, accel 1.5); 0.4 s; 5 / 20 / 30; reload 90 fr; 15 -> 6.5 over 4.5..5; gravity 0.025; range 80; error 0 / 0..0.05; autoaim 4/25, magnetism 8/25 | impact 100 explosion_large (accel 1) + 40..90 over 0.5 -> 1.5 (core 0.5, 'explosion_largw', accel 2.25); 0.4 s; 5 / 20 / 30; reload tag 5.0 s (FP animation 90 fr); 15 -> 6.5 over 4.5..5; gravity 0.025; range 80; error 0 / 0..0.05; autoaim 4/25, magnetism 6/25; zoom 2x |
| Rocket | 200 collision (1.5) + 0..240 over 0.75 -> 2.5 (core 0.6, accel 3); 0.8 s; 2 / 4 / 8; 116 fr; 8 -> 16 over 0..30; gravity 0.02; range 175; autoaim 5/60, 10/25 | 150 explosion_large (1.5) + 75..200 over 1 -> 2 (core 1, accel 2.75); 0.8 s; 2 / 4 / 8; tag 5.0 s (FP 112 fr); 8 -> 20 over 0..20; gravity 0; range 175; autoaim 5/45, 10/25 |
| Plasma Grenade | 2 collision + 25..250 over 0.54 -> 1.8 (core 0.432, explosion_small, accel 2) | none + 50..120 over 0.75 -> 1.5 (core 0.75, explosion_small, accel 2) |

The two FUEL RODS are the same gun in every field but the damage, the push, the reload tag and magnetism.

## Values

Ratio rule: Halo 2 yardstick x Reach CR / Reach yardstick, per field. A zero on BOTH Reach sides (the blast's lower
bound) = the sibling rule (Halo 2's lower x port upper / Halo 2's upper); a zero on one side = Reach's own.

| value | Reach (Original) | **Fuel Rod (provisional)** | Rocket Launcher | Plasma Grenade |
|---|---|---|---|---|
| impact | 21.5 collision, accel 0.75 | **21.5** (100 x 21.5/100), accel **0.75** | 16.1, accel 0.75 | 0 (Halo 2's has none) |
| blast | 0..21.5 over 1 -> 2, core 0.8 | **14.3..32.25 over 1.0 -> 1.33, core 0.8** (90 x 21.5/60; lower by the sibling rule) | 6.7..17.9 over 1.33 -> 1.6, core 1.33 | 0..10.3 over 1.39 -> 1.67, core 1.39 |
| knockback (blast) | 2.5 | **3.75** (2.25 x 2.5/1.5) | 2.29 | 2.5 |
| recovery | 0.333 s (3/s) | **0.333** (x1: both 0.4) | 0.333 | Reach's |
| magazine | 6 / 18 / 30 | **6 / 18 / 30** (x1.2 / 0.9 / 1: Reach's) | 6 / 18 / 30 | Reach's |
| reload | 100 fr = 3.33 s | **5.56 s** (tag 5.0 / Reach 90 fr; the GL's rule) -- 3.33 s if Halo 2's 90-frame ANIMATION is what times its fuel rod | 4.31 s | Reach's |
| flight | 12 -> 16 over 6..15 | **x1: Reach's** | 12 -> 20 over 6..10 | Reach's |
| gravity / range | 0.25 / 100 | **x1: Reach's** | 0.25 (H2 0: one side) / 100 | Reach's |
| minimum velocity | 11 | **11** (both fuel rods 0: Reach's) | 11 | 11 |
| error | 0.15, 0.4 / 0.4 | **x1: Reach's** | Reach's (0 / 0) | Reach's |
| autoaim / magnetism | 4 / 15, 8 / 15 | **4 / 15, 6 / 15** | 4 / 11.25, 8 / 15 | Reach's |
| melee | strike_melee | **smash_melee** (both fuel rods: Reach strike -> H2 smash, the GL's) | smash_melee | |
| zoom | none | none (donor's 2x removed) | none | none |

## Direct hits to kill, legendary (h2_cr_ttk_4a.py)

Blast in `plasma_fast`, impact in `collision` unless said.

| | Elite minor | Brute minor | Grunt | Jackal |
|---|---|---|---|---|
| Reach own (Original) | 4 / 1.00 s | 6 / 1.67 s | 1 | 2 / 0.33 s |
| **Fuel Rod ratio** | **3 / 0.67 s** | **5 / 1.33 s** | 1 | 2 / 0.33 s |
| Fuel Rod ratio, Halo 2's fuel rod groups (explosion_large) | 5 / 1.33 s | 5 / 1.33 s | 1 | 2 / 0.33 s |
| Rocket ratio | 5 / 1.33 s | 8 / 6.31 s | 2 / 0.33 s | 2 / 0.33 s |
| Plasma Grenade ratio | 16 / 11.0 s | 25 / 20.0 s | 4 / 1.00 s | 6 / 1.67 s |
| H2 Fuel Rod (peer) | 2 / 0.40 s | 2 / 0.40 s | 1 | 1 |
| H2 Rocket (peer) | 2 / 0.80 s | 1 | 1 | 1 |
| H2 Brute Shot (peer) | 3 / 0.60 s | 4 / 0.90 s | 1 | 1 |

Damage a second: Reach 129, Fuel Rod ratio 161, Rocket ratio 102, Plasma Grenade ratio 31; Halo 2's fuel rod 475,
Brute Shot 233. Recommended: the PROVISIONAL Fuel Rod (Halo 1's pick): in Halo 2 it is the same gun as Reach's fuel
rod, so the ratio keeps Reach's whole handling and moves only the blast (x1.5), the push and the reload.

## Decide with the user

1. **Yardstick**: Fuel Rod (recommended) / Rocket Launcher / Plasma Grenade.
2. **Damage groups** (Halo 2's table is global, per group: a weapon cannot carry its own Hunter row):
   A. **By Reach's names** (recommended, the GL's rule): impact `collision`, blast `plasma_fast`. Reach's on Elite /
      Brute / Grunt / Jackal; HUNTERS: armour immune, skin x2 (Reach 0.25 / 1) -- Halo 1's rule 'Reach's values for
      Hunters in default' cannot hold; Flood combat forms x0.5, hard Flood immune.
   B. Halo 2's fuel rod groups: `explosion_large` on both. Hunters x1 (killable through armour), Flood x1, but Elite
      shields x0.5 (5 hits instead of 3).
   C. A new damage group in matg with Reach's plasma_fast rows (Hunter armour 0.25, skin 1): a block insert in the
      SHARED globals of all 13 levels. Not recommended.
3. **Knockback**: Original = Reach's 2.5 (Halo 1's 'decent enough'); Balanced = the ratio 3.75. Any tuning waits until
   you have seen Reach's own 2.5 in game.
4. **Balanced reload**: 5.56 s by Halo 2's fuel rod TAG time (the GL took the RL's tag 5.0 the same way), or 3.33 s
   (x1) if its 90-frame animation is what you see in game.

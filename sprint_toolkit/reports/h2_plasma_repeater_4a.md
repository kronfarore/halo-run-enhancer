# B3 Plasma Repeater into Halo 2 -- step 4a (yardstick), 2026-11-21

Reach = HREK `rifle\plasma_repeater\plasma_repeater` (h3_weapon_values --kit reach) + its heat FUNCTIONS (Halo 1's
B3 reading through ManagedBlam Evaluate: 0.03 heat a tick while firing, rate 15 + (3 - 15) x heat^1.5, passive loss
0.25/s cold -> 0.06/s hot, never overheats, manual vent 2.5 s). Halo 2 = H2EK. Ratios: balance_port.py ("Plasma
Repeater" "Plasma Rifle" "Halo Reach" "Halo 2" -> balance_Plasma_Repeater_HaloReach_to_Halo2.json). Time to kill:
legendary, body shots, ttk_halo2's vitality and damage table; heat simulated in 1/600 s steps
(scratch rp_heat_fit.py: Reach's true heat model against Halo 2's held-time ramp).

## The finding: Halo 2's Plasma Rifle IS Reach's Plasma Rifle

Bungie carried the tag numbers over: rate 6 -> 9 over 0.8 s (decel 0.6), heat 0.15 a round, loss 0.8525 / 0.35
overheated, recovery 0.1, damage 6-10 plasma_slow, battery 0.0025, range 40, magnetism 9 / 18 -- identical in both.
So the Plasma Rifle ratio is x1 on every heat, rate, damage, battery and range row. Only the projectile speed
(14 vs 25: x0.56), the spread (H2's single-wield cone 0.25-0.75 vs 1.3-3.5) and autoaim angle (6 vs 5) differ.
**Balanced = Reach's own numbers except speed, spread and autoaim.**

## Where Reach's heat lives, and what Halo 2 can do with it

| | Reach repeater | Halo 2 engine |
|---|---|---|
| rate | 15 -> 3 by HEAT (heat^1.5) | rounds per second lo -> hi over HELD time (acceleration time), back over deceleration time |
| heat | +0.03 a tick firing (per-round field 0) | heat generated per ROUND |
| passive loss | 0.25/s cold -> 0.06/s hot (a function) | one `heat loss per second` |
| overheat | never: heat stops at 1, the gun fires on at 3/s | overheated threshold -> stops until heat falls to the recovery threshold at `overheated heat loss` (measured on the Laser: 0.9 / 0.4 = 2.24 s, as the tag says) |
| vent | manual, reload key, 2.5 s to 0, can be cut short | none |

Reach held from cold: 12 rounds in 1 s, 16 in 2 s, 19 in 3 s, 28 in 6 s; heat 0.99 on round 14 (1.25 s), 1.0 on
round 15; 3/s from there. Passive cooling from 1: to 0.5 in 7.5 s, to 0.1 in 11.2 s (why Reach players vent).

**A ramp 15 -> 3 over 1.6 s held** puts every shot within 0.1 s of Reach's up to full heat, same round count
(the fit). Halo 2's per-tick fire rule is NOT measured yet (Halo 1's reset-to-0 cost a rate step there):
boot 1 probes it on the port (h2_weapon_state_probe) before any re-fit.

### Approximation A (recommended; Halo 1's pick "B" there)
OVERHEAT stands in for the vent. Ramp 15 -> 3 over 1.6 s; heat 0.0915 a round with loss 0.25 (Reach's cold loss)
-> overheats on round 15 at 1.48 s (Reach full on 14-15, 1.25-1.58 s); overheated loss 0.36 to recovery 0.1 = Reach's
2.5 s vent; deceleration time 3.6 s (the meter's 0.9 drains at 0.25/s in 3.6 s, so rate and meter recover together).
LOST: venting by choice and part-way, firing on at 3/s when hot, the slow hot cooling (0.06/s).

### Approximation B
NO overheat: ramp 15 -> 3 over 1.6 s and the gun fires on at 3/s as Reach's does; heat per round small enough that
the meter peaks near full and never trips. LOST: any vent at all -- a hot gun stays slow until the deceleration
time has run (Reach's passive 11 s, or shorter by choice); the meter no longer means anything to the rate.

## THE MANUAL VENT (a question for you)

Halo 2 has no reload-key vent: a battery weapon has no magazine, so the reload press goes nowhere. Options:
1. **None**: the overheat is the vent (approximation A). Nothing new to build.
2. **A halo2.dll patch**: the reload press on a heat weapon without a magazine sets the weapon's overheated state.
   Halo 2 then vents it exactly as an overheat (overheated loss, `overheated` effect, the FP overheat animations) and
   VENTING PART-WAY COMES FREE (a press at heat 0.4 vents 0.4 -> 0.1 in 0.8 s). AI never uses it. Cost: a static
   hunt in halo2.dll for the reload input path and the overheated bit (h2_dll_dis, as the supercombine), 2-4 boots,
   a new enhancer engine option (handed off; dll patches go through the enhancer). Not researched yet: I would
   exhaust the dll statically before any boot and report whether it is cheap.

## Values

| value | Reach (Original) | via Plasma Rifle (Balanced) | via Plasma Pistol | H2 Plasma Rifle, for scale |
|---|---|---|---|---|
| damage | 5.834-7 (mean 6.42) plasma_fast | **6.42** (x1) | 2.81 (7/16) | 6-10 plasma_slow |
| rate | 15 -> 3 by heat | 15 -> 3 (x1), ramp 1.6 s | Reach's (pistol is tapped: no ratio) | 6 -> 9 over 0.8 s |
| heat | 0.03 a tick, never overheats | x1: approximation A or B | x1.14 | 0.15 a round |
| vent | 2.5 s manual | 2.5 s (A: the overheat) | 2.5 x 0.45/0.45 | overheat 2.6 s |
| battery | 0.005 (200 rounds) | 0.005 (x1) | 0.01 (100) | 0.0025 (400) |
| velocity | 25 -> 35 | **14 -> 19.6** (x0.56) | 13.8 -> 12.8 (11/20, 11/30) | 14 |
| range / air | 100 / 40 | 100 / 40 | 100 / 40 | 40 / 40 |
| error (single wield) | 0.4-3, min 0 | **0.077-0.64**, min 0 | 0-0 (the pistol has no cone) | 0.25-0.75 |
| autoaim / magnetism | 5 / 15, 10 / 20 | **6 / 15**, 10 / 20 | 7.5 / 9 | 6 / 12, 9 / 18 |
| melee | Reach strike_melee | Halo 2's strike_melee (20-60) | the same | strike / smash |
| zoom | none | none | none | none |
| dual wield | no (two-handed) | flag CLEARED on the Plasma Rifle clone | | yes |

## Materials (a second question)

Reach's bolt is `plasma_fast`, and Halo 2 HAS a plasma_fast group (Bungie's own row: shields x1, Elite armour x1,
Brute flesh x1, Jackal shield x0.5, Hunter flesh x2, Sentinels x2). Halo 2's Plasma Rifle is plasma_slow (shields
x1.5, Elite armour x0.35, Brute flesh x0.5, Sentinels x4).
- **plasma_fast** (recommended: Reach's own group by name, Halo 2's own numbers for it)
- plasma_slow (the yardstick's): strong on shields, weak on armour -- Brutes take twice as long.

## Time to kill (legendary, body shots; shots / seconds)

| | Elite minor | Brute minor | Grunt | Jackal |
|---|---|---|---|---|
| **Reach's true heat model, 6.42 plasma_fast** | 24 / 4.58 s | 39 / 9.58 s | 7 / 0.42 s | 10 / 0.68 s |
| **A: overheat = vent** | 24 / 4.53 s | 39 / 8.52 s | 7 / 0.45 s | 10 / 0.73 s |
| B: no overheat, 3/s on | 24 / 4.46 s | 39 / 9.46 s | 7 / 0.45 s | 10 / 0.73 s |
| Reach heat, plasma_slow | 31 / 6.91 s | 78 / 22.6 s | 7 / 0.42 s | 10 / 0.68 s |
| Plasma Pistol ratio (2.81, A) | 54 / 15.0 s | 90 / 28.6 s | 15 / 3.76 s | 22 / 4.36 s |
| peer: Plasma Rifle | 20 / 4.76 s | 50 / 10.87 s | 4 / 0.46 s | 6 / 0.71 s |
| peer: Brute Plasma Rifle | 20 / 4.60 s | 50 / 12.64 s | 4 / 0.36 s | 6 / 0.57 s |
| peer: SMG | 32 / 2.07 s | 106 / 8.93 s | 9 / 0.53 s | 13 / 0.80 s |
| peer: Needler (no combine) | 199 / 30.0 s | 500 / 76.4 s | 40 / 5.75 s | 60 / 8.25 s |

Elites and Brutes outlast the first heat cycle, so their times include one vent (A) or the 3/s tail (B / Reach).
The repeater lands with the Plasma Rifle family: as fast on Elites, a little faster on Brutes (plasma_fast), the
same on Grunts and Jackals -- Reach's character (a hose that wants venting) kept.

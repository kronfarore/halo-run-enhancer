# A2 Spartan Laser into Halo 2 -- step 4a (yardstick), 2026-10-28

Halo 3 = H3EK `support_high\spartan_laser\spartan_laser` (h3_weapon_values.py + the trigger / barrels /
damage read for Halo 1's A8, ports_h1/spartan_laser.py); Halo 2 = H2EK (ttk_common.flatten); legendary.
Each cell: Halo 3's laser value x (candidate's H2 / H3). DEFAULT = Halo 3's own numbers; the pick = the
BALANCED rows.

What Halo 3's laser is (A8's reading, re-checked): trigger `spew-charge` 2.5 s; while charging barrel 0
fires a no-damage aiming tracer at 20/s; charged, barrel 1 fires 5 beam rounds at 30/s; a round =
DETONATION 20 (0..0.6 wu) + the AOE SPIKE BUMP 94 inside 0.15 wu = 114 direct -> **570 a shot**; damage
group `laser` = the rocket's `explosion_large` except Hunter armour x0.5 (rocket x1); battery 0.04 a round
= **5 shots**; heat 1 a round = every shot overheats, vent (1 - 0.1) / 0.4 = **2.25 s**; cycle 2.5 + 0.13 +
2.25 = **4.88 s**; zoom 1 level **2.5x**; autoaim 1 / 25, magnetism 5 / 25; range 120; melee smash_melee;
FP ready 31 / put-away 5 frames.

| value | H3 laser | via Rocket Launcher (provisional) | via Beam Rifle | via Sniper Rifle | via Sentinel Beam |
|---|---|---|---|---|---|
| ratio source (H2 / H3) | -- | dmg 350 / 440 (both direct hits: H2 impact 150 + blast 200; H3 240 + bump 200) | 45 / 80 | 45 / 80 | 2 / 4 |
| **damage a shot** | 570 | **453** (x0.795) | 321 (x0.5625) | 321 (x0.5625) | 285 (x0.5) |
| damage group | laser (= explosion_large, Hunter x0.5) | explosion_large (the rocket's own) | plasma_fast / sniper (Hunters IMMUNE) -> keep explosion_large | bullet_fast / sniper -> keep explosion_large | plasma_fast / anti_flood |
| charge | 2.5 s | 2.5 s (recovery 0.8 / 0.8, reload tag 5 / 5: x1; by the reload ANIM 112 / 116 fr: x0.97 = 2.42 s) | 1.56 s (recovery 0.25 / 0.4) | 1.79 s (recovery 0.5 / 0.7) | -- (no ratio: spew) |
| battery (shots) | 5 | 5 (magazine 2 / 4 / 8 both games) | 4.5 (age 0.0556 / 0.05) | -- (magazine, no age) | 5 (age 0.003 both) |
| heat a shot / vent | 1 / 2.25 s | x1 (no heat on the rocket) | 0.93 (0.65 / 0.7: would NOT overheat a shot) / 2.25 s (loss 0.3 / 0.3) | x1 | 1 / 2.25 s (0.04 / 0.04, 0.35 / 0.35) |
| cycle (charge + vent) | 4.88 s | 4.88 s | 3.94 s | 4.17 s | 4.88 s |
| zoom | 2.5x | 2.5x (1.8 / 1.8) | 2.5x (3.5-9.5 both) | 2.19x (3.5 / 4) | -- (no zoom) -> 2.5x |
| range | 120 | 120 (175 / 175) | **28.8** (120 / 500: H2's beam rifle / sniper reach 120, Halo 3's 500) | **28.8** | 30 (30 / 120) |
| autoaim angle / range | 1 / 25 | 1 / **45** (5/5, 45/25) | 1 / 25 (1/1, 10/10) | 1 / 25 | 1 / 25 (1/1, 12/12) |
| magnetism angle / range | 5 / 25 | 5 / 25 (10/10, 25/25) | 5 / 25 (4/4, 14/14) | 5 / 25 | 5 / 25 (9/9, 18/18) |
| melee | smash_melee | smash_melee (H2 RL: smash) | strike_melee | strike_melee | -- |
| FP ready | 31 fr | 28.6 fr (H2 RL 24 / H3 26) | -- | -- | -- |

## Shots to kill (body / direct hit, legendary, matg table; explosion_large unless noted)

| shot | Elite minor | Elite zealot | Elite ultra | Brute minor / captain | Hunter | Flood Elite | Jackal / Grunt / Sentinel |
|---|---|---|---|---|---|---|---|
| H3 own 570 | 1 | 1 | 2 | 1 / 1 | 1 | 1 | 1 |
| **via Rocket 453** | 1 | 1 | 2 | 1 / 1 | 1 (2 with Halo 3's Hunter x0.5) | 1 | 1 |
| via Beam Rifle / Sniper 321 | 1 | 2 | 3 | 1 / 1 | 2 | 1 | 1 |
| via Sentinel 285 | 1 | 2 | 3 | 1 / 1 | 2 | 1 | 1 |
| peer: H2 Rocket (350 direct) | 1 | 2 | 3 | 1 / 1 | 2 | 1 | 1 |
| peer: H2 Beam Rifle / Sniper (45) | 3 | 3 | 6 | 6 / 6 | immune / 9+ | 9 | 1-2 |

Time: the laser's n-th shot lands at 2.5 + (n-1) x 4.88 s (Elite ultra 2 shots = 7.4 s); the H2 rocket's
3 rockets on an Elite ultra = 0.8 + 0.8 + reload 5.0 = 6.6 s; the beam rifle's 6 = 6 x 0.25 + overheats.

## Notes for the pick

* **Rocket Launcher** (Halo 1's pick, the user's 2026-10-09 reason holds here): Halo 3's laser group IS the
  rocket's explosion_large, Halo 2 has the same group, every ratio leg is a real value in both games
  (range / zoom / battery x1), the bump counted on both sides (the A8 user rule). Only the autoaim RANGE
  moves (25 -> 45: H2's rocket reaches farther). Hunter armour: Halo 3's laser does x0.5 to it, the rocket
  x1 -- carry the x0.5 (2 shots per Hunter) or not (1 shot)?
* **Beam Rifle** is the closest MECHANISM (instant beam, battery + heat, and it is the proposed DONOR) but
  its ratios break: range 500 -> 120 shrinks the laser to 29 wu; heat 0.93 stops it overheating each shot;
  its damage group makes Hunters immune.
* **Sniper**: the same range break; no battery leg.
* **Sentinel Beam**: a spew weapon, no charge / zoom leg; range 30 wu.

## The donor + the charge (not numbers -- for the record)

Donor proposed: H2 **Beam Rifle** (battery + heat, 0 magazines, two-handed, `be` prefix, 2 zoom levels ->
1). Halo 2's only `charge` trigger = the Scarab main gun (`scenarios\...\scarab\weapons\main_gun\
scarab_main_gun`): behavior **charge**, primary barrel -1, secondary barrel 0, both actions `charge`,
charging 2.8 s, overcharged action **discharge** (fires barrel 0 when full), charging effect + charged
illumination. (Its `scarab_main_gun_handheld` twin -- Bungie's player copy -- is a plain SPEW plasma rifle.)
The plasma pistol is `latch-autofire` with secondary action `charge` (0.6 s, barrel 1 = the charged bolt).
Plan: the port's trigger = the Scarab's shape (charge 2.5 s -> discharge barrel 1, the beam), tested in
game first; fallback the plasma pistol's latch + charge pair (its release-fires-the-tracer, Halo 3's own
tap behaviour).

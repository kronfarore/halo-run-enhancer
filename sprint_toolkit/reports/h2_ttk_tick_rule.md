# Halo 2 TTK under the measured 30 Hz fire rule (2026-11-22)

`ttk_halo2.sim_player` now uses `tick_shots` by default (`FIRE_RULE = 'ticks'`; a weapon dict's
`'fire rule': 'continuous'` keeps the old model). The rule was measured on the Plasma Repeater port
(reports/h2_fire_rule.jsonl): each 30 Hz tick, rate / 30 is added in float32. A shot fires when the
sum reaches 1, then the sum resets to 0. So a shot comes every ceil(30 / rate) ticks.

* At a flat rate: 20/s fires 15/s, 11/s fires 10/s, 9/s fires 7.5/s, 8/s fires 7.5/s, 3.05/s fires
  3/s. 15/s, 10/s and 6/s fire at their tag rate, because the float32 sum lands exactly on 1.0.
* A falling ramp from 15/s fires every 3 ticks (10/s), because the step falls just below 0.5.
* The sum starts at 0 when the trigger is pulled (the measurement needs this; a free first shot
  overheats on round 39). Times are counted from the first shot.
* Assumed, not measured: fire recovery and reloads round up to whole ticks. After an overheat the
  trigger starts over (sum 0, ramp from its low end).
* `python ttk_halo2.py --check` reproduces both measurements:
  * boot 1 ORIGINAL (15 -> 3 over 1.6 s, heat 0.0915, loss 0.25) overheats on round 44, at 12.17 s
    (the continuous rule gave round 15);
  * the shipped tags (20 -> 3.05 over 1.5 s, heat 0.076, loss 0.09) overheat on round 15 at 1.533 s.
* h2_role_compare: a new `fires/s` column, and dps is now computed from the fired rate. The
  shotgun's and the charge weapons' derived paces stay continuous.

## Stock Halo 2 weapons, legendary, body shots (seconds; h2_role_compare over all ten ports' sets)

| weapon | tag rate | fires | Elite minor | Brute minor | Grunt minor | Jackal minor |
|---|---|---|---|---|---|---|
| Plasma Rifle | 6-9 | 6-7.5 | **4.76 -> 2.60** | **10.87 -> 9.30** | 0.46 -> 0.47 | 0.71 -> 0.73 |
| Brute Plasma Rifle | 8-11 | 7.5-10 | 4.60 -> 4.83 | 12.64 -> 13.47 | 0.36 -> 0.40 | 0.57 -> 0.60 |
| Needler | 8 | 7.5 | 30.00 -> 31.60 | 76.38 -> 80.40 | 5.75 -> 6.07 | 8.25 -> 8.73 |
| Battle Rifle | 15 (bursts) | 15 | 3.15 -> 3.20 | 6.92 -> 7.00 | 0.79 -> 0.80 | 1.18 -> 1.20 |
| Covenant Carbine | 15 | 15 | 2.57 -> 2.67 | 6.53 -> 6.70 | 0.48 -> 0.50 | 0.90 -> 0.93 |
| Sentinel Beam | 30 | 30 | 2.47 | 6.41 -> 6.47 | 0.63 | 0.97 |
| SMG | 15 | 15 | 2.07 | 8.93 | 0.53 | 0.80 |
| Pistol | 10 | 10 | 3.27 | 13.53 | 0.40 | 0.70 |
| Plasma Pistol, Beam Rifle, Sniper Rifle, Shotgun, Rocket Launcher | | | unchanged | | | |

Why the Plasma Rifle gets FASTER: the gun now fires 7.5/s, so the heat loss (0.85/s) takes more
heat off between bolts. Against an Elite (20 bolts) it no longer overheats. Against a Brute the
first overheat moves from the 19th bolt to the 26th, and the kill has 1 overheat instead of 2. The
Battle Rifle and Carbine changes come only from the fire recovery rounding up to whole ticks
(BR 0.26 s = 8 ticks).

Ports (DEFAULT tags, the yardstick tables): Plasma Repeater 4.03 -> 4.70 s vs Elite, SAW (20/s
fires 15/s) 0.95 -> 1.27, Needle Rifle (4/s fires 3.75/s) 10.73 -> 11.27, Spike Rifle (8 fires 7.5)
2.00 -> 2.13, Flamethrower (10.8 fires 10) 0.65 -> 0.70. These ports are unchanged: AR, DMR,
Mauler, Gravity Hammer, Spartan Laser.

reports/ttk_legendary.md (ttk_report.py over reports/ttk/ttk_halo_2.json): only the Halo 2 player
rows changed. The AI rows are not quantised yet: their rate is capped at the weapon's TAG rate
(Elite Plasma Rifle 9/s, which would fire 7.5/s).

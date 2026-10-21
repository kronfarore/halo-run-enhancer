# S1 Flamethrower into Halo 2 -- step 4a (yardstick), 2026-10-21

`python h2_ft_ttk_4a.py` (Halo 1 = HCEEK `weapons\flamethrower\flamethrower`; Halo 2 = H2EK; legendary).
Each cell: Halo 1's flamethrower value x (yardstick's H2 / H1). `--` = no ratio (the yardstick has no
such value in one game) -> Halo 1's raw value.

| value | H1 flamethrower | via Plasma Rifle | via Shotgun | via SMG (H1 port) | via Sentinel Beam (H1 port) |
|---|---|---|---|---|---|
| damage per flame (upper) | 21.5 | **16.5** (x0.77) | 16.5 (x0.77) | 20.4 (x0.95) | 9.3 (x0.43) |
| damage lower bound | 18 | 10.8 | 11.3 | 0 | 7.8 |
| rate (shots/s) | 12 | **10.8** (x0.9) | 12 (--: H2 rate 0) | 12 | 12 |
| flames per shot | 2 | 2 | 1.33 | 2 | 2 |
| fuel loaded / initial / max | 100 / 300 / 600 | 100 / 300 / 600 (--) | 100 / 450 / 480 | 100 / 300 / 600 | -- |
| reload s | 3.4 | 3.4 (--) | 3.4 | 3.4 | 3.4 (--) |
| heat per shot | 0.072 | **0.135** (x1.88) | -- | -- | 0.068 |
| heat loss /s | 0.44 | **1.25** (x2.84) | -- | -- | 1.25 |
| heat recovery threshold | 0.30 | **0.12** (x0.4) | -- | -- | 0.12 |
| error angle deg | 2 - 8 | 1 - 1.2 | 1.6 - 8 | 1.6 - 5.1 | -- |
| velocity | 3.6 | 1.0 (x0.28) | 3.1 | 3.6 | 3.6 |
| range wu | 16 | 16 (--) | 3.2 (x0.2) | 16 | 4 |
| autoaim deg / wu | 1.5 / 16 | 1.8 / 7.7 | 2 / 6.4 | 1.8 / 16 | 1.5 / 16 |
| magnetism deg / wu | 4 / 20 | 3 / 14.4 | 5.3 / 8 | 4 / 20 | 4 / 20 |

Time to kill, point blank (upper bound), trigger held:

* Halo 1 itself (Elite minor): **Flamethrower 0.90 s** (10 shots), Plasma Rifle 2.10 s -> the flamethrower
  kills in 0.43x the Plasma Rifle's time.
* Halo 2 peers (Elite minor / Brute / Grunt / Jackal / Flood combat): Plasma Rifle 4.76 / 10.87 / 0.46 /
  1.38 / 9.72 s (with overheats; 2.27 s on the Elite without); SMG 2.07 / 8.93 / 0.53 / -- / 2.20;
  Sentinel Beam 2.47 / 6.41 / 0.63 / 5.24 / 1.10; Shotgun 1 / 4 / 1 / -- / 1 shot.
* The port (Plasma Rifle ratio) by Halo 2 damage group:

| group | Elite | Brute | Grunt | Jackal | Flood combat |
|---|---|---|---|---|---|
| `burning` (Halo 2's own fire row: shields x2, organic x2, metal x0-0.25, Flood x2) | 0.65 | 0.28 | 0.00 | 0.19 | 0.28 |
| `explosion_small` (nearest Halo 1's flame table: shields x0.5, organic x1) | 0.65 | 0.65 | 0.09 | 0.46 | 0.56 |
| `plasma_slow` (the Plasma Rifle's own) | 0.56 | 1.39 | 0.09 | 0.28 | 1.11 |

Halo 1's flame: Elite shields x0.5, metal x0.3, Hunter x0.5, Flood / organics x1.
Heat (Plasma Rifle ratio): overheats after ~2.7 s held (Halo 1: ~3.6 s at its 30 Hz-quantised 10 shots/s);
the 100-fuel tank lasts 50 shots = 4.6 s.

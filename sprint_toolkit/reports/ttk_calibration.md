# Difficulty baselines for equal Legendary time-to-kill

Fitted from `reports/ttk_legendary.md` (method there; this script: `sprint_toolkit/ttk_calibrate.py`). Targets = the cross-game geometric mean per category, so Legendary overall stays as hard as today on average; only the differences between games shrink. Rate of Fire stays vanilla (the AI trigger rate is capped at the weapon rate, so that dial acts unevenly).

Enemy Vitality and Enemy Shield move by ONE factor per game, so every game keeps its own shield / body balance (--split fits them separately; the totals alone barely tell the two apart, so that gives lopsided dials).

## Options -> Run rules -> Difficulty baseline (Legendary)

| game | Vitality | Shield | Damage | Rate of Fire |
|---|---|---|---|---|
| Halo 1 | 1.41 (now 1.40) | 1.41 (now 1.40) | 2.63 (now 1.80) | vanilla (1.50) |
| Halo 2 | 0.77 (now 1.00) | 0.77 (now 1.00) | 0.84 (now 1.50) | vanilla (1.50) |
| Halo 3 | 1.40 (now 1.00) | 1.40 (now 1.00) | 1.36 (now 1.60) | vanilla (1.00) |
| Halo 3: ODST | 1.34 (now 1.00) | 1.34 (now 1.00) | 3.57 (now 1.60) | vanilla (1.00) |
| Halo Reach | 0.81 (now 1.00) | 0.81 (now 1.00) | 1.58 (now 1.60) | vanilla (1.00) |
| Halo 4 | 0.92 (now 1.00) | 0.92 (now 1.00) | 1.20 (now 1.30) | vanilla (1.00) |

## Targets

| category | target | games |
|---|---|---|
| kills you Brute / Knight (paced) | 1.82 s | 5 |
| kills you Elite (paced) | 1.69 s | 5 |
| you kill Brute / Knight (automatic) | 4.88 s | 5 |
| you kill Brute / Knight (plasma) | 5.07 s | 5 |
| you kill Brute / Knight (precision) | 5.99 s | 5 |
| you kill Elite (automatic) | 2.26 s | 5 |
| you kill Elite (plasma) | 3.70 s | 5 |
| you kill Elite (precision) | 3.70 s | 5 |

## Before -> after, per row

| game | direction | enemy | weapon | before | after | target | hits after |
|---|---|---|---|---|---|---|---|
| Halo 1 | you kill | Elite | Assault Rifle | 2.20 s | 2.27 s | 2.26 s | 35 |
| Halo 1 | you kill | Elite | Plasma Rifle | 2.10 s | 2.10 s | 3.70 s | 17 |
| Halo 1 | you kill | Elite | Pistol | 5.50 s | 5.50 s | 3.70 s | 13 |
| Halo 1 | kills you | Elite | Plasma Rifle (AI) | 2.87 s | 1.70 s | 1.69 s | 11 |
| Halo 2 | you kill | Elite | SMG | 2.07 s | 1.60 s | 2.26 s | 25 |
| Halo 2 | you kill | Elite | Plasma Rifle | 4.76 s | 3.76 s | 3.70 s | 16 |
| Halo 2 | you kill | Elite | Battle Rifle | 3.15 s | 2.49 s | 3.70 s | 20 |
| Halo 2 | kills you | Elite | Plasma Rifle (AI) | 1.08 s | 1.86 s | 1.69 s | 16 |
| Halo 2 | you kill | Brute / Knight | SMG | 8.93 s | 6.89 s | 4.88 s | 82 |
| Halo 2 | you kill | Brute / Knight | Plasma Rifle | 10.87 s | 8.43 s | 5.07 s | 39 |
| Halo 2 | you kill | Brute / Knight | Battle Rifle | 6.92 s | 5.40 s | 5.99 s | 33 |
| Halo 2 | kills you | Brute / Knight | Brute Plasma Rifle (AI) | 0.96 s | 1.60 s | 1.82 s | 16 |
| Halo 3 | you kill | Elite | Assault Rifle | 1.90 s | 2.70 s | 2.26 s | 28 |
| Halo 3 | you kill | Elite | Plasma Rifle | 4.76 s | 6.76 s | 3.70 s | 28 |
| Halo 3 | you kill | Elite | Battle Rifle | 3.31 s | 4.68 s | 3.70 s | 35 |
| Halo 3 | kills you | Elite | Plasma Rifle (AI) | 3.10 s | 3.32 s | 1.69 s | 13 |
| Halo 3 | you kill | Brute / Knight | Assault Rifle | 2.70 s | 3.90 s | 4.88 s | 40 |
| Halo 3 | you kill | Brute / Knight | Plasma Rifle | 2.16 s | 3.12 s | 5.07 s | 27 |
| Halo 3 | you kill | Brute / Knight | Battle Rifle | 3.03 s | 4.21 s | 5.99 s | 33 |
| Halo 3 | kills you | Brute / Knight | Spiker (AI) | 0.88 s | 3.10 s | 1.82 s | 10 |
| Halo 3: ODST | you kill | Brute / Knight | Silenced SMG | 3.07 s | 4.13 s | 4.88 s | 63 |
| Halo 3: ODST | you kill | Brute / Knight | Plasma Rifle | 2.16 s | 3.00 s | 5.07 s | 26 |
| Halo 3: ODST | you kill | Brute / Knight | Magnum (automag) | 9.22 s | 12.43 s | 5.99 s | 63 |
| Halo 3: ODST | kills you | Brute / Knight | Spiker (AI) | 6.70 s | 3.10 s | 1.82 s | 10 |
| Halo Reach | you kill | Elite | Assault Rifle | 2.70 s | 2.20 s | 2.26 s | 23 |
| Halo Reach | you kill | Elite | Plasma Repeater | 6.11 s | 4.98 s | 3.70 s | 23 |
| Halo Reach | you kill | Elite | DMR | 3.00 s | 2.67 s | 3.70 s | 9 |
| Halo Reach | kills you | Elite | Plasma Rifle | 1.57 s | 1.57 s | 1.69 s | 10 |
| Halo Reach | you kill | Brute / Knight | Assault Rifle | 5.87 s | 4.81 s | 4.88 s | 33 |
| Halo Reach | you kill | Brute / Knight | Plasma Repeater | 9.77 s | 7.97 s | 5.07 s | 32 |
| Halo Reach | you kill | Brute / Knight | DMR | 4.67 s | 3.67 s | 5.99 s | 12 |
| Halo Reach | kills you | Brute / Knight | Spike Rifle | 1.88 s | 1.88 s | 1.82 s | 11 |
| Halo 4 | you kill | Elite | Assault Rifle | 2.50 s | 2.30 s | 2.26 s | 24 |
| Halo 4 | you kill | Elite | Storm Rifle | 2.40 s | 2.20 s | 3.70 s | 23 |
| Halo 4 | you kill | Elite | Battle Rifle | 4.03 s | 3.67 s | 3.70 s | 31 |
| Halo 4 | kills you | Elite | Storm Rifle (AI) | 0.92 s | 0.92 s | 1.69 s | 12 |
| Halo 4 | you kill | Brute / Knight | Assault Rifle | 6.37 s | 5.91 s | 4.88 s | 40 |
| Halo 4 | you kill | Brute / Knight | Storm Rifle | 6.80 s | 6.28 s | 5.07 s | 37 |
| Halo 4 | you kill | Brute / Knight | Battle Rifle | 8.57 s | 7.93 s | 5.99 s | 51 |
| Halo 4 | kills you | Brute / Knight | Suppressor (AI) | 1.87 s | 2.00 s | 1.82 s | 31 |

Average distance from the target: before x1.49, after x1.34 (geometric; 1.00 = every row exactly on target).

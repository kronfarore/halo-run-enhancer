# Difficulty baselines for equal Legendary time-to-kill

Fitted from `reports/ttk_legendary.md` (method there; this script: `sprint_toolkit/ttk_calibrate.py`). Targets = the cross-game geometric mean per category, so Legendary overall stays as hard as today on average; only the differences between games shrink. Rate of Fire stays vanilla (the AI trigger rate is capped at the weapon rate, so that dial acts unevenly).

Enemy Vitality and Enemy Shield were fitted SEPARATELY (--split).

## Options -> Run rules -> Difficulty baseline (Legendary)

| game | Vitality | Shield | Damage | Rate of Fire |
|---|---|---|---|---|
| Halo 1 | 2.62 (now 1.40) | 0.49 (now 1.40) | 2.63 (now 1.80) | vanilla (1.50) |
| Halo 2 | 0.58 (now 1.00) | 1.36 (now 1.00) | 0.84 (now 1.50) | vanilla (1.50) |
| Halo 3 | 1.91 (now 1.00) | 0.92 (now 1.00) | 1.36 (now 1.60) | vanilla (1.00) |
| Halo 3: ODST | 2.04 (now 1.00) | 0.31 (now 1.00) | 3.57 (now 1.60) | vanilla (1.00) |
| Halo Reach | 0.93 (now 1.00) | 0.64 (now 1.00) | 1.58 (now 1.60) | vanilla (1.00) |
| Halo 4 | 1.60 (now 1.00) | 0.35 (now 1.00) | 1.20 (now 1.30) | vanilla (1.00) |

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
| Halo 1 | you kill | Elite | Assault Rifle | 2.20 s | 2.20 s | 2.26 s | 34 |
| Halo 1 | you kill | Elite | Plasma Rifle | 2.10 s | 2.89 s | 3.70 s | 23 |
| Halo 1 | you kill | Elite | Pistol | 5.50 s | 5.50 s | 3.70 s | 13 |
| Halo 1 | kills you | Elite | Plasma Rifle (AI) | 2.87 s | 1.70 s | 1.69 s | 11 |
| Halo 2 | you kill | Elite | SMG | 2.07 s | 2.33 s | 2.26 s | 36 |
| Halo 2 | you kill | Elite | Plasma Rifle | 4.76 s | 4.01 s | 3.70 s | 17 |
| Halo 2 | you kill | Elite | Battle Rifle | 3.15 s | 3.67 s | 3.70 s | 29 |
| Halo 2 | kills you | Elite | Plasma Rifle (AI) | 1.08 s | 1.86 s | 1.69 s | 16 |
| Halo 2 | you kill | Brute / Knight | SMG | 8.93 s | 5.19 s | 4.88 s | 62 |
| Halo 2 | you kill | Brute / Knight | Plasma Rifle | 10.87 s | 6.21 s | 5.07 s | 29 |
| Halo 2 | you kill | Brute / Knight | Battle Rifle | 6.92 s | 4.05 s | 5.99 s | 25 |
| Halo 2 | kills you | Brute / Knight | Brute Plasma Rifle (AI) | 0.96 s | 1.60 s | 1.82 s | 16 |
| Halo 3 | you kill | Elite | Assault Rifle | 1.90 s | 2.40 s | 2.26 s | 25 |
| Halo 3 | you kill | Elite | Plasma Rifle | 4.76 s | 7.52 s | 3.70 s | 31 |
| Halo 3 | you kill | Elite | Battle Rifle | 3.31 s | 4.13 s | 3.70 s | 31 |
| Halo 3 | kills you | Elite | Plasma Rifle (AI) | 3.10 s | 3.32 s | 1.69 s | 13 |
| Halo 3 | you kill | Brute / Knight | Assault Rifle | 2.70 s | 4.40 s | 4.88 s | 45 |
| Halo 3 | you kill | Brute / Knight | Plasma Rifle | 2.16 s | 3.71 s | 5.07 s | 32 |
| Halo 3 | you kill | Brute / Knight | Battle Rifle | 3.03 s | 4.34 s | 5.99 s | 34 |
| Halo 3 | kills you | Brute / Knight | Spiker (AI) | 0.88 s | 3.10 s | 1.82 s | 10 |
| Halo 3: ODST | you kill | Brute / Knight | Silenced SMG | 3.07 s | 3.60 s | 4.88 s | 55 |
| Halo 3: ODST | you kill | Brute / Knight | Plasma Rifle | 2.16 s | 3.60 s | 5.07 s | 31 |
| Halo 3: ODST | you kill | Brute / Knight | Magnum (automag) | 9.22 s | 10.83 s | 5.99 s | 55 |
| Halo 3: ODST | kills you | Brute / Knight | Spiker (AI) | 6.70 s | 3.10 s | 1.82 s | 10 |
| Halo Reach | you kill | Elite | Assault Rifle | 2.70 s | 2.20 s | 2.26 s | 23 |
| Halo Reach | you kill | Elite | Plasma Repeater | 6.11 s | 4.75 s | 3.70 s | 22 |
| Halo Reach | you kill | Elite | DMR | 3.00 s | 2.67 s | 3.70 s | 9 |
| Halo Reach | kills you | Elite | Plasma Rifle | 1.57 s | 1.57 s | 1.69 s | 10 |
| Halo Reach | you kill | Brute / Knight | Assault Rifle | 5.87 s | 4.96 s | 4.88 s | 34 |
| Halo Reach | you kill | Brute / Knight | Plasma Repeater | 9.77 s | 8.23 s | 5.07 s | 33 |
| Halo Reach | you kill | Brute / Knight | DMR | 4.67 s | 4.00 s | 5.99 s | 13 |
| Halo Reach | kills you | Brute / Knight | Spike Rifle | 1.88 s | 1.88 s | 1.82 s | 11 |
| Halo 4 | you kill | Elite | Assault Rifle | 2.50 s | 2.50 s | 2.26 s | 26 |
| Halo 4 | you kill | Elite | Storm Rifle | 2.40 s | 2.40 s | 3.70 s | 25 |
| Halo 4 | you kill | Elite | Battle Rifle | 4.03 s | 4.03 s | 3.70 s | 34 |
| Halo 4 | kills you | Elite | Storm Rifle (AI) | 0.92 s | 0.92 s | 1.69 s | 12 |
| Halo 4 | you kill | Brute / Knight | Assault Rifle | 6.37 s | 5.15 s | 4.88 s | 35 |
| Halo 4 | you kill | Brute / Knight | Storm Rifle | 6.80 s | 5.58 s | 5.07 s | 33 |
| Halo 4 | you kill | Brute / Knight | Battle Rifle | 8.57 s | 6.98 s | 5.99 s | 45 |
| Halo 4 | kills you | Brute / Knight | Suppressor (AI) | 1.87 s | 2.00 s | 1.82 s | 31 |

Average distance from the target: before x1.49, after x1.27 (geometric; 1.00 = every row exactly on target).

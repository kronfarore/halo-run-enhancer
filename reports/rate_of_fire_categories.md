# Rate-of-fire categorisation

Vanilla values read off the shipped `weap` tags (block Barrels; Triggers in Halo 1);
cards read out of `halo.json`. The category is DERIVED from the numbers, not
hand-assigned, so this table checks the data rather than restating it.

| rule | meaning |
|---|---|
| `Shots Per Fire > 1` | **BURST** — one trigger pull sends several rounds. `Rounds Per Second` is the cadence inside the burst; `Fire Recovery Time` the gap between bursts. |
| `Fire Recovery Time > 0` | **RECOVERY-GATED** — one round per pull, and how fast you can pull is `Fire Recovery Time`. `Rounds Per Second` only bites once `Shots Per Fire` is raised above 1. |
| otherwise | **AUTOMATIC** — `Rounds Per Second` is the real rate, ramping to its Max while held. `Fire Recovery Time` ships at 0: no input cooldown. |

Every weapon carries **both** cards — **More Shooting** (Rounds Per Second + Shots
Per Fire) and **Fire Recovery Time** (the cooldown on your trigger input, which is
its own setting rather than the rate itself). Halo 1's `weap` plugin has neither
Shots Per Fire nor Fire Recovery Time, so there More Shooting is Rounds Per Second
only and there is no recovery card at all.

Values marked † ship as **0 as a placeholder** — Halo 2 parks Rounds Per Second at 0
on the weapons Halo 3 ships at 30, and Shots Per Fire is 0 on automatic weapons. The
card carries `zero_is` (30 and 1), shown in brackets, so the number displayed and the
number an operator works on are both the one the field stands for, instead of a 0
that makes every multiply a no-op.

| weapon | game | brl | RPS | RPS max | SPF | SPF max | Fire Recov | category | More Shooting writes | Fire Recovery card |
|---|---|--:|--:|--:|--:|--:|--:|---|---|---|
| Assault Rifle | H1 | 0 | 15 | 15 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Assault Rifle | H3 | 0 | 10 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Assault Rifle | ODST | 0 | 10 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Pistol | H1 | 0 | 3.5 | 3.5 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Pistol | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 0.1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Pistol | H3 | 0 | 30 | 30 | 1 | 1 | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Pistol | ODST | 0 | 30 | 30 | 1 | 1 | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Pistol | H2 | 1 | 0† (30) | 0† (30) | 1 | 1 | 0.1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Pistol | H3 | 1 | 30 | 30 | 1 | 1 | 0.1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Pistol | ODST | 1 | 30 | 30 | 1 | 1 | 0.1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Rifle | H1 | 0 | 7 | 10 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Plasma Rifle | H2 | 0 | 6 | 9 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Rifle | H3 | 0 | 6 | 9 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Rifle | ODST | 0 | 6 | 9 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Needler | H1 | 0 | 3 | 10 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Needler | H2 | 0 | 8 | 8 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Needler | H3 | 0 | 7 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Needler | ODST | 0 | 7 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Sniper Rifle | H1 | 0 | 2 | 2 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Sniper Rifle | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 0.5 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Sniper Rifle | H3 | 0 | 30 | 30 | 1 | 1 | 0.7 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Sniper Rifle | ODST | 0 | 30 | 30 | 1 | 1 | 0.7 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Rocket Launcher | H1 | 0 | 0.5 | 0.5 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Rocket Launcher | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 0.8 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Rocket Launcher | H3 | 0 | 30 | 30 | 1 | 1 | 0.8 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Rocket Launcher | ODST | 0 | 30 | 30 | 1 | 1 | 0.8 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Shotgun | H1 | 0 | 1 | 1 | - | - | - | **AUTOMATIC** | RPS, RPS max | — |
| Shotgun | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Shotgun | H3 | 0 | 30 | 30 | 1 | 1 | 1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Shotgun | ODST | 0 | 30 | 30 | 1 | 1 | 1 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| SMG | H2 | 0 | 15 | 15 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| SMG | H3 | 0 | 15 | 15 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| SMG | ODST | 0 | 15 | 15 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Brute Plasma Rifle | H2 | 0 | 8 | 11 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Battle Rifle | H2 | 0 | 15 | 15 | 3 | 3 | 0.26 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Battle Rifle | H3 | 0 | 15 | 15 | 3 | 3 | 0.28 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Battle Rifle | ODST | 0 | 15 | 15 | 3 | 3 | 0.28 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Brute Shot | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 0.3 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Brute Shot | H3 | 0 | 30 | 30 | 1 | 1 | 0.3 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Brute Shot | ODST | 0 | 30 | 30 | 1 | 1 | 0.3 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Beam Rifle | H2 | 0 | 0† (30) | 0† (30) | 1 | 1 | 0.25 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Beam Rifle | H3 | 0 | 30 | 30 | 1 | 1 | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Beam Rifle | ODST | 0 | 30 | 30 | 1 | 1 | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Covenant Carbine | H2 | 0 | 15 | 15 | 2 | 2 | 0.35 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Covenant Carbine | H3 | 0 | 30 | 30 | 1 | 1 | 0.17 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Covenant Carbine | ODST | 0 | 30 | 30 | 1 | 1 | 0.17 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Flak Cannon | H2 | 0 | 0† (30) | 0† (30) | 0† (1) | 0† (1) | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Flak Cannon | H3 | 0 | 30 | 30 | 0† (1) | 0† (1) | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Flak Cannon | ODST | 0 | 30 | 30 | 0† (1) | 0† (1) | 0.4 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Sentinel Beam | H2 | 0 | 30 | 30 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Sentinel Beam | H3 | 0 | 30 | 30 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Sentinel Beam | ODST | 0 | 30 | 30 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Mauler | H3 | 0 | 30 | 30 | 1 | 1 | 0.75 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Mauler | ODST | 0 | 30 | 30 | 1 | 1 | 0.75 | **RECOVERY-GATED** | RPS, RPS max, SPF, SPF max | yes |
| Spike Rifle | H3 | 0 | 8 | 8 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Spike Rifle | ODST | 0 | 8 | 8 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Spartan Laser | H3 | 1 | 30 | 30 | 5 | 5 | 0 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Spartan Laser | ODST | 1 | 30 | 30 | 5 | 5 | 0 | **BURST** | RPS, RPS max, SPF, SPF max | yes |
| Flamethrower | H3 | 0 | 15 | 15 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Flamethrower | ODST | 0 | 15 | 15 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Machine Gun | H3 | 0 | 5 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Machine Gun | ODST | 0 | 5 | 10 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Cannon | H3 | 0 | 7 | 13 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |
| Plasma Cannon | ODST | 0 | 7 | 13 | 0† (1) | 0† (1) | 0 | **AUTOMATIC** | RPS, RPS max, SPF, SPF max | yes |

## Consistency check

Every weapon carries both cards with exactly the right fields, and every
placeholder 0 carries a `zero_is`, in all 64 weapon/game combinations above.

## Weapons that change behaviour between games

- **Pistol** — H1: AUTOMATIC, H2: RECOVERY-GATED, H3: RECOVERY-GATED, ODST: RECOVERY-GATED
- **Sniper Rifle** — H1: AUTOMATIC, H2: RECOVERY-GATED, H3: RECOVERY-GATED, ODST: RECOVERY-GATED
- **Rocket Launcher** — H1: AUTOMATIC, H2: RECOVERY-GATED, H3: RECOVERY-GATED, ODST: RECOVERY-GATED
- **Shotgun** — H1: AUTOMATIC, H2: RECOVERY-GATED, H3: RECOVERY-GATED, ODST: RECOVERY-GATED
- **Covenant Carbine** — H2: BURST, H3: RECOVERY-GATED, ODST: RECOVERY-GATED

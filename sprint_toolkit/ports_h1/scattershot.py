r"""Scattershot (Halo 4, wave C5): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=30, wave='C5', name='Scattershot', source='Halo 4',
    messages=(93, 94), icon=50, reticle=39, label='ss', teach_from='sg',
    sound_dir='sound\\weapons\\scattershot_port', weapon_dir='weapons\\scattershot',
    yardstick={
        # step 4a (user, 2026-10-15; h3_weapon_values --kit h4 storm_spread_gun / storm_shotgun /
        # storm_energy_sword + the shard export + h1_role_compare.py scattershot)
        'pick': 'Shotgun',
        'reason': ("user, step 4a 2026-10-15: Halo 4's shotgun is the same family (bullet_slow pellets, "
                   "shell-by-shell magazine, strike_melee): H1 value = H1 shotgun x Scattershot / H4 "
                   "shotgun; keeps Halo 4's relation (144 vs 157.5 dps -> 295 vs 322). The sword ratio "
                   "maps damage only (87 dps). Kept Halo 4's own in BOTH versions (no counterpart): the "
                   "shard's speed + life (75 -> 10 wu/s, timer 0.15-0.5 s from the muzzle = dies at "
                   "~3.2-6.7 wu; the ratio's 22 wu/s would crawl), the ricochet responses, and the SUPER "
                   "DETONATION (user: 'port it'): 6 stuck shards -> 250 (Halo 4's attached super "
                   "detonation), through h1_supercombine_count's per-projectile count 6"),
        # Halo 4 (H4EK 2026-10-15): the 6 shards are the BARREL's (projectiles per shot 6, error 4 -> 7
        # deg, distribution point; the shard has NO conical spread -- unlike the Mauler / Boltshot),
        # 12 a shard bullet_slow, no falloff (flag 3 off; air damage range inert), recovery 0.5 s,
        # 5 (15 / 20) shell by shell (FP enter 14, continue_empty 21, chamber 39 fr), aim mode 6/7
        # 12/6.5, strike_melee 70. Shard flags 0x20020805: oriented along velocity, detonation max
        # time if attached, AI minor tracking threat, disable instantaneous first tick, no super
        # combine across bursts. Responses: hard metal / terrain fizzle, bounce 90-95 % at 0-75/85
        # deg (perp friction 0.7, noise 4); energy_shield_thick_cov bounce (noise 20); energy_shield
        # _thin impact (detonate); default_material attach, bounce 50 % under 55 deg never against
        # units; liquids / fences / plants overpenetrate. Super: 6 within 0.1 s; 40 (10 lower) area
        # / 250 (35 lower) attached, high explosive explosion_small, radius 0.375 -> 1.25.
        # H4 shotgun: 15 x 10.5 (lower 3 over 1.5 -> 3.75), 5 x 3 grid 3 deg, 1.0 s, 6 (18 / 24),
        # 480 wu/s, range 6.5, aim 6/5.5 12/5.5, FP enter 14 / continue 16 / chamber 34.
        # H1 shotgun: 15 x 18..25 (lower 8 over 1.5 -> 3), 1/s, 12 (24 / 60), 0.4 s a shell, error
        # 10, 140 -> 100 wu/s, range 40, aim 6/15 12/15, melee 55.
        # DEFAULT = Halo 4's own; these are the BALANCED rows (shotgun ratio):
        'balanced': {
            'pellets': 6,                    # 15 x 6/15
            'damage': 24.57,                 # 21.5 x 12/10.5 (upper 18..25 -> 20.57..28.57)
            'falloff': None,                 # Halo 4 has none (lower = upper)
            'fire_recovery_s': 0.5,          # 1.0 x 0.5/1.0
            'magazine': 10,                  # 12 x 5/6
            'rounds_total_initial': 20,      # 24 x 15/18
            'rounds_total_maximum': 50,      # 60 x 20/24
            'shell_s': 0.525,                # 0.4 x 21/16, shell by shell (both)
            'error_deg': (13.3, 23.3),       # 10 x 4/3, 10 x 7/3 (random cone both)
            'velocity': (75.0, 10.0),        # Halo 4's own (ratio degenerate)
            'timer': (0.15, 0.5),            # Halo 4's own
            'aim': (6.0, 19.1, 12.0, 17.7),  # 6 x 6/6, 15 x 7/5.5; 12 x 12/12, 15 x 6.5/5.5
            'melee': 'x1',                   # strike_melee both: 55
            'super': (6, 250.0)},            # Halo 4's own (no shotgun counterpart)
        'measured': 'h1_role_compare.py scattershot',
        'not_reproduced': ("the deceleration 75 -> 10 over 2-3 wu (Halo 1's velocity model: check in "
                           "4b), 'detonation max time if attached' (Halo 1's timer runs on), the super "
                           "detonation's 0.1 s window (Halo 1 counts stuck shards only), Halo 4's finer "
                           "material split folded onto Halo 1's 33"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun',
            'provisional': 'Shotgun',
            'alternatives': ['Energy Blade'],
            'direct': None,
            'peers': ['Shotgun', 'Energy Blade', 'Flamethrower'],
            'why': 'magazine 5, 6 projectiles per shot, close range',
            'lacks': 'ricocheting shards'}},
    # step 11: the source game's ai\generic entry (23 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun'},
)

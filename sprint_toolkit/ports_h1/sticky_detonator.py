r"""Sticky Detonator (Halo 4, wave C8): IN PROGRESS -- step 4a decided (user, 2026-10-16); the port
sections (model / retarget / pickable / sounds / catalog / test) follow.

HALO 4 (H4EK 2026-10-16, h3_weapon_values --kit h4 + the exports): the SOURCE is the campaign tag
`storm_sticky_detonator_pve` (user, over the MP tag). The two weapons are identical but for the
projectile (and abandonment 10 vs 12 s, the pickup sound): MP 10 -> 15 wu/s, burst 75..240
explosion_large (falloff exponent 6.5) over 0.4 -> 2.5, attached the same + accel 2.5; _pve 24 -> 10
wu/s, burst 75..500 explosion_small (exponent 1.5) over 0.4 -> 2.5, attached 50..500 over 0.4 -> 2.0, no
super attached damage, no holiday 'celebration' attachment. Trigger `double-latch-tether`: the press
fires, the NEXT press detonates the charge (stuck or in flight; `tether transition to linked` 0.3 s,
`max latch time to arm` 0.1 s); `max latch time to detonate` 30 s = the fallback after sticking.
Responses (`material response`, the table Halo 4 reads): default_material ATTACH (everything),
energy_shield_thick / _invulnerable BOUNCE -> the 'after first bounce' timer 0..1e-6 bursts it at once,
liquid overpenetrate. 1 loaded / 4 / 6, reloads 1 (FP reload_empty 58, reload_full 51), recovery 1.0 s,
error 0.15 / 0 -> 0.4, aim 4/15 8/15, gravity 0.25, range 20, impact 5 `collision` (accel 0.5),
strike_melee. Its ai\generic: none in any Halo 4 map (phase 0).

THE APPROXIMATION (user, step 4a): A = STICK + FUSE -- the Plasma Launcher's sticky recipe (attach on
every material, Jackal shields reflect), the fuse 0.5 s once at rest (stuck = at rest; Halo 4's fastest
detonation ~ arm 0.1 + tether 0.3 s); the FREE burst only (Halo 1 deals attached damage at the stick,
B6). Not reproduced: choosing when it bursts (trap a doorway, wait for a group), the mid-air burst,
the 30 s wait, the stuck burst's own 2.0 wu radius."""
from ._common import reserved

PORT = reserved(
    order=33, wave='C8', name='Sticky Detonator', source='Halo 4',
    messages=(99, 100), icon=53, reticle=42, label='sd', teach_from='hp',
    sound_dir='sound\\weapons\\sticky_detonator_port', weapon_dir='weapons\\sticky detonator',
    yardstick={
        # step 4a (user, 2026-10-16; h3_weapon_values --kit h4 storm_sticky_detonator(_pve) /
        # storm_rocket_launcher / storm_fuel_rod_cannon + the projectile / damage exports + h1_role_compare
        # sticky_detonator). Halo 4: rocket 200 impact + 240 explosion_large over 0.9 -> 2.5, 0.8 s, 2 / 4 /
        # 6, 116 fr, 10 -> 20 wu/s, gravity 0.02, 175, aim 5/60 10/25; fuel rod 100 + 60 over 0.5 ->
        # 2.25, 0.4 s, 5 / 15 / 20, 90 fr; plasma grenade free 250 over 0.3 -> 1.45 (25 lower), attached
        # 350 (35 lower), fuse 0.9-0.95 at rest. Halo 1: rocket 315 over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8,
        # 125 fr, 12 -> 10, range 128, aim 0/35 12/35; plasma grenade 120 + attached 120 over 0.5 -> 2.0,
        # fuse 2.0 at rest; restored fuel rod 75 over 0.5 -> 1.5 (Hunters immune).
        'pick': 'Plasma Grenade',
        'reason': ("user, step 4a 2026-10-16: the PLASMA GRENADE by the STUCK kill (the sticky family; "
                   "the Plasma Launcher's precedent), its holes (rate, magazine, reload, flight, range, "
                   "aim, melee) by the ROCKET ratio (the GL's precedent), the grenade's table in both "
                   "versions. Halo 1 stuck 240 (120 area + 120 attached) vs Halo 4 attached 350: 500 x "
                   "240/350 = 342.9 as the burst alone (Halo 1's attached damage lands at the stick). "
                   "Fuse 0.5 s in both (user)."),
        # DEFAULT = Halo 4's own; these are the BALANCED rows:
        'balanced': {
            'damage': 342.9,                 # 500 x 240/350 (the stuck kill)
            'radius': (0.667, 3.45),         # 0.4 x 0.5/0.3, 2.5 x 2.0/1.45
            'impact': 0.0,                   # the grenade has none (Halo 4's 2 -> 5 x 0/2)
            'fuse_s': 0.5,                   # user (both versions)
            'fire_recovery_s': 2.5,          # RL: 1.0 x 2.0/0.8
            'magazine': 1,                   # RL: 1 x 2/2
            'rounds_total_initial': 4,       # RL: 4 x 4/4
            'rounds_total_maximum': 8,       # RL: 6 x 8/6
            'reload_s': 4.1667 * 58 / 116,   # RL: 125 fr x 58/116
            'velocity': (28.8, 5.0),         # RL: 24 x 12/10, 10 x 10/20
            'range': 14.6,                   # RL: 128 x 20/175
            'aim': (0.0, 8.75, 9.6, 21.0),   # RL: 0 x 4/5, 35 x 15/60; 12 x 8/10, 35 x 15/25
            'gravity': 0.25,                 # the rocket's 0 vs 0.02: near-zero, no ratio -> Halo 4's
            'error_deg': (0.15, 0.0, 0.4),   # the rocket's 0 / 0 degenerate -> Halo 4's own
            'melee': 55.0},                  # strike_melee both -> the rocket's 55 (x1)
        # Time to kill (h1_role_compare sticky_detonator, direct hits): default 500+5 (PG table) 505 dps
        # column -- one charge for every Elite on legendary, Hunter 2-3; balanced 342.9 at 0.4/s 137 --
        # one charge every Elite, Hunter 3 (normal) / 4 (legendary); RL 158, PG stuck 240 (1/s), GL port
        # 410, PL tap 186, Brute Shot 243
        'measured': 'h1_role_compare.py sticky_detonator',
        'not_reproduced': ("the second-press detonation (stick + a 0.5 s fuse), the mid-air burst, the "
                           "30 s fallback, the stuck burst's 2.0 wu radius (the free 2.5 everywhere)"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\storm_sticky_detonator\\storm_sticky_detonator_pve',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Plasma Grenade', 'Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': '1-round magazine, arcing sticky explosive (gravity 0.25)',
            'lacks': 'remote detonation (approximated: stick + a 0.5 s fuse), the mid-air burst'}},
    # step 11: NO source entry found
    firing_profile={'mode': 'same_game', 'donor_weapon': None, 'why': 'no ai\\generic entry for objects\\weapons\\pistol\\storm_sticky_detonator\\storm_sticky_detonator found in Halo 4 maps -- pick a Halo 1 stand-in'},
)

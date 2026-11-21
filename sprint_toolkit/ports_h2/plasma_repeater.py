r"""Plasma Repeater into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 8,
    'wave': 'B3',
    'name': 'Plasma Repeater',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
    'reservations': {
        'message_prefix': 'rp2',
        'glyph': 0xE145,
        'weapon_dir': 'objects\\weapons\\rifle\\plasma_repeater',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\plasma_repeater',
        'fp_graph': 'weapons\\rifle\\fp_plasma_repeater\\fp_plasma_repeater',
        'hud': 'ui\\hud\\plasma_repeater',
        'hud_bitmap_prefix': 'plasma_repeater_',
        'sound_dir': 'sound\\weapons\\plasma_repeater_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\plasma_rifle\\plasma_rifle', 'message_prefix': 'pr',
              'why': 'spew heat automatic + battery + rate ramp; clear dual wield. Alt: brute_plasma_rifle (bpr)'},
    'yardstick': {
        # step 4a, user 2026-11-21: reports/h2_plasma_repeater_4a.md; balance_Plasma_Repeater_HaloReach_to_Halo2.json
        # (balance_port.py "Plasma Repeater" "Plasma Rifle" "Halo Reach" "Halo 2")
        'pick': 'Plasma Rifle',
        'reason': ("user 2026-11-21: the Plasma Rifle -- Halo 2's carries Reach's Plasma Rifle tag numbers (rate 6 -> 9 / "
                   "0.8 s, heat 0.15, loss 0.8525 / 0.35, recovery 0.1, 6-10, battery 0.0025, range 40, magnetism 9 / "
                   "18), so the ratio is x1 on every heat, rate, damage, battery and range row. Balanced = Reach's own "
                   "but bolt speed 25 -> 35 x0.56 = 14 -> 19.6, single-wield error 0.4-3 x0.19 / 0.21 = 0.077-0.64 "
                   "(min 0), autoaim angle 5 x1.2 = 6. HEAT, approximation A (user): the OVERHEAT stands in for "
                   "Reach's manual vent (no dll vent: user), the rate falls 15 -> 3 over 1.6 s HELD (fitted: every "
                   "shot within 0.1 s of Reach's heat^1.5 curve to full heat), heat 0.0915 a round with loss 0.25 "
                   "(Reach's cold loss) -> overheats on round 15 at 1.48 s (Reach full on 14-15), overheated loss "
                   "0.36 to recovery 0.1 = Reach's 2.5 s vent, deceleration 3.6 s (the meter drains with the rate). "
                   "MATERIALS (user): Halo 2's own plasma_fast group, Reach's group by name. Melee Halo 2's "
                   "strike_melee. Legendary: Elite 24 / 4.53 s, Brute 39 / 8.52 s, Grunt 7 / 0.45 s, Jackal 10 / "
                   "0.73 s (Plasma Rifle 4.76 / 10.87 / 0.46 / 0.71). Halo 2's per-tick fire rule is unmeasured: "
                   "probe it on boot 1 before any re-fit"),
        'heat': {'rate': (15.0, 3.0), 'accel': 1.6, 'decel': 3.6, 'heat_per_round': 0.0915, 'heat_loss': 0.25,
                 'overheated_loss': 0.36, 'recovery': 0.1, 'overheated_threshold': 1.0},
        'candidates': {
            'provisional': 'Plasma Rifle',
            'alternatives': ['Plasma Pistol'],
            'direct': 'Elite: carries the Plasma Rifle in both (= the provisional)',
            'peers': ['Plasma Rifle', 'Brute Plasma Rifle', 'SMG', 'Needler'],
            'why': "heat automatic plasma + battery, rate 15 -> 3 with heat (H1 pick). H2's trigger RAMPS over held time (6 -> 9) like Halo 1: H1's approximation B carries over",
            'lacks': ("the manual vent (and venting part-way), a rate tied to HEAT (Halo 2: to the held time), firing "
                      "on at 3/s when hot (Halo 2 overheats instead), Reach's slow hot cooling (0.06/s; one loss 0.25)"),
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

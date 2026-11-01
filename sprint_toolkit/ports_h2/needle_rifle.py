r"""Needle Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 7,
    'wave': 'B2',
    'name': 'Needle Rifle',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
    'reservations': {
        'message_prefix': 'nr2',
        'glyph': 0xE144,
        'weapon_dir': 'objects\\weapons\\rifle\\needle_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\needle_rifle',
        'fp_graph': 'weapons\\rifle\\fp_needle_rifle\\fp_needle_rifle',
        'hud': 'ui\\hud\\needle_rifle',
        'hud_bitmap_prefix': 'needle_rifle_',
        'sound_dir': 'sound\\weapons\\needle_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine', 'message_prefix': 'cc',
              'why': 'Covenant semi-auto magazine, latch-zoom 2x, 1/1/2; projectile from the needler (supercombine)'},
    'yardstick': {
        # step 4a, user 2026-11-01: reports/h2_needle_rifle_4a.md; balance_Needle_Rifle_HaloReach_to_Halo2.json
        # (balance_port.py "Needle Rifle" "Needler" "Halo Reach" "Halo 2")
        'pick': 'Needler',
        'reason': ("user 2026-11-01: the Needler for every needle-shaped value; Reach has no Carbine and the chain "
                   "through Halo 3 breaks on the needle rows, so the Carbine (the role twin) answers ACCURACY only: "
                   "the Needler's cone means nothing on a homing shot. Balanced: needle 3 on impact (Halo 2's real "
                   "1 + 2; the tool's 2 reads the detonation alone), 4/s + recovery 0.25, 26 / 78 / 105, reload "
                   "Reach's 82 fr (the ratio's 119 is nearly double the Carbine), error 0.3-1.0 min 0, 2x, velocity "
                   "818, range 231 / air 40, autoaim 1.97 / 19.2, magnetism 2.81 / 19.2, count 3 (Reach's; the "
                   "ratio's 3.5 is no count), timer 1.5-2.1 s (stock x 6/2 shot gaps: the third needle must "
                   "land inside it), minimum velocity 3, attached 400 + area 50 (the Needler's), radius 0.2-0.5, "
                   "melee Halo 2's strike_melee. Legendary: 3 needles = any minor at 0.50 s; needles alone "
                   "Elite 67 / 21.4 s (Carbine 2.57 s)"),
        'supercombine': ("no dll patch: Halo 2's projectile carries `super det. projectile count` (needler 7) and its "
                         "own super detonation tags; the needler is the only stock user, so boot 1 proves a 3"),
        'candidates': {
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': 'none',
            'peers': ['Covenant Carbine', 'Needler', 'Battle Rifle'],
            'why': '21-round semi-auto 4/s, 2x zoom, supercombining needle (H1 pick). The Carbine is its H2 role twin but Reach has none and there is no bridge',
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '05a_deltaapproach', 'dervish_level': '04b_floodlab'},
    'residency': {'levels': 'all', 'placements': False},
}

r"""Storm Rifle into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 13,
    'wave': 'C1',
    'name': 'Storm Rifle',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine',
    'reservations': {
        'message_prefix': 'st2',
        'glyph': 0xE14A,
        'weapon_dir': 'objects\\weapons\\rifle\\storm_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\storm_rifle',
        'fp_graph': 'weapons\\rifle\\fp_storm_rifle\\fp_storm_rifle',
        'hud': 'ui\\hud\\storm_rifle',
        'hud_bitmap_prefix': 'storm_rifle_',
        'sound_dir': 'sound\\weapons\\storm_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\plasma_rifle\\plasma_rifle', 'message_prefix': 'pr',
              'why': 'heat automatic plasma + battery; clear dual wield'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Plasma Pistol',
            'alternatives': ['Needler', 'Covenant Carbine (H4 storm_covenant_carbine)', 'Sentinel Beam'],
            'direct': "none (role = H2 Plasma Rifle, but H4 has none: the plasma-rifle family row would just take H2's numbers -- degenerate)",
            'peers': ['Plasma Rifle', 'Brute Plasma Rifle', 'SMG', 'Needler'],
            'why': 'heat automatic plasma 10/s, heat 0.09/round, battery (H1 pick)',
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

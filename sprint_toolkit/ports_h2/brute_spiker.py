r"""Spike Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 3,
    'wave': 'A3',
    'name': 'Spike Rifle',
    'source': 'Halo 3',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
    'reservations': {
        'message_prefix': 'spk2',
        'glyph': 0xE140,
        'weapon_dir': 'objects\\weapons\\rifle\\spike_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\spike_rifle',
        'fp_graph': 'weapons\\rifle\\fp_spike_rifle\\fp_spike_rifle',
        'hud': 'ui\\hud\\brute_spiker',
        'hud_bitmap_prefix': 'brute_spiker_',
        'sound_dir': 'sound\\weapons\\brute_spiker_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine 1/1/1 AND dual-wieldable -- keep the flag'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'SMG',
            'alternatives': ['Needler', 'Plasma Rifle'],
            'direct': 'none (H2 Brutes never carry a spiker)',
            'peers': ['SMG', 'Needler', 'Brute Plasma Rifle', 'Plasma Rifle'],
            'why': 'magazine 40 auto 8/s, slow arcing projectile, dual-wieldable like the SMG (both dual -> no x1.5 carry fudge); the Brute Plasma Rifle has NO H3 card, so cannot be the yardstick',
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '08a_deltacliffs', 'dervish_level': '04b_floodlab'},   # parallel pair 1
    'residency': {'levels': 'all', 'placements': False},
}

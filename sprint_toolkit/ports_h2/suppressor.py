r"""Suppressor into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 14,
    'wave': 'C2',
    'name': 'Suppressor',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg',
    'reservations': {
        'message_prefix': 'su2',
        'glyph': 0xE14B,
        'weapon_dir': 'objects\\weapons\\rifle\\suppressor',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\suppressor',
        'fp_graph': 'weapons\\rifle\\fp_suppressor\\fp_suppressor',
        'hud': 'ui\\hud\\suppressor',
        'hud_bitmap_prefix': 'suppressor_',
        'sound_dir': 'sound\\weapons\\suppressor_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine 1/1/1 (48-round); clear dual wield'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'SMG via the SAW\'s chain (--hop "Assault Rifle:Halo 4>Halo 3" --hop "SMG:Halo 3>Halo 2")',
            'alternatives': ['Needler', 'Sentinel Beam'],
            'direct': 'none (H4 has no SMG)',
            'peers': ['SMG', 'Plasma Rifle', 'Needler', 'SAW (port)'],
            'why': "magazine 48 auto 15/s, decelerating hardlight projectile -- the Forerunner SMG; the SAW's two-hop is the precedent (H1 pick AR has no H2 counterpart)",
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

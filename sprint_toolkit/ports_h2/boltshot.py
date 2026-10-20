r"""Boltshot into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 15,
    'wave': 'C3',
    'name': 'Boltshot',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol',
    'reservations': {
        'message_prefix': 'bsh2',
        'glyph': 0xE14C,
        'weapon_dir': 'objects\\weapons\\pistol\\boltshot',
        'effects_dir': 'effects\\objects\\weapons\\pistol\\boltshot',
        'fp_graph': 'weapons\\pistol\\fp_boltshot\\fp_boltshot',
        'hud': 'ui\\hud\\boltshot',
        'hud_bitmap_prefix': 'boltshot_',
        'sound_dir': 'sound\\weapons\\boltshot_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\pistol\\plasma_pistol\\plasma_pistol', 'message_prefix': 'pp',
              'why': 'latch-autofire 0.6 s + 2 barrels = the trigger; ADD a magazine element (10/40) -- the one block insert; clear dual wield. Alt: magnum (mp) + a 2nd barrel'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Pistol (bolt) + Shotgun (charged blast)',
            'alternatives': ['Plasma Pistol'],
            'direct': 'none',
            'peers': ['Magnum', 'Plasma Pistol', 'Shotgun', 'Mauler (port)'],
            'why': "magazine 10, latch-autofire 0.6 s charge -> 5-round blast: EXACTLY H2's plasma pistol trigger (latch-autofire 0.6 s, two barrels) (H1 pick)",
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

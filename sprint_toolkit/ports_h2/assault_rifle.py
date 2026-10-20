r"""Assault Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 1,
    'wave': 'A1',
    'name': 'Assault Rifle',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\assault_rifle\\assault_rifle',
    'reservations': {
        'message_prefix': 'ar2',
        'glyph': 0xE13E,
        'weapon_dir': 'objects\\weapons\\rifle\\assault_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\assault_rifle',
        'fp_graph': 'weapons\\rifle\\fp_assault_rifle\\fp_assault_rifle',
        'hud': 'ui\\hud\\assault_rifle',
        'hud_bitmap_prefix': 'assault_rifle_',
        'sound_dir': 'sound\\weapons\\assault_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine bullet 1/1/1, ammo HUD; clear can-be-dual-wielded. Alt: battle_rifle (br), two-handed non-dual'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'SMG',
            'alternatives': ['Battle Rifle', 'Plasma Rifle'],
            'direct': 'none (no AR in Halo 2; the family table maps the automatic rifle to the SMG)',
            'peers': ['SMG', 'Battle Rifle', 'Plasma Rifle', 'Brute Plasma Rifle', 'SAW (port)'],
            'why': 'magazine 32 full-auto bullet projectile (10/s) = the SMG role; the SMG is in H3 AND H2: ONE hop (balance_SMG_Halo3_to_Halo2.json exists). AR is not dual-wieldable: watch the carry (H2 SMG 240 vs H3 AR 384)',
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\assault_rifle\\assault_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

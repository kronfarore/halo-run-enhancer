r"""DMR into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 6,
    'wave': 'B1',
    'name': 'DMR',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\dmr\\dmr',
    'reservations': {
        'message_prefix': 'dmr2',
        'glyph': 0xE143,
        'weapon_dir': 'objects\\weapons\\rifle\\dmr',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\dmr',
        'fp_graph': 'weapons\\rifle\\fp_dmr\\fp_dmr',
        'hud': 'ui\\hud\\dmr',
        'hud_bitmap_prefix': 'dmr_',
        'sound_dir': 'sound\\weapons\\dmr_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle', 'message_prefix': 'br',
              'why': 'latch-zoom magazine instant bullet, 1 zoom level; burst -> single. Alt: sniper_rifle (sn)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Sniper Rifle',
            'alternatives': ['Battle Rifle via Halo 4 (--hop "DMR:Halo Reach>Halo 4" --hop "Battle Rifle:Halo 4>Halo 2"; carries H4\'s scale -- the user\'s call)', 'Pistol'],
            'direct': 'none',
            'peers': ['Battle Rifle', 'Magnum', 'Sniper Rifle', 'Covenant Carbine'],
            'why': "semi-auto 15, 3x zoom, near-instant (H1 pick Sniper). The BR is H2's mid-range precision rifle but Reach has no BR",
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

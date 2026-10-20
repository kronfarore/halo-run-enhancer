r"""LightRifle into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C4) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 16,
    'wave': 'C4',
    'name': 'LightRifle',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle',
    'reservations': {
        'message_prefix': 'lr2',
        'glyph': 0xE14D,
        'weapon_dir': 'objects\\weapons\\rifle\\light_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\light_rifle',
        'fp_graph': 'weapons\\rifle\\fp_light_rifle\\fp_light_rifle',
        'hud': 'ui\\hud\\lightrifle',
        'hud_bitmap_prefix': 'lightrifle_',
        'sound_dir': 'sound\\weapons\\lightrifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle', 'message_prefix': 'br',
              'why': 'latch-zoom 3-burst magazine 36; scoped mode: a 2nd barrel (or start from covenant_carbine, cc: 2 barrels under latch-zoom)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Battle Rifle (single hop: H4 storm_br <-> H2 battle_rifle)',
            'alternatives': ['Pistol (H1 pick)', 'Covenant Carbine', 'Sniper Rifle'],
            'direct': 'none',
            'peers': ['Battle Rifle', 'Covenant Carbine', 'Magnum', 'Sniper Rifle', 'DMR (port)'],
            'why': "magazine 36, 3x zoom, 3-round burst unscoped / one shot scoped: the BR's role, and the BR exists in both games. H2's latch-zoom has primary + secondary barrel indices like H4's -- the scoped mode H1 could not do may be native here (UNVERIFIED)",
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

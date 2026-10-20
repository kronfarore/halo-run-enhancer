r"""Focus Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B7) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 12,
    'wave': 'B7',
    'name': 'Focus Rifle',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
    'reservations': {
        'message_prefix': 'fo2',
        'glyph': 0xE149,
        'weapon_dir': 'objects\\weapons\\rifle\\focus_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\focus_rifle',
        'fp_graph': 'weapons\\rifle\\fp_focus_rifle\\fp_focus_rifle',
        'hud': 'ui\\hud\\focus_rifle',
        'hud_bitmap_prefix': 'focus_rifle_',
        'sound_dir': 'sound\\weapons\\focus_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\characters\\sentinel_aggressor\\weapons\\beam\\sentinel_aggressor_beam', 'message_prefix': 'sen_b',
              'why': "spew 30/s instant beam, heat + battery, 0 mags, beam HUD; add the beam rifle's 2 zoom levels. Alt: beam_rifle (be)"},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Plasma Rifle',
            'alternatives': ["Sentinel Beam via Halo 4 (Focus Rifle:Halo Reach>Halo 4, Sentinel Beam:Halo 4>Halo 2; H4's beam is AI-only)", 'Sniper Rifle', 'Plasma Pistol'],
            'direct': 'none',
            'peers': ['Sentinel Beam', 'Beam Rifle', 'Sniper Rifle'],
            'why': "continuous instant beam 30/s, heat 0.025/round + battery, 2 zooms 3.5-9.5 (= H2 Beam Rifle's range) (H1 pick Plasma Rifle). H2's pickable Sentinel Beam is the same mechanism but Reach has none",
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

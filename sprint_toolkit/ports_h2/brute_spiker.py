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
    'status': 'in progress',
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
        # step 4a, user 2026-10-21: the SMG; balance_Spike_Rifle_Halo3_to_Halo2.json
        # (balance_port.py "Spike Rifle" "Halo 3" "Halo 2" --hop "SMG:Halo 3>Halo 2");
        # TTK h2_spiker_ttk_4a.py h2_spiker_ttk_4a_variants.json
        'pick': 'SMG',
        'reason': ('user 2026-10-21: one hop, same role, both dual-wield; nearly every ratio x1: '
                   'balanced damage 8.55 (x0.95), rate 8, ammo 40 / 120 / 160, velocity 25 / 17.5, '
                   'spread 0 / 0.4-1.25, autoaim 6 / 12, magnetism 12 / 18, rider 0.75, dual wield '
                   'damage scale 0.667, dual error 0.25 / 0.75-1.5 (x1). Elite minor legendary TTK '
                   '2.12 s (default 2.00; H2 SMG 2.07, AR port 1.90, PR 4.76, BPR 4.60). '
                   'Alternatives: Plasma Rifle (spike 14 / 9.8, no ammo rows), Needler (no damage '
                   'row, magazine 63, contradictory rate ratios)'),
        # the user's picks beside the yardstick (2026-10-21):
        'melee': ('own clone of strike_melee x Halo 3 cut_melee 72 / strike_melee 70 '
                  '(20.57-61.71; the blades)'),
        'projectile': "Halo 3's own air gravity 0.2 (no SMG card row) AND minimum velocity 12 (user: "
                      "not the SMG rule's 0)",
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

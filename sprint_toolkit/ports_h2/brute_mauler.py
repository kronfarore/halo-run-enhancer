r"""Mauler into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A4) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 4,
    'wave': 'A4',
    'name': 'Mauler',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\pistol\\excavator\\excavator',
    'reservations': {
        'message_prefix': 'mau2',
        'glyph': 0xE141,
        'weapon_dir': 'objects\\weapons\\pistol\\excavator',
        'effects_dir': 'effects\\objects\\weapons\\pistol\\excavator',
        'fp_graph': 'weapons\\pistol\\fp_excavator\\fp_excavator',
        'hud': 'ui\\hud\\brute_mauler',
        'hud_bitmap_prefix': 'brute_mauler_',
        'sound_dir': 'sound\\weapons\\brute_mauler_port',
    },
    # step 4a (user, 2026-10-28): the H2 MAGNUM, not the stub's shotgun. The block shape decides:
    # pellets and the error cone are FIELDS (written onto any barrel), the dual structures are not
    # -- the shotgun has none (no dual HUD / messages / animations, two-handed, plus the shell
    # baggage Halo 1 stripped: 'every round must be chambered', weapon type 'shotgun'). The SMG
    # (the Spiker's) has them but spews and its FP graph carries the single-wield left-hand IK
    # (drop_ik). The magnum: latch, ONE magazine reloaded whole (rounds reloaded = loaded), one-
    # handed, 'can be dual wielded', a dual HUD, and fp_magnum has NO IK block (drop_ik n/a)
    'donor': {'weapon': 'objects\\weapons\\pistol\\magnum\\magnum', 'message_prefix': 'magnum',
              'why': ("latch, whole-magazine reload, one-handed, dual flag + dual HUD + dual lines, "
                      "fp_magnum has no left-hand IK; pellets / error = fields (the shotgun pellet's "
                      "numbers written on); user 4a 2026-10-28")},
    'yardstick': {
        # step 4a, user 2026-10-28: balance_Mauler_Halo3_to_Halo2.json (balance_port.py Mauler
        # "Halo 3" "Halo 2" --hop "Shotgun:Halo 3>Halo 2"); TTK: the session's mauler_ttk_4a
        # (h2_spiker_ttk_4a's method on the H2 shotgun's damage groups)
        'pick': 'Shotgun',
        'reason': ("user 2026-10-28: the same projectile family in Halo 3 (15-pellet 7.5 deg cone, "
                   "bullet_slow, distance falloff: 15 x 7 vs 15 x 10) -- the Pistol has no pellets, "
                   "cone or falloff (its rows degenerate: 1 x 3.73 at 5.3/s). Balanced: 10 pellets "
                   "(the H2 shotgun's 10 x 15/15) x 11.55 = 115.5 a shot (H2 shotgun 165 x 0.7), lower "
                   "2.5 over 6.25 -> 10 wu, recovery 0.75 s, magazine 10 / initial 20 / maximum 50 "
                   "(the ratio's 33 x1.5: the DUAL-WIELD CARRY RULE, the yardstick cannot be dual "
                   "wielded), the reload Halo 3's whole magazine (shell 0.4 = 0.4: x1), error 10-12 / "
                   "min 4 (both cones 7.5), velocity 120, range 10.67, autoaim 8 / 7.64, magnetism "
                   "40 / 1.27, dual wield damage scale 0.7 x 0.833 (the SMG's H3 -> H2, as the Spiker) "
                   "= 0.583. Legendary TTK (body, every pellet): Elite 2 shots 0.75 s, Brute 5 / 3.0 s "
                   "(H2 shotgun 1 / 4-3.0 s, magnum 1.80 / 6.2 s)"),
        'pellets': "user: 10 x 11.55 (the ratio's count), not Halo 3's 15 x 7.7",
        'dual': 'user: x1.5 carry (33 -> 50) + dual wield damage scale 0.583',
        'melee': ('own clone of strike_melee x Halo 3 cut_melee 72 / strike_melee 70 (20.57-61.71; '
                  "the blade -- the Spiker's rule)"),
        'candidates': {
            'provisional': 'Shotgun',
            'alternatives': ['Pistol'],
            'direct': 'none',
            'peers': ['Shotgun', 'Energy Blade', 'Magnum'],
            'why': 'magazine 5 latch, pellets, dual-wieldable one-hand shotgun (H1 pick)',
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\pistol\\excavator\\excavator', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '05b_deltatowers', 'dervish_level': '08a_deltacliffs'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}

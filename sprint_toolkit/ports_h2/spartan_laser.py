r"""Spartan Laser into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 2,
    'wave': 'A2',
    'name': 'Spartan Laser',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
    'reservations': {
        'message_prefix': 'spl2',
        'glyph': 0xE13F,
        'weapon_dir': 'objects\\weapons\\support_high\\spartan_laser',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\spartan_laser',
        'fp_graph': 'weapons\\support_high\\fp_spartan_laser\\fp_spartan_laser',
        'hud': 'ui\\hud\\spartan_laser',
        'hud_bitmap_prefix': 'spartan_laser_',
        'sound_dir': 'sound\\weapons\\spartan_laser_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle', 'message_prefix': 'be',
              'why': 'battery + heat, instant beam, two-handed, 0 mags; trigger latch -> Charge 2.5 s, zoom levels 2 -> 1. Alt: plasma_pistol (pp: 2 barrels + charge, one-hand)'},
    'yardstick': {
        # step 4a (user, 2026-10-28): reports/h2_spartan_laser_4a.md. Halo 3's laser: spew-charge
        # 2.5 s, 5 beam rounds of detonation 20 + AOE spike bump 94 = 570 a shot, group laser (=
        # explosion_large, Hunter armour x0.5), battery 5, heat 1 a shot, vent 2.25 s, 2.5x, range
        # 120, autoaim 1 / 25, magnetism 5 / 25, smash melee. Rocket ratio legs: direct hit H2 350
        # (impact 150 + blast 200) / H3 440 (240 + bump 200: the A8 rule, bumps on both sides)
        'pick': 'Rocket Launcher',
        'reason': "user, step 4a 2026-10-28: Halo 1's pick and reason hold -- Halo 3's laser group IS "
                  "the rocket's explosion_large and Halo 2 has the group; every ratio leg is a real "
                  "value in both games (the Beam Rifle / Sniper ratios shrink the range 500 -> 120 to "
                  "29 wu and break the heat; the Sentinel Beam has no charge / zoom leg). Charge x1 "
                  "(the rocket tags agree: recovery 0.8, reload 5.0; not the 112/116 animation ratio). "
                  "Hunter armour: 'Default keeps the original number, Balanced uses the balanced "
                  "formula' -> x0.5 both (H3 laser 0.5 x H2 rocket 1 / H3 rocket 1; Halo 1's port is "
                  "the same formula: H1 rocket hunter_armor 1.0 -> 0.5, no change)",
        'balanced': {'damage': 453.4,          # 570 x 350 / 440
                     'charge_s': 2.5, 'vent_s': 2.25, 'battery_shots': 5, 'range': 120.0,
                     'zoom': 2.5, 'aim': (1.0, 45.0, 5.0, 25.0),   # autoaim range 25 x 45 / 25
                     'hunter_armor': 0.5, 'melee': 'smash_melee (shared, x1)',
                     'ready_frames': 28.6},    # 31 x H2 RL 24 / H3 RL 26
        'candidates': {
            'provisional': 'Rocket Launcher',
            'alternatives': ['Beam Rifle', 'Sniper Rifle', 'Sentinel Beam'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Beam Rifle', 'Sniper Rifle', 'Flak Cannon'],
            'why': "spew-charge 2.5 s, battery, heat 1.0/shot, 2.5x zoom, instant beam (H1 pick RL: laser damage = explosion_large). H2 has no spew-charge: Charge (the scarab main gun's, 2.8 s) is the closest -- UNTESTED on a player weapon",
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03b_newmombasa', 'dervish_level': '06a_sentinelwalls'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}

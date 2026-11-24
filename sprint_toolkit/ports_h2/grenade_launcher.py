r"""Grenade Launcher into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B4, "Step 5", alone) -- IN PROGRESS
(2026-11-24).

The port: Reach's model, textures, Spartan + Elite FP animations and sounds on a clone of Halo 2's FUEL ROD
(flak_cannon: latch, magazine, an explosive shot and a SECOND, unused barrel), firing grenades built on the
BRUTE SHOT's grenade (ballistic AI aim, the 'after first bounce off any surface' fuse). The charged pair is the
plasma pistol's ONE trigger: latch-autofire, secondary action charge, secondary barrel 1.
"""

GL = r'objects\weapons\rifle\grenade_launcher'      # the source's folder (HREK) AND the port's (H2EK)
FC = r'objects\weapons\support_high\flak_cannon'    # the weapon donor (H2EK)
BS = r'objects\weapons\support_low\brute_shot'      # the projectile donor (H2EK)
FX = r'effects\objects\weapons\rifle\grenade_launcher'   # the reserved effects folder
R = 'reach:'                                        # an HREK path (reach_tags)
RM = R + GL + r'\grenade_launcher.render_model'
WP = GL + r'\grenade_launcher.weapon'
PJ = GL + r'\projectiles\grenade_launcher_grenade.projectile'          # barrel 0: the bouncing grenade
PJC = GL + r'\projectiles\grenade_launcher_tethered_grenade.projectile'  # barrel 1: the charged release
DM = GL + r'\damage_effects'

PORT = {
    'order': 9,
    'wave': 'B4',
    'name': 'Grenade Launcher',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
    'reservations': {
        'message_prefix': 'gl2',
        'glyph': 0xE146,
        'weapon_dir': 'objects\\weapons\\rifle\\grenade_launcher',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\grenade_launcher',
        'fp_graph': 'weapons\\rifle\\fp_grenade_launcher\\fp_grenade_launcher',
        'hud': 'ui\\hud\\grenade_launcher',
        'hud_bitmap_prefix': 'grenade_launcher_',
        'sound_dir': 'sound\\weapons\\grenade_launcher_port',
    },
    # The phase-0 proposal was the BRUTE SHOT (latch magazine, arcing explosive grenade, ballistic AI aim) under the
    # rule 'same block shape as the port (magazines, barrels) -- the expensive byte edit is a block insert'. The
    # charged pair (4a, user) needs TWO barrels; the Brute Shot has ONE, so the weapon is the FUEL ROD's (H2's
    # flak_cannon: latch, 1 magazine, explosive, weapon type undefined, no tracking, no world graph in its .model,
    # barrel 1 present and unused: secondary barrel -1). The Brute Shot keeps its part: its GRENADE is the
    # projectile template (ballistic AI aim, the fuse rule)
    'donor': {'weapon': FC + r'\flak_cannon', 'message_prefix': 'fc',
              'projectile': BS + r'\projectiles\grenade\grenade',
              'why': ("the charged pair needs two barrels: the Fuel Rod's weapon (latch, magazine 5 -> 1, a free barrel 1) "
                      "+ the Brute Shot's grenade (ballistic AI aim, 'after first bounce off any surface')")},
    'yardstick': {
        # step 4a, user 2026-11-24: reports/h2_grenade_launcher_4a.md (scratch gl4a_dump / gl4a_table / gl4a_ttk).
        # REACH (HREK, Halo 1's B4 reading): latch-tether, recovery 0.5 s, 1 / 8 / 16, reloads 1 (63 fr empty, 59
        # full), error 0.15 min, 0 -> 0.4, 12.5 -> 7.5 wu/s, gravity 0.7 / water 0.75, range 100, arming 0, minimum
        # velocity 0. IMPACT 25 `collision` (accel 0.5) + DETONATION 0..180 over 0.75 -> 2.25 (core 0.6,
        # `explosion_small`, accel 2); fuse 0.5 s 'after first bounce off any surface'; units > 5 wu/s detonate; world
        # 0-7 wu/s turn physical; world 75-90 deg at 7.5-14 wu/s detonates; else bounce, friction 0.42 / 0.42.
        # Release: 180 over 0.001 -> 1 (core 0.2, accel 3) + EMP 100 `emp` over 0.25 -> 2.5 (side effect emp).
        # Reach frag 0..160 over 0.675 -> 2.25, timer 0.6-0.65, arming 1.4, gravity 0.9, throw 10; Reach RL 200 +
        # 0..240 over 0.75 -> 2.5, 0.8 s, 2 / 4 / 8, 116 fr, 8 -> 16, 175, aim 5/60 10/25; Reach PP overcharge 200 emp.
        # HALO 2 (H2EK): frag 50..150 over 0.75 -> 1.75 (explosion_small, core 0.75, accel 2.25), timer 0.5 after
        # first bounce, arming 1.5, gravity 1.0 / 1.0, throw 10 (both bipeds), frictions 0.5 / 0.7; RL impact 150 +
        # 75..200 over 1 -> 2 (explosion_large), 0.8 s, 2 / 4 / 8, reload 5.0 s, 8 -> 20, range 175, autoaim 5/45,
        # magnetism 10/25, smash_melee; Fuel Rod 100 + 40..90 over 0.5 -> 1.5, 0.4 s, 5 / 20 / 30; Brute Shot 20
        # (bullet_fast) + 25..50 over 0.75 -> 1.5, 0.3 s, 4 / 12 / 16, fuse 0.2 any surface; PP overcharge 1 `emp`
        # (matg emp: shields x500, sentinel x500, enforcer x50, metal x1, flesh 0).
        'pick': 'Frag Grenade + Rocket Launcher for the holes',
        'reason': ("user 2026-11-24 (Halo 1's pick): the frag is the same damage family in both games (explosion_small; "
                   "Halo 2's own group by Reach's name); a thrown grenade's holes (rate, magazine, reload, range, aim, "
                   "melee, impact) by the Rocket Launcher ratio. The Brute Shot is Halo 2's role twin but cannot be a "
                   "ratio yardstick (Reach has none): a 5b peer, and it shows Halo 2 has Reach's own fuse rule. "
                   "HOLD + EMP (user): the plasma pistol's CHARGED PAIR, native in Halo 2 (one trigger: latch-autofire, "
                   "secondary action charge, barrel 1). FUSE (user): Reach's own 0.5 s after the first bounce off any "
                   "surface (Halo 1 had to use a fuse from launch). VEHICLE STALL (user): test Halo 2's unused damage "
                   "`side effect` emp + `emp radius` on the release. Legendary direct hits: Elite minor 2, Brute minor "
                   "2, Grunt / Jackal 1 (Original and Balanced alike); one shot every 2.6 s (Original) / 3.2 s"),
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows (the catalog's)
        'balanced': {
            # FRAG ratio: 180 x 150/160; lower: Reach 0 (unset) -> the sibling rule, 168.75 x 50/150; radius 0.75 x
            # 0.75/0.675, 2.25 x 1.75/2.25; core 0.6 x 0.75/0.6 (the frag's core = its inner radius)
            'damage': 168.75, 'damage_lower': 56.25, 'radius': (0.833, 1.75),
            # the impact is a HOLE (the frag has none) -> RL: 25 x 150/200
            'impact': 18.75,
            # the fuse, Reach's rule: 0.5 x 0.5/0.625 (the Reach frag's 0.6-0.65 mean); arming 0 x 1.5/1.4 = 0
            'timer': 0.4, 'arming': 0.0,
            # flight: the throw speed is 10 wu/s in both games -> x1; gravity 0.7 x 1.0/0.9, water 0.75 x 1.0/0.75
            'velocity': (12.5, 7.5), 'gravity': 0.778, 'water_gravity': 1.0,
            # HOLES -> the RL ratio: recovery 0.5 x 0.8/0.8; magazine 1 x 2/2, 8 x 4/4, 16 x 8/8; reload 63 fr x
            # 5.0 s / 116 fr (3.867 s) = 2.716 s; range 100 x 175/175; autoaim 4 x 5/5, 15 x 45/60; magnetism 8 x
            # 10/10, 15 x 25/25; melee Reach strike -> H2's smash_melee (the RL's)
            'fire_recovery_s': 0.5, 'magazine': 1, 'rounds_total_initial': 8, 'rounds_total_maximum': 16,
            'reload_s': 2.716, 'range': 100.0, 'autoaim': (4.0, 11.25), 'magnetism': (8.0, 15.0),
            # error: the RL's 0 / 0 is degenerate -> Reach's own 0.15 / 0..0.4 (no ratio)
            'error_deg': (0.15, 0.0, 0.4),
            # friction: Reach's 0.42 / 0.42 in both (no ratio: Halo 1's user pick)
            'friction': (0.42, 0.42),
            # the RELEASE (charged pair): the tethered blast by the frag ratio 168.75 over 0.001 x 0.75/0.675, 1 x
            # 1.75/2.25; the EMP by the plasma pistol OVERCHARGE (H2 1 x Reach EMP 100 / Reach overcharge 200) = 0.5
            # `emp` with `only hurts shields` (250 on any shield: strips every one), over 0.25 x 0.75/0.675, 2.5 x
            # 1.75/2.25
            'release_damage': 168.75, 'release_radius': (0.0011, 0.778),
            'emp': 0.5, 'emp_radius': (0.278, 1.944),
            'charge_s': 0.5},
        'candidates': {
            'provisional': 'Frag Grenade + Rocket Launcher for the holes',
            'alternatives': ['Rocket Launcher', 'Flak Cannon'],
            'direct': 'none',
            # the h2_role_compare names (the Flak Cannon is its 'Fuel Rod')
            'peers': ['Brute Shot', 'Rocket Launcher', 'Fuel Rod'],
            'why': "1-round latch-tether, bouncing grenade (H1 pick). H2 has no tether trigger (approximate as in H1); the Brute Shot is H2's own grenade launcher -- a peer only (no Reach Brute Shot)",
            'lacks': ("detonating a grenade already in flight (the release fires a contact-burst EMP grenade instead), "
                      "rolling ('turn physical': Halo 2's responses have none), the vehicle stall unless Halo 2's unused "
                      "`side effect` emp works (to test)"),
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}

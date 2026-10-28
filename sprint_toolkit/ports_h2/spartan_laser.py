r"""Spartan Laser into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

SL = r'objects\weapons\support_high\spartan_laser'    # the source's folder (H3EK) AND the port's (H2EK)
BR = r'objects\weapons\rifle\beam_rifle'                # the donor (H2EK)
FX = r'effects\objects\weapons\support_high\spartan_laser'   # the reserved effects folder
BRFX = r'effects\objects\weapons\rifle\beam_rifle'
RL = r'objects\weapons\support_high\rocket_launcher'   # the yardstick; its shaders seed the look

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
    # step 1 -- h2_port_geometry.py kind 'h3': Halo 3's render models on their OWN skeletons (world:
    # gun / body / foregrip / tubes / push_bar; FP: gun / cover / handle / laser / shield /
    # telescope / lens_1 / lens_2) -- the laser's own Halo 3 FP animations drive them (the AR's route)
    'geometry': {
        'kind': 'h3',
        'world_rm': SL + r'\spartan_laser.render_model',
        'fp_rm': SL + r'\fp_spartan_laser\fp_spartan_laser.render_model',
        'data_dir': SL,
        'world': 'spartan_laser', 'fp': 'fp_spartan_laser',
        # Halo 3 shader basename -> Halo 2 material (= the shader tag's name); decal2 renamed (Halo 1's
        # tool dropped a trailing digit of a material name, A8 -- not risked here)
        'materials': {'spartan_laser': 'spartan_laser', 'spartan_laser_dull': 'spartan_laser_dull',
                      'spartan_laser_shiny': 'spartan_laser_shiny',
                      'spartan_laser_luminous': 'spartan_laser_luminous',
                      'spartan_laser_decal': 'spartan_laser_decal',
                      'spartan_laser_decal2': 'spartan_laser_lattice'},
        # the world .model is the BR's clone (the AR's proof): its variants name `base` / `gun`
        'world_permutation': 'base', 'world_region': 'gun',
        # Halo 3's markers; the side vent = the beam rifle's `vent02` (its overheat sound attachment)
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'fx_side_vent': 'vent02', 'fx_vent': 'vent01',
                    'side_flare': 'side_flare'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['spartan_laser', r'spartan_laser\fp_spartan_laser'],
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps (base 768 + a signed-DXN bump, the AR's
    # 'bump_snorm'; two alpha decals; the luminous map is a 1x1 WHITE: the whole material lit), the
    # shaders reseeded from Bungie's Halo 2 ROCKET LAUNCHER (the human support weapon): the env-mapped
    # tubes for Halo 3's env-mapped spartan_laser / shiny, the plain body for dull, its decal shader for
    # both decals; the luminous strips on the shotgun's lit sight (tex_bump_illum) with the base map
    # tinted Halo 3's luminous blue (Halo 1's LUMINOUS_HOT) as its illum map
    'textures': {
        'kind': 'h3',
        'rel': SL + r'\bitmaps',
        'shaders_dir': SL + r'\shaders',
        'bump_gain': 1.0,
        # power-of-two sizes: `tool bitmaps` SKIPS a 768 x 768 / 96 x 128 source (Halo 1's A8 too); 512
        # = Bungie's rocket launcher, the AR's and the Spiker's (true colour: 1024 made a 6.8 MB tag)
        'bitmaps': [(SL + r'\bitmaps\spartan_laser.bitmap', 'spartan_laser', RL + r'\bitmaps\rocket_launcher', 'color',
                     (512, 512)),
                    (SL + r'\bitmaps\spartan_laser_bump.bitmap', 'spartan_laser_bump', RL + r'\bitmaps\rocket_launcher_bump',
                     'bump_snorm', (512, 512)),
                    (SL + r'\bitmaps\spartan_laser_decal.bitmap', 'spartan_laser_decal', RL + r'\bitmaps\rocket_launcher_decal',
                     'color', (128, 128)),
                    (SL + r'\bitmaps\spartan_laser_decal2.bitmap', 'spartan_laser_lattice', RL + r'\bitmaps\rocket_launcher_decal',
                     'color', None),
                    (SL + r'\bitmaps\spartan_laser.bitmap', 'spartan_laser_illum', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (0.5, 0.65, 1.0), 0), (512, 512))],
        'shaders': [
            ('spartan_laser', RL + r'\shaders\rocket_launcher_tubes',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump',
              RL + r'\bitmaps\rocket_launcher_bump_active_camo': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_shiny', RL + r'\shaders\rocket_launcher_tubes',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump',
              RL + r'\bitmaps\rocket_launcher_bump_active_camo': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_dull', RL + r'\shaders\rocket_launcher_body',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_decal', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': SL + r'\bitmaps\spartan_laser_decal'}),
            ('spartan_laser_lattice', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': SL + r'\bitmaps\spartan_laser_lattice'}),
            ('spartan_laser_luminous', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': SL + r'\bitmaps\spartan_laser_illum'}),
        ],
        'report_rows': [(SL + r'\bitmaps\spartan_laser_bump', 'the port'),
                        (RL + r'\bitmaps\rocket_launcher_bump', 'Bungie rocket launcher')],
    },

    # step 3 -- h2_port_weapon.py: the H2 BEAM RIFLE's weapon (battery + heat, 0 magazines, one
    # trigger / one barrel, instant beam, two-handed) with every tag a balance row or a look may
    # touch cloned; the beam visual = the beam rifle's two contrails (recoloured at the look step).
    # First pass (2026-10-28): the CHARGE PROOF -- the world / FP models, graphs and HUD are still the
    # beam rifle's; their own wiring joins with steps 1 / 7 / 9
    'weapon': {
        'weapon': SL + r'\spartan_laser.weapon',
        'clones': [(BR + r'\beam_rifle.weapon', SL + r'\spartan_laser.weapon'),
                   (BR + r'\projectiles\beam_rifle_beam.projectile', SL + r'\projectiles\spartan_laser_beam.projectile'),
                   (BR + r'\damage_effects\beam_rifle_impact.damage_effect', SL + r'\damage_effects\spartan_laser_beam.damage_effect'),
                   (r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger.damage_effect',
                    SL + r'\damage_effects\spartan_laser_trigger.damage_effect'),
                   (BR + r'\damage_effects\beam_rifle_trigger_misfire.damage_effect',
                    SL + r'\damage_effects\spartan_laser_misfire.damage_effect'),
                   (BRFX + r'\beam_rifle_fire.effect', FX + r'\spartan_laser_fire.effect'),
                   (BRFX + r'\beam_rifle_inner.contrail', FX + r'\spartan_laser_inner.contrail'),
                   (BRFX + r'\beam_rifle_outer.contrail', FX + r'\spartan_laser_outer.contrail'),
                   (BRFX + r'\overheated.effect', FX + r'\overheated.effect'),
                   (r'effects\materials\objects\weapons\beam_rifle.material_effects', FX + r'\spartan_laser.material_effects')],
        'wiring': [
            (SL + r'\spartan_laser.weapon', 'proj', BR + r'\projectiles\beam_rifle_beam',
             SL + r'\projectiles\spartan_laser_beam', 'projectile'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'jpt!', BR + r'\damage_effects\beam_rifle_impact',
             SL + r'\damage_effects\spartan_laser_beam', 'impact damage (the whole shot: overpenetration takes the impact only)'),
            (SL + r'\spartan_laser.weapon', 'jpt!', r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger',
             SL + r'\damage_effects\spartan_laser_trigger', 'firing damage (kick)'),
            (SL + r'\spartan_laser.weapon', 'jpt!', BR + r'\damage_effects\beam_rifle_trigger_misfire',
             SL + r'\damage_effects\spartan_laser_misfire', 'misfire damage'),
            (SL + r'\spartan_laser.weapon', 'effe', BRFX + r'\beam_rifle_fire', FX + r'\spartan_laser_fire', 'firing effect'),
            (SL + r'\spartan_laser.weapon', 'effe', BRFX + r'\overheated', FX + r'\overheated', 'overheated (vent) effect'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'cont', BRFX + r'\beam_rifle_inner',
             FX + r'\spartan_laser_inner', 'the beam: inner contrail'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'cont', BRFX + r'\beam_rifle_outer',
             FX + r'\spartan_laser_outer', 'the beam: outer contrail'),
            (SL + r'\spartan_laser.weapon', 'foot', r'effects\materials\objects\weapons\beam_rifle',
             FX + r'\spartan_laser', 'material effects (the weapon)'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'foot', r'effects\materials\objects\weapons\beam_rifle',
             FX + r'\spartan_laser', 'impact material effects'),
        ],
        'shared': [(r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'the particles inside spartan_laser_fire', "the beam rifle's (Halo 3 particles do not port)")],
    },

    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (DEFAULT; the rocket ratio = the catalog's
    # balance rows). THE CHARGE: Halo 3's spew-charge has no Halo 2 twin; the shape is the SCARAB
    # MAIN GUN's (Halo 2's only `charge` trigger, AI-driven): behavior charge, primary barrel -1 (an
    # early release fires NOTHING -- Halo 3's tap fires its harmless tracer), secondary barrel 0, both
    # actions `charge`, overcharged action DISCHARGE (fires barrel 0 when full), charged illumination 1.
    # Halo 3's 5 beam rounds a burst = ONE projectile carrying 570 (Halo 1's A8: an overpenetrated unit
    # takes the impact only)
    'numbers': {
        'numbers': [
            (SL + r'\spartan_laser.weapon', 'behavior', 'new triggers', 0, 0, 3),          # latch -> charge
            # block indices (h2_tagfield read_all(indices=True), A2): the secondary (-1, findable by
            # value) first; the primary (0 = padding-like) pinned 2 bytes before it
            (SL + r'\spartan_laser.weapon', 'secondary barrel', 'new triggers', 0, 0, 0),
            (SL + r'\spartan_laser.weapon', 'primary barrel', 'new triggers', 0, 0, -1,
             {'anchor': ('secondary barrel', -2)}),
            # the zero fields placed from the secondary barrel (the trigger element, read off the
            # plasma pistol's non-zero ones: prediction +2, 2 pad, autofire time +6 / throw +10,
            # secondary action +14, primary +16, charging time +18, charged time +22, overcharged
            # action +26, 2 pad, charged illumination +30), each proved by pin()'s probe
            (SL + r'\spartan_laser.weapon', 'secondary action', 'new triggers', 0, 0, 1,     # fire -> charge
             {'anchor': ('secondary barrel', 14)}),
            (SL + r'\spartan_laser.weapon', 'primary action', 'new triggers', 0, 0, 1,
             {'anchor': ('secondary barrel', 16)}),
            (SL + r'\spartan_laser.weapon', 'charging time', 'new triggers', 0, 0, 2.5,
             {'anchor': ('secondary barrel', 18)}),
            (SL + r'\spartan_laser.weapon', 'overcharged action', 'new triggers', 0, 0, 2,   # none -> discharge
             {'anchor': ('secondary barrel', 26)}),
            (SL + r'\spartan_laser.weapon', 'charged illumination', 'new triggers', 0, 0, 1.0,
             {'anchor': ('secondary barrel', 30)}),
            # heat 1 a shot (every shot overheats), vent (1 - 0.1) / 0.4 = 2.25 s; Halo 3's normal loss 1
            (SL + r'\spartan_laser.weapon', 'heat generated per round', 'barrels', 0, 0, 1.0),
            (SL + r'\spartan_laser.weapon', 'overheated heat loss per second', '', 0, 0, 0.4),
            (SL + r'\spartan_laser.weapon', 'heat loss per second', '', 0, 0, 1.0),
            # battery: 5 shots (Halo 3 age 0.04 a round x 5 rounds)
            (SL + r'\spartan_laser.weapon', 'age generated per round', 'barrels', 0, 0, 0.2),
            (SL + r'\damage_effects\spartan_laser_beam.damage_effect', 'damage lower bound', '', 0, 0, 570.0),
            (SL + r'\damage_effects\spartan_laser_beam.damage_effect', 'damage upper bound', '', 0, 0, [570.0, 570.0]),
        ],
        'skipped': [],
    },

    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03b_newmombasa', 'dervish_level': '06a_sentinelwalls'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}

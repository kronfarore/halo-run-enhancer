r"""Gravity Hammer into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A5) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

H3GH = r'objects\weapons\melee\gravity_hammer'        # the source's folder (H3EK) -- in H2EK Tartarus's
GH = r'objects\weapons\melee\gravity_hammer_port'     # the port's folder (H2EK, reserved)
FX = r'effects\objects\weapons\melee\gravity_hammer_port'
BEAM = r'objects\weapons\rifle\beam_rifle'            # the donor (H2EK)
BLADE = r'objects\weapons\melee\energy_blade'         # the yardstick + melee fields (H2EK)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'
import os as _os
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~melee~gravity_hammer~gravity_hammer.render_model.xml')
# ... turned on its side for those three (write_side_jms at the end of this file)
SIDE_JMS = _os.path.join(H2EK, 'data', GH, 'glyph', 'gravity_hammer_port_side.jms')

PORT = {
    'order': 5,
    'wave': 'A5',
    'name': 'Gravity Hammer',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
    'reservations': {
        'message_prefix': 'gh2',
        'glyph': 0xE142,
        'weapon_dir': 'objects\\weapons\\melee\\gravity_hammer_port',
        'effects_dir': 'effects\\objects\\weapons\\melee\\gravity_hammer_port',
        'fp_graph': 'weapons\\melee\\fp_gravity_hammer_port\\fp_gravity_hammer_port',
        'hud': 'ui\\hud\\gravity_hammer',
        'hud_bitmap_prefix': 'gravity_hammer_',
        'sound_dir': 'sound\\weapons\\gravity_hammer_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    # step 4a chose the TRIGGER route (energy per swing), so the donor needs a trigger + barrel with
    # battery aging: the sword's 0/0/0 has neither (a block insert). The H2 BEAM RIFLE is that shape
    # exactly: 0 magazines, one latch trigger, battery 'age generated per round' (0.0556), two-handed
    # -- its zoom and heat are plain fields (zeroed). Not the donor: the energy blade (0/0/0), the
    # plasma rifle (1 magazine, 3 barrels, one-handed). The HUD = the Energy Blade's plasma_sword
    # (battery meter only), the melee fields = the sword's (lunge dash_melee); the phase-0 proposal
    # was the blade (melee-only route)
    'donor': {'weapon': r'objects\weapons\rifle\beam_rifle\beam_rifle', 'message_prefix': 'be',
              'hud': r'ui\hud\plasma_sword', 'melee_from': r'objects\weapons\melee\energy_blade\energy_blade',
              'why': "trigger route (step 4a): 0 magazines / 1 latch trigger / battery age per round, "
                     "two-handed; HUD plasma_sword; melee fields the sword's"},
    'yardstick': {
        # STEP 4a (user, 2026-10-28) -- measured on the H3EK / H2EK exports:
        #   H3 hammer: jab (melee button, 1st hit) smash_melee 80; RT slam = lunge crush_melee 150 +
        #     gravity_hammer_explosion 50..160 r 0.75->1.5 accel 3.5 stun 4.5 (an ANIMATION EFFECT,
        #     every swing); campaign external aging 0.05 a swing (20); autoaim 10/1.75, magnetism 10/6.
        #   H3 sword dash_melee 150 (strike + lunge), aim 10/2.5 10/6; H2 Energy Blade slice_melee 70,
        #     lunge dash_melee 150, aim 6/6 12/8, ages per KILL only (H2 has no per-swing aging field).
        #   Tartarus (shown, not picked): tartarus_hammer_melee 150..500 r 1.0 accel 4,
        #     tartarus_hammer_explosion 100..200 plasma r 0.4->0.8 accel 2.
        'pick': 'Energy Blade', 'ratio': 'lunge x1.0',
        'reason': "user: the sword's LUNGE ratio (150 -> 150) -- Balanced = Halo 3's own numbers: slam "
                  "crush 150 + blast 50..160 r 0.75-1.5, jab 80; aim by the sword's aim ratio "
                  "(autoaim 6 / 4.2, magnetism 12 / 8)",
        'decisions': {   # user, 2026-10-28 (step 4a)
            'energy': "TRIGGER ROUTE (Halo 1's recipe): RT fires an invisible strike that bursts into "
                      "the blast; the barrel's native 'age generated per round' 0.05 (20 swings, misses "
                      "count); the melee button = the pommel jab. Not chosen: melee-only + energy per "
                      "kill; a halo2.dll per-swing patch",
            'model': "Halo 3's hammer (world, 3P, FP) -- Bungie's H2 hammer (Tartarus's) untouched",
            '3p_class': "'melee' (the Brute graph's own hammer class); h2_graph_teach clones 'sword' as "
                        "'melee' in the masterchief and dervish graphs",
            'enhancer': "one card family 'Gravity Hammer' (enhancer session 2026-10-28): catalog weap = "
                        "the port's tag; it retargets the Halo 2 rows + derives the rest at hand-off "
                        "(tell it the slam / blast / jab jpt tags)",
        },
        'candidates': {
            'provisional': 'Energy Blade',
            'alternatives': ["H2's own Gravity Hammer (Tartarus: a boss's numbers -- show, do not default)", 'Rocket / Fuel Rod melee'],
            'direct': "H2 gravity_hammer (Tartarus) = the same weapon, carded in both -- but its damage lives in tartarus_hammer_* (an AI boss's)",
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "melee-only, ages per swing; the sword is H2's only player melee weapon with Bungie's own player numbers. THE FIX IS A FULL PORT: H2's hammer tag is a Tartarus stub (no triggers, no FP model/anims, no HUD, empty message ids, no player damage) -- a NEW player tag beside it, Tartarus untouched; Bungie's H2 hammer render/collision model reusable",
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': Halo 3's world + FP hammer on their OWN skeleton
    # (hammer, shaft); the source folder is Bungie's melee\gravity_hammer (H3EK), the port's is
    # melee\gravity_hammer_port (H2EK: Tartarus's melee\gravity_hammer is never written).
    # Markers: the blast point `hammer_detonation` (world; `fp_hammer_detonation` in FP) is the
    # strike's origin = primary_trigger (Halo 1's Armed lesson: the AI fires from it); the hands
    # and the two effect markers (hammer_on's arcs + vent) keep their names
    'geometry': {
        'kind': 'h3',
        'world_rm': H3GH + r'\gravity_hammer.render_model',
        'fp_rm': H3GH + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'data_dir': GH,
        'world': 'gravity_hammer_port', 'fp': 'fp_gravity_hammer_port',
        'materials': {'hammer': 'gravity_hammer_port', 'hammer_shiny': 'gravity_hammer_port_shiny',
                      'hammer_dull': 'gravity_hammer_port_dull'},
        'markers': {'hammer_detonation': 'primary_trigger', 'fp_hammer_detonation': 'primary_trigger',
                    'left_hand': 'left_hand', 'right_hand': 'right_hand',
                    'fx_electric_arcs': 'fx_electric_arcs', 'fx_vent': 'fx_vent'},
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['gravity_hammer_port', r'gravity_hammer_port\fp_gravity_hammer_port'],
    },
    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's Halo 2
    # hammer (Tartarus's `hammer`: tex_bump_env_illum -- bump, detail, base, env, a SEPARATE
    # self_illum_map; the Spike Rifle's seed too) for the lit head (hammer, hammer_shiny), the Brute
    # Shot's own (tex_bump_env) for the dull grip. Halo 3's illum map is a grey mask lit in BLUE on
    # both lit materials (self_illum_color d7 57 2e BGRA = 46 / 87 / 215, ports_h1/gravity_hammer.py);
    # Halo 2 draws a self_illum_map as it is -> TINTED here, the Spike Rifle's final recipe (PALE,
    # soft spots: Halo 3's bloom reads pale; grown blocks read 'crosses taped on')
    'textures': {
        'kind': 'h3',
        'rel': GH + r'\bitmaps',
        'shaders_dir': GH + r'\shaders',
        'bump_gain': 1.0,                      # the AR's (user: 1.6 read 'rough')
        'bitmaps': [(H3GH + r'\bitmaps\gravity_hammer.bitmap', 'gravity_hammer_port',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer', 'color', None),
                    (H3GH + r'\bitmaps\gravity_hammer_bump.bitmap', 'gravity_hammer_port_bump',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump', 'bump_snorm', None),
                    (H3GH + r'\bitmaps\gravity_hammer_illum.bitmap', 'gravity_hammer_port_illum',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (0.75, 0.78, 1.0), 0, 1.5), None)],
        'shaders': [
            ('gravity_hammer_port', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': GH + r'\bitmaps\gravity_hammer_port_illum'}),
            ('gravity_hammer_port_shiny', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': GH + r'\bitmaps\gravity_hammer_port_illum'}),
            # the camo bump FIRST: its path and the port's bump path are both 74 characters, so once
            # the bump is repointed h2_tagref cannot tell the two records apart (2026-10-28)
            ('gravity_hammer_port_dull', r'objects\weapons\support_low\brute_shot\shaders\brute_shot',
             {r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump_active_camo': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump': GH + r'\bitmaps\gravity_hammer_port_bump'}),
        ],
        'report_rows': [(GH + r'\bitmaps\gravity_hammer_port_bump', 'the port'),
                        (r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump', "Bungie's H2 hammer")],
    },
    # step 3 -- h2_port_weapon.py: the H2 BEAM RIFLE's weapon (0 magazines / 1 latch trigger / its
    # barrel with battery age per round) cloned, every tag a balance row or a look may touch cloned:
    #   the STRIKE = the SMG bullet's clone (no model, no attachments, detonation timer 'immediately'):
    #     its impact damage = the SLAM (Halo 3's crush_melee 150, on a clone of H2's dash_melee), its
    #     detonation effect (airborne + ground) = the IMPACT effect below;
    #   the IMPACT effect = Tartarus's tartarus_hammer_impact cloned (Halo 2's own hammer look: blast
    #     ring, plasma mesh, distortion, arcs) -- its damage part repointed to the port's own BLAST
    #     (a clone of tartarus_hammer_explosion, Halo 3's numbers): the effect carries the blast as in
    #     Halo 3 (gravity_hammer_impact -> gravity_hammer_explosion) and Tartarus's brute graph;
    #   the JAB (melee button, 1st / 2nd / 3rd hit) = a clone of H2's smash_melee (Halo 3's 80), the
    #     melee lunge = the slam's clone; the responses stay Bungie's (0-damage);
    #   the world .model = the beam rifle's (no variants; render + collision pool one path: nth 0).
    'weapon': {
        'weapon': GH + r'\gravity_hammer_port.weapon',
        'clones': [(BEAM + r'\beam_rifle.weapon', GH + r'\gravity_hammer_port.weapon'),
                   (BEAM + r'\beam_rifle.model', GH + r'\gravity_hammer_port.model'),
                   (r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile',
                    GH + r'\projectiles\gravity_hammer_port_strike.projectile'),
                   (r'objects\weapons\damage_effects\dash_melee.damage_effect',
                    GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect'),
                   (r'objects\characters\brute\damage_effects\tartarus_hammer_explosion.damage_effect',
                    GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect'),
                   (r'objects\weapons\damage_effects\smash_melee.damage_effect',
                    GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect'),
                   (r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger.damage_effect',
                    GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect'),
                   (r'effects\objects\characters\brute\tartarus_hammer_impact.effect',
                    FX + r'\gravity_hammer_port_impact.effect'),
                   (r'effects\objects\weapons\rifle\beam_rifle\beam_rifle_fire.effect',
                    FX + r'\gravity_hammer_port_fire.effect'),
                   (r'effects\materials\objects\weapons\beam_rifle.material_effects',
                    FX + r'\gravity_hammer_port.material_effects'),
                   # the HUD (step 7): the ENERGY BLADE's (a battery bar + battery number, no ammo
                   # ticks, no scope) -- Halo 3's hammer HUD is an energy readout too
                   (r'ui\hud\plasma_sword.new_hud_definition', r'ui\hud\gravity_hammer.new_hud_definition')],
        'wiring': [
            (GH + r'\gravity_hammer_port.weapon', 'hlmt', BEAM + r'\beam_rifle', GH + r'\gravity_hammer_port', 'world model'),
            (GH + r'\gravity_hammer_port.model', 'mode', BEAM + r'\beam_rifle', GH + r'\gravity_hammer_port',
             'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            # the hull: step 5 builds the port's own from Bungie's H2 hammer (h2_port_collision
            # repoints from ITS donor's path, but this .model is the beam rifle's -- so here)
            (GH + r'\gravity_hammer_port.model', 'coll', BEAM + r'\beam_rifle', GH + r'\gravity_hammer_port',
             'the collision model (step 5)'),
            (GH + r'\gravity_hammer_port.weapon', 'mode', BEAM + r'\fp_beam_rifle\fp_beam_rifle',
             GH + r'\fp_gravity_hammer_port\fp_gravity_hammer_port', 'first person model, Master Chief', {'nth': 0}),
            # the same path again (every=True refuses: a third record has that path's length -- the AR's)
            (GH + r'\gravity_hammer_port.weapon', 'mode', BEAM + r'\fp_beam_rifle\fp_beam_rifle',
             GH + r'\fp_gravity_hammer_port\fp_gravity_hammer_port', 'first person model, Dervish', {'nth': 0}),
            (GH + r'\gravity_hammer_port.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle',
             r'objects\characters\masterchief\fp\weapons\melee\fp_gravity_hammer_port\fp_gravity_hammer_port',
             "Master Chief FP graph: the hammer's own Halo 3 animations"),
            (GH + r'\gravity_hammer_port.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle',
             r'objects\characters\dervish\fp\weapons\melee\fp_gravity_hammer_port\fp_gravity_hammer_port',
             "Dervish FP graph: the hammer's own Halo 3 animations"),
            (GH + r'\gravity_hammer_port.weapon', 'proj', BEAM + r'\projectiles\beam_rifle_beam',
             GH + r'\projectiles\gravity_hammer_port_strike', 'the strike'),
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'jpt!', r'objects\weapons\rifle\smg\damage_effects\smg_bullet',
             GH + r'\damage_effects\gravity_hammer_port_slam', 'impact damage = the slam'),
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\gravity_hammer_port', 'impact material effects'),
            (FX + r'\gravity_hammer_port_impact.effect', 'jpt!', r'objects\characters\brute\damage_effects\tartarus_hammer_explosion',
             GH + r'\damage_effects\gravity_hammer_port_explosion', "the blast (the effect carries it, Halo 3's way)"),
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger',
             GH + r'\damage_effects\gravity_hammer_port_trigger', 'firing damage (the wielder shove)'),
            # the player melee: 1st hit = smash_melee in the beam rifle; Halo 3's jab = its own clone
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', r'objects\weapons\damage_effects\smash_melee',
             GH + r'\damage_effects\gravity_hammer_port_melee', 'the jab (3rd hit: smash_melee in the beam rifle)', {'every': True}),
            # the beam rifle's 1st / 2nd hit are strike_melee: Halo 3's hammer hits all three with smash
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', r'objects\weapons\damage_effects\strike_melee',
             GH + r'\damage_effects\gravity_hammer_port_melee', 'the jab (1st hit)', {'nth': 0}),
            # twice (every=True refuses: other records share the path's length)
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', r'objects\weapons\damage_effects\strike_melee',
             GH + r'\damage_effects\gravity_hammer_port_melee', 'the jab (2nd hit)', {'nth': 0}),
            # the beam rifle has no lunge damage: the melee-button lunge = Halo 3's crush (the slam)
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', '', GH + r'\damage_effects\gravity_hammer_port_slam',
             'the melee lunge = the slam', {'field': 'lunge melee damage'}),
            (GH + r'\gravity_hammer_port.weapon', 'jpt!', '', r'objects\weapons\damage_effects\dash_melee_response',
             "the lunge response (the sword's, Bungie's 0-damage)", {'field': 'lunge melee response'}),
            # the strike bursts into the IMPACT effect (which carries the blast) on a hit, and in the
            # air when its timer runs out: both detonation effects
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'effe', '', FX + r'\gravity_hammer_port_impact',
             'detonation effect (airborne) = the impact + blast', {'field': 'detonation effect (airborne)'}),
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'effe', '', FX + r'\gravity_hammer_port_impact',
             'detonation effect (ground) = the impact + blast', {'field': 'detonation effect (ground)'}),
            (GH + r'\gravity_hammer_port.weapon', 'effe', r'effects\objects\weapons\rifle\beam_rifle\beam_rifle_fire',
             FX + r'\gravity_hammer_port_fire', 'firing effect (the swing)'),
            (GH + r'\gravity_hammer_port.weapon', 'foot', r'effects\materials\objects\weapons\beam_rifle',
             FX + r'\gravity_hammer_port', 'material effects (the weapon)'),
            (GH + r'\gravity_hammer_port.weapon', 'nhdt', r'ui\hud\beam_rifle', r'ui\hud\gravity_hammer', 'its own HUD (step 7, plasma_sword clone)'),
        ],
        # the 3P label (step 4a): class 'melee' (the Brute graph's hammer class, taught to the
        # masterchief / dervish graphs), type 'gh' = Bungie's Halo 2 hammer's own weapon name (no
        # graph holds a 'gh' type: every class falls back to its 'any' set)
        'string_ids': {'rifle': 'melee', 'csr': 'gh'},
        'string_ids_done': ('weapon name', 'gh'),
        'shared': [(r'objects\weapons\damage_effects\*_melee_response', "Bungie's 0-damage responses"),
                   (r'the particles inside gravity_hammer_port_impact', "Tartarus's (Halo 2's hammer look; Halo 3 particles do not port)"),
                   (r'objects\characters\brute\*, tartarus_hammer_*', 'TARTARUS: never written (the 08b boss)')],
    },
    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (= Balanced here: step 4a's lunge ratio x1.0)
    'numbers': {
        'numbers': [
            # flags'': the beam rifle's 2080 minus 'aim assists only when zoomed' (32) = 'cannot fire
            # at maximum age' alone (the hammer's energy)
            (GH + r'\gravity_hammer_port.weapon', 'flags', '', 0, 2, 2048),
            (GH + r'\gravity_hammer_port.weapon', 'magnification levels', '', 0, 0, 0),
            (GH + r'\gravity_hammer_port.weapon', 'magnification range', '', 0, 0, [0.0, 0.0]),
            # no heat: the hammer has energy only
            (GH + r'\gravity_hammer_port.weapon', 'heat recovery threshold', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'overheated threshold', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'heat loss per second', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'heat generated per round', 'barrels', 0, 0, 0.0),
            # ENERGY: Halo 3's campaign external aging 0.05 a swing (20), on the barrel (step 4a)
            (GH + r'\gravity_hammer_port.weapon', 'age generated per round', 'barrels', 0, 0, 0.05),
            # one slam per Halo 3 RT cycle: melee_lunge_unaimed, 46 frames = 1.533 s (Halo 1's A9)
            (GH + r'\gravity_hammer_port.weapon', 'fire recovery time', 'barrels', 0, 0, 1.533333),
            (GH + r'\gravity_hammer_port.weapon', 'error angle', 'barrels', 0, 1, [0.0, 0.0]),
            # aim (step 4a, the sword's aim ratio onto Halo 3's hammer 10 / 1.75, 10 / 6)
            (GH + r'\gravity_hammer_port.weapon', 'autoaim angle', '', 0, 0, 6.0),
            (GH + r'\gravity_hammer_port.weapon', 'autoaim range', '', 0, 0, 4.2),
            (GH + r'\gravity_hammer_port.weapon', 'magnetism angle', '', 0, 1, 12.0),
            (GH + r'\gravity_hammer_port.weapon', 'magnetism range', '', 0, 1, 8.0),
            # THE STRIKE: an invisible shell that bursts 0.2 s out (the slam's head-down moment, Halo
            # 1's A9) at 6 wu/s = 1.2 wu, or on whatever it touches first -- every material detonates
            # (the SMG bullet's overpenetrate / fizzle / bounce responses all made 'impact (detonate)')
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'timer', '', 0, 0, [0.2, 0.2]),
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'initial velocity', '', 0, 0, 6.0),
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'final velocity', '', 0, 0, 6.0),
            # the AI judges reach by the maximum range (Halo 1's A9 trap 3); the timer still bursts it
            (GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'maximum range', '', 0, 0, 5.0),
            # (air gravity scale: the SMG bullet's is 0 already.) The TIMER read 0,0 -- a zero field
            # cannot be found by value: its per-tag cache entry was SEEDED from `maximum range`
            # (0x1F8 - minimum velocity 4 - the bounds 8 = 0x1EC) and proven by a test write that
            # moved only the timer row (2026-10-29)
        ] + [(GH + r'\projectiles\gravity_hammer_port_strike.projectile', 'response', 'material responses', k, n, 0)
             for k, n in [(k, 0) for k in range(1, 10)] + [(3, 1), (4, 1), (6, 1)]] + [   # the other second responses already detonate
            # THE SLAM (impact damage + melee lunge): Halo 3's crush_melee 150, accel 1.5, radius 0
            (GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect', 'radius', '', 0, 0, [0.0, 0.0]),
            (GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect', 'damage lower bound', '', 0, 0, 150.0),
            (GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect', 'damage upper bound', '', 0, 0, [150.0, 150.0]),
            (GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect', 'instantaneous acceleration', '', 0, 0, 1.5),
            # THE BLAST: Halo 3's gravity_hammer_explosion -- 50..160 over 0.75 -> 1.5 wu, core 0.75,
            # accel 3.5, AI stun 4.5, category melee, flags 'does not hurt owner' (Halo 3's 2049 =
            # does not hurt owner + transfer dmg always uses min; Halo 2's bit 0 is 'does not hurt owner')
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'radius', '', 0, 0, [0.75, 1.5]),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'AOE core radius', '', 0, 0, 0.75),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'damage lower bound', '', 0, 0, 50.0),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'damage upper bound', '', 0, 0, [160.0, 160.0]),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'instantaneous acceleration', '', 0, 0, 3.5),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'AI stun radius', '', 0, 0, 4.5),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'category', '', 0, 0, 6),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'flags', '', 0, 1, 1),
            # THE JAB (melee button): Halo 3's smash_melee 80, accel 1
            (GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect', 'damage lower bound', '', 0, 0, 80.0),
            (GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect', 'damage upper bound', '', 0, 0, [80.0, 80.0]),
        ],
        'skipped': [
            ('damage pyramid', "Halo 3's hammer has 0 / 0 (the globals' default); the beam rifle's "
                               "20 x 10 / 0.6 kept -- 4b decides"),
            ('wielder shove', "Halo 1's +5 was tuned live by the user; the firing damage is the "
                              "sniper trigger's clone until boot 1"),
        ],
    },
    # step 5 -- h2_port_collision.py: Bungie's own HALO 2 HAMMER hull (Tartarus's: the same weapon's
    # shape; extract-collision-data only READS his tag), scaled per axis to Halo 3's mesh, on the
    # port's render skeleton (hammer, shaft)
    'collision': {
        'donor': r'objects\weapons\melee\gravity_hammer\gravity_hammer',
        'port': GH + r'\gravity_hammer_port',
        'src': r'gravity_hammer\collision\collision.jms',                # under data\!extracted
        'out': GH + r'\collision\gravity_hammer_port.jms',               # under data
        'port_render_jms': GH + r'\render\gravity_hammer_port.jms',
        'donor_render_jms': r'gravity_hammer\render\L5 gravity_hammer.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
        # Bungie's H2 hammer is BIGGER (render ratio 0.70 / 0.48 / 0.76) and its origin is at the
        # shaft's foot (centre z 39.1 vs Halo 3's 4.6): fitted -- shrunk per axis + re-centred
        'fit': True,
    },
    # step 7 -- the HUD: the Energy Blade's clone (step 3). Its battery bar (disintegrator_meter) and
    # number stay Bungie's (h2_port_meter `backpack_only`: just the stowed icon); the plate painted
    # from Halo 3's mesh (the sword plate's 3 images: single, multi, single_out = the dim twin of 0);
    # Halo 3's crosshair (chud `hammer`: hud_reticles #20 at widget scale 0.59 -- the AR's #0's
    # scale) at Halo 3's ON-SCREEN size: the AR's measured 64 ink px x (ink #20 167 / ink #0 110) = 97
    'meter': {
        'backpack_only': True,
        'port_hud': r'ui\hud\gravity_hammer',
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\gravity_hammer_backpack',
        'backpack_size': (62, 30),
        'model_3p': SIDE_JMS,
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\plasma_sword_bkd',
        'other': NEW_HUD + r'\backgrounds\battle_rifle_bkd',
        'name': 'gravity_hammer_bkd',
        'hud': r'ui\hud\gravity_hammer',
        'model_3p': SIDE_JMS,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        # the sword plate's SIX images: 0 / 1 bright single (64 tall), 2 / 3 the short 'multi'
        # plate (38 tall) whose sword sits 36 px further left (measured: x 69..145 vs 105..181),
        # 4 / 5 the dim twins of 0 / 1
        'all_images': {'dim': {4: 0, 5: 1}, 'boxes': {2: (69, 155, 5, 34), 3: (69, 155, 5, 34)}},
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 20,                # the Energy Blade's fullscreen crosshair
        'name': 'gravity_hammer_reticle',
        'hud': r'ui\hud\gravity_hammer',
        'footprint': 1.0,
        'h3_art': {'sheet': 'hud_reticles', 'sequence': 20, 'yardstick': 20, 'target_ink': 97},
        'preview': 'gravity_hammer_reticle_preview.png',
    },
    # step 8 -- the pickup icon at the reserved U+E142 by the H2 ICON RULE (untinted: white lines, grey
    # body, 160x62), drawn from Halo 3's mesh; the messages be_* -> gh2_* (the beam rifle's lines, the
    # Spartan Laser's donor too: each port renames only its OWN weapon's string ids)
    'glyph': {
        'box': (160, 62),
        'model_3p': SIDE_JMS,
        'tif': 'gravity_hammer_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'be', 'donor_icon': '&beam_rifle',
        'donor_name': 'Beam Rifle', 'port_name': 'Gravity Hammer',
        'weapon': GH + r'\gravity_hammer_port.weapon',
    },
    # step 9 -- h2_port_fp_anims.py: Halo 3's OWN FP hammer animations, both species, through `tool
    # fp-model-animations`. SEEDED from Bungie's H2 ENERGY BLADE graphs: their names are Halo 3's
    # hammer set (idle, melee_lunge / _airborne, melee_strike_1 / _2, moving, overlays, pitch_and_turn,
    # posing:var1, put_away, ready, throw_grenade) -- blend screen + same-name events survive. The one
    # rename: Halo 3's RT SLAM `melee_lunge_unaimed` (46 fr, head down at frame 5 -- Halo 1's A9) is
    # Halo 2's `fire_1` (the trigger route); the jab = melee_strike_1 / _2 (the melee button)
    'fp_anims': {
        'species': {
            'masterchief': {
                'graph': r'objects\characters\masterchief\fp\weapons\melee\fp_gravity_hammer\fp_gravity_hammer.model_animation_graph',
                'arms_rm': r'objects\characters\masterchief\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\melee\fp_gravity_hammer_port',
                'seed': r'objects\characters\masterchief\fp\weapons\melee\fp_energy_blade\fp_energy_blade'},
            'dervish': {
                'graph': r'objects\characters\dervish\fp\weapons\melee\fp_gravity_hammer\fp_gravity_hammer.model_animation_graph',
                'arms_rm': r'objects\characters\dervish\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\melee\fp_gravity_hammer_port',
                'seed': r'objects\characters\dervish\fp\weapons\melee\fp_energy_blade\fp_energy_blade'},
        },
        'weapon_dir': GH + r'\fp_gravity_hammer_port',
        'weapon_rm': H3GH + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'weapon_nodes': ['hammer', 'shaft'],
        'skip': ['first_person:throw_equipment'],      # Halo 2 has no equipment
        'looping': ['first_person:idle', 'first_person:posing:var1'],
        'overlay_reference': 'first_person:idle',
        'rename': {'first_person:melee_lunge_unaimed': 'first_person:fire_1'},
    },
    # 3P (step 4a, user): class 'melee' = the Brute graph's own hammer class (Armed Brutes hold it
    # natively); the player graphs had only 'sword' -> h2_graph_teach cloned it as 'melee'
    # (2026-10-28, under the H2 kit lock): masterchief 5 modes (combat, crouch, spectre_p_l / _r,
    # warthog_p; +2853 bytes, 130 rows), dervish 2 (combat, crouch; +1053 bytes, 44 rows), every
    # original row unchanged; stock kept in E:\HaloBackups\h2_graph_teach. SHARED Bungie tags
    'graph_teach': [(r'objects\characters\masterchief\masterchief.model_animation_graph', 'sword=melee', {}),
                    (r'objects\characters\dervish\dervish.model_animation_graph', 'sword=melee', {})],
    'backup': {'extra': [H2EK + r'\tags\objects\characters\masterchief\masterchief.model_animation_graph',
                         H2EK + r'\tags\objects\characters\dervish\dervish.model_animation_graph',
                         r'E:\HaloBackups\h2_graph_teach\masterchief.model_animation_graph',
                         r'E:\HaloBackups\h2_graph_teach\dervish.model_animation_graph']},
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '07a_highcharity', 'dervish_level': '08b_deltacontrol'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}


# The pickup glyph, HUD plate and backpack icon are SIDE VIEWS (h3_weapon_glyph: x across, z up) --
# right for a gun, but the hammer's shaft runs along z, so Halo 3's mesh drew it standing on end
# (a sliver; the plate stretched it). SIDE_JMS = the port's own world JMS turned -90 deg about y
# (x, y, z) -> (z, y, -x): the shaft across, the head on the RIGHT. Regenerate with
#     python ports_h2\gravity_hammer.py
def write_side_jms():
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_jms
    m = h2_jms.read(_os.path.join(H2EK, 'data', GH, 'render', 'gravity_hammer_port.jms'))
    for v in m.verts:
        x, y, z = v.pos
        v.pos = (z, y, -x)
    m.markers = []
    _os.makedirs(_os.path.dirname(SIDE_JMS), exist_ok=True)
    h2_jms.write(SIDE_JMS, m)
    print('wrote %s (%d verts)' % (SIDE_JMS, len(m.verts)))


if __name__ == '__main__':
    write_side_jms()

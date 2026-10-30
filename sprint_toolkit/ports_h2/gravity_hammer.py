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
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
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
                   # the SWING (the barrel's firing effect): check 10 (before boot 1) -- Halo 3's hammer
                   # has no muzzle flash, its flash is at the head when it lands (= the strike's
                   # detonation here, Tartarus's blast look); the beam rifle's fire effect drew flares,
                   # a bolt trail, arcs and vent smoke at every swing. So the swing = Bungie's ONE-SOUND
                   # battle_rifle\empty.effect clone, its sound the hammer's whoosh (step 10). The wiring
                   # row below still names beam_rifle_fire: that is the weapon's own reference, moved
                   # onto this tag's path; the tag's CONTENT is this clone (re-cloned 2026-10-29)
                   (r'effects\objects\weapons\rifle\battle_rifle\empty.effect',
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
        # boot 1 (07a, user 2026-10-29): no blast, no sound -- Tartarus's impact is placed at the
        # BRUTE's `melee_effect` marker (his graph's event plays it on him); a projectile's
        # detonation has only the engine's point markers (every stock detonation effect: up /
        # forward / normal / backward), so every part was skipped. `up` = the plasma grenade's.
        'string_id_renames': [(FX + r'\gravity_hammer_port_impact.effect', {'melee_effect': 'up'})],
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
            # ENERGY: Halo 3's campaign external aging 0.05 a swing (20), on the barrel (step 4a). Boot 1
            # (user: 'drains 5 per slam, but jumps to 49'): float32 0.05 is 0.0500000007, so the summed
            # age passes n x 0.05 and the floored readout drops a point (65 -> 59, 54, 49 ...). Two
            # float32 steps BELOW 0.05 (0.04999999329) reads 100, 95 ... 5, 0 exactly and the float32
            # sum still reaches 1.0 on swing 20 (simulated; one step lower needs a 21st swing)
            (GH + r'\gravity_hammer_port.weapon', 'age generated per round', 'barrels', 0, 0, 0.04999999329447746),
            # first-person placement: the beam rifle's 0.02, 0, 0; boot 1 on 07a (user): '1 unit down
            # and right' (1 unit = 0.01 wu; +y is left)
            (GH + r'\gravity_hammer_port.weapon', 'first person weapon offset', '', 0, 0, [0.02, -0.01, -0.01]),
            # one slam per Halo 3 RT cycle: melee_lunge_unaimed, 46 frames = 1.533 s (Halo 1's A9)
            (GH + r'\gravity_hammer_port.weapon', 'fire recovery time', 'barrels', 0, 0, 1.533333),
            (GH + r'\gravity_hammer_port.weapon', 'error angle', 'barrels', 0, 1, [0.0, 0.0]),
            # aim (step 4a, the sword's aim ratio onto Halo 3's hammer 10 / 1.75, 10 / 6)
            (GH + r'\gravity_hammer_port.weapon', 'autoaim angle', '', 0, 0, 6.0),
            (GH + r'\gravity_hammer_port.weapon', 'autoaim range', '', 0, 0, 4.2),
            (GH + r'\gravity_hammer_port.weapon', 'magnetism angle', '', 0, 1, 12.0),
            (GH + r'\gravity_hammer_port.weapon', 'magnetism range', '', 0, 1, 8.0),
            # the melee pyramid: Halo 3's own, as the Melee Seeking cards read it (balance_port: 0.2 rad
            # = 11.46 deg both ways, depth 0.8; the export prints the weapon's top-level 0 / 0). The
            # ANGLES are a 'real euler angles 2d' h2_tagfield does not write: the Balanced catalog row
            # sets them; the unbalanced build keeps the beam rifle's 20 x 10
            (GH + r'\gravity_hammer_port.weapon', 'damage pyramid depth', '', 0, 0, 0.8),
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
            # the MATERIAL RESPONSES (elements 1-9, both `response` rows of 3 / 4 / 6; the others read 0
            # already) were written to 0 = 'impact (detonate)' ONCE (2026-10-29) and verified in tool's
            # export (all 20 detonate). Not re-run rows: a 0 cannot be found again by value and the
            # step-10 repoint moved the tag's offsets -- a re-clone of the strike must write them again
            # THE WIELDER SHOVE (boot 1, 07a, user: 'the small player pushback is missing'): Halo 1's
            # recipe (ports_h1 gravity_hammer, user-tuned live): the FIRING damage on the wielder, a
            # token 0.01 (0 damage pushed nothing) and +5 acceleration (positive = backwards). All
            # three read 0: pinned from `active camouflage damage` (0.75; the explosion clone's
            # measured layout: lower bound -20, upper bounds -16; acceleration +20, probed: a pad word
            # follows stun time)
            (GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect', 'damage lower bound', '', 0, 0, 0.01,
             {'anchor': ('active camouflage damage', -20)}),
            (GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect', 'damage upper bound', '', 0, 0, [0.01, 0.01],
             {'anchor': ('active camouflage damage', -16)}),
            (GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect', 'instantaneous acceleration', '', 0, 0, 5.0,
             {'anchor': ('active camouflage damage', 20)}),
            # Armed test 1 (user: Elites 'get turned around when they swing'): the shove hit the AI
            # wielder too. jpt flags bit 1 'Area Damage Players Only' + bit 0 'Don't Scale By Distance'
            # with a radius of 1.5: the shove becomes AREA damage, which AI units ignore. Layout as the
            # explosion clone's (radius camo -48, flags -36)
            (GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect', 'radius', '', 0, 0, [2.5, 2.5],
             {'anchor': ('active camouflage damage', -48)}),
            (GH + r'\damage_effects\gravity_hammer_port_trigger.damage_effect', 'flags', '', 0, 0, 3,
             {'anchor': ('active camouflage damage', -36)}),
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
            # step 4b (2026-10-29): the blast's camera shake + outward push are Halo 3's own (zero in
            # Tartarus's clone: no ratio from a zero)
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'shake radius', '', 0, 0, 10.0),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'outward velocity', '', 0, 0, 15.0),
            (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect', 'outward radius', '', 0, 0, 1.0),
            # step 4b list 4 / 5: the beam rifle's leftovers -> the yardstick sword's (no heat, no
            # camo ding, no thrown-weapon collision damage, the sword's AI scariness 16)
            (GH + r'\gravity_hammer_port.weapon', 'overheated heat loss per second', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'active camo ding', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'Apply collision damage scale', '', 0, 0, 0.0),
            (GH + r'\gravity_hammer_port.weapon', 'AI scariness', '', 0, 0, 16.0),
            # THE JAB (melee button): Halo 3's smash_melee 80, accel 1
            (GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect', 'damage lower bound', '', 0, 0, 80.0),
            (GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect', 'damage upper bound', '', 0, 0, [80.0, 80.0]),
        ],
        'skipped': [],
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
        # BOOT 1 (user, 07a: 'the HUD symbol is not clean'): the boxes came from the diff against the
        # BR plate (105..191 x 5..34), which missed the sword's hilt curve -- its cyan arc (top left)
        # and blue under-blade stood beside the hammer. Measured on Bungie's plate (blue over green
        # + 40): the sword spans x 98..190 y 4..33 (0 / 1) and x 62..152 (2 / 3) -- the boxes cover it.
        # Each box's right sample column must be plate, not border: the ROUNDED images (1 / 3) reach
        # their corner line at 193 from row 2 down, its antialiased edge at 192 on row 3 (first tries smeared
        # it across the top)
        'all_images': {'dim': {4: 0, 5: 1},
                       'boxes': {0: (96, 193, 3, 34), 1: (96, 192, 4, 34),
                                 2: (60, 157, 3, 34), 3: (60, 157, 3, 34)}},
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
        # every animation's frame + sound events = Halo 3's own (the Spike Rifle's rule), onto the
        # graph's own sounds (step 10 repointed the seed's sword refs: gh_melee / gh_ready / gh_posing)
        'source_events': {'sounds': {'hammer_melee': 'gh_melee', 'hammer_ready': 'gh_ready',
                                     'hammer_posing': 'gh_posing'}},
    },
    # step 10 -- h2_port_sounds.py: Halo 3's OWN five hammer sounds from MCC's halo3 sfx.fsb (classic
    # Opus): hammer_melee (the swings), hammer_ready, hammer_posing, hammer_hit (the BLAST: the impact
    # effect's Tartarus hits + its remastered layers), hammer_drops (the head on a surface AND the
    # dropped weapon -- distinct from the blast: Halo 1's A9 rule, a hit and the blast must sound
    # different). The beam rifle's never-played refs (zoom, misfire, ammo pickup) -> own sounds too
    'sounds': {
        'weapon': GH + r'\gravity_hammer_port.weapon',
        'fire_fx': FX + r'\gravity_hammer_port_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'gravity_hammer'),
        'audio_key': 'Gravity Hammer',
        'h3_bank': {'gh_melee': [H3SND + r'\gravity_hammer\fp_hammer\hammer_melee'],
                    'gh_ready': [H3SND + r'\gravity_hammer\fp_hammer\hammer_ready'],
                    'gh_posing': [H3SND + r'\gravity_hammer\fp_hammer\hammer_posing'],
                    'gh_hit': [H3SND + r'\gravity_hammer\hammer_hit'],
                    'gh_drop': [H3SND + r'\gravity_hammer\hammer_drops']},
        'sounds': {'gh_melee': ('gh_melee', 'weapon_melee'), 'gh_ready': ('gh_ready', 'weapon_ready'),
                   'gh_posing': ('gh_posing', 'weapon_ready'),
                   'gh_hit': ('gh_hit', 'projectile_detonation'),
                   'gh_drop': ('gh_drop', 'object_impacts')},
        'repoint_tags': ([(FX + r'\gravity_hammer_port.material_effects', r'sound\weapons\impacts_riccs\%s' % old, 'gh_drop')
                          for old in ('bullet_impact_dirt', 'bullet_impact_energy', 'bullet_impact_flesh_dry',
                                      'bullet_impact_glass', 'bullet_impact_metal_thick', 'bullet_impact_metal_thick_r',
                                      'bullet_impact_metal_thin', 'bullet_impact_stone', 'bullet_impact_stone_r',
                                      'bullet_impact_vehicle', 'bullet_impact_vest', 'bullet_impact_water',
                                      'bullet_impact_wood')]
                         + [(FX + r'\gravity_hammer_port.material_effects', r'sound\weapons\beam_rifle\%s' % old, 'gh_drop')
                            for old in ('beam_rifle_drop', 'beam_rifle_drop_soft')]
                         + [(FX + r'\gravity_hammer_port_impact.effect', old, 'gh_hit')
                            for old in (r'sound\characters\brute\tartarus_hits',
                                        r'sound_remastered\characters\brute\tatarus_hammer_hits\hits_stereo',
                                        r'sound_remastered\characters\brute\tatarus_hammer_hits\hits_swtnr',
                                        r'sound_remastered\ambience\device_machines\scarab\scarab_steps_lfe')]
                         + [(GH + r'\projectiles\gravity_hammer_port_strike.projectile',
                             r'sound\weapons\impacts_riccs\bullet_flyby_short', 'gh_melee')]
                         + [(r'objects\characters\%s\fp\weapons\melee\fp_gravity_hammer_port\fp_gravity_hammer_port.model_animation_graph' % sp,
                             r'sound_remastered\weapons\energy_sword\%s' % old, 'gh_melee')
                            for sp in ('masterchief', 'dervish')
                            for old in ('energy_melee_swtnr', 'energy_melee_swtnr_elec')]),
        'repoint_fx': [(r'sound\weapons\battle_rifle\dryfire', 'gh_melee')],   # the swing (check 10)
        'repoint_weapon': [(r'sound\weapons\beam_rifle\beam_rifle_misfire', 'gh_melee'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_in', 'gh_ready'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_out', 'gh_ready'),
                           (r'sound\weapons\sniper_rifle\sniper_ammo', 'gh_ready')],
        'graph_sounds': (('energy_melee_1', 'gh_melee'), ('energy_melee_2', 'gh_melee'),
                         ('energy_sword_pose', 'gh_posing'), ('sword_ready', 'gh_ready')),
        'graph_sound_dir': r'sound\weapons\energy_sword' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_gravity_hammer_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_gravity_hammer_graphs_before_sounds',
    },
    # step 4b -- port_field_audit.py --port gravity_hammer: every field NO card covers where Halo 3's
    # hammer differs from Halo 3's sword (the yardstick) -- Halo 1's A9 pairs: the weapon, the BLAST
    # (as damage_effect, against the sword's dash), the JAB (melee), the SLAM (impact: crush vs dash)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3GH + r'\gravity_hammer.weapon', r'objects\weapons\melee\energy_blade\energy_blade.weapon'),
                   'damage_effect': (H3GH + r'\damage_effects\gravity_hammer_explosion.damage_effect',
                                     r'objects\weapons\damage_effects\dash_melee.damage_effect'),
                   'melee': (r'objects\weapons\damage_effects\smash_melee.damage_effect',
                             r'objects\weapons\damage_effects\dash_melee.damage_effect'),
                   'impact': (r'objects\weapons\damage_effects\crush_melee.damage_effect',
                              r'objects\weapons\damage_effects\dash_melee.damage_effect')},
        'target': {'weapon': (GH + r'\gravity_hammer_port.weapon', BLADE + r'\energy_blade.weapon'),
                   'damage_effect': (GH + r'\damage_effects\gravity_hammer_port_explosion.damage_effect',
                                     r'objects\weapons\damage_effects\dash_melee.damage_effect'),
                   'melee': (GH + r'\damage_effects\gravity_hammer_port_melee.damage_effect',
                             r'objects\weapons\damage_effects\slice_melee.damage_effect'),
                   'impact': (GH + r'\damage_effects\gravity_hammer_port_slam.damage_effect',
                              r'objects\weapons\damage_effects\dash_melee.damage_effect')},
        # the run of 2026-10-29 (report: reports/h2_gravity_hammer_4b.txt), decided:
        'decisions': {
            'jab (melee) list 2: damage 37.3 / accel 0.67 / rotation 0.72 / pushback 0.125':
                "the sword's STRIKE ratio -- step 4a chose the LUNGE ratio x1.0 (user): Halo 3's own 80 / 1 / 1.2 / 0.25",
            'blast list 2: instantaneous acceleration 2.33': "the same: Halo 3's own 3.5 (step 4a)",
            'weapon list 2: bounding radius / acceleration scale / damage pyramid = 0':
                "Halo 3's hammer leaves the TOP-LEVEL fields 0; no ratio from a zero -- the beam rifle's "
                "bounding radius 0.4125 / acceleration scale 1 kept; the pyramid = Halo 3's own from its melee "
                "parameters (11.46 x 11.46 at 0.8, read by the Melee Seeking cards; numbers + catalog)",
            'weapon list 4 / 5: overheated heat loss 0.3, camo ding 1, collision damage scale 8, AI scariness 6':
                "the beam rifle's -> the sword's 0 / 0 / 0 / 16 (numbers)",
            'first person weapon offset': "the beam rifle's 0.02, 0, 0 until boot 1",
            'blast list 3: shake radius 10, outward velocity 15, outward radius 1': "Halo 3's own (numbers)",
            'blast list 3: rider scales, random translation, wobble, falloff early, impulse / shake duration':
                "Tartarus's clone's kept (riders: Rider Damage is not carded from Halo 2 on this weapon; the "
                "rest have no Halo 2 field or are feel, decided in game)",
            "blast flags (Halo 3 2049)": "Halo 2 bit 0 'does not hurt owner' (numbers); 'transfer dmg always uses min' has no H2 bit",
            'functions / attachments': "the beam rifle's one attachment = its overheat loop, scaled by "
                                       "'overheated' -- never plays (no heat); Halo 3's hammer_on arcs not ported "
                                       "(no free attachment slot without a block insert; check 10)",
            'external / campaign external aging': "no Halo 2 field: the barrel's age per round 0.05 (step 4a)",
            'weapon type / tracking type / melee damage reporting type': "Halo 2's enums kept (kill feed only)",
        }},
    # make_port_catalog_h2.py gravity_hammer: balance_port.py "Gravity Hammer" "Energy Blade" "Halo 3"
    # "Halo 2" gives the AIM rows (the sword's ratio: magnetism 12 / 8, autoaim 6 / 4.2) and the melee
    # pyramid (Halo 3's 11.46 x 11.46 at 0.8, x1) on the sword's tag -> redirected onto the port's.
    # The sword has no damage / radius / energy cards to measure through: those rows are Halo 3's own
    # (step 4a, user: the LUNGE ratio x1.0 -- slam 150, jab 80, blast 50..160 over 0.75-1.5, 0.05 a
    # swing), given whole (extra_rows)
    'catalog': {
        'table': 'balance_Gravity_Hammer_Halo3_to_Halo2.json',
        'weapon_tag': GH + r'\gravity_hammer_port',
        'port_tags': [(('weap', BLADE + r'\energy_blade'), GH + r'\gravity_hammer_port')],
        'shared': [],
        'extra_rows': ([{'class': 'jpt!', 'tag': GH + r'\damage_effects\gravity_hammer_port_%s' % tag,
                         'field': field, 'block': None, 'value': value, 'card': card, 'original': value,
                         'note': "Halo 3's own (step 4a, user: the sword's lunge ratio x1.0)"}
                        for tag, card, lo, hi in (('slam', 'Hammer Damage', 150.0, 150.0),
                                                  ('explosion', 'Hammer Damage', 50.0, 160.0),
                                                  ('explosion_ai', 'Hammer Damage', 50.0, 160.0),
                                                  ('melee', 'Melee Damage', 80.0, 80.0))
                        for field, value in (('Damage Lower Bound', lo), ('Damage Upper Bound', hi),
                                             ('Damage Upper Bound Max', hi))]
                       + [{'class': 'jpt!', 'tag': GH + r'\damage_effects\gravity_hammer_port_%s' % tag,
                           'field': field, 'block': None, 'value': value, 'card': 'Hammer Radius',
                           'original': value, 'note': "Halo 3's own (step 4a)"}
                          for tag in ('explosion', 'explosion_ai')
                          for field, value in (('Radius', 0.75), ('Radius Max', 1.5))]
                       + [{'class': 'weap', 'tag': GH + r'\gravity_hammer_port', 'field': 'Age Generated Per Round',
                           'block': 'Barrels', 'value': 0.04999999329447746, 'card': 'Energy Use',
                           'original': 0.04999999329447746,
                           'note': "Halo 3's campaign external aging a swing, on the barrel (step 4a: the trigger "
                                   "route); 0.05 two float32 steps down, so the readout steps 5 exactly (boot 1)"}]),
        'fp_animations': r'objects\characters\*\fp\weapons\melee\fp_gravity_hammer_port\fp_gravity_hammer_port',
        'reload_mult': None,
        'desc': ("Halo 3's Gravity Hammer carried into Halo 2 as a player weapon with its own model, textures, "
                 "sounds and its own Halo 3 first-person animations for both species: fire slams the head down "
                 "(150) into a blast (up to 160 over 1.5 wu), 20 slams a charge; melee jabs with the pommel (80). "
                 "Tartarus's own hammer is untouched."),
    },
    # 3P (step 4a, user): class 'melee' = the Brute graph's own hammer class (Armed Brutes hold it
    # natively); the player graphs had only 'sword' -> h2_graph_teach cloned it as 'melee'
    # (2026-10-28, under the H2 kit lock): masterchief 5 modes (combat, crouch, spectre_p_l / _r,
    # warthog_p; +2853 bytes, 130 rows), dervish 2 (combat, crouch; +1053 bytes, 44 rows), every
    # original row unchanged; stock kept in E:\HaloBackups\h2_graph_teach. SHARED Bungie tags
    'graph_teach': [(r'objects\characters\masterchief\masterchief.model_animation_graph', 'sword=melee', {}),
                    (r'objects\characters\dervish\dervish.model_animation_graph', 'sword=melee', {}),
                    # boot on Sacred Icon + The Great Journey (user: 'Plasma Pistol only'): the game
                    # refused the hammer on the Arbiter -- dervish's sword class holds 4 actions (land,
                    # turn), the idle / moves come from its PARENT graph's combat > sword, and the
                    # Elite graph had no `melee`. A class must exist in the parent too
                    (r'objects\characters\elite\elite.model_animation_graph', 'sword=melee', {}),
                    # Armed test 1 (Gravemind): `melee` in the TAG with a `gh` row that CARRIES fire_1
                    # (h2_graph_teach --clone <class>=melee --type <row>=gh): the patch-time teach then
                    # has nothing to do, and its `gh` copy of the `any` row has no fire_1 at all (their
                    # fire overlays sit on the type rows). Plus the Flood, which refused the hammer
                    # (no TEACH entry in h2_enemy_weapons, no melee class). Brute + Elite: --fire-rows
                    (r'objects\characters\grunt\grunt.model_animation_graph', 'missile=melee', {'rl': 'gh'}),
                    (r'objects\characters\jackal\jackal.model_animation_graph', 'pistol=melee', {'pr': 'gh'}),
                    (r'objects\characters\bugger\bugger.model_animation_graph', 'pistol=melee', {'pp': 'gh'}),
                    (r'objects\characters\floodcombat_human\floodcombat_human.model_animation_graph', 'rifle=melee', {'br': 'gh'}),
                    (r'objects\characters\floodcombat_elite\floodcombat_elite.model_animation_graph', 'rifle=melee', {'br': 'gh'})],
    'backup': {'extra': [H2EK + r'\tags\objects\characters\masterchief\masterchief.model_animation_graph',
                         H2EK + r'\tags\objects\characters\dervish\dervish.model_animation_graph',
                         r'E:\HaloBackups\h2_graph_teach\masterchief.model_animation_graph',
                         H2EK + r'\tags\objects\characters\elite\elite.model_animation_graph',
                         r'E:\HaloBackups\h2_graph_teach\dervish.model_animation_graph',
                         r'E:\HaloBackups\h2_graph_teach\elite.model_animation_graph']
                        + [H2EK + r'\tags\objects\characters\%s\%s.model_animation_graph' % (_sp, _sp)
                           for _sp in ('brute', 'grunt', 'jackal', 'bugger', 'floodcombat_human', 'floodcombat_elite')]
                        + [r'E:\HaloBackups\h2_graph_teach\%s.model_animation_graph' % _sp
                           for _sp in ('jackal', 'bugger', 'floodcombat_human', 'floodcombat_elite')]},
    # step 11 -- `python ai_firing_profile.py --h2-port gravity_hammer`: Halo 3's ai\generic hammer
    # entry (010_jungle) name-for-name over the H2 ENERGY BLADE's (the yardstick; Halo 2's only
    # player melee weapon with an ai\generic entry -- Tartarus's hammer data lives in his own
    # character, never touched)
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
                       'donor_weapon': BLADE + r'\energy_blade',
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
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


# Boot 1 (07a, 2026-10-29), BLANKED references (length 0, path removed: h2_tagref's empty reference;
# identical pooled strings, so only which record is zeroed matters -- tool's reference list and every
# field row decide). Run after the sounds + fp_anims steps:  python ports_h2\gravity_hammer.py --blank
#   - Tartarus's impact LAYERS four sounds (tartarus_hits + three remastered layers); the sounds step
#     repoints all four onto gh_hit, which played Halo 3's ONE hammer_hit four times at once (Halo 3's
#     gravity_hammer_impact.effect has one sound part): the three later parts blanked;
#   - the Chief's FP graph (seeded from the Energy Blade's) kept the sword's blade_activate EFFECT on
#     `ready` (frame 1): Halo 3's hammer ready plays hammer_ready only (no effect event) -- blanked.
BLANKS = [(FX + r'\gravity_hammer_port_impact.effect', 'snd!', r'sound\weapons\gravity_hammer_port\gh_hit', 1),
          (r'objects\characters\masterchief\fp\weapons\melee\fp_gravity_hammer_port'
           r'\fp_gravity_hammer_port.model_animation_graph', 'effe',
           r'effects\objects\weapons\melee\energy_blade\blade_activate', 0),
          # Armed test 2: the firing damage (the wielder shove) off -- it moved into the blast, below
          (GH + r'\gravity_hammer_port.weapon', 'jpt!', GH + r'\damage_effects\gravity_hammer_port_trigger', 0)]


def blank(rel, cls, path, keep):
    """Every `cls` reference to `path` in `rel` but `keep` of them made empty."""
    import struct
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_tagref as R
    import h2_tagfield as tf
    tag = _os.path.join(H2EK, 'tags', rel)
    before = R.references(tag)
    if before.count((cls, path)) <= keep:
        print('%s: %s x%d already' % (_os.path.basename(tag), _os.path.basename(path), keep))
        return
    original = open(tag, 'rb').read()
    rows = [r[4] for r in tf.read_all(tf.export(tag))]
    want = [r for r in before if r != (cls, path)]
    if keep:
        want.insert(before.index((cls, path)), (cls, path))
    recs = R.records(original, len(path), cls)
    raw = path.encode('latin-1') + b'\0'
    for kept in (range(len(recs)) if keep else [None]):
        out = bytearray(original)
        for i, rec in enumerate(recs):
            if i != kept:
                struct.pack_into('<I', out, rec + 8, 0)
        for _n in range(len(recs) - keep):
            at = R.pooled(bytes(out), path)[-1]
            del out[at:at + len(raw)]
        open(tag, 'wb').write(bytes(out))
        x = tf.export(tag)
        now = [r[4] for r in tf.read_all(x)] if x else None
        if R.references(tag) == want and now == rows:
            print('%s: %s x%d -> x%d (%d references, every field as before)'
                  % (_os.path.basename(tag), _os.path.basename(path), len(recs), keep, len(want)))
            return
    open(tag, 'wb').write(original)
    raise ValueError('no blanking of %s worked; %s restored' % (path, _os.path.basename(tag)))


# Armed test 1 (Gravemind, 2026-10-30, user: 'Brutes hold it awkwardly and have no attack animation';
# 'do Grunts have an animation when attacking?'). A unit's FIRE animation is the `fire_1` OVERLAY of
# its class + type row, and the classes the hammer lands in have none:
#   - the Brute's own hammer class (melee / any: the real hold) has none, and h2_enemy_weapons'
#     type teach copied support / any over it as `gh` (the Brute Shot hold): a `gh` row in the TAG
#     stops that teach (it skips a type the class holds) and carries fire_1 = Tartarus's own overlay
#     swing berserk:melee:leap_melee (replacement, 24 fr) -- DUPLICATED without its events (its
#     effect event is Tartarus's blast, which would go off on top of the port's), Tartarus's stays;
#   - the Elite's melee (sword clone) has none: fire_1 = its rifle's, an approximation.
# LOOSE ANIMATION ELEMENT (136 bytes, read on brute.model_animation_graph): +0 name sid, +0x34 the
# blob's size, block counts +0x58 frame / +0x64 sound / +0x70 effect / +0x7C object-space parents
# (12 bytes each). Its data: the name, the blob (animation data is INLINE, nothing is shared; 16
# more bytes may follow it), then the chunks of those blocks; a sound event's marker sid (+4) pools
# its string after its chunk, an object-space element's 'SSoq' descriptor after the chunk's array.
#     python ports_h2\gravity_hammer.py --fire-rows      (under the H2 kit lock)
SIG = b'dfbt'
ANIM_ES = 136
ANIM_BLOCKS = (0x58, 0x64, 0x70, 0x7C)
FIRE_ROWS = [(r'objects\characters\brute\brute.model_animation_graph', ('combat', 'berserk', 'patrol', 'hoist', 'vault'), 'melee',
              ('clone', 'berserk:melee:leap_melee', 'combat:melee:gh:fire_1')),
             (r'objects\characters\elite\elite.model_animation_graph', ('combat',), 'melee',
              ('overlay', 'combat', 'rifle', 'any'))]


def _anim_block(d, names):
    """(chunk, count, [(name, struct, data start, data end, first chunk or None)]) -- `names` =
    tool's animation names in order (an element's size is not fully stored: a blob may be followed
    by a 16-byte descriptor, so the next element is found by its name)."""
    import struct
    at, n = -1, len(names)
    i = d.find(SIG, 0x40)
    while i >= 0:
        if struct.unpack_from('<II', d, i + 8) == (n, ANIM_ES):
            at = i
            break
        i = d.find(SIG, i + 4)
    if at < 0:
        raise ValueError('no block of %d animations' % n)
    out, p = [], at + 16 + n * ANIM_ES
    for i, name in enumerate(names):
        e = at + 16 + i * ANIM_ES
        raw = name.encode('latin-1')
        if d[p:p + len(raw)] != raw or d[e + 3] != len(raw):
            raise ValueError('%s is not at 0x%X' % (name, p))
        blob_end = p + len(raw) + struct.unpack_from('<I', d, e + 0x34)[0]
        if any(struct.unpack_from('<I', d, e + o)[0] for o in ANIM_BLOCKS):
            first = d.find(SIG, blob_end)
            if not 0 <= first - blob_end <= 32:
                raise ValueError('%s: no chunk after its blob (0x%X)' % (name, blob_end))
        else:
            first = None
        if i + 1 < n:
            end = d.find(names[i + 1].encode('latin-1'), blob_end)
            if end < 0 or end - blob_end > 1 << 20:
                raise ValueError('%s: next name not found' % name)
        else:
            end = _chunks(d, e, first, blob_end)['end']
        out.append((name, e, p, end, first))
        p = end
    return at, n, out


def _chunks(d, e, first, blob_end):
    """Where each event block's chunk lies. Object-space parents: 28-byte elements + a 'SSoq'
    descriptor each after the array."""
    import struct
    out, p = {}, first if first is not None else blob_end
    for off in ANIM_BLOCKS:
        if not struct.unpack_from('<I', d, e + off)[0]:
            continue
        if d[p:p + 4] != SIG:
            raise ValueError('no chunk at 0x%X' % p)
        cn, csz = struct.unpack_from('<II', d, p + 8)
        q = p + 16 + cn * csz
        if off == 0x64:                     # the sound events' marker strings
            q += sum(d[p + 16 + k * csz + 7] for k in range(cn))
        if off == 0x7C:
            q += 16 * cn
        out[off] = (p, q)
        p = q
    out['end'] = p
    return out


def clone_animation(d, src, new, names):
    """`d` with animation `src` duplicated as `new`, no frame / sound / effect events; its index."""
    import struct
    if new in names:
        return d, names.index(new)
    at, n, rows = _anim_block(bytes(d), names)
    name, e, start, end, first = rows[names.index(src)]
    elem = bytearray(d[e:e + ANIM_ES])
    struct.pack_into('<I', elem, 0, len(new) << 24)
    for off in ANIM_BLOCKS[:3]:
        struct.pack_into('<II', elem, off, 0, 0)
    blob_end = start + len(name) + struct.unpack_from('<I', d, e + 0x34)[0]
    spans = _chunks(d, e, first, blob_end)
    keep = bytes(d[spans[0x7C][0]:spans[0x7C][1]])
    data = new.encode('latin-1') + bytes(d[start + len(name):first]) + keep
    tail = rows[-1][3]
    d[tail:tail] = data
    d[at + 16 + n * ANIM_ES:at + 16 + n * ANIM_ES] = elem
    struct.pack_into('<I', d, at + 8, n + 1)
    # the count's second copy: the root struct's block field
    hits = [i for i in range(0x40, at, 4) if struct.unpack_from('<I', d, i)[0] == n]
    if len(hits) != 1:
        raise ValueError('%d root copies of the animation count' % len(hits))
    struct.pack_into('<I', d, hits[0], n + 1)
    return d, n


def add_fire_row(d, mode, cls, index):
    """`d` with a `gh` weapon type on mode > class holding one overlay, fire_1 -> animation `index`
    (the row's bytes copied from a one-overlay row of the same graph)."""
    import struct
    import h2_graph_teach as G
    at, end, elems, chunks = G.modes_chunk(bytes(d))
    donor = next(e for e in elems if e[0] == 'type' and
                 [struct.unpack_from('<I', d, e[3] + o)[0] for o in (4, 16, 28, 40, 52, 64)] == [0, 1, 0, 0, 0, 0])
    m = next(e for e in elems if e[0] == 'mode' and e[1] == at and G.label(d, e) == mode)
    c = next(e for e in elems if e[0] == 'class' and m[4] <= e[3] < m[5] and G.label(d, e) == cls)
    tc = next(k for k, v in chunks.items() if v[0] == 'type' and c[4] <= k < c[5])
    rows = [e for e in elems if e[0] == 'type' and e[1] == tc]
    if 'gh' in [G.label(d, e) for e in rows]:
        return d, False
    _so, ds, de = donor[3], donor[4], donor[5]
    old = G.label(d, donor)
    raw = bytes(d[ds:de])
    chunk = raw[len(old):]                       # dfbt header, the overlay struct, its string + IINA
    ov_at = 16
    old_ov = chunk[ov_at + 3]
    ov = bytearray(chunk[ov_at:ov_at + 8])
    pair = bytes(ov[4:8])
    struct.pack_into('<I', ov, 0, 6 << 24)
    new_pair = struct.pack('<hh', -1, index)
    ov[4:8] = new_pair
    rest = chunk[ov_at + 8 + old_ov:]
    if rest.count(pair) > 1:
        raise ValueError('the donor overlay index is ambiguous')
    data = b'gh' + chunk[:ov_at] + bytes(ov) + b'fire_1' + rest.replace(pair, new_pair)
    st = bytearray(d[donor[3]:donor[3] + 76])
    struct.pack_into('<I', st, 0, 2 << 24)
    _k, n, sz, cend = chunks[tc]
    d[cend:cend] = data
    d[tc + 16 + n * sz:tc + 16 + n * sz] = st
    struct.pack_into('<I', d, tc + 8, n + 1)
    struct.pack_into('<I', d, c[3] + 4, n + 1)
    return d, True


def fire_rows():
    import os
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_graph_teach as G
    import h2_stringid
    import h2_tagfield as tf
    import re
    import struct
    dry = '--dry' in sys.argv
    for rel, mode, cls, how in FIRE_ROWS:
        path = _os.path.join(H2EK, 'tags', rel)
        original = open(path, 'rb').read()
        keep = _os.path.join(G.BACKUP, _os.path.basename(path))
        if not _os.path.exists(keep):
            raise SystemExit('no stock copy of %s on E:' % path)
        d = bytearray(original)
        if how[0] == 'clone':
            x = tf.export(path)
            pool = x[x.find('<block name="animations"'):x.find('<block name="modes">')]
            names = re.findall(r'<element index="\d+">\s*<field name="name" type="string id">([^<]*)<', pool)
            d, index = clone_animation(d, how[1], how[2], names)
        else:
            at, end, elems, chunks = G.modes_chunk(bytes(d))
            m = next(e for e in elems if e[0] == 'mode' and e[1] == at and G.label(d, e) == how[1])
            c = next(e for e in elems if e[0] == 'class' and m[4] <= e[3] < m[5] and G.label(d, e) == how[2])
            t = next(e for e in elems if e[0] == 'type' and c[4] <= e[3] < c[5] and G.label(d, e) == how[3])
            o = next(e for e in elems if e[0] == 'action' and t[4] <= e[3] < t[5] and G.label(d, e) == 'fire_1')
            index = struct.unpack_from('<h', d, o[3] + 6)[0]
        for one in mode:                 # every mode of the class: the type teach fills any left out
            d, _added = add_fire_row(d, one, cls, index)
        if bytes(d) == original:
            print('%s: fire row already there' % _os.path.basename(path))
            continue
        G.modes_chunk(bytes(d))
        if dry:
            print('%s: dry, +%d bytes, fire_1 -> animation %d' % (_os.path.basename(path), len(d) - len(original), index))
            continue
        before = h2_stringid.export(path)
        open(path, 'wb').write(bytes(d))
        after = h2_stringid.export(path)
        lost = [r for r in before if r not in after]
        if lost or not any(r[2] == 'gh' for r in after):
            open(path, 'wb').write(original)
            raise SystemExit('%s refused, restored: %d rows lost %s' % (path, len(lost), lost[:3]))
        print('%s: gh row + fire_1 -> animation %d, +%d bytes, %d more rows, every original row '
              'unchanged' % (_os.path.basename(path), index, len(d) - len(original), len(after) - len(before)))


# Armed test 2 (Gravemind, user: 'even weirder grip'): Bungie's hammer has a third hand marker,
# right_hand_brute (the Brute's right hand; Halo 3's mesh has none, so Brutes took the Chief's). Their
# hold spreads the hands 37 units along a bent shaft (R 5.67, 1.28, 19.36; L -1.04, 0.54, 55.77 on
# Bungie's mesh), the port's is straight: the marker puts the port's shaft through BOTH hand points,
# the left hand just under the head (z 19), so the right one is 37.03 lower, and turns it by the
# hands' tilt. Node 0, JMS units. A geometry re-run drops it: run after it.
#     python ports_h2\gravity_hammer.py --brute-grip     (under the H2 kit lock)
def brute_grip():
    import math
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_jms
    import h2_port_geometry
    r = (5.67, 1.28, 19.36)
    l = (-1.04, 0.54, 55.77)
    q = (-0.009396, 0.190417, -0.144801, -0.970920)      # Bungie's right_hand_brute (x, y, z, w)
    d = [b - a for a, b in zip(r, l)]
    span = math.sqrt(sum(c * c for c in d))
    half = math.atan2(d[0], d[2]) / 2.0
    rx, ry, rz, rw = 0.0, -math.sin(half), 0.0, math.cos(half)      # the tilt, inverted
    x, y, z, w = q
    rot = (rw * x + rx * w + ry * z - rz * y, rw * y - rx * z + ry * w + rz * x,
           rw * z + rx * y - ry * x + rz * w, rw * w - rx * x - ry * y - rz * z)
    path = _os.path.join(H2EK, 'data', GH, 'render', 'gravity_hammer_port.jms')
    m = h2_jms.read(path)
    m.markers = [k for k in m.markers if k.name != 'right_hand_brute']
    m.markers.append(h2_jms.Marker('right_hand_brute', 0, rot, (0.0, 0.0, 19.0 - span), -1.0))
    h2_jms.write(path, m)
    print('right_hand_brute at z %.2f, rot %s' % (19.0 - span, ['%.4f' % c for c in rot]))
    g = PORT['geometry']
    h2_port_geometry.tool_render(g, g.get('render') or [])


# Armed test 2 (user: 'they still get affected by their own pushback'): a FIRING damage hits its
# wielder directly, whoever that is, and 'Area Damage Players Only' cannot apply to it (and a hurt AI
# turns round to look for the attacker). The shove moves into the BLAST: the impact effect's free
# (blanked) part carries the same jpt as AREA damage, players only, radius 2.5 from the burst (1.2 wu
# out) -- no AI wielder feels it, and a player in reach is thrown back from the head. Halo 1's user
# rule: 'the shockwave should push the player slightly backwards'.
#     python ports_h2\gravity_hammer.py --blast-shove    (--blank first)
def blast_shove():
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_tagref as R
    tag = _os.path.join(H2EK, 'tags', FX + r'\gravity_hammer_port_impact.effect')
    jpt = GH + r'\damage_effects\gravity_hammer_port_trigger'
    if ('jpt!', jpt) in R.references(tag):
        print('the blast already carries the shove')
        return
    R.fill_reference(tag, 'snd!', jpt)
    R.set_class(tag, 'snd!', jpt, 'jpt!')
    print(R.references(tag))


# Armed test 3 (Gravemind; user's choices 2026-10-30: 'melee swing = blast', 'try a grenade throw').
# Bungie's sword and hammer are MELEE ONLY (no trigger, no barrel): their AI charges and its attack is
# the melee animation, Tartarus's blast an EFFECT EVENT in it. The port needs a trigger (the player's
# 5 energy a slam), so its AI charged, then meleed with no blast. So:
#   - Brute + Elite: the `gh` row's `melee` action = a DUPLICATE of their melee swing whose effect
#     event (at the hit frame) plays gravity_hammer_port_impact_ai: the impact effect at the UNIT's
#     `melee_effect` / `melee` marker (`up` only exists for a projectile's detonation);
#   - Grunts + Jackals have no melee at all: fire_1 = a duplicate of throw_grenade (Grunt) / shakefist
#     (Jackal, it has no throw) played as a REPLACEMENT overlay, an experiment.
#     python ports_h2\gravity_hammer.py --ai-swings      (under the H2 kit lock)
AI_IMPACT = FX + r'\gravity_hammer_port_impact_ai'
AI_SWINGS = [(r'objects\characters\brute\brute.model_animation_graph', 'melee', 'combat:melee:melee:var1', 'combat:melee:gh:melee', 'melee_effect'),
             (r'objects\characters\elite\elite.model_animation_graph', 'melee', 'combat:sword:melee:var0', 'combat:melee:gh:melee', 'melee')]
AI_OVERLAYS = [(r'objects\characters\grunt\grunt.model_animation_graph', 'combat:pistol:throw_grenade', 'combat:melee:gh:fire_1'),
               (r'objects\characters\jackal\jackal.model_animation_graph', 'combat:pistol:shakefist', 'combat:melee:gh:fire_1')]


def _names(path):
    import re
    import h2_tagfield as tf
    x = tf.export(path)
    pool = x[x.find('<block name="animations"'):x.find('<block name="modes">')]
    return re.findall(r'<element index="\d+">\s*<field name="name" type="string id">([^<]*)<', pool)


def add_effect_reference(d, path):
    """`d` with `path` appended to the effect references block; its index."""
    import struct
    p = path.encode('latin-1')
    at = None
    k = d.find(SIG, 0x40)
    while k >= 0 and at is None:
        v, n, sz = struct.unpack_from('<III', d, k + 4)
        if sz == 20 and d[k + 16:k + 20] == b'effe'[::-1]:
            at = (k, n)
        k = d.find(SIG, k + 4)
    if at is None:
        raise ValueError('no effect references block')
    k, n = at
    q = k + 16 + n * 20
    paths = []
    for e in range(n):
        ln = struct.unpack_from('<I', d, k + 16 + e * 20 + 8)[0]
        paths.append(bytes(d[q:q + ln]))
        q += ln + 1
    if p in paths:
        return d, paths.index(p)
    elem = bytearray(d[k + 16 + (n - 1) * 20:k + 16 + n * 20])
    struct.pack_into('<I', elem, 8, len(p))
    d[q:q] = p + b'\0'
    d[k + 16 + n * 20:k + 16 + n * 20] = elem
    struct.pack_into('<I', d, k + 8, n + 1)
    if struct.unpack_from('<I', d, 0x7C)[0] != n:
        raise ValueError('the root effect count is not at 0x7C')
    struct.pack_into('<I', d, 0x7C, n + 1)
    return d, n


def clone_event_animation(d, src, new, names, effect=None, replacement=False):
    """Duplicate `src` as `new`. effect: its one effect event = that reference, at the hit frame
    (the frame event's), frame + sound events kept; else no events, `replacement` = overlay type."""
    import struct
    if new in names:
        return d, names.index(new)
    at, n, rows = _anim_block(bytes(d), names)
    name, e, start, end, first = rows[names.index(src)]
    elem = bytearray(d[e:e + ANIM_ES])
    struct.pack_into('<I', elem, 0, len(new) << 24)
    blob_end = start + len(name) + struct.unpack_from('<I', d, e + 0x34)[0]
    spans = _chunks(d, e, first, blob_end)
    def part(off):
        return bytes(d[spans[off][0]:spans[off][1]]) if off in spans else b''
    if effect is None:
        for off in ANIM_BLOCKS[:3]:
            struct.pack_into('<II', elem, off, 0, 0)
        tail = part(0x7C)
        if replacement:
            elem[0x10] = 2
    else:
        frames = part(0x58)
        hit = struct.unpack_from('<h', frames, 18)[0]      # the first frame event's frame
        event = SIG + struct.pack('<III', 1, 1, 4) + struct.pack('<hh', effect, hit)
        struct.pack_into('<I', elem, 0x70, 1)
        tail = frames + part(0x64) + event + part(0x7C)
    data = new.encode('latin-1') + bytes(d[start + len(name):first if first is not None else end]) + tail
    last = rows[-1][3]
    d[last:last] = data
    d[at + 16 + n * ANIM_ES:at + 16 + n * ANIM_ES] = elem
    struct.pack_into('<I', d, at + 8, n + 1)
    if struct.unpack_from('<I', d, 0x94)[0] != n:
        raise ValueError('the root animation count is not at 0x94')
    struct.pack_into('<I', d, 0x94, n + 1)
    return d, n


def _row(d, mode, cls, typ):
    import h2_graph_teach as G
    at, end, elems, chunks = G.modes_chunk(bytes(d))
    m = next(e for e in elems if e[0] == 'mode' and e[1] == at and G.label(d, e) == mode)
    c = next(e for e in elems if e[0] == 'class' and m[4] <= e[3] < m[5] and G.label(d, e) == cls)
    t = next(e for e in elems if e[0] == 'type' and c[4] <= e[3] < c[5] and G.label(d, e) == typ)
    return t, elems


def add_action(d, mode, cls, label, index):
    """The `gh` row (actions empty, one overlay) gets action `label` -> animation `index`: an
    actions chunk built from its overlay chunk."""
    import struct
    t, _e = _row(d, mode, cls, 'gh')
    if struct.unpack_from('<I', d, t[3] + 4)[0]:
        return d
    o = t[4] + 2                                  # after the label 'gh': the overlays chunk
    head = bytes(d[o:o + 16])
    st = bytearray(d[o + 16:o + 24])
    ln = st[3]
    rest = bytes(d[o + 24 + ln:t[5]])
    pair = bytes(st[4:8])
    new_pair = struct.pack('<hh', -1, index)
    struct.pack_into('<I', st, 0, len(label) << 24)
    st[4:8] = new_pair
    if rest[:4] != b'IINA':
        raise ValueError('no IINA descriptor after the overlay')
    data = head + bytes(st) + label.encode('latin-1') + rest[:16]      # the index lives in the struct
    d[o:o] = data
    struct.pack_into('<I', d, t[3] + 4, 1)
    return d


def set_overlay(d, mode, cls, typ, label, index):
    """Overlay `label` of a row -> animation `index` (the index lives in the overlay's struct)."""
    import struct
    import h2_graph_teach as G
    t, elems = _row(d, mode, cls, typ)
    o = next(e for e in elems if e[0] == 'action' and t[4] <= e[3] < t[5] and G.label(d, e) == label)
    new = struct.pack('<hh', -1, index)
    d[o[3] + 4:o[3] + 8] = new
    return d


def ai_swings():
    import shutil
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_graph_teach as G
    import h2_stringid
    TAGS = _os.path.join(H2EK, 'tags')
    dry = '--dry' in sys.argv
    plain = _os.path.join(TAGS, FX + r'\gravity_hammer_port_impact.effect')
    for marker in sorted({r[4] for r in AI_SWINGS}):
        dest = _os.path.join(TAGS, AI_IMPACT + ('' if marker == 'melee_effect' else '_' + marker) + '.effect')
        if not dry and not _os.path.exists(dest):
            shutil.copy(plain, dest)
            print('   ' + h2_stringid.rename(dest, {'up': marker}, write=True))
    jobs = [(rel, None, src, new, _m) for rel, _c, src, new, _m in AI_SWINGS] + [(rel, 'o', src, new, None) for rel, src, new in AI_OVERLAYS]
    for rel, kind, src, new, marker in jobs:
        path = _os.path.join(TAGS, rel)
        original = open(path, 'rb').read()
        names = _names(path)
        d = bytearray(original)
        if kind is None:
            ref = AI_IMPACT + ('' if marker == 'melee_effect' else '_' + marker)
            d, eff = add_effect_reference(d, ref)
            d, index = clone_event_animation(d, src, new, names, effect=eff)
            d = add_action(d, 'combat', 'melee', 'melee', index)
        else:
            d, index = clone_event_animation(d, src, new, names, replacement=True)
            d = set_overlay(d, 'combat', 'melee', 'gh', 'fire_1', index)
        G.modes_chunk(bytes(d))
        if dry:
            print('%s: dry, +%d bytes, %s = animation %d' % (_os.path.basename(path), len(d) - len(original), new, index))
            continue
        if bytes(d) == original:
            print('%s: already' % _os.path.basename(path))
            continue
        before = h2_stringid.export(path)
        open(path, 'wb').write(bytes(d))
        after = h2_stringid.export(path)
        lost = [r for r in before if r not in after]
        # the row's own overlay index moves in set_overlay: that one row may change
        if len(lost) > (0 if kind is None else 1) or not any(r[2] == new for r in after):
            open(path, 'wb').write(original)
            raise SystemExit('%s refused, restored: %d rows lost %s' % (path, len(lost), lost[:3]))
        print('%s: %s = animation %d, +%d bytes, %d more rows, %d original rows changed'
              % (_os.path.basename(path), new, index, len(d) - len(original), len(after) - len(before), len(lost)))


# Armed test 4 (user: 'Elites hit themselves with the blast'): an animation event's effect has no
# damage owner, so 'Does Not Hurt Owner' is no help, and the Elite's `melee` marker is on its chest
# (Tartarus's own blast reaches 0.8 wu from the hammer's head). The AI's blast = its own clone of the
# explosion, flags 'Does Not Hurt Owner' + 'Does Not Hurt Friends' (9). The enhancer's Hammer cards
# must reach it too (catalog: explosion_ai).
#     python ports_h2\gravity_hammer.py --ai-blast       (--ai-swings first)
AI_BLAST = GH + r'\damage_effects\gravity_hammer_port_explosion_ai'


def ai_blast():
    import shutil
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_tagfield as tf
    import h2_tagref as R
    TAGS = _os.path.join(H2EK, 'tags')
    plain = GH + r'\damage_effects\gravity_hammer_port_explosion'
    dest = _os.path.join(TAGS, AI_BLAST + '.damage_effect')
    if not _os.path.exists(dest):
        shutil.copy(_os.path.join(TAGS, plain + '.damage_effect'), dest)
    tf.set_field(dest, 'flags', 9, '', 0, 1)
    for tail in ('', '_melee'):
        fx = _os.path.join(TAGS, AI_IMPACT + tail + '.effect')
        if ('jpt!', AI_BLAST) not in R.references(fx):
            R.set_reference(fx, 'jpt!', plain, AI_BLAST)


if __name__ == '__main__':
    import sys as _sys
    if '--ai-blast' in _sys.argv:
        ai_blast()
    elif '--ai-swings' in _sys.argv:
        ai_swings()
    elif '--brute-grip' in _sys.argv:
        brute_grip()
    elif '--blast-shove' in _sys.argv:
        blast_shove()
    elif '--blank' in _sys.argv:
        for _row in BLANKS:
            blank(*_row)
    elif '--fire-rows' in _sys.argv:
        fire_rows()
    else:
        write_side_jms()

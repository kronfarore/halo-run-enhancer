r"""The Elites' Energy Sword made pickable (RESTORED, 2026-10-05/06): Halo 1's own sword,
Halo 3's first-person animations and sounds. PORTING.md "Halo 1: enemy-only weapons made
pickable"; memory h1-pickable-sword-fuelrod."""
from ._common import B, H3_FP_GRAPHS, ANIMS, IMPACTS, row

NAME = 'Energy Blade'          # halo.json's H2-H4 sword (user, 2026-10-06)
SWORD = B.join(['weapons', 'energy sword', 'energy sword'])
STRIKE = B.join(['weapons', 'energy sword', 'lunge strike'])
SWORD_SWING = r'sound\sfx\impulse\animations\elite\stand_sword_melee.mov'
SWORD_SOUNDS = 'sound\\weapons\\energy_sword_port\\'

PORT = {
    'order': 1,
    'wave': 'restored',
    'name': NAME,
    'source': 'Halo 1',
    'status': 'done',
    'reservations': {'messages': (49, 50), 'icon': 27, 'reticle': 17, 'label': 'fb',
                     'teach_from': 'b', 'sound_dir': r'sound\weapons\energy_sword_port',
                     'weapon_dir': r'weapons\energy sword'},
    # BORROWED sound kept ON PURPOSE (user, 2026-10-08 sound close-out): a RESTORED weapon
    # keeps Halo 1's own dispersal boom. port_sound_refs.py prints it as KEEP
    'sound_keeps': {r'sound\sfx\impulse\impacts\elite_sword_boom': "the original sword's own dispersal"},
    'yardstick': {'pick': None,
                  'reason': 'restored weapon: Halo 1\'s own numbers; balanced rows by step 5b '
                            '(h1_role_compare.py energy_blade, user-approved 2026-10-06)',
                  'candidates': {}},

    'retarget': {
        'graph': H3_FP_GRAPHS + r'\melee\fp_energy_blade\fp_energy_blade.model_animation_graph',
        'render_model': r'objects\weapons\melee\energy_blade\fp_energy_blade'
                        r'\fp_energy_blade.render_model',
        'nodes': {'handle': 'frame handle', 'blades': 'frame blades'},
        'h1_dir': r'weapons\energy sword\fp',
        # first person shows Halo 1's own sword: its world model, posed by H3's motion
        'h1_model': r'weapons\energy sword\energy sword',
        'align': 'same_space',
        # user (2026-10-10, during the DMR pilot): 'the FP was not correct' -> 1 unit (0.01 wu)
        # DOWN, the whole rig in view space (h1_fp_retarget view_offset); test 2: 'up 0.5 u and
        # towards the player 0.5 u' (x back, z up) -> (-0.005, 0, -0.005); test 3: 'back down
        # 0.5 u' -> (-0.005, 0, -0.01)
        'view_offset': (-0.005, 0.0, -0.01),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:melee_strike_1': 'first-person melee',
            # the fire button's lunge (h1_pickable_weapons.py gives the sword a trigger)
            'first_person:melee_lunge': 'first-person fire-1',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:posing:var1': 'first-person posing',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    'pickable': {
        'weapon': r'weapons\energy sword\energy sword',
        'fp_model': r'weapons\energy sword\energy sword',
        'fp_anims': r'weapons\energy sword\fp\fp',
        'teach': ('fb', 'b'),
        # no FIRE (lunge) while the slash plays: weapon flags bit 31 for the halo1.dll patch
        # h1_melee_blocks_fire.py (Halo 1 blocks only 3/4 of a melee); the ball's 3P melee
        # (28 fr) already outlasts the slash (24). CONFIRMED in game 2026-10-10
        'melee_blocks_fire': True,
        'keys': {'first-person melee': 5},
        # Halo 3's own sword sounds (h1_port_sounds.py energy_sword): the Elite's swing
        # (SWORD_SWING) is silent for 0.45 s and was heard 0.3 s late (user, 2026-10-06)
        'sounds': {'first-person melee': SWORD_SOUNDS + 'sword_melee',
                   'first-person fire-1': SWORD_SOUNDS + 'sword_lunge',
                   'first-person ready': SWORD_SOUNDS + 'sword_ready',
                   'first-person posing': SWORD_SOUNDS + 'sword_pose'},
        # Halo 3 plays the ignition from its blade_activate effect, 0.6 s after the sword
        # turns on (that event's delay) -- 18 frames into the ready (user: 'too early' at 0)
        'sound_frames': {'first-person ready': 18},
        # the hit: the melee damage effect's own sound (slash AND lunge strike use it)
        'hit_sound': SWORD_SOUNDS + 'sword_hit',
        # the hum: a sound_looping (the plasma rifle charge loop's shape) on the blade
        'hum': {'loop': SWORD_SOUNDS + 'sword_hum', 'tag': SWORD_SOUNDS + 'sword_hum',
                'like': r'sound\sfx\weapons\plasma rifle\charging', 'marker': 'flare'},
        # MCC's Halo 1 localization has no line for message 8 ("need string insert here"
        # in game, 2026-10-05): the sword gets its own appended pair, like the SAW's 47/48
        'messages': ('Picked up an energy sword', 'Picked up %d rounds for energy sword'),
        'icon': 'energy sword',                  # hud_msg_icons sequence (add_msg_icon.py)
        # the plasma pistol's HUD, whose BATTERY bar (age) is the sword's energy (the heat
        # half of `master plasma` stays empty: the sword makes no heat), with HALO 3's sword
        # reticle (hud_reticles #13) brought in by h1_add_reticle.py
        'hud': {'donor': r'weapons\plasma pistol\plasma pistol',
                'out': r'weapons\energy sword\energy sword',
                'reticle': ('hud_reticles', 13, 'energy sword')},
        # aim assist: Halo 3's sword (degrees, wu) -- the AI-only tag had none
        'aiming': {'autoaim_angle': 10.0, 'autoaim_range': 2.5,
                   'magnetism_angle': 10.0, 'magnetism_range': 6.0},
        # THE LUNGE (fire button), experimental: Halo 1 has no player lunge. A trigger
        # fires an invisible strike that dies after LUNGE_RANGE and does the sword's own
        # melee damage, and its firing damage on the wielder carries an instantaneous
        # acceleration -- the shove. Each lunge costs LUNGE_ENERGY of the battery (Halo 3
        # costs 0.1 per KILL, which Halo 1 cannot count); at full age it cannot fire.
        # Sword Elites keep their melee: their actor variants fire at rate 0.
        'lunge': {'template': r'weapons\plasma pistol\plasma pistol',
                  'strike': r'weapons\energy sword\lunge',          # projectile
                  'strike_from': r'weapons\assault rifle\bullet',
                  # the strike's OWN damage (step 3): a copy of the sword's melee damage, so a
                  # balance row (e.g. the balanced build's damage RADIUS) moves only the lunge,
                  # not the regular melee and not the Elites' sword
                  'strike_damage': r'weapons\energy sword\lunge strike',
                  'push': r'weapons\energy sword\lunge push',       # firing damage
                  'push_from': r'weapons\plasma pistol\trigger',
                  # first boot (2026-10-06): strike hit, shove did nothing with 0 damage
                  # and every material modifier 0 -- now a token 0.01 damage, modifiers 1.
                  # Second boot: +3 pushed the player BACK, a negative value forward; too
                  # much acceleration hurts the player (user tuned it live). Halo 3's
                  # aim assist stays the original; stronger lunge assist = balanced build.
                  # third boot: the user settled on -10 live
                  'range': 1.5, 'velocity': 60.0, 'acceleration': -10.0, 'push_damage': 0.01,
                  'energy': 0.1, 'rate': 1.0,
                  # the strike's HIT sound (user, 2026-10-06: the lunge hit silently -- a
                  # damage effect's sound plays for melee, not for a projectile's impact):
                  # a one-part impact effect, the AR's `impact dirt` without its decal,
                  # on every material response
                  'hit_effect': (r'weapons\assault rifle\effects\impact dirt',
                                 r'weapons\energy sword\effects\lunge hit')},
    },

    # weapon -> its weapon_ports_catalog.json name (`catalog`: the manifest's 'weapon', which
    # the enhancer keys its volume knobs by), tag folder (never under sound\sfx), sounds:
    #   name -> (Halo 3 sound folders mixed together, stock H1 sound to copy playback from,
    #            active-RMS target dBFS[, sound class override])
    'sounds': {
        'catalog': NAME,
        'dir': B.join(['sound', 'weapons', 'energy_sword_port']),
        'h3_dir': 'data\\sound\\weapons\\energy_sword\\',
        'sounds': {
            'sword_melee': (['energy_melee_1'], ANIMS + B + 'ball_melee', -16.2),
            'sword_lunge': (['energy_sword_lunge_hum', 'energy_sword_lunge_cloth'],
                            ANIMS + B + 'ball_melee', -16.2),
            'sword_ready': (['sword_ready'], ANIMS + B + 'ball_ready', -13.1),
            'sword_pose': (['energy_sword_pose'], ANIMS + B + 'ball_posing', -20.0),
            # the melee damage effect's sound, so a slash or lunge that HITS sounds like one
            'sword_hit': (['sword_impact_character'], IMPACTS + B + 'melee_impact_fleshy',
                          -14.0),
            # Halo 3's idle hum: the LOOP of a sound_looping the weapon carries always
            'sword_hum': (['sword_loop\\sword_loop\\loop'],
                          B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charge']), -27.0,
                          'weapon_idle'),
        },
    },

    # 'Energy Blade', not 'Energy Sword' (user, 2026-10-06): halo.json's H2-H4 sword entry,
    # so a run carries ONE sword across games
    'catalog': {
        'renamed_from': ('Energy Sword',),
        'entry': {
            'weapon': NAME, 'source': 'Halo 1', 'donor': None, 'default_on': False,
            'desc': "The Elites' energy sword, made pickable: Halo 3's first-person animations "
                    "and sounds, Halo 1's own sword. Fire lunges (costs energy), melee slashes.",
            'balance_desc': 'One lunge kills an Elite (420 damage), 20 lunges per charge, '
                            'stronger lunge aim assist (15 deg / 3.5 wu, 15 deg / 8 wu) and a '
                            'wider lunge hit.',
            'fp_animations': B.join(['weapons', 'energy sword', 'fp', 'fp']),
            # the lunge strike exists only in the player build
            'requires': ['proj ' + B.join(['weapons', 'energy sword', 'lunge'])],
            'anims': {},
            'balance': [
                row('weap', SWORD, 'Autoaim Angle', 15.0, 10.0, 'Lunge aim assist'),
                row('weap', SWORD, 'Autoaim Range', 3.5, 2.5, 'Lunge aim assist'),
                row('weap', SWORD, 'Magnetism Angle', 15.0, 10.0, 'Lunge aim assist'),
                row('weap', SWORD, 'Magnetism Range', 8.0, 6.0, 'Lunge aim assist'),
                row('jpt!', STRIKE, 'Radius', 1.0, 0.5, 'Lunge damage radius'),
                row('jpt!', STRIKE, 'Radius Max', 1.0, 0.5, 'Lunge damage radius'),
                # step 5b (h1_role_compare.py energy_blade, user-approved 2026-10-06): the lunge
                # kills like Halo 3's -- 420 is one lunge through an Elite commander on
                # legendary (280 shield + 140 body; every material x1); the slash stays 151
                row('jpt!', STRIKE, 'Damage Lower Bound', 420.0, 151.0, 'Lunge damage'),
                row('jpt!', STRIKE, 'Damage Upper Bound', 420.0, 151.0, 'Lunge damage'),
                row('jpt!', STRIKE, 'Damage Upper Bound Max', 420.0, 151.0, 'Lunge damage'),
                # Halo 1 charges energy per swing where Halo 3 charges per kill: 20 lunges
                row('weap', SWORD, 'Age Generated Per Round', 0.05, 0.1, 'Energy per lunge',
                    block='Triggers'),
            ]},
    },

    # step 11: carried in game (Elite commander / stealth Elite major) -- best_donor finds
    # the carriers; nothing to write
    'firing_profile': {'mode': 'carried'},
}

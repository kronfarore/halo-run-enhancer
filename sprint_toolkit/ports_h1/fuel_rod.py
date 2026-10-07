r"""The Grunts' Fuel Rod made pickable (RESTORED, 2026-10-05/06): the original gun, Halo 3's
flak_cannon first-person animations and sounds. Catalogued as 'Flak Cannon' (halo.json's
H2-H4 fuel rod). PORTING.md "Halo 1: enemy-only weapons made pickable"."""
from ._common import B, H3_FP_GRAPHS, ANIMS, row

NAME = 'Flak Cannon'
ROD = B.join(['weapons', 'fuel rod gun', 'fuel rod'])
ROD_BLAST = B.join(['weapons', 'fuel rod gun', 'grunt explosion'])
GRUNT_ROD = B.join(['characters', 'grunt', 'grunt specops fuel rod'])
ROD_SOUNDS = 'sound\\weapons\\fuel_rod_port\\'

PORT = {
    'order': 2,
    'wave': 'restored',
    'name': NAME,
    'source': 'Halo 1',
    'status': 'done',
    # the stock pickup line (46, 'Picked up a fuel rod gun') -- no pair of its own
    'reservations': {'messages': None, 'icon': 28, 'reticle': None, 'label': 'fr',
                     'teach_from': 'pc', 'sound_dir': r'sound\weapons\fuel_rod_port',
                     'weapon_dir': r'weapons\fuel rod gun'},
    'yardstick': {'pick': None,
                  'reason': 'restored weapon: Halo 1\'s own numbers; balanced rows by step 5b '
                            '(h1_role_compare.py flak_cannon, user-approved 2026-10-06)',
                  'candidates': {}},

    # Halo 3's fuel rod is the flak_cannon. Its FP graph drives the ORIGINAL Halo 1 fuel
    # rod (the Grunts' weapons\fuel rod gun\fuel rod gun model, one node `frame gun`).
    # H3's reload parts (ammo, barrel, cowling) have no counterpart there: dropped.
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\support_high\fp_flak_cannon\fp_flak_cannon.model_animation_graph',
        'render_model': r'objects\weapons\support_high\flak_cannon\fp_flak_cannon'
                        r'\fp_flak_cannon.render_model',
        'nodes': {'gun': 'frame gun'},
        'drop_nodes': ('ammo_bottom', 'barrel', 'ammo_top', 'cowling'),
        'h1_dir': r'weapons\fuel rod gun\fp',
        # the original's own mesh at Spartan size: h1_scaled_model.py, x0.75 (0.57 -> 0.43
        # long, = H3's FP fuel rod; Halo 1's own Chief-held PC fuel rod is 0.41)
        'h1_model': r'weapons\fuel rod gun\fp\fp',
        'h1_model_from': (r'weapons\fuel rod gun\fuel rod gun', 0.75),
        # the two models are NOT in one space; both put their `gun` node at the right-hand
        # grip, so the grips are matched. Measured at idle: H3's left hand sits 13 cm ahead
        # of the grip, the scaled H1 model's own `cyborg left hand` marker 20 cm.
        'align': 'node',
        # in game (a50, 2026-10-05) the left hand clipped into the H1 model: move the wrist
        # toward the player's right (-y in the gun's space), JMS units / 100. Full strength
        # within 6 units of its idle grip, none beyond 14 (the reloads leave the gun).
        'grip_node': 'gun',
        'left_hand_offset': ((0.04, -0.02, 0.0), 0.06, 0.14),
        # and during the reloads, where the hand leaves the grip (user, 2026-10-06): one
        # unit forward and one to the right, for the whole animation
        'left_hand_offset_anims': {'first_person:reload_empty': (0.01, -0.02, 0.0),
                                   'first_person:reload_full': (0.01, -0.02, 0.0)},
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:posing:var1': 'first-person posing',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    'pickable': {
        'weapon': r'weapons\fuel rod gun\fuel rod',
        # a10 has no Grunt fuel rod (its palette carries only the Hunters'): palette entry
        # + resident-only placement there too, so the enhancer can offer it (user,
        # 2026-10-06); the other nine levels carry it already
        'palette_levels': ['a10'],
        'fp_model': r'weapons\fuel rod gun\fp\fp',
        'fp_anims': r'weapons\fuel rod gun\fp\fp',
        'teach': ('fr', 'pc'),
        'keys': {'first-person melee': 5},
        # Halo 3's own fuel rod sounds (h1_port_sounds.py fuel_rod), all cued at frame 0
        # as Halo 3 does; the original fuel rod never had first-person sounds
        'sounds': {'first-person melee': ROD_SOUNDS + 'rod_melee',
                   'first-person ready': ROD_SOUNDS + 'rod_ready',
                   'first-person reload-empty': ROD_SOUNDS + 'rod_reload',
                   'first-person reload-full': ROD_SOUNDS + 'rod_reload',
                   'first-person posing': ROD_SOUNDS + 'rod_pose',
                   'first-person fire-1': ROD_SOUNDS + 'rod_fire'},
        # Halo 1 rule (PORTING.md step 3): a weapon owns its melee damage tag. The PC fuel
        # rod's is the Chief-held fuel rod's melee; the response stays shared (feedback).
        'melee': (r'weapons\plasma_cannon\effects\plasma_cannon_melee',
                  r'weapons\fuel rod gun\melee'),
        'melee_response': r'weapons\plasma_cannon\effects\plasma_cannon_melee_response',
        # HUD (user, 2026-10-06): the PC fuel rod's own -- its crosshair is the right one --
        # on `master rounds`, with the RL's loaded-ammo elements drawing HALO 3's fuel rod
        # meter, four of its rods (h1_rocket_meter.py h3_rods)
        'hud': {'donor': r'weapons\plasma_cannon\plasma_cannon',
                'readout': r'weapons\rocket launcher\rocket_launcher',
                'out': r'weapons\fuel rod gun\fuel rod',
                'meter': r'weapons\fuel rod gun\bitmaps\fuel_rod_rods', 'art': 'h3_rods_row'},
        # the charge (vanilla: hold 1.25 s, it fires when full): the plasma pistol's own
        # charging loop, as the pistol plays it -- an attachment on `primary trigger`
        # scaled by an object function fed by the weapon's primary_charged (input B).
        # Halo 1 has no FP animation slot that plays DURING a charge (`overcharged` plays
        # once full, and the fuel rod fires at that instant).
        'charge_loop': {'sound': r'sound\sfx\weapons\plasma rifle\charging',
                        'marker': 'primary trigger', 'input': 'B_in',
                        # and a GLOW while charging (user, 2026-10-06: only the model's own
                        # self-illumination showed): the fuel rod folder's own light volume
                        # (the Hunter's arm glow) and light, which nothing attached
                        'glow': [r'weapons\fuel rod gun\hunter fuel rod',
                                 r'weapons\fuel rod gun\illumination']},
        # STEP 3 (PORTING.md): its OWN projectile and damage. The Grunts' fuel rod fired
        # `weapons\fuel rod gun\fuel rod`, the HUNTERS' projectile -- so the enhancer's
        # Hunter cards (Fuel Rod Range / Velocity / Gravity on the projectile, Hunter Fuel
        # Rod Damage on `explosion` through the detonation effect) moved the Grunts' and now
        # the player's fuel rod too. Same values, own tags; the Hunters keep the originals.
        'own_projectile': {
            'projectile': (r'weapons\fuel rod gun\fuel rod', r'weapons\fuel rod gun\grunt fuel rod'),
            'effect': (r'weapons\fuel rod gun\effects\explosion',
                       r'weapons\fuel rod gun\effects\grunt explosion'),
            'damage': (r'weapons\fuel rod gun\explosion', r'weapons\fuel rod gun\grunt explosion')},
        # the AI-only tag fired with rounds_per_shot 0 (never spent a round, never reloaded)
        # and had no aim assist; Halo 3's fuel rod values (degrees, wu)
        'rounds_per_shot': 1,
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 25.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 25.0},
        'icon': 'fuel rod',
        # the fuel rod Grunts dropped it EMPTY (actv drop_weapon_loaded 0..0, ammo 0..0 --
        # it detonated anyway); a plasma pistol Grunt drops 70-90%
        'drops': {r'characters\grunt\grunt specops fuel rod': ((0.5, 1.0), (2, 6)),
                  r'characters\grunt\grunt specops fuel rod airdef': ((0.5, 1.0), (2, 6))},
    },

    # Halo 3's fuel rod is the flak_cannon; every sound it cues sits on frame 0
    'sounds': {
        'catalog': NAME,
        'dir': B.join(['sound', 'weapons', 'fuel_rod_port']),
        'h3_dir': 'data\\sound\\weapons\\flak_cannon\\',
        'sounds': {
            'rod_ready': (['flak_cannon_ready'], ANIMS + B + 'plasrifle_ready', -13.1),
            'rod_reload': (['flak_cannon_reload'], ANIMS + B + 'rocket_reload_e', -20.9),
            'rod_pose': (['flak_cannon_posing_var1'], ANIMS + B + 'rocket_posing', -20.0),
            'rod_melee': (['flak_cannon_melee'], ANIMS + B + 'fuelrod_melee', -16.2),
            'rod_fire': (['flak_cannon_fire_animation'], ANIMS + B + 'rocket_fire', -18.0),
        },
    },

    # NOT emitted, on purpose: keys the enhancer session owns survive the merge -- the
    # 'tag_map'; its 'skip_cards' was removed (user: the Zoom card GIVES the fuel rod a
    # zoom), so do not add it back.
    'catalog': {
        'entry': {
            'weapon': NAME, 'source': 'Halo 1', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "The Grunts' fuel rod, made pickable: Halo 3's first-person animations and "
                    "sounds on the original gun. Hold fire to charge; it fires when full.",
            'balance_desc': 'Instant fire at 2.5 rods/s and it hurts Hunters (the Grunts\' fuel '
                            'rods too; they fire two rods per burst instead of one).',
            'fp_animations': B.join(['weapons', 'fuel rod gun', 'fp', 'fp']),
            # its own projectile (step 3) exists only in the player build
            'requires': ['proj ' + B.join(['weapons', 'fuel rod gun', 'grunt fuel rod'])],
            'anims': {},
            'balance': [
                row('weap', ROD, 'Charging Time', 0.0, 1.25, 'Charging Time', block='Triggers'),
                # step 5b (h1_role_compare.py flak_cannon, user-approved 2026-10-06): charge 0
                # alone leaves the AI tag's 10 rounds/s -- as fast as one can click; Halo 3's
                # fuel rod fires at most every 0.4 s
                row('weap', ROD, 'Rounds Per Second', 2.5, 10.0, 'Rate of Fire', block='Triggers'),
                row('weap', ROD, 'Rounds Per Second Max', 2.5, 10.0, 'Rate of Fire',
                    block='Triggers'),
                # the explosion does x0 to Hunters (Bungie's guard against Grunts hurting
                # them); the rocket launcher does x1. Grunts' fuel rods can then hurt Hunters.
                row('jpt!', ROD_BLAST, 'Hunter Armor', 1.0, 0.0, 'Hunter damage'),
                row('jpt!', ROD_BLAST, 'Hunter Skin', 1.0, 0.0, 'Hunter damage'),
                # THE GRUNTS (a50 test 2026-10-06, user: "without the charge time they get to
                # spam"): their actor variants hold the trigger (Rate Of Fire 0) through 2.2 s
                # bursts every ~5 s. Vanilla, the 1.25 s charge allowed ONE rod per burst
                # (~12/min); balanced, the weapon's 2.5/s allows six (~46-69/min). 0.75
                # pulls/s = TWO rods per burst (~23/min, twice vanilla) -- AI only, the
                # player's fuel rod keeps 2.5/s.
                row('actv', GRUNT_ROD, 'Rate Of Fire', 0.75, 0.0, 'Grunt fuel rod rate'),
                row('actv', GRUNT_ROD + ' airdef', 'Rate Of Fire', 0.75, 0.0,
                    'Grunt fuel rod rate'),
            ]},
    },

    # step 11: carried in game (spec-ops Grunts) -- nothing to write
    'firing_profile': {'mode': 'carried'},
}

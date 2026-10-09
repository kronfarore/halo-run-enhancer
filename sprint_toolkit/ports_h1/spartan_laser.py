r"""Spartan Laser (Halo 3 -> Halo 1, wave A8) on a copy of the Halo 1 PLASMA PISTOL (heat + battery
+ a CHARGED trigger pair: its trigger 0 charges, a full charge fires trigger 1 -- the role table's
template), with the ROCKET LAUNCHER as the yardstick (step 4a, user 2026-10-09). beam_rifle.py is
the shape it copies (a heat / battery port on a template that is not its yardstick); what is new
here: a CHARGE-UP shot that fires by itself when charged (Halo 3's spew-charge), a damage that is
a direct-hit bump over a small splash, and a red BEAM visual."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\support_high\spartan_laser'
SL = 'weapons\\spartan laser\\'
SND = 'sound\\weapons\\spartan_laser_port\\'
PP = 'weapons\\plasma pistol\\'
RL = 'weapons\\rocket launcher\\'
SR = 'weapons\\sniper rifle\\'
BASE = H3 + r'\bitmaps\spartan_laser.bitmap'
# Halo 3's luminous shader: self_illum_map = a 1x1 white bitmap (the whole material lit),
# self_illum_color a two-colour gradient in its function data (BGRA ca 8f 71 -> RGB 113 / 143 /
# 202, a pale blue; 7d ff 7d -> 125 / 255 / 125, a green), intensity 6 -> 2
LUMINOUS = (113 / 255.0, 143 / 255.0, 202 / 255.0)
# ... at intensity 2..6 (Halo 3 blooms it): saturated for an additive glow
LUMINOUS_HOT = (0.5, 0.65, 1.0)
# the beam: Halo 3's is a red laser (its beam_system colours sit in function data: a start,
# judged in game)
RED = (1.0, 0.15, 0.1)
# STEP 4b (port_field_audit.py --port spartan_laser, BEFORE boot 1), the damage effect's list 2
# (ratio H3 laser / H3 rocket onto the H1 rocket's explosion), on BOTH of the laser's damage
# tags (both copies of that explosion): aoe core 0.6 x 0.15/0.5, camo damage 1 x 0.3/0.9,
# acceleration 6 x 0.2/3, shake 0.0349 x 0.04/0.075, breaking effect 80 x 30/35, 1 x 2/0.5,
# 2 x 0/0.5, 16 x 15/6. List 3: category = Halo 3's 'plasma' (Halo 1 has it); screen flash
# priority one step above the rocket (Halo 3 high vs medium; Halo 1's rocket low -> medium);
# the rocket's flash lasts 0 s -- Halo 3's shielded response (lighten 1 s, 0.5) as the Brute
# Shot's test 6, tinted RED like the beam (Halo 3's own is blue: the Brute Shot's user rule
# 'blue reads as plasma'); camera impulse 0 (the H1 rocket's: the ratio is 0)
DAMAGE_4B = {'damage.aoe_core_radius': 0.18,
             'damage.active_camouflage_damage': 1 / 3.0,
             'damage.instantaneous_acceleration': 0.4,
             'damage.category': 'plasma',
             'camera_shaking.random_translation': 0.0349066 * 0.04 / 0.075,
             'breaking_effect.forward_velocity': 80 * 30 / 35.0,
             'breaking_effect.forward_radius': 4.0,
             'breaking_effect.forward_exponent': 0.0,
             'breaking_effect.outward_velocity': 40.0,
             'screen_flash.priority': 'medium',
             'screen_flash.duration': 1.0,
             'screen_flash.maximum_intensity': 0.5,
             'screen_flash.tint_lower_bound': (1.0, 1.0, 0.3, 0.2)}
# trigger first-person offset: the FP muzzle (fp_render: the FP model's `primary trigger` in
# the idle pose, camera space forward / left / up wu; the same reading gives the Beam Rifle's
# 0.5802 / -0.0668 / -0.0449)
FP_MUZZLE = (0.215, -0.053, -0.007)        # test 6: the current view offset's (marker_dir.py)

PORT = reserved(
    order=17, wave='A8', name='Spartan Laser', source='Halo 3',
    messages=(67, 68), icon=37, reticle=26, label='sl', teach_from='rl',
    sound_dir='sound\\weapons\\spartan_laser_port', weapon_dir='weapons\\spartan laser',
    yardstick={
        # step 4a (user, 2026-10-09): h3_weapon_values.py (spartan_laser / sniper_rifle /
        # rocket_launcher / sentinel_gun, FP graphs) + the trigger, barrels, projectiles and
        # damage effect (tool export-tag-to-xml) + h1_role_compare.py spartan_laser
        # (out/sl_4a_role.txt). What h3_weapon_values does not print:
        #   CHARGE  trigger 'spew-charge', charging time 2.5 s, overcharged action discharge:
        #           while charging, barrel 0 fires the NO-DAMAGE tracer at 20/s (the aiming
        #           line); charged, barrel 1 (secondary) fires 5 beam rounds at 30/s with one
        #           firing effect a burst ('use 1 firing effect per burst')
        #   DAMAGE  a beam round = the projectile's DETONATION damage spartan_laser_beam: 20
        #           (radius 0..0.6, AOE core 0.15) + the AOE SPIKE BUMP 94 inside 0.15 = 114 on
        #           a direct hit -> 570 a shot (5 rounds). The bump is what one-shots a Halo 3
        #           Spartan (hard_metal_thin body + energy_shield_thin, both x0.5 to 'laser':
        #           100 could not). Damage group 'laser' = explosion_large (the rocket's) but
        #           hard_metal_solid (Hunter armour) x0.5 vs x1
        #   BATTERY age 0.04 a round (campaign = MP) x 5 = 0.2 a shot = 5 shots
        #   HEAT    1 a round: every shot overheats; vent (1 - 0.1) / 0.4 = 2.25 s
        # cycle 2.5 + 0.13 + 2.25 = 4.88 s -> 117 dps (Halo 3's sniper 80 / 0.7 s = 114)
        'pick': 'Rocket Launcher',
        'reason': "user, step 4a 2026-10-09: Halo 3's 'laser' damage group IS the rocket's "
                  "explosion_large (shields x0.5, Flood x2, hard metal x0.5; only Hunter armour "
                  "differs, x0.5 vs x1), so Halo 1's rocket material table carries over with "
                  "Hunter armour x0.5, and the rocket is the pose donor (`sl` from `rl`). The "
                  "Sniper ratio keeps the dps but its bullet table leaves Flood near immune "
                  "(4-5 shots); the Sentinel Beam ratio chains derived numbers and leaves 1.25 "
                  "shots a battery. User: A/B the AOE SPIKE BUMP in game (with: 408 a shot, "
                  "without: 131) and decide from that whether the Brute Shot's rocket ratio "
                  "(which used the rocket's 240 without its 200 bump) needs adjusting",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H1 rocket: explosion 315 (300..330, lower 80), radius 0.5 -> 2.0, 2.0 s a shot, 2 (4
        # / 8), reload 4.17 s, range 128, aim 0/35 12/35, melee 55. H3 rocket: 240 + bump 200
        # = 440 direct, radius 0.9 -> 2, 0.8 s, 2 (4 / 8), reload 116 fr, range 175, aim 5/25
        # 10/25, smash_melee 80
        'balanced': {
            # A (with both bumps): 315 x 570/440 = 408 a shot; B (without): 315 x 100/240 = 131
            'damage': {'A': 408.0, 'B': 131.25},
            # the rocket's SUSTAINED rate (2 rockets a 0.8 + 3.87 s in Halo 3, a 2.0 + 4.17 s
            # in Halo 1: x0.75) -> cycle 4.88 / 0.75 = 6.5 s: charge 2.5 x 6.5/4.88 = 3.33 s,
            # vent 2.25 x 6.5/4.88 = 3.0 s (loss 0.9 / 3.0 = 0.3)
            'charge_s': 3.33,
            'heat_loss': 0.3,
            'battery_shots': 5,            # the rocket's 2 / 4 / 8 = Halo 3's: x1
            'radius': (0.0, 0.6),          # 0 x 0.5/0.9, 0.6 x 2/2
            'range': 88.0,                 # 120 x 128/175
            # autoaim 0/5 is degenerate -> the magnetism's ratio 12/10: 1 x 1.2; ranges 35 x
            # 25/25; magnetism 5 x 12/10, 35 x 25/25
            'aim': (1.2, 35.0, 6.0, 35.0),
            'melee': 55.0},                # 55 x smash 80 / smash 80
        # Halo 1 materials: the rocket explosion's table (both versions), Hunter armour x0.5
        # (laser / explosion_large on hard_metal_solid)
        'materials': {'hunter_armor': 0.5},
        'measured': 'h1_role_compare.py spartan_laser',
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Rocket Launcher', 'Sentinel Beam'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon'],
            'why': 'instant beam, one huge shot, battery (age) not magazine',
            'lacks': '2.5 s charge-up (the fuel rod charge is the H1 precedent)'}},
    # step 11: the source game's ai\generic entry (18 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser'},
)

PORT.update({
    'status': 'building',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's materials: spartan_laser (base + bump,
    # chrome reflections), spartan_laser_dull (BR gun detail), spartan_laser_shiny,
    # spartan_laser_luminous (base + a 1x1 WHITE self-illum map: the whole material lit in
    # LUMINOUS), and two DECALS (spartan_laser_decal: warning stickers; decal2: a black
    # lattice -- alpha-blended, `decals`). Template: the rocket launcher's body shader
    'model': {
        'dir': r'weapons\spartan laser',
        'world': H3 + r'\spartan_laser.render_model',
        'fp': H3 + r'\fp_spartan_laser\fp_spartan_laser.render_model',
        'world_name': 'spartan laser',
        # h3_rm_info: the world model's root `gun` rests at 0 deg (not tilted: no world_frame)
        # TEST 1 (user): 'the warning stickers got duplicated; a different kind of mark should
        # be where the bigger sticker is'. Halo 1's `tool model` bound the material
        # `spartan_laser_decal2` to the shader `spartan_laser_decal` (it DROPS A TRAILING DIGIT
        # of a material name -- the Beam Rifle's `beam_rifle2` collapsed the same way, harmless
        # there): the lattice spot drew the sticker sheet. Renamed (h1_h3_weapon_model
        # `material_names`)
        'material_names': {'spartan_laser_decal2': 'spartan_laser_lattice'},
        'shaders': {'spartan_laser': (BASE, None),
                    'spartan_laser_dull': (BASE, None),
                    'spartan_laser_shiny': (BASE, None),
                    'spartan_laser_decal': (H3 + r'\bitmaps\spartan_laser_decal.bitmap', None),
                    'spartan_laser_lattice': (H3 + r'\bitmaps\spartan_laser_decal2.bitmap', None)},
        'decals': ['spartan_laser_decal', 'spartan_laser_lattice'],
        # TEST 1 (user): 'luminous bits are not lit, a usual mistake in these ports'. They are
        # 4 rows of 3 tiny indicator segments (front / rear of each side; Halo 3 blooms them);
        # a self-illuminated shader_model reads as paint in Halo 1. The Beam Rifle's GEM recipe:
        # the material itself an ADDITIVE glow, each UV island a radial white-hot centre in the
        # colour, plus glow cards x1.3 (a halo round each segment)
        # TEST 2 (user): 'in and at the right position, just need a bit more shine' -> gain
        # 1.5 on the segments (a wider white-hot core), 1.6 on the halo cards
        'glow_shaders': {'spartan_laser_luminous': {'rgb': LUMINOUS_HOT, 'additive': True, 'islands': True,
                                                    'gain': 1.5},
                         'sl_lum_card': {'rgb': LUMINOUS_HOT, 'additive': True, 'islands': True,
                                         'islands_of': 'spartan_laser_luminous', 'radius': 1.0,
                                         'falloff': 1.6, 'hot': False, 'gain': 1.6},
                         # TEST 1 (user): 'I need the charging glow'. Halo 3 attaches its
                         # charging glow / ring / flare at primary_trigger; Halo 1 draws weapon
                         # attachments at the hidden third-person gun in first person. A glow
                         # BUILT INTO the model instead: a star of radial cards at the muzzle
                         # whose additive shader FADES with D out = primary charged
                         # (`fade_source`; the plasma pistol shows its own charge in first
                         # person through a meter shader on D out)
                         'sl_charge_glow': {'rgb': RED, 'additive': True, 'radial': True,
                                            'hot': True, 'falloff': 1.4, 'fade_source': 'D_out'}},
        'glow_cards': {'spartan_laser_luminous': {'shader': 'sl_lum_card', 'scale': 1.3, 'lift': 0.05}},
        'glow_points': [{'marker': 'primary trigger', 'shader': 'sl_charge_glow', 'size': 7.0,
                         'forward': 1.0}],
        # the beam's textures (test 9): Halo 3's beam profile x its laser palette
        'baked_textures': {'sl_beam_add': {'profile': r'fx\contrails\_bitmaps\beam.bitmap',
                                           'palette': r'fx\particles\_gradients\laser_red_01.bitmap',
                                           'premultiply': True},
                           'sl_beam_body': {'profile': r'fx\contrails\_bitmaps\beam.bitmap',
                                            'palette': r'fx\particles\_gradients\laser_red_01.bitmap'}},
        'drop_materials': ['invalid'],
        # the template's overheat steam spawns at a marker: Halo 3's side vent
        'markers': {'fx_side_vent': 'overheat'},
        'template': RL + r'shaders\rocket launcher body',
    },

    # FP animations (h1_fp_retarget.py). Halo 3 spartan laser frames: ready 31, put_away 5,
    # fire_1 2 (the tap: the tracer), fire_2 28 (the charged shot), melee_strike_1 42,
    # overheated 59, o_h_exit 24, posing var1 89, idle var1..3 99
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\support_high\fp_spartan_laser\fp_spartan_laser.model_animation_graph',
        'render_model': H3 + r'\fp_spartan_laser\fp_spartan_laser.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ')
                  for n in ('gun', 'cover', 'handle', 'laser', 'shield', 'telescope', 'lens_1', 'lens_2')},
        'h1_dir': r'weapons\spartan laser\fp',
        'h1_model': r'weapons\spartan laser\fp\fp',
        'align': 'same_space',
        # the SMG's placement (user's pick, A1) as the start; TEST 1 (user): 'size is good,
        # move it left 1 unit and up 4 units' (1 unit = 0.01 wu; y = left)
        # TEST 2 (user): 'back 0.5 units to the right and 2 units down'
        'view_offset': (-0.0225, 0.005, -0.0225 + 0.02),
        'anims': {
            'first_person:idle:var1': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1': 'first-person fire-1',
            'first_person:fire_2': 'first-person fire-2',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            # Halo 3's ONE overheat animation (59 fr) plays on Halo 1's `overheating`; its
            # last frame held for `overheated` (without it the engine REPLAYS `overheating`:
            # the Sentinel Beam's finding)
            'first_person:overheated': 'first-person overheating',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
        'holds': {'first-person overheated': ('first_person:overheated', 50)},
    },

    # Halo 3's own sounds (h1_port_sounds.py spartan_laser). Levels = the stock Halo 1 sound each
    # stands in for (h1_stock_sound_levels.py, 2026-10-09): rocket launcher fire -15.1 (2 perms
    # -15.3 / -14.9: the yardstick's shot), plasma rifle startcharge -12.0 / charge -11.2 (the
    # plasma pistol template's charging loop: start + loop), plasma rifle overheat -19.5,
    # plasmahit -11.3, rocket_ready -18.3, rocket_melee -21.8, rocket_posing -22.1, sniper
    # zooms -28.9 / -29.2, rlauncher_impact -23.0, rocket_ammo -28.8, AR dryfire -17.6. Halo 3's
    # laser NAMES the rocket launcher's drop (its material effects) and ammo sounds and the
    # battle rifle's dry fire: own copies of those (the Brute Shot's precedent). Its firing
    # effect plays fire + the overheat together: the overheat goes on Halo 1's overheating
    # animation, which starts with the shot
    'sounds': {
        'catalog': 'Spartan Laser',
        'dir': B.join(['sound', 'weapons', 'spartan_laser_port']),
        'h3_dir': 'data\\sound\\weapons\\spartan_laser\\',
        'sounds': {
            'sl_fire': (['fire'], 'sound\\sfx\\weapons\\rocket launcher\\fire', -15.1),
            'sl_charge_in': (['charging\\charging\\in'], 'sound\\sfx\\weapons\\plasma rifle\\startcharge', -12.0),
            'sl_charge_loop': (['charging\\charging\\loop'], 'sound\\sfx\\weapons\\plasma rifle\\charge', -11.2),
            'sl_charge_out': (['charging\\charging\\out'], 'sound\\sfx\\weapons\\plasma rifle\\startcharge', -12.0),
            'sl_overheat': (['spartan_laser_overheat'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -19.5),
            'sl_impact': (['spartan_laser_impacts'], 'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
            'sl_ready': (['fp_spartan_laser\\fp_spartan_laser_ready'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_ready', -18.3),
            'sl_melee': (['fp_spartan_laser\\fp_spartan_laser_melee'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_melee', -21.8),
            'sl_pose': (['fp_spartan_laser\\fp_spartan_laser_posing_var1'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_posing', -22.1),
            'sl_zoom_in': (['spartan_laser_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'sl_zoom_out': (['spartan_laser_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'sl_drop': (['data\\sound\\weapons\\rocket_launcher\\rocket_launcher_drop'], 'sound\\sfx\\impulse\\weapon_drops\\rlauncher_impact', -23.0),
            'sl_ammo': (['data\\sound\\weapons\\rocket_launcher\\rocket_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\rocket_ammo', -28.8),
            'sl_dryfire': (['data\\sound\\weapons\\battle_rifle\\dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only spartan_laser) on a COPY of the Halo 1 PLASMA
    # PISTOL: heat + battery, no magazine, and Halo 1's CHARGED TRIGGER PAIR -- trigger 0
    # charges; released early it fires its own projectile, fully charged it fires trigger 1.
    # Halo 3's spew-charge FIRES BY ITSELF when charged: trigger 0's charge hold 0 + overcharged
    # action 'discharge' (the fuel rod's and the BR burst's way). A tap fires trigger 0's
    # projectile = Halo 3's NO-DAMAGE tracer (Halo 3 fires it while charging; Halo 1 cannot
    # fire during a charge). DEFAULT = HALO 3's OWN NUMBERS; the rocket ratio = the balance rows.
    # Template layout (the Beam Rifle's reading): exports A heat / B primary charged / C
    # illumination / D age; functions 0 age inverted (A out), 1 heat (B out), 2 illumination
    # (C out), 3 primary charged (D out); attachments 0 muzzle light (C), 1 / 4 heat flares
    # (B), 2 overcharge flare (D), 3 the charging loop (D)
    'pickable': {
        'weapon': SL + 'spartan laser',
        'template': PP + 'plasma pistol',
        'world_model': SL + 'spartan laser',
        'fp_model': SL + 'fp\\fp',
        'fp_anims': SL + 'fp\\fp',
        'label': 'sl',
        # two-handed HEAVY: Halo 1's rocket pose (the plan's proposal; Halo 3's weapon class
        # 'missile')
        'teach': ('sl', 'rl'),
        'keys': {'first-person melee': 5},          # H3 melee_strike_1 primary_keyframe 5
        'sounds': {'first-person ready': SND + 'sl_ready',
                   'first-person posing': SND + 'sl_pose',
                   'first-person melee': SND + 'sl_melee',
                   'first-person overheating': SND + 'sl_overheat'},
        # every template attachment goes: lights / flares draw at the hidden THIRD-PERSON gun
        # in first person (Sentinel Beam, Beam Rifle); the muzzle light moves into the firing
        # effect; the plasma rifle's charging loop is replaced by Halo 3's (fire_loop)
        'drop_attachments': [0, 1, 2, 3, 4],
        # Halo 3's charging sound (sound_looping in / loop / out) while the trigger charges:
        # the template's charge function (D out = primary charged) scales it
        'fire_loop': {'like': 'sound\\sfx\\weapons\\plasma rifle\\charging',
                      'start': SND + 'sl_charge_in', 'loop': SND + 'sl_charge_loop',
                      'end': SND + 'sl_charge_out', 'tag': SND + 'sl_charging',
                      'marker': 'primary trigger', 'scale': 'D_out'},
        # trigger 0: Halo 3's TRACER (spartan_laser_tracer: no damage, 4000 wu/s, range 120)
        'beam': {'projectile': (SR + 'sniper bullet', SL + 'tracer'),
                 'no_impact_damage': True, 'velocity': 4000.0, 'range': 120.0,
                 'contrail': {'from': SR + 'sniper', 'out': SL + 'tracer', 'rgb': RED,
                              'no_physics': True, 'blend': 'add'},
                 'proj_fields': {'proj_attrs.physics.water_gravity_scale': 0.0},
                 'clear_response_effects': True,
                 'triggers': (0,)},
        # trigger 1: the BEAM. Halo 3's 5 rounds = ONE Halo 1 round of the whole shot. Its
        # damage split in two so a direct hit is Halo 3's 570 and a near miss its splash:
        # IMPACT 470 (= 5 x the 94 aoe spike bump: what only a direct hit gets) + a DETONATION
        # splash 100 (= 5 x 20 over 0..0.6 wu, core 0.15). Both on copies of the ROCKET's
        # explosion damage (the yardstick's table) with Hunter armour x0.5. Responses: Halo 3's
        # beam overpenetrates units (except giants), glass, water, plants and detonates on the
        # rest -> the sniper bullet's overpenetrate set without Hunter skin (a giant), plus the
        # Jackal, player and Sentinel shields/bodies; detonate everywhere else (the splash).
        # OBSERVATION to check in game: an overpenetrated unit takes the impact (470) only
        'bullet': {'projectile': (SR + 'sniper bullet', SL + 'beam'),
                   'damage': (RL + 'explosion', SL + 'beam'),
                   # TEST 5 (two lasers): only the copy at the SNIPER's 1000 wu/s overpenetrated
                   # (impact at the corpse, then on the ground behind it); at Halo 3's 4000 (the
                   # whole 120 wu in one tick) Halo 1 does not overpenetrate. 1000 here: the
                   # range takes 0.12 s. (Collision radius 0 as well -- the sniper's)
                   # TEST 6 (user): 'the beam is not visible from where I fire -- only at an
                   # offset' (the Sentinel Beam's end-on case, but the trigger's first-person
                   # offset IS set): Halo 1 lays a contrail's FIRST point where the projectile
                   # is after its first update -- 33 wu out at 1000 wu/s, so from the firing
                   # point the beam starts almost on the crosshair. Halo 1 changes a projectile's
                   # speed from initial to final over its range (the Brute Shot's 16 -> 7): a
                   # beam that STARTS SLOW, 60 -> 1940 wu/s -- the first update 2 wu out, the
                   # 120 wu in ~0.2 s, ~380-700 wu/s at 20-40 wu (it penetrated at 1000)
                   'dmg': 470.0, 'velocity': (60.0, 1940.0), 'range': 120.0,
                   'fields': dict(DAMAGE_4B, **{'radius': (0.0, 0.0),
                                                'damage_modifiers.hunter_armor': 0.5}),
                   'explosion': {'effect': (RL + 'effects\\rocket explosion', SL + 'effects\\beam impact'),
                                 'damage': (RL + 'explosion', SL + 'splash'),
                                 'lower': 0.0, 'upper': (100.0, 100.0), 'radius': (0.0, 0.6),
                                 'mods': {'hunter_armor': 0.5},
                                 'fields': DAMAGE_4B,
                                 # TEST 3 (user): 'the impact is underwhelming, a small
                                 # plasma hole -- it should be a red laser explosion and leave
                                 # a bigger scorch'. Halo 3's impact: a burst, gas, smoke,
                                 # sparks and a scorch decal. The rocket explosion's own parts,
                                 # small and RED: its fire particle system x0.35 (fire state
                                 # recoloured), the grenade-char SCORCH decal, its light red,
                                 # its flare red, the drifting smoke; no shock wave, no gravel
                                 'drop_parts': [r'weapons\frag grenade\shock wave'],
                                 'drop_particles': ('gravel small',),
                                 'scale': 0.35, 'out_dir': SL + 'effects\\',
                                 'psys_tint': {'fire': ((1.0, 1.0, 0.45, 0.35), (1.0, 1.0, 0.12, 0.08))},
                                 # TEST 4 (user): 'is there a flare more fitting an energy
                                 # weapon?' Halo 1 has two flare particles: the grenade's and
                                 # `flare h stealth cannon` (the charged plasma bolt's impacts)
                                 'particle_swaps': {r'effects\particles\lens flare\grenade explosion flare':
                                                    r'effects\particles\lens flare\flare h stealth cannon'},
                                 'particle_tint': RED, 'tint_match': ('flare h stealth cannon',),
                                 'light': {'out': SL + 'effects\\impact light', 'rgb': RED},
                                 'swaps': {r'sound\sfx\weapons\frag grenade\expl': SND + 'sl_impact'}},
                   'default_responses': {'overpenetrate': [9, 11, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 28, 29, 30],
                                         'detonate': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 18, 26, 27, 31, 32]},
                   # 4b list 2 (H3 laser / H3 rocket onto the H1 rocket): collision radius 0.1 x
                   # 0.15/0.1, air damage range 100 x 500/150, water 10 x 20/10. Velocity keeps
                   # Halo 3's 4000 (the rocket accelerates 8 -> 16, the laser is instant: the
                   # ratio's 6000 -> 2500 means nothing). Water gravity 0 (Halo 3's)
                   'proj_fields': {'proj_attrs.physics.water_gravity_scale': 0.0,
                                   # TEST 4 (control, the stock sniper as secondary): the
                                   # sniper overpenetrates, the laser did not. The suspect: this
                                   # 4b collision radius (the sniper's is 0: a swept sphere may
                                   # re-hit the unit it passes) -> 0 on the beam; the test
                                   # secondary also takes the sniper's 1000 wu/s
                                   'proj_attrs.collision_radius': 0.0,
                                   'proj_attrs.physics.air_damage_range': (0.0, 333.333),
                                   'proj_attrs.physics.water_damage_range': (0.0, 20.0)},
                   # TEST 1 (user): 'the beam is thin and transparent, not epic at all'. It
                   # was the sniper's vapour trail (wispy texture, 0.1-0.35 s) recoloured. Now
                   # a SOLID beam texture (the plasma rifle contrail's: a30's beam emitter
                   # draws a 0.5 wu beam with it) in two additive layers on the same marker: a
                   # white-hot CORE and a wide red GLOW, both lingering ~0.5 s and fading (Halo
                   # 3's beam: a thick red beam with a bright core)
                   # TEST 4 (user): 'transparent beam visible again -- can't we reuse the beam
                   # the Sentinels fire?' We can: the CORE is now a copy of the Sentinel's beam
                   # contrail (characters\sentinel\beam: additive, its own beam texture; its
                   # points live 0 s -- a continuous beam -- so they get lifetimes here), white-
                   # hot; the GLOW is ALPHA-BLENDED opaque red on the solid texture (additive red
                   # reads transparent over a bright scene)
                   # TEST 9 (colour-coded layers, user): 'the big initial part is red/magenta,
                   # then comes the sentinel beam style (orange-white) -- they don't match'.
                   # Halo 3's beam_system (fx\firing_1p) is ONE layer: a soft beam profile
                   # (fx\contrails\_bitmaps\beam: constant along u, 0 -> 255 -> 0 across v)
                   # palette-mapped through fx\particles\_gradients\laser_red_01 (black ->
                   # deep red -> red -> near-white 254 / 249 / 249), blended additively x alpha
                   # (template _2_8_0_0). Baked into one texture (h1_h3_weapon_model
                   # `baked_textures`): an ADDITIVE beam (premultiplied) + a narrower ALPHA-
                   # BLENDED body on the same colours (solid over bright scenery), white contrail
                   # colour so the texture's colours show. Widths a start (Halo 3's thickness
                   # function reads empty)
                   'contrail': {'from': SR + 'sniper', 'out': SL + 'beam', 'no_physics': True,
                                'blend': 'add', 'bitmap': SL + 'bitmaps\\sl_beam_add',
                                'sequence': (0, 0),
                                'states': [{'duration': (0.25, 0.3), 'transition': (0.3, 0.4),
                                            'width': 0.22, 'argb': (1.0, 1.0, 1.0, 1.0)},
                                           {'width': 0.18, 'argb': (0.0, 1.0, 1.0, 1.0)}],
                                'extra': [{'out': SL + 'beam body', 'blend': 'alpha_blend',
                                           'bitmap': SL + 'bitmaps\\sl_beam_body', 'sequence': (0, 0),
                                           'states': [{'duration': (0.25, 0.3), 'transition': (0.3, 0.4),
                                                       'width': 0.12, 'argb': (0.9, 1.0, 1.0, 1.0)},
                                                      {'width': 0.1, 'argb': (0.0, 1.0, 1.0, 1.0)}]}]},
                   # the impacts: the plasma pistol bolt's per-material effects (energy, not
                   # bullet dust), recoloured red (the Beam Rifle's recipe)
                   'material_effects_from': PP + 'bolt',
                   'change_color': {'from': PP + 'bolt', 'rgb': RED},
                   'impact_tint': {'rgb': RED, 'out': SL + 'effects\\impact\\',
                                   'match': ('particles\\energy\\', 'shield impact'),
                                   'decals': {'effects\\decals\\bullet holes\\plasma green burn large':
                                              'effects\\decals\\bullet holes\\plasma burn'}},
                   'triggers': (1,)},
        # Halo 3: no error, no spread; the muzzle offset -- the trail starts at the FP muzzle
        'trigger': {'acceleration_time': 0.0, 'deceleration_time': 0.0,
                    'first_person_offset': FP_MUZZLE},
        # Halo 3: overheated at 1.0, back at 0.1; Halo 1 has ONE loss: every shot overheats,
        # so the OVERHEATED loss (0.4) is the one that ever runs -> a 2.25 s vent
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.4},
        # TEST 1 (user): 'venting looks like the fuel rod venting -- as close to the original as
        # possible'. The template's vent = green `plasma overheat` energy particles; Halo 3's =
        # a 2.5 s first-person STEAM event from the side vent (fx\particles\steam, a line
        # emitter): Halo 1's white `effects\particles\air\steam`, spread over 2.2 s (the vent)
        'overheated_effect': {'from': PP + 'effects\\overheated', 'out': SL + 'effects\\overheated',
                              'locations': {'vent_rear': 'overheat', 'vent_mid': 'overheat',
                                            'vent_front': 'overheat'},
                              # TEST 2 (user): 'I can't see the steam at all' -- Halo 1's
                              # `air\steam` (a 4 s ambient puff) at the sparks' 2-3 cm radius.
                              # Now Halo 1's FIRST-PERSON gun smoke (`smoke h fp`, 1 s), x3
                              # TEST 7 (user): 'still travels to the right, and moved further
                              # right' -- the yaw did not change its travel: Halo 1's FP smoke
                              # rides `warm smoke cloud` physics ('uses simple wind') and drifts
                              # with a30's wind. An OWN copy on `vacuum particle` physics (the
                              # plasma sparks' own: no wind, no gravity) keeps the vent's
                              # direction. The flipped offset moved it right: +x IS left
                              'own_particles': [{'from': r'effects\particles\air\smoke h fp',
                                                 'out': SL + 'effects\\vent smoke',
                                                 'physics': r'effects\point physics\vacuum particle'}],
                              'particles': {r'effects\particles\energy\plasma overheat': SL + 'effects\\vent smoke'},
                              # TEST 4 (user): 'phasing through the weapon -- reduce to 50%'
                              'radius_scale': 1.5,
                              # TEST 3 (user): steam visible, white confirmed (Halo 3); 'double
                              # check the position'. The marker IS Halo 3's (fx_side_vent, the
                              # steam event's location 3); the plasma pistol's entries spray to
                              # BOTH sides (+-60..90 deg, its twin vents) -- all out of the vent
                              # TEST 6 (user): 'the steam moves left to right from the vent
                              # THROUGH the weapon -- revert the direction': yaw 0 points INTO
                              # the gun (the marker reading had the axis flipped), so 180 deg,
                              # and the 2.5 cm offset the other way (it had pushed the start in)
                              'direction': (0.0, 0.0), 'cone': 25.0,
                              # TEST 5 (user): 'move the steam ejection to the left'. The vent
                              # marker sits on the gun's LEFT side and points left (its x axis =
                              # camera +y in the idle pose, out/sl/marker_dir.py) -- the puffs
                              # started inside the shell: 2.5 cm further out along the vent
                              # TEST 8 (user): 'fixed, emitted to the left -- move it back half
                              # a unit to the right'
                              'offset': (0.02, 0.0, 0.005),
                              'duration': 2.2, 'distribution': 'constant', 'tint': (1.0, 1.0, 1.0)},
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.0, 0.0)},
        # H3 aim assist, absolute; zoom = Halo 3's one level 2.5x
        'aiming': {'autoaim_angle': 1.0, 'autoaim_range': 25.0,
                   'magnetism_angle': 5.0, 'magnetism_range': 25.0,
                   'zoom_levels': 1, 'zoom_ranges': (2.5, 2.5)},
        # THE FIRING EFFECT of the beam (the Sentinel Beam's recipe): the plasma pistol's flash
        # sprite tinted red, Halo 3's fire sound, a red muzzle light 0.1 s
        'fire_effect': {'from': PP + 'effects\\fire bolt', 'out': SL + 'effects\\fire beam',
                        'sound': SND + 'sl_fire', 'light': SL + 'muzzle light',
                        'keep_particles': 'flash c generic', 'tint': (1.0,) + RED},
        'own_light': {'shape': PP + 'muzzle flash', 'look': PP + 'muzzle flash',
                      'out': SL + 'muzzle light', 'argb': (1.0,) + RED, 'duration': 0.1},
        'fields': {
            # TRIGGER 0 = the charge (Halo 3: 2.5 s, fires itself when charged)
            'weap_attrs.triggers.0.charging.charging_time': 2.5,
            'weap_attrs.triggers.0.charging.charge_hold_time': 0.0,
            'weap_attrs.triggers.0.charging.overcharged_action': 'discharge',
            'weap_attrs.triggers.0.misc.heat_generated_per_round': 0.0,
            'weap_attrs.triggers.0.misc.age_generated_per_round': 0.0,
            # a tap: Halo 3's tracer effect has no sound and no flash
            'weap_attrs.triggers.0.firing_effects.0.firing_effect.filepath': '',
            'weap_attrs.triggers.0.firing_effects.0.firing_damage.filepath': '',
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.triggers.0.firing_effects.0.misfire_damage.filepath': '',
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'sl_dryfire',
            # TRIGGER 1 = the beam: heat 1 (every shot overheats), age 0.2 (5 shots a battery:
            # Halo 3's 0.04 a round x 5 rounds, campaign = multiplayer)
            'weap_attrs.triggers.1.misc.heat_generated_per_round': 1.0,
            # TEST 1 (user): 'the third shot got the battery down to 39 instead of 40': 0.2 in
            # float32 sums to 0.6000000238 after three shots (1 - that = 39.99..%). The float
            # just below 0.2 shows 80 / 60 / 40 / 20 / 0 -- but after five shots the age is
            # 0.99999994 < 1: TEST 2 checks that no 6th shot fires
            'weap_attrs.triggers.1.misc.age_generated_per_round': 0.19999999,
            # TEST 2 (user): 'the 6th shot fires'; TEST 3: clearing the charged trigger's 'can
            # fire with partial ammo' did NOT stop it (the template's flag is kept). Halo 1's
            # AGE MISFIRE does it instead (below): misfire from age 0.9999 at chance 1 -- after
            # five shots the age is 0.99999994, after four 0.79999995
            # (no empty effect on trigger 1: an empty battery clicks on trigger 0, the one the
            # player presses; trigger 1's slot is EFFECT-class -- a sound there failed the build)
            # Halo 3's laser never misfires on a low battery (the template's 0.9 / 0.5 would)
            'weap_attrs.age.misfire_start': 0.9999,
            'weap_attrs.age.misfire_chance': 1.0,
            'weap_attrs.triggers.1.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.triggers.1.firing_effects.0.misfire_damage.filepath': '',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'sl_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'sl_zoom_out',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'sl_ammo',
            'item_attrs.collision_sound.filepath': SND + 'sl_drop',
            # STEP 4b (before boot 1). List 2 (H3 laser / H3 rocket onto the H1 rocket):
            # bounding radius 0.2875 x 0.215/0.25, active camo ding 1 x 0.12/1; the tracer
            # barrel's firing-effect shot count 0 skipped (Halo 3's tracer barrel: no Halo 1
            # meaning). List 4 (the source pair agrees -> the yardstick's): acceleration scale
            # 2, camo regrowth 0, illumination recovery 0.3 (both triggers). List 3: trigger
            # flags kept (Halo 3's laser trigger has no latch: holding charges again after the
            # vent); weapon type kept the template's (its charge pair -- judged in boot 1);
            # Halo 3's 'magnetizes only when zoomed' = a BALANCED catalog row (the Beam Rifle's
            # user rule); 'strict deviation angle': no Halo 1 field
            'obje_attrs.bounding_radius': 0.2875 * 0.215 / 0.25,
            'weap_attrs.interface.active_camo_ding': 0.12,
            'weap_attrs.interface.active_camo_regrowth_rate': 0.0,
            'obje_attrs.acceleration_scale': 2.0,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.3,
            'weap_attrs.triggers.1.misc.illumination_recovery_time': 0.3,
        },
        # the smash (Halo 3 smash_melee 80; the template's 40 / 50..60 = the rocket's): DEFAULT
        # Halo 3's 80 as the copy's mean; balanced 55 (x 80/80 the rocket's)
        # the ROCKET's melee tag (the same 40 / 50..60 as the template's; step 4b list 4: its
        # breaking effect is the yardstick's -- Halo 3's smash and smash agree)
        'melee': (RL + 'melee', SL + 'melee'),
        'melee_dmg': 80.0,
        'melee_response': PP + 'melee_response',
        'messages': ('Picked up a spartan laser', 'Picked up %d rounds for spartan laser'),
        'icon': 'spartan laser',
        # the PLASMA PISTOL's HUD (heat + battery meters) with Halo 3's laser reticle (H3
        # hud_reticles #11) at the reserved 26. ZOOM = Halo 3's scope (the standard):
        # ui\chud\spartan_laser -- the battle rifle's ring (mirrored, scale 1.1), the zoom
        # level marks and protractor, the zoomed crosshair (spartan_outerring #25); its meter
        # fills and warning flashes dropped (a mask is static). Size / shape: the Beam Rifle's
        # picked 80% / x0.8 (judged in game). The plasma pistol HUD has no screen effect: the
        # sniper's (night vision + desaturation off)
        'hud': {'donor': PP + 'plasma pistol', 'out': SL + 'spartan laser',
                'screen_effect_from': SR + 'sniper rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                'scope': {'chud': r'ui\chud\spartan_laser', 'out': SL + 'bitmaps\\scope_mask',
                          # TEST 1 (user): 'the HUD is oval instead of round' with the Beam
                          # Rifle's x0.8 squash -> the BR's 4/3 (its ring is the same bitmap,
                          # battle_rifle_scope) and span 660 (Halo 3's ring at 58%; the laser's
                          # widget is x1.1 the BR's, which the bake keeps)
                          'size': 1024, 'span': 660.0, 'aspect': 4 / 3.0, 'alpha': 'outside',
                          'per_widget': {'overheat_flash_scope': {'drop': True},
                                         'lowbatt_flash_scope': {'drop': True},
                                         'charge_meter': {'drop': True},
                                         'meter_overheat_flash_right': {'drop': True}}},
                'reticle': ('hud_reticles', 11, 'spartan laser'),
                # TEST 1 (user): 'not close enough to the original: lost its delicate look
                # with the thickened lines, and the inner circle is missing'. Halo 3 draws TWO
                # crosshair widgets: hud_reticles #11 at 0.59 and the inner double circle
                # `spartan_outerring` (one 100 px bitmap) at 0.95 -> both layers, no thickening
                'reticle_layers': [(r'ui\chud\bitmaps\spartan_outerring.bitmap', None, 0.95 / 0.59)],
                # TEST 2 (user): unthickened, the lines 'look fizzled out' (screenshot: broken
                # ticks). Cause: Halo 1 draws the 256 px sheet at about half size with NO
                # mipmaps (stock reticles have none either -- their strokes are thick), so a
                # 1-2 texel Halo 3 stroke is undersampled. A PREFILTER instead of thickening:
                # the art area-averaged x0.5 and back (h1_add_reticle.prefiltered)
                # TEST 3 (user): the prefilter did not fix it ('the idea is sound, iterate'). Now
                # the sheet art at HALF size (area-averaged) and the HUD overlay x2: Halo 1
                # MAGNIFIES the sprite (no texel skipped) instead of minifying it unmipped
                # TEST 4 (user): 'better, but fizzled again, especially the middle; the outer
                # circle's indentations connected where there should be gaps' -- at half size
                # a 1 px tick and its 1 px gap merge. The user's screenshot: Halo 1 draws the
                # reticle ~110 px across, Halo 3 the same art ~170 px at 1080p (its chud is 1152
                # units wide: 104 units x 1.67). Drawn at HALO 3's size at ~1 texel a pixel:
                # art x0.78 in the sheet (174 px), overlay x2.1 (the sheet shows at ~0.49 a
                # texel) -> ~179 px, magnified 1.03 (no texel skipped, gaps kept)
                # TEST 5 (user): 'keep the Halo 1 size; any other way to clean up the fizzled
                # art?' Any RESAMPLED art breaks up under Halo 1's unmipped ~2:1 minification
                # (tests 2-4). PIXEL DOUBLING: the art at its on-screen size (area-averaged, thin
                # lines brightened), then each pixel a 2 x 2 block in the sheet -- whichever
                # texel Halo 1 samples, it reads the intended screen pixel
                'reticle_thicken': 0,
                # TEST 6 (user's screenshot): pixel-doubled, it drew BLURRED; registration 126
                # changed nothing (test 7). User: 'a resolution fix won't hold on every setup'.
                # The GENERAL fix: MIPMAPS on this reticle's bitmap (stock HUD sheets have none;
                # Halo 3's do) -- the full-resolution art, minified by the GPU at any size
                # TEST 8 (user): mips changed NOTHING. TEST 9's chart (1 / 2 / 3 / 4 / 6 px line
                # pairs; 2 px the first to resolve, unevenly; 1 px rings fine but small): MCC
                # draws the sheet at ~0.5 with BILINEAR sampling -- a 2 x 2 average, so a 2 px
                # line is 1 px at 100 % or 2 px at 50 % by its phase and flickers along a curve.
                # Every stroke at least 3 sheet px (h1_add_reticle.grow_to: only the thinner
                # strokes, +1 px at 4x supersampling, per layer keeping its brightness); the
                # ticks (4 px) and all gaps unchanged. Checked in a bilinear simulation at
                # 0.49 and three sub-pixel phases (out/reticle_spartan_laser_sim.png)
                'reticle_min_width': 3,
                # Halo 3's CHARGE indicator (its triangle orbiting the reticle) -- DROPPED after
                # three boots: Halo 1's `charge` crosshair type (no stock HUD uses it) drew
                # nothing as an own bitmap (+ _r twin), as small sprites in hud_reticles at 44,
                # or as whole frames there (tests 2-4). The muzzle charge glow is the cue; the
                # experiment's sequences were removed from both sheets again
                },
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py spartan_laser). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the ROCKET LAUNCHER ratio rule (step 4a, user
    # 2026-10-09), version A (with both spike bumps) until the A/B test decides.
    # Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Spartan Laser', 'source': 'Halo 3', 'donor': 'Rocket Launcher', 'default_on': False,
            # the BEAM (trigger 1): the derivation would take `beam` = the tracer
            'requires': ['proj ' + SL + 'beam'],
            'desc': "Halo 3's Spartan Laser: its model, first-person animations, sounds, scope and "
                    "numbers. Hold the trigger 2.5 s and it fires one devastating red beam that "
                    "overheats it; five shots a battery, 2.5x zoom.",
            'balance_desc': "Measured against the Rocket Launcher, which both games have: 408 "
                            "damage per beam, a 3.3 s charge and a 3 s vent, a shorter reach and "
                            "Halo 1-style aim assist; the battery stays five shots.",
            'balance': [
                # A: impact 470 x 315/440 = 336.5, splash 100 x 315/440 = 71.6
                row('jpt!', SL + 'beam', 'Damage Lower Bound', 336.5, 470.0, 'Beam Damage'),
                row('jpt!', SL + 'beam', 'Damage Upper Bound', 336.5, 470.0, 'Beam Damage'),
                row('jpt!', SL + 'beam', 'Damage Upper Bound Max', 336.5, 470.0, 'Beam Damage'),
                row('jpt!', SL + 'splash', 'Damage Upper Bound', 71.6, 100.0, 'Beam Damage'),
                row('jpt!', SL + 'splash', 'Damage Upper Bound Max', 71.6, 100.0, 'Beam Damage'),
                # trigger 0's charge (index 0 of Triggers)
                row('weap', SL + 'spartan laser', 'Charging Time', 3.33, 2.5, 'Charge Time', block='Triggers'),
                row('weap', SL + 'spartan laser', 'Heat Loss Per Second', 0.3, 0.4, 'Heat Loss'),
                row('proj', SL + 'beam', 'Maximum Range', 88.0, 120.0, 'Projectile'),
                row('proj', SL + 'tracer', 'Maximum Range', 88.0, 120.0, 'Projectile'),
                row('weap', SL + 'spartan laser', 'Autoaim Angle', 1.2, 1.0, 'Autoaim'),
                row('weap', SL + 'spartan laser', 'Autoaim Range', 35.0, 25.0, 'Autoaim'),
                row('weap', SL + 'spartan laser', 'Magnetism Angle', 6.0, 5.0, 'Magnetism'),
                row('weap', SL + 'spartan laser', 'Magnetism Range', 35.0, 25.0, 'Magnetism'),
                # the smash: 55 = the template's own 40 / 50..60; default Halo 3's 80 (x 80/55:
                # 58.18 / 72.73..87.27)
                row('jpt!', SL + 'melee', 'Damage Lower Bound', 40.0, 58.18, 'Melee Damage'),
                row('jpt!', SL + 'melee', 'Damage Upper Bound', 50.0, 72.73, 'Melee Damage'),
                row('jpt!', SL + 'melee', 'Damage Upper Bound Max', 60.0, 87.27, 'Melee Damage'),
                # Halo 3's 'magnetizes only when zoomed' (user rule, the Beam Rifle: balanced
                # only) -- the WHOLE weapon flags word, Assembly 'Flags' nth 3 (0 object, 1 a
                # block's, 2 item, 3 weapon): 2048 cannot fire at maximum age + 32
                dict(row('weap', SL + 'spartan laser', 'Flags', 2080, 2048, 'Aim assist zoomed only'), nth=3),
            ]},
    },

    # step 4b (port_field_audit.py --port spartan_laser): the source pair (H3 spartan laser vs
    # the yardstick, H3 rocket launcher) against the target pair (the H1 port vs the H1 rocket;
    # the template is the plasma pistol -- the full field diff covers it)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\spartan_laser.weapon', r'objects\weapons\support_high\rocket_launcher\rocket_launcher.weapon'),
                   'projectile': (H3 + r'\projectiles\spartan_laser_beam.projectile',
                                  r'objects\weapons\support_high\rocket_launcher\projectiles\rocket.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\spartan_laser_beam.damage_effect',
                                     r'objects\weapons\support_high\rocket_launcher\damage_effects\rocket_launcher_explosion.damage_effect'),
                   'melee': (r'objects\weapons\damage_effects\smash_melee.damage_effect',
                             r'objects\weapons\damage_effects\smash_melee.damage_effect')},
        'target': {'weapon': (SL + 'spartan laser.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (SL + 'beam.projectile', RL + 'rocket.projectile'),
                   'damage_effect': (SL + 'splash.damage_effect', RL + 'explosion.damage_effect'),
                   'melee': (SL + 'melee.damage_effect', RL + 'melee.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), a battery weapon spawns
    # charged (rounds 0 / 0)
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

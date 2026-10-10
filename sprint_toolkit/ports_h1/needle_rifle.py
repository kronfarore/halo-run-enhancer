r"""Needle Rifle (Halo Reach, wave B2): a MAGAZINE semi-automatic NEEDLE rifle with a 2x zoom on a
copy of the Halo 1 NEEDLER (the yardstick, step 4a: its needle projectile -- attach, its OWN
super-detonation effect, the needle materials -- its ammo and its 'needles remaining' function).
The DMR (dmr.py) is the nearest shape for the Reach plumbing (`reach:` paths, Reach's bank, its
own FP graph); the Spike Rifle (brute_spiker.py) for a stuck projectile and glow spots."""
from ._common import B, reserved, row

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\needle_rifle'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle'
NR = 'weapons\\needle rifle\\'
SND = 'sound\\weapons\\needle_rifle_port\\'
N = 'weapons\\needler\\'
PISTOL = 'weapons\\pistol\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
RSN = RS + 'needle_rifle\\'
# Halo 1 material indices (proj material responses): TERRAIN / props -- dirt, sand, stone, snow,
# wood, metal hollow / thin / thick, rubber, glass, plastic, ice. Reach's needle sticks only to
# BIPEDS ('attach, only against bipeds'); elsewhere it bounces at 0-30 deg (friction 0 / 0.7,
# noise 2 deg) or detonates -- with NO detonation effect, so it just ends
TERRAIN = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 27, 31]
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# Reach's self-illumination colours (ManagedBlam, the shaders' function data, 2026-10-10):
# the stowed CRYSTALS (needler_crystal_solid, illum_detail, intensity 3) violet (87, 19, 237)
# -> (160, 33, 248); the needle HOLES (simple illum, intensity 3 -> 2) (106, 13, 143) ->
# (174, 27, 255); the display / indicator halograms blue (22, 37, 105) at 2.5
VIOLET = (160 / 255.0, 33 / 255.0, 248 / 255.0)

PORT = reserved(
    order=20, wave='B2', name='Needle Rifle', source='Halo Reach',
    messages=(73, 74), icon=40, reticle=29, label='nr', teach_from='pr',
    sound_dir='sound\\weapons\\needle_rifle_port', weapon_dir='weapons\\needle rifle',
    yardstick={
        # step 4a (user, 2026-10-10; h1_role_compare.py needle_rifle)
        'pick': 'Needler',
        'reason': ("the needle family (Reach's `needle` group = Halo 1's needle materials) and the "
                   "only Halo 1 weapon with a supercombine; FIRED LIKE A PRECISION WEAPON (Reach's "
                   "semi-auto trigger, straight unguided needle, 2x zoom). The port has its OWN "
                   "supercombine damage (a Halo 1 projectile names its own super_detonation "
                   "effect; only the count, 7, is the engine's): default Reach's 390 at 7, stuck "
                   "4 s; balanced 60 at 7 (needler ratio), stuck 0.75 s x 6/2 shot intervals "
                   "(7 needles vs Reach's 3) = 2.25 s. Per-weapon count via halo1.dll: a later "
                   "Supercombine Needle Count card for Halo 1"),
        # DEFAULT = Reach's own numbers (wave rule); these are the BALANCED rows (H1 needler x
        # Reach needle rifle / Reach needler). Reach: needle rifle 6 per 0.25 s = 4/s, 21 (63 /
        # 105), reload 82 fr, error 0.15 -> 2, 2x, 1500 wu/s, range 250, aim 2.25/25 5/25,
        # supercombine 350 + 40 at 3 (0.05 s); needler 6 at 8 -> 12/s, 24 (72 / 120), 44 fr,
        # error 0.1 -> 3, 11 wu/s homing, range 26, aim 8/26 16/26, the same 390 at 6. H1
        # needler 10 (when the needle bursts) at 3 -> 10/s, 20 (80 / 80), 70 fr, 4 wu/s
        # guided, range 20, aim 6/25 12/25, supercombine 60 at 7, stuck 0.75 s
        'balanced': {
            'damage': 10.0,              # 10 x 6/6
            'rate': 3.333,               # 10/s x 4/12 (semi-automatic: the tag rate is the cap)
            'magazine': 18,              # 20 x 21/24 = 17.5
            'rounds_total_initial': 70,  # 80 x 63/72
            'rounds_total_maximum': 70,  # 80 x 105/120 (the needler is not dual-wieldable in Reach)
            'reload_s': 4.35,            # 70 fr x 82/44 = 130.5 fr
            'velocity': 545.0,           # 4 x 1500/11 (the needler's guided crawl -> a straight needle)
            'range': 192.0,              # 20 x 250/26
            'aim': (1.69, 24.0, 3.75, 24.0),  # 6 x 2.25/8, 25 x 25/26; 12 x 5/16, 25 x 25/26
            'zoom': 2.0,                 # Reach's own 2x (the needler has none)
            'super': 60.0,               # 60 x 390/390, at Halo 1's 7
            'stuck_s': 2.25,             # 0.75 x 4/4 (the attached timer ratio) x 6/2 intervals
            'melee': None},              # Reach shares strike_melee: x1 = the needler's own
        'measured': 'h1_role_compare.py needle_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Needler', 'Sniper Rifle'],
            'why': 'magazine, semi-auto, 2x zoom, fast needle that supercombines like the needler',
            'lacks': "Reach's 3-needle supercombine (Halo 1's engine count is 7)"}},
    # step 11: Reach's ai\generic Needle Rifle entry (m10) over a base -- 'nr' has no carrier.
    # Donor / WDM rule: filled at step 11 (h1_weapon_carriers of the needler)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map',
                    'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle'},
)

PORT.update({
    'status': 'in progress',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for
    # world AND first person. needle_rifle.render_model: 15 nodes -- b_gun (root), b_scope (+
    # b_shell under it) and TWELVE stowed needles b_l_needle1-6 / b_r_needle1-6 (Reach shows
    # the magazine with them: the `ammunition_needles` replacement animation); 1 mesh, 13
    # parts, primary_trigger present. Materials: needle_rifle_metal / _shell (self-illum OFF),
    # needle_rifle_glass (opaque, illum off), needle_holes (purple illum), needler_crystal_solid
    # (the stowed needles, violet illum_detail), needle_rifle_display (a METER shader: illum
    # plasma_pistol_display, meter plasma_launcher_holo), needle_rifle_illum_indicator and
    # needle_rifle_reload_effect (halograms)
    'model': {
        'dir': r'weapons\needle rifle',
        'world': R + RW + r'\needle_rifle.render_model',
        'fp': R + RW + r'\needle_rifle.render_model',
        'world_name': 'needle rifle',
        'markers': {'primary_ejection': 'primary ejection', 'left_hand': 'left hand'},
        'shaders': {'needle_rifle_metal': (R + RW + r'\bitmaps\needle_rifle_diffuse.bitmap', None),
                    'needle_rifle_shell': (R + RW + r'\bitmaps\needle_rifle_diffuse.bitmap', None),
                    'needle_rifle_glass': (R + RW + r'\bitmaps\needle_rifle_diffuse.bitmap', None),
                    'needle_holes': (R + r'objects\vehicles\covenant\phantom\bitmaps\phantom_illum.bitmap',
                                     R + r'objects\vehicles\covenant\phantom\bitmaps\phantom_illum.bitmap'),
                    'needler_crystal_solid': (R + r'objects\weapons\pistol\needler\bitmaps\needler_crystal_illum.bitmap',
                                              R + r'objects\weapons\pistol\needler\bitmaps\needler_crystal_illum.bitmap')},
        # boot 1: the two halograms (scrolling data stream / reload shimmer: no Halo 1 shader)
        # dropped -- the look is judged in game (render by material first)
        'drop_materials': ('needle_rifle_illum_indicator', 'needle_rifle_reload_effect'),
        'template': N + r'shaders\needler gun',
        'glow': {'needle_holes': (174 / 255.0, 27 / 255.0, 1.0), 'needler_crystal_solid': VIOLET},
        # BOOT 1 (user): 'the display shows only squares'. needle_rifle_display is a Reach METER
        # shader: its illum map plasma_pistol_display = a RING GAUGE (the ring in R, an angular
        # fill gradient in A; G and B solid 255 -- so max(RGB) made every texel shape). The
        # Carbine's `meters` (shader_transparent_meter) with the shape from R (`shape`), the
        # fill = AMMO: the needler template's out C (`needles remaining`, B in = primary
        # ammunition); the halogram blue (22, 37, 105 at 2.5) normalized, off a quarter
        'meters': {'needle_rifle_display': {
            'map': R + r'objects\weapons\pistol\plasma_pistol\bitmaps\plasma_pistol_display.bitmap',
            'from': r'weapons\plasma rifle\fp\shaders\gauge', 'shape': 'r', 'gradient': 'alpha',
            'value': 'C_out', 'color': (22 / 105.0, 37 / 105.0, 1.0)}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's OWN fp_needle_rifle retargeted (the
    # DMR's recipe: drop Reach's helper nodes, its view_offset). fp_needle_rifle (26 animations,
    # reach_tags --pose): fire_1 var1-3 (11 fr), idle 100, posing var1 / var2 94, ready 19
    # (ready_initial 27), put_away 4, reload empty / full 82 (primary keyframe 48), melee 34
    # (primary 5), throw_grenade 44, moving 20, look 9.
    # BOOT 1 (user): 'the draining needles would be nice'. Reach's `ammunition_needles` (14 fr,
    # a REPLACEMENT on the 12 needle nodes: frame 0 = empty, 13 = full; a spent needle shrinks
    # to SCALE 0.01, turned 23 / 163 deg) = Halo 1's `first-person ammunition` OVERLAY (the
    # needler's: 21 frames after its reference, first = empty, last = zero delta = full; it
    # pulls spent needles into the gun). h1_fp_retarget `replacement_overlays`: the reference =
    # the full frame, every other node held at it, node scale carried
    'retarget': {
        'replacement_overlays': {'first_person:ammunition_needles': 'first-person ammunition'},
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\needle_rifle.render_model',
        'nodes': dict([('b_gun', 'frame b gun'), ('b_scope', 'frame b scope'), ('b_shell', 'frame b shell')]
                      + [('b_%s_needle%d' % (s, i), 'frame b %s needle%d' % (s, i))
                         for s in 'lr' for i in range(1, 7)]),
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\needle rifle\fp',
        'h1_model': r'weapons\needle rifle\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1)
        'view_offset': (-0.0225 - 0.025, 0.0, -0.0125),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Reach's own sounds (h1_port_sounds.py needle_rifle, Reach's sfx.fsb). Levels = the active
    # RMS of the stock Halo 1 NEEDLER sound each stands in for (h1_stock_sound_levels.py,
    # 2026-10-10): fire -16.0, dryfire -11.7, needle burst (expl) -15.9, reload -18.3, ready
    # -17.9, melee -18.4, posing -26.7, ammo -26.0, drop (plasma_impact) -18.7, supercombine
    # (needler_super_expl) -17.6; zoom = the DMR's sniper zoom levels (-28.9 / -29.2).
    # THE FIRE: Reach's firing effect plays needle_rifle_fire + an exterior TAIL; Halo 1 plays
    # one sound a round -> the shot and the exterior tail MIXED (the DMR)
    'sounds': {
        'catalog': 'Needle Rifle',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'needle_rifle_port']),
        'h3_dir': RSN,
        'sounds': {
            'nr_fire': ([RSN + 'needle_rifle_fire', RSN + 'n_rifle_tails_ext'],
                        'sound\\sfx\\weapons\\needler\\fire', -16.0),
            'nr_dryfire': ([RS + 'needler\\dryfire'], 'sound\\sfx\\weapons\\needler\\dryfire', -11.7),
            'nr_reload': (['needle_rifle_fp\\needle_rifle_reload'], 'sound\\sfx\\weapons\\weapon_anims\\needle_reload', -18.3),
            'nr_ready': (['needle_rifle_fp\\needle_rifle_ready'], 'sound\\sfx\\weapons\\weapon_anims\\needle_ready', -17.9),
            'nr_melee': (['needle_rifle_fp\\needle_rifle_melee'], 'sound\\sfx\\weapons\\weapon_anims\\needle_melee', -18.4),
            'nr_pose': (['needle_rifle_fp\\needle_rifle_posing1'], 'sound\\sfx\\weapons\\weapon_anims\\needle_posing', -26.7),
            'nr_zoom_in': (['needle_rifle_zoom\\needle_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'nr_zoom_out': (['needle_rifle_zoom\\needle_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            # Reach's weapon names carbine_ammo_pickup; its own needle_rifle_powerup is the bank's
            'nr_ammo': (['needle_rifle_powerup'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\needle_ammo', -26.0),
            'nr_drop': ([RS + 'needler\\needler_drop'], 'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            # a stuck needle's end (Reach: needle_rifle_bolt_expl) and the SUPERCOMBINE
            'nr_burst': (['needle_rifle_bolt_expl'], 'sound\\sfx\\weapons\\needler\\expl', -15.9),
            'nr_super': ([RS + 'needler\\needler_super_expl'], 'sound\\sfx\\impulse\\impacts\\needler_super_expl', -17.6),
            # the needle's FLYBY (Reach: needle_rifle_bolt_by; the needle's needler_projectile
            # -26.1 / -21.0 / -21.7 -> -22.9): found by hand before boot 1 -- port_sound_refs
            # does not read a projectile's own sound fields
            'nr_flyby': (['needle_rifle_bolt_by'], 'sound\\sfx\\impulse\\impacts\\needler_projectile', -22.9),
            # the BALANCED reload (the patcher retimes it, then swaps this in)
            'nr_reload_balanced': (['needle_rifle_fp\\needle_rifle_reload'], 'sound\\sfx\\weapons\\weapon_anims\\needle_reload', -18.3),
        },
        'stretch': {'nr_reload_balanced': 1.59},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only needle_rifle) on a COPY of the Halo 1 NEEDLER.
    # DEFAULT = REACH's OWN NUMBERS; the ratio values are the balance rows. STEP 6: the needler's
    # magazine names `powerups\needler ammo` (80) -- needler ammo tops the needle rifle up
    'pickable': {
        'weapon': NR + 'needle rifle',
        'template': N + 'needler',
        'world_model': NR + 'needle rifle',
        'fp_model': NR + 'fp\\fp',
        'fp_anims': NR + 'fp\\fp',
        'label': 'nr',
        'teach': ('nr', 'pr'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'nr_ready',
                   'first-person posing': SND + 'nr_pose',
                   'first-person melee': SND + 'nr_melee',
                   'first-person reload-empty': SND + 'nr_reload',
                   'first-person reload-full': SND + 'nr_reload'},
        # own needle + damage (step 3). Reach: needle_rifle_shard_impact 6 ON IMPACT (Halo 1's
        # needle does 0 on impact and its 10 when it bursts), 1500 wu/s straight (no guidance),
        # range 250, stuck up to 4 s ('detonation max time if attached', when at rest) with NO
        # damage at the end; materials = the needle's own (`detonation damage`: Reach's needle
        # group = Halo 1's needle materials, step 4a)
        'bullet': {'projectile': (N + 'needle', NR + 'needle'),
                   'damage': (N + 'detonation damage', NR + 'needle'),
                   'dmg': 6.0, 'acceleration': 0.2, 'velocity': 1500.0, 'range': 250.0,
                   # STEP 4b on the damage: list 2 camo damage 0.1 x 0.33/0.2; the forward
                   # EXPONENT degenerates (1 x 8/0.2 = 40) -> Reach's own 8 (the BR / DMR rule).
                   # List 3: category bullet (Reach's) kept; 'can cause headshots' has no
                   # Halo 1 jpt flag; instantaneous acceleration 0.2 (above)
                   'fields': {'damage.active_camouflage_damage': 0.165,
                              'breaking_effect.forward_exponent': 8.0},
                   'proj_fields': {'proj_attrs.physics.guided_angular_velocity': 0.0,
                                   # Reach's needle has no attached detonation damage
                                   'proj_attrs.physics.attached_detonation_damage.filepath': '',
                                   'proj_attrs.detonation.timer': (4.0, 4.0),
                                   'proj_attrs.flags.detonation_max_time_if_attached': True,
                                   # STEP 4b (before boot 1). List 2 (ratio vs Reach's needler
                                   # onto the H1 needle): air damage range 0, 100 x 40/60. List 3
                                   # (a zero on one side -> the source value): water gravity 0.2
                                   'proj_attrs.physics.air_damage_range': (0.0, 66.667),
                                   'proj_attrs.physics.water_gravity_scale': 0.2,
                                   'proj_attrs.physics.flyby_sound.filepath': SND + 'nr_flyby'},
                   # Reach's material responses (4b list 3): a needle sticks to BODIES only (the
                   # needle's own attach kept on 11-26 and Elite shields 30 -- the supercombine
                   # needs it); on terrain it ENDS ('disappear', the impact effect plays) or
                   # bounces off at 0-30 deg (the Spike Rifle's reflect). The needle's shield
                   # reflects (10 / 16 / 18 / 32) and water / leaves pass-through kept
                   'default_responses': {'disappear': TERRAIN},
                   'reflect': {'materials': TERRAIN, 'angle_deg': (0.0, 30.0),
                               'parallel_friction': 0.0, 'perpendicular_friction': 0.7,
                               'noise_deg': 2.0, 'effect_from_default': True},
                   # the stuck needle's end: the needle's burst, its sound Reach's own
                   'detonation_effect': {'from': N + 'effects\\needle detonate',
                                         'out': NR + 'effects\\needle detonate',
                                         'swaps': {'sound\\sfx\\weapons\\needler\\expl': SND + 'nr_burst'}},
                   # THE SUPERCOMBINE (step 4a): own copies of the needle's super-detonation
                   # effect and damage. Reach: attached 35 -> 350 + area 10 -> 40 (r 0.375-1.25)
                   # = ONE Halo 1 damage 45 -> 390 over Reach's radius; materials the needle
                   # explosion's (Elite shields x4, Flood x2). Its 'shock wave' shove kept
                   'super_explosion': {'effect': (N + 'effects\\explosion', NR + 'effects\\supercombine'),
                                       'damage': (N + 'explosion', NR + 'supercombine'),
                                       'lower': 45.0, 'upper': (390.0, 390.0), 'radius': (0.375, 1.25),
                                       'swaps': {'sound\\sfx\\impulse\\impacts\\needler_super_expl': SND + 'nr_super'}},
                   # BOOT 1 (user): 'the trail repeats the Brute Shot's mistake -- not following
                   # the needle, orthogonal to the surface, nothing visible in flight'. The
                   # needler's needle carries a LIGHT-VOLUME widget (weapons\needler\needle:
                   # turns with the surface on a stuck needle) -> dropped; its contrail
                   # (weapons\needler\needler) emits 30 points/s = one every 50 wu at 1500 wu/s
                   # -> the SNIPER bullet's trail (the Beam Rifle's: points at its speed), no
                   # point physics, ADDITIVE, Reach's needle-trail pink (contrail_system
                   # profile colour 237, 94, 237 -> 122, 43, 244)
                   'drop_widgets': True,
                   'attachments_from': 'weapons\\sniper rifle\\sniper bullet',
                   'contrail': {'from': 'weapons\\sniper rifle\\sniper', 'out': NR + 'needle trail',
                                'rgb': (237 / 255.0, 94 / 255.0, 237 / 255.0),
                                'no_physics': True, 'blend': 'add'},
                   # THE HIT-EFFECT RULE: max(default 4, balanced 3.33) = 4/s
                   'impact_thin': {'materials': [22], 'out': NR + 'effects\\impact\\',
                                   'thin': {}, 'rate': 4.0}},
        # semi-automatic (Reach: latch, 4/s, recovery 0.25 s); the needler's ramp 3 -> 10 off
        'trigger': {'rounds_per_second': (4.0, 4.0), 'does_not_repeat_automatically': True,
                    'acceleration_time': 0.0, 'deceleration_time': 0.0,
                    # Reach blooms by a firing-penalty function (decay 0.9 s); Halo 1's ramp
                    'error_acceleration_time': 1.0, 'error_deceleration_time': 0.9},
        # Reach's own spread; minimum error 0 (4b list 4: the needler's 2 deg is its spray --
        # the user: 'fire like a precision weapon')
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.15, 2.0)},
        # Reach: 21 loaded, 63 at pickup, 105 most
        'magazine': {'rounds_loaded_maximum': 21, 'rounds_reloaded': 21,
                     'rounds_total_initial': 63, 'rounds_total_maximum': 105,
                     'reload_time': 0.0},
        'aiming': {'autoaim_angle': 2.25, 'autoaim_range': 25.0,
                   'magnetism_angle': 5.0, 'magnetism_range': 25.0,
                   'zoom_levels': 1, 'zoom_ranges': (2.0, 2.0),
                   # 4b list 3: a zero on one side (the needler 0) -> Reach's own
                   'deviation_angle': 2.25},
        'sound_effects': {
            # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Reach's FIRST-PERSON flash
            # (fx\firing.effect, 'only in first person'): five particle systems ALL on the one
            # primary_trigger marker -- muzzle_flash_round (bounds 0.066 wu), a 0.025 one,
            # flash_large 0.071, muzzle_flash_plasma 0.074, plasma_blue_small 0.035; tints white
            # -> violet (72, 5, 255) / blue (16, 64, 217). The needler's (h1_effect_particles):
            # centre flashes 0.013-0.087 at the bore, a forward tracer 0.10-0.15 at +0.1, AND
            # two SIDEWAYS pairs (yaw +-75/90 deg, 0.05-0.087) at +-0.05 wu that Reach lacks ->
            # dropped (`drop_off_axis`, the SMG's recipe); size kept (Reach's span)
            'firing_effect': (N + 'effects\\fire needle', NR + 'effects\\fire needle',
                              {'sound\\sfx\\weapons\\needler\\fire': SND + 'nr_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012}),
            # the needler's EMPTY field is an EFFECT (the sniper's named a sound: the DMR's
            # field write failed the boot-1 build) -> an own copy, the dry fire swapped
            'empty_effect': (N + 'effects\\empty', NR + 'effects\\empty',
                             {'sound\\sfx\\weapons\\needler\\dryfire': SND + 'nr_dryfire'})},
        'fields': {
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'nr_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'nr_zoom_out',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'nr_ammo',
            'item_attrs.collision_sound.filepath': SND + 'nr_drop',
            # STEP 4b list 2 (ratio vs Reach's needler onto the H1 needler): camo ding 0.16 x
            # 0.75/0.2, illumination recovery 0.2 x 0.1/0.04
            'weap_attrs.interface.active_camo_ding': 0.6,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.5,
            # STEP 6: Reach has no per-weapon pickup count (its ammo box gives 0) -> the DMR's
            # rule (user, B1): the YARDSTICK's pickup : initial (needler 80 : 80) on Reach's 63
            'weap_attrs.magazines.0.magazine_items.0.rounds': 63,
        },
        'melee': (N + 'melee', NR + 'melee'),
        'melee_response': N + 'melee_response',
        'messages': ('Picked up a Needle Rifle', 'Picked up %d needles for Needle Rifle'),
        'icon': 'needle rifle',
        'extra_sounds': [SND + 'nr_reload_balanced'],
        # the NEEDLER's HUD (its needle readout) with the PISTOL's zoom screen effect (the
        # needler has none: the Beam Rifle's `screen_effect_from`) baked with Reach's scope
        # (ui\chud\needle_rifle: the carbine_scope ring at 1.4 x 1, black = a mask; its
        # nr_glyphs blips / markers and zoom_hatches are COLOURED (teal / green, alpha 0.1-0.5)
        # -- a Halo 1 mask can only darken: they bake DARK (preview h1_h3_scope --screen,
        # 2026-10-10: they read as the scope's own markings), kept for boot 1, the user judges)
        # and Reach's reticle (hud_reticles #4, four mirrored ticks at +-14: the Carbine's)
        'hud': {'donor': N + 'needler', 'out': NR + 'needle rifle',
                'screen_effect_from': PISTOL + 'pistol',
                'scope': {'chud': R + r'ui\chud\needle_rifle', 'out': NR + 'bitmaps\\scope_mask',
                          'size': 1024, 'span': 660.0 / 0.9, 'aspect': 4 / 3.0, 'alpha': 'outside'},
                # Reach's reticle = ONE arc sprite (hud_reticles #4, 11 x 27, a '(' arc) on four
                # widgets: left at -14, right mirrored at +14, top / bottom at -+14 (the arc
                # turned): composed by h1_add_reticle's per-layer xform -- a ring, unbroken in
                # the MCC simulation at min width 3 (out\reticle_needle_rifle_sim.png)
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 4, 'needle rifle'),
                'reticle_xform': {'offset': (-14.0, 0.0)},
                'reticle_layers': [(R + r'ui\chud\bitmaps\hud_reticles', 4, 1.0, {'flip_x': True, 'offset': (14.0, 0.0)}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 4, 1.0, {'rotate': -90, 'offset': (0.0, -14.0)}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 4, 1.0, {'rotate': 90, 'offset': (0.0, 14.0)})],
                'reticle_min_width': 3},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py needle_rifle). DEFAULT = Reach's
    # own numbers in the tags; BALANCED = the NEEDLER ratio rule (step 4a, user 2026-10-10).
    # Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Needle Rifle', 'source': 'Halo Reach', 'donor': 'Needler', 'default_on': False,
            'desc': "Halo Reach's Needle Rifle: its model, first-person animations, sounds, scope "
                    "and numbers. A 21-round semi-automatic needle rifle with a 2x zoom; seven "
                    "stuck needles supercombine. Needler ammo tops it up.",
            'balance_desc': "Measured against the Needler: 10 damage a needle at up to 3.3 "
                            "rounds a second, an 18-needle magazine with a slower reload, a "
                            "slower needle with a shorter reach, Halo 1-style aim assist and the "
                            "needler's own supercombine; the zoom stays Reach's.",
            # step 9: reload 70 fr x 82/44 = 130.5 over the built 82 = x1.59; swap: the H1
            # needler's ready x Reach needle rifle 19 / Reach needler 22 over the built 19
            'anims': {'reload': 1.59},
            'anim_sounds': {'reload': [
                {'mult': 1.59, 'from': SND + 'nr_reload', 'to': SND + 'nr_reload_balanced'}]},
            'balance': [
                row('jpt!', NR + 'needle', 'Damage Lower Bound', 10.0, 6.0, 'Needle Damage'),
                row('jpt!', NR + 'needle', 'Damage Upper Bound', 10.0, 6.0, 'Needle Damage'),
                row('jpt!', NR + 'needle', 'Damage Upper Bound Max', 10.0, 6.0, 'Needle Damage'),
                row('jpt!', NR + 'supercombine', 'Damage Lower Bound', 6.9, 45.0, 'Explosion Damage'),
                row('jpt!', NR + 'supercombine', 'Damage Upper Bound', 60.0, 390.0, 'Explosion Damage'),
                row('jpt!', NR + 'supercombine', 'Damage Upper Bound Max', 60.0, 390.0, 'Explosion Damage'),
                row('weap', NR + 'needle rifle', 'Rounds Per Second', 3.333, 4.0, 'More Shooting', block='Triggers'),
                row('weap', NR + 'needle rifle', 'Rounds Per Second Max', 3.333, 4.0, 'More Shooting', block='Triggers'),
                row('weap', NR + 'needle rifle', 'Rounds Loaded Maximum', 18, 21, 'Magazine', block='Magazines'),
                row('weap', NR + 'needle rifle', 'Rounds Reloaded', 18, 21, 'Magazine', block='Magazines'),
                row('weap', NR + 'needle rifle', 'Rounds Total Initial', 70, 63, 'Magazine', block='Magazines'),
                row('weap', NR + 'needle rifle', 'Rounds Total Maximum', 70, 105, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the needler's 80 : 80 on the balanced initial 70
                row('weap', NR + 'needle rifle', 'Rounds', 70, 63, 'Ammo pickup', block='Magazines/Magazines'),
                # spread: the needler's 4 -> 4 deg x (Reach 0.15 -> 2 / needler 0.1 -> 3): the
                # maximum 2.67, the minimum INVERTS (6) -> the SIBLING RULE in Reach's shape (the
                # DMR): 2.67 x 0.15/2 = 0.2; minimum error 0 both (precision)
                row('weap', NR + 'needle rifle', 'Error Angle', 0.2, 0.15, 'Error Angle', block='Triggers'),
                row('weap', NR + 'needle rifle', 'Error Angle Max', 2.67, 2.0, 'Error Angle', block='Triggers'),
                row('proj', NR + 'needle', 'Initial Velocity', 18.167, 50.0, 'Projectile'),
                row('proj', NR + 'needle', 'Final Velocity', 18.167, 50.0, 'Projectile'),
                row('proj', NR + 'needle', 'Maximum Range', 192.0, 250.0, 'Projectile'),
                row('proj', NR + 'needle', 'Timer', 2.25, 4.0, 'Needle Timer'),
                row('proj', NR + 'needle', 'Timer Max', 2.25, 4.0, 'Needle Timer'),
                row('weap', NR + 'needle rifle', 'Autoaim Angle', 1.69, 2.25, 'Autoaim'),
                row('weap', NR + 'needle rifle', 'Autoaim Range', 24.0, 25.0, 'Autoaim'),
                row('weap', NR + 'needle rifle', 'Magnetism Angle', 3.75, 5.0, 'Magnetism'),
                row('weap', NR + 'needle rifle', 'Magnetism Range', 24.0, 25.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port needle_rifle): the source pair (Reach needle rifle vs
    # the yardstick, Reach's needler) against the target pair (the H1 port vs its template, the
    # H1 needler)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\needle_rifle.weapon', r'objects\weapons\pistol\needler\needler.weapon'),
                   'projectile': (RW + r'\projectiles\needle_rifle_shard.projectile',
                                  r'objects\weapons\pistol\needler\projectiles\needler_shard.projectile'),
                   'damage_effect': (RW + r'\projectiles\damage_effects\needle_rifle_shard_impact.damage_effect',
                                     r'objects\weapons\pistol\needler\projectiles\damage_effects\needler_shard_impact.damage_effect')},
        'target': {'weapon': (NR + 'needle rifle.weapon', N + 'needler.weapon'),
                   'projectile': (NR + 'needle.projectile', N + 'needle.projectile'),
                   'damage_effect': (NR + 'needle.damage_effect', N + 'detonation damage.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), Reach's own loadout
    'test': {'level': 'a30', 'rounds': (21, 63), 'grunt': None, 'elite': None},
})

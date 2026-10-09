r"""Mauler (Halo 3 -> Halo 1, wave A6) on a copy of the Halo 1 SHOTGUN, which is also the
yardstick (step 4a, user 2026-10-08). brute_spiker.py is the shape it copies (a dual-wieldable
one-hander with a blade); what is new here: a ONE-HANDED PELLET weapon (15 pellets, distance
falloff), a WHOLE-MAGAZINE reload on a shell-by-shell template, and the pistol's third-person
pose (label `ml` taught from `hp`: Halo 1's `sg` is two-handed)."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\pistol\excavator'
ML = 'weapons\\mauler\\'
SND = 'sound\\weapons\\mauler_port\\'
SG = 'weapons\\shotgun\\'
# Halo 3's self-illum colour of the body and metal shaders (BGRA 1e 3c bf in the function data
# = RGB 191 / 60 / 30, an orange-red; intensity a curve 8 -> 4). The shiny shader names the
# illum map with no colour of its own (intensity 1)
ORANGE = (191 / 255.0, 60 / 255.0, 30 / 255.0)
# TEST 1: Halo 3's 191/60/30 at intensity 8 clips toward white (the drum windows read white-hot
# with orange rims): the base self-illum in that saturated colour, the glow cards in a brighter
# orange than the raw one
HOT = (1.0, 0.78, 0.55)
ORANGE_GLOW = (1.0, 0.45, 0.18)
ILLUM = H3 + r'\bitmaps\excavator_illum.bitmap'
BASE = H3 + r'\bitmaps\excavator.bitmap'

PORT = reserved(
    order=15, wave='A6', name='Mauler', source='Halo 3',
    messages=(63, 64), icon=35, reticle=24, label='ml', teach_from='hp',
    sound_dir='sound\\weapons\\mauler_port', weapon_dir='weapons\\mauler',
    yardstick={
        # step 4a (user, 2026-10-08): h3_weapon_values.py (excavator / shotgun / magnum /
        # energy_blade) + the projectiles' `conical spread` block + h1_role_compare.py
        # brute_mauler. Halo 3's mauler is the shotgun's own projectile with other numbers:
        # 15 pellets (3 x 5 grid, 7.5 deg) both, bullet_slow both, falloff both -- every value
        # has a shotgun counterpart; the pistol has no pellets, no cone and no falloff
        'pick': 'Shotgun',
        'reason': "user, step 4a 2026-10-08: the same projectile family in Halo 3 (15-pellet "
                  "7.5 deg cone, bullet_slow, distance falloff) -- H1 value = H1 shotgun x H3 "
                  "mauler / H3 shotgun; keeps Halo 3's relation (140 vs 150 dps -> 301 vs 322). "
                  "The reload stays WHOLE-MAGAZINE (the ratio of a full reload lands on 55 fr)",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: mauler / shotgun. H1 shotgun: 15 x 18..25 (lower 8 over 1.5 -> 3 wu), 1/s,
        # 12 (24 / 60) 0.4 s a shell, error 10, 140 -> 100 wu/s, range 40, aim 6/15 12/15,
        # melee 55. Default (H3 own): 15 x 7 (lower 1.5 over 2.5 -> 5), 0.75 s, 5 (10 / 25),
        # 55 fr, 7.5 deg, 480 wu/s, range 8, aim 8/7 16/7, cut_melee 72
        'balanced': {
            'pellets': 15,                 # 15 x 15/15
            'damage': (12.6, 17.5),        # 18..25 x 7/10 (mean 15.05)
            'damage_lower': 4.0,           # 8 x 1.5/3
            'damage_range': (1.875, 3.75),  # 1.5 x 2.5/2, 3 x 5/4
            'fire_recovery_s': 0.75,       # 1.0 s x 0.75/1.0 (rounds_per_second 1.333)
            'magazine': 10,                # 12 x 5/6
            'rounds_total_initial': 13,    # 24 x 10/18
            # DUAL-WIELD CARRY RULE: 60 x (25/36) x 1.5 = 62.5
            'rounds_total_maximum': 62,
            # WHOLE magazine: H1 shotgun empty -> full (12 shells x 12 fr = 144) x H3 mauler
            # 55 fr / H3 shotgun empty -> full (14 + 6 x 16 + 34 = 144) = 55 fr
            'reload_s': 55 / 30.0,
            'error_deg': 10.0,             # 10 x 7.5/7.5 (Halo 1: a random cone, no grid)
            'velocity': (140.0, 100.0),    # x 480/480
            'range': 53.3,                 # 40 x 8/6
            'aim': (6.0, 19.1, 12.0, 19.1),  # 6 x 8/8, 15 x 7/5.5; 12 x 16/16, 15 x 7/5.5
            'melee': 56.6},                # 55 x cut_melee 72 / strike_melee 70
        'measured': 'h1_role_compare.py brute_mauler',
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\excavator\\excavator',
            'provisional': 'Shotgun',
            'alternatives': ['Pistol'],
            'direct': None,
            'peers': ['Shotgun', 'Energy Blade', 'Flamethrower'],
            'why': '5-round magazine, instant pellets, 8 wu range: a one-hand shotgun',
            'lacks': 'dual wield'}},
    # step 11: the source game's ai\generic entry (14 fields, verified 2026-10-07) laid over a
    # Halo 1 SHOTGUN carrier ('ml' has no carrier). Halo 1's shotgun carriers (2026-10-09):
    # Flood combat Elite / human (WDM 0.15), Marine plain / anchor and armoured Marine major
    # (0.6) -- no Covenant one. The two bases differ x4, so ONE donor is pinned for every slot
    # (the Beam Rifle's donor_variant; user 2026-10-09): the Flood combat Elite, a combatant
    # and the carrier an Elite slot would clone anyway. ARMED WDM RULE: base 0.15 x shotgun
    # 322 / mauler dps -- default 105 x 1.33 = 140 (0.35), balanced 15.05 x 15 x 1.33 = 301
    # (0.16)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\pistol\\excavator\\excavator',
                    'donor_weapon': 'weapons\\shotgun\\shotgun',
                    'donor_variant': 'characters\\floodcombat elite\\floodcombat elite shotgun',
                    'wdm_rule': {'base': 0.15, 'yardstick_dps': 322.0, 'port_dps': 140.0,
                                 'balanced_port_dps': 301.0}},
)

PORT.update({
    # 2026-10-09: tested on a30 over 7 boots (dry default, fixes x2, balanced x3 incl. glow,
    # Armed) -- confirmed by the user; the ten-map rebuild is BATCHED with the SMG, BR,
    # Carbine, Beam Rifle and Spike Rifle (user's go)
    'status': 'done',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's four materials all sample the same
    # `excavator` base map (+ bump): the body `excavator` (detail metal_dirty, self-illum
    # excavator_illum in ORANGE at 8 -> 4), `excavator_dull` (rubber detail, no illum: the
    # grip), `excavator_metal` (as the body, illum ORANGE) and `excavator_shiny` (chrome
    # reflections: the blade; the illum map with no colour, intensity 1). Template: the
    # shotgun's gun shader
    'model': {
        'dir': r'weapons\mauler',
        'world': H3 + r'\excavator.render_model',
        'fp': H3 + r'\fp_excavator\fp_excavator.render_model',
        'world_name': 'mauler',
        'shaders': {'excavator': (BASE, ILLUM),
                    'excavator_dull': (BASE, None),
                    'excavator_metal': (BASE, ILLUM),
                    'excavator_shiny': (BASE, ILLUM)},
        # TEST 1 (user, screenshots H3 vs H1): 'glow needs work' -- Halo 3's drum windows read
        # WHITE-HOT with orange edges (191/60/30 x intensity 8, + bloom), ours a dim orange.
        # fp_material_view --illum --texels: the lit texels are the drum's round windows
        # (excavator_metal, ~100 texels each) and a few body spots (excavator). Halo 1 shows
        # colour x mask, no bloom -> the base colour itself saturated (HOT), lit texels grown
        # 1 px, and a radial additive glow card per lit window (the Spike Rifle's spot recipe)
        # with a white core fading to ORANGE: the bloom
        'illum_dilate': 1,
        'glow': {'excavator': HOT, 'excavator_metal': HOT, 'excavator_shiny': HOT},
        # TEST 2 (user): 'much better -- but in H3 they have DISTINCT SHAPES; ours look like
        # lights drawn onto the weapon' (the radial spot cards: round blobs over the faces).
        # Now the window SHAPES: each lit triangle copied in place (scale 1.0, lifted 0.02,
        # the same UVs) as an additive glow whose texture IS Halo 3's illum mask (grown 1 px;
        # brightness -> ORANGE_GLOW up to half, then towards white: a hot core on the mask's
        # bright texels) -- the light sits exactly where and in the shape Halo 3 draws it.
        # Barrel ENDS left out (faces exactly along the gun, dot 1.0; Halo 3 shows no light
        # there -- the render check of test 2); the drum windows face back / forward TILTED
        # (dot 0.84..0.99) and stay
        'glow_shaders': {'mauler_window': {'rgb': ORANGE_GLOW, 'additive': True, 'mask': ILLUM,
                                           'mask_channel': 'rgb', 'dilate': 1, 'gain': 1.0},
                         # the body's thin SLITS (test 5, below): the same mask, grown 3 px,
                         # x2 gain -- a line reads only when thick and saturated
                         'mauler_slit': {'rgb': ORANGE_GLOW, 'additive': True, 'mask': ILLUM,
                                         'mask_channel': 'rgb', 'dilate': 3, 'gain': 2.0}},
        'glow_cards': {'excavator_metal': {'shader': 'mauler_window', 'lit': ILLUM,
                                           'scale': 1.0, 'lift': 0.02,
                                           'skip_normals': ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
                                           'skip_dot': 0.995},
                       'body': {'of': 'excavator', 'shader': 'mauler_slit', 'lit': ILLUM,
                                'scale': 1.0, 'lift': 0.02}},
        # TEST 3 (user, ground + FP screenshots): 'the ground model has a lit shape that should
        # be visible in the FP view'. Test 3's guess (cards on the rear-top lights, excavator_
        # metal FP -2.5 +-1 6.4) was WRONG -- test 4: 'that part was already lit'. TEST 4 (user
        # circled it on Halo 3's FP view and ours): a thin vertical SLIT on the left side of the
        # upper body under the barrel = the body material's lit texels at FP (4.3, +1.1, 7.2)
        # (its mirror at -1.1 on the right), faces pointing straight sideways (+-y): edge-on to
        # the FP camera, a few texels -- Halo 3 shows it by bloom. The Spike Rifle's side-light
        # recipe (test 4/6, approved there): a small radial card per slit FACING BACK (-x) at
        # the camera, only that card (the face keeps its shaped one); `highest` 2 keeps the
        # pair under the barrel (the lower pair by the grip, z 3.4, gets none)
        # TEST 5 (user): 'right position, but not fitting the slit layout' -- the square
        # camera-facing card read as a blob. Measured (lit texels > 64): each slit is a LINE
        # ALONG THE GUN, x 3.55..4.33 at z ~7.1 (0.2 tall) on a sideways face; from the FP
        # camera it projects as Halo 3's short near-vertical streak. A fin card along it
        # (glow_spots `strip`) rendered nearly edge-on, while the slit's OWN face shows at an
        # angle (the lit-texel render: a vertical streak where the user circled) -- so the
        # face carries it: its shaped glow card (`slit` above, Halo 3's mask) grown 3 px and
        # x2 gain, the Spike Rifle's side-line finding (thin lines need thickness + a
        # saturated colour without bloom). No spot cards
        'template': SG + r'shaders\shotgun gun',
    },

    # FP animations (h1_fp_retarget.py). Halo 3 mauler (single-wield) frames: ready 20,
    # put_away 5, fire_1 19, melee_strike_1 29, reload empty / full 55. DUAL-WIELDABLE: the
    # graph holds a second (dual) resource group -- the (group, member) keying (Pilot A1)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\pistol\fp_excavator\fp_excavator.model_animation_graph',
        'render_model': H3 + r'\fp_excavator\fp_excavator.render_model',
        'nodes': {n: 'frame ' + n for n in ('gun', 'drum', 'barrel', 'piston')},
        'h1_dir': r'weapons\mauler\fp',
        'h1_model': r'weapons\mauler\fp\fp',
        'align': 'same_space',
        # the SMG's placement (user's pick, A1), tuned in test 1
        # test 1 (user): 'lower the FP position by 2 units' (1 unit = 0.01 wu)
        'view_offset': (-0.0225, 0.0, -0.0225 - 0.02),
        # --list (2026-10-08): single-wield idle var1-3 (99/124/74), posing var1 124, fire_1
        # var1-3 19, melee_strike_1 29 (primary_keyframe 5), reload_empty / full 55 (no
        # variants; primary_keyframe 40), throw_grenade 41 -- the frame counts match the
        # graph's own (h3_weapon_values). The dual group (reload 99) is not used
        'anims': {
            'first_person:idle:var1': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py brute_mauler). Levels = the stock Halo 1 sound
    # each stands in for (h1_stock_sound_levels.py, MCC sounds_adpcm.fsb 2026-10-08): shotgun
    # fire -16.7 (the shotgun's firing effect plays it TWICE, two events at 0 s: the copy
    # keeps both, so the Mauler matches the shotgun's loudness), shotgun_ready -15.3,
    # shotgun_melee -13.5, shotgun_posing -23.0, drop (shotgun_impact) -20.7, shotgun_ammo
    # -28.9, pistol dryfire -15.3 (the shotgun's own empty effect), pistol_reload -19.0 (a
    # WHOLE-magazine reload sound; the shotgun's are per shell, -19.9..-24.0). Halo 3's
    # mauler reuses the MAGNUM's ammo / dry fire / drop sounds (its weapon tag and the magnum
    # material effects): its own copies here, as Halo 3 does. Single-wield FP cues: ready,
    # melee, pose, reload (both reloads)
    'sounds': {
        'catalog': 'Mauler',
        'dir': B.join(['sound', 'weapons', 'mauler_port']),
        'h3_dir': 'data\\sound\\weapons\\excavator\\',
        'sounds': {
            'ml_fire': (['excavator_fire'], 'sound\\sfx\\weapons\\shotgun\\fire', -16.7),
            'ml_reload': (['excavator_fp\\excavator_reload'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'ml_ready': (['excavator_fp\\excavator_ready'], 'sound\\sfx\\weapons\\weapon_anims\\shotgun_ready', -15.3),
            'ml_melee': (['excavator_fp\\excavator_melee'], 'sound\\sfx\\weapons\\weapon_anims\\shotgun_melee', -13.5),
            'ml_pose': (['excavator_fp\\excavator_pose'], 'sound\\sfx\\weapons\\weapon_anims\\shotgun_posing', -23.0),
            'ml_drop': (['data\\sound\\weapons\\magnum\\magnum_drop'], 'sound\\sfx\\impulse\\weapon_drops\\shotgun_impact', -20.7),
            'ml_ammo': (['data\\sound\\weapons\\magnum\\magnum_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\shotgun_ammo', -28.9),
            # the shotgun's EMPTY field names the AR dry fire SOUND itself (its `shotgun empty`
            # effect sits on the misfire field): the level of what plays, AR dryfire -17.6
            'ml_dryfire': (['data\\sound\\weapons\\magnum\\magnum_dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only brute_mauler) on a COPY of the Halo 1 Shotgun.
    # DEFAULT = HALO 3's OWN NUMBERS (PORTING "Balance"); the ratio values are the balance rows
    # (yardstick['balanced']). The shotgun's 15 pellets (projectiles per shot) are Halo 3's
    # 15 too (the conical spread block, 3 x 5); its trigger flag 'projectile is client side
    # only' is kept (a pellet weapon's)
    'pickable': {
        'weapon': ML + 'mauler',
        'template': SG + 'shotgun',
        'world_model': ML + 'mauler',
        'fp_model': ML + 'fp\\fp',
        'fp_anims': ML + 'fp\\fp',
        'label': 'ml',
        # one-handed: Halo 1's PISTOL pose (`hp`), not the shotgun's two-handed `sg`
        'teach': ('ml', 'hp'),
        'keys': {'first-person melee': 5},          # H3 melee_strike_1 primary_keyframe 5
        'sounds': {'first-person ready': SND + 'ml_ready',
                   'first-person posing': SND + 'ml_pose',
                   'first-person melee': SND + 'ml_melee',
                   'first-person reload-empty': SND + 'ml_reload',
                   'first-person reload-full': SND + 'ml_reload'},
        # own pellet + damage (step 3): Halo 3 excavator_shard 7 a pellet, falling to 1.5 over
        # 2.5 -> 5 wu ('damage scales based on distance' + air damage range; Halo 1 has the
        # same fields: the shotgun pellet 18..25 -> 8 over 1.5 -> 3), 480 wu/s instantaneous
        # (Halo 1 has no instant flag: 480 wu/s crosses the 8 wu range in 1/60 s), range 8.
        # Materials: the H1 shotgun pellet's (both bullet_slow in Halo 3)
        # THE HIT-EFFECT RULE with pellets (user, 2026-10-08): count SHOTS, not pellets --
        # 1.33 shots/s is under the rule's 3.5/s, so the pellet's shield-hit effect stays the
        # shotgun's (x1, no `impact_thin`); pellets x rate (20/s) would have been x0.004
        'bullet': {'projectile': (SG + 'pellet', ML + 'pellet'),
                   'damage': (SG + 'pellet', ML + 'pellet'),
                   'dmg': 7.0, 'velocity': 480.0, 'range': 8.0,
                   'fields': {'damage.damage_lower_bound': 1.5},
                   'proj_fields': {'proj_attrs.physics.air_damage_range': (2.5, 5.0)}},
        # H3: fire recovery 0.75 s (rounds per second 0 = recovery-limited) = 1.333/s
        'trigger': {'rounds_per_second': (4 / 3.0, 4 / 3.0),
                    # 4b list 2: ejection port recovery H3 0 (mauler, no casing) vs 1
                    # (shotgun) -> 0 (the H1 shotgun 0.15: its pump's shell eject)
                    'ejection_port_recovery_time': 0.0},
        # H3: a fixed 7.5 deg GRID (yaw 3 x pitch 5); Halo 1: a random cone (the shotgun's
        # 'point' distribution, error angle 10 / 10) -> 7.5 / 7.5
        'error_deg': {'minimum_error': 0.0, 'error_angle': (7.5, 7.5)},
        # H3: 5 loaded, 10 at pickup, 25 most, all 5 reloaded at once (55 fr; reload time 0
        # = the animation's). Halo 1's shotgun reloads ONE shell per 0.4 s cycle: rounds
        # reloaded 5 + one 1.8 s cycle = Halo 3's whole-magazine reload
        'magazine': {'rounds_loaded_maximum': 5, 'rounds_reloaded': 5,
                     'rounds_total_initial': 10, 'rounds_total_maximum': 25,
                     'reload_time': 1.8},
        # H3 aim assist, absolute (balanced = the ratio rule)
        'aiming': {'autoaim_angle': 8.0, 'autoaim_range': 7.0,
                   'magnetism_angle': 16.0, 'magnetism_range': 7.0},
        # STEP 6 (user, 2026-10-08): Halo 3's mauler has NO ammo item; the template's magazine
        # names `powerups\shotgun ammo` (60 rounds a box) -- KEPT: a box refills the Mauler
        # (capped at 25 / 62 balanced)
        'fields': {
            # STEP 4b list 2 (ratio vs the H3 shotgun onto the H1 shotgun; before boot 1):
            # bounding radius 0.2 x 0.2/0.225; acceleration scale 2 x 1.25/1.0
            'obje_attrs.bounding_radius': 0.2 * 0.2 / 0.225,
            'obje_attrs.acceleration_scale': 2.5,
            # list 3, by NAME: Halo 3's shotgun has the magazine flag 'every round must be
            # chambered' (2) and weapon type 'shotgun' -- the MAULER has neither (0,
            # 'undefined'): both follow the source (the whole-magazine reload, not a
            # shotgun's shell loop)
            'weap_attrs.magazines.0.flags.every_round_must_be_chambered': False,
            'weap_attrs.weapon_type': 'undefined',
            # port_sound_refs (before boot 1): the shotgun's trigger names the AR dry fire
            # SOUND as its empty effect and `shotgun empty` (the pistol dry fire) as its
            # MISFIRE effect (a magazine weapon never misfires; Halo 3's mauler has none):
            # empty = the mauler's own dry fire, misfire cleared
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'ml_dryfire',
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'ml_ammo',
            'item_attrs.collision_sound.filepath': SND + 'ml_drop'},
        'sound_effects': {
            # Halo 3's mauler flash: muzzle_flash_long + round, flash_large, glow_soft, fiery
            # sparks, muzzle smoke, a light -- no casing (the shotgun's casing event dropped)
            'firing_effect': (SG + 'effects\\shotgun firing', ML + 'effects\\fire pellets',
                              {r'sound\sfx\weapons\shotgun\fire': SND + 'ml_fire'},
                              {'drop_particles': ('casing',)})},
        # the BLADE (Halo 3 cut_melee 72; the shotgun's strike_melee 70): DEFAULT = Halo 3's 72
        # as the copy's mean (the shotgun's 50..60 spread kept: 65.5..78.5); balanced 56.6
        'melee': (SG + 'melee', ML + 'melee'),
        'melee_dmg': 72.0,
        'melee_response': SG + 'melee_response',
        'messages': ('Picked up a mauler', 'Picked up %d rounds for mauler'),
        'icon': 'mauler',
        # the shotgun's HUD with Halo 3's mauler reticle (H3 hud_reticles #12) at the reserved
        # 24, a magazine meter drawn for 5 (default) and 10 (balanced); low-ammo flash 2 of 12
        'hud': {'donor': SG + 'shotgun', 'out': ML + 'mauler',
                'reticle': ('hud_reticles', 12, 'mauler'),
                'reticle_thicken': 1,
                # TEST 1 (user): 'the ammo meter needs to be replaced by the original pips' --
                # Halo 3's own round icon (chud excavator: ballistic_meters #13, five pips)
                # one a round in a row, at Halo 3's spacing (ammo_meter `art`)
                'ammo_meter': {'sizes': (5, 10), 'base': ML + 'bitmaps\\mauler_ammo',
                               'art': {'h3': ('ballistic_meters', 13)}},
                'flash_base': 12},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py brute_mauler). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the SHOTGUN ratio rule (step 4a, user
    # 2026-10-08). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Mauler', 'source': 'Halo 3', 'donor': 'Shotgun', 'default_on': False,
            'desc': "Halo 3's Mauler: its model, first-person animations, sounds and numbers. "
                    "A one-handed 5-round Brute shotgun firing 15 pellets that lose most of "
                    "their damage past a few metres, with a blade for melee.",
            'balance_desc': "Measured against the Shotgun, which both games have: 15 pellets of "
                            "12.6-17.5 damage (4 at range, over 1.9-3.8 m), a 10-round "
                            "magazine, 13 at pickup / 62 most, a wider cone, Halo 1-style "
                            "pellet speed and range, and Halo 1-style aim assist.",
            # step 9: the balanced reload = H1 shotgun empty -> full (144 fr) x 55 / 144 (H3)
            # = 55 fr, the built length (x1.0); swap = H1 shotgun ready 23 fr x 20/23 = 20 fr,
            # the built 20 (x1.0): no retime
            'balance': [
                row('jpt!', ML + 'pellet', 'Damage Lower Bound', 4.0, 1.5, 'Pellet Damage'),
                row('jpt!', ML + 'pellet', 'Damage Upper Bound', 12.6, 7.0, 'Pellet Damage'),
                row('jpt!', ML + 'pellet', 'Damage Upper Bound Max', 17.5, 7.0, 'Pellet Damage'),
                row('proj', ML + 'pellet', 'Air Damage Range', 1.875, 2.5, 'Pellet Damage'),
                row('proj', ML + 'pellet', 'Air Damage Range Max', 3.75, 5.0, 'Pellet Damage'),
                row('proj', ML + 'pellet', 'Initial Velocity', 140.0 / 30, 480.0 / 30, 'Projectile'),
                row('proj', ML + 'pellet', 'Final Velocity', 100.0 / 30, 480.0 / 30, 'Projectile'),
                row('proj', ML + 'pellet', 'Maximum Range', 53.3, 8.0, 'Projectile'),
                row('weap', ML + 'mauler', 'Rounds Loaded Maximum', 10.0, 5.0, 'Magazine', block='Magazines'),
                row('weap', ML + 'mauler', 'Rounds Reloaded', 10.0, 5.0, 'Magazine', block='Magazines'),
                row('weap', ML + 'mauler', 'Rounds Total Initial', 13.0, 10.0, 'Magazine', block='Magazines'),
                # the DUAL-WIELD CARRY RULE: 60 x 25/36 x 1.5 = 62.5
                row('weap', ML + 'mauler', 'Rounds Total Maximum', 62.0, 25.0, 'Magazine', block='Magazines'),
                row('weap', ML + 'mauler', 'Error Angle', 10.0, 7.5, 'Error Angle', block='Triggers'),
                row('weap', ML + 'mauler', 'Error Angle Max', 10.0, 7.5, 'Error Angle', block='Triggers'),
                row('weap', ML + 'mauler', 'Autoaim Angle', 6.0, 8.0, 'Autoaim'),
                row('weap', ML + 'mauler', 'Autoaim Range', 19.1, 7.0, 'Autoaim'),
                row('weap', ML + 'mauler', 'Magnetism Angle', 12.0, 16.0, 'Magnetism'),
                row('weap', ML + 'mauler', 'Magnetism Range', 19.1, 7.0, 'Magnetism'),
                # the blade: 55 x 72/70 = 56.6 as the copy's mean (the shotgun's 40 / 50..60
                # spread x 56.6/55); default Halo 3's 72 (x 72/55)
                row('jpt!', ML + 'melee', 'Damage Lower Bound', 41.16, 52.36, 'Melee Damage'),
                row('jpt!', ML + 'melee', 'Damage Upper Bound', 51.45, 65.45, 'Melee Damage'),
                row('jpt!', ML + 'melee', 'Damage Upper Bound Max', 61.75, 78.55, 'Melee Damage'),
                # the 10 magazine's meter: mauler_ammo sequence 1 (ammo_meter 5 10), step 25
                # (default 50: ammo_meter's top threshold stays below 255); flash at 2 x 10/12 = 2 (default 1)
                dict(row('wphi', ML + 'mauler', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', ML + 'mauler', 'Alpha Multiplier', 25, 50, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', ML + 'mauler', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', ML + 'mauler', 'Loaded Ammo Cutoff', 2, 1, 'Ammo display'), index=0),
            ]},
    },

    # CLOSE-OUT RECORD (2026-10-09). 4b + template diff + port_sound_refs ran BEFORE boot 1.
    # Weapon: list 2 = only the reload time, 1.8 s on purpose (Halo 3's 0 = the animation's
    #   length; Halo 1 needs a number). Written by list 2: bounding radius 0.178, acceleration
    #   scale 2.5, ejection port recovery 0. List 3 by NAME: magazine 'every round must be
    #   chambered' cleared + weapon type 'undefined' (Halo 3's mauler has neither; its shotgun
    #   both); 'can be dual wielded' / 'old dual fire error code' (dual wield not reproduced:
    #   the carry rule x1.5); attachments (Halo 3 2: firing light kept as the shotgun's AR
    #   muzzle light); fp offset override, font icons, ground scales, power on/off, aim
    #   falloff, look-pitch error, dual-wield damage scale, damage reporting type: no Halo 1
    #   field. Fire recovery 0.75 s = rounds per second 1.333.
    # Projectile: list 2 = 0 (range 8 and air damage range 2.5..5 default; balanced rows).
    #   Halo 3's attachment `fx\projectile` is an EMPTY effect (nothing to port); pellets: the
    #   shotgun's 15 (Halo 3's conical grid 3 x 5 = 15), cone 7.5 random (Halo 1 has no grid).
    # Damage effect: list 2 = 0 (lower 1.5, upper 7; balanced 4 / 12.6..17.5); materials the
    #   shotgun pellet's (both bullet_slow). Shield-hit effect x1: THE HIT-EFFECT RULE counts
    #   SHOTS, not pellets (user) -- 1.33/s.
    # Full field diff (h1_port_template_diff.py): every difference = a decision above, a
    #   reference to the port's own tags, the dropped casing, the HUD pips / reticle / icon.
    # Steps 6-10: 6 the shotgun's ammo item (60 a box) KEPT (user; Halo 3 has none); 7 the
    #   shotgun's HUD, Halo 3's own pips (ballistic_meters #13, ammo_meter `art`, top-aligned;
    #   5 / 10, step 50 -- the top threshold below 255), reticle 24 (H3 #12); 8 icon 35 +
    #   messages 63/64; 9 reload and swap x1.0 (the ratio lands on Halo 3's own 55 / 20 fr);
    #   10 own sounds: fire (two events, the shotgun's layering), reload, ready, melee, pose,
    #   drop / ammo / dry fire (Halo 3's own reuse of the magnum's).
    # Look: base self-illum HOT (+1 px); the drum windows in Halo 3's own shapes (lit
    #   triangles copied, additive, the illum mask as texture); the body slits (mask +3 px,
    #   x2) -- OPEN, minor (user 2026-10-09: 'still doesn't render, a very minor detail'):
    #   tried a camera-facing radial card (a blob), a fin strip (edge-on), the bolder face.
    # Tag writes PROVEN (closing check 6): 39 tags (every weapons\mauler tag, messages, cyborg
    #   animations, the ten scenarios) flattened, the writer re-run, 0 of 693,643 changed.
    # Closing checks: port_refs_audit 0 (kit a30), port_sound_refs all OWN, port_sounds
    #   --check 0, validate_halo_json 0; 5b: default = Halo 3's row (140 dps), balanced = the
    #   Shotgun-ratio row (301 dps; h1_role_compare now keeps a damage range's two bounds).
    #   Check 8: the Armed pass armed Grunt / Jackal / Elite slots, all from the pinned Flood
    #   combat Elite shotgun + Halo 3's excavator profile; one-handed (enhancer default 'one':
    #   Grunts full rate, Jackals keep the shield -- confirmed in game).
    # Not reproduced: dual wield, the fixed pellet grid, the slit glow (open).
    # step 4b (port_field_audit.py --port brute_mauler): the source pair (H3 mauler vs the
    # yardstick, H3 shotgun) against the target pair (the H1 port vs its template = the H1
    # shotgun)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\excavator.weapon', r'objects\weapons\rifle\shotgun\shotgun.weapon'),
                   'projectile': (H3 + r'\projectiles\excavator_shard.projectile',
                                  r'objects\weapons\rifle\shotgun\projectiles\shotgun_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\excavator_shard.damage_effect',
                                     r'objects\weapons\rifle\shotgun\damage_effects\shotgun_bullet.damage_effect')},
        'target': {'weapon': (ML + 'mauler.weapon', SG + 'shotgun.weapon'),
                   'projectile': (ML + 'pellet.projectile', SG + 'pellet.projectile'),
                   'damage_effect': (ML + 'pellet.damage_effect', SG + 'pellet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), the mauler as the primary
    # with Halo 3's own loadout (5 loaded, 10 in all)
    'test': {'level': 'a30', 'rounds': (5, 10), 'grunt': None, 'elite': None},
})

r"""Suppressor (Halo 4, wave C2) on a copy of the Halo 1 ASSAULT RIFLE, which is also the yardstick
(step 4a, user 2026-10-14). The Halo 4 route of storm_rifle.py (h4: paths, Foundry FP decode, the arms
re-solved, Wwise sounds, a CUI crosshair) on the MAGAZINE shape of smg.py / brute_spiker.py (a slow
visible projectile on every round: the Spike Rifle's AR-template recipe).

HALO 4 (h3_weapon_values --kit h4, 2026-10-14): a hardlight shard 6.25 (plasma_fast) x 15/s, magazine 48
(192 / 336), reload 59 / 68 fr (full / empty), error 0.5 -> 3 deg, aim (MODE block) 7.5/15 10/20. The
shard flies 60 -> 15 wu/s over its first 2.5 wu (acceleration range 0..2.5), then 15 wu/s to its 100 wu
range; Halo 1 slows a projectile linearly over its WHOLE range with the final velocity a floor (B4's
probe) -> 15 -> 15 (user, 4a: within ~0.1 s of Halo 4 at every distance). Its damage effect has NO
falloff ('damage scales based on distance' unset: the 0..60 air damage range is inert) -> a flat 6.25.

THE DIFFUSE (user: 'get the real texture'): H4EK's _default_metal.material names a colour map
(storm_forerunner_smg_default_diff) that is shipped NOWHERE -- not in H4EK, not in MCC's maps. The
SHIPPED default material (m020.map: bitmaps normal / SHATTER control / cube / detail spec, specular
100, mix 0.9, reflection gamma 0.42, fresnel power 0.5936) is H4EK's _shatter_metal.material: the
srf_char_forerunner_andrew shader draws its diffuse from the control map's df channel (spdfgl: G) x
albedo tint 0.494, no colour map -> h4_standin_diffuse.py (channel mode): grey = 0.494 x G, the
specular channel (R) as the base map's alpha (Halo 1's reflection mask). Dark gunmetal (mean 0.12),
as the user's Halo 4 screenshot shows it."""
from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_forerunner_smg'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_forerunner_smg\storm_fp_forerunner_smg'
SBM = SW + r'\bitmaps\storm_forerunner_smg_default' + B
SUR = r'ui\hud\weapons\forerunner\forerunner_smg\bitmap' + B    # Halo 4's crosshair art (CUI)
SU = 'weapons\\suppressor\\'
SND = 'sound\\weapons\\suppressor_port\\'
AR = 'weapons\\assault rifle\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# the diffuse (h4_standin_diffuse.py <shatter control> <this>, in the port's own data folder)
STANDIN = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\suppressor\source\su_metal_diffuse.png'
SHATTER_CONTROL = SW + r'\bitmaps\storm_forerunner_smg_shatter\storm_forerunner_smg_shatter_control.bitmap'
# Forerunner hardlight yellow-orange, from the user's Halo 4 screenshot (2026-10-14): the glow strips'
# unclipped edges RGB 214 / 161 / 29 (the cores clip to 244 / 228 / 32) -> the shard's streak, the
# gun's glow strips and the muzzle tint
ORANGE = (1.0, 0.75, 0.13)

# the Halo 4 FP skeleton's arm nodes Halo 1's 37-node arms lack -- the Storm Rifle's DROP list (C1);
# this graph's 93 nodes = the same 80 arm / camera nodes + 13 gun bones (checked 2026-10-14)
DROP = (['pedestal', 'aim_pitch', 'aim_yaw'] +
        ['%s_%s' % (s, n) for s in 'lr' for n in
         ('shoulder_helper1', 'shoulder_helper2', 'shoulder_helper3', 'shoulder_helper4',
          'shoulder_fixup', 'upperarm_fixup', 'forearm_helper1', 'forearm_helper2',
          'forearm_helper3', 'forearm_helper4', 'forearm_fixup', 'elbow_fixup', 'elbow_armor',
          'hand_twist', 'wrist_fixup', 'grip', 'pinky0')] +
        ['r_hand_helper1', 'r_hand_helper2', 'r_hand_helper3', 'r_hand_helper4',
         'l_hand_marker_offset'])
GUN = ('gun', 'r_shell_1', 'r_shell_2', 'r_shell_3', 'l_shell_1', 'l_shell_2', 'l_shell_3', 'chamber',
       'cartridge', 'top_1', 'top_2', 'r_power_core', 'l_power_core')

PORT = reserved(
    order=27, wave='C2', name='Suppressor', source='Halo 4',
    messages=(87, 88), icon=47, reticle=36, label='su', teach_from='ar',
    sound_dir='sound\\weapons\\suppressor_port', weapon_dir='weapons\\suppressor',
    yardstick={
        # step 4a (user, 2026-10-14; h1_role_compare.py suppressor)
        'pick': 'Assault Rifle',
        'reason': ("user, step 4a 2026-10-14: same role (a magazine automatic). DEFAULT = Halo 4's own "
                   "numbers, BALANCED = the AR ratio rows (H1 AR x H4 Suppressor / H4 AR). The "
                   "speed is degenerate (Halo 4's AR is hitscan) -> Halo 4's 15 wu/s in both, 15 -> "
                   "15 (Halo 4's 60 -> 15 over 2.5 wu; Halo 1 would slow over the whole range). The "
                   "minimum error by the maximum's ratio (2 x 1.25 = 2.5; its own 3.33 gives 6.7). "
                   "No dual wield in Halo 4: no x1.5 carry. Halo 4's shard has no damage falloff "
                   "(flag unset) -- nothing to copy. Needler ratio rejected: inverted error bounds, "
                   "the needle's materials"),
        # DEFAULT = Halo 4's own numbers; these are the BALANCED rows. Halo 4: Suppressor / AR
        # (6.25 plasma_fast x 15 / 7.5 bullet_slow x 10; 48 / 32; 192 / 160; 336 / 256; 59 / 59 fr;
        # error 0.5 -> 3 / 0.15 -> 2.4; aim 7.5/15 10/20 / 5/16 10/16; range 100 / 100)
        'balanced': {
            'damage': 8.33,              # 10 x 6.25/7.5
            'rounds_per_second': 22.5,   # 15 x 15/10 -- Halo 1 fires 15..29.9 at 15/s (measure)
            'magazine': 90,              # 60 x 48/32
            'rounds_total_initial': 288,  # 240 x 192/160
            'rounds_total_maximum': 787,  # 600 x 336/256 = 787.5 (no dual wield: no x1.5)
            'reload_s': 2.9,             # 87 fr x 59/59
            'error_min_deg': 2.5,        # 2 x 2.5/2 (user: the maximum's ratio 3/2.4 = 1.25)
            'error_max_deg': 8.13,       # 6.5 x 3/2.4
            'velocity': 15.0,            # degenerate (hitscan AR) -> Halo 4's own
            'range': 40.0,               # 40 x 100/100
            'aim': (9.0, 23.4, 12.0, 31.25),  # 6 x 7.5/5, 25 x 15/16; 12 x 10/10, 25 x 20/16
            'melee': None},              # Halo 4 shares strike_melee: x1
        'measured': 'h1_role_compare.py suppressor',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg',
            'provisional': 'Assault Rifle',
            'alternatives': ['Needler', 'Sentinel Beam (H4 storm_sentinel_beam, AI-only)'],
            'direct': None,
            'peers': ['Assault Rifle', 'Plasma Rifle', 'Needler', 'SMG (port)', 'Storm Rifle (port)'],
            'why': 'magazine 48 full-auto, decelerating hardlight projectile (60 -> 15 wu/s)',
            'lacks': "Halo 4's first 2.5 wu at 60 -> 15 wu/s (15 flat), sprint"}},
    # step 11: Halo 4's ai\generic Suppressor entry (m020: weapon properties #22, firing pattern #22,
    # 18 fields) over a base -- 'su' has no carrier. Halo 1's ASSAULT RIFLE carriers
    # (h1_weapon_carriers, 2026-10-14): Marines / Flood combat 0.4, armoured Marines 0.5 - 0.6, the
    # Grunts' plasma-pistol-with-AR variants 0.5 / 0.6, the wounded sitting Marine 0 -- donor = the AR
    # (the SMG's choice). WDM RULE: 0.4 x the AR's player dps 150 (h1_role_compare suppressor) / the
    # port's (default 6.25 x 15 = 93.75, balanced 8.33 x 15 (22.5 tag) = 125)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg',
                    'donor_weapon': 'weapons\\assault rifle\\assault rifle',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 150.0, 'port_dps': 93.75,
                                 'balanced_port_dps': 125.0},
                    # THE BALANCED DROP RULE: Halo 1's AR carriers 0.3 - 0.9 (10 of 12) x Halo 4
                    # Suppressor 0.7 - 0.9 / Halo 4 AR 0.5 - 0.9 (m020 ai\generic) = 0.42 - 0.9; the
                    # rounds: Halo 4's Suppressor sets none (AR 192 - 256): a zero on one side, no row
                    'balanced_set': ['0x1D8=0.42:Drop Weapon Loaded', '0x1DC=0.9:Drop Weapon Loaded Max'],
                    # THE SPECIES SKILL RULE (C1): each slot's aim on its own species' stock skill
                    'species_skill': True},
)

PORT.update({
    'status': 'done',             # 2026-10-15: 8 dry boots, balanced, Armed (grunt, jackal, elite) on a30
    #   RE-CHECK 2026-10-19/20 (user): firing glow (su_fire_glow on D out = rate of fire), 3 boots on a30
    # CLOSE-OUT RECORD (2026-10-15):
    # STEP 4b (port_field_audit --port suppressor, final): weapon list 2 = 0 (error deceleration 1.2,
    #   illumination recovery 0.04 written); list 4 deliberate (rate ramp 0 / 0 and tracers 0 = Halo 4's
    #   own; tracers on every round = the shard's streak); list 5 = decisions (message 87, reload time 2.0
    #   = the full reload's 1.97 s, the FP offset = the measured FP muzzle). Projectile list 2: speed (user,
    #   4a: 15 -> 15) and the air damage range (INERT both sides: Halo 4's distance flag is off, the AR
    #   bullet's lower = upper) -- kept. List 3 decided: deviation angle 0 (the template's), bounding radius
    #   0 (the Spike Rifle's), the material responses = the AR bullet's (Halo 4's shard bounces only at
    #   20-30 wu/s: never at 15), damage category kept 'bullet' (the Beam Rifle's precedent: Halo 1 has no
    #   plasma_fast counterpart that changes damage).
    #   List 3, every line with a Halo 1 field (re-checked at close-out, flags by NAME from the Halo 4 MCC
    #   plugin): weapon flags 6656 vs the AR's 2560 = bit 12 'Loop FP Firing Animation' (no Halo 1 flag:
    #   Halo 1 restarts fire-1 a round -- the Spike Rifle's; firing passed every boot); weapon functions
    #   4 vs 3 and attachments 3 vs 1 = Halo 4's own shader / FX hooks -> the template's 4 functions and
    #   2 attachments (muzzle light, flashlight) kept; projectile functions / change colours blocks and
    #   attachment[0] (Halo 4's projectile EFFECT, the streak) -> the contrail + shard glow; projectile
    #   flags 131073 = 'Oriented Along Velocity' (set) + bit 17 'Disable Instantaneous First Tick' (no
    #   Halo 1 field); water damage range 0..10 vs 5..10 (a zero on one side) INERT like the air range ->
    #   the template's 0..5 kept; damage flags (the AR's bit 19, the Suppressor's 0; Halo 1's template 0)
    #   nothing to write.
    # TAG WRITES PROVEN (closing check 6; Halo 1 = port_field_audit.flatten): 54 tags (every
    #   weapons\suppressor tag, cyborg animations, hud_item_messages, hud_reticles / _msg_icons + _r, the
    #   ten scenarios), the model + pickable writers re-run: 1,036,348 fields, 4 changed = the bitmaps'
    #   base address (tool's garbage pointer). Checks 7 / 2: port_sounds --check 0, validate_halo_json 0;
    #   8: in used_weapons(), donors for every Armed slot; 9: shield-hit effect x0.098 (all 25 particles).
    # TEMPLATE DIFF (h1_port_template_diff, final, 566 lines): weapon 29 (the numbers above, own tags,
    #   label su), shard 30 (own impact effects: the impact sound + the hit-effect rule; the glow light;
    #   oriented along velocity; 15 wu/s, range 100, no gravity, own flyby), damage 2 (6.25), melee 0 (the
    #   AR's: Halo 4 shares strike_melee), fire effect 491 (off-axis flashes / FP smoke / casing / eject
    #   dropped, the centre flash tinted and 3 units up), empty 1, HUD 11 (reticle 36, icon 47, the 48
    #   meter), shader 2 (own maps). Every line a decision below.
    # 5b (h1_role_compare suppressor, the built port): default = Halo 4's own row (94 dps, Elite minor
    #   2.53 s normal); balanced = the AR-ratio row (125 dps, 1.93 s; the AR 150, 1.60 s).
    # AUDITS on the a30 test copy: port_refs_audit 0 problems; port_sound_refs all OWN but the KEEPs below.
    # CAPACITY: Halo 1's 32 MiB model-buffer cap found on this port (memory h1-model-buffer-32mib-cap):
    #   world = fp tag, decimated to 60 %.

    # BORROWED sounds kept ON PURPOSE (port_sound_refs prints these as KEEP)
    'sound_keeps': {r'sound\sfx\weapons\assault rifle\flashlight': 'the flashlight rule: the game\'s own',
                    r'sound\sfx\weapons\weapon_pickup_ammo\ar_ammo':
                        'user, boot 1: the ammo pickup sound does not need adapting (Halo 4 names only a '
                        'fallback event, ammo_pickup_generic, no bank)'},

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). ONE render model for world AND
    # first person: 13 nodes (b_gun root, not tilted; three shells a side, chamber + cartridge, top_1
    # / top_2, two power cores); two regions with data, 'default' (mesh 0: 1106 verts, the stock) and
    # 'knight_arm' (mesh 1: 12793 verts, the rest -- the Knight's version drops 'default'), the
    # shatter / mechanical / refractive skins empty (no geometry). Materials: _glow
    # (srf_char_blinn_selfillum, si white x12 through the control map) and _metal
    # (srf_char_forerunner_andrew: diff (MISSING) + control + normal + cube, albedo tint 0.431).
    # Markers: primary_trigger 0.187 (the shard's spawn) and primary_trigger_muzzle 0.257 (the
    # flash) -> Halo 1's ONE 'primary trigger' at the muzzle; flashlight; left_hand etc. unused
    'model': {
        'dir': r'weapons\suppressor',
        'world': H4 + SW + r'\storm_forerunner_smg.render_model',
        'fp': H4 + SW + r'\storm_forerunner_smg.render_model',
        'world_name': 'suppressor',
        # DECIMATION (plan 0.1 rule for new Reach / Halo 4 ports; Halo 1's 32 MiB model buffer):
        # previews 40 / 50 / 60 (h1_decimate preview --render): 40 and 50 lumpy on the side (stock,
        # lower rails merged), 60 keeps the outline, rails and drum -> 60 % (15698 -> 9418 triangles,
        # 0.767 -> 0.501 MiB; shape error 99% 1.8 mm, max 2.7 mm). FP-visible surface protected
        'markers': {'primary_trigger': None, 'primary_trigger_muzzle': 'primary trigger'},
        'ground_point': 'auto',
        # an own hull (the template's hides the world model, C1): the render model's extent (x
        # -0.049..0.260, y +-0.025, z -0.039..0.079) as body + grip
        'collision': {'material': 'metal',
                      'boxes': [((-0.049, -0.025, 0.0), (0.26, 0.025, 0.079)),
                                ((-0.035, -0.015, -0.039), (0.04, 0.015, 0.0))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_forerunner_smg_default_metal': 'su_metal',
                           'storm_forerunner_smg_default_glow': 'su_glow'},
        'shaders': {'su_metal': (STANDIN, None)},
        'template': AR + r'fp\shaders\gun',
        'glow': {},
        # the glow strips (Halo 4: self-illum x12 on the control map's near-white texels there) --
        # an additive radial glow per UV island (the Storm Rifle's).
        # BOOT 1 (user: 'the illuminated parts are a bit underwhelming'): the strips are long thin
        # islands and a radial glow lit their middles only -> gain 2.2, falloff 0.35, radius 1.3: the
        # whole strip lit, a yellow-white core (Halo 4's cores clip to 244 / 228 / 32)
        'glow_shaders': {'su_glow': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_smg_default_glow',
                                     # BOOT 2 (user: 'now pure white'): the white-hot core
                                     # took over at gain 2.2 -> no hot core: the whole strip in
                                     # the screenshot's yellow-orange
                                     # BOOT 4 (user: 'any concept to make it really pop?' -> try the
                                     # halo + the hot centreline together, on different parts): B
                                     # = every strip a STRIP glow (falls off across the long axis,
                                     # not radially) with a narrow pale-yellow core line
                                     'strip': True, 'gain': 1.6, 'falloff': 0.5, 'radius': 1.2,
                                     # BOOT 5 (user: 'the back glow lights are too light' -- the rear
                                     # strips / drum ring without the halo read pale-white): the core
                                     # narrower (power 3) and yellower
                                     'hot': True, 'core': 3.0, 'hot_rgb': (1.0, 0.9, 0.5)},
                         # A = the HALO (bloom stand-in): a soft wide strip glow on the cards below
                         'su_halo': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_smg_default_glow',
                                     'strip': True, 'gain': 0.8, 'falloff': 1.5, 'radius': 1.0,
                                     'hot': False},
                         # REWORK 2026-10-19 (user: 'the weapon glow when firing like the other
                         # Forerunner weapons'): the LightRifle's firing light-up -- the strips
                         # again, hotter and wider, FADED by D out (the rate of fire: on while
                         # firing, 0.6 s fade; the trigger below). Colour = Halo 4's own firing
                         # light (fr_smg_firing.cheap_light colour 239 / 110 / 12) -> (1, 0.46, 0.05).
                         # BOOT 3 (user: 'visible, could use some more red / orange'; additive over
                         # the yellow strips) -> (1, 0.30, 0)
                         'su_fire_glow': {'rgb': (1.0, 0.30, 0.0), 'additive': True, 'islands': True,
                                          'islands_of': 'storm_forerunner_smg_default_glow',
                                          'strip': True, 'gain': 2.0, 'falloff': 0.8, 'radius': 1.3,
                                          'hot': False, 'fade_source': 'D_out'}},
        # BOOT 4 test: halo cards (each strip copied x2.2 about its centre, lifted 0.05) on the FRONT-LEFT
        # strips only (islands 2 / 5 / 8: the long strip, the short one, the front ring; within 3.5
        # of (16, 1, 2) JMS units) -- the rear-left strips (12 / 13 / 17) show B alone.
        # BOOT 5 (user: front good, the rear too light): the halo on EVERY strip
        # BOOT 6 (user: 'the back strip is too long, through another part'; 'the front glow is a square
        # floating off the gun, a line in FP'): x2.2 ACROSS a strip only (`along` 1.05), and no card
        # on the pieces facing along the barrel (+-x: the front / end caps)
        'glow_cards': {'su_halo': {'of': 'su_glow', 'shader': 'su_halo', 'scale': 2.2, 'along': 1.05,
                                   # + the tilted top plate (island 4, normal 0.66 / 0 / 0.76): its card
                                   # stood above the gun outline (the floating square)
                                   'lift': 0.05, 'skip_piece_normals': [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
                                                                  (0.655, 0.0, 0.756)],
                                   'skip_piece_dot': 0.9,
                                   # BOOT 7 (user: 'the circle is tilted off the gun', both rings on the
                                   # world model): cards scale in the piece's own plane only; a
                                   # round piece (the rings) x1.4 both ways
                                   'round_scale': 1.4},
                       # the firing cards (the LightRifle's lr_fire): every strip, lifted past the
                       # halo; the same skipped pieces as su_halo (barrel-facing caps, the tilted top
                       # plate). BOOT 1 (user: 'pretty good -- shrink it a bit onto the existing glow
                       # panels'): x2.6 / rings x1.8 / lift 0.08 -> x1.3 / x1.15 / 0.06. BOOT 2 (user:
                       # 'not visible enough, partly back'): halfway -> x1.9 / x1.45 / 0.07
                       'su_fire': {'of': 'su_glow', 'shader': 'su_fire_glow', 'scale': 1.9, 'along': 1.05,
                                   'lift': 0.07, 'round_scale': 1.45,
                                   'skip_piece_normals': [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
                                                          (0.655, 0.0, 0.756)],
                                   'skip_piece_dot': 0.9}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_forerunner_smg (Foundry,
    # h4_fp_dump.py -> out\h4_fp), the arms RE-SOLVED. 24 animations: fire_1 var1 5, idle 100, posing
    # var1 90 / var2 106, ready 20 (ready_initial 29), put_away 5, melee_strike_1 34 (primary keyframe
    # 4) / _2 36, reload_full 59 / reload_empty 68, throw_grenade 44, moving 22 / look 9 (overlays),
    # first_time_pickup 94, sprint / jump / land / fall (no Halo 1 state)
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_forerunner_smg.render_model',
        'nodes': {n: 'frame b ' + n.replace('_', ' ') for n in GUN},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\suppressor\fp',
        'h1_model': r'weapons\suppressor\fp\fp',
        # BOOT 1 (user's video: 'the left hand position, not sure if it's weird'): Halo 4's left
        # fingers curl over the gun's front-left, visible above / left of the drum; ours sat lower
        # and behind the drum (a tan sliver). Rendered through Halo 4's reference camera (FOV 70)
        # with trial offsets: (0, +0.01, +0.01) gun space matches the look. The hand-in-gun count
        # DOUBLES (idle 3229 -> 6150: Halo 1's chunkier palm sits inside the gun, unseen) -- the
        # look decides (the count stands in for it). Idle / posing / fire only; ready, reloads,
        # melee, grenade on Halo 4's own wrists
        'hand_offset_anims': {a: {'l': (0.0, 0.01, 0.01)} for a in
                              ('first_person:idle', 'first_person:posing:var1', 'first_person:fire_1:var1')},
        'align': 'same_space',
        # BALANCED BOOT (user: 'lower the entire FP by 2 units'; 1 unit = 0.01 wu)
        'view_offset': (0.0, 0.0, -0.02),
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

    # Halo 4's own sounds (h1_port_sounds.py suppressor, `bank` 'halo4'). The graph's frame events:
    # ready / melee_strike_1 / reload_full = ONE foley event each, 3 random variants (-> Halo 1
    # permutations; reload_empty 2); posing var1 = player_a @0 + player_b @46; fire = the weapon's
    # 'single shot fire for automatics' play_forerunner_smg_player_fire_single, THREE layers at once
    # (body 1.09 s, crack 0.33 s, sweetener 0.29 s) -> one Halo 1 sound a round; dry fire =
    # play_wea_forerunner_smg_player_dry_fire. put_away / fire_1 foley: empty in MCC. The drop (its
    # material effects: wea_drop_pistol_fr_bolt_pistol_nonplayer, bank forerunner_bolt_pistol_player),
    # the flyby (proj_forerunner_whizby_small, 17 variants), the impact (the material effects' plasma
    # impact dirt + the forerunner sweetener). Levels = the stock Halo 1 AR sound each stands in for
    # (smg.py: fire -13.0, dryfire -17.6, ar_reload -20.9, ar_melee -16.2, weapon ready -13.1,
    # pistol_posing -26.5, assault_impact -20.7); flyby / impact the Storm Rifle's (-26.2 / -11.3)
    'sounds': {
        'catalog': 'Suppressor',
        'bank': 'halo4',
        'wwise_bank': 'forerunner_smg_player',
        'dir': B.join(['sound', 'weapons', 'suppressor_port']),
        'sounds': {
            'su_fire': (['play_forerunner_smg_player_fire_single:0', 'play_forerunner_smg_player_fire_single:1',
                         'play_forerunner_smg_player_fire_single:2'],
                        'sound\\sfx\\weapons\\assault rifle\\fire', -13.0),
            'su_dryfire': (['play_wea_forerunner_smg_player_dry_fire'],
                           'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'su_ready': (['play_npc_storm_fp_forerunner_smg_foley_first_person_ready'],
                         'sound\\sfx\\weapons\\assault rifle\\weapon ready', -13.1),
            'su_melee': (['play_npc_storm_fp_forerunner_smg_foley_first_person_melee_strike_1'],
                         'sound\\sfx\\weapons\\weapon_anims\\ar_melee', -16.2),
            'su_reload': (['play_npc_storm_fp_forerunner_smg_foley_first_person_reload_full'],
                          'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            'su_reload_empty': (['play_npc_storm_fp_forerunner_smg_foley_first_person_reload_empty'],
                                'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            # the BALANCED reloads' sounds (the patcher retimes the reloads and swaps these in)
            'su_reload_balanced': (['play_npc_storm_fp_forerunner_smg_foley_first_person_reload_full'],
                                   'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            'su_reload_empty_balanced': (['play_npc_storm_fp_forerunner_smg_foley_first_person_reload_empty'],
                                         'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            'su_pose': (['play_smg_first_person_posing_var1_player_a', 'play_smg_first_person_posing_var1_player_b'],
                        'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'su_drop': (['play_wea_drop_pistol_fr_bolt_pistol_nonplayer@forerunner_bolt_pistol_player'],
                        'sound\\sfx\\impulse\\weapon_drops\\assault_impact', -20.7),
            'su_flyby': (['play_proj_forerunner_whizby_small@proj_forerunner_whizby_small'],
                         'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            'su_impact': (['play_wea_plasma_impact_dirt@plasma_impact_generic',
                           'play_wea_forerunner_impact_generic@forerunner_impact_sweetener'],
                          'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
        },
        'offsets': {'su_pose': [0.0, 46 / 30.0]},
        'stretch': {'su_reload_balanced': 87 / 59.0, 'su_reload_empty_balanced': 87 / 59.0},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only suppressor) on a COPY of the Halo 1 ASSAULT RIFLE.
    # DEFAULT = HALO 4's OWN NUMBERS; the AR-ratio values are the balance rows.
    # STEP 6, the ammo pickup: the template's magazine names `powerups\assault rifle ammo` (AR ammo
    # tops it up). Halo 4 gives no pickup amount (its ammo comes from Forerunner ammo boxes: item
    # rounds 0) -> the H1 AR's own pickup : initial (240 : 240) on Halo 4's initial = 192
    'pickable': {
        'weapon': SU + 'suppressor',
        'template': AR + 'assault rifle',
        'world_model': SU + 'suppressor',
        # ONE model tag for world AND first person (user, 2026-10-14): Halo 1's map builder crashes
        # past 32 MiB of model vertices + indices (memory h1-model-buffer-32mib-cap); the world and
        # fp gbxmodels are the same geometry (only the permutation name differs), so the weapon
        # names the world tag twice and the map stores it once (-0.80 MB). fp\fp.gbxmodel is still
        # written by the model step for the FP tools (fp_render, h1_fp_muzzle, h1_fp_hand_clip)
        'fp_model': SU + 'suppressor',
        'fp_anims': SU + 'fp\\fp',
        'label': 'su',
        'teach': ('su', 'ar'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'su_ready',
                   'first-person posing': SND + 'su_pose',
                   'first-person melee': SND + 'su_melee',
                   'first-person reload-empty': SND + 'su_reload_empty',
                   'first-person reload-full': SND + 'su_reload'},
        # own shard + damage (step 3): Halo 4 storm_forerunner_smg_shard 6.25 (lower 0, upper 6.25 /
        # 6.25, NO distance flag: flat), plasma_fast, 15 wu/s flat (see the docstring), range 100.
        # Materials: the AR bullet's (Halo 4 plasma_fast / bullet_slow = 1, C1)
        'bullet': {'projectile': (AR + 'bullet', SU + 'shard'),
                   'damage': (AR + 'bullet', SU + 'shard'),
                   'dmg': 6.25, 'velocity': (15.0, 15.0), 'range': 100.0,
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'su_flyby',
                                   # Halo 4: 'oriented along velocity'-style streak (a tracer
                                   # system); air gravity 0 (the AR's 1 at 15 wu/s would drop it)
                                   'proj_attrs.physics.air_gravity_scale': 0.0,
                                   'proj_attrs.flags.oriented_along_velocity': True},
                   # every response effect that plays the AR's bullet impacts -> the shard's own
                   # BOOT 1 (user: 'looking forward to the impact sound'): Halo 4's shard plays
                   # plasma impact + the forerunner sweetener on every hard surface (its material
                   # effects) -> su_impact over the AR bullet's hard-surface hits; flesh, shield and
                   # water hits stay the game's (Halo 4's own flesh / shield sets not ported)
                   'impact_tint': {'match': (), 'rgb': None, 'out': SU + 'effects\\impact\\',
                                   'sounds': {'sound\\sfx\\impulse\\impacts\\' + s: SND + 'su_impact'
                                              for s in ('dirthits', 'granhit', 'metalhit', 'woodhit',
                                                        'snow_hits', 'glass_hits', 'bullet_ricc',
                                                        'ice_hits')}},
                   # THE HIT-EFFECT RULE: a 15/s weapon (default 15; balanced 22.5 fires 15/s)
                   'impact_thin': {'materials': [22], 'out': SU + 'effects\\impact\\',
                                   'thin': {}, 'rate': 15.0},
                   # the LOOK: Halo 4's shard = a tracer system + light volumes in hardlight
                   # orange -> the AR tracer's contrail recoloured (the Spike Rifle's), every round
                   'contrail': {'from': AR + 'bullet', 'out': SU + 'shard', 'rgb': ORANGE,
                                # BOOT 1 (user: 'shards are a bit too translucent'): an additive
                                # streak cannot be opaque -> brighter towards a hot yellow-white and
                                # wider (the AR tracer's 0.05 -> 0.07), plus the glow below
                                'states': [{'transition': (0.01, 0.0125), 'width': 0.07,
                                            'argb': (1.0, 1.0, 0.88, 0.45)},
                                           {'width': 0.07, 'argb': (1.0, 1.0, 0.88, 0.45)}]},
                   # BOOT 1: a GLOWING shard (Halo 4: a lens flare + light volumes on every shard) --
                   # the Concussion Rifle's recipe: own copies of the fuel rod exhaust light + flare
                   'glow': {'light': (r'weapons\fuel rod gun\fuel rod exhaust', SU + 'shard glow'),
                            'flare': SU + 'shard glow', 'rgb': ORANGE, 'flare_radius': 0.06,
                            'marker': ''}},
        # Halo 4: 15/s flat (rate ramp 0 / 0)
        # STEP 4b list 2: error deceleration Halo 4 0.6 / its AR 0.5 x the H1 AR's 1.0 = 1.2 s
        # THE FIRING GLOW (user, 2026-10-19): Halo 4's `visable` = primary_barrel_firing, on at once
        # while firing, back to 0 linearly over 0.6 s, off with primary_ammunition. Halo 1's nearest
        # signal is the trigger's RATE OF FIRE ramp (the Sentinel Beam's hum source: smooth, follows
        # acceleration / deceleration time, 0 unless the bounds differ) -> 15 .. 16 (Halo 1 fires
        # 15 .. 29.9 at 15/s: the rate is unchanged), acceleration 0, deceleration Halo 4's 0.6 s
        'trigger': {'rounds_per_second': (15.0, 16.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.6, 'error_deceleration_time': 1.2,
                    'rounds_between_tracers': 0,
                    # the FP muzzle in the idle (h1_fp_muzzle weapons\suppressor\fp\fp): the shard's
                    # streak starts at the first-person muzzle (the Storm Rifle's)
                    # (balanced boot: the FP view 2 units lower -> re-measured, up -0.0331 -> -0.0531)
                    'first_person_offset': (0.3317, -0.0259, -0.0531)},
        'fields': {
            'weap_attrs.magazines.0.magazine_items.0.rounds': 192,
            # STEP 4b list 2: illumination recovery 0.04 x 0.1/0.1 (Halo 4 / its AR x the H1 AR)
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.04,
            'item_attrs.collision_sound.filepath': SND + 'su_drop',
            # the OWN hull (h1_box_collision.py suppressor --write; model['collision']): stage 1's
            # a30 build crashed with the AR's hull (other nodes) on the 13-node model
            'obje_attrs.collision_model.filepath': SU + 'suppressor',
            # the template's object export D (compass) cleared: the weapon's export D carries the
            # rate of fire (rewire below), so function 3 has one source
            'obje_attrs.D_in': 'none'},
        # the firing glow's signal: the AR template's layout (A integrated light, B ammo, C
        # illumination) + D = primary rate of fire -> function 3 (D out, the su_fire_glow shader's
        # fade) turning off with function 0 (the loaded fraction: Halo 4's off with
        # primary_ammunition)
        'rewire': {'inputs': ('integrated_light', 'primary_ammunition', 'illumination',
                              'primary_rate_of_fire'),
                   'functions': {3: (3, 'D_in', 'firing glow', {'turn_off_with': 0})}},
        # Halo 4: minimum error 0, error angle 0.5 -> 3
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.5, 3.0)},
        # Halo 4: 48 loaded, 192 at the start, 336 most; reload time: none in the tag (the animation
        # decides: full 59 fr = 1.97 s) -> 2.0 (the SMG's)
        'magazine': {'rounds_loaded_maximum': 48, 'rounds_reloaded': 48,
                     'rounds_total_initial': 192, 'rounds_total_maximum': 336,
                     'reload_time': 2.0},
        # Halo 4 aim assist (the MODE block), absolute
        'aiming': {'autoaim_angle': 7.5, 'autoaim_range': 15.0,
                   'magnetism_angle': 10.0, 'magnetism_range': 20.0},
        'sound_effects': {
            # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Halo 4's FIRST-PERSON firing
            # (fx\fr_smg_firing_muzzle_flash + fx\fr_smg_firing): NO flash sprite -- a cheap light
            # at primary_trigger_muzzle (firing_1p) and small hardlight sparkles on the side plates
            # (mid_plate / top_plate / rear slide particles, not reproduced); no smoke, no casing.
            # The AR's (h1_effect_particles): six off-axis FP flashes 0.10-0.125 at +-0.02-0.03 wu
            # (dropped: drop_off_axis), the on-axis centre flash 0.038-0.043 (KEPT, orange: the
            # light's stand-in), FP smoke 4-6 (dropped), the casing + the pistol's eject (dropped)
            'firing_effect': (AR + 'effects\\fire bullet', SU + 'effects\\fire shard',
                              {r'sound\sfx\weapons\assault rifle\fire': SND + 'su_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.0,
                               # BOOT 1 (user: 'not at the muzzle yet, a bit higher'): 1 unit up;
                               # BOOT 2 ('needs to move further up'): 2 units; BOOT 3 ('2 more
                               # units up'): 4 units
                               # BOOT 4 ('1 unit back down'): 3 units
                               'shift': (0.0, 0.0, 0.03),
                               'drop_particles': ('casing', 'smoke h fp'),
                               'drop_parts': (r'sound\sfx\weapons\pistol\eject',),
                               'tint': (1.0,) + ORANGE}),
            'empty_effect': (AR + 'effects\\empty', SU + 'effects\\empty',
                             {r'sound\sfx\weapons\assault rifle\dryfire': SND + 'su_dryfire'})},
        'melee': (AR + 'melee', SU + 'melee'),
        'melee_response': AR + 'melee_response',
        'messages': ('Picked up a suppressor', 'Picked up %d rounds for suppressor'),
        'icon': 'suppressor',
        'extra_sounds': [SND + 'su_reload_balanced', SND + 'su_reload_empty_balanced'],
        # the AR's HUD with Halo 4's crosshair (ui\hud\weapons\forerunner\forerunner_smg: the hex
        # inner_bracket top / bottom (24 x 16, scale 0.7 about its centre, 0.95), the inner_carrot
        # left / right (8 x 16, x0.7, 0.95), the four outer corners (24 x 24, 0.5)) -- 3 px a unit;
        # PROVISIONAL until the user's Halo 4 screenshot. A magazine meter for 48 / 90
        'hud': {'donor': AR + 'assault rifle', 'out': SU + 'suppressor',
                'reticle': (H4 + SUR + 'outer', 0, 'suppressor'),
                'reticle_xform': {'offset': (-28.0, -21.0), 'gain': 0.5},
                'reticle_layers': [(H4 + SUR + 'outer', 0, 1.0, {'flip_x': True, 'offset': (28.0, -21.0), 'gain': 0.5}),
                                   (H4 + SUR + 'outer', 0, 1.0, {'flip_y': True, 'offset': (-27.0, 20.0), 'gain': 0.5}),
                                   (H4 + SUR + 'outer', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (28.0, 20.0), 'gain': 0.5}),
                                   (H4 + SUR + 'inner_bracket', 0, 0.7, {'offset': (0.0, -6.0), 'gain': 0.95}),
                                   (H4 + SUR + 'inner_bracket', 0, 0.7, {'flip_y': True, 'offset': (0.0, 6.0), 'gain': 0.95}),
                                   (H4 + SUR + 'inner_carrot', 0, 0.7, {'offset': (-13.0, 0.0), 'gain': 0.95}),
                                   (H4 + SUR + 'inner_carrot', 0, 0.7, {'flip_x': True, 'offset': (13.0, 0.0), 'gain': 0.95})],
                'reticle_split': 1,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 1.6, 'reticle_overlay': 1.5 / (123 / 97.0 * 1.6 * 2 * 0.75),
                # ticks as tall as stock Halo 1's AR meter's (30 px), the rows re-wrapped to reach it (user 2026-10-20: 'drawn comparatively small')
                'ammo_meter': {'sizes': (48, 90), 'base': SU + 'bitmaps\\suppressor_ammo',
                               # Halo 4's own pips (generic-meter audit, user 2026-10-17): they touch at their soft
                               # edges -> cut at alpha 128, and 24 a row (two stay joined at any cut)
                               'art': {'tick_h': 30, 'h3': (H4 + r'ui\hud\weapons\forerunner\forerunner_smg\bitmap\ammo_forerunnersmg', 0),
                                       'native': True, 'grid': 24, 'cut': 128}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py suppressor). DEFAULT = Halo 4's own
    # numbers in the tags; BALANCED = the AR ratio (step 4a, user 2026-10-14). Assembly Halo1 units:
    # angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Suppressor', 'source': 'Halo 4', 'donor': 'Assault Rifle', 'default_on': False,
            'desc': "Halo 4's Suppressor: its model, first-person animations, sounds and numbers. A "
                    "48-round Forerunner automatic firing slow, glowing hardlight shards, 15 a "
                    "second; Assault Rifle ammo tops it up.",
            'balance_desc': "Measured against the Assault Rifle, which both games have: 8.3 damage "
                            "a shard (Halo 1 fires it at 15 a second), a 90 magazine, 288 at the "
                            "start / 787 most, a 2.9 s reload, a wider spray, 40 wu range and "
                            "Halo 1-style aim assist.",
            # step 9: the balanced reload, H1 AR 87 fr x 59/59 = 87 over the BUILT 59 / 68 = x1.47 /
            # x1.28 (ONE multiplier: the full reload's); swap (the ready's): H1 AR ready 29 fr x
            # 20/20 (Halo 4 AR ready 20) over the built 20 = x1.45
            'anims': {'reload': 87 / 59.0, 'swap': 1.45},
            # both reloads play their own sound (Halo 4: reload_full / reload_empty events) -> a LIST
            # of swaps (the Battle Rifle's), each stretched x87/59 (the one reload multiplier)
            'anim_sounds': {'reload': [{'mult': 87 / 59.0, 'from': SND + 'su_reload',
                                        'to': SND + 'su_reload_balanced'},
                                       {'mult': 87 / 59.0, 'from': SND + 'su_reload_empty',
                                        'to': SND + 'su_reload_empty_balanced'}]},
            'balance': [
                row('jpt!', SU + 'shard', 'Damage Lower Bound', 8.33, 6.25, 'Bullet Damage'),
                row('jpt!', SU + 'shard', 'Damage Upper Bound', 8.33, 6.25, 'Bullet Damage'),
                row('jpt!', SU + 'shard', 'Damage Upper Bound Max', 8.33, 6.25, 'Bullet Damage'),
                row('weap', SU + 'suppressor', 'Rounds Per Second', 22.5, 15.0, 'More Shooting', block='Triggers'),
                row('weap', SU + 'suppressor', 'Rounds Per Second Max', 23.5, 16.0, 'More Shooting', block='Triggers'),  # the glow's ramp: bounds differ
                row('weap', SU + 'suppressor', 'Rounds Loaded Maximum', 90.0, 48.0, 'Magazine', block='Magazines'),
                row('weap', SU + 'suppressor', 'Rounds Reloaded', 90.0, 48.0, 'Magazine', block='Magazines'),
                row('weap', SU + 'suppressor', 'Rounds Total Initial', 288.0, 192.0, 'Magazine', block='Magazines'),
                row('weap', SU + 'suppressor', 'Rounds Total Maximum', 787.0, 336.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the H1 AR's pickup : initial (240 : 240) on the balanced 288
                row('weap', SU + 'suppressor', 'Rounds', 288, 192, 'Ammo pickup', block='Magazines/Magazines'),
                # the minimum by the maximum's ratio (user, 4a): 2 x 3/2.4 = 2.5; max 6.5 x 3/2.4
                row('weap', SU + 'suppressor', 'Error Angle', 2.5, 0.5, 'Error Angle', block='Triggers'),
                row('weap', SU + 'suppressor', 'Error Angle Max', 8.13, 3.0, 'Error Angle', block='Triggers'),
                row('proj', SU + 'shard', 'Maximum Range', 40.0, 100.0, 'Projectile'),
                row('weap', SU + 'suppressor', 'Autoaim Angle', 9.0, 7.5, 'Autoaim'),
                row('weap', SU + 'suppressor', 'Autoaim Range', 23.4, 15.0, 'Autoaim'),
                row('weap', SU + 'suppressor', 'Magnetism Angle', 12.0, 10.0, 'Magnetism'),
                row('weap', SU + 'suppressor', 'Magnetism Range', 31.25, 20.0, 'Magnetism'),
                # the 90 magazine's meter: suppressor_ammo sequence 1 (ammo_meter 48 90), step 255 //
                # 90 = 2 (default 255 // 48 = 5); flash at 10 x 90/60 = 15 (default 10 x 48/60 = 8)
                dict(row('wphi', SU + 'suppressor', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SU + 'suppressor', 'Alpha Multiplier', 2, 5, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SU + 'suppressor', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', SU + 'suppressor', 'Loaded Ammo Cutoff', 15, 8, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port suppressor): the source pair (Halo 4 Suppressor vs the
    # yardstick, Halo 4's AR) against the target pair (the H1 port vs its template = the H1 AR)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_forerunner_smg.weapon',
                              r'objects\weapons\rifle\storm_assault_rifle\storm_assault_rifle.weapon'),
                   'projectile': (SW + r'\projectiles\storm_forerunner_smg_shard.projectile',
                                  r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.projectile'),
                   'damage_effect': (SW + r'\projectiles\storm_forerunner_smg_shard.damage_effect',
                                     r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.damage_effect')},
        'target': {'weapon': (SU + 'suppressor.weapon', AR + 'assault rifle.weapon'),
                   'projectile': (SU + 'shard.projectile', AR + 'bullet.projectile'),
                   'damage_effect': (SU + 'shard.damage_effect', AR + 'bullet.damage_effect')}},

    # the dry test: a30 (this session's level, parallel pair 3), Halo 4's own loadout (48 + 192)
    'test': {'level': 'a30', 'rounds': (48, 192), 'grunt': None, 'elite': None},
})

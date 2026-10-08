r"""Spike Rifle (Halo 3 -> Halo 1, wave A5) on a copy of the Halo 1 ASSAULT RIFLE, which is also the
yardstick (step 4a, user 2026-10-08). smg.py is the shape it copies (a dual-wieldable automatic
on the AR); what is new here: a SLOWING, ARCING projectile (Halo 3: 25 -> 17.5 wu/s, air gravity
0.2) that RICOCHETS off hard surfaces, the blade melee (Halo 3 cut_melee 72), and a visible spike
on every round (Halo 3's light-volume streak) instead of the AR's every-third tracer."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\rifle\spike_rifle'
SK = 'weapons\\spiker\\'
SND = 'sound\\weapons\\spiker_port\\'
AR = 'weapons\\assault rifle\\'
# Halo 3's spike: a hot streak (a light volume on the lens-flare glow bitmap); its profile
# colour function holds BGRA 0c 39 ef = RGB 239 / 57 / 12, red-orange
ORANGE = (239 / 255.0, 57 / 255.0, 12 / 255.0)
# Halo 1 material indices the spike RICOCHETS off (Halo 3 chance 1, 0-60 deg: hard_terrain ->
# stone 2; hard_metal_thin / thick / solid -> metal hollow 5, thin 6, thick 7;
# energy_shield_invincible -> force field 10). Chance 0 in Halo 3 (default material, plain
# glass, ice, energy_shield_thick) -> none. Halo 1 materials 16 (Jackal shield) and 32 (Hunter
# shield) already REFLECT by default on the AR bullet: kept
RICOCHET = [2, 5, 6, 7, 10]
# the STUCK SPIKE (test 1): Halo 3 detonates the spike on most surfaces and leaves a model
# particle; Halo 1 does it the needle's way -- the spike ATTACHES (and shows its model) on
# everything Halo 3's spike does not pass through or fizzle on: overpenetrate water 28 /
# leaves 29 (Halo 3 liquid / plant), disappear on glass 9, force field 10, engineer force
# field 18, cyborg 22 / Elite 30 shields (Halo 3 fizzle), the AR's reflect on Jackal 16 /
# Hunter 32 shields kept. Bodies too (Halo 3 detonates on them, no pass-through)
ATTACH = [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 17, 19, 20, 21, 23, 24, 25, 26, 27, 31]
DISAPPEAR = [9, 10, 18, 22, 30]
# Halo 3's self-illum colours (BGRA bytes in the shaders' function data) and its grey mask
BLUE = (47 / 216.0, 49 / 216.0, 1.0)
# TEST 3 (user's Halo 3 screenshot): the lit spots read near-WHITE lavender in Halo 3 -- the
# body's blue at self_illum_intensity 6 (+ bloom) saturates; Halo 1 shows colour x mask, so
# the colour itself is the saturated one (47/49/216 x 6 clips to white; the bloom's blue tint)
PALE = (0.75, 0.78, 1.0)
AMBER = (1.0, 205 / 255.0, 87 / 255.0)
ILLUM = H3 + r'\bitmaps\brute_bolter_illum.bitmap'

PORT = reserved(
    order=14, wave='A5', name='Spike Rifle', source='Halo 3',
    messages=(61, 62), icon=34, reticle=23, label='sk', teach_from='hp',
    sound_dir='sound\\weapons\\spiker_port', weapon_dir='weapons\\spiker',
    yardstick={
        # step 4a (user, 2026-10-08): h3_weapon_values.py (spiker / needler / AR / plasma
        # rifle) + h1_role_compare.py brute_spiker. Halo 3's spiker is bullet_slow -- the
        # AR's damage group, not the needler's plasma_slow -- and does the AR's dps (72 vs
        # 75/s). AR ratio: 12 x 12/s = 144/s (H1 AR 150), every value scales, 12/s is under
        # the 15/s cap observation; needler ratio 180/s on the needle's materials (Flood in
        # 3 shots), its spread minimum 0/0 and the needle tag's speed 4 do not scale
        'pick': 'Assault Rifle',
        'reason': "user, step 4a 2026-10-08: the same damage type (Halo 3 bullet_slow, both) "
                  "and role (magazine automatic); H1 value = H1 AR x H3 spiker / H3 AR. "
                  "Values with no AR counterpart keep Halo 3's own in both versions: air "
                  "gravity 0.2 (H3 AR 0) and the ricochet material responses",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: spiker / AR. H1 AR: 10 dmg x 15/s, 60 (240 / 600), 87 fr reload, error 2 ->
        # 6.5 (min 0), 324 wu/s, gravity 1.0, range 40, aim 6/25 12/25, melee 55
        'balanced': {
            'damage': 12.0,              # 10 x 9/7.5
            'rounds_per_second': 12.0,   # 15 x 8/10
            'magazine': 75,              # 60 x 40/32
            'rounds_total_initial': 300,  # 240 x 120/96
            # DUAL-WIELD CARRY RULE: 600 x (160/384) x 1.5 = 375
            'rounds_total_maximum': 375,
            'reload_s': 2.8,             # 87 fr x 56/58 = 84 fr
            # the minimum's own ratio is degenerate (2 x 0.5/0.1 = 10 > the max): the
            # maximum's 6.5/3.0 on both bounds (the SMG rule): 0.5 -> 1.08, 1.25 -> 2.71
            'error_deg': (1.08, 2.71),
            'velocity': (101.25, 70.88),  # 324 x 25/80, 324 x 17.5/80
            'air_gravity': 0.2,          # H3 AR 0: no ratio -- Halo 3's own (user)
            'range': 70.0,               # 40 x 70/40
            'aim': (6.0, 20.0, 14.4, 22.5),  # 6 x 5/5, 25 x 12/15; 12 x 12/10, 25 x 18/20
            'melee': 56.6},              # 55 x cut_melee 72 / strike_melee 70
        'measured': 'h1_role_compare.py brute_spiker',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
            'provisional': 'Needler',
            'alternatives': ['Assault Rifle'],
            'direct': None,
            'peers': ['Assault Rifle', 'Needler', 'Plasma Rifle'],
            'why': "magazine 40 automatic, slow arcing projectile (25 wu/s, gravity): the needler's family",
            'lacks': 'dual wield, blade melee'}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07) laid over
    # the H1 AR's carriers ('sk' has no carrier; the SMG's precedent). Halo 1's AR carriers
    # (2026-10-08): Marines (plain / armoured / anchor, WDM 0.4-0.6), Flood combat human and
    # Elite (0.4), Grunt minor / major 'plasma pistol with assault rifle' (0.6 / 0.5).
    # ARMED WDM RULE: base 0.4 (the AR donors, as the SMG) x AR 150 / spiker dps -- default
    # 9 x 8 = 72 (0.83), balanced 12 x 12 = 144 (0.42)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
                    'donor_weapon': 'weapons\\assault rifle\\assault rifle',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 150.0, 'port_dps': 72.0,
                                 'balanced_port_dps': 144.0}},
)

PORT.update({
    'status': 'building',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's three materials all sample the same
    # `brute_bolter` base map (+ bump, + the brute_bolter_illum self-illumination): the body
    # `bolt_thrower` (detail metal_dirty), `bolt_thrower_dull` (rubber detail: the grip) and
    # `bolt_thrower_shiny` (chrome reflections: the blades). No meter shader on this gun.
    # The FP model also has 20 triangles of `shaders\invalid` (a flat cap at both barrel ends,
    # x 15.8 cm, on barrel 1 / 2) that Halo 3 never draws: dropped. Template: the AR's FP gun
    'model': {
        'dir': r'weapons\spiker',
        'world': H3 + r'\spike_rifle.render_model',
        'fp': H3 + r'\fp_spike_rifle\fp_spike_rifle.render_model',
        'world_name': 'spiker',
        'shaders': {'bolt_thrower': (H3 + r'\bitmaps\brute_bolter.bitmap', H3 + r'\bitmaps\brute_bolter_illum.bitmap'),
                    'bolt_thrower_dull': (H3 + r'\bitmaps\brute_bolter.bitmap', H3 + r'\bitmaps\brute_bolter_illum.bitmap'),
                    'bolt_thrower_shiny': (H3 + r'\bitmaps\brute_bolter.bitmap', H3 + r'\bitmaps\brute_bolter_illum.bitmap'),
                    # the STUCK SPIKE (test 1, user: 'it leaves a physical object behind, like
                    # the needler'): Halo 3's impact spawns a model particle
                    # (fx\particles\models\weapons\brute_spike, an opaque grey-metal map) for
                    # 4-5 s -- Halo 1 has no model particles: the projectile's own model
                    'spike': (r'fx\particles\models\weapons\brute_spike\_bitmaps\spike.bitmap', None)},
        'extra_models': {'spike model': {'from': r'fx\particles\models\weapons\brute_spike\brute_spike.particle_model',
                                         'dir': r'weapons\spiker\spike model', 'material': 'spike'}},
        'drop_materials': ['invalid'],
        # the illum map is a GREY mask of 68 texels (0.1%: small indicator lights); Halo 3
        # colours it per shader (self_illum_color, BGRA bytes in the function data): the body
        # blue 2f/31/d8 at intensity 6, dull + shiny hot orange ff/cd/57 at 3. fp_material_view
        # --illum: 4 lit FP triangles, all body. Lines thickened 1 px (no bloom in Halo 1)
        # TEST 3 (user, screenshot circles 1 + 2): the side lines ARE lit in Halo 1 (the built
        # map keeps 557 of 565 lit texels through DXT1, mean G 175) but read as nothing: a
        # few texels at colour x1. Halo 3: intensity 6 + bloom -> PALE and 2 px thicker
        'illum_dilate': 2,
        'glow': {'bolt_thrower': PALE, 'bolt_thrower_dull': AMBER, 'bolt_thrower_shiny': AMBER},
        # TEST 1 (user): 'no glowing effects on the weapon in FP or world model' -- the lit
        # texels sit on the two barrel MUZZLE faces (facing forward, away from the camera), two
        # side slots (x 10.4 cm), two small faces by the drum and two rear blade bits (shiny);
        # Halo 3 shows them by bloom only. User: MAKE THEM VISIBLE -> GLOW CARDS on just the
        # lit triangles (h1_h3_weapon_model.lit_pieces; a material island would light the
        # whole body), same UVs, textured with Halo 3's OWN illum mask (grey, thickened 1 px)
        # as an additive glow in the shader's colour: exactly Halo 3's lit spots, brighter
        # TEST 2 (user): 'no visible glow; the glow inside the MUZZLE on the 3D model looks like
        # two squares plastered onto it' -- the Beam Rifle's early flat-card problem. Halo 3's
        # glow is the two muzzle BORES (the user saw it there in Halo 3's model); the side /
        # rear faces hold a few lit texels on large faces (a card lights the whole face). Now
        # the Beam Rifle's FINAL recipe on the bores only: a radial card per bore (colour
        # falling to nothing at the edge, no white core), x1.3, the blue of Halo 3's body
        # TEST 3 (user): 'you identified small glowing parts that are not on the muzzle, and now
        # say they don't exist?' -- my error: fp_material_view's 6x6 / 15% sampling missed
        # thin lit lines on larger faces; EXACT coverage on the built model's UVs marks them
        # where the user circled them in Halo 3 (side line, dot -- mirrored on the far side).
        # They are lit by the base shader (PALE, 2 px, above). Circle 3, the white TRAPEZOID,
        # is a 2-triangle WINDOW of the blade material (no lit texel: Halo 3 draws it bright
        # with its chrome): a FLAT additive card in PALE (a lit window, not a radial gem)
        'glow_shaders': {'spiker_glow_blue': {'rgb': PALE, 'additive': True, 'islands': True,
                                              'islands_of': 'bolt_thrower', 'lit': ILLUM,
                                              'normal': (1.0, 0.0, 0.0), 'min_dot': 0.7,
                                              'radius': 1.0, 'falloff': 1.6, 'hot': False, 'gain': 1.0},
                         'spiker_window': {'rgb': PALE, 'additive': True},
                         # TEST 4 (user): 'the side parts not yet'. fp_material_view --texels:
                         # under Halo 1's UVs Halo 3's side lights are a FLECK of a few texels
                         # (circle 1; circle 2 smaller) -- right, but invisible without bloom.
                         # A radial HALO card per lit-texel cluster (the Beam Rifle's gem halo,
                         # placed on the spot, not over the face)
                         # TEST 5 (user): 'side glows visible now' -- A/B: A brightness 50%, B
                         # size 50%. TEST 6 (user): 'B looks better, zoom hides the glow' (FP
                         # geometry: hidden with the FP model when zoomed) -> full brightness,
                         # size 0.4 (below)
                         'spiker_spot': {'rgb': PALE, 'additive': True, 'radial': True,
                                         'falloff': 1.6, 'gain': 1.0}},
        'glow_spots': [{'material': 'bolt_thrower', 'illum': ILLUM, 'shader': 'spiker_spot',
                        'size': 0.4, 'lift': 0.05, 'merge': 0.4, 'skip_normal': (1.0, 0.0, 0.0),
                        # the faces are nearly edge-on to the FP camera (render): a second card
                        # per spot facing back along the gun (-x), where the camera looks from
                        'face': (-1.0, 0.0, 0.0)}],
        'glow_cards': {'window': {'of': 'bolt_thrower_shiny', 'shader': 'spiker_window',
                                  'near': ((0.8, 0.0, 3.3), 0.5), 'scale': 1.0, 'lift': 0.03},
                       'bolt_thrower': {'shader': 'spiker_glow_blue', 'lit': ILLUM,
                                        'normal': (1.0, 0.0, 0.0), 'min_dot': 0.7,
                                        'scale': 1.3, 'lift': 0.05}},
        'template': r'weapons\assault rifle\fp\shaders\gun',
    },

    # FP animations (h1_fp_retarget.py). Halo 3 spike rifle (single-wield) frames: idle 89,
    # posing var1 115, ready 20, put_away 5, fire_1 var1 8, melee 36 (primary_keyframe 4),
    # reload empty / full var1 56 each (primary_keyframe 30), throw_grenade 41. DUAL-WIELDABLE:
    # the graph holds a second (dual) resource group -- the (group, member) keying (Pilot A1)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\rifle\fp_spike_rifle\fp_spike_rifle.model_animation_graph',
        'render_model': H3 + r'\fp_spike_rifle\fp_spike_rifle.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in
                  ('gun', 'ammo_drum', 'barrel_1', 'barrel_2', 'clamp_left', 'clamp_right', 'slide')},
        'h1_dir': r'weapons\spiker\fp',
        'h1_model': r'weapons\spiker\fp\fp',
        'align': 'same_space',
        # the SMG's placement (user's pick, A1), tuned in test 1
        'view_offset': (-0.0225, 0.0, -0.0225),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:reload_empty:var1': 'first-person reload-empty',
            'first_person:reload_full:var1': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py brute_spiker). Levels = the stock Halo 1 AR sound
    # each stands in for (the SMG's measurements, MCC sounds_adpcm.fsb 2026-10-07): AR fire
    # -13.0, ar_reload -20.9, ar_melee -16.2, AR weapon ready -13.1, pistol_posing -26.5, drop
    # (assault_impact) -20.7, ar_ammo -24.9. Halo 3's spike rifle fire is a ONE-SHOT sound a
    # round (6 permutations, 1.7-3.1 s with the tail): no loop to slice (the SMG's `shots`).
    # Halo 3's single-wield FP cues: ready, melee, posing var1, reload_full (both reloads)
    'sounds': {
        'catalog': 'Spike Rifle',
        'dir': B.join(['sound', 'weapons', 'spiker_port']),
        'h3_dir': 'data\\sound\\weapons\\spike_rifle\\',
        'sounds': {
            'sk_fire': (['spike_rifle_fire'], 'sound\\sfx\\weapons\\assault rifle\\fire', -13.0),
            'sk_reload': (['fp_spike_rifle\\fp_spike_rifle_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            # the BALANCED reload's sound (the patcher retimes the reload x1.5, then swaps it in)
            'sk_reload_balanced': (['fp_spike_rifle\\fp_spike_rifle_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            'sk_ready': (['fp_spike_rifle\\fp_spike_rifle_ready'], 'sound\\sfx\\weapons\\assault rifle\\weapon ready', -13.1),
            'sk_melee': (['fp_spike_rifle\\fp_spike_rifle_melee'], 'sound\\sfx\\weapons\\weapon_anims\\ar_melee', -16.2),
            'sk_pose': (['fp_spike_rifle\\fp_spike_rifle_posing_var1'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'sk_drop': (['spike_rifle_drops\\spike_rifle_drop'], 'sound\\sfx\\impulse\\weapon_drops\\assault_impact', -20.7),
            'sk_ammo': (['spike_rifle_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\ar_ammo', -24.9),
            # Halo 3's spiker names the SMG's dry fire as its empty effect (sound\weapons\smg\
            # dryfire): its own copy here (AR dryfire -17.6, as the SMG's)
            'sk_dryfire': (['data\\sound\\weapons\\smg\\dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
        },
        'stretch': {'sk_reload_balanced': 1.5},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only brute_spiker) on a COPY of the Halo 1 Assault
    # Rifle. DEFAULT = HALO 3's OWN NUMBERS (PORTING "Balance"); the ratio values are the
    # balance rows (yardstick['balanced']). STEP 6: the template's magazine names `powerups\
    # assault rifle ammo`, so Halo 1's AR ammo tops the spiker up (Halo 3's spiker takes the
    # SMG ammo item, 120 rounds -- the source value)
    'pickable': {
        'weapon': SK + 'spiker',
        'template': AR + 'assault rifle',
        'world_model': SK + 'spiker',
        'fp_model': SK + 'fp\\fp',
        'fp_anims': SK + 'fp\\fp',
        'label': 'sk',
        'teach': ('sk', 'hp'),
        'keys': {'first-person melee': 4},          # H3 melee_strike_1 primary_keyframe 4
        'sounds': {'first-person ready': SND + 'sk_ready',
                   'first-person posing': SND + 'sk_pose',
                   'first-person melee': SND + 'sk_melee',
                   'first-person reload-empty': SND + 'sk_reload',
                   'first-person reload-full': SND + 'sk_reload'},
        # own spike + damage (step 3): Halo 3 spike_shard 9 damage, 25 -> 17.5 wu/s, range 70,
        # air gravity 0.2 (the AR bullet 7.5, 80, 40, 0). Materials: the H1 AR bullet's
        # (both bullet_slow in Halo 3). Halo 1's AR bullet has air gravity 1.0 at 324 wu/s
        # (no visible drop); the spike's 0.2 at ~21 wu/s drops ~1.1 g over its 70 wu
        'bullet': {'projectile': (AR + 'bullet', SK + 'spike'),
                   'damage': (AR + 'bullet', SK + 'spike'),
                   'dmg': 9.0, 'velocity': (25.0, 17.5), 'range': 70.0,
                   'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.2,
                                   # STEP 4b (before boot 1). List 2 (ratio vs the H3 AR bullet
                                   # onto the H1 AR bullet): air damage range 5..15 x 60/40 on
                                   # the upper bound (lower 0 / 0 kept); water gravity 0.4 x 0.4/0.2
                                   'proj_attrs.physics.air_damage_range': (5.0, 22.5),
                                   'proj_attrs.physics.water_gravity_scale': 0.8,
                                   # list 3: the AR bullet starts its timer ON FIRST BOUNCE with
                                   # timer 0 -- a ricochet would end at the first bounce. Halo
                                   # 3's spike: when at rest, timer 1 s, detonates below 12 wu/s
                                   # (the H3 AR: immediately, 0, 0 -- a zero on one side: the
                                   # source values; balanced minimum velocity = a catalog row)
                                   'proj_attrs.detonation_timer_starts': 'when_at_rest',
                                   # TEST 1: the stuck spike lasts Halo 3's model-particle life
                                   # (4-5 s, fx\impact.effect), then VANISHES (user: no damage,
                                   # Halo 3 has no detonation effect / damage). Was 1 s
                                   'proj_attrs.detonation.timer': (4.0, 5.0),
                                   'proj_attrs.detonation.minimum_velocity': 12.0,
                                   # flags by NAME (the Beam Rifle's rule): Halo 3's spike has
                                   # 'oriented along velocity' (Halo 1 has it) and 'no impact
                                   # effects on bounce' (Halo 1 has none: the reflect below gets
                                   # no effect). NOT set: 'AI must use ballistic aiming' -- Halo
                                   # 3's spike lacks it too (watch the Armed boot)
                                   'proj_attrs.flags.oriented_along_velocity': True},
                   # the RICOCHET (Halo 3: bounce at 0-60 deg, 20-30 wu/s, chance 1, never
                   # against units; parallel 0.35 / perpendicular 0.7 friction, 4 deg noise).
                   # The velocity window is left open: the balanced spike runs 4x faster and a
                   # catalog row cannot reach a response block (approximation, recorded)
                   'reflect': {'materials': RICOCHET, 'angle_deg': (0.0, 60.0),
                               'parallel_friction': 0.35, 'perpendicular_friction': 0.7,
                               'noise_deg': 4.0, 'effect_from_default': False},
                   # TEST 1 (user): the spike STICKS (attach) and shows its model, the needle's
                   # recipe; the ricochet above stays the potential response on stone / metal
                   # TEST 3 A/B (user): stagger identical with attach (A) and test 1's body
                   # responses (B, secondary) -- enemies stagger after enough spikes either way:
                   # attach does not cost the damage response. Kept
                   'default_responses': {'attach': ATTACH, 'disappear': DISAPPEAR},
                   'model': r'weapons\spiker\spike model\spike model',
                   # TEST 2 (user): 'why not let them detonate (with no damage) like the
                   # needles?' -- the needle's burst (`needle detonate`: no damage part; the
                   # needle's damage is its attached detonation damage, which the spike lacks)
                   # minus the pink crystal debris, flash + flare in the spike's red-orange,
                   # smoke and scorch decal kept. SILENT: the needle's `expl` would be a BORROW
                   # and Halo 3's spike has no detonation sound (asked the user)
                   'detonation_effect': {'from': r'weapons\needler\effects\needle detonate',
                                         'out': SK + 'effects\\spike detonate',
                                         'drop_particles': ('needler spike debris',),
                                         'tint_match': ('flash h pistol detonate', 'flare h stealth cannon'),
                                         'tint': ORANGE,
                                         # TEST 3 (user): 'the explosion is nice, could just be
                                         # reduced in size' -> every particle x0.5
                                         'scale': 0.5,
                                         'drop_parts': (r'sound\sfx\weapons\needler\expl',)},
                   # the LOOK: Halo 3's spike is a hot streak on every round -- the AR tracer's
                   # contrail recoloured orange (a tracer on every round: trigger below)
                   'contrail': {'from': AR + 'bullet', 'out': SK + 'spike', 'rgb': ORANGE}},
        # H3: 8/s (no ramp effect: 8 -> 8), rate ramp 1.0 / 0.2 (H3 AR 0: the source value).
        # Error ramp: no card covers it -- step 4b's ratio outright (the SMG's): H1 AR 0.6 x
        # 1.0/0.5 = 1.2 s to bloom, 1.0 x 0.2/0.5 = 0.4 s to settle
        'trigger': {'rounds_per_second': (8.0, 8.0), 'acceleration_time': 1.0,
                    'deceleration_time': 0.2, 'error_acceleration_time': 1.2,
                    'error_deceleration_time': 0.4,
                    # every round a tracer (the AR: 3 between). TEST 1 checks that 0 = all
                    'rounds_between_tracers': 0,
                    # 4b list 3: Halo 3's single-wield first-person offset (barrel 0 of 3; the
                    # other two are the dual-wield left / right) -- the spike leaves 5 cm right
                    # and 1 cm under the camera (Halo 1's AR: 0, from the camera)
                    'first_person_offset': (0.0, -0.05, -0.01)},
        'fields': {
            # STEP 4b list 2 (ratio vs the H3 AR onto the H1 AR): bounding radius 0.6 x 0.15/0.175
            'obje_attrs.bounding_radius': 0.6 * 0.15 / 0.175,
            # STEP 6, how much one pickup gives: Halo 3's spiker magazine item 120 (the SMG's)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 120,
            'weap_attrs.interface.pickup_sound.filepath': SND + 'sk_ammo',
            'item_attrs.collision_sound.filepath': SND + 'sk_drop'},
        # H3: minimum error 0, error angle 0.5 -> 1.25 (H1 AR 0, 2 -> 6.5). No barrel climb
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.5, 1.25)},
        # H3: 40 loaded, 120 at pickup, 160 most; reload time 2.0 (H3 AR 0: the source value)
        # over the 1.87 s animation
        'magazine': {'rounds_loaded_maximum': 40, 'rounds_reloaded': 40,
                     'rounds_total_initial': 120, 'rounds_total_maximum': 160,
                     'reload_time': 2.0},
        # H3 aim assist, absolute (balanced = the ratio rule)
        'aiming': {'autoaim_angle': 5.0, 'autoaim_range': 12.0,
                   'magnetism_angle': 12.0, 'magnetism_range': 18.0},
        'sound_effects': {
            # Halo 3's spiker flash = muzzle_flash_long + muzzle_flash_round, on-axis: the AR's
            # off-axis ring sprites dropped and the SMG's test-2 placement as the start
            'firing_effect': (AR + 'effects\\fire bullet', SK + 'effects\\fire spike',
                              {r'sound\sfx\weapons\assault rifle\fire': SND + 'sk_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.0,
                               # TEST 1 (user): 'move the muzzle effect up 0.5 units' (1 unit
                               # = 0.01 wu): z 0.01 -> 0.015
                               'shift': (0.01, 0.0, 0.015),
                               # TEMPLATE DIFF (before boot 1): the AR ejects a casing with
                               # the pistol's eject sound; a spike has no casing (Halo 3's
                               # spiker effect has none) -- both dropped
                               'drop_particles': ('casing',),
                               'drop_parts': (r'sound\sfx\weapons\pistol\eject',)}),
            'empty_effect': (AR + 'effects\\empty', SK + 'effects\\empty',
                             {r'sound\sfx\weapons\assault rifle\dryfire': SND + 'sk_dryfire'})},
        # the BLADE (Halo 3 cut_melee 72; the AR's strike_melee 70): DEFAULT = Halo 3's 72 as
        # the copy's mean (the AR's 50..60 spread kept: 65.5..78.5); balanced 56.6 = 55 x 72/70
        'melee': (AR + 'melee', SK + 'melee'),
        'melee_dmg': 72.0,
        'melee_response': AR + 'melee_response',
        'messages': ('Picked up a spike rifle', 'Picked up %d rounds for spike rifle'),
        'icon': 'spiker',
        'extra_sounds': [SND + 'sk_reload_balanced'],      # unused until the balanced retime
        # the AR's HUD with Halo 3's spike rifle reticle (H3 hud_reticles #2) at the reserved
        # 23, a magazine meter drawn for 40 (default) and 75 (balanced)
        'hud': {'donor': AR + 'assault rifle', 'out': SK + 'spiker',
                'reticle': ('hud_reticles', 2, 'spiker'),
                'reticle_thicken': 1,
                'ammo_meter': {'sizes': (40, 75), 'base': SK + 'bitmaps\\spiker_ammo'}},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py brute_spiker). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the AR ratio rule (step 4a, user 2026-10-08).
    # Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Spike Rifle', 'source': 'Halo 3', 'donor': 'Assault Rifle', 'default_on': False,
            'desc': "Halo 3's Spike Rifle: its model, first-person animations, sounds and numbers. "
                    "A 40-round Brute automatic firing slow, arcing spikes that ricochet off "
                    "metal and rock, with a blade for melee; Assault Rifle ammo tops it up.",
            'balance_desc': "Measured against the Assault Rifle, which both games have: 12 "
                            "damage per spike at 12 a second, a 75 magazine, 300 at pickup / "
                            "375 most, a 2.8 s reload, a wider spray, faster spikes and Halo "
                            "1-style aim assist; the arc and the ricochet stay Halo 3's.",
            # step 9: the balanced reload, H1 AR 87 fr x 56/58 = 84 fr over the BUILT 56 =
            # x1.5; swap (ONE multiplier, the ready's): H1 AR ready 29 fr x 20/20 over the
            # built 20 = x1.45 (the SMG's)
            'anims': {'reload': 1.5, 'swap': 1.45},
            'anim_sounds': {'reload': {'mult': 1.5, 'from': SND + 'sk_reload',
                                       'to': SND + 'sk_reload_balanced'}},
            'balance': [
                row('jpt!', SK + 'spike', 'Damage Lower Bound', 12.0, 9.0, 'Spike Damage'),
                row('jpt!', SK + 'spike', 'Damage Upper Bound', 12.0, 9.0, 'Spike Damage'),
                row('jpt!', SK + 'spike', 'Damage Upper Bound Max', 12.0, 9.0, 'Spike Damage'),
                row('weap', SK + 'spiker', 'Rounds Per Second', 12.0, 8.0, 'More Shooting', block='Triggers'),
                row('weap', SK + 'spiker', 'Rounds Per Second Max', 12.0, 8.0, 'More Shooting', block='Triggers'),
                row('weap', SK + 'spiker', 'Rounds Loaded Maximum', 75.0, 40.0, 'Magazine', block='Magazines'),
                row('weap', SK + 'spiker', 'Rounds Reloaded', 75.0, 40.0, 'Magazine', block='Magazines'),
                row('weap', SK + 'spiker', 'Rounds Total Initial', 300.0, 120.0, 'Magazine', block='Magazines'),
                # the DUAL-WIELD CARRY RULE: 600 x 160/384 x 1.5 = 375
                row('weap', SK + 'spiker', 'Rounds Total Maximum', 375.0, 160.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced (the SMG rule): Halo 3's own pickup : initial (120 : 120) on
                # the balanced initial 300 = 300. Default: Halo 3's 120
                row('weap', SK + 'spiker', 'Rounds', 300, 120, 'Ammo pickup', block='Magazines/Magazines'),
                # the minimum's own ratio degenerates (0.5/0.1 x 2 = 10): the maximum's 6.5/3.0
                row('weap', SK + 'spiker', 'Error Angle', 1.08, 0.5, 'Error Angle', block='Triggers'),
                row('weap', SK + 'spiker', 'Error Angle Max', 2.71, 1.25, 'Error Angle', block='Triggers'),
                row('proj', SK + 'spike', 'Initial Velocity', 101.25 / 30, 25.0 / 30, 'Projectile'),
                row('proj', SK + 'spike', 'Final Velocity', 70.875 / 30, 17.5 / 30, 'Projectile'),
                # the spike detonates below 12 wu/s (Halo 3): x 324/80 with the speed = 48.6
                row('proj', SK + 'spike', 'Minimum Velocity', 48.6 / 30, 12.0 / 30, 'Projectile'),
                row('weap', SK + 'spiker', 'Autoaim Angle', 6.0, 5.0, 'Autoaim'),
                row('weap', SK + 'spiker', 'Autoaim Range', 20.0, 12.0, 'Autoaim'),
                row('weap', SK + 'spiker', 'Magnetism Angle', 14.4, 12.0, 'Magnetism'),
                row('weap', SK + 'spiker', 'Magnetism Range', 22.5, 18.0, 'Magnetism'),
                # the blade: 55 x 72/70 = 56.6 as the copy's mean (the AR's 40 / 50..60 spread
                # x 56.6/55); default Halo 3's 72 (x 72/55)
                row('jpt!', SK + 'melee', 'Damage Lower Bound', 41.16, 52.36, 'Melee Damage'),
                row('jpt!', SK + 'melee', 'Damage Upper Bound', 51.45, 65.45, 'Melee Damage'),
                row('jpt!', SK + 'melee', 'Damage Upper Bound Max', 61.75, 78.55, 'Melee Damage'),
                # the 75 magazine's meter: spiker_ammo sequence 1 (ammo_meter 40 75), step 255 //
                # 75 = 3 (default 255 // 40 = 6); flash at 10 x 75/60 = 12 (default 7)
                dict(row('wphi', SK + 'spiker', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SK + 'spiker', 'Alpha Multiplier', 3, 6, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SK + 'spiker', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', SK + 'spiker', 'Loaded Ammo Cutoff', 12, 7, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port brute_spiker): the source pair (H3 spiker vs the
    # yardstick, H3 AR) against the target pair (the H1 port vs its template = the H1 AR)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\spike_rifle.weapon', r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
                   'projectile': (H3 + r'\projectiles\spike_shard\spike_shard.projectile',
                                  r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\spike_rifle_spike.damage_effect',
                                     r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect')},
        'target': {'weapon': (SK + 'spiker.weapon', AR + 'assault rifle.weapon'),
                   'projectile': (SK + 'spike.projectile', AR + 'bullet.projectile'),
                   'damage_effect': (SK + 'spike.damage_effect', AR + 'bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), the spiker as the primary
    # with Halo 3's own loadout (40 loaded, 120 in all)
    'test': {'level': 'a30', 'rounds': (40, 120), 'grunt': None, 'elite': None},
})

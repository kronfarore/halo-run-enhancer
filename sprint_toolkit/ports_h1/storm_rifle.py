r"""Storm Rifle (Halo 4, wave C1 -- the PILOT of the Halo 4 route): a HEAT automatic plasma rifle on a
battery, on a copy of the Halo 1 PLASMA RIFLE (the template: its heat / battery HUD, gauge, bolt,
overheat states); the yardstick is the PLASMA PISTOL (step 4a, user). The Plasma Repeater
(plasma_repeater.py) is the nearest shape.

THE HALO 4 SOURCE (`h4:` paths, h4_tags.py): H4EK's export is Halo 3-shaped (the Halo 3 readers run
unchanged); bitmaps decode by the pixel blob's end check (multi-image tags: the 10 Covenant digits,
the 7 heat stages); the FP graph is COMPRESSED-ONLY -> decoded through Foundry in Blender
(h4_fp_dump.py) and the arms RE-SOLVED on Halo 1's lengths (h1_fp_retarget._resolve_arms).

HALO 4's HEAT (h3_weapon_values --kit h4, 2026-10-13): 0.09 a round, loss 0.55/s, 0.3/s overheated,
recovery 0.1, warning 0.8. Halo 4 DRAINS heat while the trigger is held (user's correction relayed
2026-10-13: the old 'cools only while not firing' rule was wrong) -> it overheats on the 27th bolt
(~2.6 s at 10/s: 0.09 - 0.055 a bolt). Halo 1 also cools while firing (B3) but has ONE loss:
approximation A' (user, after the correction) -- loss 0.3 (Halo 4's 3.0 s overheat lockout to 0.1
kept), heat fitted 0.0665 a round (the 27th bolt again); cooling between bursts 0.3/s (Halo 4: 0.55).
Boots 1-2 ran the first fit A (0.1125: the 12th bolt, built on the wrong rule). The MANUAL VENT (Halo 4's reload: vent_enter / loop / exit) has no
Halo 1 counterpart: the overheat is the vent (B3's precedent)."""
from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_assault_carbine'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_assault_carbine\storm_fp_assault_carbine'
SBM = SW + r'\bitmaps\storm_assault_carbine_default' + B
ST = 'weapons\\storm rifle\\'
STR = r'ui\hud\weapons\covenant\assault_carbine\bitmap' + B    # Halo 4's crosshair art (CUI)
SND = 'sound\\weapons\\storm_rifle_port\\'
PR = 'weapons\\plasma rifle\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

# the Halo 4 FP skeleton (84 nodes, h4_tags.h3_name) less what Halo 1's 37-node arms lack: the
# pedestal / aim nodes above base, every helper / fixup / twist / armour bone, the grips, the left
# hand's marker offset and the pinky metacarpals (pinky_low is solved off the hand directly)
DROP = (['pedestal', 'aim_pitch', 'aim_yaw'] +
        ['%s_%s' % (s, n) for s in 'lr' for n in
         ('shoulder_helper1', 'shoulder_helper2', 'shoulder_helper3', 'shoulder_helper4',
          'shoulder_fixup', 'upperarm_fixup', 'forearm_helper1', 'forearm_helper2',
          'forearm_helper3', 'forearm_helper4', 'forearm_fixup', 'elbow_fixup', 'elbow_armor',
          'hand_twist', 'wrist_fixup', 'grip', 'pinky0')] +
        ['r_hand_helper1', 'r_hand_helper2', 'r_hand_helper3', 'r_hand_helper4',
         'l_hand_marker_offset'])

PORT = reserved(
    order=26, wave='C1', name='Storm Rifle', source='Halo 4',
    messages=(85, 86), icon=46, reticle=35, label='st', teach_from='pr',
    sound_dir='sound\\weapons\\storm_rifle_port', weapon_dir='weapons\\storm rifle',
    yardstick={
        # step 4a (user, 2026-10-13; h1_role_compare.py storm_rifle)
        'pick': 'Plasma Pistol',
        'reason': ("the only heat-based plasma weapon both games have (Halo 4 has NO plasma rifle). "
                   "Wave C keeps the rule: DEFAULT = Halo 4's own numbers, BALANCED = the ratio "
                   "rows. Halo 1 approximation A' for the one heat loss (user): 0.3 = Halo 4's "
                   "overheated loss, heat a round fitted so it overheats on the 27th bolt as Halo 4 "
                   "does (both games drain heat while firing; Halo 4 has two losses). The pistol is TAPPED: its rate gives no ratio -> "
                   "Halo 4's 10/s. Materials: the template (plasma rifle) bolt table in DEFAULT; "
                   "BALANCED = the plasma pistol bolt's table x Halo 4's plasma_fast / plasma_slow "
                   "(shields x0.625, Elite / cyborg body x2.5). The ratio's battery is degenerate "
                   "(Halo 4's plasma pistol has 50 shots -> 1667) -> Halo 4's own 167 kept (B5's "
                   "keep-the-source rule)"),
        # DEFAULT = Halo 4's own numbers; BALANCED (H1 plasma pistol x Storm Rifle / H4 plasma
        # pistol). Halo 4: storm 8 plasma_fast, 10/s, heat 0.09, loss 0.55 / 0.3, rec 0.1, battery
        # 0.006, 50 wu/s, range 100, error 0.5 -> 2.75, aim (mode block) 5/15 10/20; plasma pistol
        # 14 plasma_slow tapped, heat 0.18, loss 0.6 / 0.45, rec 0.1, battery 0.02, 20 -> 30 wu/s,
        # range 40, aim 4/20 8/20. H1 plasma pistol 18 (16-20), heat 0.16, loss 0.65, rec 0.25,
        # battery 0.002, 25 -> 15 wu/s, range 50, aim 5/20 12/20
        'balanced': {
            'damage': 10.29,             # 18 x 8/14
            'rate': (10.0, 10.0),        # tapped yardstick: Halo 4's own
            'heat_per_round': 0.0639,    # 0.16 x 0.09/0.18 = 0.08, losses 0.596 / 0.433 draining: 47 bolts -> fitted on the one 0.433
            'loss': 0.433,               # 0.65 x 0.3/0.45 (the overheated losses: approximation A)
            'recovery': 0.25,            # 0.25 x 0.1/0.1
            'battery': 0.006,            # degenerate ratio (0.0006) -> Halo 4's own
            'velocity': (62.5, 62.5),    # 25 x 50/20 (Halo 4's bolt has no speed change)
            'range': 125.0,              # 50 x 100/40
            'aim': (6.25, 15.0, 15.0, 20.0),  # 5 x 5/4, 20 x 15/20; 12 x 10/8, 20 x 20/20
            'materials': 'PP bolt table x plasma_fast / plasma_slow',
            'melee': None},              # Halo 4 shares strike_melee: x1
        'measured': 'h1_role_compare.py storm_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine',
            'provisional': 'Plasma Pistol',
            'alternatives': ['Assault Rifle', 'Needler', 'Elite carrier (= Plasma Rifle)'],
            'direct': None,
            'peers': ['Plasma Rifle', 'Assault Rifle', 'Needler', 'Plasma Repeater (port)'],
            'why': 'heat-based automatic plasma bolt; Halo 4 has no Plasma Rifle, so the Plasma Pistol is the only heat plasma weapon in both',
            'lacks': ("the manual vent on reload (and venting part-way: the overheat stands in), "
                      "cooling only while not firing (Halo 1 cools while firing: the heat a round "
                      "fitted), two heat losses (Halo 1 one: the overheated one kept)")}},
    # step 11: Halo 4's ai\generic Storm Rifle entry (m020) over a base -- 'st' has no carrier. Halo
    # 1's PLASMA RIFLE carriers (h1_weapon_carriers, 2026-10-13): Elite minor / major / stealth
    # 0.5, commander / spec-ops 0.6, Flood combat (both) 0.4, Marines 0.5, armoured Marines 0.6 --
    # the Elite carries the Storm Rifle in Halo 4 where it carries the plasma rifle in Halo 1. Donor
    # = the ELITE MINOR plasma rifle (B3's choice: one donor for every slot). WDM RULE: 0.5 x the
    # YARDSTICK's player dps (the plasma pistol tapped 5/s x 18 = 90, h1_role_compare storm_rifle) /
    # the port's (default 8 x 10 = 80, balanced 10.29 x 10 = 103)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine',
                    'donor_weapon': 'weapons\\plasma rifle\\plasma rifle',
                    'donor_variant': 'characters\\elite\\elite minor\\elite minor plasma rifle',
                    'wdm_rule': {'base': 0.5, 'yardstick_dps': 90.0, 'port_dps': 80.0,
                                 'balanced_port_dps': 103.0},
                    # THE BALANCED DROP RULE: Halo 1's plasma-pistol carriers drop 0.7 - 0.9 (9 of 11
                    # actor variants) x Halo 4 storm rifle 0.5 - 0.9 / Halo 4 plasma pistol 0.7 - 0.9
                    # (m020 ai\generic) = 0.5 - 0.9: the default's own values
                    'balanced_set': ['0x1D8=0.5:Drop Weapon Loaded', '0x1DC=0.9:Drop Weapon Loaded Max']},
)

PORT.update({
    'status': 'in_progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). Halo 4's ONE render model for
    # world AND first person: 4 nodes -- b_gun (root, identity: not tilted), b_cannister, b_top_vent,
    # b_bottom_vent; 1 mesh (10934 verts, 12 parts). Markers: ONE primary_trigger (0.301 / 0 /
    # 0.027), left_hand, fx_vent (the muzzle vent), fx_gas_vent x2, cannister_vent, muzzle_brake x2.
    # Materials (H4 .material): metal / shell (diff + control + normal), glow (self-illum teal 0, 1,
    # 0.73 through the control map), cac_display_base / _wire / _heat (constant METERS on heat: the
    # heat panel's 7 stages `buildup`), cac_overheat (the overheat chevron, by `overheated`),
    # covglyph_ones / _tens (the battery COUNTER: 10 Covenant digits by primary_ammunition)
    'model': {
        'dir': r'weapons\storm rifle',
        'world': H4 + SW + r'\storm_assault_carbine.render_model',
        'fp': H4 + SW + r'\storm_assault_carbine.render_model',
        'world_name': 'storm rifle',
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent', 'primary_trigger': 'primary trigger'},
        # the plasma rifle template fires through TWO markers (its upper / lower firing effects);
        # Halo 4's one muzzle carries both
        'extra_markers': [('primary trigger1', 0, (0.3008, 0.0, 0.0268), (1.0, 0.0, 0.0, 0.0))],
        'ground_point': 'auto',
        # BOOT 1 (user: 'the world model does not render'): the weapon kept the TEMPLATE's hull
        # (the plasma rifle's, other nodes) -- an own hull (h1_box_collision.py) from the world
        # model's extent (x -0.098..0.294, y +-0.024, z -0.027..0.074): body + grip, as the Plasma
        # Repeater's
        'collision': {'material': 'metal',
                      'boxes': [((-0.098, -0.024, 0.0), (0.294, 0.024, 0.074)),
                                ((-0.02, -0.015, -0.027), (0.05, 0.015, 0.0))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name: every
        # `storm_assault_carbine_default_c...` read as ONE name (it looped on the type prompt) -> short
        # Halo 1 names (`material_names`), the shaders / bitmaps keyed by them
        'material_names': {'storm_assault_carbine_default_' + k: 'st_' + v for k, v in (
            ('metal', 'metal'), ('shell', 'shell'), ('glow', 'glow'),
            ('cac_display_base', 'display_base'), ('cac_display_wire', 'display_wire'),
            ('cac_display_heat', 'display_heat'), ('cac_overheat', 'overheat'),
            ('covglyph_ones', 'glyph_ones'), ('covglyph_tens', 'glyph_tens'))},
        'shaders': {'st_metal': (H4 + SBM + 'storm_assault_carbine_default_diff.bitmap', None),
                    'st_shell': (H4 + SBM + 'storm_assault_carbine_default_diff.bitmap', None)},
        'template': PR + r'fp\shaders\gun',
        'glow': {},
        # the glow lights (Halo 4: srf_char_blinn_selfillum, si teal 0, 1, 0.73 x20 through the
        # control map): an additive radial glow per UV island (the Plasma Repeater's pilot)
        # THE OVERHEAT CHEVRON (Halo 4: srf_blinn_selfillum, overheat image 0, si 1, 0.78, 0.18 x5,
        # by `overheated`): additive, its brightness = A out (pickable: function 0 = C in =
        # overheated)
        'glow_shaders': {'st_glow': {'rgb': (0.0, 1.0, 0.73), 'additive': True, 'islands': True,
                                     'islands_of': 'storm_assault_carbine_default_glow'},
                         'st_overheat': {'rgb': (1.0, 0.78, 0.18), 'additive': True, 'size': 64,
                                         'mask': H4 + SBM + 'overheat.bitmap', 'fade_source': 'A_out'}},
        # THE ON-GUN DISPLAY (Halo 4: three srf_constant_meter layers on `heat`): the HEAT PANEL fills
        # bottom-up through 7 stages (`buildup`: stage k lit at heat k/6, si red 1, 0, 0) -> ONE
        # meter whose threshold per texel = the first stage it is lit in (`stages`), on B out (=
        # heat, the template's gauge input); the dim teal BASE (si 0, 0.26, 0.21) and bright WIRE
        # outline (si 0, 1, 0.45) as lit shapes (Halo 4 tints them by heat: not reproduced)
        'meters': {
            # BOOT 2 (user: 'the heat gauge starts with the first section already lit'): B out =
            # heat FLOORED at 0.1 (B3's probe) and stage 1's threshold was 0.08 -> the stages
            # remapped onto 0.1..1 (`value_floor`)
            'st_display_heat': {'map': H4 + SBM + 'buildup.bitmap', 'stages': True, 'value_floor': 0.1,
                                'from': PR + r'fp\shaders\gauge', 'value': 'B_out',
                                'color': (1.0, 0.2, 0.1), 'color_off': (0.1, 0.02, 0.01)},
            'st_display_base': {'map': H4 + SBM + 'cac_display_base.bitmap', 'from': PR + r'fp\shaders\gauge',
                                'shape': 'g', 'gradient': 0.0,
                                'static': r'weapons\needler\shaders\needler luminous',
                                'color': (0.0, 0.26, 0.21)},
            'st_display_wire': {'map': H4 + SBM + 'cac_display_wire.bitmap', 'from': PR + r'fp\shaders\gauge',
                                'shape': 'a', 'gradient': 0.0,
                                'static': r'weapons\needler\shaders\needler luminous',
                                'color': (0.0, 1.0, 0.45)}},
        # THE BATTERY COUNTER (Halo 4's material covglyph_ones / _tens: the 10 Covenant numerals by
        # primary_ammunition_ones / _tens) -- BOOT 2 (user): 'there is no on-gun counter in the
        # original, safe to disable' (Halo 4's colour map is `counter_hide`, a 1 x 1 placeholder: the
        # counter never draws there). Its two quads DROPPED; boot 2's numeric shader with Halo 4's
        # digits (`numeric` 'digits', glyph in RGB + alpha) worked and stays a tool feature
        'drop_materials': ('storm_assault_carbine_default_covglyph_ones',
                           'storm_assault_carbine_default_covglyph_tens'),
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's OWN storm_fp_assault_carbine (user,
    # 2026-10-13), decoded by Foundry (h4_fp_dump.py), the arms RE-SOLVED. 37 animations: fire_1
    # var1/var2 (10 fr), idle 100, posing var1 96 / var2 89, ready 19 (ready_initial 30), put_away 6,
    # melee_strike_1 34 (+ _overheated 39 / _vent 34), throw_grenade 44 (+ _overheated / _vent),
    # moving 22 (overlay), look 9 (overlay), THE OVERHEAT overheating 59 / overheated 30 / o_h_exit 37
    # (= Halo 1's own three states), the manual vent vent_enter 21 / loop 30 / exit 13 (not used:
    # no manual vent in Halo 1), sprint / jump / land (no Halo 1 state)
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_assault_carbine.render_model',
        'nodes': {'gun': 'frame b gun', 'cannister': 'frame b cannister',
                  'top_vent': 'frame b top vent', 'bottom_vent': 'frame b bottom vent'},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\storm rifle\fp',
        'h1_model': r'weapons\storm rifle\fp\fp',
        # BOOT 1 (user: 'one flicker in the overheat transition, the hand disappears and returns'):
        # Halo 4's `overheated` is NOT between overheating and o_h_exit -- overheating's end meets
        # o_h_exit's start within 0.08 cm, `overheated` sits 16-25 cm from every state (Halo 4 holds
        # overheating's end until it cools). And Halo 1 plays `overheated` ONCE: 1.97 + 1.0 s < the
        # 3.0 s lockout -> a frame of idle. Now: Halo 1's overheated = overheating's LAST frame held
        # 40 frames (the Sentinel Beam's hold), both joins seamless
        # BOOT 2 (user: 'the hold lasts a bit too long'): Halo 1 plays the exit only after the hold
        # -- 40 frames ran to 3.3 s; 31 = 1.97 + 1.03 s = the 3.0 s lockout
        'holds': {'first-person overheated': ('first_person:overheating', 31)},
        # BOOT 4 (user's melee video: 'hands phasing through the weapon'): the motion matches Halo
        # 4's own (its arms + gun rendered from b_camera_control, frame for frame) -- Halo 1's glove
        # and cuff are chunkier than Halo 4's slim hand and sink into the gun. Measured (hand
        # triangle centres inside the gun mesh, ray parity, every 3rd frame): right hand 2 cm to the
        # gun's right (-y): idle 2771 -> 32, melee 853 -> 132; left hand 1 cm down (-z): idle 243 ->
        # 52, fire 24 -> 5 (its melee contact is Halo 4's own: the hand off the gun)
        # BOOT 5 (user: 'idle was fine before, the fidget better now; the melee: the right hand does
        # not grip the handle, a finger stretched out') -- the offset lifted the right hand off the
        # handle in the melee (Halo 4's hand wraps it: rendered at 25 deg, frames 6-16). Now only
        # the FIDGET keeps it; every other animation sits on Halo 4's wrists
        'hand_offset_anims': {'first_person:posing:var1': {'r': (0.0, -0.02, 0.0), 'l': (0.0, 0.0, -0.01)}},
        'align': 'same_space',
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:overheating': 'first-person overheating',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
    },

    # Halo 4's own sounds (h1_port_sounds.py storm_rifle, `bank` 'halo4': the Wwise packages, the
    # SAW's route). Halo 4's first-person events live in the PLAYER bank assault_carbine_player
    # (the non-player assault_carbine holds the third-person ones). Cues (the graph's
    # frame_event_list): fire = play_weapons_storm_assault_carbine_player_fire, SIX layers at once
    # (h4_wwise HIRC: a random crack of 9 [2-10], body 1, sweetener 0 (1.6 s), body 14 (1.8 s), a
    # random tail of 3 [11-13], a 30 ms 6 kHz click 15 = haptics, dropped) -> Halo 1's one sound a
    # round = crack k + 1 + 0 + 14 + tail k (9 permutations); ready = switchto_mech + switchto_fly
    # @0; melee = foley_melee1; posing var1 = idle a @0, b @38, c @68 (`offsets`); overheating =
    # player_overheat + over_heat_a + over_heat_b @0; o_h_exit = over_heat_b + oh_foley_exit;
    # dry fire = player_dry_fire. Levels = the active RMS of the stock Halo 1 PLASMA RIFLE sound
    # each stands in for (the Plasma Repeater's h1_stock_sound_levels: fire -9.3, overheat / dry
    # -20.9, melee -11.4, oh_exit -20.0, overheating -26.7, posing -30.5, ready -21.2)
    'sounds': {
        'catalog': 'Storm Rifle',
        'bank': 'halo4',
        'wwise_bank': 'assault_carbine_player',
        'dir': B.join(['sound', 'weapons', 'storm_rifle_port']),
        'sounds': {
            'st_fire': (['play_weapons_storm_assault_carbine_player_fire:2,3,4,5,6,7,8,9,10',
                         'play_weapons_storm_assault_carbine_player_fire:1',
                         'play_weapons_storm_assault_carbine_player_fire:0',
                         'play_weapons_storm_assault_carbine_player_fire:14',
                         'play_weapons_storm_assault_carbine_player_fire:11,12,13'],
                        'sound\\sfx\\weapons\\plasma rifle\\fire', -9.3),
            'st_dryfire': (['play_wea_assault_carbine_player_dry_fire'],
                           'sound\\sfx\\weapons\\plasma rifle\\overheat', -20.9),
            'st_ready': (['play_wea_assault_carbine_switchto_mech_player',
                          'play_wea_assault_carbine_switchto_fly_player'],
                         'sound\\sfx\\weapons\\weapon_anims\\plasrifle_ready', -21.2),
            'st_melee': (['play_wea_assault_carbine_foley_melee1_player'],
                         'sound\\sfx\\weapons\\weapon_anims\\plasrifle_melee', -11.4),
            'st_pose': (['play_wea_assault_carbine_idle_player_a', 'play_wea_assault_carbine_idle_player_b',
                         'play_wea_assault_carbine_idle_player_c'],
                        'sound\\sfx\\weapons\\weapon_anims\\plasrifle_posing', -30.5),
            'st_overheat': (['play_wea_assault_carbine_player_overheat', 'play_wea_assault_carbine_over_heat_a',
                             'play_wea_assault_carbine_over_heat_b'],
                            'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'st_oh_exit': (['play_wea_assault_carbine_over_heat_b', 'play_wea_assault_carbine_oh_foley_exit_player'],
                           'sound\\sfx\\weapons\\weapon_anims\\plasrifle_oh_exit', -20.0),
            # the drop (fx\material_effects\weapons\assault_carbine: wea_drop_rifle_cv_assault_carbine,
            # in the player bank), the bolt's FLYBY (its projectile names sound\weapons\
            # impacts_riccs\plasma_flyby_reach -> bank proj_cov_whizby, 19 variants; the projectile's
            # own proj loop events are EMPTY in MCC's Halo 4), its IMPACT (the material effects'
            # wea_plasma_impact_dirt -> bank plasma_impact_generic, 8 variants; the storm-specific
            # impact events are in no MCC bank) -- levels: plasma_impact -18.7, plasrif_projectile
            # -26.2, plasmahit -11.3 (the Plasma Repeater's measurements)
            'st_drop': (['play_wea_drop_rifle_cv_assault_carbine_nonplayer'],
                        'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            'st_flyby': (['play_weapons_impacts_riccs_plasma_flyby_reach@proj_cov_whizby'],
                         'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            'st_impact': (['play_wea_plasma_impact_dirt@plasma_impact_generic'],
                          'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
        },
        'offsets': {'st_pose': [0.0, 38 / 30.0, 68 / 30.0]},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only storm_rifle) on a COPY of the Halo 1 PLASMA RIFLE
    # (the template: heat + battery HUD, gauge, bolt, overheat states; the yardstick is the
    # plasma pistol -- a template that is not the yardstick, the Beam Rifle's case). DEFAULT =
    # HALO 4's OWN NUMBERS through approximation A; the plasma-pistol ratio values are the
    # balance rows. Template layout: inputs A heat / B illumination / D age
    'pickable': {
        'weapon': ST + 'storm rifle',
        'template': PR + 'plasma rifle',
        'world_model': ST + 'storm rifle',
        'fp_model': ST + 'fp\\fp',
        'fp_anims': ST + 'fp\\fp',
        'label': 'st',
        'teach': ('st', 'pr'),
        # Halo 4's melee_strike_1 marks 'primary keyframe' 28 of 34 (after 'allow interruption'
        # 22: not the hit) -- the Reach repeater's 34-frame strike hits at 5 (its primary)
        'keys': {'first-person melee': 5},
        'sounds': {'first-person ready': SND + 'st_ready',
                   'first-person posing': SND + 'st_pose',
                   'first-person melee': SND + 'st_melee',
                   'first-person overheating': SND + 'st_overheat',
                   'first-person o-h-exit': SND + 'st_oh_exit'},
        # own bolt + damage (step 3). Halo 4: storm_assault_carbine_bolt 8 (lower = upper:
        # no falloff), plasma_fast, instantaneous acceleration 0.125, 50 wu/s flat, range 100.
        # Materials: the plasma rifle bolt's table (DEFAULT); balanced rows = the PLASMA PISTOL
        # bolt's table x Halo 4's plasma_fast / plasma_slow
        'bullet': {'projectile': (PR + 'bolt', ST + 'bolt'),
                   'damage': (PR + 'bolt', ST + 'bolt'),
                   'dmg': 8.0, 'velocity': (50.0, 50.0), 'range': 100.0,
                   'fields': {'damage.damage_upper_bound': (8.0, 8.0)},
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'st_flyby'},
                   # every response effect that plays plasmahit -> an own copy playing st_impact
                   'impact_tint': {'match': (), 'rgb': None, 'out': ST + 'effects\\impact\\',
                                   'sounds': {'sound\\sfx\\weapons\\plasma rifle\\plasmahit': SND + 'st_impact'}},
                   # THE HIT-EFFECT RULE: a 10/s weapon (max(default 10, balanced 10))
                   'impact_thin': {'materials': [22], 'out': ST + 'effects\\impact\\',
                                   'thin': {}, 'rate': 10.0}},
        # APPROXIMATION A' (user, after the drain correction): 10/s flat (boot 1's probe: 10.0/s, gaps
        # 100 ms), heat 0.0665 a round = the 27th bolt overheats with Halo 1 cooling 0.03 between
        # rounds (27 x 0.0665 - 26 x 0.03 = 1.016; 26 bolts 0.979), as Halo 4's 0.09 - 0.055 a bolt;
        # one loss 0.3 (Halo 4's overheated one: 1 -> 0.1 in 3.0 s, the probe 3.00 s), battery 0.006
        # (Halo 4's campaign = mp). Boots 1-2: fit A, 0.1125 (the 12th bolt: probe-confirmed)
        'trigger': {'rounds_per_second': (10.0, 10.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0, 'heat_generated_per_round': 0.0665,
                    'age_generated_per_round': 0.006,
                    # the FP muzzle in the idle (h1_fp_muzzle: the built FP model + animations)
                    'first_person_offset': (0.3654, -0.0403, -0.0306)},
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.3,
                 'illumination': 1.0},
        # the template's overheat steam aims at its `vent` (Halo 4's fx_vent, mapped in the model)
        'overheated_effect': {'from': PR + 'effects\\overheated', 'out': ST + 'effects\\overheated',
                              'locations': {}},
        # Halo 4's own spread (minimum error 0)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.5, 2.75)},
        # Halo 4 aim assist (the MODE block, the live one -- the H4 kit's Sentinel Beam drift
        # lesson), absolute
        'aiming': {'autoaim_angle': 5.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 10.0, 'magnetism_range': 20.0},
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Halo 4's FIRST-PERSON flash
        # (fx\firing.effect -> fx\parts\firing_1p, 'only in first person'): eight particle systems
        # ALL at primary_trigger, no offsets, bounding radius estimates 0.024-0.094 wu. The plasma
        # rifle's (h1_effect_particles): centre flash 0.06-0.075, a VERTICAL pair pitched +-120
        # deg at +-0.04 wu that Halo 4 lacks -> dropped (`drop_off_axis`, the Plasma Repeater's
        # recipe), forward 0.075-0.125 at +0.05 / +0.1, smoke 6-10; size kept (judged in game)
        'sound_effects': {
            'firing_effect': (PR + 'effects\\plasma rifle upper fire', ST + 'effects\\fire upper',
                              {'sound\\sfx\\weapons\\plasma rifle\\fire': SND + 'st_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012}),
            'firing_effect@1': (PR + 'effects\\plasma rifle lower fire', ST + 'effects\\fire lower',
                                {'sound\\sfx\\weapons\\plasma rifle\\fire': SND + 'st_fire'},
                                {'match': 'flash', 'drop_off_axis': 0.012})},
        'fields': {
            # the dead-battery click: the plasma rifle's empty is a SOUND reference
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'st_dryfire',
            # Halo 4 has no age penalties and never misfires (age misfire start / chance 0 / 0)
            'weap_attrs.age.heat_penalty': 0.0,
            'weap_attrs.age.rate_of_fire_penalty': 0.0,
            'weap_attrs.age.misfire_chance': 0.0,
            'weap_attrs.triggers.0.firing_effects.1.misfire_effect.filepath': '',
            'obje_attrs.bounding_radius': 0.3,
            'obje_attrs.collision_model.filepath': ST + 'storm rifle',
            'item_attrs.collision_sound.filepath': SND + 'st_drop',
            # STEP 4b (port_field_audit --port storm_rifle, before boot 1). List 2, no card: camo
            # ding 0.3 x 0.4/0.6, illumination recovery 0.15 x 0.1/0.05. KEPT: the bolt's water
            # damage range (Halo 4 0..10, its pistol 5..10: a zero on one side), the damage effect's
            # breaking-effect forward exponent (Halo 4 8 vs its pistol 0.2 -> 320: not Halo 1's
            # field). The rest of lists 2 / 4 / 5 = Halo 4's own numbers (default rule) or the
            # decisions above (functions, heat, age penalties, the FP offset)
            'weap_attrs.interface.active_camo_ding': 0.2,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.3,
            # the ON-GUN functions (glow 'st_overheat'): out A = overheated (function 0, the
            # template's colour wander, used by nothing of the port's; C in = overheated); out B
            # stays heat (the flares + the heat meter). BOOT 3 (user: 'a leftover sigil' = the
            # chevron lit at rest): function 3 was used first -- the template's carries INVERT
            # (1 - age), so it read 1 - overheated, and function 1 (B out) is 'turned off with' 3
            'weap_attrs.C_in': 'overheated',
            'obje_attrs.functions.0.function': 'one',
            'obje_attrs.functions.0.period': 0.0,
            'obje_attrs.functions.0.scale_function_by': 'C_in',
        },
        'melee': (PR + 'melee', ST + 'melee'),
        'melee_response': PR + 'melee_response',
        'messages': ('Picked up a storm rifle', 'Picked up %d rounds for storm rifle'),
        'icon': 'storm rifle',
        # the PLASMA RIFLE's HUD (heat + battery meters); the crosshair from Halo 4's CUI screen
        # (ui\hud\weapons\covenant\assault_carbine: four 16 x 16 ac_tick wedges 1 unit off the
        # centre, flipped per corner, opacity 0.9; the faint ring ac_circle 128 x 1.1 at 0.35) --
        # Halo 4's HUD art is 3 px a widget unit (48 -> 16, 384 -> 128)
        # Halo 4's HUD canvas is 1280 x 720 (the H4 kit's scope work): a unit = 1.5 px at 1080p --
        # the ring ~110 px across, the wedges 24 px. Layers in widget units (y down): each tick's
        # box centre (right boxes span 1..17 -> 9, left -18..-2 -> -10), the ring's (-0.5, -1) x1.1.
        # THE SUPERSAMPLE RECIPE (memory h1-reticle-supersample): F 2, scale 2.3 (the ring keeps a
        # ~10 px margin in the 512 cell), on-screen px = sheet px x 0.75 x overlay -> overlay =
        # 1.5 / (123/97 x 2.3 x 2 x 0.75)
        'hud': {'donor': PR + 'plasma rifle', 'out': ST + 'storm rifle',
                'reticle': (H4 + STR + 'ac_tick', 0, 'storm rifle'),
                'reticle_xform': {'offset': (9.0, -10.0), 'gain': 0.9},
                'reticle_layers': [(H4 + STR + 'ac_tick', 0, 1.0, {'flip_x': True, 'offset': (-10.0, -10.0), 'gain': 0.9}),
                                   (H4 + STR + 'ac_tick', 0, 1.0, {'flip_y': True, 'offset': (9.0, 9.0), 'gain': 0.9}),
                                   (H4 + STR + 'ac_tick', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (-10.0, 9.0), 'gain': 0.9}),
                                   (H4 + STR + 'ac_circle', 0, 1.1, {'offset': (-0.5, -1.0), 'gain': 0.35})],
                'reticle_split': 1,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 2.3, 'reticle_overlay': 1.5 / (123 / 97.0 * 2.3 * 2 * 0.75)},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py storm_rifle). DEFAULT = Halo 4's own
    # numbers in the tags (approximation A); BALANCED = the PLASMA PISTOL ratio (step 4a, user
    # 2026-10-13). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Storm Rifle', 'source': 'Halo 4', 'donor': 'Plasma Rifle', 'default_on': False,
            'desc': "Halo 4's Storm Rifle: its model, first-person animations, sounds and numbers. A "
                    "Covenant automatic on heat and battery: 10 bolts a second, overheating after "
                    "27 bolts (about 2.6 s) for a 3 s vent. 167 shots a battery.",
            'balance_desc': "Measured against the Plasma Pistol, the only heat plasma weapon both "
                            "games have: 10.3 damage a bolt (fast plasma: better on armour, worse on "
                            "shields than the pistol's), 47 bolts to overheat and a 1.7 s vent, a "
                            "faster bolt with more range and Halo 1-style aim assist.",
            # step 9 (swap, ONE multiplier): the H1 plasma pistol's ready 14 fr x Storm Rifle 19 /
            # Halo 4 plasma pistol 16 = 16.6 over the built ready 19 (no reload: a battery weapon)
            'anims': {'swap': 16.6 / 19.0},
            'balance': [
                # damage: 18 x 8/14 on Halo 4's 8 / 8
                row('jpt!', ST + 'bolt', 'Damage Lower Bound', 10.29, 8.0, 'Bolt Damage'),
                row('jpt!', ST + 'bolt', 'Damage Upper Bound', 10.29, 8.0, 'Bolt Damage'),
                row('jpt!', ST + 'bolt', 'Damage Upper Bound Max', 10.29, 8.0, 'Bolt Damage'),
                # materials: the plasma PISTOL bolt's table (cyborg 0.6 / 0.6 where the rifle bolt's
                # is 0.5 / 2.0) x Halo 4 plasma_fast / plasma_slow (shields x0.625, Elite and
                # Spartan body hard_metal_thin x2.5; flesh x1)
                row('jpt!', ST + 'bolt', 'Elite Energy Shield', 1.25, 2.0, 'Bolt materials'),
                row('jpt!', ST + 'bolt', 'Elite', 2.5, 1.0, 'Bolt materials'),
                row('jpt!', ST + 'bolt', 'Cyborg Energy Shield', 0.375, 2.0, 'Bolt materials'),
                row('jpt!', ST + 'bolt', 'Cyborg', 1.5, 0.5, 'Bolt materials'),
                # heat: 0.16 x 0.09/0.18 = 0.08 a round, losses 0.65 x 0.55/0.6 = 0.596 / 0.65 x 0.3/0.45 =
                # 0.433, draining while firing: 47 bolts to overheat -> on Halo 1's ONE loss 0.433
                # (approximation A': the vent, 1 -> 0.25 in 1.73 s) the heat fitted 0.0639 (47 bolts:
                # 47 x 0.0639 - 46 x 0.0433 = 1.012; 46: 0.991)
                row('weap', ST + 'storm rifle', 'Heat Generated Per Round', 0.0639, 0.0665, 'Heat', block='Triggers'),
                row('weap', ST + 'storm rifle', 'Heat Loss Per Second', 0.433, 0.3, 'Heat'),
                row('weap', ST + 'storm rifle', 'Heat Recovery Threshold', 0.25, 0.1, 'Heat'),
                # bolt: 25 x 50/20 = 62.5 wu/s (per tick); range 50 x 100/40 = 125
                row('proj', ST + 'bolt', 'Initial Velocity', 62.5 / 30.0, 50 / 30.0, 'Projectile'),
                row('proj', ST + 'bolt', 'Final Velocity', 62.5 / 30.0, 50 / 30.0, 'Projectile'),
                row('proj', ST + 'bolt', 'Maximum Range', 125.0, 100.0, 'Projectile'),
                # aim: 5 x 5/4, 20 x 15/20 (= 15, no row); 12 x 10/8, 20 x 20/20 (= 20, no row)
                row('weap', ST + 'storm rifle', 'Autoaim Angle', 6.25, 5.0, 'Autoaim'),
                row('weap', ST + 'storm rifle', 'Magnetism Angle', 15.0, 10.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port storm_rifle): the source pair (Halo 4 storm rifle vs the
    # yardstick, Halo 4's plasma pistol) against the target pair (the H1 port vs its TEMPLATE, the
    # H1 plasma rifle -- lists 4 / 5 catch a template that is not the yardstick)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_assault_carbine.weapon',
                              r'objects\weapons\pistol\storm_plasma_pistol\storm_plasma_pistol.weapon'),
                   'projectile': (SW + r'\projectiles\storm_assault_carbine_bolt.projectile',
                                  r'objects\weapons\pistol\storm_plasma_pistol\projectiles\storm_plasma_pistol_bolt.projectile'),
                   'damage_effect': (SW + r'\projectiles\storm_assault_carbine_bolt.damage_effect',
                                     r'objects\weapons\pistol\storm_plasma_pistol\projectiles\damage_effects\storm_plasma_pistol_bolt.damage_effect')},
        'target': {'weapon': (ST + 'storm rifle.weapon', PR + 'plasma rifle.weapon'),
                   'projectile': (ST + 'bolt.projectile', PR + 'bolt.projectile'),
                   'damage_effect': (ST + 'bolt.damage_effect', PR + 'bolt.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 2), a battery weapon spawns charged
    'test': {'level': 'b30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

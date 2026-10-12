r"""Focus Rifle (Halo Reach, wave B7): a CONTINUOUS BEAM on heat + battery with two zoom levels, on a
copy of the Halo 1 PLASMA RIFLE (the yardstick, step 4a). Nearest shapes: plasma_repeater.py /
needle_rifle.py for the Reach plumbing, sentinel_beam.py for the beam on heat + battery (the 15/s
cap, the end-on contrail, the first-person offset, the held-trigger hum), beam_rifle.py for the
scope. Built in parallel with B5 (the Concussion Rifle): test level b30, zoom glyphs at
hud_reticles 48-51 only (H1_PORT_PLAN "Running two ports in parallel").

STEP 4a (user, 2026-10-12; h1_role_compare.py focus_rifle). Reach (HREK, h3_weapon_values --kit
reach): a spew beam, 3 a round (plasma_fast) x 30/s = 90 dps, 4000 wu/s, range 120, error 0,
heat 0.025 a round, loss 0.35 / 0.23 overheated, recovery 0.1, overheated 1, battery 0.0016125 a
round (campaign the same: 620 rounds = 20.7 s), zoom 2 (3.5, 9.5), aim 2/10 4/10, strike_melee.
REACH COOLS WHILE FIRING: the user's stopwatch in Reach, ~2.5 s to overheat from cold = 0.75 heat/s
generated - 0.35 loss (the meter never visibly falls); 'no cooling' would be 1.33 s. Halo 1 fires a
held 30/s at 15/s (the SMG / Sentinel Beam observation): per-SECOND damage, heat and battery are
kept -> 6 a round, battery 1/310; Halo 1 cools while firing at its ONE loss (the Plasma Repeater's
probe) -> heat a round fitted so the gun overheats on the same second as Reach."""
from ._common import B, reserved, row

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\focus_rifle'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle'
FO = 'weapons\\focus rifle\\'
SND = 'sound\\weapons\\focus_rifle_port\\'
PR = 'weapons\\plasma rifle\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

PORT = reserved(
    order=25, wave='B7', name='Focus Rifle', source='Halo Reach',
    messages=(83, 84), icon=45, reticle=34, label='fo', teach_from='sr',
    sound_dir='sound\\weapons\\focus_rifle_port', weapon_dir='weapons\\focus rifle',
    yardstick={
        # step 4a (user, 2026-10-12): 'Plasma Rifle, check the H4 port for reference'
        'pick': 'Plasma Rifle',
        'reason': ("the heat + battery Covenant automatic of both games (Reach has one; the sniper "
                   "has no heat, battery or Flood damage, the plasma pistol is tapped). DEFAULT = "
                   "Reach's own numbers at Halo 1's 15/s (6 a round, overheat on the 39th round at "
                   "2.53 s = Reach's ~2.5 s, one heat loss = the MEAN of Reach's 0.35 / 0.23 (user; "
                   "the Beam Rifle's precedent): 0.29, a 3.1 s vent; Reach 3.9 s). BALANCED = the "
                   "plasma-rifle ratio. Materials (user, the Plasma Repeater's rule): the H1 plasma "
                   "rifle bolt's table in DEFAULT, x Reach's plasma_fast / plasma_slow per armour "
                   "class in BALANCED. The Halo 4 port of the same weapon (reference): Reach's own "
                   "values, heat + battery as the port's own, heat cards from the Sentinel Beam "
                   "(card_donors), ammo cards skipped"),
        # DEFAULT = Reach's own (above); these are the BALANCED rows (H1 plasma rifle x Reach focus
        # rifle / Reach plasma rifle). Reach plasma rifle: 10 plasma_slow x 6 -> 9/s (ramp 0.8 s),
        # heat 0.15 a round, loss 0.8525 / 0.35 overheated, recovery 0.1, battery 0.0025, 25 wu/s,
        # range 40, aim 5/12 9/18. H1 plasma rifle 12-14 (13) x 7 -> 10/s, heat 0.08, loss 0.3,
        # recovery 0.25, battery 0.005, 50 -> 25 wu/s, no range, aim 5/25 12/25
        'balanced': {
            'damage': 8.67,              # dps 13 x 10 = 130 x FR 90 / Reach PR 90 -> / 15/s
            'rate': (15.0, 15.0),        # 10 x 30/9 = 33 -> Halo 1's 15/s cap (damage keeps the dps)
            'overheat_s': 3.0,           # TIME TO OVERHEAT (both games cool while firing): H1 PR
                                         # 2.67 s x FR 2.47 / Reach PR 2.17 (19 rounds) -> the 46th round
            'heat_per_round': 0.0346,    # fitted under Halo 1's fire rule with the loss below
            'loss': 0.197,               # 0.3 (= the OVERHEATED loss, the Beam Rifle's reading) x 0.23/0.35
            'recovery': 0.25,            # 0.25 x 0.1/0.1 (vent 1 -> 0.25 at 0.197 = 3.8 s)
            'battery': 1 / 140.0,        # by TIME: H1 PR 20 s x FR 20.7 / Reach PR 44.4 = 9.3 s -> 140 rounds
            'velocity': 8000.0,          # 50 x 4000/25 -- see 4b (overpenetration: the laser's 1000)
            'range': 120.0,              # the H1 plasma rifle bolt has none: a zero on one side, Reach's
            'aim': (2.0, 20.83, 5.33, 13.89),  # 5 x 2/5, 25 x 10/12; 12 x 4/9, 25 x 10/18
            'zoom': None,                # the plasma rifle has none: Reach's 2 levels 3.5 / 9.5 kept
            'materials': 'x plasma_fast / plasma_slow (RP_FAST_SLOW in h1_role_compare)',
            'melee': None},              # Reach shares strike_melee: x1 = the plasma rifle's own
        'measured': 'h1_role_compare.py focus_rifle (rows "FR = Reach B, loss .29" and "FR = PR ratio")',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Sniper Rifle', 'Plasma Pistol'],
            'direct': None,
            'peers': ['Sniper Rifle', 'Sentinel Beam'],
            'why': "continuous instant beam, heat + battery (the H1 Sentinel Beam's model, but Reach has no Sentinel Beam)",
            'lacks': "Reach's 30 rounds a second (Halo 1: 15, per-second values kept); its TWO heat "
                     "losses (Halo 1: one, the mean); a beam drawn as one continuous ribbon (Halo 1: "
                     "a contrail a round)"}},
    # step 11: the source game's ai\generic entry (22 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle'},
)

PORT.update({
    'status': 'in progress',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for world
    # AND first person. focus_rifle.render_model: 14 nodes -- b_gun (root, identity: not tilted),
    # the charge cylinder / outer charges, barrel top / bottom (+01), the arm joints 01-03; 1 mesh,
    # 16 parts; ONE primary_trigger (identity, 0.371 / 0.004 / 0.039), fx_vent x2 (the overheat
    # vents, either side), left_hand. Materials (shader templates = the option indices):
    # focus_rifle_metal / _rubber / _shell (diffuse; metal and rubber NAME an illum map --
    # battle_rifle_illum / sniper_rifle_scope_illum -- but self-illum option 0 = off), _display
    # (_2_0_0_0_4_0_6_1: a METER, illum plasma_pistol_display + meter plasma_launcher_holo,
    # additive), _display2 (option 3, additive: plasma_launcher_holo), _illum_plasma (a halogram:
    # plasma_clouds noise through phantom_illum, palette soft_plasma_blue), _indicator (halogram,
    # plasma_launcher_holo x data_stream), _scope_alpha (black glass, 'calculate Z camera')
    'model': {
        'dir': r'weapons\focus rifle',
        'world': R + RW + r'\focus_rifle.render_model',
        'fp': R + RW + r'\focus_rifle.render_model',
        'world_name': 'focus rifle',
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent', 'primary_trigger': 'primary trigger'},
        'ground_point': 'auto',
        'shaders': {'focus_rifle_metal': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_rubber': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_shell': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_display': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_display2': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_illum_plasma': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_indicator': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None)},
        # the scope's black glass (a Reach halogram, no Halo 1 equivalent; the DMR's glass rule)
        'drop_materials': ('focus_rifle_scope_alpha',),
        'template': PR + r'fp\shaders\gun',
        'glow': {},
        # GLOW (fp_material_view --illum --texels 24, threshold 16, BEFORE choosing): the display
        # (the readout in the scope housing: 99 of 248 triangles on plasma_launcher_holo's lit
        # texels), the indicator (the scope window + two spots: 36 of 97), the plasma strip down the
        # left side (208 of 236 on phantom_illum, its alpha mask); display2 has no triangles. Reach's
        # colours (reach_function_data): display meter ON (255, 134, 22) orange / OFF (0, 69, 200)
        # blue, intensity 0.5..1; indicator self_illum (17, 134, 247) blue; the plasma halogram
        # through soft_plasma_blue (peak 67, 69, 216), color_medium (27, 53, 90). Boot 1: the
        # Needle Rifle's / repeater's STATIC lit shapes (additive chicago, function-free -- every
        # Halo 1 weapon out reads 0 until the first shot), Reach's colours; to judge against the
        # user's Reach screenshot (a heat-driven display = the repeater's ramp, if Reach's is)
        'meters': {
            'focus_rifle_display': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (1.0, 134 / 255.0, 22 / 255.0)},
            'focus_rifle_indicator': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (0.5 * 17 / 255.0, 0.5 * 134 / 255.0, 0.5 * 247 / 255.0)},
            'focus_rifle_illum_plasma': {
                'map': R + r'objects\vehicles\covenant\phantom\bitmaps\phantom_illum.bitmap',
                'from': PR + r'fp\shaders\gauge', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (67 / 255.0, 69 / 255.0, 216 / 255.0)}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's OWN fp_focus_rifle retargeted (the DMR's
    # recipe). fp_focus_rifle (reach_tags --pose, 61 nodes): idle 100, posing var1 / var2 89, ready
    # 22 (ready_initial 29, ready_overheated 22), put_away 6, fire_1 19, melee_strike_1 36 (primary
    # 5; _overheated 36), throw_grenade 44 (primary 8), throw_overheated 44, moving 20, look 9;
    # THE OVERHEAT: overheating 56 / overheated 59 / o_h_exit 38 = Halo 1's own three states (the
    # plasma rifle template's). Not reproduced: the overlays barrel (1), barrel_vibration (5),
    # fire_vibration (5), fire_buildup (90), fire_push_back (1), acceleration_screens (9) -- driven by
    # weapon functions Halo 1's graph has no slot for; crouch / jump / fall / land, sprint
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\focus_rifle.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in (
            'b_gun', 'b_outercharge_right', 'b_upper_armjoint01', 'b_barrel_top',
            'b_innercharge_cylinder', 'b_outercharge_left', 'b_barrel_bottom', 'b_lower_armjoint01',
            'b_upper_armjoint02', 'b_lower_armjoint02', 'b_barrel_bottom01', 'b_barrel_top01',
            'b_lower_armjoint03', 'b_upper_armjoint03')},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\focus rifle\fp',
        'h1_model': r'weapons\focus rifle\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1; the repeater's start too)
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
            'first_person:overheating': 'first-person overheating',
            'first_person:overheated': 'first-person overheated',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
    },

    # Reach's own sounds (h1_port_sounds.py focus_rifle, Reach's sfx.fsb). Levels = the active RMS of
    # the stock Halo 1 PLASMA RIFLE sound each stands in for (the template's; the repeater's
    # h1_stock_sound_levels readings, 2026-10-11): fire -9.3, overheat / dry -20.9, melee -11.4,
    # oh_exit -20.0, overheating -26.7, posing -30.5, ready -21.2, drop (plasma_impact) -18.7, flyby
    # (plasrif_projectile) -26.2, impact (plasmahit) -11.3; the hum -16 (the Sentinel Beam's loop,
    # same stand-in), zooms = the sniper's -28.9 / -29.2 (the Beam Rifle's). Reach's cues: the
    # weapon's attachments play focus_rifle_fire (in / loop / out, on primary_firing) + the FP layer
    # focus_rifle_firing_loop (in, a SILENT loop, out) + the tails; fr_overheat (in + loop, on
    # overheated); the FP graph: overheating -> fp_focus_rifle_overheating, o_h_exit ->
    # focus_rifle_oh_exit, ready, posing 1, melee; the projectile: focus_beam_flyby, the material
    # effects: focus_beam_impact, the drop: flak_cannon_drop; the empty effect beam_rifle_misfire;
    # zoom = the beam rifle's zoom in / out (Reach's weapon names them)
    'sounds': {
        'catalog': 'Focus Rifle',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'focus_rifle_port']),
        'h3_dir': RS + 'focus_rifle\\',
        'sounds': {
            # THE HUM (the Sentinel Beam's recipe): a sound_looping on the trigger's rate of fire;
            # start = the 3p fire in + the FP layer's in, loop = the fire loop, end = the fire out +
            # the FP out + the exterior tail
            'fo_fire_in': (['focus_rifle_fire\\focus_rifle_fire\\in', 'focus_rifle_fp\\focus_rifle_firing_loop\\track1\\in'],
                           'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_fire_loop': (['focus_rifle_fire\\focus_rifle_fire\\loop'], 'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_fire_out': (['focus_rifle_fire\\focus_rifle_fire\\out', 'focus_rifle_fp\\focus_rifle_firing_loop\\track1\\out',
                             'focus_rifle_tails_ext\\fr_tails_ext\\out'],
                            'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_dryfire': ([RS + 'beam_rifle\\beam_rifle_misfire'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -20.9),
            'fo_ready': (['focus_rifle_fp\\focus_rifle_ready'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_ready', -21.2),
            'fo_melee': (['focus_rifle_fp\\focus_rifle_melee'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_melee', -11.4),
            'fo_pose': (['focus_rifle_fp\\focus_rifle_posing1'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_posing', -30.5),
            # THE OVERHEAT (Halo 1's three states): the FP overheating cue + fr_overheat's in mixed,
            # its loop on `overheated`, the exit cue on o-h-exit
            'fo_overheat': (['focus_rifle_fp\\focus_rifle_overheating', 'fr_overheat\\fr_overheat\\in'],
                            'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'fo_overheat_loop': (['fr_overheat\\fr_overheat\\loop'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'fo_oh_exit': (['focus_rifle_fp\\focus_rifle_oh_exit'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_oh_exit', -20.0),
            'fo_zoom_in': ([RS + 'beam_rifle\\beam_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'fo_zoom_out': ([RS + 'beam_rifle\\beam_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'fo_drop': ([RS + 'flak_cannon\\flak_cannon_drop'], 'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            # the beam's own FLYBY (port_sound_refs does not read projectile sound fields: by hand)
            'fo_flyby': (['focus_beam_flyby\\single'], 'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            'fo_impact': (['focus_beam_impact'], 'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
        },
        # Halo 1 finishes a loop pass before the end track (the Sentinel Beam: 0.5 s)
        'loop_len': {'fo_fire_loop': 0.5},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only focus_rifle) on a COPY of the Halo 1 PLASMA RIFLE
    # (the yardstick = the template: heat + battery HUD, overheat states) wired as the SENTINEL
    # BEAM (sentinel_beam.py, a continuous beam on the same template, 12 boots): the hum, the own
    # firing effect, the beam projectile. DEFAULT = REACH'S OWN NUMBERS at Halo 1's 15/s (the
    # yardstick block); the ratio values are the balance rows. Template layout after the
    # Sentinel Beam's rewire: inputs A primary firing / B illumination / C rate of fire / D age;
    # function 0 = the hum (C in, off with 1), 1 = primary firing (A in, off with 3), 3 = age
    'pickable': {
        'weapon': FO + 'focus rifle',
        'template': PR + 'plasma rifle',
        'world_model': FO + 'focus rifle',
        'fp_model': FO + 'fp\\fp',
        'fp_anims': FO + 'fp\\fp',
        'label': 'fo',
        'teach': ('fo', 'sr'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'fo_ready',
                   'first-person posing': SND + 'fo_pose',
                   'first-person melee': SND + 'fo_melee',
                   'first-person overheating': SND + 'fo_overheat',
                   'first-person overheated': SND + 'fo_overheat_loop',
                   'first-person o-h-exit': SND + 'fo_oh_exit'},
        'rewire': {'inputs': ('primary_firing', 'illumination', 'primary_rate_of_fire', 'age'),
                   'functions': {0: (2, 'C_in', 'fire loop', {'turn_off_with': 1}),
                                 1: (2, 'A_in', 'primary firing', {'turn_off_with': 3})},
                   'drop_attachments_on': ('B_out',)},
        'fire_loop': {'tag': SND + 'fo_fire', 'like': r'sound\sfx\weapons\flamethrower\fire_ft',
                      'start': SND + 'fo_fire_in', 'loop': SND + 'fo_fire_loop',
                      'end': SND + 'fo_fire_out', 'marker': 'primary trigger',
                      'scale': 'A_out'},
        # THE FIRING EFFECT (the Sentinel Beam's): the plasma rifle's one flash sprite (additive
        # sprites saturate at 15/s), no sound (the hum), the muzzle light as a part. REACH'S FOCUS
        # RIFLE MUZZLE IS ORANGE (the H4 kit: its particle tints (255, 98, 42) -> (255, 92, 0),
        # sparks (255, 200, 72) -> (238, 83, 31); the firing light blue-violet)
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1; h1_effect_particles): Reach's
        # FIRST-PERSON flash (fx\firing.effect, 'only in first person', all at primary_trigger, no
        # offsets): flash_large (emitter bounds 0.106 wu), muzzle_flash_plasma (0.108, 'render when
        # zoomed'), distortion_ring (0.229: a refraction ring, no Halo 1 equivalent), spark_ember
        # (0.51: physics sparks, orange) + the 1p beam and the blue-violet firing light. Ours: ONE
        # `flash c generic` 0.06-0.075 wu at the bore, first person only (the plasma rifle's other
        # five sprites dropped: additive sprites saturate to white at 15/s, the Sentinel Beam's
        # finding) -- within Reach's size; the sparks and the ring not reproduced (judge in game)
        'fire_effect': {'from': PR + 'effects\\plasma rifle upper fire',
                        'out': FO + 'effects\\fire', 'sound': '', 'light': FO + 'muzzle light',
                        'keep_particles': 'flash c generic', 'tint': (1.0, 1.0, 0.38, 0.16)},
        # the `c generic` particles take the WEAPON's change colour A (the Sentinel Beam's test 6)
        'change_color_a': ((1.0, 0.38, 0.16), (1.0, 0.36, 0.0)),
        'own_light': {'shape': PR + 'muzzle flash', 'look': PR + 'muzzle flash',
                      'out': FO + 'muzzle light', 'argb': (1.0, 1.0, 0.38, 0.16), 'duration': 0.1,
                      'no_flare': True},
        # the template's overheat steam aims at its `vent` (Reach's fx_vent, mapped in the model)
        'overheated_effect': {'from': PR + 'effects\\overheated', 'out': FO + 'effects\\overheated',
                              'locations': {}},
        'attach_swap': {PR + 'muzzle flash': FO + 'muzzle light'},
        'attach_markers': {'secondary trigger': 'primary trigger', 'heat flare': 'vent',
                           'heat flare1': 'vent'},
        'fields': {
            # the dead-battery click: the plasma rifle's empty is a SOUND reference
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'fo_dryfire',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'fo_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'fo_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'fo_drop',
            # Reach's focus rifle: no age penalties, no misfire (its age block is all 0; only
            # 'cannot fire at maximum age') -- the template's rate -20 % / heat +20 % at an empty
            # battery stopped the repeater overheating; misfire 0.9 / 0.5 off with its effect
            'weap_attrs.age.heat_penalty': 0.0,
            'weap_attrs.age.rate_of_fire_penalty': 0.0,
            'weap_attrs.age.misfire_start': 0.0,
            'weap_attrs.age.misfire_chance': 0.0,
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.triggers.0.firing_effects.1.misfire_effect.filepath': '',
            # STEP 4b (before boot 1). List 2 (the ratio vs Reach's plasma rifle onto the H1 plasma
            # rifle): camo ding 0.3 x 1/0.4, illumination recovery 0.15 x 0.1/0.03. List 3: firing
            # noise Reach's 'shout' (the plasma rifle 'loud'), weapon type Reach's 'undefined' (the
            # plasma rifle's 'plasma rifle'), deviation angle 1 deg (a zero on one side: the source
            # value, the DMR's / Needle Rifle's way)
            'weap_attrs.interface.active_camo_ding': 0.75,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.5,
            'weap_attrs.triggers.0.firing.firing_noise': 'shout',
            'weap_attrs.weapon_type': 'undefined',
        },
        'melee': (PR + 'melee', FO + 'melee'),
        'melee_response': PR + 'melee_response',
        'messages': ('Picked up a focus rifle', 'Picked up %d rounds for focus rifle'),
        'icon': 'focus rifle',
        # the PLASMA RIFLE's HUD (heat + battery meters) with Reach's reticle (ui\chud\focus_rifle:
        # hud_reticles 22, the H4 kit's reading -- recheck with the user's screenshot), the
        # sniper's zoom screen effect; THE SCOPE (h1_h3_scope, Reach's chud) waits for the user's
        # Reach screenshot (`--fit`)
        'hud': {'donor': PR + 'plasma rifle', 'out': FO + 'focus rifle',
                'screen_effect_from': r'weapons\sniper rifle\sniper rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                # Reach's chud (h1_h3_scope reach:ui\chud\focus_rifle): scope_mask (beam_rifle_scope,
                # 4 copies), meter_border (4), meter_heat / meter_batt (meter fills), the low-battery
                # and overheat flashes. The Beam Rifle's decisions (user, A4): the frame baked, the
                # fills (garbage as a mask) and the flashes (hidden until a warning) dropped -- the
                # Halo 1 HUD's own heat / battery meters show while zoomed. SIZE: a placeholder (the
                # Beam Rifle's 828 / x0.8) until the user's Reach screenshot (`--fit W,H`)
                'scope': {'chud': R + r'ui\chud\focus_rifle', 'out': FO + 'bitmaps\\scope_mask',
                          'size': 1024, 'span': 828.0, 'aspect': (4 / 3.0) / 0.8, 'alpha': 'outside',
                          'per_widget': {'lowbatt_flash_scope': {'drop': True},
                                         'meter_heat': {'drop': True},
                                         'meter_batt': {'drop': True},
                                         'meter_lowbatt_flash_left': {'drop': True},
                                         'meter_overheat_flash_right': {'drop': True}}},
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 22, 'focus rifle'),
                'reticle_min_width': 3},
        'aiming': {'autoaim_angle': 2.0, 'autoaim_range': 10.0,
                   'magnetism_angle': 4.0, 'magnetism_range': 10.0,
                   'zoom_levels': 2, 'zoom_ranges': (3.5, 9.5),
                   'deviation_angle': 1.0},           # 4b list 3 (degrees here)
        # THE BEAM (the Sentinel Beam's): a copy of Halo 1's Sentinel beam projectile (its contrail
        # = a continuous beam, the look Reach's 1p beam shares: energy_trail through the
        # sentinel_beam palette, black -> gold -> white -- the bake waits for the user's
        # screenshot), Reach's 120 wu range; the damage a copy of the plasma rifle BOLT (the
        # yardstick's table = the DEFAULT materials, user), Reach's 3 a round x 30/s = 6 at 15/s,
        # instantaneous acceleration 0.1 (Reach's). Speed: the Sentinel beam's own 1200 wu/s (proven
        # visible from the FP muzzle); Reach 4000 crosses the whole range in one tick (the Spartan
        # Laser: no overpenetration at that speed) -- 4b decides the responses
        # STEP 4b (before boot 1): the damage effect's camo damage 0.12 x 0.1/0.25 (list 2); breaking
        # effect (list 3: Reach 0, its plasma rifle 3 / 0.5 / 0.2) = the bolt's 0. The projectile:
        # air / water damage range Reach's own 0..120 / 0..20 (no falloff: lower = upper damage);
        # impact / detonation noise Reach's 'loud' (list 3, enums); water gravity 0 (Reach's).
        # RESPONSES: the Halo 1 Sentinel beam overpenetrates every unit body and reflects off Jackal
        # shields; Reach's focus_rifle_beam overpenetrates glass, liquid, plants and 'tough_organic'
        # UNITS EXCEPT GIANTS, detonates on the rest (Elite bodies are hard_metal_thin, armour
        # tough_inorganic) and never reflects -> overpenetrate glass 9, grunt 11, jackal 15,
        # engineer 17, flood 19 / 20, human skin 24, water 28, leaves 29; the hunter skin 13, elite
        # 14, Jackal shield 16, cyborg / human armour 21 / 23, plastic 27 stop it ('disappear', the
        # Sentinel beam's own stop, with its impact effects). The shields' potential 'reflect' (0..180
        # deg, the Sentinel beam's) kept: an OBSERVATION to check in game (no velocity window)
        'beam': {'projectile': (r'characters\sentinel\beam', FO + 'beam'),
                 'damage': (PR + 'bolt', FO + 'beam'),
                 'range': 120.0, 'dmg': 6.0, 'acceleration': 0.1,
                 'fields': {'damage.active_camouflage_damage': 0.048},
                 'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'fo_flyby',
                                 'proj_attrs.physics.air_damage_range': (0.0, 120.0),
                                 'proj_attrs.physics.water_damage_range': (0.0, 20.0),
                                 'proj_attrs.physics.water_gravity_scale': 0.0,
                                 'proj_attrs.impact_noise': 'loud',
                                 'proj_attrs.physics.detonation_noise': 'loud'},
                 'default_responses': {'overpenetrate': [9, 11, 15, 17, 19, 20, 24, 28, 29],
                                       'disappear': [13, 14, 16, 21, 23, 27]}},
        # Reach: spew 30/s (Halo 1: 15/s; the hum needs differing bounds, 29..30 both fire 15/s),
        # no rate ramp (4b: Reach's 0.3 is the ERROR deceleration -- error 0 here); the rate
        # deceleration 0.1 = the Sentinel Beam's (the hum's tail follows it); heat 0.0451 a round = the 39th round overheats at 2.53 s with
        # Halo 1 cooling while firing at 0.29 (Reach ~2.5 s, the user's stopwatch); battery 1/310
        # (Reach's 620 x 0.0016125 at 30/s); error 0; every round a tracer; the FP muzzle
        # (h1_fp_muzzle.py, the idle pose: 0.4496 / -0.0643 / -0.0387 wu)
        'trigger': {'rounds_per_second': (29.0, 30.0), 'heat_generated_per_round': 0.0451,
                    'acceleration_time': 0.05, 'deceleration_time': 0.1,
                    'age_generated_per_round': 1 / 310.0, 'error_angle': (0.0, 0.0),
                    'rounds_between_tracers': 0,
                    'first_person_offset': (0.4496, -0.0643, -0.0387),
                    'illumination_recovery_time': 0.5},
        # Reach: overheated at 1, back at 0.1; ONE loss = the mean of 0.35 / 0.23 (user, step 4a)
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.29},
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.0, 0.0)},
        'palette_levels': LEVELS,
    },

    # step 4b (port_field_audit.py --port focus_rifle): the source pair (Reach focus rifle vs the
    # yardstick, Reach's plasma rifle) against the target pair (the H1 port vs its template = the
    # yardstick, the H1 plasma rifle)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\focus_rifle.weapon', r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon'),
                   'projectile': (RW + r'\projectiles\focus_rifle_beam.projectile',
                                  r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (RW + r'\projectiles\focus_rifle_beam.damage_effect',
                                     r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.damage_effect')},
        'target': {'weapon': (FO + 'focus rifle.weapon', PR + 'plasma rifle.weapon'),
                   'projectile': (FO + 'beam.projectile', PR + 'bolt.projectile'),
                   'damage_effect': (FO + 'beam.damage_effect', PR + 'bolt.damage_effect')}},

    # the dry test: b30 (the parallel pair's level for B7), a battery weapon spawns charged
    'test': {'level': 'b30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

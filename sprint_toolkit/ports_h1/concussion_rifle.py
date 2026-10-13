r"""Concussion Rifle (Halo Reach -> Halo 1, wave B5). Yardstick: the restored FUEL ROD (step 4a,
user 2026-10-12); the weapon is a copy of the Halo 1 ROCKET LAUNCHER (user: 'the Rocket Launcher
as the copy if it's easier' -- the tested explosive-magazine route, the Brute Shot's and the
Grenade Launcher's) firing a plasma bolt built on the fuel rod's projectile and explosion. What
is new: a fast KNOCKBACK blast (Reach's 2.5 = its gravity hammer impulse) and a bolt that SPEEDS
UP in flight (Reach 12 -> 16 wu/s over 6..15 wu). Reach plumbing: grenade_launcher.py; the
explosive bolt: brute_shot.py."""
from ._common import B, reserved, row  # noqa: F401

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\concussion_rifle'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle'
CR = 'weapons\\concussion rifle\\'
SND = 'sound\\weapons\\concussion_rifle_port\\'
RL = 'weapons\\rocket launcher\\'
FR = 'weapons\\fuel rod gun\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
TEX = R + RW + r'\bitmaps' + B
HOLO = R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap'
STATIC = r'weapons\needler\shaders\needler luminous'
GAUGE = r'weapons\plasma rifle\fp\shaders\gauge'
# Reach's indicator blue, read off the user's Reach screenshot (2026-10-12: ~70 / 150 / 255)
BLUE = (0.3, 0.6, 1.0)
# Reach's concussion PLASMA (boot 1, user: 'a normal plasma release'; 'fuel rod projectiles, not
# changed yet, including the detonation size and color' + a Reach screenshot of the bolt). Read
# from Reach: the muzzle flare gradient muzzle_flare_concussion_rifle (black -> 50 / 46 / 174 ->
# 103 / 84 / 247 -> 199 / 148 / 255 -> white), the contrail gradient concussion_rifle (the same
# violet -> white), the bolt's lens flare 1 / 0.19 / 0.12 (red-orange) over it; the screenshot's
# bolt: a white-hot core in a PINK-MAGENTA glow (mid 168 / 125 / 151), violet-white sparks, no
# trail to see
VIOLET = (0.78, 0.58, 1.0)
VIOLET_DEEP = (0.40, 0.33, 0.97)
PINK = (1.0, 0.45, 0.75)
# BOOT 6 DIAGNOSTIC (boot 5, user: 'leaves the bolt in flight as the remaining green object' --
# every in-flight tag reads non-green in the deployed map): one colour per element, the GL's
# method -- SPARKS red, glow light + flare BLUE, model shell YELLOW, model core WHITE
# BOOT 6 (user: 'unchanged, green' -- a big green ball, white core, none of the four colours):
# not an attachment at all -- the fuel rod copy's light-volume WIDGET `hunter fuel rod` (green
# 0.68 / 0.96 / 0.29 -> 0.52 / 0.98 / 0.29, radius 0.02 -> 0.1 wu). Diagnostic off
DIAG = False

PORT = reserved(
    order=23, wave='B5', name='Concussion Rifle', source='Halo Reach',
    messages=(79, 80), icon=43, reticle=32, label='cr', teach_from='pr',
    sound_dir='sound\\weapons\\concussion_rifle_port', weapon_dir='weapons\\concussion rifle',
    yardstick={
        # STEP 4a (user, 2026-10-12): h3_weapon_values.py --kit reach (concussion_rifle /
        # flak_cannon / rocket_launcher / plasma_rifle, FP graphs), reach_tag_fields.py of the bolt
        # and its damage effects, the HREK globals damage table, h1_role_compare.py
        # concussion_rifle (new set).
        # REACH'S CONCUSSION RIFLE (HREK): recovery 0.333 s (3/s), 6 / 18 / 30, reloads 6 (100 fr
        # empty AND full), error 0.15 min, 0.4 / 0.4, no zoom, aim 4/15 8/15, melee strike_melee, FP
        # ready 19 / put_away 4 / melee 34 / fire 25. Chud `elite_shot`: hud_reticles #17 at
        # (0.85, 1.0) mirrored, ballistic_meters #0 (a 24-pip bar, scale 0 = animated).
        # The BOLT concussion_rifle_grenade: 12 -> 16 wu/s over the ACCELERATION RANGE 6..15 wu (it
        # speeds up), air + water gravity 0.25, range 100, minimum velocity 11, timer
        # 'immediately' 0, collision radius 0.1, danger radius 0.5, AI velocity x0.7 / 0.9 / 1.1,
        # flags oriented along velocity + AI ballistic aiming; detonates on everything, plants and
        # liquid overpenetrate. Damage: IMPACT 21.5 (`collision`, accel 0.75, category high
        # explosive) + the BLAST 0..21.5 over 1 -> 2 wu (AOE core 0.8, `plasma_fast`, accel 2.5,
        # 'detonates explosives', 'transfer dmg always uses min') = 43 a direct hit.
        # THE KNOCKBACK: the blast's 2.5 = Reach's own GRAVITY HAMMER IMPULSE (2.5 over 0.6 -> 2).
        # Halo 1 per Reach unit: rocket 6 / 3, plasma grenade 4 / 2, fuel rod 4 / 1.5; the Halo 1
        # hammer blast was TUNED LIVE to 7.5 (A9; the ratio's 5.83 moved only dead bodies).
        # THE FLIGHT: Halo 1 changes speed LINEARLY over the whole range (the GL's probe), so 12 ->
        # 16 over 100 wu arrives 6-15 % late (15 / 30 / 50 wu: Reach 1.15 / 2.09 / 3.34 s, Halo 1
        # 1.22 / 2.38 / 3.85 s; a fitted 14 -> 16: 1.06 / 2.10 / 3.45 s).
        # Yardsticks (Reach): fuel rod (flak_cannon) 100 impact (collision) + 0..60 over 0.5 ->
        # 2.25 (explosion_large, core 0.5, accel 1.5) = 160, recovery 0.4, 5 / 20 / 30, reload 90
        # fr, 15 -> 6.5 wu/s, gravity 0.025, range 80, error 0 / 0..0.05, aim 4/25 8/25, FP ready
        # 26, put_away 5, melee 47; rocket 200 + 240 = 440, 0.8 s, 2 / 4 / 8, 116 fr, 8 -> 16;
        # plasma grenade 2 + 25..250 over 0.54 -> 1.8 (explosion_small, accel 2).
        # Halo 1: the restored fuel rod 40..75 over 0.5 -> 1.5 (no impact; accel 4, high
        # explosive, HUNTER ARMOUR AND SKIN x0 = immune, Flood x2), 1.25 s a charged shot (tag 10/s),
        # 4 / 12 / 24, reload 90 fr, 14 -> 5 wu/s, gravity 1, range 0, error 0, aim 4/25 6/25, FP
        # ready 26 / put_away 5 / melee 42; rocket 80..300-330 over 0.5 -> 2.0, accel 6, 2.0 s,
        # 2 / 4 / 8, 125 fr, 12 -> 10, range 128, aim 0/35 12/35.
        # Reach's damage table (plasma_fast / explosion_large / collision): hard_metal_thick
        # (Hunter armour) 0.25 / 0.75 / 0.75, energy_shield_thick (Jackal) 0.5 / 0.75 / 0.75,
        # energy_shield_thin (Elite, Spartan) 1 / 0.75 / 1, hard_metal_thin (Elite body) 1 / 1 /
        # 1, tough_inorganic (Marine armour), soft_organic x1.
        'pick': 'Flak Cannon (H1 fuel rod)',
        'reason': "user, step 4a 2026-10-12: 'Fuel Rod yardstick, but you can take the Rocket "
                  "Launcher as the copy if it's easier, material change in balanced, the other "
                  "proposed changes only after seeing the default values, unless those are "
                  "balanced values and calculated'. Reach's own fuel rod is a 5-round magazine "
                  "plasma explosive like the concussion rifle; the ratio rows make it a weak, slow "
                  "gun (20 dps against the fuel rod's 60: Reach's concussion rifle has a third of "
                  "its fuel rod's dps, and Halo 1's fuel rod is paced by its 1.25 s charge). "
                  "Materials: the FUEL ROD's table in default (Hunters immune), that table x "
                  "Reach's plasma_fast / explosion_large in balanced. The knockback (proposed 7.5) "
                  "and the fitted flight (14 -> 16) wait for the default boot: default = Reach's "
                  "own 2.5 and 12 -> 16.",
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows, every one
        # the FUEL ROD ratio per field (H1 fuel rod x Reach CR / Reach fuel rod)
        'balanced': {
            # the blast: 75 x 21.5/60 = 26.9; lower: Reach 0 / 0 (unset) -> the sibling rule, 40 x
            # 26.9/75 = 14.3; radius 0.5 x 1/0.5, 1.5 x 2/2.25
            'damage': 26.9, 'damage_lower': 14.3, 'radius': (1.0, 1.333),
            # the impact: Halo 1's fuel rod has none (0 x 21.5/100 = 0: a zero on one side ->
            # zero in balanced, the Needle Rifle's / Grenade Launcher's rule)
            'impact': 0.0,
            # knockback 4 x 2.5/1.5 (Halo 1 fuel rod explosion / Reach's)
            'acceleration': 6.67,
            # 1.25 s x 0.333/0.4 = 1.04 s (0.96/s); 4 x 6/5 = 4.8 -> 5, 12 x 18/20 = 10.8 -> 11,
            # 24 x 30/30; reload 90 fr x 100/90 = 100 = Reach's own (x1); ready 26 x 19/26, put
            # away 5 x 4/5: x1
            'rounds_per_second': 0.96,
            'magazine': 5, 'rounds_total_initial': 11, 'rounds_total_maximum': 24,
            # flight 14 x 12/15 = 11.2, 5 x 16/6.5 = 12.3; gravity 1 x 0.25/0.025 = 10 (a near-zero
            # source: no ratio -> Reach's own 0.25, the GL's precedent); range: the fuel rod's 0 is
            # UNSET -> Reach's own 100 (boot 11: a 0 range destroyed the bolt on creation)
            'velocity': (11.2, 12.3), 'gravity': 0.25, 'range': 100.0,
            # aim 4 x 4/4, 25 x 15/25; 6 x 8/8, 25 x 15/25
            'aim': (4.0, 15.0, 6.0, 15.0),
            # error: Reach's fuel rod 0 / 0..0.05, Halo 1's 0 / 0 -> degenerate: Reach's own
            'error_deg': (0.15, 0.4, 0.4),
            # materials (user): the fuel rod's table x Reach's plasma_fast / explosion_large on the
            # blast -- Elite / cyborg shield x1.333, Jackal shield x0.667, Hunter armour 0 x 0.33 =
            # 0 (immune stays), the rest x1 (Reach has no Flood: x2 kept)
            'blast_mods': {'elite_energy_shield': 1.333, 'cyborg_energy_shield': 1.333,
                           'jackal_energy_shield': 0.667}},
        # Time to kill (h1_role_compare concussion_rifle, direct hits, normal): Reach's own 43 at 3/s
        # (129 dps, = the Plasma Rifle's 130) -- Elite minor 5 shots 1.3 s, commander 7 / 5.3 s;
        # fuel rod ratio 20.2 at 0.96/s (19 dps) -- Elite 10 / 15 shots (12.7 s / 21 s), Hunters
        # immune; RL ratio 30.8 at 1.2/s (37 dps); the fuel rod 75 at 0.8/s (60 dps)
        'measured': 'h1_role_compare.py concussion_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle',
            'provisional': 'Flak Cannon (H1 fuel rod)',
            'alternatives': ['Rocket Launcher', 'Plasma Grenade'],
            'direct': None,
            'peers': ['Flak Cannon', 'Rocket Launcher', 'Plasma Rifle'],
            'why': "magazine 6, Covenant explosive plasma bolt; Reach's fuel rod is a 5-round magazine",
            # what Halo 1 cannot do: speed up a projectile over a short acceleration range (it
            # changes speed over the whole range)
            'lacks': 'the acceleration range (12 -> 16 over 6..15 wu)'}},
    # step 11: the source game's ai\generic entry (m10: weapon properties #1, firing pattern #1 --
    # max firing distance 15, rate 3.625, desired range 6-8, WDM 0.75, bursts 0.99-1.4 s every
    # 1.31-2.06 s, drop 0.125-0.35 / 6-9) laid over a Halo 1 FUEL ROD carrier ('cr' has no carrier).
    # Halo 1's fuel rod carriers (h1_weapon_carriers, 2026-10-13): grunt specops fuel rod (+ airdef),
    # both WDM 0.5, actor flags 0, drop 0.5-1.0 loaded / 2-6 ammo -- they agree, no donor_variant.
    # ARMED WDM RULE: base 0.5 x fuel rod 60 / port dps (h1_role_compare 5b on the BUILT port:
    # default 21.5 + 21.5 every 0.333 s = 129 -> 0.233; balanced 26.9 every 1.04 s = 26 -> 1.15,
    # above 1.0 applied as is: the DMR's rule)
    # BALANCED DROP (user 2026-10-12, every weapon): H1 yardstick carriers x source port / source
    # yardstick, the source values from the MAP (m10): Reach CR 0.125-0.35 / 6-9, Reach fuel rod
    # (flak_cannon) 0.25-0.4 / 2-4 -> loaded 0.5 x 0.125/0.25 = 0.25, 1.0 x 0.35/0.4 = 0.875; ammo
    # 2 x 6/2 = 6, 6 x 9/4 = 13.5 -> 13
    firing_profile={'balanced_set': ['0x1D8=0.25:Drop Weapon Loaded', '0x1DC=0.875:Drop Weapon Loaded Max',
                                     '0x1E0=h6:Drop Weapon Ammo', '0x1E2=h13:Drop Weapon Ammo Max'],
                    'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle',
                    'donor_weapon': 'weapons\\fuel rod gun\\fuel rod',
                    'wdm_rule': {'base': 0.5, 'yardstick_dps': 60.0, 'port_dps': 129.0,
                                 'balanced_port_dps': 26.0}},
)

PORT.update({
    # 2026-10-13: tested on a30 over 12 boots (dry default 1-9: mechanics + the look found layer by
    # layer; balanced 10-12, probe-measured) + Armed (all three species fire it) -- confirmed by the
    # user; the ten-map rebuild is BATCHED for wave B (user's go)
    'status': 'done',
    # CLOSE-OUT RECORD (2026-10-13). 4b + template diff + port_sound_refs + the muzzle flash BEFORE
    # boot 1. Yardstick: the FUEL ROD (user); default = Reach's own, balanced = the fuel rod ratio.
    # Weapon (rocket copy): 6 / 18 / 30, 3/s, reload 3.33 s, error 0.15 / 0.4, no zoom, aim 4/15 8/15;
    #   balanced 0.96/s, 5 / 11 / 24, magnetism 6, a 5-tick meter (flash 2).
    # Bolt (fuel rod copy): 12 -> 16 wu/s (flies ~constant: probe), gravity 0.25, range 100, min
    #   velocity 11 (balanced 0); impact 21.5 (balanced 0) + blast 11.47..21.5 over 1 -> 2, knockback
    #   2.5 (balanced 26.9 / 14.3 over 1 -> 1.33, 6.67); fuel rod table, Hunters Reach's values,
    #   balanced shields x1.33 / x0.67.
    # Look: Reach's model + bolt model, the plasma pistol flash in violet, a pink light volume, violet
    #   sparks / blast / impacts, the plain plasma burn, Reach's crosshair supersampled.
    # Closing checks: port_refs_audit 0 problems, port_sound_refs all OWN (the bolt's own sound fields
    #   empty, as Reach's), hit-effect rule x1 (3/s < 3.5), check 8: Armed Grunt / Jackal / Elite
    #   fire it (hands 'two', WDM 0.233 / 1.15, drop 0.25-0.875 / 6-13 balanced). Knockback uncarded.

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for world
    # AND first person. concussion_rifle.render_model: b_gun (root, identity: not tilted) >
    # b_wing_left / _right (the side vents), b_hatch > b_drum > six b_drum_flap0x (the revolving
    # drum); markers primary_trigger (0.234 / 0.001 / 0.034), left_hand, 2 x vent, fx_reload_gas,
    # weapon_stow_anchor -- no primary_ejection. Materials: inside / metal / rubber / shell (one
    # diffuse, concussion_rifle_diffuse), gas_effect (halogram: clouds_256), indicator (halogram:
    # plasma_launcher_holo + data_stream), overheat (plasma_launcher_holo illum)
    'model': {
        'dir': r'weapons\concussion rifle',
        'world': R + RW + r'\concussion_rifle.render_model',
        'fp': R + RW + r'\concussion_rifle.render_model',
        'world_name': 'concussion rifle',
        'ground_point': 'auto',
        'markers': {'left_hand': 'left hand'},
        'shaders': {'concussion_rifle_inside': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    'concussion_rifle_metal': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    'concussion_rifle_rubber': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    'concussion_rifle_shell': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    # every material needs a shader or `tool model` ASKS for a type and loops on
                    # the empty answer (found 2026-10-12: 50 min of prompts) -- the glow parts
                    # unlit off the diffuse until fp_material_view decides them
                    'concussion_rifle_gas_effect': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    'concussion_rifle_indicator': (TEX + 'concussion_rifle_diffuse.bitmap', None),
                    'concussion_rifle_overheat': (TEX + 'concussion_rifle_diffuse.bitmap', None)},
        'template': r'weapons\plasma rifle\fp\shaders\gun',
        # GLOW (fp_material_view --illum, 2026-10-12): the INDICATOR (180 tris, every one on lit
        # texels: the holo glyphs on the top right of the gun, blue in the user's Reach screenshot)
        # and the OVERHEAT panel (84 of 92 lit) both sample Reach's plasma_launcher_holo (shape in
        # R, grey panels + white lines) -> lit static shapes (the GL's LCD recipe), Reach blue read
        # off the screenshot. The GAS (the top vent slots, a clouds_256 halogram) stays unlit
        # off the diffuse for boot 1 (dark slots in the screenshot)
        'meters': {'concussion_rifle_indicator': {'map': HOLO, 'from': GAUGE, 'shape': 'r',
                                                  'gradient': 0.0, 'static': STATIC, 'color': BLUE},
                   'concussion_rifle_overheat': {'map': HOLO, 'from': GAUGE, 'shape': 'r',
                                                 'gradient': 0.0, 'static': STATIC, 'color': BLUE}},
        # THE BOLT'S MODEL (boot 2): Reach's own concussion_rifle_grenade (one node, no markers;
        # materials plasma_nade_metal / plasma_launcher_projectile) instead of the fuel rod's green
        # ammo orb -- both SOLID GLOW: the white-hot core of the screenshot
        # BOOT 3 (user): 'still all green' -- a solid glow is a shader_model on the template (the
        # plasma rifle gun), whose REFLECTION tints (perpendicular 0.24 / 1 / 0.56) drew the bolt
        # green over the pink -> ADDITIVE glows (transparent chicago: no reflection), the white-hot
        # core inside the pink
        'glow_shaders': {'plasma_nade_metal': {'rgb': (1.0, 1.0, 0.0) if DIAG else PINK, 'additive': True},
                         'plasma_launcher_projectile': {'rgb': (1.0, 1.0, 1.0) if DIAG else (1.0, 0.85, 0.95), 'additive': True}},
        'extra_models': {'bolt': {'from': R + RW + r'\projectiles\concussion_rifle_grenade.render_model',
                                  'dir': CR + 'bolt'}},
        'collision': {'material': 'metal',
                      # the world model's bounds (JMS, wu): x -0.108..0.230, y -0.029..0.031, z -0.049..0.075
                      'boxes': [((-0.108, -0.029, -0.049), (0.230, 0.031, 0.075))]},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's own fp_concussion_rifle (the DMR's
    # recipe). One resource group. fire_1 var1-3 25 fr, idle 100, posing var1 / var2 94, ready 19
    # (ready_initial 32), put_away 4, reload_empty = reload_full 100 (primary 48), melee_strike_1 34
    # (primary 5), throw_grenade 44 (primary 8), moving 20, look 9, barrel_spin 25 (an overlay:
    # the drum turns a shot -- Reach's `chased_barrel_spin` function); sprint / jump / land /
    # fall / acceleration_screens not reproduced
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\concussion_rifle.render_model',
        'nodes': {'b_gun': 'frame b gun', 'b_wing_left': 'frame b wing left',
                  'b_wing_right': 'frame b wing right', 'b_hatch': 'frame b hatch',
                  'b_drum': 'frame b drum', 'b_drum_flap01': 'frame b drum flap01',
                  'b_drum_flap02': 'frame b drum flap02', 'b_drum_flap03': 'frame b drum flap03',
                  'b_drum_flap04': 'frame b drum flap04', 'b_drum_flap05': 'frame b drum flap05',
                  'b_drum_flap06': 'frame b drum flap06'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\concussion rifle\fp',
        'h1_model': r'weapons\concussion rifle\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1; the repeater and the GL kept it)
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

    # Reach's own sounds (h1_port_sounds.py concussion_rifle, Reach's sfx.fsb). Levels = the active
    # RMS of the stock Halo 1 sound each stands in for (h1_stock_sound_levels.py, 2026-10-12): fuel
    # rod fire -12.2, explosion -11.4 / -10.1; the Grenade Launcher's measured ready -18.3, melee
    # -21.8, posing -22.1, rocket_reload -22.5, rocket_ammo -28.8, AR dryfire -17.6, rlauncher
    # impact -23.0. Reach's cues: firing.effect = concussion_rifle_fire + brute_shot_tails_ext
    # (Halo 1 plays one sound a round: MIXED, the DMR / GL); detonation.effect's explosion event =
    # concussion_round_expl (+ the expl tails); the empty effect = plasma_pistol\plasma_dryfire;
    # FP: fp_cr_ready / _melee1 / _posing1 / _reload (ONE reload for empty and full); no weapon drop
    # sound of its own (the fuel rod's flak_cannon_drop stands in); pickup: brute_shot_ammo (the GL's)
    'sounds': {
        'catalog': 'Concussion Rifle',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'concussion_rifle_port']),
        'h3_dir': RS + 'concussion_rifle' + B,
        'sounds': {
            'cr_fire': (['concussion_rifle_fire', RS + 'brute_shot' + B + 'brute_shot_tails_ext'],
                        B.join(['sound', 'sfx', 'weapons', 'fuel rod gun', 'fire']), -12.2),
            'cr_explode': (['concussion_round_expl'],
                           B.join(['sound', 'sfx', 'weapons', 'fuel rod gun', 'explosion']), -10.8),
            'cr_reload': (['fp_concussion_rifle' + B + 'fp_cr_reload'],
                          B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_reload_e']), -22.5),
            'cr_ready': (['fp_concussion_rifle' + B + 'fp_cr_ready'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_ready']), -18.3),
            'cr_melee': (['fp_concussion_rifle' + B + 'fp_cr_melee1'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_melee']), -21.8),
            'cr_pose': (['fp_concussion_rifle' + B + 'fp_cr_posing1'],
                        B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_posing']), -22.1),
            'cr_ammo': ([RS + 'brute_shot' + B + 'brute_shot_ammo'],
                        B.join(['sound', 'sfx', 'weapons', 'weapon_pickup_ammo', 'rocket_ammo']), -28.8),
            'cr_dryfire': ([RS + 'plasma_pistol' + B + 'plasma_dryfire'],
                           B.join(['sound', 'sfx', 'weapons', 'assault rifle', 'dryfire']), -17.6),
            'cr_drop': ([RS + 'flak_cannon' + B + 'flak_cannon_drop'],
                        B.join(['sound', 'sfx', 'impulse', 'weapon_drops', 'rlauncher_impact']), -23.0),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only concussion_rifle) on a COPY of the Halo 1 ROCKET
    # LAUNCHER (a magazine explosive launcher: magazine, reload, HUD, melee) firing a BOLT built on
    # the restored FUEL ROD's projectile (the yardstick: the Grunts' plasma bolt, its contrail,
    # sparks and light) and its explosion effect around own damage copies. DEFAULT = REACH's OWN
    # NUMBERS; the fuel rod ratio values are the balance rows.
    'pickable': {
        'weapon': CR + 'concussion rifle',
        'template': RL + 'rocket launcher',
        'world_model': CR + 'concussion rifle',
        'fp_model': CR + 'fp' + B + 'fp',
        'fp_anims': CR + 'fp' + B + 'fp',
        'label': 'cr',
        # the reserved pose donor: the plasma rifle (a Covenant rifle, carried by Elites)
        'teach': ('cr', 'pr'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'cr_ready',
                   'first-person posing': SND + 'cr_pose',
                   'first-person melee': SND + 'cr_melee',
                   'first-person reload-empty': SND + 'cr_reload',
                   'first-person reload-full': SND + 'cr_reload'},
        # THE BOLT. Reach: impact 21.5 (`collision`, accel 0.75) + the blast 0..21.5 over 1 -> 2
        # (core 0.8, plasma_fast, accel 2.5). The impact on a copy of the fuel rod explosion's table
        # with no radius (the yardstick's table: Hunters immune); the blast = the fuel rod's own
        # explosion effect around an own copy of its damage, lower bound by the sibling rule
        # (Reach 0 / unset: 40 x 21.5/75 = 11.5). Flight: Reach's own 12 -> 16 wu/s (the fit waits
        # for boot 1, user), air gravity 0.25, water 0.25, range 100
        'bullet': {'projectile': (FR + 'grunt fuel rod', CR + 'bolt'),
                   'damage': (FR + 'grunt explosion', CR + 'impact'),
                   'dmg': 21.5, 'acceleration': 0.75,
                   # HUNTERS (user, 2026-10-12: 'Use Reach's values for Hunters in default and
                   # offset in the balanced, like the other damage values'): the fuel rod's x0
                   # -> Reach's collision on hard_metal_thick 0.75 (armour), soft_organic 1 (skin)
                   'fields': {'radius': (0.0, 0.0),
                              'damage_modifiers.hunter_armor': 0.75,
                              'damage_modifiers.hunter_skin': 1.0},
                   'explosion': {'effect': (FR + 'effects' + B + 'grunt explosion', CR + 'effects' + B + 'bolt explosion'),
                                 'part': FR + 'grunt explosion',
                                 'out_dir': CR + 'effects' + B,
                                 'damage': (FR + 'grunt explosion', CR + 'explosion'),
                                 'lower': 11.47, 'upper': (21.5, 21.5), 'radius': (1.0, 2.0),
                                 # HUNTERS (user): Reach's plasma_fast on hard_metal_thick 0.25
                                 # (armour), soft_organic 1 (skin) in place of the fuel rod's x0
                                 'mods': {'hunter_armor': 0.25, 'hunter_skin': 1.0},
                                 # Reach's own knockback (user: the 7.5 proposal after boot 1)
                                 # 4b: active camo damage 1 x 1/0.9; AOE core: the H1 fuel rod's 0
                                 # (a zero on one side) -> Reach's own 0.8; category high explosive
                                 # kept (Reach's 'bullet' only reports)
                                 'fields': {'damage.instantaneous_acceleration': 2.5,
                                            'damage.active_camouflage_damage': 1.0 / 0.9,
                                            'damage.aoe_core_radius': 0.8},
                                 'swaps': {B.join(['sound', 'sfx', 'weapons', 'fuel rod gun', 'explosion']): SND + 'cr_explode'},
                                 # THE BLAST'S LOOK (boot 2, user: 'detonation size and color'):
                                 # Reach's detonation = explosive_flash (bounding 0.73 wu), sparks,
                                 # plasma_noise_long (0.48), violet; the fuel rod's burst is 1.5 wu
                                 # -> x0.5, its green `c fire` states and stealth-cannon flare violet
                                 'scale': 0.5,
                                 'psys_tint': {'fuelrod burst': ((1.0,) + VIOLET, (1.0,) + VIOLET_DEEP),
                                               'c energy smoke': ((0.65,) + VIOLET, (0.85,) + VIOLET_DEEP),
                                               'death': ((0.0,) + VIOLET_DEEP, (0.0,) + VIOLET_DEEP),
                                               # BOOT 3 (user): 'still all green' -- the map held the
                                               # violet states; the TYPE states `birth` / `death`
                                               # multiply every particle by the fuel rod's green
                                               # (1 / 0.14 / 1 / 0.02) -> white (the states colour)
                                               '@birth': (1.0, 1.0, 1.0, 1.0), '@death': (0.0, 1.0, 1.0, 1.0)},
                                 'particle_tint': VIOLET, 'tint_match': ('stealth cannon',)},
                   'velocity': (12.0, 16.0), 'range': 100.0,
                   # THE BOLT'S LOOK (boot 2): Reach's model glowing; the fuel rod's green contrail
                   # and green exhaust light dropped (the screenshot shows no trail); its trail
                   # sparks kept as an own copy tinted Reach violet-white; a PINK glow (the fuel
                   # rod exhaust light + flare recoloured, 0.2 wu: the screenshot's halo)
                   'model': CR + 'bolt' + B + 'bolt',
                   'keep_attachments': (1,),
                   # BOOT 2 (user): 'the bolt is still green, probably too big compared to the
                   # original of Reach; the blast is also still the green explosion' -- every tag
                   # was violet in the built map: Halo 1's `c` particles (the sparks' `c energy`,
                   # the blast's `c fire`) take the CREATING OBJECT's CHANGE COLOUR (the Beam Rifle's
                   # finding), and the fuel rod copy has none -> an own change colour, Reach violet
                   # (the plasma pistol bolt's block). Smaller: sparks x0.5 radius, x0.6 count
                   # (Reach's spark_ember 0.055 wu), the flare 0.2 -> 0.12 wu
                   'change_color': {'from': 'weapons' + B + 'plasma pistol' + B + 'bolt', 'rgb': VIOLET},
                   'set_attachments': {0: {'class': 'effect', 'type': FR + 'effects' + B + 'fuel rod tail sparks',
                                           'copy': {'out': CR + 'effects' + B + 'bolt sparks',
                                                    'tint': (1.0,) + ((1.0, 0.0, 0.0) if DIAG else VIOLET), 'scale': 0.5 * 0.75, 'count': 0.6}}},
                   # the GLOW BALL = the fuel rod's light volume, an own copy: white-pink at the
                   # core (hither), Reach pink outward (yon) -- the screenshot's hot core in a halo
                   # BOOT 7 (user): 'the flying projectile is blue now' -- the volume's sprite
                   # sheet (`flares pr overcharge`) is CYAN (bright 110 / 164 / 168, mid 36 / 85 /
                   # 88) and the tint multiplies it: per channel compensated, target / sprite
                   # normalised -- the halo Reach's mid pink 168 / 125 / 151 -> 1 / 0.31 / 0.37, the
                   # core white-pink -> 1 / 0.63 / 0.64 (red is capped by the sprite: dimmer)
                   # BOOT 8 (user): 'a lot whiter, but not pink at all' -- the volume draws
                   # ADDITIVELY in layers: every channel clipped -> white. The exact ratio (Reach
                   # pink 1 / 0.45 / 0.75 over the sprite's mid 0.41 / 0.97 / 1 -> 1 / 0.19 / 0.31)
                   # with the alpha (brightness) at 0.45 so the layers stop clipping; the core a
                   # little whiter
                   # BOOT 9 (user): 'Big success. Change its size for the final version to 75% of
                   # the current size' -> the volume, the flare and the sparks x0.75
                   'widget_tint': {'out': CR + 'bolt glow volume', 'hither': (0.45, 1.0, 0.45, 0.55),
                                   'yon': (0.45, 1.0, 0.19, 0.31), 'radius': 0.75},
                   'glow': {'light': (FR + 'fuel rod exhaust', CR + 'bolt glow'), 'flare': CR + 'bolt glow',
                            'rgb': (0.0, 0.0, 1.0) if DIAG else PINK, 'flare_radius': 0.12 * 0.75, 'marker': 'contrail'},
                   # BOOT 2 (user): 'the scorch mark can stay, the green plasma burn would be good to
                   # change' -> own copies of the fuel rod's impact effects with Halo 1's plain plasma
                   # burn (the Beam Rifle's swap)
                   # BOOT 4 (user): 'the bolt and burn stay green' -- read from the map: half the
                   # responses still named the fuel rod's effects (each names its effect twice: the
                   # nested POTENTIAL response kept the green burn) -> `potential`; and those impact
                   # effects carry their own particles -- `flare h stealth cannon` + `flash h shield
                   # impact` (tinted green), `tracer` / `smoke c generic` -- the green ball at the
                   # impact -> tinted Reach violet
                   'impact_tint': {'match': ('stealth cannon', 'shield impact', 'c generic'), 'rgb': VIOLET,
                                   'potential': True, 'out': CR + 'effects' + B + 'impact' + B,
                                   'decals': {B.join(['effects', 'decals', 'bullet holes', 'plasma green burn large']):
                                              B.join(['effects', 'decals', 'bullet holes', 'plasma burn large'])}},
                   'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.25,
                                   'proj_attrs.physics.water_gravity_scale': 0.25,
                                   # Reach's 11 -- in Halo 1 minimum velocity DETONATES (the Brute
                                   # Shot); the bolt never flies slower than 12 here, so Reach's
                                   # own value stays for boot 1 (user: defaults first)
                                   'proj_attrs.detonation.minimum_velocity': 11.0,
                                   # 4b list 3: the AI's danger radius -- the H1 fuel rod's 0 (a
                                   # zero on one side) -> Reach's own 0.5. Air damage range: Reach
                                   # 0,0 = unset -> the fuel rod's 0..100 kept (the GL's)
                                   'proj_attrs.detonation.danger_radius': 0.5,
                                   'proj_attrs.flags.oriented_along_velocity': True,
                                   'proj_attrs.flags.ai_must_use_ballistic_aiming': True},
                   'triggers': [0]},
        # Reach: fire recovery 0.333 s (rounds per second 0 = recovery-limited) = 3/s
        # 4b (Reach CR / Reach fuel rod onto the H1 fuel rod): illumination recovery 1.2 x 0.1/0.3
        # = 0.4; first person offset: the H1 fuel rod's 0 (a zero on one side) -> Reach's own
        'trigger': {'rounds_per_second': (3.0, 3.0), 'first_person_offset': (0.0, -0.025, -0.02),
                    'illumination_recovery_time': 0.4},
        # Reach: minimum error 0.15, error angle 0.4 / 0.4
        'error_deg': {'minimum_error': 0.15, 'error_angle': (0.4, 0.4)},
        # Reach: 6 loaded, 18 at pickup, 30 most, 6 reloaded (100 fr both; Halo 1 needs a number:
        # 3.33 s)
        'magazine': {'rounds_loaded_maximum': 6, 'rounds_reloaded': 6,
                     'rounds_total_initial': 18, 'rounds_total_maximum': 30,
                     'reload_time': 3.33},
        # Reach aim assist, absolute
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 8.0, 'magnetism_range': 15.0},
        'fields': {
            # Reach's concussion rifle has NO zoom; the rocket's 2x goes with its sounds
            'weap_attrs.aiming.zoom_levels': 0,
            'weap_attrs.interface.zoom_in_sound.filepath': '',
            'weap_attrs.interface.zoom_out_sound.filepath': '',
            # STEP 6: the rocket's ammo box ratio-scaled by the carry, 2 x 30/8 = 7.5 -> 7 (balanced
            # 6: the catalog row)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 7,
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'cr_dryfire',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'cr_ammo',
            'item_attrs.collision_sound.filepath': SND + 'cr_drop',
            'obje_attrs.collision_model.filepath': CR + 'concussion rifle',
            'obje_attrs.bounding_radius': 0.26,
            # 4b list 3: the item's acceleration scale (how far blasts throw it) 1.5 x 1/0.8 (Reach
            # CR / fuel rod onto the H1 fuel rod; the rocket template's 2.0)
            'obje_attrs.acceleration_scale': 1.875,
            # 4b list 3 (found in the final step check): active camo ding -- the H1 fuel rod's 0 (a
            # zero on one side) -> Reach's own 0.75 (the rocket template's 1.0 had stayed)
            'weap_attrs.interface.active_camo_ding': 0.75,
            'obje_attrs.attachments.0.type.filepath': CR + 'muzzle light'},
        # THE MUZZLE-FLASH RULE (closing check 10). Reach's FIRST-PERSON flash (fxiring.effect,
        # `1st_person`): glow_soft (bounding radius 0.106 wu), muzzle_flash_round (0.071, coloured by
        # muzzle_flare_concussion_rifle: VIOLET) and smoke_fiery_small (0.117), all at
        # primary_trigger, no sparks, no casing (+ the firing_1p light). BOOT 1 had the fuel rod's
        # green flash; USER: 'I think the muzzle flash is a normal plasma release' -> Halo 1's
        # PLASMA PISTOL `fire bolt` (the Carbine's precedent): `flash c generic` 0.04-0.05, two
        # sideways `med` fins at +-0.04 (dropped: Reach's flash is round), the front `med`
        # 0.065-0.08, `small` 0.15-0.25, smoke -- the flashes x0.7 (generic 0.03, med 0.05, small
        # 0.1-0.18 ~ Reach's glow), everything tinted Reach violet, its fire sound swapped
        'sound_effects': {
            'firing_effect': (RL + 'effects' + B + 'fire rocket', CR + 'effects' + B + 'fire bolt',
                              {B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'fire']): SND + 'cr_fire'},
                              {'copy_from': 'weapons' + B + 'plasma pistol' + B + 'effects' + B + 'fire bolt',
                               'match': 'flash c generic', 'drop_off_axis': 0.02, 'scale': 0.7,
                               'tint': (1.0,) + VIOLET})},
        # the MUZZLE LIGHT: the rocket's (the AR's yellow `muzzle flash`, its flash function kept) ->
        # an own copy in Reach violet (the plasma pistol's light colour slot)
        'own_light': {'shape': 'weapons' + B + 'assault rifle' + B + 'muzzle flash',
                      'look': 'weapons' + B + 'plasma pistol' + B + 'muzzle flash',
                      'out': CR + 'muzzle light', 'argb': (1.0,) + VIOLET},
        # the fuel rod's melee (Reach: strike_melee on both = x1 in both versions)
        'melee': (FR + 'melee', CR + 'melee'),
        'melee_response': RL + 'melee_response',
        'messages': ('Picked up a concussion rifle', 'Picked up %d rounds for concussion rifle'),
        'icon': 'concussion rifle',
        # the ROCKET's HUD with Reach's crosshair at the reserved 32. Reach's chud `elite_shot`:
        # `crosshair` = hud_reticles #17 at (0.85, 1.0), 'mirror horizontal' -- the sprite is ONE
        # crescent + three HALF drop triangles at its right edge; Reach draws it with its right
        # edge on the centre and its mirror image on the other side (the halves meet: whole
        # triangles). The sprite's registration is its box centre, the crescent sits in its top
        # half -> moved down 22.6 units onto the aim point (the screenshot centres it).
        # SIZED FROM THE USER'S REACH SCREENSHOT (1080p, 2026-10-12): the two crescents 88 x 38 px,
        # three fading triangles below. SUPERSAMPLED x2 (memory h1-reticle-supersample): scale 1.3,
        # the crescents 252 sheet px wide -> overlay 88 / (252 x 0.75) = 0.466; `split` 100 for the
        # dim triangles
        'hud': {'donor': RL + 'rocket_launcher', 'out': CR + 'concussion rifle',
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 17, 'concussion rifle'),
                'reticle_xform': {'stretch': (0.85, 1.0), 'offset': (-23.0, 22.6)},
                'reticle_layers': [(R + r'ui\chud\bitmaps\hud_reticles', 17, 1.0,
                                    {'flip_x': True, 'stretch': (0.85, 1.0), 'offset': (23.0, 22.6)})],
                'reticle_split': 100,
                'reticle_scale': 1.3, 'reticle_overlay': 88 / (252 * 0.75),
                'reticle_supersample': 2,
                'reticle_min_width': 2,
                'ammo_meter': {'sizes': (6, 5), 'base': CR + 'bitmaps' + B + 'concussion_rifle_ammo'},
                'flash_base': 2},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py concussion_rifle). DEFAULT = Reach's
    # own numbers in the tags; BALANCED = the FUEL ROD ratio (step 4a, user 2026-10-12). Assembly
    # Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Concussion Rifle', 'source': 'Halo Reach', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "Halo Reach's Concussion Rifle: its model, first-person animations, sounds and "
                    "numbers. Six plasma bolts a magazine, three a second; each bolt bursts on "
                    "contact and its blast knocks back whatever it catches, the wielder included.",
            'balance_desc': "Measured against the Fuel Rod: a heavier blast (27) without the impact "
                            "hit, about one bolt a second, five a magazine, slower bolts and a "
                            "stronger knockback.",
            'balance': [
                # the blast: 75 x 21.5/60 = 26.9, lower 40 x 26.9/75 = 14.3 (the sibling rule);
                # radius 0.5 x 1/0.5, 1.5 x 2/2.25; knockback 4 x 2.5/1.5
                row('jpt!', CR + 'explosion', 'Damage Lower Bound', 14.3, 11.47, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Damage Upper Bound', 26.9, 21.5, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Damage Upper Bound Max', 26.9, 21.5, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Radius', 1.0, 1.0, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Radius Max', 1.333, 2.0, 'Explosion Damage'),
                # MCC's Halo 1 plugin splits the field into a vector3: the legacy scalar is `i`
                # (boot 10: 'Instantaneous Acceleration' was 'not found in plugin')
                row('jpt!', CR + 'explosion', 'Instantaneous Acceleration i', 6.67, 2.5, 'Knockback'),
                # materials (user): the fuel rod's table x Reach's plasma_fast / explosion_large --
                # Elite / cyborg shield 1 x 1/0.75, Jackal shield 1 x 0.5/0.75; Hunters: Reach's
                # own values in both (the damage itself carries the offset; the fuel rod's 0 has no
                # ratio -- Reach's fuel rod 0.75 x 0.25/0.75 = 0.25 = default)
                row('jpt!', CR + 'explosion', 'Elite Energy Shield', 1.333, 1.0, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Cyborg Energy Shield', 1.333, 1.0, 'Explosion Damage'),
                row('jpt!', CR + 'explosion', 'Jackal Energy Shield', 0.667, 1.0, 'Explosion Damage'),
                # the impact: Halo 1's fuel rod has none -> 0 (a zero on one side)
                row('jpt!', CR + 'impact', 'Damage Lower Bound', 0.0, 21.5, 'Bolt Damage'),
                row('jpt!', CR + 'impact', 'Damage Upper Bound', 0.0, 21.5, 'Bolt Damage'),
                row('jpt!', CR + 'impact', 'Damage Upper Bound Max', 0.0, 21.5, 'Bolt Damage'),
                # 1.25 s x 0.333/0.4 = 1.04 s
                row('weap', CR + 'concussion rifle', 'Rounds Per Second', 0.96, 3.0, 'More Shooting', block='Triggers'),
                row('weap', CR + 'concussion rifle', 'Rounds Per Second Max', 0.96, 3.0, 'More Shooting', block='Triggers'),
                # 4 x 6/5 = 4.8 -> 5, 12 x 18/20 = 10.8 -> 11, 24 x 30/30
                row('weap', CR + 'concussion rifle', 'Rounds Loaded Maximum', 5, 6, 'Magazine', block='Magazines'),
                row('weap', CR + 'concussion rifle', 'Rounds Reloaded', 5, 6, 'Magazine', block='Magazines'),
                row('weap', CR + 'concussion rifle', 'Rounds Total Initial', 11, 18, 'Magazine', block='Magazines'),
                row('weap', CR + 'concussion rifle', 'Rounds Total Maximum', 24, 30, 'Magazine', block='Magazines'),
                # STEP 6: Reach has no concussion rifle ammo and Halo 1's fuel rod no pickup -> the
                # template's rocket box RATIO-SCALED by the carry (the Brute Shot's): 2 x 30/8 = 7.5
                # -> 7 (default), 2 x 24/8 = 6 (balanced)
                row('weap', CR + 'concussion rifle', 'Rounds', 6, 7, 'Ammo pickup', block='Magazines/Magazines'),
                # flight: 14 x 12/15 = 11.2, 5 x 16/6.5 = 12.3 (wu/s -> per tick); range 0 x 100/80
                # = 0 (none: the fuel rod's); gravity: no ratio (Reach's fuel rod 0.025)
                row('proj', CR + 'bolt', 'Initial Velocity', 11.2 / 30, 12.0 / 30, 'Projectile'),
                row('proj', CR + 'bolt', 'Final Velocity', 12.3 / 30, 16.0 / 30, 'Projectile'),
                # Maximum Range: NO ROW (boot 11 probe: 0 projectiles logged over 5 balanced shots --
                # the bolt was destroyed the tick it was made). The H1 fuel rod's 0 is UNSET (it
                # comes down by gravity), not a zero to carry over: a ratio on an unset field is
                # degenerate (the GL's air damage range) -> Reach's 100 in both versions
                # BOOT 10 (user): 'the bolt is invisible now' -- the balanced bolt starts at 11.2
                # wu/s, 0.2 above Reach's MINIMUM VELOCITY 11, which DETONATES in Halo 1 (the Brute
                # Shot): it burst at the muzzle. The ratio rule had no row for it: the H1 fuel rod's
                # 0 = a zero on one side -> 0 in balanced (default keeps Reach's 11, margin 1)
                row('proj', CR + 'bolt', 'Minimum Velocity', 0.0, 11.0 / 30, 'Projectile'),
                # aim: 8 x 6/8 (the rest x1)
                row('weap', CR + 'concussion rifle', 'Magnetism Angle', 6.0, 8.0, 'Magnetism'),
                # the 5 magazine's meter: concussion_rifle_ammo sequence 1 (ammo_meter 6 5), step 50
                # (default 42); flash at 1 x 5/2 = 2.5 -> 2 (default 1 x 6/2 = 3)
                dict(row('wphi', CR + 'concussion rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', CR + 'concussion rifle', 'Alpha Multiplier', 50, 42, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', CR + 'concussion rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', CR + 'concussion rifle', 'Loaded Ammo Cutoff', 2, 3, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port concussion_rifle): the source pair (Reach concussion
    # rifle vs the yardstick, Reach's fuel rod = flak_cannon) against the target pair (the H1 port
    # vs the H1 fuel rod)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\concussion_rifle.weapon', r'objects\weapons\support_high\flak_cannon\flak_cannon.weapon'),
                   'projectile': (RW + r'\projectiles\concussion_rifle_grenade.projectile',
                                  r'objects\weapons\support_high\flak_cannon\projectiles\flak_bolt.projectile'),
                   'damage_effect': (RW + r'\projectiles\damage_effects\concussion_rifle_grenade_explosion.damage_effect',
                                     r'objects\weapons\support_high\flak_cannon\projectiles\damage_effects\flak_bolt_explosion.damage_effect'),
                   'impact': (RW + r'\projectiles\damage_effects\concussion_rifle_grenade_impact.damage_effect',
                              r'objects\weapons\support_high\flak_cannon\projectiles\damage_effects\flak_bolt_impact.damage_effect')},
        'target': {'weapon': (CR + 'concussion rifle.weapon', FR + 'fuel rod.weapon'),
                   'projectile': (CR + 'bolt.projectile', FR + 'grunt fuel rod.projectile'),
                   'damage_effect': (CR + 'explosion.damage_effect', FR + 'grunt explosion.damage_effect'),
                   'impact': (CR + 'impact.damage_effect', FR + 'grunt explosion.damage_effect')}},

    # the dry test: a30, Reach's own loadout (6 + 18)
    'test': {'level': 'a30', 'rounds': (6, 18), 'grunt': None, 'elite': None},
})

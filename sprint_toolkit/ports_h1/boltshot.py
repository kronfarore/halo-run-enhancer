r"""Boltshot (Halo 4, wave C3): a Forerunner MAGAZINE sidearm with a CHARGED BLAST, on a copy of the
Halo 1 PISTOL (the template: its magazine, reload, HUD, melee) with Halo 1's CHARGED TRIGGER PAIR
added (`add_triggers`, the Grenade Launcher's way): a tap fires the bolt (trigger 0), a full charge
fires the blast (trigger 1). The Halo 4 route is the Storm Rifle's (storm_rifle.py: `h4:` paths,
Foundry FP decode + arm re-solve on the shared storm_fp skeleton).

HALO 4 (H4EK 2026-10-14, h3_weapon_values --kit h4 + the export): ONE trigger, latch-autofire with a
charge -- a tap fires barrel 0 (the BOLT: 7.5 bullet_slow, recovery 0.1 s, 2700 wu/s, range 40, no
falloff, error 0.4 -> 2 deg); held 0.6 s it charges, then stays charged 0.8 s and DISCHARGES (fires
by itself); a charged release fires barrel 1 (the BLAST: ONE projectile with a 5 x 3 `conical spread`
= 15 pellets in a 3.5 deg grid, 10 a pellet falling to 6 over 2.5 -> 4 wu, bullet_slow / category
shotgun, 480 wu/s, range 5.5, recovery 1.0 s, FIVE ROUNDS a blast). Magazine 10 (30 / 40), reload
51 fr (reload_full only), aim (mode block) 2.25/20 5/20, strike_melee.

THE APPROXIMATION (step 4a, user): Halo 1's charged pair. Not reproduced: the fixed 5 x 3 pellet GRID
(Halo 1 scatters projectiles at random inside the error cone), the charging rumble; a blast with
fewer than 5 rounds loaded (measure what Halo 1 does); the AI never fires the charged trigger (B4)."""
import math

from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\pistol\storm_stasis_pistol'
SFP = r'objects\characters\storm_fp\weapons\pistol\fp_stasis_pistol\storm_fp_stasis_pistol'
SBM = SW + r'\bitmaps\storm_stasis_pistol_default' + B
BO = 'weapons\\boltshot\\'
SND = 'sound\\weapons\\boltshot_port\\'
PISTOL = 'weapons\\pistol\\'
SG = 'weapons\\shotgun\\'
PP = 'weapons\\plasma pistol\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

# the Storm Rifle's DROP list: every storm_fp graph shares the skeleton (checked 2026-10-14: the
# Boltshot graph's 97 bones = the Storm Rifle's arms + its own 16 gun bones)
from .storm_rifle import DROP  # noqa: E402

# the render model's 17 nodes, all animated by the FP graph
GUN_NODES = ('b_gun', 'b_low_a', 'b_top_a', 'b_top_c', 'b_right_capsule', 'b_left_capsule',
             'b_right_top_plate', 'b_cartridge', 'b_left_top_plate', 'b_fx_end', 'b_low_b', 'b_top_b',
             'b_left_low_plate', 'b_low_pipe', 'b_low_c', 'b_right_low_plate', 'b_top_lever')

PORT = reserved(
    order=28, wave='C3', name='Boltshot', source='Halo 4',
    messages=(89, 90), icon=48, reticle=37, label='bo', teach_from='pp',
    sound_dir='sound\\weapons\\boltshot_port', weapon_dir='weapons\\boltshot',
    yardstick={
        # step 4a (user, 2026-10-14; h1_role_compare.py boltshot): a ratio PER MODE
        'pick': 'Pistol (bolt) + Shotgun (blast)',
        'reason': ("two modes, two yardsticks. The BOLT by the PISTOL (a magazine sidearm, the same "
                   "damage family: bullet_slow on the Magnum and the Boltshot). The BLAST by the "
                   "SHOTGUN: Halo 4's own shotgun is a near-twin (the same 5 x 3 cone of 15 pellets, "
                   "480 wu/s, 1.0 s recovery, 10.5 vs 10 a pellet). Halo 4's 0.6 s CHARGE is KEPT (no "
                   "yardstick charges -- B6's rule; Halo 1's plasma pistol charges 0.6 s too). The "
                   "bolt's RANGE kept Halo 4's 40 (the ratio 40 x 40/250 = 6.4 is degenerate: the "
                   "Magnum's 250; 40 is also Halo 1's pistol's). Balanced magazine 15 -> 7 ROUNDS a "
                   "blast (two blasts a magazine, as Halo 4's 10 / 5). DEFAULT = Halo 4's own numbers"),
        # DEFAULT = Halo 4's own; BALANCED: bolt = H1 pistol x Boltshot / H4 magnum, blast = H1
        # shotgun x blast / H4 shotgun. H4 magnum 15 bullet_slow, 0.2 s, 8 (24 / 40), 3000 wu/s,
        # range 250, error 0.15 -> 1.75, reload_empty 51 fr, aim 2.25/20 5/20; H4 shotgun 15 pellets
        # x 10.5 (lower 3 over 1.5 -> 3.75), 480, range 6.5, 1.0 s, cone 3 deg. H1 pistol 25 x 3.5/s,
        # 12 (60 / 120), 300 wu/s, range 40, error 0.2 -> 2, reload 67 fr, aim 3/30 6/30; H1 shotgun
        # 15 x 21.5 (lower 8 over 1.5 -> 3), 1/s, 140 -> 100 wu/s, range 40, error 10
        'balanced': {
            'bolt_damage': 12.5,            # 25 x 7.5/15
            'bolt_rate': 7.0,               # 3.5 x 0.2/0.1
            'magazine': 15,                 # 12 x 10/8
            'ammo': (75, 120),              # 60 x 30/24, 120 x 40/40
            'reload': 'x1',                 # 67 fr x 51/51
            'bolt_velocity': 270.0,         # 300 x 2700/3000
            'bolt_range': 40.0,             # Halo 4's own (ratio degenerate: 6.4)
            'bolt_error': (0.53, 2.29),     # 0.2 x 0.4/0.15, 2 x 2/1.75
            'aim': 'x1',                    # the same mode block: Halo 1's pistol 3/30 6/30
            'blast_damage': 20.48,          # 21.5 x 10/10.5 a pellet
            'blast_lower': 16.0,            # 8 x 6/3
            'blast_damage_range': (2.5, 3.2),  # 1.5 x 2.5/1.5, 3 x 4/3.75
            'blast_error': 11.67,           # 10 x 3.5/3
            'blast_velocity': (140.0, 100.0),  # x 480/480
            'blast_range': 33.8,            # 40 x 5.5/6.5
            'blast_recovery': 1.0,          # 1.0 x 1.0/1.0
            'charge': 0.6,                  # KEPT (no yardstick charges)
            'rounds_per_blast': 7,          # 15 / 2 (user)
            'melee': None},                 # Halo 4 shares strike_melee: x1
        'measured': 'h1_role_compare.py boltshot',
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol',
            'provisional': 'Pistol (bolt) + Shotgun (charged blast)',
            'alternatives': ['Plasma Pistol'],
            'direct': None,
            'peers': ['Pistol', 'Plasma Pistol', 'Shotgun', 'Mauler (port)'],
            'why': 'magazine 10 semi-auto bolt; a 0.6 s charge fires a 15-pellet blast for 5 rounds: a ratio per mode',
            'lacks': ("the fixed 5 x 3 pellet grid (Halo 1: random inside the error cone); the "
                      "charging rumble; the AI's charged shot (Halo 1's AI only taps a charged pair)")}},
    # step 11: Halo 4's ai\generic Boltshot entry (m020) over a base -- 'bo' has no carrier. Halo 1's
    # PLASMA PISTOL carriers (h1_weapon_carriers, 2026-10-14): Grunt minor / major / flee, Jackal
    # minor / major, the engineer 0.5; Flood combat (both) 0.4 -- Halo 1's sidearm of the
    # Covenant (the human pistol: crewmen / Flood only). Donor = the JACKAL MINOR plasma pistol (one
    # donor for every slot, B3's choice; the species skill rule gives each slot its own species'
    # aim). WDM RULE: 0.5 x the BOLT's yardstick player dps (the pistol 25 x 3.5 = 88,
    # h1_role_compare boltshot) / the port's tapped bolt (default 7.5 x 10 = 75, balanced 12.5 x 7
    # = 87.5) -- Halo 1's AI only taps a charged pair (B4): the bolt is what it fires
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol',
                    'donor_weapon': 'weapons\\plasma pistol\\plasma pistol',
                    'donor_variant': 'characters\\jackal\\jackal minor plasma pistol',
                    'wdm_rule': {'base': 0.5, 'yardstick_dps': 88.0, 'port_dps': 75.0,
                                 'balanced_port_dps': 87.5},
                    # dry run (2026-10-14): ai\generic #21, WDM 0.5867 / 0.5029 (balanced), drop 0.7-0.9.
                    # THE BALANCED DROP RULE: Halo 1's plasma-pistol carriers drop 0.7 - 0.9 x Halo 4
                    # Boltshot 0.7 - 0.9 / Halo 4 plasma pistol 0.7 - 0.9 (m020 ai\generic) = 0.7 - 0.9
                    'balanced_set': ['0x1D8=0.7:Drop Weapon Loaded', '0x1DC=0.9:Drop Weapon Loaded Max'],
                    'species_skill': True},
)

PORT.update({
    'status': 'in_progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). Halo 4's ONE render model for
    # world AND first person: 17 nodes (b_gun root), 3 permutations = SKINS (default / piston /
    # engine; the export's piston / engine meshes are EMPTY: 7238 verts either way). Markers: primary_trigger (0.140 / 0 /
    # 0.011), left_hand, fx_vent x2, buckshot x8 (the blast's spark points). Materials (H4
    # .material): alien_metal / metal (diff + control + normal), glow (srf_char_blinn_reflection_
    # selfillum: si 1, 0.91, 0.18 x50 on the diffuse -- the Forerunner orange)
    'model': {
        'dir': r'weapons\boltshot',
        'world': H4 + SW + r'\storm_stasis_pistol.render_model',
        'fp': H4 + SW + r'\storm_stasis_pistol.render_model',
        'world_name': 'boltshot',
        # DECIMATION (h1_decimate, 2026-10-14; H1_PORT_PLAN 0.1): the side view broke at 40 (holes,
        # slabs), 50 / 60 (lumps), 70 (a dark sliver in the slide); 80 intact (max 1.07 mm) ->
        # 9150 -> 7320 triangles, ~0.44 -> 0.36 MiB of the model buffer (a small gun: little to gain)
        'decimate': {'keep': 80.0, 'protect': 1.0, 'views': [((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 1.0), ((-0.1982, 0.066, 0.058), (0.995, -0.0669, -0.0743), (0.0741, -0.0051, 0.9972), 1.0), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 1.0), ((0.0735, 0.0, -0.0154), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), 1.0), ((0.0735, 0.0003, -0.0154), (0.0016, -0.0156, 0.9999), (-0.0075, 0.9999, 0.0156), 1.0), ((0.0735, 0.0003, -0.0154), (-0.0057, -0.003, 1.0), (0.004, 1.0, 0.003), 1.0), ((-0.1964, 0.0648, 0.0656), (0.9924, -0.0657, -0.1042), (0.103, -0.0222, 0.9944), 1.0), ((-0.1908, 0.0647, 0.0545), (0.996, -0.0662, -0.0591), (0.0601, 0.0122, 0.9981), 1.0), ((-0.1964, 0.0648, 0.0656), (0.9924, -0.0657, -0.1042), (0.103, -0.0222, 0.9944), 1.0), ((-0.1229, 0.1737, -0.1246), (0.0425, -0.1285, 0.9908), (-0.8578, 0.5037, 0.1022), 0.5), ((-0.1571, 0.0639, 0.1282), (0.9086, -0.0148, -0.4173), (0.4137, 0.168, 0.8948), 0.5), ((-0.1229, 0.1737, -0.1246), (0.0425, -0.1285, 0.9908), (-0.8578, 0.5037, 0.1022), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5), ((-0.1341, 0.1522, 0.1608), (0.7904, -0.3336, -0.5138), (0.5472, 0.0072, 0.837), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5), ((-0.1341, 0.1522, 0.1608), (0.7904, -0.3336, -0.5138), (0.5472, 0.0072, 0.837), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5), ((-0.0558, -0.0274, 0.1748), (0.8245, 0.56, 0.0817), (0.3226, -0.5837, 0.7452), 0.5), ((-0.1988, 0.0651, 0.0576), (0.9957, -0.0667, -0.0647), (0.0635, -0.0195, 0.9978), 0.5)]},
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent', 'primary_trigger': 'primary trigger'},
        'ground_point': 'auto',
        # an own hull from the world model's extent (h1_box_collision; the Storm Rifle's boot 1:
        # the template's hull hid the world model) -- set from the built JMS extent
        'collision': {'material': 'metal',
                      # the world model's extent (JMS, wu): x -0.017..0.161, y +-0.015, z -0.037..0.067
                      'boxes': [((-0.017, -0.015, -0.037), (0.161, 0.015, 0.067))]},
        'material_names': {'storm_stasis_pistol_' + k: 'bo_' + k for k in (
            'alien_metal', 'metal', 'glow')},
        'shaders': {'bo_alien_metal': (H4 + SBM + 'storm_stasis_pistol_diff.bitmap', None),
                    'bo_metal': (H4 + SBM + 'storm_stasis_pistol_diff.bitmap', None)},
        'template': PISTOL + r'fp\shaders\silver',     # the pistol's reflective metal
        'glow': {},
        'glow_shaders': {'bo_glow': {'rgb': (1.0, 0.91, 0.18), 'additive': True, 'islands': True,
                                     'islands_of': 'storm_stasis_pistol_glow'}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's OWN storm_fp_stasis_pistol (the Storm
    # Rifle's recipe), decoded by Foundry (h4_fp_dump.py: 38 animations, 97 bones). fire_1 var1 /
    # var2 12 fr (the bolt), fire_2 22 (the blast), overcharge 2 (the transition) / overcharged 35
    # (the held charge = Halo 1's `overcharged` slot, the plasma pistol's), idle 90, posing var0
    # 141 / var1 75, ready 17 (ready_initial 25), put_away 5, melee_strike_1 37 (primary 4) / _2 35,
    # reload_full 51 (NO reload_empty: both Halo 1 reloads), throw_grenade 45, moving 21, look 10;
    # overheat leftovers (overheated / o_h_exit / *_overheated: the Boltshot has no heat), sprint,
    # jump, land, fall: no Halo 1 state
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_stasis_pistol.render_model',
        'nodes': {n[2:]: 'frame ' + n.replace('_', ' ') for n in GUN_NODES},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\boltshot\fp',
        'h1_model': r'weapons\boltshot\fp\fp',
        'align': 'same_space',
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:fire_2': 'first-person fire-2',
            'first_person:overcharged': 'first-person overcharged',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
        # Halo 4 has one reload: Halo 1's reload-empty plays the same (`also_as`)
        'also_as': {'first-person reload-empty': 'first_person:reload_full'},
    },

    # Halo 4's own sounds (h1_port_sounds.py boltshot, `bank` 'halo4'). The player bank
    # forerunner_bolt_pistol_player (the weapon's .sound tags name it; the FP graph's
    # frame_event_list for the animation cues). HIRC (2026-10-14): fire = a random crack of 2 [0, 1]
    # + body 2 + a random tail of 2 [3, 4] (+ a 30 ms haptic click 5: dropped); charged_fire = a
    # random blast of 3 [0-2] + body 3; charge_in (the charge loop's `in`) = a random whine of 3 [0-2]
    # + a 6 s hum 3 + random foley [4, 5]; ready / melee_strike_1 / reload_full = random of 2;
    # posing var1 = a @0, b @27, c @62 (pose1's own event is empty in MCC); dry fire 1. Levels =
    # the active RMS of the stock Halo 1 sound each stands in for (h1_stock_sound_levels): pistol
    # fire -12.8, dryfire -15.3, pistol_ready -15.2, pistol_melee -19.8, pistol_reload -19.0,
    # pistol_posing -26.5, shotgun fire -16.7, plasma rifle charge -11.2, pistol drop -28.8
    'sounds': {
        'catalog': 'Boltshot',
        'bank': 'halo4',
        'wwise_bank': 'forerunner_bolt_pistol_player',
        'dir': B.join(['sound', 'weapons', 'boltshot_port']),
        'sounds': {
            'bo_fire': (['play_wea_forerunner_bolt_pistol_player_fire:0,1',
                         'play_wea_forerunner_bolt_pistol_player_fire:2',
                         'play_wea_forerunner_bolt_pistol_player_fire:3,4'],
                        'sound\\sfx\\weapons\\pistol\\fire', -12.8),
            'bo_blast': (['play_wea_forerunner_bolt_pistol_player_charged_fire:0,1,2',
                          'play_wea_forerunner_bolt_pistol_player_charged_fire:3'],
                         'sound\\sfx\\weapons\\shotgun\\fire', -16.7),
            # the held charge: the 6 s hum (charge_in 3) as a seamless loop (`slice` its sustain)
            'bo_charge_loop': (['play_wea_forerunner_bolt_pistol_player_charge_in:3'],
                               'sound\\sfx\\weapons\\plasma rifle\\charge', -11.2),
            'bo_dryfire': (['play_wea_forerunner_bolt_pistol_player_dry_fire'],
                           'sound\\sfx\\weapons\\pistol\\dryfire', -15.3),
            'bo_ready': (['play_weapons_stasis_pistol_ready:0,1'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'bo_melee': (['play_weapons_stasis_pistol_melee_strike_1:0,1'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_melee', -19.8),
            'bo_reload': (['play_wea_stasis_pistol_reload_full:0,1'],
                          'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'bo_pose': (['play_bolt_first_person_posing_var1_player_a',
                         'play_bolt_first_person_posing_var1_player_b',
                         'play_bolt_first_person_posing_var1_player_c'],
                        'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'bo_drop': (['play_wea_drop_pistol_fr_bolt_pistol_nonplayer'],
                        'sound\\sfx\\impulse\\weapon_drops\\pistol_impact', -28.8),
        },
        'offsets': {'bo_pose': [0.0, 27 / 30.0, 62 / 30.0]},
        'slice': {'bo_charge_loop': (2.0, 4.0)},
        'loop_len': {'bo_charge_loop': 1.5},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only boltshot) on a COPY of the Halo 1 PISTOL (the bolt's
    # yardstick: magazine, reload, HUD, melee, bullet materials) with the CHARGED PAIR: trigger 1 =
    # a copy of trigger 0 (`add_triggers`); trigger 0 charges 0.6 s, holds 0.8 s, then DISCHARGES
    # (Halo 4's overcharged action) -- a tap fires trigger 0 (the bolt), a full charge released or
    # held past the hold fires trigger 1 (the blast). DEFAULT = HALO 4's OWN NUMBERS; the ratio
    # values are the balance rows. Template layout (the BR's reading): the pistol exports A =
    # illumination, nothing on B -> B in = primary charged (the charge loop's scale)
    'pickable': {
        'weapon': BO + 'boltshot',
        'template': PISTOL + 'pistol',
        'world_model': BO + 'boltshot',
        # ONE model tag for world AND first person (user, 2026-10-14; the Suppressor's rule): Halo 1's
        # map builder crashes past 32 MiB of model vertices + indices (memory
        # h1-model-buffer-32mib-cap); fp\fp.gbxmodel is still written for the FP tools
        'fp_model': BO + 'boltshot',
        'fp_anims': BO + 'fp\\fp',
        'label': 'bo',
        'teach': ('bo', 'pp'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'bo_ready',
                   'first-person posing': SND + 'bo_pose',
                   'first-person melee': SND + 'bo_melee',
                   'first-person reload-empty': SND + 'bo_reload',
                   'first-person reload-full': SND + 'bo_reload'},
        'add_triggers': [0],
        # THE BOLT (trigger 0, a tap): Halo 4 storm_stasis_pistol_bolt 7.5 (lower = upper),
        # bullet_slow, instantaneous acceleration 0.1, 2700 wu/s flat, range 40 (air damage range
        # 0..40: no falloff). The pistol bullet's table (bullet_slow both sides)
        'bullet': {'projectile': (PISTOL + 'bullet', BO + 'bolt'),
                   'damage': (PISTOL + 'bullet', BO + 'bolt'),
                   'dmg': 7.5, 'acceleration': 0.1, 'velocity': 2700.0, 'range': 40.0,
                   'proj_fields': {'proj_attrs.physics.air_damage_range': (0.0, 40.0)},
                   # THE HIT-EFFECT RULE: max(default 10/s, balanced 7/s)
                   'impact_thin': {'materials': [22], 'out': BO + 'effects\\impact\\',
                                   'thin': {}, 'rate': 10.0},
                   'triggers': [0]},
        # THE BLAST (trigger 1, a full charge): Halo 4's charged_blast = ONE projectile of 15
        # pellets (5 x 3 grid, 3.5 deg) -> 15 projectiles a shot inside a 3.5 deg cone; a pellet 10,
        # lower 6 over 2.5 -> 4 wu (bullet_slow / shotgun: the shotgun pellet's table), 480 wu/s,
        # range 5.5. On a copy of Halo 1's shotgun PELLET
        'projectiles': [{
            'projectile': (SG + 'pellet', BO + 'pellet'),
            'damage': (SG + 'pellet', BO + 'pellet'),
            'dmg': 10.0, 'acceleration': 0.1, 'velocity': 480.0, 'range': 5.5,
            'fields': {'damage.damage_lower_bound': 6.0},
            'proj_fields': {'proj_attrs.physics.air_damage_range': (2.5, 4.0)},
            # the blast lands 15 pellets at once, ~1/s: the shotgun's per-hit effect at its rate
            'impact_thin': {'materials': [22], 'out': BO + 'effects\\impact\\pellet ',
                            'thin': {}, 'rate': 1.0},
            'triggers': [1]}],
        # THE BOLT RATE: Halo 4 recovery 0.1 s (rounds per second 30 = recovery-limited) = 10/s
        'trigger': {'rounds_per_second': (10.0, 10.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0},
        # Halo 4: minimum error 0, error angle 0.4 -> 2 (bloom decel 0.5)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.4, 2.0)},
        # Halo 4: 10 loaded, 30 at pickup, 40 most, 10 reloaded. Reload time: Halo 4 none (the
        # animation's 51 fr = 1.7 s) in the H1 pistol's shape (2.17 tag over its 2.23 s animation)
        'magazine': {'rounds_loaded_maximum': 10, 'rounds_reloaded': 10,
                     'rounds_total_initial': 30, 'rounds_total_maximum': 40,
                     'reload_time': 1.7 * 2.17 / 2.23},
        # Halo 4 aim assist: the MODE block (the live one), absolute; no zoom
        'aiming': {'autoaim_angle': 2.25, 'autoaim_range': 20.0,
                   'magnetism_angle': 5.0, 'magnetism_range': 20.0},
        # THE CHARGE CUE: Halo 4's charge loop (its `in` = the hum) at the muzzle, scaled by the
        # charge (B out = primary charged, the plasma pistol's function 3 `one` x B in)
        'fire_loop': {'like': B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charging']),
                      'start': '', 'loop': SND + 'bo_charge_loop', 'end': '',
                      'tag': SND + 'bo_charging', 'marker': 'primary trigger', 'scale': 'B_out'},
        'obje_functions': [{'from': PISTOL + 'pistol', 'index': 0},
                           {'from': PP + 'plasma pistol', 'index': 3}],
        'fields': {
            'weap_attrs.B_in': 'primary_charged',
            # THE CHARGE (Halo 4: charging 0.6 s, charged 0.8 s, overcharged action discharge)
            'weap_attrs.triggers.0.charging.charging_time': 0.6,
            'weap_attrs.triggers.0.charging.charge_hold_time': 0.8,
            'weap_attrs.triggers.0.charging.overcharged_action': 'discharge',
            'weap_attrs.triggers.1.charging.charging_time': 0.0,
            'weap_attrs.triggers.1.charging.charge_hold_time': 0.0,
            'weap_attrs.triggers.1.charging.overcharged_action': 'none',
            # THE BLAST trigger: 15 projectiles a shot, 5 rounds a shot, Halo 4's 1.0 s recovery
            'weap_attrs.triggers.1.firing.rounds_per_second': (1.0, 1.0),
            'weap_attrs.triggers.1.firing.rounds_per_shot': 5,
            'weap_attrs.triggers.1.projectile.projectiles_per_shot': 15,
            'weap_attrs.triggers.1.projectile.distribution_function': 'point',
            'weap_attrs.triggers.1.projectile.minimum_error': 0.0,
            'weap_attrs.triggers.1.projectile.error_angle': (math.radians(3.5), math.radians(3.5)),
            # Halo 4 has no zoom: the pistol's 2x goes, its zoom sounds with it (the GL)
            'weap_attrs.aiming.zoom_levels': 0,
            'weap_attrs.interface.zoom_in_sound.filepath': '',
            'weap_attrs.interface.zoom_out_sound.filepath': '',
            # the blast's own firing effect (sound_effects re-points every trigger naming the
            # pistol's `fire bullet` to the bolt's; `fields` run last)
            'weap_attrs.triggers.1.firing_effects.0.firing_effect.filepath': BO + 'effects\\fire blast',
            'item_attrs.collision_sound.filepath': SND + 'bo_drop',
            'obje_attrs.collision_model.filepath': BO + 'boltshot',
        },
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Halo 4's FIRST-PERSON particles
        # (fx\firing.effect, camera mode 'only in first person'): at primary_trigger muzzle_flash
        # 0.072 + muzzle_flash_diamond 0.071 + flash_large 0.141 wu + rings 0.009-0.010, ALL
        # on-axis, NO smoke; the rest sparkles on the gun body (rails / slides / vent 0.006-0.052:
        # markers Halo 1's model does not carry). The pistol's (h1_effect_particles): two SIDE
        # flashes 0.035-0.05 at +-0.023 wu angled 65 deg, a centre 0.045-0.056, smoke 26-35 x
        # 0.08-0.135, a casing. -> side flashes dropped (`drop_off_axis`), the centre x1.5 (0.07-
        # 0.085 ~ Halo 4's two flashes), smoke and casing dropped (a Forerunner gun: no casing, no
        # eject sound), tinted the gun's Forerunner orange (si 1, 0.91, 0.18)
        # THE BLAST (fx\charged_concussion): plate flashes 0.10-0.21 wu (top / bottom plates), a
        # soft glow 0.21 at the muzzle, a forward energy wave (2.6 wu), no smoke -> the SHOTGUN's
        # flash (flash h generic 0.100-0.125 + its sparks trail) without smoke / casing, tinted;
        # its fire sound kept once (the shotgun plays it in both events: the Brute Shot's
        # drop_event_parts)
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', BO + 'effects\\fire bolt',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'bo_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.5,
                               'drop_particles': ('casing', 'smoke'),
                               'drop_parts': [r'sound\sfx\weapons\pistol\eject'],
                               'tint': (1.0, 1.0, 0.91, 0.18)}),
            'firing_effect@1': (PISTOL + 'effects\\fire bullet', BO + 'effects\\fire blast',
                                {r'sound\sfx\weapons\shotgun\fire': SND + 'bo_blast'},
                                {'copy_from': SG + 'effects\\shotgun firing',
                                 'drop_particles': ('casing', 'smoke'),
                                 'drop_event_parts': {1: [r'sound\sfx\weapons\shotgun\fire']},
                                 'tint': (1.0, 1.0, 0.91, 0.18)}),
            'empty_effect': (PISTOL + 'effects\\empty', BO + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'bo_dryfire'})},
        'melee': (PISTOL + 'melee', BO + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a boltshot', 'Picked up %d rounds for boltshot'),
        'icon': 'boltshot',
        'hud': {'donor': PISTOL + 'pistol', 'out': BO + 'boltshot',
                'flash_base': 12,                # the pistol's low-ammo cutoff is of 12
                'ammo_meter': {'sizes': (10, 15), 'base': BO + 'bitmaps\\boltshot_ammo'}},
        'palette_levels': LEVELS,
    },

    # step 4b (port_field_audit.py --port boltshot): the source pair (Halo 4 Boltshot vs the bolt's
    # yardstick, Halo 4's magnum) against the target pair (the H1 port vs its template, the pistol)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_stasis_pistol.weapon',
                              r'objects\weapons\pistol\storm_magnum\storm_magnum.weapon'),
                   'projectile': (SW + r'\projectiles\storm_stasis_pistol_bolt.projectile',
                                  r'objects\weapons\pistol\storm_magnum\projectiles\storm_magnum_bullet.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_stasis_pistol_bolt.damage_effect',
                                     r'objects\weapons\pistol\storm_magnum\projectiles\damage_effects\storm_magnum_bullet.damage_effect')},
        'target': {'weapon': (BO + 'boltshot.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (BO + 'bolt.projectile', PISTOL + 'bullet.projectile'),
                   'damage_effect': (BO + 'bolt.damage_effect', PISTOL + 'bullet.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 3)
    'test': {'level': 'b30', 'rounds': (10, 30), 'grunt': None, 'elite': None},
})

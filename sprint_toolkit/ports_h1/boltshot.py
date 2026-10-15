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
BR4 = r'ui\hud\weapons\forerunner\burst_gun\bitmap' + B      # Halo 4's crosshair art (CUI)
# the base maps (boot 1): RGB = Halo 4's colour map x the material's albedo_tint, A = the control
# map's R (specular) -- written by this snippet (2026-10-14), kept beside the kit data:
#   d = h4_tags.bitmap_images(SBM + 'storm_stasis_pistol_diff.bitmap')[0]; c = ... '_control' ...
#   rgb = d.rgb x 0.706 (alien metal) / 0.78 (metal); a = c.R
BASE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\boltshot\source' + B
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
                      "charging rumble; the AI's charged shot (Halo 1's AI only taps a charged pair); "
                      "the full magazine of bolts: Halo 1 auto-reloads once fewer rounds are loaded "
                      "than the blast costs (boot 2: 6 bolts of 10, 4 left) -- the user kept Halo 4's "
                      "5 a blast (balanced 7: 9 bolts of 15)")}},
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
    'status': 'done',             # 2026-10-15: 6 dry boots, balanced, Armed (grunt, jackal, elite) on b30
    # CLOSE-OUT RECORD (2026-10-15): port_refs_audit on the built b30 test map 0 problems (own bolt /
    # pellet / melee; the pistol's melee response + trigger feedback GLOBAL); port_sound_refs: every
    # sound own but the ammo PICKUP, a KEEP (user, boot 1: Halo 4's ammo_pickup_generic tag is empty);
    # step 4b (port_field_audit) list 2 = the balance rows + the non-card fields applied (water
    # gravity / damage range, camo, breaking effect), list 3 decided (the overheat; the bounding
    # radius / deviation angle kept the template's, the Storm Rifle's reading); template diff traced
    # to the config's decisions; the muzzle-flash rule (check 10) done and boot-tuned; THE HIT-
    # EFFECT RULE on both projectiles (bolt 10/s x0.19, pellets 1/s x1); step 11 profile + species
    # skill; Armed confirmed (user)
    'sound_keeps': {r'sound\sfx\weapons\weapon_pickup_ammo\pistol_ammo':
                    "Halo 4 has no ammo pickup sound (ammo_pickup_generic is empty): user, boot 1"},

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
        # + Halo 4's charging-effect locations (its `charging` effect: plate glows at top_plate /
        # bottom_plate, a vent glow at fx_vent, the core at the muzzle) for the CHARGE GLOW below
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent', 'primary_trigger': 'primary trigger',
                    'top_plate': 'top plate', 'bottom_plate': 'bottom plate', 'sight': 'sight'},
        'ground_point': 'auto',
        # an own hull from the world model's extent (h1_box_collision; the Storm Rifle's boot 1:
        # the template's hull hid the world model) -- set from the built JMS extent
        'collision': {'material': 'metal',
                      # the world model's extent (JMS, wu): x -0.017..0.161, y +-0.015, z -0.037..0.067
                      'boxes': [((-0.017, -0.015, -0.037), (0.161, 0.015, 0.067))]},
        'material_names': {'storm_stasis_pistol_' + k: 'bo_' + k for k in (
            'alien_metal', 'metal', 'glow')},
        # BOOT 1 (user: 'the gun is missing its texture' -- it drew WHITE): the colour map's alpha
        # is solid, so Halo 1's reflection mask (multipurpose R = the base map's alpha) was 255
        # everywhere: full chrome. Halo 4 keeps specular in the CONTROL map (control_map_spglrf: R
        # specular, G gloss, B reflection). Base maps built from both (the Suppressor's route, a
        # prepared PNG as the base map): RGB = the colour map x albedo_tint (alien metal 0.706, metal
        # 0.78), A = the control map's R (specular: lit edges, a dark body); built by
        # BASE_MAPS below. Template: the AR's gun shader (the Suppressor's, user-approved; the
        # pistol's `silver` is a mirror)
        'shaders': {'bo_alien_metal': (BASE + 'bo_alien_metal_base.png', None),
                    'bo_metal': (BASE + 'bo_metal_base.png', None)},
        'template': r'weapons\assault rifle\fp\shaders\gun',
        'glow': {},
        # BOOT 1 (user: 'the normal glowing parts need some work'; Halo 4 at rest: the sight, the rear
        # rings and the side strips lit hard orange with bloom, ours a faint yellow spot): the glow
        # islands lit end to end and wider, the Suppressor's tuned settings (gain 2.2, falloff 0.35,
        # radius 1.3), the colour read off the user's screenshot (core yellow-orange)
        # BOOT 3 (user: 'a lot better; the display could use more glow, and it's more yellow than
        # orange'): the colour deeper orange (0.72 -> 0.55 green) + a static radial card on the sight
        # display (Halo 4's `sight` marker; `bo_display_glow`, not faded)
        'glow_shaders': {'bo_glow': {'rgb': (1.0, 0.55, 0.1), 'additive': True, 'islands': True,
                                     'islands_of': 'storm_stasis_pistol_glow',
                                     'gain': 2.2, 'falloff': 0.35, 'radius': 1.3,
                                     # BOOT 2 (user: 'the glow is white, not orange'): the islands'
                                     # default white-hot centre saturated every tiny island white
                                     'hot': False},
                         # THE CHARGE GLOW (boot 1, user: 'more indication -- a muzzle light and / or
                         # more glowing parts, which is what it does normally'): Halo 4's charging
                         # effect lights the four plates, the vents and a core at the muzzle; Halo 1
                         # draws weapon attachments at the hidden third-person gun in first person ->
                         # the Spartan Laser's recipe: radial cards built INTO the model at those
                         # markers (on their nodes: the plate cards open with the plates), an additive
                         # shader FADING with B out = primary charged
                         'bo_charge_glow': {'rgb': (1.0, 0.6, 0.12), 'additive': True, 'radial': True,
                                            'hot': True, 'falloff': 1.4, 'fade_source': 'B_out'},
                         'bo_display_glow': {'rgb': (1.0, 0.55, 0.1), 'additive': True, 'radial': True,
                                             'falloff': 1.6}},
        'glow_points': ([{'marker': 'primary trigger', 'shader': 'bo_charge_glow', 'size': 5.0,
                          'forward': 0.5}] +
                        [{'marker': m, 'index': i, 'shader': 'bo_charge_glow', 'size': 2.5}
                         for m in ('top plate', 'bottom plate') for i in (0, 1)] +
                        [{'marker': 'vent', 'index': i, 'shader': 'bo_charge_glow', 'size': 1.5}
                         for i in (0, 1)] +
                        # BOOT 4 (user: 'a nice glow on the display -- restrict it to the display
                        # area, it extends into the weapon'): ONE card in the display's plane (its
                        # glow piece: 0.75..1.35 / +-0.31 / 5.03..5.85 cm, normal -0.78 / 0 / 0.54),
                        # 1 cm, 0.1 cm in front of it -- not three crossed 2.5 cm cards
                        [{'marker': 'sight', 'shader': 'bo_display_glow', 'size': 1.0,
                          'at': (0.968, 0.0, 5.497), 'normal': (-0.78, 0.0, 0.54)}]),
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
            'first_person:o_h_exit': 'first-person o-h-exit',
        },
        # Halo 4 has one reload: Halo 1's reload-empty plays the same (`also_as`)
        # THE BLAST OVERHEATS (step 4b, 2026-10-14: barrel 1 heat 1.0 a round, threshold 1): Halo 4
        # plays fire_2, HOLDS its last frame while overheated and plays o_h_exit (fire_2's end =
        # o_h_exit's start, 0.00 apart; `overheated` is another pose -- ready_overheated's end, the
        # Storm Rifle's case) -> Halo 1's overheating = fire_2, overheated = fire_2's last frame held
        # for the rest of the 1.8 s lockout (1.8 - 22/30 s = 32 fr), then o-h-exit
        'also_as': {'first-person reload-empty': 'first_person:reload_full',
                    'first-person overheating': 'first_person:fire_2'},
        'holds': {'first-person overheated': ('first_person:fire_2', 32)},
        # BOOT 1 (user: 'the FP position is too far up and forward -- down 2 units and back 1')
        # BOOT 2 (user: '2 more units down')
        'view_offset': (-0.01, 0.0, -0.04),
        # BOOT 1 (user: 'the side plates don't flip out during the charge'): Halo 4 opens its four
        # plates by a charge-driven OVERLAY (`flaps`: exactly the four plate bones) Halo 1 cannot play
        # -> the open plates of fire_2's last frame (fire_2 keeps them open, o_h_exit closes them)
        # baked into `overcharged` (full charge)
        'node_from': {'first-person overcharged': [
            ('first_person:fire_2', -1, ['frame b left top plate', 'frame b right top plate',
                                         'frame b left low plate', 'frame b right low plate'])]},
        # BOOT 1 (user's charge video: 'something is going on with that right hand'): in the blast's
        # held pose Halo 4's right hand re-grips forward and Halo 1's glove sinks into the gun
        # (h1_fp_hand_clip right, fire_2: 1977 -> 572 at 2 cm to the gun's right; the idle grip's
        # fingers did not help: 181 -> 194). The user: every other animation fine -> only the
        # blast's chain: overcharged (2044 -> 429) ramping in, fire_2 (+ the held overheat), o_h_exit
        # (1797 -> 1049) ramping out -- Halo 1 snaps between FP animations (`ramp`: no pop)
        # BOOT 3 (user's charge video: 'the hand clips through the weapon and is not on the grip when
        # overcharging'): the offset on overcharged moved the hand OFF Halo 4's grip (the count fell
        # because the hand left the gun) -> none there; fire_2 ramps it in over its first 4 frames
        # BOOT 4 (user: 'the hand still slides off the grip after the charged shot -- the overheated
        # state moves it to the right'): the ramp made the 2 cm move visible as a slide, and 2 cm
        # reads as off the grip in the held pose -> 1 cm (h1_fp_hand_clip fire_2: 1977 none / 1135
        # at 1 cm / 572 at 2 cm), set at once (the recoil hides the change), the exit ramping out
        'hand_offset_anims': {'first_person:fire_2': {'r': (0.0, -0.01, 0.0)},
                              'first_person:o_h_exit': {'r': (0.0, -0.01, 0.0), 'ramp': {'out': 12}}},
        # BOOT 3 (user: 'the FP needs more adjustment, 2 more units down -- unless we can adjust only
        # the melee'): the MELEE alone 2 units further down, ramped in / out (melee_strike_1 37 fr)
        'view_offset_anims': {'first_person:melee_strike_1': {'offset': (0.0, 0.0, -0.02),
                                                              'ramp': {'in': 4, 'out': 8}}},
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
            # BOOT 1 (user: 'the hum for charging is a bit quiet'): -11.2 (the plasma rifle's charge
            # level) -> -6
            'bo_charge_loop': (['play_wea_forerunner_bolt_pistol_player_charge_in:3'],
                               'sound\\sfx\\weapons\\plasma rifle\\charge', -6.0),
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
            # the overheat's exit (o_h_exit's cue; Halo 1 plaspistol_overheat_exit -18.5)
            'bo_oh_exit': (['play_weapons_stasis_pistol_overheat_exit:0,1'],
                           B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'plaspistol_overheat_exit']), -18.5),
            'bo_drop': (['play_wea_drop_pistol_fr_bolt_pistol_nonplayer'],
                        'sound\\sfx\\impulse\\weapon_drops\\pistol_impact', -28.8),
            # the BALANCED reload's sound (the patcher retimes the reload x1.314 and swaps it in:
            # catalog anim_sounds; the BR's recipe)
            'bo_reload_balanced': (['play_wea_stasis_pistol_reload_full:0,1'],
                                   'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
        },
        'stretch': {'bo_reload_balanced': 67 / 51.0},
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
                   'first-person reload-full': SND + 'bo_reload',
                   'first-person o-h-exit': SND + 'bo_oh_exit'},
        'add_triggers': [0],
        # THE BOLT (trigger 0, a tap): Halo 4 storm_stasis_pistol_bolt 7.5 (lower = upper),
        # bullet_slow, instantaneous acceleration 0.1, 2700 wu/s flat, range 40 (air damage range
        # 0..40: no falloff). The pistol bullet's table (bullet_slow both sides)
        'bullet': {'projectile': (PISTOL + 'bullet', BO + 'bolt'),
                   'damage': (PISTOL + 'bullet', BO + 'bolt'),
                   'dmg': 7.5, 'acceleration': 0.1, 'velocity': 2700.0, 'range': 40.0,
                   # step 4b list 2 (H4 bolt vs magnum onto the H1 pistol bullet): water gravity
                   # 0.4 x 0/0.2 = 0; list 3 (a zero on one side -> Halo 4's own): water damage
                   # range 5..10 (magnum 0..10); damage: active camouflage 0.45 x 0.25/0.5, the
                   # breaking effect Halo 4's (magnum 0)
                   'proj_fields': {'proj_attrs.physics.air_damage_range': (0.0, 40.0),
                                   'proj_attrs.physics.water_gravity_scale': 0.0,
                                   'proj_attrs.physics.water_damage_range': (5.0, 10.0)},
                   'fields': {'damage.active_camouflage_damage': 0.225,
                              'breaking_effect.forward_velocity': 35.0,
                              'breaking_effect.forward_radius': 0.12,
                              'breaking_effect.forward_exponent': 0.2,
                              'breaking_effect.outward_velocity': 3.0,
                              'breaking_effect.outward_radius': 0.3,
                              'breaking_effect.outward_exponent': 0.2},
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
            # BOOT 1 (user: 'the charge fires something, but I can't see the pellets'): Halo 1's
            # pellet is invisible and lives 5.5 wu -- Halo 4 draws charged_energy_wave / slug
            # particles over it. Every pellet a tracer: the AR bullet's contrail (attachments_from)
            # recoloured the Forerunner orange (the Spiker's recipe; trigger 1 has 0 rounds between
            # tracers: every pellet)
            'attachments_from': r'weapons\assault rifle\bullet',
            'contrail': {'from': r'weapons\assault rifle\bullet', 'out': BO + 'pellet trail',
                         'rgb': (1.0, 0.6, 0.12)},
            # BOOT 2 (user's picks: 'burst at range end' + 'orange impacts'): a pellet that reaches
            # its 5.5 wu detonates -> a small orange spark burst there (the needle's `detonate`,
            # the Spike Rifle's recipe: debris / smoke / decal / sound dropped, flash + flare tinted,
            # x0.25 -- 15 at once); the impacts' environment sparks and flashes tinted orange
            # (shields and blood keep their own)
            'detonation_effect': {'from': r'weapons\needler\effects\needle detonate',
                                  'out': BO + 'effects\\pellet burst',
                                  'drop_particles': ('debris', 'smoke'),
                                  'drop_parts': (r'effects\decals\bullet holes\dirt pistol',
                                                 r'sound\sfx\weapons\needler\expl'),
                                  'tint_match': ('flash h pistol detonate', 'flare h stealth cannon'),
                                  'tint': (1.0, 0.6, 0.12), 'scale': 0.25},
            # BOOT 3 (user: 'no orange impacts when close to a target, only further away'): a pellet
            # that HITS played only its material's impact (dust on dirt / stone) -- the burst was the
            # range end's alone. Now every pellet DETONATES on contact (units + world; the GL's
            # material lists): the same orange burst on every hit
            'default_responses': {'detonate': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
                                               25, 26, 30, 32] + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 27, 31]},
            'impact_tint': {'match': ('sparks impact', 'sparks trail', 'flash h generic',
                                      'flash c generic', 'flare h stealth cannon'),
                            'rgb': (1.0, 0.6, 0.12), 'out': BO + 'effects\\impact\\pellet '},
            # the blast lands 15 pellets at once, ~1/s: the shotgun's per-hit effect at its rate
            'impact_thin': {'materials': [22], 'out': BO + 'effects\\impact\\pellet ',
                            'thin': {}, 'rate': 1.0},
            'triggers': [1]}],
        # THE BOLT RATE: Halo 4 recovery 0.1 s (rounds per second 30 = recovery-limited) = 10/s
        'trigger': {'rounds_per_second': (10.0, 10.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0,
                    # the FP muzzle in the idle after boot 2's move (h1_fp_muzzle: the built FP model +
                    # animations): where the bolt and the pellet tracers start in first person
                    'first_person_offset': (0.3349, -0.0427, -0.0637)},
        # THE OVERHEAT (Halo 4: overheated threshold 1, recovery 0.1, loss 0.6 / 0.5 overheated; the
        # bolt 0 heat, the blast 1.0 a round): Halo 1's ONE loss = the overheated one (the Storm
        # Rifle's A') -> 1.8 s lockout after every blast, nothing fires. The blast's heat per round
        # sits on trigger 1 (`fields`): Halo 1 adds it per SHOT (the plugin: "each time the trigger is fired")
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.5},
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
            'weap_attrs.triggers.1.misc.heat_generated_per_round': 1.0,
            'weap_attrs.triggers.0.misc.heat_generated_per_round': 0.0,
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
            # STEP 6: the template's magazine names `powerups\pistol ammo` (pistol ammo tops it
            # up). Halo 4 gives no pickup amount (Forerunner ammo boxes) -> the YARDSTICK's pickup :
            # initial (the H1 pistol's 120 : 60) on Halo 4's initial 30 = 60 (the DMR / Suppressor)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 60,
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
        # BOOT 2 (user: 'the muzzle flash is below the muzzle, not on it'): the Suppressor's finding
        # on the same Halo 4 / storm_fp setup (3 boots: 4 units up) as the start -- `shift` 0.04 up
        # on both flashes (the blast's: every particle, `match` 'particles'); BOOT 3 (user: '1 unit
        # forward, away from the camera'): + 0.01 forward; BOOT 4 ('0.5 units down and forward
        # again'): 0.5 down, 1 more forward
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', BO + 'effects\\fire bolt',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'bo_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.5,
                               'shift': (0.02, 0.0, 0.035),
                               # BOOT 5 (user: 'increase the duration of the muzzle flash slightly'):
                               # Halo 1's pistol flash lives 0.075 s (2-3 frames) -> own copies x1.6
                               # (0.12 s) with a 0.04 s fade-out (the blast's shotgun flash already 0.3 s)
                               'own_particles': {'out': BO + 'effects\\particles\\bolt ',
                                                 'lifespan': 1.6, 'fade_out': 0.04},
                               'drop_particles': ('casing', 'smoke'),
                               'drop_parts': [r'sound\sfx\weapons\pistol\eject'],
                               'tint': (1.0, 1.0, 0.91, 0.18)}),
            'firing_effect@1': (PISTOL + 'effects\\fire bullet', BO + 'effects\\fire blast',
                                {r'sound\sfx\weapons\shotgun\fire': SND + 'bo_blast'},
                                {'copy_from': SG + 'effects\\shotgun firing',
                                 'match': 'particles', 'shift': (0.02, 0.0, 0.035),
                                 'drop_particles': ('casing', 'smoke'),
                                 'drop_event_parts': {1: [r'sound\sfx\weapons\shotgun\fire']},
                                 'tint': (1.0, 1.0, 0.91, 0.18)}),
            'empty_effect': (PISTOL + 'effects\\empty', BO + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'bo_dryfire'})},
        'melee': (PISTOL + 'melee', BO + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a boltshot', 'Picked up %d rounds for boltshot'),
        'extra_sounds': [SND + 'bo_reload_balanced'],
        'icon': 'boltshot',
        # the PISTOL's HUD; the crosshair from Halo 4's CUI screen (ui\hud\weapons\forerunner\
        # burst_gun) and the USER'S SCREENSHOTS (2026-10-14, 1080p, at rest + charged): THREE
        # concentric rings of four corner brackets, one art piece per ring (img_boltpistol_inner 24 px
        # drawn 8 units, _middle 48 -> 16, _outer 96 -> 32: Halo 4's 3 px a unit). The art IS the
        # top-left piece (a stepped top edge, then a diagonal down and out -- the screenshot); the
        # other corners mirror it. Box centres in widget units (y down) from the CUI props: inner
        # (+-5, -4 / 5), mid (+-10, -10 / 11), outer (-14 / 14..15, +-16). Opacity at REST (the
        # CUI's widget_idle binding at 0, the screenshot): inner 0.85, mid 0.4, outer 0.1; charged
        # all 1 -- Halo 1's crosshair is static: the REST look (not reproduced: the rings lighting
        # outward with the charge, the inner ring's spread). On screen (1080p): inner ~28 px, mid
        # ~48, outer ~78 across. SUPERSAMPLE recipe: F 2, the ~64-unit span at scale 3.5 in the 512
        # cell; overlay = 1.5 px a unit / (123/97 x 3.5 x 2 x 0.75) -- SIMULATED against the
        # screenshot (2026-10-14): inner ~28 / mid ~47 / outer ~79 px (Halo 4 28 / 47 / 75), margin ~19 px
        'hud': {'donor': PISTOL + 'pistol', 'out': BO + 'boltshot',
                'reticle': (H4 + BR4 + 'img_boltpistol_inner', 0, 'boltshot'),
                'reticle_xform': {'offset': (-5.0, -4.0), 'gain': 0.85},
                'reticle_layers': [
                    (H4 + BR4 + 'img_boltpistol_inner', 0, 1.0, {'flip_x': True, 'offset': (5.0, -4.0), 'gain': 0.85}),
                    (H4 + BR4 + 'img_boltpistol_inner', 0, 1.0, {'flip_y': True, 'offset': (-5.0, 5.0), 'gain': 0.85}),
                    (H4 + BR4 + 'img_boltpistol_inner', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (5.0, 5.0), 'gain': 0.85}),
                    (H4 + BR4 + 'img_boltpistol_middle', 0, 1.0, {'offset': (-10.0, -10.0), 'gain': 0.4}),
                    (H4 + BR4 + 'img_boltpistol_middle', 0, 1.0, {'flip_x': True, 'offset': (10.0, -10.0), 'gain': 0.4}),
                    (H4 + BR4 + 'img_boltpistol_middle', 0, 1.0, {'flip_y': True, 'offset': (-10.0, 11.0), 'gain': 0.4}),
                    (H4 + BR4 + 'img_boltpistol_middle', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (10.0, 11.0), 'gain': 0.4}),
                    (H4 + BR4 + 'img_boltpistol_outer', 0, 1.0, {'offset': (-14.0, -16.0), 'gain': 0.1}),
                    (H4 + BR4 + 'img_boltpistol_outer', 0, 1.0, {'flip_x': True, 'offset': (14.0, -16.0), 'gain': 0.1}),
                    (H4 + BR4 + 'img_boltpistol_outer', 0, 1.0, {'flip_y': True, 'offset': (-14.0, 16.0), 'gain': 0.1}),
                    (H4 + BR4 + 'img_boltpistol_outer', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (15.0, 16.0), 'gain': 0.1})],
                'reticle_split': 100,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 3.5, 'reticle_overlay': 1.5 / (123 / 97.0 * 3.5 * 2 * 0.75),
                'flash_base': 12,                # the pistol's low-ammo cutoff is of 12
                # Halo 4's own round pips (ammo_burstgun: 10 in a row, the screenshot's top right),
                # one a round (ammo_meter `art`, the Mauler's), for 10 (default) and 15 (balanced)
                'ammo_meter': {'sizes': (10, 15), 'base': BO + 'bitmaps\\boltshot_ammo',
                               # BOOT 1 (user: 'squished and not readable'): scaled to Halo 3's unit
                               # the ten pips merged into ONE strip (taken as one tick) -> read at the
                               # strip's own density (`native`: ten pips, 33 px apart)
                               'art': {'h3': (H4 + BR4 + 'ammo_burstgun', 0), 'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py boltshot). DEFAULT = Halo 4's own
    # numbers in the tags; BALANCED = the PISTOL ratio for the bolt / magazine / aim, the SHOTGUN
    # ratio for the blast (step 4a, user 2026-10-14). Assembly Halo1 units: angles in degrees,
    # velocity in wu per TICK. Trigger rows reach trigger 0 unless `index` (the GL's finding)
    'catalog': {
        'entry': {
            'weapon': 'Boltshot', 'source': 'Halo 4', 'donor': 'Pistol', 'default_on': False,
            'desc': "Halo 4's Boltshot: its model, first-person animations, sounds and numbers. A "
                    "Forerunner sidearm: a tap fires a bolt (10 a magazine), holding the trigger "
                    "0.6 s charges a 15-pellet close-range blast for 5 rounds that overheats the "
                    "gun for 1.8 s.",
            'balance_desc': "Measured against the Pistol (the bolt) and the Shotgun (the blast): "
                            "12.5 damage a bolt at 7 a second from a 15-round magazine, Pistol "
                            "aim assist and reload; the blast's pellets hit like the Shotgun's "
                            "(20.5, reaching 34 wu) and cost 7 rounds -- two blasts a magazine.",
            # step 9: the balanced reload = the H1 pistol's 67 fr x Boltshot 51 / magnum 51 = 67 over
            # the built 51 = x1.314; swap (ready + put-away, ONE multiplier): the pistol's ready 35
            # x 17 / 17 = 35 over the built 17 = x2.06
            'anims': {'reload': 67 / 51.0, 'swap': 35 / 17.0},
            'anim_sounds': {'reload': [
                {'mult': 67 / 51.0, 'from': SND + 'bo_reload', 'to': SND + 'bo_reload_balanced'}]},
            'balance': [
                # the bolt: 25 x 7.5/15 (the pistol bullet's table, bullet_slow both sides)
                row('jpt!', BO + 'bolt', 'Damage Lower Bound', 12.5, 7.5, 'Bolt Damage'),
                row('jpt!', BO + 'bolt', 'Damage Upper Bound', 12.5, 7.5, 'Bolt Damage'),
                row('jpt!', BO + 'bolt', 'Damage Upper Bound Max', 12.5, 7.5, 'Bolt Damage'),
                # 3.5/s x 0.2/0.1 (trigger 0)
                row('weap', BO + 'boltshot', 'Rounds Per Second', 7.0, 10.0, 'Rate of fire', block='Triggers'),
                row('weap', BO + 'boltshot', 'Rounds Per Second Max', 7.0, 10.0, 'Rate of fire', block='Triggers'),
                # magazine 12 x 10/8, initial 60 x 30/24, maximum 120 x 40/40 (= the pistol's)
                row('weap', BO + 'boltshot', 'Rounds Loaded Maximum', 15.0, 10.0, 'Magazine', block='Magazines'),
                row('weap', BO + 'boltshot', 'Rounds Reloaded', 15.0, 10.0, 'Magazine', block='Magazines'),
                row('weap', BO + 'boltshot', 'Rounds Total Initial', 75.0, 30.0, 'Magazine', block='Magazines'),
                row('weap', BO + 'boltshot', 'Rounds Total Maximum', 120.0, 40.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the pistol's pickup : initial (120 : 60) on the balanced 75
                row('weap', BO + 'boltshot', 'Rounds', 150, 60, 'Ammo pickup', block='Magazines/Magazines'),
                # the bolt's spread: 0.2 x 0.4/0.15, 2 x 2/1.75 (trigger 0)
                row('weap', BO + 'boltshot', 'Error Angle', 0.533, 0.4, 'Error Angle', block='Triggers'),
                row('weap', BO + 'boltshot', 'Error Angle Max', 2.286, 2.0, 'Error Angle', block='Triggers'),
                # 300 x 2700/3000 = 270 wu/s; range 40 kept (the ratio's 6.4 is degenerate, user)
                row('proj', BO + 'bolt', 'Initial Velocity', 270 / 30.0, 2700 / 30.0, 'Projectile'),
                row('proj', BO + 'bolt', 'Final Velocity', 270 / 30.0, 2700 / 30.0, 'Projectile'),
                # aim: the same mode block on both Halo 4 sides (x1) -> the pistol's 3/30 6/30
                row('weap', BO + 'boltshot', 'Autoaim Angle', 3.0, 2.25, 'Autoaim'),
                row('weap', BO + 'boltshot', 'Autoaim Range', 30.0, 20.0, 'Autoaim'),
                row('weap', BO + 'boltshot', 'Magnetism Angle', 6.0, 5.0, 'Magnetism'),
                row('weap', BO + 'boltshot', 'Magnetism Range', 30.0, 20.0, 'Magnetism'),
                # THE BLAST (Shotgun ratio): a pellet 21.5 x 10/10.5 = 20.48, lower 8 x 6/3 = 16 over
                # 1.5 x 2.5/1.5 = 2.5 -> 3 x 4/3.75 = 3.2 wu; 140 -> 100 wu/s (x 480/480); range 40 x
                # 5.5/6.5 = 33.8; cone 10 x 3.5/3 = 11.67 deg; 7 rounds a blast (15 / 2, user)
                row('jpt!', BO + 'pellet', 'Damage Lower Bound', 16.0, 6.0, 'Blast Damage'),
                row('jpt!', BO + 'pellet', 'Damage Upper Bound', 20.48, 10.0, 'Blast Damage'),
                row('jpt!', BO + 'pellet', 'Damage Upper Bound Max', 20.48, 10.0, 'Blast Damage'),
                row('proj', BO + 'pellet', 'Air Damage Range Max', 3.2, 4.0, 'Blast falloff'),
                row('proj', BO + 'pellet', 'Initial Velocity', 140 / 30.0, 480 / 30.0, 'Blast projectile'),
                row('proj', BO + 'pellet', 'Final Velocity', 100 / 30.0, 480 / 30.0, 'Blast projectile'),
                row('proj', BO + 'pellet', 'Maximum Range', 33.8, 5.5, 'Blast projectile'),
                dict(row('weap', BO + 'boltshot', 'Error Angle', 11.67, 3.5, 'Blast spread', block='Triggers'), index=1),
                dict(row('weap', BO + 'boltshot', 'Error Angle Max', 11.67, 3.5, 'Blast spread', block='Triggers'), index=1),
                dict(row('weap', BO + 'boltshot', 'Rounds Per Shot', 7, 5, 'Blast cost', block='Triggers'), index=1),
                # the 15 magazine's meter: boltshot_ammo sequence 1 (ammo_meter 10 15); alpha
                # multiplier 255 // n; low-ammo flash 3 of 10 -> 5 of 15 (the pistol's 4 of 12)
                dict(row('wphi', BO + 'boltshot', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', BO + 'boltshot', 'Alpha Multiplier', 17, 25, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', BO + 'boltshot', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', BO + 'boltshot', 'Loaded Ammo Cutoff', 5, 3, 'Ammo display'), index=0),
            ]},
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
                                     r'objects\weapons\pistol\storm_magnum\projectiles\storm_magnum_bullet.damage_effect')},
        'target': {'weapon': (BO + 'boltshot.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (BO + 'bolt.projectile', PISTOL + 'bullet.projectile'),
                   'damage_effect': (BO + 'bolt.damage_effect', PISTOL + 'bullet.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 3)
    'test': {'level': 'b30', 'rounds': (10, 30), 'grunt': None, 'elite': None},
})

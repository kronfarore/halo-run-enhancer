r"""The Flamethrower into Halo 2 -- a SPECIAL CASE outside the spreadsheet's 20 (user, 2026-10-21: "my
current play run uses it and I want it available before the next session, in case we make it to
Halo 2"). Halo 2 never had one. A phase-0 STUB (reservations, candidates, the proposed donor);
the port session fills the pipeline sections (ports_h2/assault_rifle.py is the complete Halo 3
-route example) and sets 'status' to 'in progress' at its start, 'done' at its end.

SOURCE, PROPOSED (the session confirms it with the user first): HALO 1, `HCEEK weapons\flamethrower`
-- a full first-person weapon (gbxmodel, fp\ model + FP animations, flame projectile, heat display).
Halo 3's `objects\weapons\turret\flamethrower` is a TURRET weapon: third-person only, no FP model or
graph, so it gives Halo 2 nothing to hold in first person. Halo 1's FP arm skeleton IS Halo 2's
masterchief (H2_PORT_PLAN 0.4: shoulders +-9.399, upper arm 10.25, forearm 10.89 -- "exactly Halo
1's numbers"), so its FP animations should carry to the Chief node-for-node as Halo 3's did for the
AR; the DERVISH has no Halo 1 source (Elite hands: 4 digits) -- the arm chain is the same, the
fingers are not (re-pose the hand, or the SAW route: a donor's H2 dervish graph retimed).
"""

FT = r'objects\weapons\support_low\flamethrower'       # the port's folder (H2EK)
SMG = r'objects\weapons\rifle\smg'                       # the donor (H2EK)
FX = r'effects\objects\weapons\support_low\flamethrower'  # the reserved effects folder
H1FT = r'weapons\flamethrower'                           # the source's folder (HCEEK)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
import os as _os
NEW_HUD = r'ui\hud\bitmaps\new_hud'
# the port's own world mesh (step 1's JMS): the silhouette the HUD plate, backpack icon and pickup
# glyph are drawn from (h3_weapon_glyph.mesh reads a .jms) -- Halo 1 has no Halo 3 render model
WORLD_JMS = H2EK + r'\data' + '\\' + FT + r'\render\flamethrower.jms'

PORT = {
    'order': 22,
    'wave': 'S1',
    'name': 'Flamethrower',
    'source': 'Halo 1',
    'status': 'in progress',
    'source_tag': r'weapons\flamethrower\flamethrower',      # HCEEK (Halo 1)
    'reservations': {
        'message_prefix': 'ft2',
        'glyph': 0xE153,                     # free in all eight English fonts (phase 0 checked E13E..E153)
        'weapon_dir': r'objects\weapons\support_low\flamethrower',
        'effects_dir': r'effects\objects\weapons\support_low\flamethrower',
        'fp_graph': r'weapons\support_low\fp_flamethrower\fp_flamethrower',
        'hud': r'ui\hud\flamethrower',
        'hud_bitmap_prefix': 'flamethrower_',
        'sound_dir': r'sound\weapons\flamethrower_port',
    },
    # PROPOSED: the AR's proven shape -- weapon cloned from the H2 SMG (spew, 1 magazine / 1 trigger /
    # 1 barrel; clear dual wield), world .model / HUD / collision from a two-handed donor (the BR's, as
    # the AR); the Halo 1 flamethrower also heats -- check whether its magazine or its heat is the
    # limit and pick the donor's block shape by that (the plasma rifle = heat + battery, 0 magazines)
    # STEP 0 (user, 2026-10-21): source HALO 1 -- the user's rule "if Halo 2 has no turret-style
    # 3rd-person weapons, Halo 1": H2EK's h_turret_mp_item / c_turret_mp_item sit in Bungie's weapon
    # palettes but carry 'cannot be used by player', no FP model / graph (3P class `missile`), and the
    # engine has no third-person hold. Dervish: RE-POSE (arms + wrists from the Chief's Halo 1 frames,
    # fingers = the Chief finger's curl as a delta on the Elite's own bind; middle dropped). Donor: the
    # SMG clone + Halo 2's heat fields (fuel AND heat, as Halo 1).
    'donor': {'weapon': r'objects\weapons\rifle\smg\smg', 'message_prefix': 'smg',
              'why': 'spew automatic magazine 1/1/1 (the AR route); alt plasma_rifle (pr) if heat is the limit'},
    'yardstick': {
        # step 4a WITH the user (2026-10-21; reports/h2_flamethrower_4a.md, h2_ft_ttk_4a.py)
        'pick': 'Plasma Rifle',
        'reason': 'native in both games and the only native candidate that also HEATS: carries damage '
                  'x0.77 (21.5 -> 16.5 a flame, 2 a shot), rate x0.9 (12 -> 10.8/s) and the heat model '
                  '(0.072 -> 0.135 a shot, loss 0.44 -> 1.25/s, recovery 0.30 -> 0.12; overheats after '
                  '~2.7 s held, Halo 1 ~3.6 s); fuel 100/300/600, reload 3.4 s and range 16 wu have no '
                  'Plasma Rifle counterpart -> Halo 1 raw. Damage group (user): Halo 2 own `burning` '
                  '(Halo 1 category flame) -- Elite 0.65 s, Brute 0.28, Jackal 0.19, Flood 0.28 point blank',
        'damage_group': 'burning',
        'candidates': {
            'provisional': 'Plasma Rifle (native in Halo 1 AND Halo 2: an automatic, close-mid range)',
            'alternatives': ['Shotgun (native in both: the close-range role)',
                             'Sentinel Beam (H2 pickable; Halo 1\'s is a PORT with DERIVED numbers -- a '
                             'ratio on it chains two derivations)',
                             'SMG (the donor; no Halo 1 SMG native -- Halo 1\'s is a port)'],
            'direct': 'none (Halo 2 has no flamethrower; H1 Flood carry it, H2 Flood carry the Flood weapons)',
            'peers': ['Shotgun', 'Plasma Rifle', 'Sentinel Beam', 'SMG', 'Energy Blade'],
            'why': 'continuous short-range flame (H1: flame projectile, burning damage over time, heat display); '
                   'the yardsticks must exist in Halo 1 AND Halo 2 with cards in both (halo.json)',
        },
    },
    # Halo 1's AI data is an actor variant, not ai\generic: ai_firing_profile.py --h2-port reads
    # Halo 3 / ODST / Reach / Halo 4 sources -- the session picks a Halo 2 stand-in entry (e.g. the
    # SMG's or the plasma rifle's) or teaches the reader Halo 1 (H2_PORT_PLAN 0.5b)
    'firing_profile': {'from_game': 'Halo 1', 'from_weapon': r'weapons\flamethrower\flamethrower',
                       'note': 'no ai\\generic source: a Halo 2 stand-in, decided in session',
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties'},
    # step 1 -- h2_port_geometry.py kind 'h1': the Halo 1 gbxmodels on their OWN skeleton (gun / ammo /
    # cover in first person) -- Halo 1's own FP animations drive them (H2_PORT_PLAN 0.4: Halo 1's FP
    # arms ARE Halo 2's masterchief; the reader checked on the cyborg arms: 37/37 nodes = Bungie's
    # fp_arms.jms to 3e-6). Halo 1's world root carries a ~55 deg bind rotation over model-space
    # vertices: dropped (root_identity), as Halo 2's world weapons sit on an identity `frame gun`
    'geometry': {
        'kind': 'h1',
        'world_gbx': r'weapons\flamethrower\flamethrower',
        'fp_gbx': r'weapons\flamethrower\fp\fp',
        'data_dir': FT,
        'world': 'flamethrower', 'fp': 'fp_flamethrower',
        'root_identity': True,
        # Halo 1 shader basename (#permutation for the counter's digits: 0 ones, 1 tens, 2 hundreds)
        # -> Halo 2 material. The counter on the BR's digit shaders (tens / ones, Bungie's `=?`
        # symbols; the AR's route): Halo 2 has no hundreds digit -- dropped (100 reads 00)
        'materials': {'ft gun': 'flamethrower', 'ft ammo': 'flamethrower_ammo',
                      'ft screen': 'flamethrower_screen', 'ft heat_display': 'flamethrower_heat_display',
                      'ft numbers#1': 'flamethrower_tens=?', 'ft numbers#0': 'flamethrower_ones=?',
                      'ft numbers#2': None,
                      'ft_numbers#1': 'flamethrower_tens=?', 'ft_numbers#0': 'flamethrower_ones=?',
                      'ft_numbers#2': None},
        'node_names': {},                    # Halo 1 names them `frame gun` / `frame ammo` / `frame cover`
        'world_permutation': 'base', 'world_region': 'gun',      # the BR's .model's variants
        'markers': {'primary trigger': 'primary_trigger', 'left hand': 'left_hand',
                    'defoliant spawn': 'muzzle_flash',
                    # first person: Halo 1 spawns the flame at `spawn fire`, its pilot light at `pilot`
                    'spawn fire': 'primary_trigger', 'pilot': 'pilot', 'flashlight': 'flashlight',
                    'steam vent01': 'steam_vent', 'steam vent02': 'steam_vent'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'min_tris': 200,
        'render': ['flamethrower', r'flamethrower\fp_flamethrower'],
    },

    # step 2 -- h2_port_textures.py kind 'h1': Halo 1's own maps (HCEEK, h1_decode). Halo 1's
    # shader_model has NO bump map -> a flat height (Halo 1's look); its multipurpose RED (the
    # reflection mask) becomes the diffuse's ALPHA, Halo 2's specular mask (Bungie's SMG diffuse
    # carries one there). Shaders reseeded from Bungie's: the SMG's metals, the shotgun's lit sight
    # (tex_bump_illum, opaque) for the fuel screen, the Plasma Rifle's HEAT GAUGE as it is
    # (meter_active_camo: Halo 2's own heat display on Halo 1's heat-display quad), the BR's digits
    'textures': {
        'kind': 'h1',
        'rel': FT + r'\bitmaps',
        'shaders_dir': FT + r'\shaders',
        'bitmaps': [(H1FT + r'\bitmaps\flamethrower', 'flamethrower', SMG + r'\bitmaps\smg',
                     ('alpha_from', H1FT + r'\bitmaps\flamethrower multipurpose', 0), None),
                    (None, 'flamethrower_bump', SMG + r'\bitmaps\smg_bump', 'flat_bump', (64, 64)),
                    (H1FT + r'\bitmaps\flamethrower_screen', 'flamethrower_screen',
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color', None)],
        'shaders': [
            ('flamethrower', SMG + r'\shaders\smg_painted_metal',
             {SMG + r'\bitmaps\smg': FT + r'\bitmaps\flamethrower',
              SMG + r'\bitmaps\smg_bump': FT + r'\bitmaps\flamethrower_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': FT + r'\bitmaps\flamethrower_bump'}),
            ('flamethrower_ammo', SMG + r'\shaders\smg_bare_metal',
             {SMG + r'\bitmaps\smg': FT + r'\bitmaps\flamethrower',
              SMG + r'\bitmaps\smg_bump': FT + r'\bitmaps\flamethrower_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': FT + r'\bitmaps\flamethrower_bump'}),
            ('flamethrower_screen', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': FT + r'\bitmaps\flamethrower_screen'}),
            ('flamethrower_heat_display', r'objects\weapons\rifle\plasma_rifle\shaders\plasma_rifle_gauge', {}),
            ('flamethrower_tens', r'objects\weapons\rifle\battle_rifle\shaders\tens', {}),
            ('flamethrower_ones', r'objects\weapons\rifle\battle_rifle\shaders\ones', {}),
        ],
        'report_rows': [(FT + r'\bitmaps\flamethrower_bump', 'the port (flat)'),
                        (SMG + r'\bitmaps\smg_bump', 'Bungie SMG')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon (spew, 1 magazine / 1 trigger / 1 barrel; the
    # heat fields are plain fields, step 4), the BR's world .model (two-handed). The FLAME:
    #   projectile = the Plasma Rifle bolt's clone (the yardstick's; Halo 2's player projectile WITH
    #     flight attachments -- a contrail + light volume: the BRUTE plasma rifle's red pair cloned,
    #     the warmest Bungie has, recoloured orange in step 4, as the flame's look; 'faster
    #     when owned by player' kept with the PR's velocity ratio);
    #   impact damage = Bungie's globals\flaming_death clone: category `flame`, group `burning` (the
    #     user's 4a pick) -- and step 4 sets damage flag bit 7 'causes flaming death' (H2's own burning,
    #     tool.exe's damage_effect_definitions: the stand-in for Halo 1's burning effect)
    'weapon': {
        'weapon': FT + r'\flamethrower.weapon',
        'clones': [(SMG + r'\smg.weapon', FT + r'\flamethrower.weapon'),
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', FT + r'\flamethrower.model'),
                   (r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.projectile',
                    FT + r'\projectiles\flame.projectile'),
                   (r'globals\flaming_death.damage_effect', FT + r'\damage_effects\flame.damage_effect'),
                   (SMG + r'\damage_effects\smg_trigger.damage_effect', FT + r'\damage_effects\flamethrower_trigger.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect', FX + r'\flamethrower_fire.effect'),
                   (r'effects\objects\weapons\rifle\smg\smg_muzzle_flash.light', FX + r'\flamethrower_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\smg.material_effects', FX + r'\flamethrower.material_effects'),
                   (r'effects\materials\objects\weapons\plasma_rifle.material_effects', FX + r'\flame.material_effects'),
                   (r'effects\objects\weapons\rifle\brute_plasma_rifle\red_plasma_streak.contrail', FX + r'\flame_streak.contrail'),
                   (r'effects\objects\weapons\rifle\brute_plasma_rifle\red_plasma_streak.light_volume', FX + r'\flame_streak.light_volume'),
                   # the RELOAD sound: the seed graph (the PR's) has no reload animation, so no reload
                   # sound event -- the magazine's reloading effect carries it instead: a clone of
                   # Bungie's sound-only BR dryfire effect (step 10 repoints its sound)
                   (r'effects\objects\weapons\rifle\battle_rifle\empty.effect', FX + r'\flamethrower_reload.effect')],
        'wiring': [
            (FT + r'\flamethrower.weapon', 'hlmt', SMG + r'\smg', FT + r'\flamethrower', 'world model'),
            (FT + r'\flamethrower.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             FT + r'\flamethrower', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (FT + r'\flamethrower.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             FT + r'\fp_flamethrower\fp_flamethrower', 'first person model, Master Chief', {'nth': 0}),
            (FT + r'\flamethrower.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             FT + r'\fp_flamethrower\fp_flamethrower', 'first person model, Dervish (one FP model)', {'nth': 0}),
            (FT + r'\flamethrower.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\masterchief\fp\weapons\support_low\fp_flamethrower\fp_flamethrower',
             "Master Chief FP graph: Halo 1's own animations"),
            (FT + r'\flamethrower.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\dervish\fp\weapons\support_low\fp_flamethrower\fp_flamethrower',
             "Dervish FP graph: Halo 1's animations re-posed"),
            (FT + r'\flamethrower.weapon', 'proj', SMG + r'\projectiles\smg_bullet',
             FT + r'\projectiles\flame', 'projectile'),
            (FT + r'\projectiles\flame.projectile', 'jpt!', r'objects\weapons\rifle\plasma_rifle\damage_effects\plasma_rifle_bolt',
             FT + r'\damage_effects\flame', 'impact damage'),
            (FT + r'\flamethrower.weapon', 'jpt!', SMG + r'\damage_effects\smg_trigger',
             FT + r'\damage_effects\flamethrower_trigger', 'firing damage'),
            (FT + r'\flamethrower.weapon', 'effe', r'effects\objects\weapons\rifle\smg\fire_bullet',
             FX + r'\flamethrower_fire', 'firing effect'),
            (FT + r'\flamethrower.weapon', 'ligh', r'effects\objects\weapons\rifle\smg\smg_muzzle_flash',
             FX + r'\flamethrower_muzzle_flash', 'muzzle flash light'),
            (FT + r'\flamethrower.weapon', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\flamethrower', 'material effects (the weapon)'),
            (FT + r'\projectiles\flame.projectile', 'foot', r'effects\materials\objects\weapons\plasma_rifle',
             FX + r'\flame', 'impact material effects'),
            (FT + r'\projectiles\flame.projectile', 'cont', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             FX + r'\flame_streak', "the flame's trail (contrail)", {'nth': 0}),
            (FT + r'\projectiles\flame.projectile', 'MGS2', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             FX + r'\flame_streak', "the flame's glow (light volume)", {'nth': 0}),
            # the HUD is the BR's clone (step 7: single, two-handed; the SMG's is dual-wield shaped)
            (FT + r'\flamethrower.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\flamethrower', 'its own HUD (step 7)'),
            (FT + r'\flamethrower.weapon', 'effe', r'effects\objects\weapons\rifle\battle_rifle\reload',
             FX + r'\flamethrower_reload', "the magazine's reloading effect (Halo 1's reload sound, step 10)"),
        ],
        # the 3P label: the BR's `rifle` / `br` (every character's graph holds the two-handed BR; the
        # Grunt's taught by the AR, h2_graph_teach). Halo 1's label `ft` has no Halo 2 graph
        'string_ids': {'rifle': 'rifle', 'smg': 'br'},
        'string_ids_done': ('weapon name', 'br'),
        'shared': [(r'the particles inside flamethrower_fire', "the SMG's (Halo 1's particle systems do not port)"),
                   (r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'effects\impact\plasma_slow\* (the projectile material responses)', "the PR bolt's (step 4b)"),
                   (r'sound\weapons\plasma_rifle\plasma_proj (flyby)', "the PR bolt's (step 10)"),
                   (r'objects\powerups\smg_ammo\smg_ammo', "the SMG's ammo pickup item (unused in campaign)")],
    },

    # step 4 -- h2_port_numbers.py: Halo 1's flamethrower through the PLASMA RIFLE's ratio (4a, the
    # user): H2 PR / H1 PR per value; a value the PR lacks (fuel, reload, range, timer) = Halo 1 raw.
    # h1_weapon_values.py "weapons\flamethrower\flamethrower" / h2_ft_ttk_4a.py
    'numbers': {
        'numbers': [
            # flags'': the SMG's minus 'can be dual wielded' (0x400000); 'loop fp firing animation' kept
            (FT + r'\flamethrower.weapon', 'flags', '', 0, 2, 131072),
            # aim assist: H1 1.5 deg / 16 wu, magnetism 4 deg / 20 wu x the PR's (6/5, 12/25; 9/12, 18/25)
            (FT + r'\flamethrower.weapon', 'autoaim angle', '', 0, 0, 1.8),
            (FT + r'\flamethrower.weapon', 'autoaim range', '', 0, 0, 7.68),
            (FT + r'\flamethrower.weapon', 'magnetism angle', '', 0, 1, 3.0),
            (FT + r'\flamethrower.weapon', 'magnetism range', '', 0, 1, 14.4),
            # HEAT: H1 0.072 a shot, loss 0.44/s, recovery 0.30, overheat 1.0; H2 PR / H1 PR = 0.15/0.08,
            # 0.8525/0.30, 0.10/0.25, 1/1. Halo 1 has ONE loss rate: the overheated one = the PR's 0.35
            # x (0.44 / 0.30). Illumination 1 (both). All read 0 in the SMG: pinned after `ready time`
            # +36 (two unexported tag references between: ready effect / ready damage effect; found by
            # a probe scan), then overheated +40, detonation threshold / fraction, loss +52, illumination
            # +56, overheated loss +60
            (FT + r'\flamethrower.weapon', 'heat recovery threshold', '', 0, 0, 0.12, {'anchor': ('ready time', 36)}),
            (FT + r'\flamethrower.weapon', 'overheated threshold', '', 0, 0, 1.0, {'anchor': ('ready time', 40)}),
            (FT + r'\flamethrower.weapon', 'heat loss per second', '', 0, 0, 1.250333, {'anchor': ('ready time', 52)}),
            (FT + r'\flamethrower.weapon', 'overheated heat loss per second', '', 0, 0, 0.513333, {'anchor': ('ready time', 60)}),
            (FT + r'\flamethrower.weapon', 'heat illumination', '', 0, 0, 1.0, {'anchor': ('ready time', 56)}),
            (FT + r'\flamethrower.weapon', 'heat generated per round', 'barrels', 0, 0, 0.135,
             {'anchor': ('illumination recovery time', 4)}),
            # FUEL (no PR counterpart: Halo 1 raw): 100 loaded / 300 initial / 600 maximum, 2 a shot
            (FT + r'\flamethrower.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 100),
            (FT + r'\flamethrower.weapon', 'rounds reloaded', 'magazines', 0, 0, 100),
            (FT + r'\flamethrower.weapon', 'rounds total initial', 'magazines', 0, 0, 300),
            (FT + r'\flamethrower.weapon', 'rounds total maximum', 'magazines', 0, 0, 600),
            (FT + r'\flamethrower.weapon', 'reload time', 'magazines', 0, 0, 3.4),
            (FT + r'\flamethrower.weapon', 'rounds per shot', 'barrels', 0, 0, 2),
            (FT + r'\flamethrower.weapon', 'projectiles per shot', 'barrels', 0, 0, 2),
            # rate: H1 12 x (9/10) = 10.8, flat (Halo 1 has no ramp)
            (FT + r'\flamethrower.weapon', 'rounds per second', 'barrels', 0, 0, [10.8, 10.8]),
            # (zero now: a re-run finds them by the rate, not by the shared offset cache)
            (FT + r'\flamethrower.weapon', 'acceleration time', 'barrels', 0, 0, 0.0,
             {'anchor': ('rounds per second', 8)}),
            (FT + r'\flamethrower.weapon', 'deceleration time', 'barrels', 0, 0, 0.0,
             {'anchor': ('rounds per second', 12)}),
            # the ERROR ramp (nth 1, A1's 4b lesson): Halo 1's 0 / 0 -> the full cone at once
            (FT + r'\flamethrower.weapon', 'acceleration time', 'barrels', 0, 1, 0.0),
            (FT + r'\flamethrower.weapon', 'deceleration time', 'barrels', 0, 1, 0.0),
            # the live cone (nth 1): H1 0 / 2-8 deg x the PR's (0.25/0.5, 0.75/5.0) -> 0 / 1.0-1.2
            (FT + r'\flamethrower.weapon', 'minimum error', 'barrels', 0, 1, 0.0),
            (FT + r'\flamethrower.weapon', 'error angle', 'barrels', 0, 1, [1.0, 1.2]),
            # no barrel climb, no tracers (Halo 1's flame)
            (FT + r'\flamethrower.weapon', 'angle change per shot', 'barrels', 0, 0, [0.0, 0.0]),
            (FT + r'\flamethrower.weapon', 'rounds between tracers', 'barrels', 0, 0, 0),
            # the FLAME: velocity 3.6 -> 0 x (14/50) (the PR's; 'faster when owned by player' kept);
            # maximum range 16, lifetime 1.3-8 s, radii: Halo 1 raw; damage over its whole range (H1
            # air damage range 100 > 16: no falloff). The fields reading 0 are PINNED by the struct's
            # order (AI perception, collision, arming, danger radius, timer, minimum velocity,
            # maximum range -- h2_port_numbers.pin, probed)
            (FT + r'\projectiles\flame.projectile', 'initial velocity', '', 0, 0, 1.008),
            (FT + r'\projectiles\flame.projectile', 'final velocity', '', 0, 0, 0.0),
            (FT + r'\projectiles\flame.projectile', 'maximum range', '', 0, 0, 16.0),
            (FT + r'\projectiles\flame.projectile', 'timer', '', 0, 0, [1.3, 8.0], {'anchor': ('maximum range', -12)}),
            (FT + r'\projectiles\flame.projectile', 'collision radius', '', 0, 0, 0.5, {'anchor': ('maximum range', -24)}),
            (FT + r'\projectiles\flame.projectile', 'AI perception radius', '', 0, 0, 2.0, {'anchor': ('maximum range', -28)}),
            (FT + r'\projectiles\flame.projectile', 'danger radius', '', 0, 0, 0.4, {'anchor': ('maximum range', -16)}),
            (FT + r'\projectiles\flame.projectile', 'air damage range', '', 0, 0, [100.0, 100.0]),
            # damage: H1 18 / 20-23 x the PR's (6/10, 10/13); 'causes flaming death' (damage flags
            # bit 7, nth 1 -- the first `flags` is the effect's own: scale by distance / players only)
            (FT + r'\damage_effects\flame.damage_effect', 'damage lower bound', '', 0, 0, 10.8),
            (FT + r'\damage_effects\flame.damage_effect', 'damage upper bound', '', 0, 0, [15.384615, 17.692308]),
            (FT + r'\damage_effects\flame.damage_effect', 'flags', '', 0, 1, 128, {'anchor': ('damage lower bound', -8)}),
            # step 4b (port_field_audit.py --port flamethrower, list 2: H1 flamethrower / H1 PR x H2 PR)
            (FT + r'\flamethrower.weapon', 'bounding radius', '', 0, 0, 0.28),
            (FT + r'\flamethrower.weapon', 'acceleration scale', '', 0, 0, 0.444444),
            (FT + r'\flamethrower.weapon', 'illumination recovery time', 'barrels', 0, 0, 0.0),
            # list 4: ready time 0 in both Halo 1 tags -> the target donor's (the PR's) 0
            (FT + r'\flamethrower.weapon', 'ready time', '', 0, 0, 0.0),
            (FT + r'\projectiles\flame.projectile', 'bounding radius', '', 0, 0, 0.15),
            (FT + r'\damage_effects\flame.damage_effect', 'active camouflage damage', '', 0, 0, 1.25,
             {'anchor': ('damage upper bound', 16)}),
            # the flame's LOOK: the Brute plasma rifle's red streak recoloured to flame orange (a, r, g,
            # b), head -> tail, and widened (Halo 1's flame is a 0.5 wu collision ball) -- in game
            (FX + r'\flame_streak.contrail', 'color lower bound', 'point states', 0, 0, [0.6, 1.0, 0.55, 0.15]),
            (FX + r'\flame_streak.contrail', 'color upper bound', 'point states', 0, 0, [0.6, 1.0, 0.55, 0.15]),
            (FX + r'\flame_streak.contrail', 'color lower bound', 'point states', 1, 0, [0.15, 1.0, 0.25, 0.05]),
            (FX + r'\flame_streak.contrail', 'color upper bound', 'point states', 1, 0, [0.15, 1.0, 0.25, 0.05]),
            (FX + r'\flame_streak.contrail', 'width', 'point states', 0, 0, 0.35),
            (FX + r'\flame_streak.contrail', 'width', 'point states', 1, 0, 0.35),
            # first-person placement: Halo 1's animations carry Halo 1's view (camera = origin), so
            # start with none (the SMG's 0.02, 0, 0 is for its own graph) -- checked in game
            (FT + r'\flamethrower.weapon', 'first person weapon offset', '', 0, 0, [0.0, 0.0, 0.0]),
        ],
        'skipped': [
            ('melee damage', 'Halo 2 weapons share strike_melee / smash_melee: a row would move every weapon'),
            ("Halo 1's 'burning' effect (fire left on a target)", "no Halo 2 equivalent: 'causes flaming death' instead"),
        ],
    },

    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull (the world .model's donor, two
    # handed) scaled per axis to the flamethrower's render mesh, on the port's own world skeleton
    'collision': {
        'donor': r'objects\weapons\rifle\battle_rifle\battle_rifle',
        'port': FT + r'\flamethrower',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': FT + r'\collision\flamethrower.jms',                      # under data
        'port_render_jms': FT + r'\render\flamethrower.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 2.5,                   # the flamethrower is ~2x the BR's length
        'nodes_from_render': True,
    },

    # step 7 -- the HUD: a clone of the BATTLE RIFLE's (single, two-handed), the FUEL as 50 ticks (one
    # a shot = 2 fuel; Halo 2's meter reveals by fraction) on the BR meter's canvas, plate / backpack /
    # glyph drawn from the flamethrower's OWN world mesh (its H2 JMS: h3_weapon_glyph.mesh reads one),
    # Halo 1's crosshair (hud_reticles #5) sized by the PLASMA RIFLE ratio (H2 PR #4 ink / H1 PR #4
    # ink), the scope widgets blanked (no zoom in Halo 1). Heat shows on the gun (the PR's gauge)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\battle_rifle_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'flamethrower_meter',
        'donor_hud': r'ui\hud\battle_rifle',
        'port_hud': r'ui\hud\flamethrower',
        'weapon': FT + r'\flamethrower.weapon',
        'rounds': 50, 'rows': 2,
        'canvas': (197, 34), 'tick_w': 6,
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\flamethrower_backpack',
        'backpack_size': (62, 30),
        'model_3p': WORLD_JMS,
        'preview': 'flamethrower_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\battle_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',
        'name': 'flamethrower_bkd',
        'hud': r'ui\hud\flamethrower',
        'model_3p': WORLD_JMS,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 4,                 # the Plasma Rifle's fullscreen crosshair (the yardstick)
        'name': 'flamethrower_reticle',
        'hud': r'ui\hud\flamethrower',
        'footprint': 1.0,
        'h3_art': {'kind': 'h1', 'sheet': r'ui\hud\bitmaps\combined\hud_reticles', 'sequence': 5,
                   'yardstick': 4},
        'preview': 'flamethrower_reticle_preview.png',
    },
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\battle_rifle_scope_mask',
        'name': 'flamethrower_blank',
        'hud': r'ui\hud\flamethrower.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair',
                    'top_crosshair', '2x', 'distance_meter'),
        'size': (8, 8),
    },

    # step 8 -- the pickup icon at U+E153 (Halo 2's look, the AR's: HUD blue, outline + feature lines,
    # solid body), the messages smg_* -> ft2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': WORLD_JMS,
        'tif': 'flamethrower_h2_glyph.tif',
        'colour': (110, 171, 233),
        'style': {'line': (134, 202, 255), 'body': (72, 118, 172)},
    },
    'messages': {
        'donor_prefix': 'smg', 'donor_icon': '&smg',
        'donor_name': 'SMG', 'port_name': 'Flamethrower',
        'weapon': FT + r'\flamethrower.weapon',
    },

    # step 10 -- h2_port_sounds.py: Halo 1's OWN sounds from MCC's CLASSIC halo1 bank (h1_bank; 22 kHz
    # XBOX IMA, the .lst index -- memory h1-fmod-bank-sounds), 48 kHz, classic Opus. Halo 1 plays its
    # flame as a LOOP (fire_ft: `fire`); Halo 2 fires a sound per shot -> `fire` cut into 8 per-shot
    # slices (one shot interval 1/10.8 s + a 30 ms raised-cosine crossfade). The PR seed's graph
    # events cue: ready, melee, posing, OVERHEAT (Halo 1's overheat effect is silent: `burnout`, the
    # flame dying, approximates it) and the overheat EXIT (`light`, the re-ignition); the reload rides
    # the magazine's reloading effect; the flame's flyby is SILENT (Halo 1's flames have none)
    'sounds': {
        'weapon': FT + r'\flamethrower.weapon',
        'fire_fx': FX + r'\flamethrower_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'flamethrower'),
        'audio_key': 'Flamethrower',
        'h1_bank': {'ft_fire': (r'sound\old_sfx\weapons\flamethrower\fire',
                                {'slices': 8, 'seconds': 0.1226, 'fade': 0.03}),
                    'ft_dryfire': (r'sound\old_sfx\weapons\flamethrower\empty', {}),
                    'ft_reload': (r'sound\old_sfx\weapons\weapon_anims\flamethrower_reload', {}),
                    'ft_ready': (r'sound\old_sfx\weapons\weapon_anims\flamethrower_ready', {}),
                    'ft_melee': (r'sound\old_sfx\weapons\weapon_anims\flamethrower_melee', {}),
                    'ft_posing': (r'sound\old_sfx\weapons\weapon_anims\flamethrower_posing', {}),
                    'ft_overheat': (r'sound\old_sfx\weapons\flamethrower\burnout', {}),
                    'ft_oh_exit': (r'sound\old_sfx\weapons\flamethrower\light', {}),
                    'ft_ammo': (r'sound\old_sfx\weapons\weapon_pickup_ammo\ar_ammo', {}),
                    'ft_flyby': (None, {})},
        'sounds': {'ft_fire': ('ft_fire', 'weapon_fire'), 'ft_dryfire': ('ft_dryfire', 'weapon_empty'),
                   'ft_reload': ('ft_reload', 'weapon_reload'), 'ft_ready': ('ft_ready', 'weapon_ready'),
                   'ft_melee': ('ft_melee', 'weapon_melee'), 'ft_posing': ('ft_posing', 'weapon_ready'),
                   'ft_overheat': ('ft_overheat', 'weapon_overheat'),
                   'ft_oh_exit': ('ft_oh_exit', 'weapon_ready'),
                   'ft_ammo': ('ft_ammo', 'weapon_reload'), 'ft_flyby': ('ft_flyby', 'projectile_flyby')},
        'repoint_fx': [(r'sound\weapons\smg\fire', 'ft_fire'),
                       (r'sound_remastered\weapons\smg\fire_lod', 'ft_fire')],
        'repoint_weapon': [(r'sound\weapons\smg\dryfire', 'ft_dryfire'),
                           (r'sound\weapons\smg\smg_ammo', 'ft_ammo')],
        'repoint_tags': [(FX + r'\flamethrower_reload.effect', r'sound\weapons\battle_rifle\dryfire', 'ft_reload'),
                         (FT + r'\projectiles\flame.projectile', r'sound\weapons\plasma_rifle\plasma_proj', 'ft_flyby')],
        'graph_sounds': tuple((s, n) for s, n in (
            ('plasrifle_ready', 'ft_ready'), ('plasrifle_dual_ready', 'ft_ready'),
            ('plasrifle_melee1', 'ft_melee'),
            ('plasrifle_overheat', 'ft_overheat'), ('plasrifle_dual_overheat_l', 'ft_overheat'),
            ('plasrifle_dual_overheat_r', 'ft_overheat'),
            ('plasrifle_oh_exit', 'ft_oh_exit'), ('plasrifle_dual_ohexit_l', 'ft_oh_exit'),
            ('plasrifle_dual_ohexit_r', 'ft_oh_exit'),
            ('plasrifle_posing_zero', 'ft_posing'), ('plasrifle_posing_one', 'ft_posing'))
            + tuple(('plasrifle_dual_pose%d_%s' % (k, side), 'ft_posing') for k in range(4) for side in 'lr')),
        'graph_sound_dir': r'sound\weapons\plasma_rifle' + '\\',
        'gain': {'ft_flyby': -40.0},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_flamethrower_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_flamethrower_graphs_before_sounds',
    },

    # step 9 -- h2_port_fp_anims.py kind 'h1': Halo 1's OWN FP animations (HCEEK weapons\flamethrower\
    # fp\fp), composed into Halo 2 source animations and imported by `tool fp-model-animations`; the
    # graphs SEEDED from the Plasma Rifle's (its blend screen, its overheat events / sounds). The
    # Dervish RE-POSED (user, step 0): the Chief's arm chain, the Elite's fingers with the Chief's curl
    'fp_anims': {
        'kind': 'h1',
        'antr': H1FT + r'\fp\fp',
        'chief_arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
        'weapon_nodes': ['gun', 'ammo', 'cover'],
        # (Halo 1, Halo 2[, opt]). Halo 2's overheat = ONE animation `overheating` (the PR's 89 frames)
        # + `o_h_exit`: Halo 1's overheating (enter, 10) then its overheated loop to ~the overheat's
        # length ((1 - 0.12) / 0.513 = 1.7 s = 52 frames). No reload-full / put-away / 2nd melee in
        # Halo 1: the reload-empty serves both reloads, the melee both strikes, the ready reversed is
        # the put-away; throw-overheated has no Halo 2 slot (dropped)
        'map': [('first-person idle', 'first_person:idle', {'loop': True}),
                ('first-person posing', 'first_person:posing:var1', {'loop': True}),
                ('first-person ready', 'first_person:ready'),
                ('first-person ready', 'first_person:put_away', {'reverse': True, 'frames': 6}),
                ('first-person reload-empty', 'first_person:reload_empty'),
                ('first-person reload-empty', 'first_person:reload_full'),
                ('first-person melee', 'first_person:melee_strike_1'),
                ('first-person melee', 'first_person:melee_strike_2'),
                ('first-person throw-grenade', 'first_person:throw_grenade'),
                ('first-person overheating', 'first_person:overheating',
                 {'then': 'first-person overheated', 'frames': 52}),
                ('first-person o-h-exit', 'first_person:o_h_exit'),
                ('first-person moving', 'first_person:moving'),
                ('first-person overlays', 'first_person:overlays'),
                ('first-person overlays', 'first_person:pitch_and_turn')],
        'species': {
            'masterchief': {
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\support_low\fp_flamethrower',
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_plasma_rifle\fp_plasma_rifle'},
            'dervish': {
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\support_low\fp_flamethrower',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_plasma_rifle\fp_plasma_rifle',
                'repose': True},
        },
        'weapon_dir': FT + r'\fp_flamethrower',
    },

    # step 4b -- port_field_audit.py --port flamethrower: every field NO card covers where Halo 1's
    # flamethrower differs from Halo 1's Plasma Rifle (the yardstick) -- list 2 must say 0 to port
    'field_audit': {
        'source_kit': 'HCEEK',
        'source': {'weapon': (H1FT + r'\flamethrower.weapon', r'weapons\plasma rifle\plasma rifle.weapon'),
                   'projectile': (H1FT + r'\flame.projectile', r'weapons\plasma rifle\bolt.projectile'),
                   'damage_effect': (H1FT + r'\impact damage.damage_effect', r'weapons\plasma rifle\bolt.damage_effect')},
        'target': {'weapon': (FT + r'\flamethrower.weapon', r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon'),
                   'projectile': (FT + r'\projectiles\flame.projectile',
                                  r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (FT + r'\damage_effects\flame.damage_effect',
                                     r'objects\weapons\rifle\plasma_rifle\damage_effects\plasma_rifle_bolt.damage_effect')},
        # first run 2026-10-21: list 2 weapon 5 / projectile 1 / damage 5 -> written (numbers, 4b rows) or
        # decided here. Lists 3 / 4 / 5, decided:
        'decisions': {
            'barrels/[0]/rounds per second': "4a's flat 10.8 (H1 12 x the PR's 9/10; Halo 1 has no ramp)",
            'barrels/[0]/error angle (by name: the DUAL cone)': "4a's LIVE cone nth 1 = 1.0-1.2; the dual cone (nth 0) "
                                                               "stays the SMG's (not dual wielded)",
            'damage upper bound (element-wise 16.67, 16.43)': "4a's pair 15.38-17.69 (H1 20-23 x the PR's AVERAGE ratio "
                                                              "10/13 -- the PR's H2 pair is flat, an element ratio inverts it)",
            'forward / outward velocity, radius, exponent; rotation; pushback':
                "breaking-effect / camera-shake cosmetics: flaming_death's 0 (Halo 1's flame shakes nothing)",
            'instantaneous acceleration': "0 (both Halo 1 tags 0; a flame does not push)",
            'barrels/[0]/minimum error (nth 0)': "the SMG's dual-cone 0.5 (not dual wielded)",
            'flags (projectile 112 / damage)': "Halo 1 enums do not carry; damage flags = 'causes flaming death' (128)",
            'attachments/#count': "the PR bolt's 2 (contrail + light volume = the flame's look)",
            'impact / detonation noise': "the PR bolt's (Halo 1's 'loud' is an AI-perception enum)",
            'timer, radii, maximum range, air damage range': 'Halo 1 raw (a 0 on the PR: no ratio), step 4',
            'damage modifiers/*': "no Halo 2 field: the damage TABLE (group `burning`) carries the material response",
            'functions (the PR\'s `heat` export)': "the SMG clone has none: the heat display's gauge may sit still "
                                                  "(checked in game)",
            'firing effects/[1], old message index, on-ground scale, predicted bitmaps': "the SMG's (clone donor)",
        },
    },

    'test': {'level': '05a_deltaapproach', 'dervish_level': '06b_floodzone'},
    'residency': {'levels': 'all', 'placements': False},
}

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
# a Bungie effect with nothing in it (no parts, no particles): where a slot must stay filled but show
# nothing (the flame's old glow attachment, its impacts)
EMPTY_FX = r'effects\objects\weapons\support_high\rocket_launcher\rocket_overpenetrate_glass'
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
        'glyph': 0xE153,           # 2026-10-22: back from E553 (MCC claims E400+: its placeholder); user: untinted
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
    # step 11 (decided in session): Halo 1 keeps AI firing data in ACTOR VARIANTS (the Flood carry the
    # flamethrower there), not ai\generic -- so a Halo 2 STAND-IN: the Plasma Rifle's own entry (the
    # yardstick; Halo 2's automatic close-range heat weapon), unchanged -- its maximum firing range 13
    # sits inside the flame's 16, normal combat range 3-7. `ai_firing_profile.py --h2-port flamethrower`
    'firing_profile': {'donor_weapon': r'objects\weapons\rifle\plasma_rifle\plasma_rifle',
                       'why': "Halo 1 has no ai\\generic: the yardstick's own entry, max firing range 13 < 16"},
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
        # symbols; the AR's route); the hundreds digit dropped (boot 2, the user: 100 cannot show)
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
                    # `vent`: the PR overheat effect's marker (boot 3: the overheat effect)
                    'steam vent01': 'vent', 'steam vent02': 'vent'},
        # boot 4 (user: 'move the digits a bit apart'): the two counter quads touch (Halo 1 drew three
        # in a row); each pushed out by 12% of their spacing
        # boot 8 ('the numbers can be re-aligned'); boot 9's +0.33 towards the ones side was the
        # wrong way ('they need to move LEFT and DOWN on the box'): 0.2 of their spacing towards the
        # tens side from where Halo 1 put them, and down 0.15 of a digit's height
        'digit_spread': (('flamethrower_tens=?', 'flamethrower_ones=?'), 0.12, -0.2, 0.15),
        # boot 8 (the user's plasma pistol check: its charge glow shows in FP, ours never did): Halo 2
        # draws attachment effects at the WORLD model's markers even in first person (boot 5: `pilot`
        # on the FP model only -> nothing anywhere), and the flamethrower's world model hangs at the
        # hip, out of view. So the FP pilot is FP GEOMETRY: two crossed cards (1.2 x 2.4 cm) standing
        # on the `pilot` marker (32.04, 0.44, 3.36), Halo 1's flame sprite in blue on Bungie's
        # time-animated additive shader (step 2); the world-model pilot stays the attachment
        # boot 10 ('still not visible'; its FP screenshot): `pilot` sits INSIDE the nozzle mouth
        # (Halo 1's camera-facing sprite glows out of it; the gun's vertices within 4 units span y
        # -2.1..2.9) -> a larger card (2.5 x 3.5) just in front of the muzzle (primary_trigger x 33.0)
        # boot 15: VISIBLE for the first time (two_add_env_illum) -- 'move it forward and turn it':
        # forward to the nozzle's HEAD (x 42-45), at the mouth of its claw (which faces the camera's
        # left, +y), smaller -- checked on Halo 1's FP idle render (a forward-pointing card is edge-on
        # to the camera; one behind the head is hidden)
        # boot 16 video: 'slightly up' -> +0.7
        'fp_cards': [('flamethrower_pilot', (42.6, 1.6, 4.6), (1.4, 2.2))],
        # boot 5 ('no visible pilot flame'): Halo 1 has `pilot` / the steam vents on the FP model only;
        # the weapon's attachments look markers up on the WORLD model -- placed there at the FP
        # markers' offsets from primary_trigger (the two models share the gun's axes and length)
        'world_extra_markers': [('pilot', 0, (0.437775, -0.317111, -0.155106, 0.826883), (44.7091, 0.4053, 6.8813)),
                                ('vent', 0, (0.641769, 0.309753, 0.634685, 0.298932), (17.9504, 3.4267, 1.9751)),
                                ('vent', 0, (0.707975, 0.012502, 0.706127, -0.000299), (19.7424, -0.223, 4.6328))],
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
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color', None),
                    # boot 1 ('the screen and the weapon overall is missing some details'): Halo 1's
                    # SELF-ILLUMINATION -- the diffuse x its multipurpose GREEN (the self-illum mask:
                    # the lit tank window, the lights), on Bungie's lit PR template
                    (H1FT + r'\bitmaps\flamethrower', 'flamethrower_illum', SMG + r'\bitmaps\smg',
                     ('mask_from', H1FT + r'\bitmaps\flamethrower multipurpose', 1), None),
                    # the gun's HEAT BAR (boot 1: Bungie's PR gauge art showed as a brown block on Halo
                    # 1's quad): Halo 1's own red bar as the meter's colour, and a REVEAL ramp over the
                    # rows the quad samples (0.466-0.966: Halo 1 scrolled the texture)
                    (H1FT + r'\bitmaps\flamethrower_heat_display', 'flamethrower_heat_meter',
                     r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_heat_gauge', 'color', None),
                    # (boot 3's flame_sprite -- Halo 1's `burning flame` sprite 4 as the contrail's
                    # texture -- left with the contrail in boot 4: a particle needs a SPRITES bitmap)
                    (None, 'flamethrower_heat_alpha',
                     r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_heat_gauge_alpha',
                     # (boot 9 reversed this ramp: 'still starts filled, now top to bottom' -- the
                     # fill direction was right; the 'full' look is the gauge's OFF part, step 3)
                     ('gradient', 'v', True, (0.466, 0.966)), (32, 128)),
                    # the FP PILOT card (boot 8): Halo 1's `burning flame` sprite 4, its grey tinted
                    # Halo 1's pilot blue, on the seed of the shader that draws it (additive: black = clear)
                    (r'effects\particles\flash\bitmaps\burning flame', 'flamethrower_pilot_flame',
                     r'objects\cinematics\human\pillarofautumn\bitmaps\poa_exhaust',
                     # boot 13: bright, the core near white (an additive card adds nothing visible on
                     # 06b's bright snow at boot 12's peak blue 173 -- Halo 2's own flames are white-hot)
                     ('sprite', 4, ('tint', (1.2, 1.5, 2.0), 0)), (64, 64))],
        'shaders': [
            # the gun and the tank lit (boot 1): Bungie's PR `plasma_rifle_luminous` (tex_bump_env_illum:
            # bump, base, self-illum -- the base named twice; '#1' = the self-illum copy, moved first)
            ('flamethrower', r'objects\weapons\rifle\plasma_rifle\shaders\plasma_rifle_luminous',
             {r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle#1': FT + r'\bitmaps\flamethrower_illum',
              r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle': FT + r'\bitmaps\flamethrower',
              r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_bump': FT + r'\bitmaps\flamethrower_bump'}),
            ('flamethrower_ammo', r'objects\weapons\rifle\plasma_rifle\shaders\plasma_rifle_luminous',
             {r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle#1': FT + r'\bitmaps\flamethrower_illum',
              r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle': FT + r'\bitmaps\flamethrower',
              r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_bump': FT + r'\bitmaps\flamethrower_bump'}),
            # the fuel SCREEN: Halo 1 self-lights it by its own multipurpose map (= the screen bitmap):
            # the shotgun sight's tex_bump_illum (lit base + self-illum, OPAQUE). Boots 1-7 it never
            # showed -- the model was inside-out (boot 8); boot 8 on the BR digit shader read
            # 'holographic, transparent, hard to read' (its detail globs, full white): back here, the
            # glow a moderate grey (step 3)
            ('flamethrower_screen', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': FT + r'\bitmaps\flamethrower_screen'}),
            # the FP PILOT card: Bungie's time-animated additive (the Pillar of Autumn's engine exhaust:
            # one_add_illum, its self-illum colour pulsing on a 2 s period -- the one shipped example)
            # boot 14 ('no pilot flame still', after boots 10-14 on poa_engine_exhaust): no Bungie FP weapon
            # draws one_add_illum -- their FP glow parts are two_add_env_illum (the compass / display
            # kind) or *_active_camo -> the AR port's compass shader (two_add_env_illum, constant white,
            # drawn in first person in the AR's boots)
            ('flamethrower_pilot', r'objects\weapons\rifle\assault_rifle\shaders\assault_rifle_compass',
             {r'objects\weapons\rifle\assault_rifle\bitmaps\assault_rifle_compass': FT + r'\bitmaps\flamethrower_pilot_flame'}),
            ('flamethrower_heat_display', r'objects\weapons\rifle\plasma_rifle\shaders\plasma_rifle_gauge',
             # the alpha FIRST: the meter's new path is as long as `..._heat_gauge_alpha`, and a
             # repoint refuses two records of one length
             {r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_heat_gauge_alpha': FT + r'\bitmaps\flamethrower_heat_alpha',
              r'objects\weapons\rifle\plasma_rifle\bitmaps\plasma_rifle_heat_gauge': FT + r'\bitmaps\flamethrower_heat_meter'}),
            ('flamethrower_tens', r'objects\weapons\rifle\battle_rifle\shaders\tens', {}),
            ('flamethrower_ones', r'objects\weapons\rifle\battle_rifle\shaders\ones', {}),
            # Halo 1's THIRD digit: boot 1 added it (a shader reading 'primary_ammunition_zero', which no
            # weapon exports: always 0 -- Halo 2 exports only primary_ammunition_ones / _tens); boot 2
            # (user: '000 is useless for a full tank'): removed again, two digits
        ],
        'report_rows': [(FT + r'\bitmaps\flamethrower_bump', 'the port (flat)'),
                        (SMG + r'\bitmaps\smg_bump', 'Bungie SMG')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon (spew, 1 magazine / 1 trigger / 1 barrel; the
    # heat fields are plain fields, step 4), the BR's world .model (two-handed). The FLAME:
    #   projectile = the Plasma Rifle bolt's clone (the yardstick's; Halo 2's player projectile WITH
    #     flight attachments -- a contrail + light volume, both made attached EFFECTS: the flame is
    #     Bungie's rocket exhaust, boot 4);
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
                   # the FLAME (boot 4): Bungie's ROCKET EXHAUST -- its rocket_flame / rocket_flame_core
                   # systems are LOCAL looping particles, a flame that rides its rocket; its two smoke
                   # systems (world space: the boot-3 'big fire, not moving') disabled in step 4. Its
                   # particle = Bungie's own fire sprite (effects\generic\fires\fire, screen facing)
                   (r'effects\objects\weapons\support_high\rocket_launcher\rocket_exhaust.effect', FX + r'\flame_burning.effect'),
                   (r'effects\generic\fires\fire.particle', FX + r'\flame_fire.particle'),
                   (r'effects\objects\weapons\support_high\rocket_launcher\rocket_flame.particle', FX + r'\flame_flash.particle'),
                   # boot 3 (user: 'build the support for the pilot flame and overheat effect'): the PILOT
                   # (Halo 1: a small blue flame at `pilot` while the weapon is ready) = the same rocket
                   # flame, tiny and tinted blue (boot 4: the plasma pistol's charge sparks were invisible);
                   # the OVERHEAT effect = the plasma rifle's (Halo 1's own is the same `plasma overheat`
                   # particles at its steam vents)
                   (r'effects\objects\weapons\support_high\rocket_launcher\rocket_exhaust.effect', FX + r'\flamethrower_pilot.effect'),
                   # boot 6 ('a green flame, static'): the orange fire sprite x a blue tint reads green
                   # -> Bungie's TINTABLE flame (white_rolling_flame: an alpha sprite, the tint is its colour)
                   (r'effects\generic\fires\white_rolling_flame.particle', FX + r'\pilot_flame.particle'),
                   (r'effects\objects\weapons\rifle\plasma_rifle\overheated.effect', FX + r'\flamethrower_overheated.effect'),
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
            # the FLAME. Halo 1 (HCEEK, per second -- its AR bullet reads 324): a flame projectile at 3.6
            # wu/s + the shooter's velocity, living 1.3 s in flight, carrying `flame detonation` ->
            # `burning`: small flame sprites (radius 0.1-0.25 wu) and smoke. Boots 1-3 (a plasma streak;
            # Bungie's scenery fire; the rocket exhaust -- both drop big WORLD-space fire where they
            # start: 'too big, in my face, not moving'); boot 4 a contrail + the PR bolt's LIGHT VOLUME
            # (the light volume IS the plasma bolt's look: 'the same projectile as boot 1', the contrail
            # unseen). Now: the bolt's contrail slot becomes the attached EFFECT flame_burning (the
            # rocket's local flame, Bungie's fire sprite, Halo 1's flame size), its light volume slot an
            # empty effect; 21.6 flames a second overlap into the stream
            (FT + r'\projectiles\flame.projectile', 'cont', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak', 'the contrail slot -> an effect',
             {'class': 'effe', 'nth': 0}),
            (FT + r'\projectiles\flame.projectile', 'effe', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             FX + r'\flame_burning', "the flame (the rocket's local flame)", {'nth': 0}),
            (FT + r'\projectiles\flame.projectile', 'MGS2', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak', 'the light volume slot -> an effect',
             {'class': 'effe', 'nth': 0}),
            (FT + r'\projectiles\flame.projectile', 'effe', r'effects\objects\weapons\rifle\plasma_rifle\plasma_streak',
             EMPTY_FX, "no plasma bolt (the PR's light volume)", {'nth': 0}),
            (FX + r'\flame_burning.effect', 'prt3', r'effects\objects\weapons\support_high\rocket_launcher\rocket_flame',
             FX + r'\flame_fire', 'the flame: a fire sprite'),
            (FX + r'\flame_burning.effect', 'prt3', r'effects\objects\weapons\support_high\rocket_launcher\rocket_flame_core',
             FX + r'\flame_fire', "the flame's core: a fire sprite"),
            # the first-person MUZZLE FLASH (closing check 10, h2_effect_particles: Halo 1's is `fp flash
            # flame` -- 3-5 flame sprites at `spawn fire`, first person only; the port wore the SMG's
            # two burst sprites): the SMG's bursts drawn with the fire sprite, its smoke kept
            # (boot 13 drew the fire sprite there: 'I can't see the muzzle flash' -> the rocket's
            # own flame-flash sprite, a muzzle sprite made for a 0.1 s life)
            (FX + r'\flamethrower_fire.effect', 'prt3', r'effects\objects\weapons\rifle\smg\fire_burst_center',
             FX + r'\flame_flash', 'the FP flash: a flame, not a bullet burst', {'every': True}),
            (FX + r'\flamethrower_fire.effect', 'prt3', r'effects\objects\weapons\rifle\smg\fire_burst_long',
             FX + r'\flame_flash', 'the FP flash: a flame, not a bullet burst'),
            (FX + r'\flamethrower_pilot.effect', 'prt3', r'effects\objects\weapons\support_high\rocket_launcher\rocket_flame',
             FX + r'\pilot_flame', 'the pilot: a tintable flame'),
            (FX + r'\flamethrower_pilot.effect', 'prt3', r'effects\objects\weapons\support_high\rocket_launcher\rocket_flame_core',
             FX + r'\pilot_flame', "the pilot's core: a tintable flame"),
            # where a flame hits: no big fire (boot 2); Halo 1's `flame char` is a scorch + a small
            # flash -- the clone's material effects keep the scorch decals
            (FT + r'\projectiles\flame.projectile', 'effe', r'effects\impact\plasma_slow\soft_terrain',
             EMPTY_FX, 'impact on soft materials -> nothing big', {'every': True}),
            (FT + r'\projectiles\flame.projectile', 'effe', r'effects\impact\plasma_slow\hard_metal_thick',
             EMPTY_FX, 'impact on hard materials -> nothing big', {'every': True}),
            # the OVERHEAT effect into the clone's EMPTY `overheated` slot (h2_tagref.fill_reference,
            # field-checked: an empty reference is not exported, only the result says which was filled)
            (FT + r'\flamethrower.weapon', 'effe', '', FX + r'\flamethrower_overheated', 'the overheat effect',
             {'field': 'overheated'}),
            # the HUD is the BR's clone (step 7: single, two-handed; the SMG's is dual-wield shaped)
            (FT + r'\flamethrower.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\flamethrower', 'its own HUD (step 7)'),
            (FT + r'\flamethrower.weapon', 'effe', r'effects\objects\weapons\rifle\battle_rifle\reload',
             FX + r'\flamethrower_reload', "the magazine's reloading effect (Halo 1's reload sound, step 10)"),
        ],
        # the PILOT flame: a second attachment beside the muzzle light, at the FP model's `pilot`
        # marker, no scale function = always on (Halo 1: `ready`) -- h2_tagref.append_attachment
        'append_attachments': [(FT + r'\flamethrower.weapon', 'effe', FX + r'\flamethrower_pilot', 'pilot', 'ligh')],
        # the rocket flame's SIZE (emitter function data, float32): flame 0.5-0.55 -> 0.15-0.3 wu (Halo
        # 1's flame sprites, radius 0.1-0.25), core 0.65 -> 0.08; the pilot 0.012-0.016 / 0.008, its
        # white tint (BGRA ffffffff, every system) -> a pale blue (Halo 1's pilot light)
        'byte_edits': [
            (FX + r'\flame_burning.effect', '0000003fcdcc0c3f', '9a99193e9a99993e'),
            (FX + r'\flame_burning.effect', '010008006666263f', '010008000ad7a33d'),
            # the flame GROWS (boot 6, user: 'would be nice if the flame started small and expanded'):
            # the size functions read the EMITTER's age (= the flame's, the effect is born with the
            # projectile), not the particle's (a looping sprite reborn every 0.02 s: always ~0) --
            # each emitter function starts with four 2-byte enums (input, range, output modifier,
            # its input), the size the 5th; found by the unique run before it (its predecessor's
            # data pointer). 0 particle age -> 4 emitter age; the curves in function_edits
            (FX + r'\flame_burning.effect', '00aa6a03cccf800100000200', '00aa6a03cccf800104000200',
             ('Input Variable',)),
            (FX + r'\flame_burning.effect', '78af6a03cccf800100000200', '78af6a03cccf800104000200',
             ('Input Variable',)),
            # (boot 5: the pilot 0.02-0.03 / 0.012 wu)
            (FX + r'\flamethrower_pilot.effect', '0000003fcdcc0c3f', '0ad7a33c8fc2f53c'),
            (FX + r'\flamethrower_pilot.effect', '010008006666263f', '01000800a69b443c'),
            # boot 6 ('green, static'): the pilot EMITS -- 12 flames a second living 0.25 s (the
            # rocket's one looping sprite never changes), flags 'looping' off in step 4
            (FX + r'\flamethrower_pilot.effect', '010000000000803f0000803f', '01000000000040410000803f'),
            (FX + r'\flamethrower_pilot.effect', '010000000ad7a33c', '010000000000803e'),
            # the fuel SCREEN's self-illum colour is an animation function (a const colour is unused):
            # the shotgun sight's dark green BGRA 07 30 0e -> a moderate grey (boot 8: full white
            # read washed out)
            (FT + r'\shaders\flamethrower_screen.shader', '0120000007300eff', '012000008c8c8cff'),
            # the heat gauge's OFF part (above the heat level): the PR draws it at 0.5-0.67 opacity
            # (meter_off_opacity, a periodic on `one`) -- on Halo 1's red bar it read as 'starts
            # filled' (boots 8-10); Halo 1 shows only the heat -> 0
            (FT + r'\shaders\flamethrower_heat_display.shader', '03000a000000003f83c02a3f',
             '03000a000000000000000000'),
            (FX + r'\flamethrower_pilot.effect', '01200000ffffffff0000803f00000000ffffffff',
             '01200000ff9040ff0000803f00000000ff9040ff'),
        ],
        # the DIGITS' colour (boots 5-7 'red, always'): function TYPE 1 is CONSTANT -- it ignores
        # its input whatever its colours; type 2, a TRANSITION (Bungie's PR heat gauge: green -> red
        # by heat), is 36 bytes: slot 0 = input 0 = EMPTY -> red, slot 3 = input 1 = FULL -> the BR's
        # cyan; the input the fuel FRACTION (filled below: 100 and 0 both read '00')
        'function_edits': [
            # the flame's SIZE over its age: type 1 constants (0.15-0.3 / 0.08) -> type 2 transitions
            # (a scalar transition: +4 the value at input 0, +8 at input 1 -- Bungie's PR gauge
            # meter_value): flame 0.06 -> 0.35, core 0.04 -> 0.12 (Halo 1's sprites grow as they fly).
            # Boots 13-16: the user's one-shot VIDEO (boot 16, the flame at the ratio's 1.0 wu/s) shows
            # it plainly -- the first frame the largest, then shrinking: +4 IS the start (age 0); boot
            # 13's 'starts big' was perspective (3.6 wu/s, leaving the camera). And far too big: Halo
            # 1's sprites are radius 0.1-0.25 -> flame 0.05 -> 0.3, core 0.03 -> 0.1 (the 2nd pair of
            # rows takes boot 16's tags there)
            (FX + r'\flame_burning.effect', '010108009a99193e9a99993e00000000000000000000803f0000803f',
             '02000000cdcc4c3d9a99993e0000000000000000000000000000803f000000000000803f'),
            (FX + r'\flame_burning.effect', '010008000ad7a33d0000000000000000000000000000803f0000803f',
             '020000008fc2f53ccdcccc3d0000000000000000000000000000803f000000000000803f'),
            (FX + r'\flame_burning.effect', '02000000cdcccc3e0ad7a33c0000000000000000000000000000803f000000000000803f',
             '02000000cdcc4c3d9a99993e0000000000000000000000000000803f000000000000803f'),
            (FX + r'\flame_burning.effect', '02000000295c0f3e0ad7233c0000000000000000000000000000803f000000000000803f',
             '020000008fc2f53ccdcccc3d0000000000000000000000000000803f000000000000803f'),
            # the FP pilot FLICKERS (boot 16 video: 'not animated'): the compass shader's constant
            # white -> a periodic COLOUR (Bungie's exhaust periodic, colour slots in place of its first
            # four floats: dim grey / white), its time period set in step 4
            (FT + r'\shaders\flamethrower_pilot.shader', '01200000ffffffff0000000000000000ffffff000000803f0000803f',
             '03200900808080ffffffffffffffffffffffffff0000803f00000000000000bf0000803f0000803f00000000000000000000803f'),
            (FT + r'\shaders\flamethrower_tens.shader', '01200000f4e08eff0000000000000000ffffff000000803f0000803f',
             '022003004040ffff0000000000000000f4e08eff000000000000803f000000000000803f'),
            (FT + r'\shaders\flamethrower_ones.shader', '01200000f4e08eff0000000000000000ffffff000000803f0000803f',
             '022003004040ffff0000000000000000f4e08eff000000000000803f000000000000803f')],
        # the pilot effect sits at the weapon's `pilot` marker (the rocket's is `exhaust`)
        # and the flame's at `root` (boot 5, 'no visible projectile': a projectile has no model, so no
        # `exhaust`; Bungie's effects on model-less bolts name `root` -- the plasma pistol's charged glow)
        'string_id_renames': [(FX + r'\flamethrower_pilot.effect', {'exhaust': 'pilot'}),
                              (FX + r'\flame_burning.effect', {'exhaust': 'root'})],
        # the digits' colour input: the fuel FRACTION `primary_ammunition` (the engine value the
        # Carbine's own `ammo` function imports; boots 5-7 were red because the function was constant,
        # not for this input -- the tens digit could not tell 100 from 0, the user's point of the
        # colour). The pilot only while the weapon is READY (Halo 1's pilot; the
        # PR's heat flares scale by `ready`, the plasma pistol's charge glow by primary_charged): an
        # attachment with no scale is made once, on the world model -- boot 6 drew it only there
        'string_id_fills': [
            (FT + r'\flamethrower.weapon', 'primary scale', 'attachments', 1, 0, 'ready',
             {'after': 'flamethrower_pilot\x00pilot'}),      # the pilot element's pooled path + marker
            (FT + r'\shaders\flamethrower_tens.shader', 'input name', 'animation properties', 0, 1, 'primary_ammunition'),
            (FT + r'\shaders\flamethrower_ones.shader', 'input name', 'animation properties', 0, 1, 'primary_ammunition')],
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
            # BOOT 1 (user: 'no heat functionality, I can fire the entire ammo load'): the per-value PR
            # ratio broke the MECHANIC -- heat x1.88 but loss x2.84: 0.135 x 10.8/s - 1.25/s = +0.21/s,
            # overheat after 4.8 s, the 100-fuel tank empties in 4.6 s (the boot shows Halo 2 adds heat
            # per SHOT and drains it while firing). Now HALO 1'S OWN HEAT PER SECOND: Halo 1 fires 10/s
            # (its 30 Hz trigger) x 0.072 = 0.72/s -> 0.0667 a shot at 10.8/s; loss 0.44 (one rate in
            # Halo 1, both here), recovery 0.30: overheat after 1 / (0.72 - 0.44) = 3.6 s held (tank
            # 4.6 s), cool-down (1 - 0.3) / 0.44 = 1.6 s
            (FT + r'\flamethrower.weapon', 'heat recovery threshold', '', 0, 0, 0.3, {'anchor': ('ready time', 36)}),
            (FT + r'\flamethrower.weapon', 'overheated threshold', '', 0, 0, 1.0, {'anchor': ('ready time', 40)}),
            (FT + r'\flamethrower.weapon', 'heat loss per second', '', 0, 0, 0.44, {'anchor': ('ready time', 52)}),
            (FT + r'\flamethrower.weapon', 'overheated heat loss per second', '', 0, 0, 0.44, {'anchor': ('ready time', 60)}),
            (FT + r'\flamethrower.weapon', 'heat illumination', '', 0, 0, 1.0, {'anchor': ('ready time', 56)}),
            (FT + r'\flamethrower.weapon', 'heat generated per round', 'barrels', 0, 0, 0.066667,
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
            # the live cone (nth 1): H1 0 / 2-8 deg x the PR's (0.25/0.25, 0.75/2.5) -> 0 / 2.0-2.4.
            # The Halo 1 PR's cone is read from MCC's MAP (0.25-2.5 deg, balance_port / the catalog):
            # the HCEEK tag says 0.5-5, and the 4a table (h2_ft_ttk_4a, HCEEK) gave 1.0-1.2 from it
            (FT + r'\flamethrower.weapon', 'minimum error', 'barrels', 0, 1, 0.0),
            (FT + r'\flamethrower.weapon', 'error angle', 'barrels', 0, 1, [2.0, 2.4]),
            # no barrel climb, no tracers (Halo 1's flame)
            (FT + r'\flamethrower.weapon', 'angle change per shot', 'barrels', 0, 0, [0.0, 0.0]),
            (FT + r'\flamethrower.weapon', 'rounds between tracers', 'barrels', 0, 0, 0),
            # the FLAME: velocity 3.6 -> 0 x (14/50) (the PR's; 'faster when owned by player' kept);
            # maximum range 16, lifetime 1.3-8 s, radii: Halo 1 raw; damage over its whole range (H1
            # air damage range 100 > 16: no falloff). The fields reading 0 are PINNED by the struct's
            # order (AI perception, collision, arming, danger radius, timer, minimum velocity,
            # maximum range -- h2_port_numbers.pin, probed)
            # BOOT 1 ('projectiles are not flames at all ... mirror their exact behavior'): the flame moves
            # as HALO 1's does -- 3.6 wu/s -> 0, without Halo 2's player speed-up (the PR ratio's 1.0
            # wu/s crawled); Halo 1's projectile flags carry no such speed-up
            (FT + r'\projectiles\flame.projectile', 'flags', '', 0, 1, 0),
            (FT + r'\projectiles\flame.projectile', 'initial velocity', '', 0, 0, 3.6),
            (FT + r'\projectiles\flame.projectile', 'final velocity', '', 0, 0, 0.0),
            (FT + r'\projectiles\flame.projectile', 'maximum range', '', 0, 0, 16.0),
            # boot 2 ('the projectile flies for far too long'): Halo 1's flame flags 112 = 'MINIMUM
            # unattached detonation time' + 'random attached detonation time' -- in flight it lives the
            # timer's MINIMUM, 1.3 s (~4.7 wu at 3.6); 1.3-8 s only once stuck. Halo 2 has neither flag
            # (only 'detonation max time if attached'): the flight value, 1.3 s
            (FT + r'\projectiles\flame.projectile', 'timer', '', 0, 0, [1.3, 1.3], {'anchor': ('maximum range', -12)}),
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
            # boot 2 ('muzzle is not lit'): the weapon's muzzle light is scaled by `illumination`, and a
            # 0 recovery (the 4b ratio from Halo 1's 0) gives it no time to show -> the SMG's 0.05
            (FT + r'\flamethrower.weapon', 'illumination recovery time', 'barrels', 0, 0, 0.05,
             {'anchor': ('heat generated per round', -4)}),
            # list 4: ready time 0 in both Halo 1 tags -> the target donor's (the PR's) 0
            (FT + r'\flamethrower.weapon', 'ready time', '', 0, 0, 0.0),
            (FT + r'\projectiles\flame.projectile', 'bounding radius', '', 0, 0, 0.15),
            (FT + r'\damage_effects\flame.damage_effect', 'active camouflage damage', '', 0, 0, 1.25,
             {'anchor': ('damage upper bound', 16)}),
            # first-person placement: Halo 1's animations carry Halo 1's view (camera = origin), so
            # start with none (the SMG's 0.02, 0, 0 is for its own graph) -- checked in game
            # the flame and the pilot (boot 4: the rocket exhaust's clones): its two WORLD-space smoke
            # systems (#2 rocket_exhaust_smoke, #3 smoke_volumetric: boot 3's 'big fire, not moving')
            # off -- flags 128 ('spread between ticks') + 8 'disabled for debugging' (bit 3, which
            # Bungie ships set: slipspace_open's burst_additive reads 10)
            (FX + r'\flame_burning.effect', 'flags', 'particle systems', 2, 0, 136),
            (FX + r'\flame_burning.effect', 'flags', 'particle systems', 3, 0, 136),
            (FX + r'\flamethrower_pilot.effect', 'flags', 'particle systems', 2, 0, 136),
            (FX + r'\flamethrower_pilot.effect', 'flags', 'particle systems', 3, 0, 136),
            # the pilot's flames EMIT (boot 6, 'static'): 'looping particle' off
            (FX + r'\flamethrower_pilot.effect', 'flags', 'particle systems', 0, 0, 0),
            (FX + r'\flamethrower_pilot.effect', 'flags', 'particle systems', 1, 0, 0),
            # the FP pilot's flicker period: 0.15 s (the compass reads 0 -- pinned 12 bytes after the
            # animation's `type`: type / input / range / time period)
            (FT + r'\shaders\flamethrower_pilot.shader', 'time period', 'animation properties', 0, 0, 0.15,
             {'anchor': ('type', 12)}),
            # the screen's speculars (the shotgun sight's were green): grey
            (FT + r'\shaders\flamethrower_screen.shader', 'const color', 'parameters', 3, 0, [0.15, 0.15, 0.15]),
            (FT + r'\shaders\flamethrower_screen.shader', 'const color', 'parameters', 4, 0, [0.07, 0.07, 0.07]),
            # boot 1 (user): '1 unit forward and down' (1 unit = 0.01 wu, the AR's convention)
            (FT + r'\flamethrower.weapon', 'first person weapon offset', '', 0, 0, [0.01, 0.0, -0.01]),
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
        # boot 2 (user: 'one draining meter rather than ammo pips'): one 1-px column a threshold
        # step -- 197 columns in one row = a bar that drains with the fuel fraction, 14 px tall
        'rounds': 197, 'rows': 1,
        'canvas': (197, 14), 'tick_w': 1,
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
                   'yardstick': 4,
                   # boot 1 (user: 'crosshair is too big'): Halo 1's ON-SCREEN size, measured on the
                   # user's 1080p screenshots -- Halo 1's ring 119 px across, ours 236 px from 177 ink
                   # px -> 177 x 119 / 236 = 89 ink px (the AR's rule: the source game's own size)
                   'target_ink': 89},
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

    # step 7b -- h2_port_hud_widgets.py: the HEAT METER (boot 1: 'no heat meter'). Two of the blanked
    # scope widgets become the Plasma Rifle's heat widgets (its `heat_meter_right` / `heat_background_
    # right`: input WEAPON heat / WEAPON time on overheat, its meter + pulse art and shaders, its
    # flags), placed UNDER the fuel meter (at -196,42; boot 2 a 14 px bar -> y 60).
    # Widget fields reading 0 are pinned from the widget's `anchor` (input 1 at -24, probed)
    'hud_widgets': {
        'hud': r'ui\hud\flamethrower.new_hud_definition',
        'widgets': [
            {'name': 'distance_meter', 'bitmap': NEW_HUD + r'\meters\plasma_meter_r',
             'shader': r'ui\hud\shaders\plasma_meter',
             'fields': [('input 1', 49, ('anchor', -24)), ('[Y] unit flags', 48), ('[N] unit flags', 1024),
                        ('[N] weapon flags', 6), ('fullscreen offset', [-189, 60]),
                        ('halfscreen offset', [-95, 30]), ('quarterscreen offset', [-95, 30]), ('anchor', 0)]},
            {'name': '2x', 'bitmap': NEW_HUD + r'\meters\plasma_bkd_r',
             'shader': r'ui\hud\shaders\widget_gradient_flash_pulse',
             'fields': [('input 1', 55, ('anchor', -24)), ('[Y] unit flags', 48), ('[N] unit flags', 1024),
                        ('[N] weapon flags', 6), ('fullscreen offset', [-190, 60]),
                        ('halfscreen offset', [-95, 30]), ('quarterscreen offset', [-95, 30]), ('anchor', 0)]},
        ],
    },

    # step 8 -- the pickup icon at U+E153 (Halo 2's look, the AR's: HUD blue, outline + feature lines,
    # solid body), the messages smg_* -> ft2_*
    'glyph': {
        'box': (160, 62),          # Bungie's size at E153 (halo2.dll draws the E000-E3FF band x0.72)
        'model_3p': WORLD_JMS,
        'tif': 'flamethrower_h2_glyph.tif',
        # UNTINTED (user, 2026-10-22, the H2 icon rule): halo2.dll forces the band white; white
        # lines over a grey body, as the SAW's first icon / the AR / the Spiker
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'smg', 'donor_icon': '&smg',
        'donor_name': 'SMG', 'port_name': 'Flamethrower',
        # boot 1: 'Picked up an Flamethrower' (the SMG's article) -> the article with the name
        'names': [('an SMG', 'a Flamethrower'), ('SMG', 'Flamethrower')],
        # boot 1 (user: 'show me both icons'): Halo 2 SHIPS a flamethrower icon, U+E117 (macro
        # &flamethrower, all eight English fonts, in the band Halo 2 tints) -- the remnant of the cut
        # weapon. Boots 2-5 drew it on the PICKUP line for a comparison; 2026-10-22 (the H2 icon rule):
        # both lines draw the port's own E153 (Bungie's E117 stays an option for the user)
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
        # boot 3 (user: 'the overheat sound exists, but is too quiet'): +6 dB. Boot 4 ('still quiet'):
        # measured, Halo 1's burnout samples sit ~15 dB under the fire loop (RMS 0.045 vs 0.27 after
        # +3) -> +16 in the samples (saw_port_sounds.boosted: tanh-limited, peaks under 0.95)
        'gain': {'ft_flyby': -40.0, 'ft_overheat': 0.0},     # Halo 2's gain base tops out at 0 dB
        'boost': {'ft_overheat': 16.0},
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
        # boot 2 ('no sound' on the overheat): the import flags changed animations 'verify sound
        # events' -- cleared, as Bungie's graphs ship (h2_port_fp_anims.clear_verify)
        'clear_verify': True,
        # (Halo 1, Halo 2[, opt]). Halo 2's overheat = ONE animation `overheating` (the PR's 89 frames)
        # + `o_h_exit`: Halo 1's overheating (enter, 10) then its overheated loop to ~the overheat's
        # length ((1 - 0.3) / 0.44 = 1.6 s = 48 frames, the boot-1 heat). No reload-full / put-away / 2nd melee in
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
                 {'then': 'first-person overheated', 'frames': 48}),
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
            'attachments/#count': "the PR bolt's 2 slots: the flame effect + an empty effect (boot 4)",
            'impact / detonation noise': "the PR bolt's (Halo 1's 'loud' is an AI-perception enum)",
            'timer, radii, maximum range, air damage range': 'Halo 1 raw (a 0 on the PR: no ratio), step 4',
            'damage modifiers/*': "no Halo 2 field: the damage TABLE (group `burning`) carries the material response",
            'functions (the PR\'s `heat` export)': "the SMG clone has none: the heat display's gauge may sit still "
                                                  "(checked in game)",
            'firing effects/[1], old message index, on-ground scale, predicted bitmaps': "the SMG's (clone donor)",
        },
    },

    # make_port_catalog_h2.py flamethrower: the Plasma Rifle table's rows (balance_port.py Flamethrower
    # "Halo 1" "Halo 2" --hop "Plasma Rifle:Halo 1>Halo 2") onto the port's own weapon / flame / damage;
    # melee rows dropped (strike_melee is every weapon's); the air damage range kept at Halo 1's no-
    # falloff 100 (the PR's 20-50 -> 0-40 ratio would add a falloff Halo 1's flame never had)
    'catalog': {
        'table': 'balance_Flamethrower_Halo1_to_Halo2.json',
        'weapon_tag': FT + r'\flamethrower',
        'port_tags': [(('weap', r'objects\weapons\rifle\plasma_rifle\plasma_rifle'), FT + r'\flamethrower'),
                      (('proj', r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt'),
                       FT + r'\projectiles\flame'),
                      (('jpt!', r'objects\weapons\rifle\plasma_rifle\damage_effects\plasma_rifle_bolt'),
                       FT + r'\damage_effects\flame')],
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        'value_overrides': {'Air Damage Range': 100.0, 'Air Damage Range Max': 100.0,
                            'Water Damage Range': 100.0, 'Water Damage Range Max': 100.0},
        'fp_animations': r'objects\characters\*\fp\weapons\support_low\fp_flamethrower\fp_flamethrower',
        'reload_mult': None,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds and its own '
                 'Halo 1 first-person animations (the Arbiter\'s re-posed), balanced through the Plasma Rifle.'),
    },

    'test': {'level': '05a_deltaapproach', 'dervish_level': '06b_floodzone', 'rounds': (100, 300)},
    'residency': {'levels': 'all', 'placements': False},
}

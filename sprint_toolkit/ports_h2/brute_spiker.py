r"""Spike Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

SR = r'objects\weapons\rifle\spike_rifle'        # the source's folder (H3EK) AND the port's (H2EK)
SMG = r'objects\weapons\rifle\smg'                # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\spike_rifle'  # the reserved effects folder
NEW_HUD = r'ui\hud\bitmaps\new_hud'
import os as _os
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~rifle~spike_rifle~spike_rifle.render_model.xml')
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'

PORT = {
    'order': 3,
    'wave': 'A3',
    'name': 'Spike Rifle',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
    'reservations': {
        'message_prefix': 'spk2',
        'glyph': 0xE140,
        'weapon_dir': 'objects\\weapons\\rifle\\spike_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\spike_rifle',
        'fp_graph': 'weapons\\rifle\\fp_spike_rifle\\fp_spike_rifle',
        'hud': 'ui\\hud\\brute_spiker',
        'hud_bitmap_prefix': 'brute_spiker_',
        'sound_dir': 'sound\\weapons\\brute_spiker_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine 1/1/1 AND dual-wieldable -- keep the flag'},
    'yardstick': {
        # step 4a, user 2026-10-21: the SMG; balance_Spike_Rifle_Halo3_to_Halo2.json
        # (balance_port.py "Spike Rifle" "Halo 3" "Halo 2" --hop "SMG:Halo 3>Halo 2");
        # TTK h2_spiker_ttk_4a.py h2_spiker_ttk_4a_variants.json
        'pick': 'SMG',
        'reason': ('user 2026-10-21: one hop, same role, both dual-wield; nearly every ratio x1: '
                   'balanced damage 8.55 (x0.95), rate 8, ammo 40 / 120 / 160, velocity 25 / 17.5, '
                   'spread 0 / 0.4-1.25, autoaim 6 / 12, magnetism 12 / 18, rider 0.75, dual wield '
                   'damage scale 0.667, dual error 0.25 / 0.75-1.5 (x1). Elite minor legendary TTK '
                   '2.12 s (default 2.00; H2 SMG 2.07, AR port 1.90, PR 4.76, BPR 4.60). '
                   'Alternatives: Plasma Rifle (spike 14 / 9.8, no ammo rows), Needler (no damage '
                   'row, magazine 63, contradictory rate ratios)'),
        # the user's picks beside the yardstick (2026-10-21):
        'melee': ('own clone of strike_melee x Halo 3 cut_melee 72 / strike_melee 70 '
                  '(20.57-61.71; the blades)'),
        'projectile': "Halo 3's own air gravity 0.2 (no SMG card row) AND minimum velocity 12 (user: "
                      "not the SMG rule's 0)",
        'candidates': {
            'provisional': 'SMG',
            'alternatives': ['Needler', 'Plasma Rifle'],
            'direct': 'none (H2 Brutes never carry a spiker)',
            'peers': ['SMG', 'Needler', 'Brute Plasma Rifle', 'Plasma Rifle'],
            'why': 'magazine 40 auto 8/s, slow arcing projectile, dual-wieldable like the SMG (both dual -> no x1.5 carry fudge); the Brute Plasma Rifle has NO H3 card, so cannot be the yardstick',
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': the Halo 3 render models on their OWN skeletons
    # (world: gun, barrel, bullet, magazine, slide, safety; FP: gun, ammo_drum, barrel_1,
    # barrel_2, clamp_left, clamp_right, slide) -- the Spiker's own FP animations drive them
    'geometry': {
        'kind': 'h3',
        'world_rm': SR + r'\spike_rifle.render_model',
        'fp_rm': SR + r'\fp_spike_rifle\fp_spike_rifle.render_model',
        'data_dir': SR,
        'world': 'spike_rifle', 'fp': 'fp_spike_rifle',
        # Halo 3's three shaders all sample `brute_bolter` (+ bump, + the illum mask): the body,
        # the dull grip, the shiny blades (Halo 1's A5). `shaders\invalid` = 20 FP triangles
        # Halo 3 never draws (the barrel end caps): dropped
        'materials': {'bolt_thrower': 'spike_rifle', 'bolt_thrower_dull': 'spike_rifle_dull',
                      'bolt_thrower_shiny': 'spike_rifle_shiny'},
        # the world .model is the BR's clone (the AR's shape: no world-model graph): its
        # variants name permutation `base`, region `gun`
        'world_permutation': 'base', 'world_region': 'gun',
        # no ejection port (spikes); Halo 3's muzzle_brake / fx_reload / weapon_stow_anchor unused
        'markers': {'primary_trigger': 'primary_trigger', 'left_hand': 'left_hand',
                    'flashlight': 'flashlight'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'render': ['spike_rifle', r'spike_rifle\fp_spike_rifle'],
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's
    # BRUTE weapons: the gravity hammer's `hammer` (tex_bump_env_illum: bump, detail, base, env,
    # a SEPARATE self_illum_map) for the lit body and blades, the Brute Shot's own (tex_bump_env,
    # metal_dirty) for the dull grip. Halo 3's illum map is a grey mask of 68 texels coloured per
    # shader (body blue 2f/31/d8 x6, dull + shiny amber ff/cd/57 x3, read by bloom): Halo 2 draws
    # its self_illum_map as it is, so the mask is TINTED here -- Halo 1's A5 colours (PALE for the
    # blue: Halo 3's x6 + bloom reads pale; AMBER), lines grown 2 px (no bloom)
    'textures': {
        'kind': 'h3',
        'rel': SR + r'\bitmaps',
        'shaders_dir': SR + r'\shaders',
        'bump_gain': 1.0,                      # the AR's (user: 1.6 read 'rough')
        'bitmaps': [(SR + r'\bitmaps\brute_bolter.bitmap', 'spike_rifle',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot', 'color', None),
                    (SR + r'\bitmaps\brute_bolter_bump.bitmap', 'spike_rifle_bump',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'bump_snorm', None),
                    (SR + r'\bitmaps\brute_bolter_illum.bitmap', 'spike_rifle_illum_blue',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (0.75, 0.78, 1.0), 2), None),
                    (SR + r'\bitmaps\brute_bolter_illum.bitmap', 'spike_rifle_illum_amber',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (1.0, 205 / 255.0, 87 / 255.0), 2), None)],
        'shaders': [
            ('spike_rifle', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': SR + r'\bitmaps\spike_rifle_illum_blue'}),
            ('spike_rifle_shiny', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': SR + r'\bitmaps\spike_rifle_illum_amber'}),
            ('spike_rifle_dull', r'objects\weapons\support_low\brute_shot\shaders\brute_shot',
             {r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump_active_camo': SR + r'\bitmaps\spike_rifle_bump'}),
        ],
        'report_rows': [(SR + r'\bitmaps\spike_rifle_bump', 'the port'),
                        (r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'Bungie Brute Shot')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon (the yardstick's own tag: spew, 1 magazine
    # / 1 trigger / 1 barrel, ammo HUD, DUAL-WIELDABLE -- kept), every tag a balance row or a look
    # may touch cloned; the world .model from the BATTLE RIFLE's (the AR's shape: no world-model
    # graph -- the SMG's names one for its own charging handle). NEW: the BLADE melee, an own clone
    # of strike_melee (user, step 4a) named by both of the weapon's strike_melee references
    'weapon': {
        'weapon': SR + r'\spike_rifle.weapon',
        'clones': [(SMG + r'\smg.weapon', SR + r'\spike_rifle.weapon'),
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', SR + r'\spike_rifle.model'),
                   (SMG + r'\projectiles\smg_bullet.projectile', SR + r'\projectiles\spike_rifle_spike.projectile'),
                   (SMG + r'\damage_effects\smg_bullet.damage_effect', SR + r'\damage_effects\spike_rifle_spike.damage_effect'),
                   (SMG + r'\damage_effects\smg_trigger.damage_effect', SR + r'\damage_effects\spike_rifle_trigger.damage_effect'),
                   (r'objects\weapons\damage_effects\strike_melee.damage_effect', SR + r'\damage_effects\spike_rifle_melee.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect', FX + r'\spike_rifle_fire.effect'),
                   (r'effects\objects\weapons\rifle\smg\smg_muzzle_flash.light', FX + r'\spike_rifle_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\smg.material_effects', FX + r'\spike_rifle_spike.material_effects')],
        'wiring': [
            (SR + r'\spike_rifle.weapon', 'hlmt', SMG + r'\smg', SR + r'\spike_rifle', 'world model'),
            (SR + r'\spike_rifle.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             SR + r'\spike_rifle', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             SR + r'\fp_spike_rifle\fp_spike_rifle', 'first person model, Master Chief', {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             SR + r'\fp_spike_rifle\fp_spike_rifle', 'first person model, Dervish (one Halo 3 FP model)',
             {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle',
             "Master Chief FP graph: the Spiker's own Halo 3 animations (single + dual)"),
            (SR + r'\spike_rifle.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\dervish\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle',
             "Dervish FP graph: the Spiker's own Halo 3 animations (single + dual)"),
            (SR + r'\spike_rifle.weapon', 'proj', SMG + r'\projectiles\smg_bullet',
             SR + r'\projectiles\spike_rifle_spike', 'projectile'),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'jpt!', SMG + r'\damage_effects\smg_bullet',
             SR + r'\damage_effects\spike_rifle_spike', 'impact damage'),
            (SR + r'\spike_rifle.weapon', 'jpt!', SMG + r'\damage_effects\smg_trigger',
             SR + r'\damage_effects\spike_rifle_trigger', 'firing damage'),
            # both strike_melee references (the weapon names it twice, each beside its response)
            (SR + r'\spike_rifle.weapon', 'jpt!', r'objects\weapons\damage_effects\strike_melee',
             SR + r'\damage_effects\spike_rifle_melee', 'the blade melee (own, x72/70)', {'every': True}),
            (SR + r'\spike_rifle.weapon', 'effe', r'effects\objects\weapons\rifle\smg\fire_bullet',
             FX + r'\spike_rifle_fire', 'firing effect'),
            (SR + r'\spike_rifle.weapon', 'ligh', r'effects\objects\weapons\rifle\smg\smg_muzzle_flash',
             FX + r'\spike_rifle_muzzle_flash', 'muzzle flash light'),
            (SR + r'\spike_rifle.weapon', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\spike_rifle_spike', 'material effects (the weapon)'),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\spike_rifle_spike', 'impact material effects'),
            # the HUD is the SMG's clone (step 7: dual-wield shaped -- plate x4, meter x2 -- kept)
            (SR + r'\spike_rifle.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\brute_spiker', 'its own HUD (step 7)'),
        ],
        # the 3P label: the SMG's own `rifle` / `smg`, kept (no rename). Halo 3's is `pistol` /
        # `spr`, which no Halo 2 graph has; `smg` is a type of the masterchief / elite `dual`
        # class (their dual-wield stance), of every rifle-class graph's (marine, flood combat,
        # masterchief), and `rifle` / `any` is the Brute's (rifle: pr, sg) and the taught Grunt's
        'shared': [(r'the particles inside spike_rifle_fire', "the SMG's (Halo 3 particles do not port)"),
                   (r'objects\weapons\damage_effects\strike_melee_response, smash_melee(_response)',
                    "the melee's responses + the second hit, shared by every Halo 2 weapon"),
                   (r'objects\weapons\rifle\smg\damage_effects\smg_empty', "the SMG's dry-fire damage (none)"),
                   (r'effects\objects\weapons\pistol\needler\ready, ...\battle_rifle\reload',
                    "Bungie's own SMG names them (ready / reloading effects)"),
                   (r'objects\powerups\smg_ammo\smg_ammo', "the SMG's ammo pickup item (unused in campaign)"),
                   (r'sound\weapons\impacts_riccs\bullet_flyby_short', "the projectile's fly-by"),
                   (r'effects\bitmaps\weapons_fire\*, smoke_warthog_gun', "the SMG's own weapon bitmaps")],
    },

    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '08a_deltacliffs', 'dervish_level': '04b_floodlab'},   # parallel pair 1
    'residency': {'levels': 'all', 'placements': False},
}

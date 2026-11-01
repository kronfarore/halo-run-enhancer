r"""Needle Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

NR = r'objects\weapons\rifle\needle_rifle'           # the source's folder (HREK) AND the port's (H2EK)
CC = r'objects\weapons\rifle\covenant_carbine'       # the donor (H2EK)
ND = r'objects\weapons\pistol\needler'               # the yardstick: its needle projectile + damage
DM = NR + r'\damage_effects'
PR = NR + r'\projectiles\needle_rifle_shard.projectile'
FX = r'effects\objects\weapons\rifle\needle_rifle'   # the reserved effects folder
NFX = r'effects\objects\weapons\pistol\needler'
XP = r'effects\impact\explosion_small\needler'
MAT = r'effects\materials\objects\weapons'
WP = NR + r'\needle_rifle.weapon'

PORT = {
    'order': 7,
    'wave': 'B2',
    'name': 'Needle Rifle',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
    'reservations': {
        'message_prefix': 'nr2',
        'glyph': 0xE144,
        'weapon_dir': 'objects\\weapons\\rifle\\needle_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\needle_rifle',
        'fp_graph': 'weapons\\rifle\\fp_needle_rifle\\fp_needle_rifle',
        'hud': 'ui\\hud\\needle_rifle',
        'hud_bitmap_prefix': 'needle_rifle_',
        'sound_dir': 'sound\\weapons\\needle_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine', 'message_prefix': 'cc',
              'why': 'Covenant semi-auto magazine, latch-zoom 2x, 1/1/2; projectile from the needler (supercombine)'},
    'yardstick': {
        # step 4a, user 2026-11-01: reports/h2_needle_rifle_4a.md; balance_Needle_Rifle_HaloReach_to_Halo2.json
        # (balance_port.py "Needle Rifle" "Needler" "Halo Reach" "Halo 2")
        'pick': 'Needler',
        'reason': ("user 2026-11-01: the Needler for every needle-shaped value; Reach has no Carbine and the chain "
                   "through Halo 3 breaks on the needle rows, so the Carbine (the role twin) answers ACCURACY only: "
                   "the Needler's cone means nothing on a homing shot. Balanced: needle 3 on impact (Halo 2's real "
                   "1 + 2; the tool's 2 reads the detonation alone), 4/s + recovery 0.25, 26 / 78 / 105, reload "
                   "Reach's 82 fr (the ratio's 119 is nearly double the Carbine), error 0.3-1.0 min 0, 2x, velocity "
                   "818, range 231 / air 40, autoaim 1.97 / 19.2, magnetism 2.81 / 19.2, count 3 (Reach's; the "
                   "ratio's 3.5 is no count), timer 1.5-2.1 s (stock x 6/2 shot gaps: the third needle must "
                   "land inside it), minimum velocity 3, attached 400 + area 50 (the Needler's), radius 0.2-0.5, "
                   "melee Halo 2's strike_melee. Legendary: 3 needles = any minor at 0.50 s; needles alone "
                   "Elite 67 / 21.4 s (Carbine 2.57 s)"),
        'supercombine': ("no dll patch: Halo 2's projectile carries `super det. projectile count` (needler 7) and its "
                         "own super detonation tags; the needler is the only stock user, so boot 1 proves a 3"),
        'candidates': {
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': 'none',
            'peers': ['Covenant Carbine', 'Needler', 'Battle Rifle'],
            'why': '21-round semi-auto 4/s, 2x zoom, supercombining needle (H1 pick). The Carbine is its H2 role twin but Reach has none and there is no bridge',
        },
    },
    # step 3 -- h2_port_weapon.py: the H2 COVENANT CARBINE's weapon (latch-zoom magazine, 2x, Covenant, 3P label
    # rifle / cb -- Reach's own weapon names `cb` too) with the NEEDLER's needle as the projectile: its
    # model, light volume, contrail, attach response, `has super combining explosion` and its own
    # super detonation tags. Halo 2's needle has a `detonation damage` (2) Reach's does not: own
    # zero-damage clone in both of its references (a reference cannot be emptied by h2_tagref)
    'weapon': {
        'weapon': WP,
        'clones': [(CC + r'\covenant_carbine.weapon', WP),
                   (CC + r'\covenant_carbine.model', NR + r'\needle_rifle.model'),
                   (ND + r'\projectiles\needler_shard\needler_shard.projectile', PR),
                   (ND + r'\damage_effects\needler_shard_impact.damage_effect', DM + r'\needle_rifle_shard_impact.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_detonation.damage_effect', DM + r'\needle_rifle_shard_detonation.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_super_detonation.damage_effect', DM + r'\needle_rifle_shard_super_detonation.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_attached_super_detonation.damage_effect', DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect'),
                   (CC + r'\damage_effects\carbine_trigger.damage_effect', DM + r'\needle_rifle_trigger.damage_effect'),
                   (NFX + r'\firing.effect', FX + r'\needle_rifle_fire.effect'),
                   (r'effects\objects\weapons\rifle\covenant_carbine\reloading.effect', FX + r'\needle_rifle_reloading.effect'),
                   (NFX + r'\projectile.contrail', FX + r'\needle_rifle_shard.contrail'),
                   (NFX + r'\needle.light_volume', FX + r'\needle_rifle_shard.light_volume'),
                   (XP + r'\standard_detonation.effect', FX + r'\standard_detonation.effect'),
                   (XP + r'\airborne_detonation.effect', FX + r'\airborne_detonation.effect'),
                   (XP + r'\super_detonation.effect', FX + r'\super_detonation.effect'),
                   (MAT + r'\covenant_carbine.material_effects', FX + r'\needle_rifle.material_effects'),
                   (MAT + r'\needler.material_effects', FX + r'\needle_rifle_shard.material_effects')],
        'wiring': [
            (WP, 'hlmt', CC + r'\covenant_carbine', NR + r'\needle_rifle', 'world model'),
            (WP, 'proj', CC + r'\projectiles\carbine_slug\carbine_slug', NR + r'\projectiles\needle_rifle_shard',
             'the needle (both barrels)', {'every': True}),
            (WP, 'jpt!', CC + r'\damage_effects\carbine_trigger', DM + r'\needle_rifle_trigger', 'firing damage'),
            (WP, 'effe', r'effects\objects\weapons\rifle\covenant_carbine\firing', FX + r'\needle_rifle_fire',
             "firing effect (both barrels; the needler's violet burst)", {'every': True}),
            (WP, 'effe', r'effects\objects\weapons\rifle\covenant_carbine\reloading', FX + r'\needle_rifle_reloading', 'reloading effect'),
            (WP, 'foot', MAT + r'\covenant_carbine', FX + r'\needle_rifle', 'material effects (the weapon)'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_impact', DM + r'\needle_rifle_shard_impact', 'impact damage'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_detonation', DM + r'\needle_rifle_shard_detonation',
             'detonation damage: zero, as Reach', {'nth': 0}),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_detonation', DM + r'\needle_rifle_shard_detonation',
             'attached detonation damage: zero, as Reach', {'nth': 0}),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_super_detonation', DM + r'\needle_rifle_shard_super_detonation', 'super detonation damage'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_attached_super_detonation', DM + r'\needle_rifle_shard_attached_super_detonation', 'super attached detonation damage'),
            (PR, 'effe', XP + r'\airborne_detonation', FX + r'\airborne_detonation', 'detonation effect (airborne)'),
            (PR, 'effe', XP + r'\standard_detonation', FX + r'\standard_detonation', 'detonation effect (ground)'),
            (PR, 'effe', XP + r'\super_detonation', FX + r'\super_detonation', 'super detonation'),
            (PR, 'foot', MAT + r'\needler', FX + r'\needle_rifle_shard', 'impact material effects (the needle)'),
            (PR, 'cont', NFX + r'\projectile', FX + r'\needle_rifle_shard', 'the trail'),
            (PR, 'MGS2', NFX + r'\needle', FX + r'\needle_rifle_shard', 'the light volume'),
        ],
        'shared': [(ND + r'\projectiles\needler_shard\needler_shard', "the needle's mesh, until the look step"),
                   (r'objects\weapons\damage_effects\strike_melee, smash_melee(_response)',
                    "Reach names strike_melee too: Halo 2's own, shared by every weapon")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (DEFAULT; the balanced rows are the catalog's, step
    # 4a's Needler table). h3_weapon_values.py --kit reach rifle\needle_rifle\needle_rifle
    'numbers': {
        'numbers': [
            # THE LIVE BARREL. The Carbine's trigger names barrel 1 for both primary and secondary (barrel 0 is
            # idle), and every card and catalog row addresses barrel 0: the trigger is pointed at barrel 0
            (WP, 'primary barrel', 'new triggers', 0, 0, 0),
            (WP, 'secondary barrel', 'new triggers', 0, 0, 0),
            # Reach's trigger is SPEW (hold = 4/s; its DMR is latch): Halo 1's record called it latch
            (WP, 'behavior', 'new triggers', 0, 0, 0),
            (WP, 'rounds per second', 'barrels', 0, 0, [4.0, 4.0]),
            (WP, 'shots per fire', 'barrels', 0, 0, [1, 1]),
            (WP, 'fire recovery time', 'barrels', 0, 0, 0.25),
            (WP, 'soft recovery fraction', 'barrels', 0, 0, 0.2),
            (WP, 'error angle', 'barrels', 0, 1, [0.15, 2.0]),
            # Reach blooms by a firing-penalty function, decay 0.9 s: Halo 1's ramp reading (its B2)
            (WP, 'acceleration time', 'barrels', 0, 1, 1.0),
            (WP, 'deceleration time', 'barrels', 0, 1, 0.9),
            (WP, 'illumination recovery time', 'barrels', 0, 0, 0.1),
            (WP, 'rounds loaded maximum', 'magazines', 0, 0, 21),
            (WP, 'rounds reloaded', 'magazines', 0, 0, 21),
            (WP, 'rounds total initial', 'magazines', 0, 0, 63),
            (WP, 'rounds total maximum', 'magazines', 0, 0, 105),
            (WP, 'autoaim angle', '', 0, 0, 2.25),
            (WP, 'autoaim range', '', 0, 0, 25.0),
            (WP, 'magnetism angle', '', 0, 1, 5.0),
            (WP, 'magnetism range', '', 0, 1, 25.0),
            (WP, 'deviation angle', '', 0, 0, 2.25, {'anchor': ('autoaim range', 12)}),
            (WP, 'active camo ding', '', 0, 0, 0.75),
            (WP, 'AI scariness', '', 0, 0, 5.0),
            # the needle: straight, fast, unguided
            (PR, 'initial velocity', '', 0, 0, 1500.0),
            (PR, 'final velocity', '', 0, 0, 1500.0),
            (PR, 'guided angular velocity (lower)', '', 0, 0, 0.0),
            (PR, 'guided angular velocity (upper)', '', 0, 0, 0.0),
            (PR, 'maximum range', '', 0, 0, 250.0),
            (PR, 'air damage range', '', 0, 0, [0.0, 40.0]),
            (PR, 'water gravity scale', '', 0, 0, 0.2, {'anchor': ('air damage range', 8)}),
            (PR, 'minimum velocity', '', 0, 0, 9.0),
            # Reach: 0-4 s + `detonation max time if attached`. Halo 2 has no such flag; only a stuck needle
            # rests, so one timer at Reach's maximum says the same
            (PR, 'timer', '', 0, 0, [4.0, 4.0]),
            (PR, 'super det. projectile count', '', 0, 0, 3),
            # THE RESPONSES BY NAME. A Halo 2 element holds two responses (Reach has a list): default_material
            # stays ATTACH (Reach's bipeds) + bounce 0-30 at chance 1, never against units
            (PR, 'chance fraction', 'material responses', 0, 0, 1.0),
            (PR, 'between', 'material responses', 0, 0, [0.0, 30.0]),
            (PR, 'angular noise', 'material responses', 0, 0, 2.0),
            (PR, 'perpendicular friction', 'material responses', 0, 0, 0.0),
            (PR, 'chance fraction', 'material responses', 3, 0, 0.5),      # energy_shield_thick
            (PR, 'chance fraction', 'material responses', 4, 0, 0.8),      # hard_metal_solid
            (PR, 'between', 'material responses', 4, 0, [0.0, 85.0]),
            # damage: 6 on impact, a headshot (flags: below, once H2's flag rows are read)
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'damage lower bound', '', 0, 0, 6.0),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'damage upper bound', '', 0, 0, [6.0, 6.0]),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.2),
            # flags 8194, the Carbine slug's: can cause headshots + ignore seat scale (Reach's needle has both)
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'flags', '', 0, 1, 8194, {'anchor': ('category', 2)}),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'damage lower bound', '', 0, 0, 0.0),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'damage upper bound', '', 0, 0, [0.0, 0.0]),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.0),
            # the area blast: 10-40 over 0.375-1.25 wu, core 0.3
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'radius', '', 0, 0, [0.375, 1.25]),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'AOE core radius', '', 0, 0, 0.3),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'damage lower bound', '', 0, 0, 10.0),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'damage upper bound', '', 0, 0, [40.0, 40.0]),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'instantaneous acceleration', '', 0, 0, 2.0),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'shake radius', '', 0, 0, 2.0),
            # the attached blast: 35-350
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'damage lower bound', '', 0, 0, 35.0),
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'damage upper bound', '', 0, 0, [350.0, 350.0]),
        ],
        'skipped': [
            ('reload time', "the magazine's reload time does not drive the player's reload: Reach's own animation does"),
            ('super det. time', "Reach's 0.05 s delay: no Halo 2 field, the blast is immediate"),
            ('super detonation object types', "Reach's biped only: no Halo 2 field, a vehicle combines as the stock needler does"),
        ],
    },

    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '05a_deltaapproach', 'dervish_level': '04b_floodlab'},
    'residency': {'levels': 'all', 'placements': False},
}

r"""Spartan Laser into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

SL = r'objects\weapons\support_high\spartan_laser'    # the source's folder (H3EK) AND the port's (H2EK)
BR = r'objects\weapons\rifle\beam_rifle'                # the donor (H2EK)
FX = r'effects\objects\weapons\support_high\spartan_laser'   # the reserved effects folder
BRFX = r'effects\objects\weapons\rifle\beam_rifle'
RL = r'objects\weapons\support_high\rocket_launcher'   # the yardstick; its shaders seed the look
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
import os as _os
NEW_HUD = r'ui\hud\bitmaps\new_hud'
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~support_high~spartan_laser~spartan_laser.render_model.xml')

PORT = {
    'order': 2,
    'wave': 'A2',
    'name': 'Spartan Laser',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
    'reservations': {
        'message_prefix': 'spl2',
        'glyph': 0xE13F,
        'weapon_dir': 'objects\\weapons\\support_high\\spartan_laser',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\spartan_laser',
        'fp_graph': 'weapons\\support_high\\fp_spartan_laser\\fp_spartan_laser',
        'hud': 'ui\\hud\\spartan_laser',
        'hud_bitmap_prefix': 'spartan_laser_',
        'sound_dir': 'sound\\weapons\\spartan_laser_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle', 'message_prefix': 'be',
              'why': 'battery + heat, instant beam, two-handed, 0 mags; trigger latch -> Charge 2.5 s, zoom levels 2 -> 1. Alt: plasma_pistol (pp: 2 barrels + charge, one-hand)'},
    'yardstick': {
        # step 4a (user, 2026-10-28): reports/h2_spartan_laser_4a.md. Halo 3's laser: spew-charge
        # 2.5 s, 5 beam rounds of detonation 20 + AOE spike bump 94 = 570 a shot, group laser (=
        # explosion_large, Hunter armour x0.5), battery 5, heat 1 a shot, vent 2.25 s, 2.5x, range
        # 120, autoaim 1 / 25, magnetism 5 / 25, smash melee. Rocket ratio legs: direct hit H2 350
        # (impact 150 + blast 200) / H3 440 (240 + bump 200: the A8 rule, bumps on both sides)
        'pick': 'Rocket Launcher',
        'reason': "user, step 4a 2026-10-28: Halo 1's pick and reason hold -- Halo 3's laser group IS "
                  "the rocket's explosion_large and Halo 2 has the group; every ratio leg is a real "
                  "value in both games (the Beam Rifle / Sniper ratios shrink the range 500 -> 120 to "
                  "29 wu and break the heat; the Sentinel Beam has no charge / zoom leg). Charge x1 "
                  "(the rocket tags agree: recovery 0.8, reload 5.0; not the 112/116 animation ratio). "
                  "Hunter armour: 'Default keeps the original number, Balanced uses the balanced "
                  "formula' -> x0.5 both (H3 laser 0.5 x H2 rocket 1 / H3 rocket 1; Halo 1's port is "
                  "the same formula: H1 rocket hunter_armor 1.0 -> 0.5, no change)",
        'balanced': {'damage': 453.4,          # 570 x 350 / 440
                     'charge_s': 2.5, 'vent_s': 2.25, 'battery_shots': 5, 'range': 120.0,
                     'zoom': 2.5, 'aim': (1.0, 45.0, 5.0, 25.0),   # autoaim range 25 x 45 / 25
                     'hunter_armor': 0.5, 'melee': 'smash_melee (shared, x1)',
                     'ready_frames': 28.6},    # 31 x H2 RL 24 / H3 RL 26
        'candidates': {
            'provisional': 'Rocket Launcher',
            'alternatives': ['Beam Rifle', 'Sniper Rifle', 'Sentinel Beam'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Beam Rifle', 'Sniper Rifle', 'Flak Cannon'],
            'why': "spew-charge 2.5 s, battery, heat 1.0/shot, 2.5x zoom, instant beam (H1 pick RL: laser damage = explosion_large). H2 has no spew-charge: Charge (the scarab main gun's, 2.8 s) is the closest -- UNTESTED on a player weapon",
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': Halo 3's render models on their OWN skeletons (world:
    # gun / body / foregrip / tubes / push_bar; FP: gun / cover / handle / laser / shield /
    # telescope / lens_1 / lens_2) -- the laser's own Halo 3 FP animations drive them (the AR's route)
    'geometry': {
        'kind': 'h3',
        'world_rm': SL + r'\spartan_laser.render_model',
        'fp_rm': SL + r'\fp_spartan_laser\fp_spartan_laser.render_model',
        'data_dir': SL,
        'world': 'spartan_laser', 'fp': 'fp_spartan_laser',
        # Halo 3 shader basename -> Halo 2 material (= the shader tag's name); decal2 renamed (Halo 1's
        # tool dropped a trailing digit of a material name, A8 -- not risked here)
        'materials': {'spartan_laser': 'spartan_laser', 'spartan_laser_dull': 'spartan_laser_dull',
                      'spartan_laser_shiny': 'spartan_laser_shiny',
                      'spartan_laser_luminous': 'spartan_laser_luminous',
                      'spartan_laser_decal': 'spartan_laser_decal',
                      'spartan_laser_decal2': 'spartan_laser_lattice'},
        # the world .model is the BR's clone (the AR's proof): its variants name `base` / `gun`
        'world_permutation': 'base', 'world_region': 'gun',
        # Halo 3's markers; the side vent = the beam rifle's `vent02` (its overheat sound attachment)
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'fx_side_vent': 'vent02', 'fx_vent': 'vent01',
                    'side_flare': 'side_flare'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['spartan_laser', r'spartan_laser\fp_spartan_laser'],
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps (base 768 + a signed-DXN bump, the AR's
    # 'bump_snorm'; two alpha decals; the luminous map is a 1x1 WHITE: the whole material lit), the
    # shaders reseeded from Bungie's Halo 2 ROCKET LAUNCHER (the human support weapon): the env-mapped
    # tubes for Halo 3's env-mapped spartan_laser / shiny, the plain body for dull, its decal shader for
    # both decals; the luminous strips on the shotgun's lit sight (tex_bump_illum) with the base map
    # tinted Halo 3's luminous blue (Halo 1's LUMINOUS_HOT) as its illum map
    'textures': {
        'kind': 'h3',
        'rel': SL + r'\bitmaps',
        'shaders_dir': SL + r'\shaders',
        'bump_gain': 1.0,
        # power-of-two sizes: `tool bitmaps` SKIPS a 768 x 768 / 96 x 128 source (Halo 1's A8 too); 512
        # = Bungie's rocket launcher, the AR's and the Spiker's (true colour: 1024 made a 6.8 MB tag)
        'bitmaps': [(SL + r'\bitmaps\spartan_laser.bitmap', 'spartan_laser', RL + r'\bitmaps\rocket_launcher', 'color',
                     (512, 512)),
                    (SL + r'\bitmaps\spartan_laser_bump.bitmap', 'spartan_laser_bump', RL + r'\bitmaps\rocket_launcher_bump',
                     'bump_snorm', (512, 512)),
                    (SL + r'\bitmaps\spartan_laser_decal.bitmap', 'spartan_laser_decal', RL + r'\bitmaps\rocket_launcher_decal',
                     'color', (128, 128)),
                    (SL + r'\bitmaps\spartan_laser_decal2.bitmap', 'spartan_laser_lattice', RL + r'\bitmaps\rocket_launcher_decal',
                     'color', None),
                    # BOOT 2 (user): 'the glow stripes are missing' -- the illum map was the DARK base map
                    # tinted (mean ~22/255): now Halo 3's own luminous map, its 1x1 WHITE (the whole
                    # luminous material lit, Halo 3's way), tinted Halo 3's pale blue-white
                    (SL + r'\bitmaps\spartan_laser_light.bitmap', 'spartan_laser_illum', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (0.85, 0.92, 1.0), 0), (64, 64))],
        'shaders': [
            ('spartan_laser', RL + r'\shaders\rocket_launcher_tubes',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump',
              RL + r'\bitmaps\rocket_launcher_bump_active_camo': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_shiny', RL + r'\shaders\rocket_launcher_tubes',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump',
              RL + r'\bitmaps\rocket_launcher_bump_active_camo': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_dull', RL + r'\shaders\rocket_launcher_body',
             {RL + r'\bitmaps\rocket_launcher': SL + r'\bitmaps\spartan_laser',
              RL + r'\bitmaps\rocket_launcher_bump': SL + r'\bitmaps\spartan_laser_bump'}),
            ('spartan_laser_decal', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': SL + r'\bitmaps\spartan_laser_decal'}),
            ('spartan_laser_lattice', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': SL + r'\bitmaps\spartan_laser_lattice'}),
            ('spartan_laser_luminous', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': SL + r'\bitmaps\spartan_laser_illum'}),
        ],
        'report_rows': [(SL + r'\bitmaps\spartan_laser_bump', 'the port'),
                        (RL + r'\bitmaps\rocket_launcher_bump', 'Bungie rocket launcher')],
    },

    # step 3 -- h2_port_weapon.py: the H2 BEAM RIFLE's weapon (battery + heat, 0 magazines, one
    # trigger / one barrel, instant beam, two-handed) with every tag a balance row or a look may
    # touch cloned; the beam visual = the beam rifle's two contrails (recoloured at the look step).
    # First pass (2026-10-28): the CHARGE PROOF -- the world / FP models, graphs and HUD are still the
    # beam rifle's; their own wiring joins with steps 1 / 7 / 9
    'weapon': {
        'weapon': SL + r'\spartan_laser.weapon',
        'clones': [(BR + r'\beam_rifle.weapon', SL + r'\spartan_laser.weapon'),
                   # the world .model: the BATTLE RIFLE's (the AR's proof: variants `base` / `gun`, human
                   # metal; the beam rifle's names Covenant materials)
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', SL + r'\spartan_laser.model'),
                   (BR + r'\projectiles\beam_rifle_beam.projectile', SL + r'\projectiles\spartan_laser_beam.projectile'),
                   (BR + r'\damage_effects\beam_rifle_impact.damage_effect', SL + r'\damage_effects\spartan_laser_beam.damage_effect'),
                   (r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger.damage_effect',
                    SL + r'\damage_effects\spartan_laser_trigger.damage_effect'),
                   (BR + r'\damage_effects\beam_rifle_trigger_misfire.damage_effect',
                    SL + r'\damage_effects\spartan_laser_misfire.damage_effect'),
                   (BRFX + r'\beam_rifle_fire.effect', FX + r'\spartan_laser_fire.effect'),
                   (BRFX + r'\beam_rifle_inner.contrail', FX + r'\spartan_laser_inner.contrail'),
                   (BRFX + r'\beam_rifle_outer.contrail', FX + r'\spartan_laser_outer.contrail'),
                   (BRFX + r'\overheated.effect', FX + r'\overheated.effect'),
                   (r'effects\materials\objects\weapons\beam_rifle.material_effects', FX + r'\spartan_laser.material_effects'),
                   # THE CHARGE CUE, the PLASMA PISTOL's way (boot 2, user: 'a tap plays the entire charging
                   # cue' and 'no charge-up light at the muzzle' -- boot 2 played Halo 3's charge sound as a
                   # one-shot part of the trigger's charging effect, the Scarab main gun's, whose particles
                   # never showed): attachments scaled by `primary_charged` -- its charging SOUND_LOOPING
                   # (start + loop, 'fade out at stop': a release stops it), its two overcharge LIGHTS (3P +
                   # FP) and its muzzle LENS FLARE, recoloured red
                   (r'sound\weapons\plasma_pistol\charging.sound_looping', FX + r'\sl_charging.sound_looping'),
                   (r'effects\generic_lights\overcharge.light', FX + r'\sl_charge.light'),
                   (r'effects\generic_lights\overcharge_fp.light', FX + r'\sl_charge_fp.light'),
                   (r'effects\lens_flares\plasma_pistol.lens_flare', FX + r'\sl_charge.lens_flare'),
                   # step 7: the beam rifle's HUD (battery text, heat meter, zoomed meters, scope widgets)
                   (r'ui\hud\beam_rifle.new_hud_definition', r'ui\hud\spartan_laser.new_hud_definition')],
        'wiring': [
            (SL + r'\spartan_laser.weapon', 'hlmt', BR + r'\beam_rifle', SL + r'\spartan_laser', 'world model'),
            (SL + r'\spartan_laser.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             SL + r'\spartan_laser', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (SL + r'\spartan_laser.weapon', 'mode', BR + r'\fp_beam_rifle\fp_beam_rifle',
             SL + r'\fp_spartan_laser\fp_spartan_laser', 'first person model, Master Chief', {'nth': 0}),
            (SL + r'\spartan_laser.weapon', 'mode', BR + r'\fp_beam_rifle\fp_beam_rifle',
             SL + r'\fp_spartan_laser\fp_spartan_laser', 'first person model, Dervish (one Halo 3 FP model)', {'nth': 0}),
            (SL + r'\spartan_laser.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle',
             r'objects\characters\masterchief\fp\weapons\support_high\fp_spartan_laser\fp_spartan_laser',
             "Master Chief FP graph: the laser's own Halo 3 animations"),
            (SL + r'\spartan_laser.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle',
             r'objects\characters\dervish\fp\weapons\support_high\fp_spartan_laser\fp_spartan_laser',
             "Dervish FP graph: the laser's own Halo 3 animations"),
            (SL + r'\spartan_laser.weapon', 'proj', BR + r'\projectiles\beam_rifle_beam',
             SL + r'\projectiles\spartan_laser_beam', 'projectile'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'jpt!', BR + r'\damage_effects\beam_rifle_impact',
             SL + r'\damage_effects\spartan_laser_beam', 'impact damage (the whole shot: overpenetration takes the impact only)'),
            (SL + r'\spartan_laser.weapon', 'jpt!', r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_trigger',
             SL + r'\damage_effects\spartan_laser_trigger', 'firing damage (kick)'),
            (SL + r'\spartan_laser.weapon', 'jpt!', BR + r'\damage_effects\beam_rifle_trigger_misfire',
             SL + r'\damage_effects\spartan_laser_misfire', 'misfire damage'),
            (SL + r'\spartan_laser.weapon', 'effe', BRFX + r'\beam_rifle_fire', FX + r'\spartan_laser_fire', 'firing effect'),
            (SL + r'\spartan_laser.weapon', 'effe', BRFX + r'\overheated', FX + r'\overheated', 'overheated (vent) effect'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'cont', BRFX + r'\beam_rifle_inner',
             FX + r'\spartan_laser_inner', 'the beam: inner contrail'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'cont', BRFX + r'\beam_rifle_outer',
             FX + r'\spartan_laser_outer', 'the beam: outer contrail'),
            (SL + r'\spartan_laser.weapon', 'foot', r'effects\materials\objects\weapons\beam_rifle',
             FX + r'\spartan_laser', 'material effects (the weapon)'),
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'foot', r'effects\materials\objects\weapons\beam_rifle',
             FX + r'\spartan_laser', 'impact material effects'),
            (SL + r'\spartan_laser.weapon', 'nhdt', r'ui\hud\beam_rifle', r'ui\hud\spartan_laser', 'its own HUD (step 7)'),
            # (boot 2's trigger `charging effect` -- the Scarab's, filled at `behavior` +42 with
            # record_from -- is gone: a one-shot effect plays whole however short the press)
            # the charge loop's tracks: Halo 3's charging in + loop (step 10); its remastered twin -> itself
            (FX + r'\sl_charging.sound_looping', 'snd!', r'sound\weapons\plasma_pistol\startcharge',
             r'sound\weapons\spartan_laser_port\sl_charge', "the charge loop's start: Halo 3's charging in"),
            (FX + r'\sl_charging.sound_looping', 'snd!', r'sound\weapons\plasma_pistol\charge',
             r'sound\weapons\spartan_laser_port\sl_charge_loop', "the charge loop: Halo 3's charging loop"),
            (FX + r'\sl_charging.sound_looping', 'lsnd', r'sound_remastered\weapons\plasma_pistol\charging',
             FX + r'\sl_charging', "its remastered twin: itself (no plasma pistol sound left)"),
        ],
        # (tag, class, path, marker, like class, scale function): the plasma pistol's charge cue
        'append_attachments': [
            (SL + r'\spartan_laser.weapon', 'lsnd', FX + r'\sl_charging', 'primary_trigger', 'lsnd', 'primary_charged'),
            (SL + r'\spartan_laser.weapon', 'ligh', FX + r'\sl_charge', 'primary_trigger', 'lsnd', 'primary_charged'),
            (SL + r'\spartan_laser.weapon', 'ligh', FX + r'\sl_charge_fp', 'primary_trigger', 'lsnd', 'primary_charged'),
            (SL + r'\spartan_laser.weapon', 'lens', FX + r'\sl_charge', 'primary_trigger', 'lsnd', 'primary_charged'),
        ],
        # the 3P label: the ROCKET LAUNCHER's (`missile` / `rl`, Halo 1's A8: `sl` taught from `rl`) -- a
        # heavy two-handed carry every Halo 2 character graph holds (Grunts included); the beam rifle's
        # `rifle` / `csr` is the Covenant sniper's
        'string_ids': {'rifle': 'missile', 'csr': 'rl'},
        'string_ids_done': ('weapon name', 'rl'),
        # THE DAMAGE GROUPS (step 4a: Halo 3's `laser` = the rocket's explosion_large): the beam rifle's
        # plasma_fast / sniper (Hunters IMMUNE, Elite shields x2) -> explosion_large / `all` (x1 on every
        # armour). Halo 3's Hunter armour x0.5 has NO Halo 2 group (none pairs Hunter 0.5 with
        # explosion_large's other rows) -- OPEN with the user: a new group in globals, or Hunter x1
        'string_id_renames': [(SL + r'\damage_effects\spartan_laser_beam.damage_effect',
                               {'plasma_fast': 'explosion_large', 'sniper': 'all'})],
        'shared': [(r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'the particles inside spartan_laser_fire', "the beam rifle's (Halo 3 particles do not port)")],
    },

    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (DEFAULT; the rocket ratio = the catalog's
    # balance rows). THE CHARGE: Halo 3's spew-charge has no Halo 2 twin; the shape is the SCARAB
    # MAIN GUN's (Halo 2's only `charge` trigger, AI-driven): behavior charge, primary barrel -1 (an
    # early release fires NOTHING -- Halo 3's tap fires its harmless tracer), secondary barrel 0, both
    # actions `charge`, overcharged action DISCHARGE (fires barrel 0 when full), charged illumination 1.
    # Halo 3's 5 beam rounds a burst = ONE projectile carrying 570 (Halo 1's A8: an overpenetrated unit
    # takes the impact only)
    # BOOT 1 (03b, 2026-10-28, still in the beam rifle's look; user): 'Works' -- charges, fires by itself
    # when full, an early release fires nothing, 5-shot battery: HALO 2's CHARGE TRIGGER WORKS ON A PLAYER
    # WEAPON (an observation of one port). 'The charge time might be higher than 2.5' -- measure charge
    # and vent later
    'numbers': {
        'numbers': [
            (SL + r'\spartan_laser.weapon', 'behavior', 'new triggers', 0, 0, 3),          # latch -> charge
            # block indices (h2_tagfield read_all(indices=True), A2): the secondary (-1, findable by
            # value) first; the primary (0 = padding-like) pinned 2 bytes before it
            (SL + r'\spartan_laser.weapon', 'secondary barrel', 'new triggers', 0, 0, 0,
             {'anchor': ('behavior', 4)}),      # once 0 (a re-run), placed after behavior + primary
            (SL + r'\spartan_laser.weapon', 'primary barrel', 'new triggers', 0, 0, -1,
             {'anchor': ('secondary barrel', -2)}),
            # the zero fields placed from the secondary barrel (the trigger element, read off the
            # plasma pistol's non-zero ones: prediction +2, 2 pad, autofire time +6 / throw +10,
            # secondary action +14, primary +16, charging time +18, charged time +22, overcharged
            # action +26, 2 pad, charged illumination +30), each proved by pin()'s probe
            (SL + r'\spartan_laser.weapon', 'secondary action', 'new triggers', 0, 0, 1,     # fire -> charge
             {'anchor': ('secondary barrel', 14)}),
            (SL + r'\spartan_laser.weapon', 'primary action', 'new triggers', 0, 0, 1,
             {'anchor': ('secondary barrel', 16)}),
            (SL + r'\spartan_laser.weapon', 'charging time', 'new triggers', 0, 0, 2.5,
             {'anchor': ('secondary barrel', 18)}),
            (SL + r'\spartan_laser.weapon', 'overcharged action', 'new triggers', 0, 0, 2,   # none -> discharge
             {'anchor': ('secondary barrel', 26)}),
            (SL + r'\spartan_laser.weapon', 'charged illumination', 'new triggers', 0, 0, 1.0,
             {'anchor': ('secondary barrel', 30)}),
            # heat 1 a shot (every shot overheats), vent (1 - 0.1) / 0.4 = 2.25 s; Halo 3's normal loss 1
            (SL + r'\spartan_laser.weapon', 'heat generated per round', 'barrels', 0, 0, 1.0),
            (SL + r'\spartan_laser.weapon', 'overheated heat loss per second', '', 0, 0, 0.4),
            (SL + r'\spartan_laser.weapon', 'heat loss per second', '', 0, 0, 1.0),
            # battery: 5 shots (Halo 3 age 0.04 a round x 5 rounds) -- a hair under 0.2 (boot 2:
            # 0.2 x 3 = 0.6000000238 showed 39 %; the misfire rows below stop the 6th shot)
            (SL + r'\spartan_laser.weapon', 'age generated per round', 'barrels', 0, 0, 0.1999995),   # 5e-7 off: h2_tagfield's 'already' tolerance
            # Halo 3's aim assist (the beam rifle's 1 / 10, 4 / 14) and ONE zoom level at 2.5x (its 2:
            # 3.5-9.5); the scope widgets stay
            (SL + r'\spartan_laser.weapon', 'autoaim angle', '', 0, 0, 1.0),
            (SL + r'\spartan_laser.weapon', 'autoaim range', '', 0, 0, 25.0),
            (SL + r'\spartan_laser.weapon', 'magnetism angle', '', 0, 1, 5.0),
            (SL + r'\spartan_laser.weapon', 'magnetism range', '', 0, 1, 25.0),
            (SL + r'\spartan_laser.weapon', 'magnification levels', '', 0, 0, 1),
            (SL + r'\spartan_laser.weapon', 'magnification range', '', 0, 0, [2.5, 2.5]),
            # step 4b (port_field_audit --port h2:spartan_laser, 2026-10-28, out/sl_4b_1.txt) -- list 2 / 4:
            # Halo 3's laser is exact (error 0; the beam rifle's 0.5 unzoomed cone + 'use error when
            # unzoomed' made it miss from the hip), its bounding radius by the ratio, camo ding, AI
            # scariness / acceleration scale / illumination recovery = the source pair's agreed value,
            # the FP offset by the ratio (0, 0, -0.005), the beam's collision radius by the ratio
            (SL + r'\spartan_laser.weapon', 'error angle', 'barrels', 0, 1, [0.0, 0.0]),
            (SL + r'\spartan_laser.weapon', 'bounding radius', '', 0, 0, 0.24725),
            (SL + r'\spartan_laser.weapon', 'active camo ding', '', 0, 0, 0.12),
            (SL + r'\spartan_laser.weapon', 'ai scariness', '', 0, 0, 12.0),
            (SL + r'\spartan_laser.weapon', 'acceleration scale', '', 0, 0, 0.8),
            (SL + r'\spartan_laser.weapon', 'illumination recovery time', 'barrels', 0, 0, 0.2),
            # BOOT 2 (user, 2026-10-29): 'move 0.5 units to the right, 1 unit down' (1 unit = 0.01 wu,
            # y = left): (0, 0, -0.005) -> (0, -0.005, -0.015)
            (SL + r'\spartan_laser.weapon', 'first person weapon offset', '', 0, 0, [0.0, -0.005, -0.015]),
            # (the beam's collision radius: 4b's 0.15 reverted to 0 after boot 2 -- the row below)
            # BOOT 2: 'the laser doesn't fire from the muzzle' -- the beam rifle's barrel first-person
            # offset is 0 (the camera). Halo 1's A8 measured the laser's FP muzzle at (0.215, -0.053,
            # -0.007) of the view; + boot 2's move -> (0.215, -0.058, -0.022) (Halo 3's own 0, -0.05, 0
            # leans on its 1p beam system, which Halo 2 lacks)
            (SL + r'\spartan_laser.weapon', 'first person offset', 'barrels', 0, 0, [0.215, -0.058, -0.022],
             {'anchor': ('fire recovery time', 92)}),   # the rocket's 0, -0.1, 0 sits at fire recovery +92
            # BOOT 2: 'battery 39 after 3 shots' (Halo 1's A8 again): 0.2 x 3 in float32 = 0.6000000238
            # -> 39 %. The float just under 0.2 shows 80 / 60 / 40 / 20 but leaves 0.99999994 after five
            # and a 6th would fire -> Halo 1's fix: AGE MISFIRE from 0.9999, chance 1
            # (the age row above is 0.1999995: x5 = 0.9999975). Placed from `ai scariness` (12): (read off the plasma pistol's
            # 0.9 / 0.5): misfire start +52, chance +56
            (SL + r'\spartan_laser.weapon', 'age misfire start', '', 0, 0, 0.9999,
             {'anchor': ('ai scariness', 52)}),
            (SL + r'\spartan_laser.weapon', 'age misfire chance', '', 0, 0, 1.0,
             {'anchor': ('ai scariness', 56)}),
            # BOOT 2 (user): 'on the zoom HUD the right bar should show the remaining charge and the left
            # the heat -- flip those': the beam rifle's zoomed meters swapped by input (widget 8 heat ->
            # battery fraction, widget 10 battery fraction -> heat; their art and places stay)
            (r'ui\hud\spartan_laser.new_hud_definition', 'input 1', 'bitmap widgets', 8, 0, 56),
            (r'ui\hud\spartan_laser.new_hud_definition', 'input 1', 'bitmap widgets', 10, 0, 49),
            # ...and both bar groups 301 units IN (the beam rifle's sit at +-357..457 from the crosshair,
            # ~400 px at 1080p; Halo 3's hug it at ~75-140 px): right 7 / 8 / 9, left 10 / 11 / 12, their
            # halfscreen twins by the same share (/ 4.04)
            ] + [(r'ui\hud\spartan_laser.new_hud_definition', f, 'bitmap widgets', i, 0, v) for i, f, v in (
                (7, 'fullscreen offset', [67, -114]), (8, 'fullscreen offset', [67, -114]),
                (9, 'fullscreen offset', [56, -120]), (10, 'fullscreen offset', [-152, -114]),
                (11, 'fullscreen offset', [-156, -120]), (12, 'fullscreen offset', [-151, -114]),
                (7, 'halfscreen offset', [17, -28]), (8, 'halfscreen offset', [17, -28]),
                (9, 'halfscreen offset', [13, -30]), (10, 'halfscreen offset', [-38, -28]),
                (11, 'halfscreen offset', [-39, -30]), (12, 'halfscreen offset', [-38, -28]))] + [
            # the charge cue recoloured from the plasma pistol's green to Halo 3's laser red (A8: 1, 0.15, 0.1);
            # the flare a little bigger than the pistol's (a support weapon's muzzle)
            (FX + r'\sl_charge.light', 'specular upper bound', '', 0, 0, [1.0, 0.15, 0.1]),
            (FX + r'\sl_charge.light', 'diffuse upper bound', '', 0, 0, [1.0, 0.15, 0.1]),
            (FX + r'\sl_charge_fp.light', 'diffuse upper bound', '', 0, 0, [1.0, 0.15, 0.1]),
            (FX + r'\sl_charge.lens_flare', 'color', 'reflections', 0, 0, [1.0, 0.2, 0.15]),
            (FX + r'\sl_charge.lens_flare', 'radius', 'reflections', 0, 0, [0.08, 0.1]),
            # BOOT 2 (user): 'the muzzle effect is not correct' -- it is the beam rifle's: flares, ring and
            # soft burst at the muzzle (kept: Halo 3's first-person flash is a bright flash + flare there),
            # plus ELECTRIC ARCS and a purple ENERGY BOLT TRAIL (event 0's systems 3 / 6) and steam at
            # vent03-05, markers the laser has none of (events 4-6) -> third person only (camera mode 2;
            # Halo 2 has no 'never'); the steam at vent01 / 02 stays (Halo 3: steam at the side vent)
            (FX + r'\spartan_laser_fire.effect', 'camera mode', 'particle systems', 3, 0, 2),
            # (system 6's zero camera mode placed from its own `coordinate system` (1) +6. Events 4-6's
            # steam -- 'particle systems[0]' of the 5th-7th event -- cannot be placed: h2_tagfield scopes
            # a search to a block's FIRST occurrence. They name vent03-05, which the laser lacks: left)
            (FX + r'\spartan_laser_fire.effect', 'camera mode', 'particle systems', 6, 0, 2,
             {'anchor': ('coordinate system', 6)}),
            # BOOT 2: 'no impact effect visible' -- 4b had given the INSTANT beam Halo 3's collision
            # radius 0.15 (by the ratio); Bungie's instant beams (beam rifle, sniper) all use 0: back to 0
            (SL + r'\projectiles\spartan_laser_beam.projectile', 'collision radius', '', 0, 0, 0.0,
             {'anchor': ('maximum range', -24)}),   # collision, arming, danger, timer x2, min velocity
            # THE BEAM (look, first pass): the beam rifle's two contrails (inner core, outer glow, both
            # additive) recoloured from its purple to Halo 3's laser red (Halo 1's A8: RED 1, 0.15, 0.1;
            # a white-hot core), the outer glow wider (Halo 3's beam is thick)
            (FX + r'\spartan_laser_inner.contrail', 'color lower bound', 'point states', 0, 0, [1.0, 1.0, 0.8, 0.7]),
            (FX + r'\spartan_laser_inner.contrail', 'color upper bound', 'point states', 0, 0, [1.0, 1.0, 0.3, 0.2]),
            (FX + r'\spartan_laser_outer.contrail', 'color lower bound', 'point states', 0, 0, [0.6, 1.0, 0.1, 0.05]),
            (FX + r'\spartan_laser_outer.contrail', 'color upper bound', 'point states', 0, 0, [0.6, 1.0, 0.2, 0.1]),
            (FX + r'\spartan_laser_outer.contrail', 'width', 'point states', 0, 0, 0.25),
            (SL + r'\damage_effects\spartan_laser_beam.damage_effect', 'damage lower bound', '', 0, 0, 570.0),
            (SL + r'\damage_effects\spartan_laser_beam.damage_effect', 'damage upper bound', '', 0, 0, [570.0, 570.0]),
        ],
        'skipped': [],
    },

    # step 7 -- the HUD: a clone of the BEAM RIFLE's (the donor's: the battery percentage text, the heat
    # meter, the zoomed battery + heat meters and the scope widgets -- Halo 3's laser HUD is a battery
    # readout + a charge cue, no ammo ticks), its plate painted from the laser's mesh, Halo 3's crosshair
    # (chud hud_reticles #11, H1 A8's) at Halo 3's on-screen size (~170 px at 1080p, A8's measurement /
    # 1.117 screen px a bitmap px, the AR's) -- the scope widgets STAY (one zoom level, 2.5x)
    # no ammo meter (a battery): h2_port_meter `backpack_only` draws just the stowed icon
    'meter': {
        'backpack_only': True,
        'port_hud': r'ui\hud\spartan_laser',
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\spartan_laser_backpack',
        'backpack_size': (62, 30),
        'model_3p': H3_RM_XML,
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\beam_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\sniper_rifle_bkd',
        'name': 'spartan_laser_bkd',
        'hud': r'ui\hud\spartan_laser',
        'model_3p': H3_RM_XML,
        # the beam rifle plate: 12 images -- 0-3 the bright plates (206x64 x2 with the battery row,
        # 206x38 x2), 4-7 the ZOOM ARCS (100x120 ...: no symbol, kept as Bungie's), 8-11 their dim twins.
        # The symbol box measured on image 0 (the sniper 'other' is another shape: no diff)
        # boot 2 (user, screenshot 3: 'a little messed up compared to original icons'): rows 3-5 of the box
        # held the plate's own border pixels (blue 156), read as the symbol's top colour -> a flat dark
        # blue drawing over the whole box. Bungie's symbol spans rows 11-31 (green 196 -> 9 over blue ~225)
        'fallback_box': (86, 198, 9, 33),
        'stretch': 1.4,
        'all_images': {'dim': {8: 0, 9: 1, 10: 2, 11: 3}, 'skip': [4, 5, 6, 7]},
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 19,                # the beam rifle's (the cloned HUD's crosshair)
        'name': 'spartan_laser_reticle',
        'hud': r'ui\hud\spartan_laser',
        'footprint': 1.0,
        # BOOT 2 (user's Halo 3 screenshot: 'crosshair needs work'): Halo 3 draws TWO crosshair widgets
        # -- #11 at scale 0.59 and the inner double ring `spartan_outerring` at 0.95 (Halo 1's A8) --
        # boot 2 had #11 alone
        'h3_art': {'sheet': 'hud_reticles', 'sequence': 11, 'yardstick': 11, 'target_ink': 98,   # the user's Halo 3 screenshot: the ring ~110 px at 1080p / 1.117
                   'layers': [(r'ui\chud\bitmaps\spartan_outerring.bitmap', 0.95 / 0.59)]},
        'preview': 'spartan_laser_reticle_preview.png',
    },
    # step 7, ZOOMED (boot 2, user: 'crosshair needs work, normal and zoomed', Halo 3's zoomed screenshot:
    # a translucent dark DISC ~300 px across round the crosshair, the heat / charge bars hugging it, the
    # world clear outside). The beam rifle's mask widget (registered at its corner, mirrored both ways)
    # draws one quarter of a disc now (h2_port_scope `disc`): radius 150 HUD units (~170 px at 1080p,
    # the bars' outer edge), 35 % dark, a 3-unit rim at 60 %. The bars: see `numbers` (offsets)
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\beam_rifle_scope_mask',
        'name': 'spartan_laser_scope_mask',
        'hud': r'ui\hud\spartan_laser.new_hud_definition',
        'widgets': ('scope_mask',),
        'size': (160, 160),
        'disc': {'radius': 150, 'alpha': 0.35, 'rim': 0.6, 'rim_width': 3},
    },
    # step 8 -- the pickup icon at U+E13F (the H2 ICON RULE: untinted, white lines, grey body, 160x62)
    # and the messages (be_* -> spl2_*)
    'glyph': {
        'box': (160, 62),
        'model_3p': H3_RM_XML,
        'tif': 'spartan_laser_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'be', 'donor_icon': '&beam_rifle',
        'donor_name': 'Beam Rifle', 'port_name': 'Spartan Laser',
        'weapon': SL + r'\spartan_laser.weapon',
    },

    # step 10 -- h2_port_sounds.py: Halo 3's OWN sounds from MCC's halo3 sfx.fsb (render_h3_bank), classic
    # Opus. The Beam Rifle clone names: firing effect fire / fire_lod / lfe, the weapon's misfire, overheat
    # attachment, zoom in / out, pickup (the sniper's ammo), the beam's flyby; the seeded graphs the
    # beam rifle's first-person fire, melee x2, posing x2, ready. Halo 1's A8 source list
    'sounds': {
        'weapon': SL + r'\spartan_laser.weapon',
        'fire_fx': FX + r'\spartan_laser_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'spartan_laser'),
        'audio_key': 'Spartan Laser',
        'h3_bank': {'sl_fire': [H3SND + r'\spartan_laser\fire'],
                    'sl_fire_lod': [H3SND + r'\spartan_laser\spartan_laser_lod_far'],
                    'sl_overheat': [H3SND + r'\spartan_laser\spartan_laser_overheat'],
                    'sl_zoom_in': [H3SND + r'\spartan_laser\spartan_laser_zoom_in'],
                    'sl_zoom_out': [H3SND + r'\spartan_laser\spartan_laser_zoom_out'],
                    'sl_flyby': [H3SND + r'\spartan_laser\beam_flyby'],
                    'sl_ready': [H3SND + r'\spartan_laser\fp_spartan_laser\fp_spartan_laser_ready'],
                    'sl_melee': [H3SND + r'\spartan_laser\fp_spartan_laser\fp_spartan_laser_melee'],
                    'sl_pose1': [H3SND + r'\spartan_laser\fp_spartan_laser\fp_spartan_laser_posing_var1'],
                    'sl_pose2': [H3SND + r'\spartan_laser\fp_spartan_laser\fp_spartan_laser_posing_var2'],
                    'sl_ammo': [H3SND + r'\rocket_launcher\rocket_ammo'],
                    'sl_dryfire': [H3SND + r'\battle_rifle\dryfire'],
                    # the charge: Halo 3's charging sound_looping, `in` + `loop` -> the tracks of the laser's
                    # own charge loop (FX sl_charging, cloned from the plasma pistol's; 'fade out at stop')
                    'sl_charge': [H3SND + r'\spartan_laser\charging\charging\in'],
                    'sl_charge_loop': [H3SND + r'\spartan_laser\charging\charging\loop']},
        'sounds': {'sl_fire': ('sl_fire', 'weapon_fire'), 'sl_fire_lod': ('sl_fire_lod', 'weapon_fire'),
                   'sl_overheat': ('sl_overheat', 'weapon_overheat'),
                   'sl_zoom_in': ('sl_zoom_in', 'weapon_ready'), 'sl_zoom_out': ('sl_zoom_out', 'weapon_ready'),
                   'sl_flyby': ('sl_flyby', 'projectile_flyby'), 'sl_ready': ('sl_ready', 'weapon_ready'),
                   'sl_melee': ('sl_melee', 'weapon_melee'), 'sl_pose1': ('sl_pose1', 'weapon_ready'),
                   'sl_pose2': ('sl_pose2', 'weapon_ready'), 'sl_ammo': ('sl_ammo', 'weapon_reload'),
                   'sl_dryfire': ('sl_dryfire', 'weapon_empty'), 'sl_charge': ('sl_charge', 'weapon_fire'),
                   'sl_charge_loop': ('sl_charge_loop', 'weapon_fire')},
        'repoint_fx': [(r'sound\weapons\beam_rifle\beam_rifle_fire', 'sl_fire'),
                       (r'sound_remastered\weapons\beam_rifle\beam_rifle_fire_lod', 'sl_fire_lod'),
                       (r'sound_remastered\weapons\beam_rifle\beamrifle_lfe', 'sl_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\beam_rifle\beam_rifle_misfire', 'sl_dryfire'),
                           # (the beam rifle's overheat attachment is a LOOPING sound (lsnd) on the
                           # `overheated` function -- not a snd! slot; Halo 3 cues its one-shot overheat
                           # in the overheat animation: OPEN, a BORROW until then)
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_in', 'sl_zoom_in'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_out', 'sl_zoom_out'),
                           (r'sound\weapons\sniper_rifle\sniper_ammo', 'sl_ammo')],
        'repoint_tags': [(SL + r'\projectiles\spartan_laser_beam.projectile',
                          r'sound\weapons\beam_rifle\beam_rifle_flyby', 'sl_flyby')],
        'graph_sounds': (('beam_rifle_first_person_fire', 'sl_fire'), ('beam_rifle_melee_var1', 'sl_melee'),
                         ('beam_rifle_melee_var2', 'sl_melee'), ('beam_rifle_posing_var1', 'sl_pose1'),
                         ('beam_rifle_posing_var2', 'sl_pose2'), ('beam_rifle_ready', 'sl_ready')),
        'graph_sound_dir': r'sound\weapons\beam_rifle' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_spartan_laser_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_spartan_laser_graphs_before_sounds',
    },

    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull (the world .model's donor, as the
    # AR's) scaled per axis to the laser's render mesh
    'collision': {
        'donor': r'objects\weapons\rifle\battle_rifle\battle_rifle',
        'port': SL + r'\spartan_laser',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': SL + r'\collision\spartan_laser.jms',                     # under data
        'port_render_jms': SL + r'\render\spartan_laser.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 3.0,              # the laser is 2.9x the BR's width: the hull fits the mesh
        'nodes_from_render': True,      # the laser's own skeleton (the Spiker's case)
    },

    # step 9 -- h2_port_fp_anims.py: Halo 3's OWN FP animations, both species (the AR's route), the
    # graphs SEEDED from the Beam Rifle's (the donor: its overheating / o_h_exit / throw_overheated
    # events and sounds survive the import for the same names). Halo 3 -> Halo 2 names:
    #   fire_2 (the CHARGED shot, 28 fr) -> fire_1:var1 -- the beam is the trigger's barrel 0;
    #     Halo 3's fire_1 (the 2-frame TAP: its harmless tracer) has no Halo 2 shot -> dropped
    #   overheated (59 fr, Halo 3's one overheat) -> overheating (Halo 2's one, the S1 finding)
    #   idle:var1 -> idle (Halo 2 has one idle; var2 / var3 dropped -- the posing fidgets stay)
    #   the Dervish's `o_h:exit` (Halo 3's own typo) -> o_h_exit
    # Dropped: button_press / throw_equipment (Halo 3's equipment)
    'fp_anims': {
        'species': {
            'masterchief': {
                'graph': r'objects\characters\masterchief\fp\weapons\support_high\fp_spartan_laser\fp_spartan_laser.model_animation_graph',
                'arms_rm': r'objects\characters\masterchief\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\support_high\fp_spartan_laser',
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle'},
            'dervish': {
                'graph': r'objects\characters\dervish\fp\weapons\support_high\fp_spartan_laser\fp_spartan_laser.model_animation_graph',
                'arms_rm': r'objects\characters\dervish\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\support_high\fp_spartan_laser',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_beam_rifle\fp_beam_rifle'},
        },
        'weapon_dir': SL + r'\fp_spartan_laser',
        'weapon_rm': SL + r'\fp_spartan_laser\fp_spartan_laser.render_model',
        'weapon_nodes': ['gun', 'cover', 'handle', 'laser', 'shield', 'telescope', 'lens_1', 'lens_2'],
        'skip': ['first_person:fire_1', 'first_person:button_press', 'first_person:throw_equipment',
                 'first_person:idle:var2', 'first_person:idle:var3'],
        'rename': {'first_person:fire_2': 'first_person:fire_1:var1',
                   'first_person:overheated': 'first_person:overheating',
                   'first_person:idle:var1': 'first_person:idle',
                   'first_person:o_h:exit': 'first_person:o_h_exit'},
        'looping': ['first_person:idle:var1', 'first_person:posing:var1', 'first_person:posing:var2',
                    'first_person:posing:var3'],
        'overlay_reference': 'first_person:idle:var1',
        # the import flags changed animations 'verify sound events' (S1 boot 2: 'no sound') -- cleared
        'clear_verify': True,
        # BOOT 2 (user): 'after a grenade throw the Chief's wrist twists slightly into idle' -- the
        # throws' composed quaternions flip sign at frame 6 (left hand + fingers; Chief throw-grenade /
        # throw-overheated, Dervish throw-overheated): made sign-continuous
        'quat_continuity': True,
        # the import gives a name new to the seed 0.0001 (the SAW rework's finding): the three fidgets even
        'weights': {'first_person:posing:var1': 0.33, 'first_person:posing:var2': 0.33,
                    'first_person:posing:var3': 0.33},
    },

    # step 4b -- port_field_audit.py --port h2:spartan_laser: every field NO card covers where Halo 3's
    # laser differs from Halo 3's rocket launcher (the yardstick) -- list 2 must say 0 to port. The laser's
    # shot = its BEAM projectile (barrel 1 in Halo 3; Halo 3's damage is the beam's detonation)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (SL + r'\spartan_laser.weapon', RL + r'\rocket_launcher.weapon'),
                   'projectile': (SL + r'\projectiles\spartan_laser_beam.projectile', RL + r'\projectiles\rocket.projectile'),
                   'damage_effect': (SL + r'\damage_effects\spartan_laser_beam.damage_effect',
                                     RL + r'\damage_effects\rocket_launcher_explosion.damage_effect')},
        'target': {'weapon': (SL + r'\spartan_laser.weapon', RL + r'\rocket_launcher.weapon'),
                   'projectile': (SL + r'\projectiles\spartan_laser_beam.projectile', RL + r'\projectiles\rocket.projectile'),
                   'damage_effect': (SL + r'\damage_effects\spartan_laser_beam.damage_effect',
                                     RL + r'\damage_effects\rocket_launcher_explosion.damage_effect')},
    },

    # make_port_catalog_h2.py spartan_laser: BALANCED = step 4a's rocket ratio. balance_port.py's card
    # table (balance_Spartan_Laser_Halo3_to_Halo2.json, kept for the record) has no leg for the laser's
    # beam damage / battery / heat (the rocket has no such cards) and would carry Halo 3's 5-round salvo
    # onto the one-projectile shot -- so no table row is mapped (port_tags empty) and the entry is step
    # 4a's rows as extra_rows. Every other leg is x1 (charge 2.5, vent 2.25, battery 5, range 120, zoom
    # 2.5, autoaim / magnetism angle, magnetism range): the default IS balanced there
    'catalog': {
        'table': 'balance_Spartan_Laser_Halo3_to_Halo2.json',
        'weapon_tag': SL + r'\spartan_laser',
        'port_tags': [],
        'shared': [('jpt!', r'objects\weapons\damage_effects\smash_melee')],
        # the WEAPON row FIRST: weapon_ports.weap_path reads the entry's weapon tag off its first row
        # (boot 2's build found 'no catalog entry' with the damage rows first)
        'extra_rows': [
            {'class': 'weap', 'tag': SL + r'\spartan_laser', 'field': 'Autoaim Range', 'block': None,
             'value': 45.0, 'card': 'Autoaim', 'original': 25.0,
             'note': "step 4a: Halo 3's 25 x the rockets' 45 / 25"}] + [
            {'class': 'jpt!', 'tag': SL + r'\damage_effects\spartan_laser_beam', 'field': f, 'block': None,
             'value': 453.4, 'card': 'Beam Damage', 'original': 570.0,
             'note': 'step 4a (user 2026-10-28): the rocket ratio, direct hits with the AOE bumps counted -- '
                     'H2 rocket 150 + 200 / H3 rocket 240 + 200 = 0.795; 570 x 0.795'}
            for f in ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')],
        'fp_animations': r'objects\characters\*\fp\weapons\support_high\fp_spartan_laser\fp_spartan_laser',
        'reload_mult': None,
        'desc': ("Halo 3's Spartan Laser carried into Halo 2 with its own model, textures, sounds and "
                 "first-person animations for both species: hold the trigger 2.5 s and it fires one "
                 "devastating beam by itself, overheating; five shots a battery, 2.5x zoom. Balanced "
                 "through the Rocket Launcher: 453 damage a beam, a longer autoaim reach."),
    },

    # step 11 -- `python ai_firing_profile.py --h2-port spartan_laser`: Halo 3's ai\generic laser entry
    # (010_jungle) name-for-name into H2EK ai\generic, over the H2 ROCKET LAUNCHER's (the yardstick).
    # Halo 1's A8 lesson to check in the Armed test: a charged weapon needs the AI to HOLD the trigger
    # longer than the charge (Halo 3's profile bursts 2.6 s for its 2.5 s)
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
                       'donor_weapon': r'objects\weapons\support_high\rocket_launcher\rocket_launcher',
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03b_newmombasa', 'dervish_level': '06a_sentinelwalls'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}

r"""Gravity Hammer (Halo 3 -> Halo 1, wave A9) with the restored ENERGY SWORD as the yardstick (step
4a, user 2026-10-10). energy_sword.py is the example of a melee weapon with an energy (age) charge
per swing and a fire-button strike (`lunge`); spartan_laser.py of a new weapon on a copy of the
PLASMA PISTOL (battery HUD), its HUD and Armed-AI lessons. What is new here: a melee weapon whose
every swing sets off an AREA damage with knockback (Halo 3's gravity_hammer_explosion), which
Halo 1 does not have."""
from ._common import ANIMS, B, H3_FP_GRAPHS, IMPACTS, reserved

H3 = r'objects\weapons\melee\gravity_hammer'
GH = 'weapons\\gravity hammer\\'
SND = 'sound\\weapons\\gravity_hammer_port\\'
RL = 'weapons\\rocket launcher\\'
PP = 'weapons\\plasma pistol\\'
PG = 'weapons\\plasma grenade\\'
SW = 'weapons\\energy sword\\'
BASE = H3 + r'\bitmaps\gravity_hammer.bitmap'
ILLUM = H3 + r'\bitmaps\gravity_hammer_illum.bitmap'
# Halo 3's self_illum_color on `hammer` and `hammer_shiny` (function data BGRA d7 57 2e -> RGB
# 46 / 87 / 215, a blue; intensity empty = 1)
BLUE = (46 / 255.0, 87 / 255.0, 215 / 255.0)

PORT = reserved(
    order=18, wave='A9', name='Gravity Hammer', source='Halo 3',
    messages=(69, 70), icon=38, reticle=27, label='gh', teach_from='f',
    sound_dir='sound\\weapons\\gravity_hammer_port', weapon_dir='weapons\\gravity hammer',
    yardstick={
        # step 4a (user, 2026-10-10): h3_weapon_values.py (gravity_hammer / energy_blade) + the
        # weapon, its damage effects and FP graph (tool export-tag-to-xml) + h1_role_compare.py
        # gravity_hammer. What h3_weapon_values does not print:
        #   SWING   1st / 2nd / 3rd hit = the SHARED `smash_melee` 80 (no radius; the same tag
        #           as Halo 3's rocket launcher and flak cannon melee), PLUS the hammer's own
        #           `gravity_hammer_explosion` 50..160 over 0.75 -> 1.5 wu (AOE core 0.75),
        #           instantaneous acceleration 3.5, category melee / explosion_small, AI stun
        #           4.5 wu, shake 10 wu, small screen flash. It is set off by an ANIMATION EFFECT
        #           (fp_gravity_hammer_impact on the FP strike / lunge at frame 4 = the primary
        #           keyframe; gravity_hammer_impact on the third-person one, marker
        #           hammer_detonation) -- on every swing, hit or not. Brutes swing their own
        #           `gravity_hammer_explosion_brute` (20..160, 0.6 -> 1.2). The `rumble` part is
        #           0 damage, acceleration 3, a shake
        #           -> a direct swing 80 + 160 = 240 (upper bounds, the Spartan Laser's rule),
        #           every melee_strike 38 fr = 1.27 s (189 dps)
        #   LUNGE   `crush_melee` 150 (collision) + the explosion = 310, melee_lunge 46 fr; flags
        #           'allows unaimed lunge', 'melee only', 'cannot fire at maximum age', 'use
        #           empty melee on empty'
        #   AOE SPIKE  none: aoe spike radius / bump 0 on all four damage effects (smash, crush,
        #           explosion, explosion_brute)
        #   ENERGY  campaign external aging 0.05 a swing (20 swings; multiplayer 0.0835): Halo 3
        #           ages the hammer from the damage routine for the attacker's CURRENT weapon
        #           whenever its explosion damage applies (memory halo-weapon-aging-energy)
        #   AIM     autoaim 10 deg / 1.75 wu (falloff 1.75), magnetism 10 deg / 6 wu
        # Ratio candidates (h1_role_compare.py gravity_hammer; H1 yardstick melee x H3 hammer /
        # H3 yardstick melee on both parts, interval x H1 / H3 melee animation, aim per field):
        #   Energy Sword  151/150 (dash_melee) -> 80.5 + 161.1, 1.27 s, aim = Halo 3's: x1.007
        #   Fuel Rod      55/80 (flak smash_melee) -> 55 + 110, 1.27 s, aim = Halo 3's
        #   Rocket L.     55/80 -> 55 + 110, 1.57 s, aim 0/2.45 12/8.4
        #   AR            55/70 (strike_melee) -> 62.9 + 125.7, 1.56 s, aim 12/2.92 12/7.5
        #   Oddball       80/150 (oneshot_melee) -> 42.7 + 85.3, 1.04 s, aim 0
        # Legendary hits to kill (H3 own / sword): Elite minor 2, major 2, commander 2, Hunter 2,
        # Flood 1; the Fuel Rod / RL ratios one more on majors and commanders
        'pick': 'Energy Sword',
        'reason': "user, step 4a 2026-10-10: the restored sword is Halo 1's only melee weapon in "
                  "the hammer's role and already carries Halo 3's own melee damage (151 vs "
                  "dash_melee 150) and aim assist, so the ratio is x1.007 -- BALANCED = DEFAULT in "
                  "practice (241.6 vs 240 a swing, the same 1.27 s and aim). Energy has no ratio "
                  "(Halo 3 ages the sword per KILL, the hammer per swing): the hammer keeps Halo "
                  "3's 0.05 a swing in both. The heavy-weapon reading (Fuel Rod / RL melee, "
                  "x0.69: Halo 3's hammer smash IS their smash_melee) was shown and not picked",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); BALANCED = the sword ratio x1.007
        'balanced': {
            'smash': 80.53,                # 80 x 151/150
            'explosion': 161.07,           # 160 x 151/150 (lower bound 50 -> 50.3)
            'radius': (0.75, 1.5),         # the sword's melee radius 0.5 = Halo 3's dash 0.5: x1
            'interval_s': 38 / 30.0,       # 0.80 s / 24 fr: x1
            'aim': (10.0, 1.75, 10.0, 6.0),  # the H1 sword tag carries Halo 3's: x1
            'energy': 0.05},               # no ratio (per kill vs per swing)
        # Halo 1 materials: the smash on the sword's melee table (every material x1); the
        # explosion on the rocket explosion's (Halo 3 explosion_small = _large for Halo 1
        # except soft flood flesh x1 vs x2: the Brute Shot's finding) with Flood x1
        'materials': {'explosion': {'flood_combat_form': 1.0}},
        'measured': 'h1_role_compare.py gravity_hammer',
        'candidates': {
            'source_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
            'provisional': 'Energy Blade',
            'alternatives': ['Fuel Rod melee', 'Rocket Launcher melee', 'Assault Rifle melee',
                             'Oddball'],
            'direct': None,
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "pure melee, energy aging per swing like the sword (whose H1 numbers are Bungie's own)",
            'lacks': 'area knockback blast'}},
    # step 11: the source game's ai\generic entry (8 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer'},
)

PORT.update({
    'status': 'in progress',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's materials: hammer (base + bump + brute
    # metal detail + the ILLUM map), hammer_shiny (base + chrome reflections + illum), hammer_dull
    # (base, rubber detail: the grip). h3_rm_info: both roots `hammer` rest at 0 deg and the
    # shaft runs along +z -- Halo 1's FLAG pole does too (z -0.11..0.90, the `f` pose this port
    # is taught from), so no world_frame. Template: the rocket launcher's body shader (the
    # Brute Shot's: Brute metal)
    'model': {
        'dir': r'weapons\gravity hammer',
        'world': H3 + r'\gravity_hammer.render_model',
        'fp': H3 + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'world_name': 'gravity hammer',
        'shaders': {'hammer': (BASE, ILLUM),
                    'hammer_shiny': (BASE, ILLUM),
                    'hammer_dull': (BASE, None)},
        'glow': {'hammer': BLUE, 'hammer_shiny': BLUE},
        'drop_materials': ['invalid'],
        'template': RL + r'shaders\rocket launcher body',
    },

    # FP animations (h1_fp_retarget.py). Halo 3 hammer frames: ready 55, put_away 6,
    # melee_strike_1 / _2 38 (primary keyframe 4, the explosion effect at 4), melee_lunge 46,
    # posing var1 69, idle 99, moving 23. The FIRE button swings (strike 1, the explosion strike);
    # the MELEE button is strike 2 (Halo 3 alternates them)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\melee\fp_gravity_hammer\fp_gravity_hammer.model_animation_graph',
        'render_model': H3 + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'nodes': {'hammer': 'frame hammer', 'shaft': 'frame shaft'},
        'h1_dir': r'weapons\gravity hammer\fp',
        'h1_model': r'weapons\gravity hammer\fp\fp',
        'align': 'same_space',
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:melee_strike_1': 'first-person fire-1',
            'first_person:melee_strike_2': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py gravity_hammer). Halo 3 cues: hammer_melee at frame 0
    # of both strikes, hammer_ready / hammer_posing at 0 (graph_sound_events); the strike's
    # impact effects play hammer_hit (third person, with the explosion) and the Brute's
    # tartarus_melee (first person) on the same frame -> ONE hit sound, both mixed; drops
    # hammer_drops (its material effects). Levels = the stock Halo 1 sound each stands in for:
    # the sword's melee weapon pair (ball_melee -16.2, its hit melee_impact_fleshy -14.0), the
    # rocket's heavy-weapon foley (rocket_ready -18.3, rocket_posing -22.1, rlauncher_impact -23.0)
    'sounds': {
        'catalog': 'Gravity Hammer',
        'dir': B.join(['sound', 'weapons', 'gravity_hammer_port']),
        'h3_dir': 'data\\sound\\weapons\\gravity_hammer\\',
        'sounds': {
            'gh_melee': (['fp_hammer\\hammer_melee'], ANIMS + B + 'ball_melee', -16.2),
            'gh_ready': (['fp_hammer\\hammer_ready'], ANIMS + B + 'rocket_ready', -18.3),
            'gh_pose': (['fp_hammer\\hammer_posing'], ANIMS + B + 'rocket_posing', -22.1),
            'gh_hit': (['hammer_hit', 'data\\sound\\characters\\brute\\tartarus_melee'],
                       IMPACTS + B + 'melee_impact_fleshy', -14.0),
            'gh_drop': (['hammer_drops'], 'sound\\sfx\\impulse\\weapon_drops\\rlauncher_impact', -23.0),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only gravity_hammer) on a COPY of the Halo 1 PLASMA
    # PISTOL (the Spartan Laser's base: a stock pickable weapon with a collision model and the
    # battery HUD; the restored sword's tag carries blade contrail widgets, a glow light and
    # the hum, and no collision model). DEFAULT = HALO 3's OWN NUMBERS; the sword ratio
    # (x1.007) = the balance rows.
    # HALO 1 HAS NO AREA MELEE. The approximation (the sword lunge's precedent: a trigger):
    #   FIRE  = Halo 3's swing: the sword's fire-button trigger (`lunge`, no shove) fires an
    #           invisible STRIKE that hits for the smash (impact 80) and DETONATES -- on whatever
    #           it meets, or by its timer in the air -- into the hammer's explosion (160 over
    #           0.75 -> 1.5 wu, the knockback): every swing blasts, hit or not, as Halo 3's. Each
    #           swing costs 0.05 energy (Halo 3's campaign aging); at full age it cannot fire
    #   MELEE = Halo 1's melee: the smash alone (80). Halo 1 cannot age a weapon on melee, so
    #           it costs nothing and does not blast
    # Not reproduced: the lunge (crush_melee 150 at a target in lunge range: Halo 1 has no
    # player lunge), the blast on the melee button, the Brutes' smaller explosion
    'pickable': {
        'weapon': GH + 'gravity hammer',
        'template': PP + 'plasma pistol',
        'world_model': GH + 'gravity hammer',
        'fp_model': GH + 'fp\\fp',
        'fp_anims': GH + 'fp\\fp',
        'label': 'gh',
        # two-handed, held like the FLAG (its pole runs along z like the hammer's shaft)
        'teach': ('gh', 'f'),
        'keys': {'first-person melee': 4},           # H3 melee_strike primary keyframe 4
        'sounds': {'first-person ready': SND + 'gh_ready',
                   'first-person posing': SND + 'gh_pose',
                   'first-person melee': SND + 'gh_melee',
                   'first-person fire-1': SND + 'gh_melee'},
        # every template attachment goes (lights / flares draw at the hidden third-person gun
        # in first person; the charging loop is the plasma pistol's)
        'drop_attachments': [0, 1, 2, 3, 4],
        # the MELEE button's smash: a copy of the sword's melee (every material x1: Halo 3's
        # smash_melee is a melee-category hit on everything), Halo 3's 80 as its mean
        'melee': (SW + 'melee', GH + 'melee'),
        'melee_dmg': 80.0,
        'melee_response': PP + 'melee_response',
        # the melee's hit sound (the sword's recipe): Halo 3's hammer hit
        'hit_sound': SND + 'gh_hit',
        # the FIRE button (h1_pickable_weapons.make_lunge): trigger only, no shove -- one swing
        # every 38 fr, 0.05 energy each
        'lunge': {'template': PP + 'plasma pistol', 'strike': None, 'push': None,
                  'rate': 30 / 38.0, 'energy': 0.05},
        # THE STRIKE (own_beam): a copy of the sword's invisible lunge projectile, its impact the
        # smash, its detonation the explosion. Range 1.2 wu (Halo 3 slams the head about a
        # hammer's length ahead); detonate on EVERY material; a 0.05 s timer from launch
        # bursts it in the air (a miss) -- the range alone may not detonate
        'bullet': {'projectile': (SW + 'lunge', GH + 'strike'),
                   'damage': (SW + 'lunge strike', GH + 'smash'),
                   'dmg': 80.0, 'acceleration': 1.0,
                   'range': 1.2,
                   'default_responses': {'detonate': list(range(33))},
                   'clear_response_effects': True,
                   'fields': {'sound.filepath': ''},       # the copy's sword hit (the blast sounds)
                   'proj_fields': {'proj_attrs.detonation_timer_starts': 'immediately',
                                   'proj_attrs.detonation.timer': (0.05, 0.05)},
                   'explosion': {'effect': (PG + 'effects\\explosion', GH + 'effects\\blast'),
                                 # the rocket explosion's material table (Halo 3's explosion_small
                                 # = _large for Halo 1 but Flood x1)
                                 'damage': (RL + 'explosion', GH + 'explosion'),
                                 'part': PG + 'explosion',
                                 'lower': 50.0, 'upper': (160.0, 160.0), 'radius': (0.75, 1.5),
                                 'mods': {'flood_combat_form': 1.0},
                                 'fields': {'damage.instantaneous_acceleration': 3.5,
                                            'damage.aoe_core_radius': 0.75,
                                            'damage.flags.does_not_hurt_owner': True},
                                 # the plasma grenade's blue burst + light; its 8 wu shock wave,
                                 # burn decal and sound go (the hammer brings its own)
                                 'drop_parts': [PG + 'shock wave',
                                                'effects\\decals\\bullet holes\\plasma burn large'],
                                 'swaps': {'sound\\sfx\\weapons\\plasma grenade\\plasmagrenexpl': SND + 'gh_hit'},
                                 'scale': 0.75, 'out_dir': GH + 'effects\\'},
                   'triggers': (0,)},
        'fields': {
            # Armed AI swing the weapon's own melee damage (the sword's flag)
            'weap_attrs.flags.ai_uses_weapon_melee_damage': True,
            'weap_attrs.interface.pickup_sound.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'gh_drop',
        },
        'messages': ('Picked up a gravity hammer', 'Picked up %d rounds for gravity hammer'),
        'icon': 'gravity hammer',
        # the PLASMA PISTOL's HUD: its BATTERY bar is the hammer's energy (the sword's), Halo 3's
        # hammer reticle (hud_reticles #20 at chud scale 0.59, one widget, no mirror) at the
        # reserved 27. Simulated first (out/reticle_gh_*_sim.png): the sprite has TWO levels,
        # white strokes ~250 and dim inner outlines ~70-95; grown together to 3 px the dim
        # outlines fell under the threshold and drew dotted -> grown apart (`reticle_split`)
        'hud': {'donor': PP + 'plasma pistol', 'out': GH + 'gravity hammer',
                'reticle': ('hud_reticles', 20, 'gravity hammer'),
                'reticle_min_width': 3, 'reticle_split': 160},
        # Halo 3's aim assist, absolute
        'aiming': {'autoaim_angle': 10.0, 'autoaim_range': 1.75,
                   'magnetism_angle': 10.0, 'magnetism_range': 6.0},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # the dry test: a30 (Covenant within seconds of the landing), a battery weapon spawns
    # charged (rounds 0 / 0)
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

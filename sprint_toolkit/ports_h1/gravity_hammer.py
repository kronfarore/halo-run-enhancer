r"""Gravity Hammer (Halo 3 -> Halo 1, wave A9) with the restored ENERGY SWORD as the yardstick (step
4a, user 2026-10-10). energy_sword.py is the example of a melee weapon with an energy (age) charge
per swing and a fire-button strike (`lunge`); spartan_laser.py of a new weapon on a copy of the
PLASMA PISTOL (battery HUD), its HUD and Armed-AI lessons. What is new here: a melee weapon whose
every swing sets off an AREA damage with knockback (Halo 3's gravity_hammer_explosion), which
Halo 1 does not have."""
from ._common import ANIMS, B, H3_FP_GRAPHS, IMPACTS, reserved, row

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
# BOOT 2 (user): 'apply the glow' -- the Spike Rifle's final recipe (its blue was Halo 3's 2f/31/d8,
# the hammer's 2e/57/d7): Halo 3 lights thin lines of a few texels and BLOOMS them; Halo 1 shows
# them as nothing at colour x1 -> PALE (Halo 3's intensity + bloom read pale) and 2 px thicker
PALE = (0.75, 0.78, 1.0)
# STEP 4b (port_field_audit.py --port gravity_hammer, BEFORE boot 1; out/gh/4b.txt). Source
# pair: the H3 hammer vs the H3 energy blade; target: the H1 port vs the H1 sword.
# The SMASH (smash_melee vs dash_melee onto the H1 sword's melee), on the melee AND the fire
# swing's strike: acceleration 1 x 2.5/1.5 = 1.67; screen flash duration 1 x 3/1.25 = 2.4 (the
# shielded response; Halo 1 has one flash). Radius 0 x 0.5/0.5 = 0 NOT taken: every stock Halo 1
# melee is 0.5 and a 0 radius risks a melee that never connects. Camera impulse (1.2 / 0.25,
# the H1 sword 0): skipped, Halo 1's melees have none
SMASH_4B = {'damage.instantaneous_acceleration': 2.5 / 1.5,
            'screen_flash.duration': 2.4}
# The EXPLOSION (gravity_hammer_explosion vs dash_melee onto the H1 sword's melee). List 2:
# ACCELERATION 3.5 x 2.5/1.5 = 5.83 (Halo 1 pushes ~2x Halo 3 per unit: the rocket 6 vs 3, the
# sword 2.5 vs 1.5 -- 5.83 sits at the H1 rocket's 6), active camo damage 0.1 x 1/0.9; damage
# 50 / 160 x 151/150 = the BALANCED rows. List 4: category = Halo 3's own 'melee' (both melee in
# the source; the H1 sword's is plasma, the template rocket's high_explosive). List 3 (a zero on
# one side -> the source value): breaking effect forward 30 / 2 wu / exponent 0, outward 15 / 1
# wu; shake random translation 0.05. Kept the rocket's: screen flash (duration 0 = none, Halo
# 3's small_screen_flash is a response, not a field), vibration, camera impulse 0 (an angle
# whose Halo 3 units are unchecked), damage modifiers (the yardstick decision: the rocket's
# table, Flood x1)
EXPLOSION_4B = {'damage.instantaneous_acceleration': 3.5 * 2.5 / 1.5,
                'damage.active_camouflage_damage': 0.1 / 0.9,
                'damage.category': 'melee',
                'damage.aoe_core_radius': 0.75,
                'damage.flags.does_not_hurt_owner': True,
                'camera_shaking.random_translation': 0.05,
                'breaking_effect.forward_velocity': 30.0,
                'breaking_effect.forward_radius': 2.0,
                'breaking_effect.forward_exponent': 0.0,
                'breaking_effect.outward_velocity': 15.0,
                'breaking_effect.outward_radius': 1.0}

# THE SHOCKWAVE (boots 2-7). Halo 3's ring is a mesh particle (fx ... blast_radius); Halo 1 has
# none. Halo 1's own shockwave ring is the Wraith mortar's `light ring expand` (additive, lying
# perpendicular to the effect's direction, radius x0.25 -> x20 in 0.1-0.2 s; the mortar: 2 at
# radius 0.2..0.5 -> 4..10 wu).
#   BOOT 3 (user): 'not the described behaviour; it looks better than the last explosion,
#     remember this state' -- kept as effects\blast.effect.boot3 (2 stock rings at location 0
#     over the plasma grenade burst): at location 0 a ring faces the effect's direction, the
#     strike's flight -- an air burst stood them up, small, facing the player.
#   BOOT 4: location 1 = 'gravity' (straight down: the grenade's scorch decal) -> FLAT; still
#     not seen. BOOT 5: an OWN copy lasting 0.5-0.6 s (fading over the last 0.4), full bright,
#     to ~3 wu -> user: 'there is the ring, I like it. Remove the explosion, size the ring to
#     the explosion' -> boot 6: the ring alone, ending at the blast's 1.5 wu (radius 0.075).
#   BOOT 6 (user): 'slightly bigger; try two setups -- rings stacked above and beneath, and
#     several rings from the same position; one brighter, the other longer'. Both end at 1.8
#     wu (radius 0.09). A/B in ONE boot round (A on a30, B on a50).
#   BOOT 7 (user): 'A it is -- the stacked rings are brighter; B's long duration does not look
#     good, the old one is better, and rings one after another enhance that'. A, its top and
#     bottom rings closer to the centre: 0.25 -> 0.12 wu
RING = {'from': r'vehicles\wraith\effects\wraith mortar explosion', 'match': 'light ring expand',
        'location': 1, 'radius': (0.09, 0.09), 'tint': (1.0, 0.75, 0.85, 1.0)}
RING_PART = {'out': GH + r'effects\shockwave ring', 'lifespan': (0.5, 0.6), 'fade_out': 0.4}
# three rings stacked along the gravity location's axis (i = down) 0.12 wu apart, each drawn x4
# (additive: brighter). (B -- three rings from the same spot 0.12 s apart, 0.9-1.0 s each -- was
# rejected)
RINGS = [dict(RING, offset=(i, 0.0, 0.0), count=4, particle=RING_PART) for i in (-0.12, 0.0, 0.12)]

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
        'glow': {'hammer': PALE, 'hammer_shiny': PALE},
        'illum_dilate': 2,
        # ... and a small radial HALO card per cluster of lit texels (the Spike Rifle's side lights,
        # its test 5-6 size 0.4), both lit materials (out/gh/glow_map.png: 159 lit triangles --
        # the head's front faces, the side panels by the head, the pommel)
        'glow_shaders': {'gh_spot': {'rgb': PALE, 'additive': True, 'radial': True,
                                     'falloff': 1.6, 'gain': 1.0}},
        'glow_spots': [{'material': 'hammer', 'illum': ILLUM, 'shader': 'gh_spot',
                        'size': 0.4, 'lift': 0.05, 'merge': 0.4},
                       {'material': 'hammer_shiny', 'illum': ILLUM, 'shader': 'gh_spot',
                        'size': 0.4, 'lift': 0.05, 'merge': 0.4}],
        'drop_materials': ['invalid'],
        'template': RL + r'shaders\rocket launcher body',
        # BOOT 1 (user): 'the weapon sinks into the ground'. It kept the plasma pistol template's
        # collision model (a pistol-sized hull, other node names). Its OWN hull, three boxes
        # from the world model's cross-section (h1_box_collision.py): shaft + knob, the neck
        # and blade under the head, the head
        'collision': {'material': 'metal',
                      'boxes': [((-0.025, -0.025, -0.30), (0.048, 0.025, 0.05)),
                                ((-0.08, -0.022, 0.05), (0.02, 0.022, 0.20)),
                                ((-0.095, -0.051, 0.20), (0.09, 0.051, 0.40))]},
    },

    # FP animations (h1_fp_retarget.py). Halo 3 hammer frames: ready 55, put_away 6,
    # melee_strike_1 / _2 38 (primary keyframe 4, the explosion effect at 4), melee_lunge 46,
    # posing var1 69, idle 99, moving 23.
    # BOOT 1 (user): 'the fire button uses the wrong swing -- it strikes with the KNOB, like the
    # melee; it should strike with the hammer HEAD'. melee_strike_1 / _2 are Halo 3's pommel
    # jabs (the melee button); the head SLAM is the lunge (the RT attack): melee_lunge_unaimed
    # (46 fr: wind-up over the right shoulder frames 1-3, the head lands at frame 4 = 0.13 s and
    # stays down to ~26, recovery to 46; out/gh/lunge_sheet.png) -> FIRE. The melee button keeps
    # strike 1 (Halo 1 has one melee animation)
    # BOOT 1 (user): 'FP position is too high, lower it by 1 unit' (1 unit = 0.01 wu, z up)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\melee\fp_gravity_hammer\fp_gravity_hammer.model_animation_graph',
        'render_model': H3 + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'nodes': {'hammer': 'frame hammer', 'shaft': 'frame shaft'},
        'h1_dir': r'weapons\gravity hammer\fp',
        'h1_model': r'weapons\gravity hammer\fp\fp',
        'align': 'same_space',
        # BOOT 2 (user): 'another unit lower'
        # BOOT 3 (user): 'about 0.5 closer to the camera' (x = forward)
        'view_offset': (-0.005, 0.0, -0.02),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:melee_lunge_unaimed': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
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
    #   FIRE  = Halo 3's head SLAM (its RT attack, the lunge animation -- boot 1): the sword's
    #           fire-button trigger fires an invisible STRIKE that hits for the lunge's
    #           crush_melee (impact 150) and DETONATES -- on whatever it meets, or by its timer
    #           in the air -- into the hammer's explosion (160 over 0.75 -> 1.5 wu, the
    #           knockback): every slam blasts, hit or not, as Halo 3's. One slam every 46 fr;
    #           each costs 0.05 energy (Halo 3's campaign aging); at full age it cannot fire
    #   MELEE = Halo 3's pommel jab (melee_strike): the smash alone (80). Halo 1 cannot age a
    #           weapon on melee, so it costs nothing and does not blast (user: the right design)
    # Not reproduced: the lunge's dash toward a target (user: not needed if it can't be
    # helped), the blast on the melee button, the Brutes' smaller explosion
    # (4a correction, boot 1: the fire swing is Halo 3's lunge, 150 + 160 = 310 every 46 fr,
    # not the strike's 80 + 160 every 38 -- the 'GH lunge = H3 own' row of h1_role_compare; the
    # sword ratio is the same x151/150, so the pick stands)
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
        'melee_fields': SMASH_4B,
        'melee_response': PP + 'melee_response',
        # the melee's hit sound (the sword's recipe): Halo 3's hammer hit
        'hit_sound': SND + 'gh_hit',
        # the FIRE button (h1_pickable_weapons.make_lunge): one slam every 46 fr, 0.05 energy each.
        # BOOT 1 (user): 'no knockback on the player -- the shockwave should push the player
        # slightly BACKWARDS with no damage'. The blast does not hurt its owner (and so does not
        # push him); the sword's SHOVE instead: a firing damage on the wielder, a token 0.01
        # damage with every material x1 (0 damage pushed nothing, sword boot 1), POSITIVE
        # acceleration = backwards (sword boot 2). +2 a start ('slightly'; the sword lunge is -10)
        'lunge': {'template': PP + 'plasma pistol', 'strike': None,
                  'push': GH + 'recoil', 'push_from': PP + 'trigger',
                  # BOOT 2 (user, tuned live in Assembly): 5
                  'acceleration': 5.0, 'push_damage': 0.01,
                  'rate': 30 / 46.0, 'energy': 0.05},
        # THE STRIKE (own_beam): a copy of the sword's invisible lunge projectile, its impact the
        # lunge's crush, its detonation the explosion. Range 1.2 wu (Halo 3 slams the head about
        # a hammer's length ahead); detonate on EVERY material.
        # BOOT 1 (user): 'the explosion happens too early, basically frame 1, rather than on
        # impact'. The strike flew 1.2 wu at 60 wu/s (0.02 s) and burst by a 0.05 s timer; the
        # head lands at frame 4 (0.13 s): now 9 wu/s (1.2 wu in 0.13 s) with the timer at 0.13 s
        # -- the slam's own moment in the air, sooner on a target in reach
        'bullet': {'projectile': (SW + 'lunge', GH + 'strike'),
                   'damage': (SW + 'lunge strike', GH + 'crush'),
                   # Halo 3's crush_melee 150 = the sword's dash_melee in every field but radius
                   # (0 vs 0.5) and damage type: the sword strike's own acceleration (2.5) and
                   # screen flash are already the 4b ratio (x1)
                   'dmg': 150.0,
                   # BOOT 2 (user): 'blast still too early'. The retargeted slam's head (0.3 wu up
                   # the hammer node) is lowest from frame 5 (0.17 s; frame 4 is still at eye
                   # level), and Halo 1 starts the animation about a tick after the shot ->
                   # 0.20 s: 6 wu/s for 1.2 wu, timer 0.2
                   'range': 1.2, 'velocity': 6.0,
                   'default_responses': {'detonate': list(range(33))},
                   'clear_response_effects': True,
                   # the copy's sword hit sound off (the blast sounds)
                   'fields': {'sound.filepath': ''},
                   'proj_fields': {'proj_attrs.detonation_timer_starts': 'immediately',
                                   'proj_attrs.detonation.timer': (0.2, 0.2)},
                   'explosion': {'effect': (PG + 'effects\\explosion', GH + 'effects\\blast'),
                                 # the rocket explosion's material table (Halo 3's explosion_small
                                 # = _large for Halo 1 but Flood x1)
                                 'damage': (RL + 'explosion', GH + 'explosion'),
                                 'part': PG + 'explosion',
                                 'lower': 50.0, 'upper': (160.0, 160.0), 'radius': (0.75, 1.5),
                                 'mods': {'flood_combat_form': 1.0},
                                 # BOOT 1 (user): 'no knockback on the enemy'. 5.83 (the 4b
                                 # ratio, the H1 rocket's 6) moves only DEAD bodies visibly: a
                                 # living biped on the ground sheds a few wu/s at once (Elites
                                 # take x0.6, Grunts x0.9). 15 a start; Halo 3's hammer launches
                                 # its targets. Live-tunable: the explosion jpt's
                                 # Instantaneous Acceleration (Assembly)
                                 # BOOT 2 (user, tuned live in Assembly): 15 -> 7.5
                                 'fields': dict(EXPLOSION_4B, **{'damage.instantaneous_acceleration': 7.5}),
                                 # the SHOCKWAVE (boots 2-6): RINGS, see RING above
                                 'add_particles': RINGS,
                                 # the plasma grenade's blue burst + light; its 8 wu shock wave,
                                 # burn decal and sound go (the hammer brings its own)
                                 'drop_parts': [PG + 'shock wave',
                                                'effects\\decals\\bullet holes\\plasma burn large'],
                                 'swaps': {'sound\\sfx\\weapons\\plasma grenade\\plasmagrenexpl': SND + 'gh_hit'},
                                 # BOOT 5 (user): 'the ring is there and I like it. Remove the
                                 # explosion, size the ring to the explosion' -> no burst, no
                                 # light flash: the damage, its knockback and the sound stay
                                 'drop_classes': ['particle_system', 'light'],
                                 'out_dir': GH + 'effects\\'},
                   'triggers': (0,)},
        'fields': {
            # Armed AI swing the weapon's own melee damage (the sword's flag)
            'weap_attrs.flags.ai_uses_weapon_melee_damage': True,
            'weap_attrs.interface.pickup_sound.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'gh_drop',
            # STEP 4b, the weapon. List 2: acceleration scale 0 x 2/1 = 0 (Halo 3's hammer is not
            # thrown about by explosions); bounding radius 0 = Halo 3 computes it -> the
            # template's. List 4 (both 0 in the source -> the sword's 0): active camo ding /
            # regrowth. List 3: 'melee only' / 'allows unaimed lunge' (no Halo 1 flag), autoaim
            # falloff, tracking, turn-on time (no Halo 1 field); external aging = the trigger's
            # age per round (the lunge `energy`)
            'obje_attrs.acceleration_scale': 0.0,
            'weap_attrs.interface.active_camo_ding': 0.0,
            'weap_attrs.interface.active_camo_regrowth_rate': 0.0,
            # BOOT 1 (user): 'sinks into the ground' -> its OWN hull (model['collision'],
            # h1_box_collision.py), and a bounding radius that covers the 0.67 wu model (the
            # template's 0.2 is a pistol's; the farthest vertex sits 0.40 wu from the origin)
            'obje_attrs.collision_model.filepath': GH + 'gravity hammer',
            # BOOT 3 (user's screenshots): the hull changed nothing -- Halo 1 rests a dropped
            # item on its ORIGIN (the grip) with its model z axis VERTICAL, either way up: the
            # hammer stood on its head or its handle (stock guns lie flat only because their
            # z is the model's up). The user's pick of three (lie flat + shoulder / rifle pose,
            # or stand like the flag): STAND LIKE THE FLAG -- the flag pose kept, the flag's
            # 'always maintains z up': head up every time, the lower 0.29 wu of handle in the
            # ground (the hull stays: what projectiles hit)
            'item_attrs.flags.always_maintains_z_up': True,
            'obje_attrs.bounding_radius': 0.42,
            # BOOT 1 (user): 'each swing costs ABOUT 5%' -- float32 0.05 is 0.0500000007, so the
            # HUD reads 94, 89, ... Boot 2 tried the Spartan Laser's fix (the float just below,
            # 0.049999997): 'steps to 39 from 45 -- the fix doesn't hold at a step of 5'. The
            # laser had 5 additions; 20 float32 sums of 0.05 round by up to ~3e-8 each, more
            # than that 3e-9 margin. Now a margin the sums cannot eat: 0.0499 a slam (the HUD
            # reads 95.01 -> 95 ... 5.19 -> 5, 0.2 -> 0); after 20 slams the age is 0.998 < 1,
            # so the age MISFIRE stops a 21st (start 0.99: 19 slams = 0.948 still fire; chance 1;
            # make_lunge cleared the misfire effects)
            'weap_attrs.triggers.0.misc.age_generated_per_round': 0.0499,
            'weap_attrs.age.misfire_start': 0.99,
            'weap_attrs.age.misfire_chance': 1.0,
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

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py gravity_hammer). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the ENERGY SWORD ratio (step 4a, user 2026-10-10):
    # x151/150 on every damage -- the rest is x1 (interval 0.80 s / 24 fr, aim = Halo 3's in
    # both swords, swap: the H1 sword's ready 54 fr = Halo 3's 54 -> x1, no `anims` row; energy
    # has no ratio). Assembly Halo1 units
    'catalog': {
        'entry': {
            'weapon': 'Gravity Hammer', 'source': 'Halo 3', 'donor': 'Energy Blade', 'default_on': False,
            # no weapon-class balance row names the weapon tag: say it (the Sentinel Beam's key)
            'weap': GH + 'gravity hammer',
            # the swing's strike exists only in the port build
            'requires': ['proj ' + GH + 'strike'],
            # the Armed rule's class (h1_enemy_weapons.hands): TWO-handed (held like the flag;
            # Halo 3's Brutes carry it two-handed) -- a proposal for the enhancer session
            'hands': 'two',
            'desc': "Halo 3's Gravity Hammer: its model, first-person animations, sounds, reticle "
                    "and numbers. Fire slams the head down (150) into a knockback blast (160 over "
                    "1.5 wu), 20 slams a charge; melee jabs with the pommel (80).",
            'balance_desc': "Measured against the Energy Sword, which both games have: the "
                            "same as Halo 3's within 1% (Halo 1's sword already carries Halo 3's "
                            "own melee damage and aim assist).",
            'anims': {},
            'balance': [
                # x151/150: the slam's crush 150 -> 151 (= the sword lunge's own), the melee's
                # smash 80 -> 80.53
                row('jpt!', GH + 'crush', 'Damage Lower Bound', 151.0, 150.0, 'Slam Damage'),
                row('jpt!', GH + 'crush', 'Damage Upper Bound', 151.0, 150.0, 'Slam Damage'),
                row('jpt!', GH + 'crush', 'Damage Upper Bound Max', 151.0, 150.0, 'Slam Damage'),
                row('jpt!', GH + 'melee', 'Damage Lower Bound', 80.53, 80.0, 'Smash Damage'),
                row('jpt!', GH + 'melee', 'Damage Upper Bound', 80.53, 80.0, 'Smash Damage'),
                row('jpt!', GH + 'melee', 'Damage Upper Bound Max', 80.53, 80.0, 'Smash Damage'),
                # the blast 50..160 -> 50.33..161.07
                row('jpt!', GH + 'explosion', 'Damage Lower Bound', 50.33, 50.0, 'Blast Damage'),
                row('jpt!', GH + 'explosion', 'Damage Upper Bound', 161.07, 160.0, 'Blast Damage'),
                row('jpt!', GH + 'explosion', 'Damage Upper Bound Max', 161.07, 160.0, 'Blast Damage'),
            ]},
    },

    # step 4b (port_field_audit.py --port gravity_hammer): the source pair (H3 hammer vs the
    # yardstick, H3 energy blade) against the target pair (the H1 port vs the H1 sword). Halo 3
    # has no hammer projectile; the explosion's pair is the sword's own hit (dash_melee / the
    # H1 sword melee) -- the only damage the yardstick has; the template is the plasma pistol
    # (the full field diff covers it)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\gravity_hammer.weapon', r'objects\weapons\melee\energy_blade\energy_blade.weapon'),
                   'damage_effect': (H3 + r'\damage_effects\gravity_hammer_explosion.damage_effect',
                                     r'objects\weapons\damage_effects\dash_melee.damage_effect'),
                   'melee': (r'objects\weapons\damage_effects\smash_melee.damage_effect',
                             r'objects\weapons\damage_effects\dash_melee.damage_effect')},
        'target': {'weapon': (GH + 'gravity hammer.weapon', SW + 'energy sword.weapon'),
                   'damage_effect': (GH + 'explosion.damage_effect', SW + 'melee.damage_effect'),
                   'melee': (GH + 'melee.damage_effect', SW + 'melee.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), a battery weapon spawns
    # charged (rounds 0 / 0)
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

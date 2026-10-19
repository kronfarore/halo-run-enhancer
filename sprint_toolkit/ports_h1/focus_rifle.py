r"""Focus Rifle (Halo Reach, wave B7): a CONTINUOUS BEAM on heat + battery with two zoom levels, on a
copy of the Halo 1 PLASMA RIFLE (the yardstick, step 4a). Nearest shapes: plasma_repeater.py /
needle_rifle.py for the Reach plumbing, sentinel_beam.py for the beam on heat + battery (the 15/s
cap, the end-on contrail, the first-person offset, the held-trigger hum), beam_rifle.py for the
scope. Built in parallel with B5 (the Concussion Rifle): test level b30, zoom glyphs at
hud_reticles 48-51 only (H1_PORT_PLAN "Running two ports in parallel").

STEP 4a (user, 2026-10-12; h1_role_compare.py focus_rifle). Reach (HREK, h3_weapon_values --kit
reach): a spew beam, 3 a round (plasma_fast) x 30/s = 90 dps, 4000 wu/s, range 120, error 0,
heat 0.025 a round, loss 0.35 / 0.23 overheated, recovery 0.1, overheated 1, battery 0.0016125 a
round (campaign the same: 620 rounds = 20.7 s), zoom 2 (3.5, 9.5), aim 2/10 4/10, strike_melee.
REACH COOLS WHILE FIRING: the user's stopwatch in Reach, ~2.5 s to overheat from cold = 0.75 heat/s
generated - 0.35 loss (the meter never visibly falls); 'no cooling' would be 1.33 s. Halo 1 fires a
held 30/s at 30/s -- BOOT 2's probe (h1_weapon_state_probe, the 15/s 'cap' did not hold: shots 33 ms
apart, the repeater's fire rule: rate/30 a tick reaches 1 every tick) -> Reach's own per-round values
(3 a round, battery 0.0016125); Halo 1 cools while firing at its ONE loss (the Plasma Repeater's
probe) -> heat a round fitted so the gun overheats on the same second as Reach."""
from ._common import B, reserved, row

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\focus_rifle'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle'
FO = 'weapons\\focus rifle\\'
SND = 'sound\\weapons\\focus_rifle_port\\'
PR = 'weapons\\plasma rifle\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# the heat colour of the display tiles (Reach's meter: OFF (0, 69, 200) blue, ON (255, 134, 22)
# orange; the user's idle screenshot reads a lighter blue on the gun)
HEAT_RAMP = [(0.0, (0.15, 0.5, 1.0)), (0.1, (0.15, 0.5, 1.0)),
             (0.9, (1.0, 134 / 255.0, 22 / 255.0)), (1.0, (1.0, 134 / 255.0, 22 / 255.0))]

PORT = reserved(
    order=25, wave='B7', name='Focus Rifle', source='Halo Reach',
    messages=(83, 84), icon=45, reticle=34, label='fo', teach_from='sr',
    sound_dir='sound\\weapons\\focus_rifle_port', weapon_dir='weapons\\focus rifle',
    yardstick={
        # step 4a (user, 2026-10-12): 'Plasma Rifle, check the H4 port for reference'
        'pick': 'Plasma Rifle',
        'reason': ("the heat + battery Covenant automatic of both games (Reach has one; the sniper "
                   "has no heat, battery or Flood damage, the plasma pistol is tapped). DEFAULT = "
                   "Reach's own numbers at 30/s (3 a round, overheat on the 75th round at "
                   "2.47 s = Reach's ~2.5 s; BOOT 2's probe: Halo 1 fires the tag's 30/s, one heat loss = the MEAN of Reach's 0.35 / 0.23 (user; "
                   "the Beam Rifle's precedent): 0.29, a 3.1 s vent; Reach 3.9 s). BALANCED = the "
                   "plasma-rifle ratio. Materials (user, the Plasma Repeater's rule): the H1 plasma "
                   "rifle bolt's table in DEFAULT, x Reach's plasma_fast / plasma_slow per armour "
                   "class in BALANCED. The Halo 4 port of the same weapon (reference): Reach's own "
                   "values, heat + battery as the port's own, heat cards from the Sentinel Beam "
                   "(card_donors), ammo cards skipped"),
        # DEFAULT = Reach's own (above); these are the BALANCED rows (H1 plasma rifle x Reach focus
        # rifle / Reach plasma rifle). Reach plasma rifle: 10 plasma_slow x 6 -> 9/s (ramp 0.8 s),
        # heat 0.15 a round, loss 0.8525 / 0.35 overheated, recovery 0.1, battery 0.0025, 25 wu/s,
        # range 40, aim 5/12 9/18. H1 plasma rifle 12-14 (13) x 7 -> 10/s, heat 0.08, loss 0.3,
        # recovery 0.25, battery 0.005, 50 -> 25 wu/s, no range, aim 5/25 12/25
        'balanced': {
            'damage': 4.33,              # dps 13 x 10 = 130 x FR 90 / Reach PR 90 -> / 30/s (boot 2: 8.67 at 15/s)
            'rate': (30.0, 30.0),        # 10 x 30/9 = 33 -> Halo 1's one round a tick (damage keeps the dps)
            'overheat_s': 3.0,           # TIME TO OVERHEAT (both games cool while firing): H1 PR
                                         # 2.67 s x FR 2.47 / Reach PR 2.17 (19 rounds) -> the 46th round
            'heat_per_round': 0.0175,    # fitted at 30/s with the loss below (the 91st round at 3.0 s)
            'loss': 0.197,               # 0.3 (= the OVERHEATED loss, the Beam Rifle's reading) x 0.23/0.35
            'recovery': 0.25,            # 0.25 x 0.1/0.1 (vent 1 -> 0.25 at 0.197 = 3.8 s)
            'battery': 1 / 280.0,        # by TIME: H1 PR 20 s x FR 20.7 / Reach PR 44.4 = 9.3 s -> 280 rounds at 30/s
            'velocity': 8000.0,          # 50 x 4000/25 -- see 4b (overpenetration: the laser's 1000)
            'range': 120.0,              # the H1 plasma rifle bolt has none: a zero on one side, Reach's
            'aim': (2.0, 20.83, 5.33, 13.89),  # 5 x 2/5, 25 x 10/12; 12 x 4/9, 25 x 10/18
            'zoom': None,                # the plasma rifle has none: Reach's 2 levels 3.5 / 9.5 kept
            'materials': 'x plasma_fast / plasma_slow (RP_FAST_SLOW in h1_role_compare)',
            'melee': None},              # Reach shares strike_melee: x1 = the plasma rifle's own
        'measured': 'h1_role_compare.py focus_rifle (rows "FR = Reach B, loss .29" and "FR = PR ratio")',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Sniper Rifle', 'Plasma Pistol'],
            'direct': None,
            'peers': ['Sniper Rifle', 'Sentinel Beam'],
            'why': "continuous instant beam, heat + battery (the H1 Sentinel Beam's model, but Reach has no Sentinel Beam)",
            'lacks': "Reach's 30 rounds a second (Halo 1: 15, per-second values kept); its TWO heat "
                     "losses (Halo 1: one, the mean); a beam drawn as one continuous ribbon (Halo 1: "
                     "a contrail a round)"}},
    # step 11: Reach's ai\generic Focus Rifle entry (m10, verified) over a base -- 'fo' has no carrier.
    # Halo 1's PLASMA RIFLE carriers (h1_weapon_carriers, 2026-10-13): Elite minor / major / stealth
    # 0.5, commander / spec-ops 0.6, Flood combat (both) 0.4, Marines 0.5, armoured Marines 0.6; no
    # actor flags. The yardstick's own carrier = the ELITE MINOR plasma rifle for every slot (the
    # repeater's choice). WDM RULE: 0.5 x plasma rifle 130 / the port's dps (5b, the built port:
    # default 3 x 30 = 90, balanced 4.33 x 30 = 130)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map',
                    'from_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
                    'donor_weapon': 'weapons\\plasma rifle\\plasma rifle',
                    'donor_variant': 'characters\\elite\\elite minor\\elite minor plasma rifle',
                    'wdm_rule': {'base': 0.5, 'yardstick_dps': 130.0, 'port_dps': 90.0,
                                 'balanced_port_dps': 130.0},
                    # THE BALANCED DROP RULE: Reach's m10 (the shipped map) focus rifle 0.375-0.475,
                    # its plasma rifle 0.35-0.45 (the repeater's read); the H1 plasma rifle carriers
                    # 0.7-0.9 -> 0.7 x 0.375/0.35, 0.9 x 0.475/0.45
                    'balanced_set': ['0x1D8=0.75:Drop Weapon Loaded', '0x1DC=0.95:Drop Weapon Loaded Max']},
)

PORT.update({
    # DONE 2026-10-13: 13 boots on b30 (parallel with B5) + the Armed boot; the ten-map rebuild is
    # BATCHED for wave B (user's go). CLOSE-OUT RECORD:
    # STEP 4a: yardstick the Plasma Rifle (user); Reach cools while firing (user's stopwatch ~2.5 s);
    #   the PROBE (boot 2): Halo 1 fires the 29..30 tag at 30/s -> Reach's own per-round values;
    #   default heat 0.0229 / one loss 0.29 (the mean) -> 2.47 s; balanced = the plasma-rifle ratio by
    #   time to overheat (4.33, 0.0175 / 0.197 / 0.25, battery 1/280); materials bolt table / x fast-slow.
    # STEP 4b (port_field_audit --port focus_rifle, final): weapon list 2 = the rate (one round a tick)
    #   and the hum's 0.05 / 0.1 ramp; camo ding, illumination recovery, noise 'shout', type
    #   'undefined', deviation 1 written. List 5 (29) = every line a decision here: B in heat + function 2
    #   (the display ramp), the hum wiring, Reach's heat / zoom / age, the FP offset, the dropped
    #   attachments. Projectile list 2: Reach's own damage ranges; velocity 1200 (the Sentinel beam's,
    #   proven; Reach's 4000 and the ratio's 8000 cross the range in one tick: no overpenetration, the
    #   Spartan Laser's finding); responses = Reach's (overpenetrate flesh / glass / liquid / plants).
    #   Damage: camo damage 0.048, instantaneous acceleration 0.1.
    #   FINAL CHECK (user: 'every step, especially 4b'): list 3 line by line -- error deceleration 0.3
    #   written; detonation timer starts (Reach 'after first bounce') inert: the beam's timer is 0 (the
    #   bolt's too); projectile flags (Reach damage_not_predictable_by_clients: multiplayer) none either
    #   side; weapon / trigger flags by NAME = the template's (cannot fire at maximum age; Reach's
    #   "don't clear fire bit" has no Halo 1 field); block-count lines = the battery weapon (no
    #   magazine) and the projectile's own attachments (the contrail); deviation 1, noise, type written.
    #   Projectile list 5: the bolt's function + second attachment absent (the Sentinel beam copy has
    #   one contrail). Age rate-of-fire penalty 0 in BOTH versions (Reach's, both sides of the ratio;
    #   the 30/s fit needs it -- no row or card touches it).
    #   REPRODUCIBLE: port_sha_snapshot before / after a full regen of the chain from this config
    #   (model, retarget + tool animations, sounds, pickable): 5 changed + 16 bitmap headers -- the FP
    #   antr content-equal (h1_antr_diff: 0 animations differ, sound references same) and four FP-cue
    #   sound tags whose ogg_sample_count `tool sounds` writes 128 samples apart (the bank sources MCC
    #   plays unchanged); two further regens byte-identical.
    # TEMPLATE DIFF (h1_port_template_diff, final): weapon 70, HUD 18 (reticle 34, icon 45, the scope
    #   screen effect), the gun shaders 2 each, the three lit shapes; display / indicator / illum_plasma
    #   shader_models MISSING by design (the lit-shape chicagos take those materials).
    # Closing checks: 0 port_refs_audit 0 problems (the boot-13 test copy: own beam + damage + melee);
    #   2 validate_halo_json 0 problems; 4 port_backup h1; 5 n/a (Halo 1: the bank manifest); 6 = 4b;
    #   7 port_sound_refs OWN only (hum, drop, zooms, dry), the FP-animation / flyby / impact sounds own
    #   (by hand), port_sounds --check 0; 8 the Armed boot: Grunt / Jackal / Elite from the Elite minor
    #   plasma rifle + Reach's profile, WDM 0.722 / 0.5, Grunts x0.5, Jackals shieldless, balanced drop
    #   0.75-0.95; 9 the shield hit: material #22 has NO response effect on this beam (nothing to thin;
    #   h1_hit_effect_load: 0 load); 10 the muzzle flash: one orange sprite at the bore vs Reach's 1p
    #   flash (recorded at fire_effect).
    # THE LOOK: Reach's scope fitted to the user's screenshot; crosshair #22 supersampled; the display
    #   tiles a heat ramp; THE BEAM: one contrail 0.2 wu, a white-orange centre + blue-violet bands
    #   (components), a knot map sliding on game time (contrail secondary map: the contrail's own u
    #   scroll drew static). Recipe applied to the Spartan Laser (user, 57b5e67).
    # Not reproduced: Reach's two heat losses (one, the mean), the meter filling tile by tile (one ramp),
    #   the distortion ring and spark embers of the muzzle, the 3p plasma beam, a second contrail layer
    #   with its own animation (did not draw), Reach's 4000 wu/s.
    'status': 'done',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for world
    # AND first person. focus_rifle.render_model: 14 nodes -- b_gun (root, identity: not tilted),
    # the charge cylinder / outer charges, barrel top / bottom (+01), the arm joints 01-03; 1 mesh,
    # 16 parts; ONE primary_trigger (identity, 0.371 / 0.004 / 0.039), fx_vent x2 (the overheat
    # vents, either side), left_hand. Materials (shader templates = the option indices):
    # focus_rifle_metal / _rubber / _shell (diffuse; metal and rubber NAME an illum map --
    # battle_rifle_illum / sniper_rifle_scope_illum -- but self-illum option 0 = off), _display
    # (_2_0_0_0_4_0_6_1: a METER, illum plasma_pistol_display + meter plasma_launcher_holo,
    # additive), _display2 (option 3, additive: plasma_launcher_holo), _illum_plasma (a halogram:
    # plasma_clouds noise through phantom_illum, palette soft_plasma_blue), _indicator (halogram,
    # plasma_launcher_holo x data_stream), _scope_alpha (black glass, 'calculate Z camera')
    'model': {
        'dir': r'weapons\focus rifle',
        'world': R + RW + r'\focus_rifle.render_model',
        'fp': R + RW + r'\focus_rifle.render_model',
        'world_name': 'focus rifle',
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent', 'primary_trigger': 'primary trigger'},
        'ground_point': 'auto',
        'shaders': {'focus_rifle_metal': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_rubber': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_shell': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_display': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_display2': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_illum_plasma': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None),
                    'focus_rifle_indicator': (R + RW + r'\bitmaps\focus_rifle_diffuse.bitmap', None)},
        # the scope's black glass (a Reach halogram, no Halo 1 equivalent; the DMR's glass rule)
        'drop_materials': ('focus_rifle_scope_alpha',),
        'template': PR + r'fp\shaders\gun',
        'glow': {},
        # GLOW (fp_material_view --illum --texels 24, threshold 16, BEFORE choosing): the display
        # (the readout in the scope housing: 99 of 248 triangles on plasma_launcher_holo's lit
        # texels), the indicator (the scope window + two spots: 36 of 97), the plasma strip down the
        # left side (208 of 236 on phantom_illum, its alpha mask); display2 has no triangles. Reach's
        # colours (reach_function_data): display meter ON (255, 134, 22) orange / OFF (0, 69, 200)
        # blue, intensity 0.5..1; indicator self_illum (17, 134, 247) blue; the plasma halogram
        # through soft_plasma_blue (peak 67, 69, 216), color_medium (27, 53, 90). Boot 1: the
        # Needle Rifle's / repeater's STATIC lit shapes (additive chicago, function-free -- every
        # Halo 1 weapon out reads 0 until the first shot), Reach's colours; to judge against the
        # user's Reach screenshot (a heat-driven display = the repeater's ramp, if Reach's is)
        # BOOT 1 (user): 'glow tiles looking pretty good -- they are a heat tracking meter as well'
        # (the user's Reach screenshots: idle blue, overheated orange; the display IS Reach's meter
        # by heat, OFF blue / ON orange) -> the DISPLAY = the repeater's backup recipe ('remember this
        # setup'): the lit shape white x a colour RAMP slid by the heat out (C out = function 2 = 'one'
        # x B in heat, the pickable rewire), blue cold -> orange hot. Not reproduced: Reach fills the
        # meter by PLACE (tile by tile); here every tile turns together, and the colour follows the heat
        # back down through the vent
        'meters': {
            'focus_rifle_display': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous', 'color': (1.0, 1.0, 1.0),
                'ramp': HEAT_RAMP, 'ramp_source': 'C_out'},
            'focus_rifle_indicator': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (0.5 * 17 / 255.0, 0.5 * 134 / 255.0, 0.5 * 247 / 255.0)},
            'focus_rifle_illum_plasma': {
                'map': R + r'objects\vehicles\covenant\phantom\bitmaps\phantom_illum.bitmap',
                'from': PR + r'fp\shaders\gauge', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (67 / 255.0, 69 / 255.0, 216 / 255.0)}},
        # THE BEAM'S LOOK (boot 2): Reach's FIRST-PERSON beam (fx\projectile_1p.beam_system) = a
        # `center` aligned ribbon on energy_trail + a 12-sided `pulse` tube, BOTH through the palette
        # `sentinel_beam` (missing from HREK; Halo 3's fx\contrails\_gradients\sentinel_beam: black ->
        # gold -> white -- the user's firing screenshot: a white-gold core); the violet is the 3p beam's
        # plasma layers and the muzzle particles. Baked (the Spartan Laser's route): colour =
        # palette[profile], premultiplied for the additive contrail
        # BOOT 3 (user): 'the beam is a static image -- can we animate it?' The core's energy_trail
        # barely varies along u (column-mean spread 4), so the contrail's scroll shows nothing; Reach's
        # MOTION is the `pulse` layer (512 x 64, spread 32: bright knots along the beam) scrolled
        # -5 / s at tiling 0.15 -> baked at its own length (`size` (w, h)) through the same palette
        # BOOT 8 (user, the h1_beam_variant test on the secondary: 'the secondary beam MOVES now --
        # apply it; I like the darker shade'): the core in REACH'S COLOURS from the user's firing
        # screenshot (white-hot centre, warm orange-peach edges; colour stops instead of the gold
        # sentinel_beam palette) and an outer violet layer, each MODULATED by a greyscale knot map
        # (Reach's pulse, floor 0.35 / 0.25) sliding along the beam on GAME time (pickable contrail
        # `secondary`, function slide, 0.4 / 0.3 s)
        # BOOTS 9-12 (user: 'none of them show blue, violet or purple'): an ADDED contrail layer on the
        # beam did not draw once it carried a secondary map (boot 11's diagnostic: the core's own
        # texture drew violet at once) -> the violet FOLDED INTO THE CORE (boot 12, user: 'looks
        # right now, apply it'): one texture = a narrow white-orange centre (energy_trail ^ 2.2) +
        # blue-violet bands outside it (energy_trail ^ 0.45, hollow stops, gain 1.6), the core 0.2 wu
        'baked_textures': {'fo_beam': {'components': [
                               {'profile': R + r'fx\bitmaps\contrails\energy_trail.bitmap', 'power': 2.2,
                                'stops': [(0.0, (0, 0, 0)), (0.3, (170, 55, 15)), (0.6, (255, 140, 60)),
                                          (0.85, (255, 215, 175)), (1.0, (255, 255, 255))]},
                               {'profile': R + r'fx\bitmaps\contrails\energy_trail.bitmap', 'power': 0.45,
                                'stops': [(0.0, (0, 0, 0)), (0.2, (70, 40, 255)), (0.55, (110, 80, 255)),
                                          (0.8, (40, 25, 140)), (1.0, (0, 0, 0))], 'gain': 1.6}]},
                           'fo_beam_sec': {'profile': R + r'fx\bitmaps\contrails\pulse.bitmap',
                                           'size': (512, 64), 'grey': 0.35}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's OWN fp_focus_rifle retargeted (the DMR's
    # recipe). fp_focus_rifle (reach_tags --pose, 61 nodes): idle 100, posing var1 / var2 89, ready
    # 22 (ready_initial 29, ready_overheated 22), put_away 6, fire_1 19, melee_strike_1 36 (primary
    # 5; _overheated 36), throw_grenade 44 (primary 8), throw_overheated 44, moving 20, look 9;
    # THE OVERHEAT: overheating 56 / overheated 59 / o_h_exit 38 = Halo 1's own three states (the
    # plasma rifle template's). Not reproduced: the overlays barrel (1), barrel_vibration (5),
    # fire_vibration (5), fire_buildup (90), fire_push_back (1), acceleration_screens (9) -- driven by
    # weapon functions Halo 1's graph has no slot for; crouch / jump / fall / land, sprint
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\focus_rifle.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in (
            'b_gun', 'b_outercharge_right', 'b_upper_armjoint01', 'b_barrel_top',
            'b_innercharge_cylinder', 'b_outercharge_left', 'b_barrel_bottom', 'b_lower_armjoint01',
            'b_upper_armjoint02', 'b_lower_armjoint02', 'b_barrel_bottom01', 'b_barrel_top01',
            'b_lower_armjoint03', 'b_upper_armjoint03')},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\focus rifle\fp',
        'h1_model': r'weapons\focus rifle\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1; the repeater's start too)
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
            'first_person:overheating': 'first-person overheating',
            'first_person:overheated': 'first-person overheated',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
    },

    # Reach's own sounds (h1_port_sounds.py focus_rifle, Reach's sfx.fsb). Levels = the active RMS of
    # the stock Halo 1 PLASMA RIFLE sound each stands in for (the template's; the repeater's
    # h1_stock_sound_levels readings, 2026-10-11): fire -9.3, overheat / dry -20.9, melee -11.4,
    # oh_exit -20.0, overheating -26.7, posing -30.5, ready -21.2, drop (plasma_impact) -18.7, flyby
    # (plasrif_projectile) -26.2, impact (plasmahit) -11.3; the hum -16 (the Sentinel Beam's loop,
    # same stand-in), zooms = the sniper's -28.9 / -29.2 (the Beam Rifle's). Reach's cues: the
    # weapon's attachments play focus_rifle_fire (in / loop / out, on primary_firing) + the FP layer
    # focus_rifle_firing_loop (in, a SILENT loop, out) + the tails; fr_overheat (in + loop, on
    # overheated); the FP graph: overheating -> fp_focus_rifle_overheating, o_h_exit ->
    # focus_rifle_oh_exit, ready, posing 1, melee; the projectile: focus_beam_flyby, the material
    # effects: focus_beam_impact, the drop: flak_cannon_drop; the empty effect beam_rifle_misfire;
    # zoom = the beam rifle's zoom in / out (Reach's weapon names them)
    'sounds': {
        'catalog': 'Focus Rifle',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'focus_rifle_port']),
        'h3_dir': RS + 'focus_rifle\\',
        'sounds': {
            # THE HUM (the Sentinel Beam's recipe): a sound_looping on the trigger's rate of fire;
            # start = the 3p fire in + the FP layer's in, loop = the fire loop, end = the fire out +
            # the FP out + the exterior tail
            'fo_fire_in': (['focus_rifle_fire\\focus_rifle_fire\\in', 'focus_rifle_fp\\focus_rifle_firing_loop\\track1\\in'],
                           'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_fire_loop': (['focus_rifle_fire\\focus_rifle_fire\\loop'], 'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_fire_out': (['focus_rifle_fire\\focus_rifle_fire\\out', 'focus_rifle_fp\\focus_rifle_firing_loop\\track1\\out',
                             'focus_rifle_tails_ext\\fr_tails_ext\\out'],
                            'sound\\sfx\\weapons\\plasma rifle\\fire', -16.0),
            'fo_dryfire': ([RS + 'beam_rifle\\beam_rifle_misfire'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -20.9),
            'fo_ready': (['focus_rifle_fp\\focus_rifle_ready'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_ready', -21.2),
            'fo_melee': (['focus_rifle_fp\\focus_rifle_melee'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_melee', -11.4),
            'fo_pose': (['focus_rifle_fp\\focus_rifle_posing1'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_posing', -30.5),
            # THE OVERHEAT (Halo 1's three states): the FP overheating cue + fr_overheat's in mixed,
            # its loop on `overheated`, the exit cue on o-h-exit
            'fo_overheat': (['focus_rifle_fp\\focus_rifle_overheating', 'fr_overheat\\fr_overheat\\in'],
                            'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'fo_overheat_loop': (['fr_overheat\\fr_overheat\\loop'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'fo_oh_exit': (['focus_rifle_fp\\focus_rifle_oh_exit'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_oh_exit', -20.0),
            'fo_zoom_in': ([RS + 'beam_rifle\\beam_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'fo_zoom_out': ([RS + 'beam_rifle\\beam_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'fo_drop': ([RS + 'flak_cannon\\flak_cannon_drop'], 'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            # the beam's own FLYBY (port_sound_refs does not read projectile sound fields: by hand)
            'fo_flyby': (['focus_beam_flyby\\single'], 'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            'fo_impact': (['focus_beam_impact'], 'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
        },
        # Halo 1 finishes a loop pass before the end track (the Sentinel Beam: 0.5 s)
        'loop_len': {'fo_fire_loop': 0.5},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only focus_rifle) on a COPY of the Halo 1 PLASMA RIFLE
    # (the yardstick = the template: heat + battery HUD, overheat states) wired as the SENTINEL
    # BEAM (sentinel_beam.py, a continuous beam on the same template, 12 boots): the hum, the own
    # firing effect, the beam projectile. DEFAULT = REACH'S OWN NUMBERS at 30/s (the
    # yardstick block); the ratio values are the balance rows. Template layout after the
    # Sentinel Beam's rewire: inputs A primary firing / B illumination / C rate of fire / D age;
    # function 0 = the hum (C in, off with 1), 1 = primary firing (A in, off with 3), 3 = age
    'pickable': {
        'weapon': FO + 'focus rifle',
        'template': PR + 'plasma rifle',
        'world_model': FO + 'focus rifle',
        # ONE model tag for world AND first person (user, 2026-10-14): Halo 1's map builder crashes
        # past 32 MiB of model vertices + indices (memory h1-model-buffer-32mib-cap); the world and
        # fp gbxmodels are the same geometry (only the permutation name differs), so the weapon
        # names the world tag twice and the map stores it once (-1.21 MB). fp\fp.gbxmodel is still
        # written by the model step for the FP tools (fp_render, h1_fp_muzzle, h1_fp_hand_clip)
        'fp_model': FO + 'focus rifle',
        'fp_anims': FO + 'fp\\fp',
        'label': 'fo',
        'teach': ('fo', 'sr'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'fo_ready',
                   'first-person posing': SND + 'fo_pose',
                   'first-person melee': SND + 'fo_melee',
                   'first-person overheating': SND + 'fo_overheat',
                   'first-person overheated': SND + 'fo_overheat_loop',
                   'first-person o-h-exit': SND + 'fo_oh_exit'},
        # BOOT 2: input B = HEAT (was illumination: it only scaled the muzzle-light attachment, whose
        # light the firing effect already carries per shot -- the Beam Rifle's test 3: an attachment
        # light stays lit) -> function 2 = 'one' x B in = the heat out C, the display tiles' ramp
        'rewire': {'inputs': ('primary_firing', 'heat', 'primary_rate_of_fire', 'age'),
                   'functions': {0: (2, 'C_in', 'fire loop', {'turn_off_with': 1}),
                                 1: (2, 'A_in', 'primary firing', {'turn_off_with': 3}),
                                 2: (2, 'B_in', 'heat')},
                   'drop_attachments_on': ('B_out',)},
        # the muzzle-light attachment (index 0 after the rewire; it would now follow the heat)
        'drop_attachments': [0],
        'fire_loop': {'tag': SND + 'fo_fire', 'like': r'sound\sfx\weapons\flamethrower\fire_ft',
                      'start': SND + 'fo_fire_in', 'loop': SND + 'fo_fire_loop',
                      'end': SND + 'fo_fire_out', 'marker': 'primary trigger',
                      'scale': 'A_out'},
        # THE FIRING EFFECT (the Sentinel Beam's): the plasma rifle's one flash sprite (additive
        # sprites saturate at 15/s), no sound (the hum), the muzzle light as a part. REACH'S FOCUS
        # RIFLE MUZZLE IS ORANGE (the H4 kit: its particle tints (255, 98, 42) -> (255, 92, 0),
        # sparks (255, 200, 72) -> (238, 83, 31); the firing light blue-violet)
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1; h1_effect_particles): Reach's
        # FIRST-PERSON flash (fx\firing.effect, 'only in first person', all at primary_trigger, no
        # offsets): flash_large (emitter bounds 0.106 wu), muzzle_flash_plasma (0.108, 'render when
        # zoomed'), distortion_ring (0.229: a refraction ring, no Halo 1 equivalent), spark_ember
        # (0.51: physics sparks, orange) + the 1p beam and the blue-violet firing light. Ours: ONE
        # `flash c generic` 0.06-0.075 wu at the bore, first person only (the plasma rifle's other
        # five sprites dropped: additive sprites saturate to white at 15/s, the Sentinel Beam's
        # finding) -- within Reach's size; the sparks and the ring not reproduced (judge in game)
        'fire_effect': {'from': PR + 'effects\\plasma rifle upper fire',
                        'out': FO + 'effects\\fire', 'sound': '', 'light': FO + 'muzzle light',
                        'keep_particles': 'flash c generic', 'tint': (1.0, 1.0, 0.38, 0.16)},
        # the `c generic` particles take the WEAPON's change colour A (the Sentinel Beam's test 6)
        'change_color_a': ((1.0, 0.38, 0.16), (1.0, 0.36, 0.0)),
        'own_light': {'shape': PR + 'muzzle flash', 'look': PR + 'muzzle flash',
                      'out': FO + 'muzzle light', 'argb': (1.0, 1.0, 0.38, 0.16), 'duration': 0.1,
                      'no_flare': True},
        # the template's overheat steam aims at its `vent` (Reach's fx_vent, mapped in the model)
        'overheated_effect': {'from': PR + 'effects\\overheated', 'out': FO + 'effects\\overheated',
                              'locations': {}},
        'attach_swap': {PR + 'muzzle flash': FO + 'muzzle light'},
        'attach_markers': {'secondary trigger': 'primary trigger', 'heat flare': 'vent',
                           'heat flare1': 'vent'},
        'fields': {
            # the dead-battery click: the plasma rifle's empty is a SOUND reference
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'fo_dryfire',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'fo_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'fo_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'fo_drop',
            # Reach's focus rifle: no age penalties, no misfire (its age block is all 0; only
            # 'cannot fire at maximum age') -- the template's rate -20 % / heat +20 % at an empty
            # battery stopped the repeater overheating; misfire 0.9 / 0.5 off with its effect
            'weap_attrs.age.heat_penalty': 0.0,
            'weap_attrs.age.rate_of_fire_penalty': 0.0,
            'weap_attrs.age.misfire_start': 0.0,
            'weap_attrs.age.misfire_chance': 0.0,
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.triggers.0.firing_effects.1.misfire_effect.filepath': '',
            # STEP 4b (before boot 1). List 2 (the ratio vs Reach's plasma rifle onto the H1 plasma
            # rifle): camo ding 0.3 x 1/0.4, illumination recovery 0.15 x 0.1/0.03. List 3: firing
            # noise Reach's 'shout' (the plasma rifle 'loud'), weapon type Reach's 'undefined' (the
            # plasma rifle's 'plasma rifle'), deviation angle 1 deg (a zero on one side: the source
            # value, the DMR's / Needle Rifle's way)
            'weap_attrs.interface.active_camo_ding': 0.75,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.5,
            'weap_attrs.triggers.0.firing.firing_noise': 'shout',
            'weap_attrs.weapon_type': 'undefined',
        },
        'melee': (PR + 'melee', FO + 'melee'),
        'melee_response': PR + 'melee_response',
        'messages': ('Picked up a focus rifle', 'Picked up %d rounds for focus rifle'),
        'icon': 'focus rifle',
        # the PLASMA RIFLE's HUD (heat + battery meters) with Reach's reticle (ui\chud\focus_rifle:
        # hud_reticles 22, the H4 kit's reading -- recheck with the user's screenshot), the
        # sniper's zoom screen effect; THE SCOPE (h1_h3_scope, Reach's chud) waits for the user's
        # Reach screenshot (`--fit`)
        'hud': {'donor': PR + 'plasma rifle', 'out': FO + 'focus rifle',
                'screen_effect_from': r'weapons\sniper rifle\sniper rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                # Reach's chud (h1_h3_scope reach:ui\chud\focus_rifle): scope_mask (beam_rifle_scope,
                # 4 copies), meter_border (4), meter_heat / meter_batt (meter fills), the low-battery
                # and overheat flashes. The Beam Rifle's decisions (user, A4): the frame baked, the
                # fills (garbage as a mask) and the flashes (hidden until a warning) dropped -- the
                # Halo 1 HUD's own heat / battery meters show while zoomed. SIZE from the user's Reach
                # screenshot (1080p, zoom 1): the lens 1293 x 707 px (x 313-1606, y 186-893 on the
                # centre row / column) -> `h1_h3_scope.py reach:ui\chud\focus_rifle --port focus_rifle
                # --fit 1293,707` = span 931.1, aspect 1.2506 (re-bake: 1293 x 713)
                'scope': {'chud': R + r'ui\chud\focus_rifle', 'out': FO + 'bitmaps\\scope_mask',
                          'size': 1024, 'span': 931.1, 'aspect': 1.2506, 'alpha': 'outside',
                          'per_widget': {'lowbatt_flash_scope': {'drop': True},
                                         'meter_heat': {'drop': True},
                                         'meter_batt': {'drop': True},
                                         'meter_lowbatt_flash_left': {'drop': True},
                                         'meter_overheat_flash_right': {'drop': True}}},
                # THE CROSSHAIR (the supersample recipe, memory h1-reticle-supersample): Reach's
                # hud_reticles #22 (three arcs; matches the user's screenshot), ~55 px wide at 1080p
                # (Halo 3 density 93 px); x2 supersampled. The cell art = 93 x h1_add_reticle.SCALE
                # (1.268, its Halo 3 -> Halo 1 calibration) x scale x 2: scale 2.0 -> 472 of the 512
                # cell (~20 px margin; 2.4 overflowed it); on-screen = sheet px x 0.75 x overlay ->
                # overlay 55 / (472 x 0.75)
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 22, 'focus rifle'),
                'reticle_scale': 2.0, 'reticle_overlay': 55 / (93 * 123.0 / 97.0 * 2.0 * 2 * 0.75),
                'reticle_supersample': 2,
                'reticle_min_width': 2},
        'aiming': {'autoaim_angle': 2.0, 'autoaim_range': 10.0,
                   'magnetism_angle': 4.0, 'magnetism_range': 10.0,
                   'zoom_levels': 2, 'zoom_ranges': (3.5, 9.5),
                   'deviation_angle': 1.0},           # 4b list 3 (degrees here)
        # THE BEAM (the Sentinel Beam's): a copy of Halo 1's Sentinel beam projectile (its contrail
        # = a continuous beam, the look Reach's 1p beam shares: energy_trail through the
        # sentinel_beam palette, black -> gold -> white -- the bake waits for the user's
        # screenshot), Reach's 120 wu range; the damage a copy of the plasma rifle BOLT (the
        # yardstick's table = the DEFAULT materials, user), Reach's 3 a round at 30/s (boot 2's probe),
        # instantaneous acceleration 0.1 (Reach's). Speed: the Sentinel beam's own 1200 wu/s (proven
        # visible from the FP muzzle); Reach 4000 crosses the whole range in one tick (the Spartan
        # Laser: no overpenetration at that speed) -- 4b decides the responses
        # STEP 4b (before boot 1): the damage effect's camo damage 0.12 x 0.1/0.25 (list 2); breaking
        # effect (list 3: Reach 0, its plasma rifle 3 / 0.5 / 0.2) = the bolt's 0. The projectile:
        # air / water damage range Reach's own 0..120 / 0..20 (no falloff: lower = upper damage);
        # impact / detonation noise Reach's 'loud' (list 3, enums); water gravity 0 (Reach's).
        # RESPONSES: the Halo 1 Sentinel beam overpenetrates every unit body and reflects off Jackal
        # shields; Reach's focus_rifle_beam overpenetrates glass, liquid, plants and 'tough_organic'
        # UNITS EXCEPT GIANTS, detonates on the rest (Elite bodies are hard_metal_thin, armour
        # tough_inorganic) and never reflects -> overpenetrate glass 9, grunt 11, jackal 15,
        # engineer 17, flood 19 / 20, human skin 24, water 28, leaves 29; the hunter skin 13, elite
        # 14, Jackal shield 16, cyborg / human armour 21 / 23, plastic 27 stop it ('disappear', the
        # Sentinel beam's own stop, with its impact effects). The shields' potential 'reflect' (0..180
        # deg, the Sentinel beam's) kept: an OBSERVATION to check in game (no velocity window)
        'beam': {'projectile': (r'characters\sentinel\beam', FO + 'beam'),
                 'damage': (PR + 'bolt', FO + 'beam'),
                 'range': 120.0, 'dmg': 3.0, 'acceleration': 0.1,
                 'fields': {'damage.active_camouflage_damage': 0.048},
                 'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'fo_flyby',
                                 'proj_attrs.physics.air_damage_range': (0.0, 120.0),
                                 'proj_attrs.physics.water_damage_range': (0.0, 20.0),
                                 'proj_attrs.physics.water_gravity_scale': 0.0,
                                 'proj_attrs.impact_noise': 'loud',
                                 'proj_attrs.physics.detonation_noise': 'loud'},
                 'default_responses': {'overpenetrate': [9, 11, 15, 17, 19, 20, 24, 28, 29],
                                       'disappear': [13, 14, 16, 21, 23, 27]},
                 # the Sentinel beam's five impact effects play sound\sfx\vehicles\sent_laser_impact
                 # (a BORROW) -> own copies playing Reach's focus_beam_impact (the repeater's sound swap,
                 # no particle match). THE HIT-EFFECT RULE (check 9): material #22 (cyborg energy
                 # shield) has NO response effect on this projectile (default 'disappear', effect
                 # empty; the potential reflect's empty too) -- nothing to thin at 15/s
                 'impact_tint': {'match': (), 'rgb': None, 'out': FO + 'effects\\impact\\',
                                 'sounds': {'sound\\sfx\\vehicles\\sent_laser_impact': SND + 'fo_impact'}},
                 # BOOT 2: an OWN copy of the Sentinel contrail (white x texture, additive, 0.095 wu,
                 # its point states kept) on the baked Reach beam (model `baked_textures` fo_beam)
                 'contrail': {'from': r'characters\sentinel\beam', 'out': FO + 'beam',
                              'bitmap': FO + 'bitmaps\\fo_beam', 'sequence': (0, 0),
                              'secondary': {'bitmap': FO + 'bitmaps\\fo_beam_sec', 'function': 'slide',
                                            'period': 0.4, 'scale': 1.0},
                              # BOOT 12 (user): the core 0.2 wu (x 0.2 / 0.095 on the Sentinel's states)
                              # for the folded-in violet. The extra layers of boots 4-10 (a gold pulse
                              # tube, then violet with its own knot map) are GONE: the added layer drew
                              # in boot 4 (no secondary map) but not from boot 8 on (with one) --
                              # an OBSERVATION from this port; one textured contrail does it all
                              'width': 0.2 / 0.095}},
        # Reach: spew 30/s. BOOT 2 (user: 'overheats in under 2 s'; the PROBE): Halo 1 fires 29..30 at
        # 30/s -- 29 rounds in 0.97 s, shots 33 ms apart, heat 0.045 -> 1.0 (cools while firing at 0.29),
        # vent 3.07 s -- the per-round values doubled for 15/s overheated it at 1 s. Now Reach's own
        # per-round values (the hum needs differing bounds, 29..30),
        # no rate ramp (4b: Reach's 0.3 is the ERROR deceleration -- error 0 here); the rate
        # deceleration 0.1 = the Sentinel Beam's (the hum's tail follows it); heat (1 + 74 / 30 x 0.29) / 75 = 0.0229 a round =
        # the 75th round at 2.47 s with Halo 1 cooling while firing at 0.29 (Reach ~2.5 s, the user's
        # stopwatch); battery Reach's 0.0016125 (620 rounds = 20.7 s)
        # (Reach's 620 x 0.0016125 at 30/s); error 0; every round a tracer; the FP muzzle
        # (h1_fp_muzzle.py, the idle pose: 0.4496 / -0.0643 / -0.0387 wu)
        'trigger': {'rounds_per_second': (29.0, 30.0), 'heat_generated_per_round': 0.0229,
                    'acceleration_time': 0.05, 'deceleration_time': 0.1,
                    'age_generated_per_round': 0.0016125, 'error_angle': (0.0, 0.0),
                    # FINAL CHECK (4b list 3): error deceleration -- Reach 0.3, the H1 plasma rifle 0: a
                    # zero on one side, the source value (inert with error 0; written, the DMR's way)
                    'error_deceleration_time': 0.3,
                    'rounds_between_tracers': 0,
                    # BOOT 1 (user): 'starts roughly at the muzzle -- try moving it back a unit' (1 unit
                    # = 0.01 wu)
                    'first_person_offset': (0.4396, -0.0643, -0.0387),
                    'illumination_recovery_time': 0.5},
        # Reach: overheated at 1, back at 0.1; ONE loss = the mean of 0.35 / 0.23 (user, step 4a)
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.29},
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.0, 0.0)},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py focus_rifle). DEFAULT = Reach's own
    # numbers in the tags (at 30/s); BALANCED = the PLASMA RIFLE ratio (step 4a, user
    # 2026-10-12; yardstick['balanced']). Assembly Halo1 units: angles in degrees, velocity in wu
    # per TICK
    'catalog': {
        'entry': {
            'weapon': 'Focus Rifle', 'source': 'Halo Reach', 'donor': 'Plasma Rifle', 'default_on': False,
            'desc': "Halo Reach's Focus Rifle: its model, first-person animations, sounds, scope and "
                    "numbers. A Covenant beam on heat and battery: hold the trigger for a continuous "
                    "beam; about 2.5 s of fire overheats it, 20 s of fire a battery, 3.5x / 9.5x zoom.",
            'balance_desc': "Measured against the Plasma Rifle, which both games have: 8.7 damage a "
                            "round (the plasma rifle's family, faster on armour and slower on "
                            "shields, as Reach's fast plasma), 3 s of fire before it overheats, a "
                            "3.8 s vent, 9 s of fire a battery and Halo 1-style aim assist.",
            # step 9 (swap, ONE multiplier; no reload: a battery weapon): the H1 plasma rifle's ready
            # 29 fr x Reach focus rifle 22 / Reach plasma rifle 20 = 31.9 over the built ready (23)
            'anims': {'swap': 29 * 22 / 20.0 / 23.0},
            'balance': [
                # damage: dps 130 (H1 PR 13 x 10/s) x 90/90 -> / 30/s = 4.33 (default Reach's 3 at 30/s)
                row('jpt!', FO + 'beam', 'Damage Lower Bound', 4.33, 3.0, 'Beam Damage'),
                row('jpt!', FO + 'beam', 'Damage Upper Bound', 4.33, 3.0, 'Beam Damage'),
                row('jpt!', FO + 'beam', 'Damage Upper Bound Max', 4.33, 3.0, 'Beam Damage'),
                # materials (user): the plasma rifle bolt's table x Reach plasma_fast / plasma_slow per
                # armour class (h1_role_compare RP_FAST_SLOW -- the Plasma Repeater's rows)
                row('jpt!', FO + 'beam', 'Elite Energy Shield', 1.25, 2.0, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Elite', 2.5, 1.0, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Cyborg Energy Shield', 1.25, 2.0, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Cyborg', 1.25, 0.5, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Hunter Armor', 1.0, 0.5, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Jackal Energy Shield', 0.5, 1.0, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Armored Human', 2.0, 1.0, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Metal (Hollow)', 0.625, 0.25, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Metal (Thin)', 0.625, 0.25, 'Beam materials'),
                row('jpt!', FO + 'beam', 'Metal (Thick)', 0.5, 0.25, 'Beam materials'),
                # heat by TIME TO OVERHEAT (both games cool while firing): H1 PR 2.67 s x 2.47 / 2.17
                # = 3.0 s -> the 91st round at 30/s at the loss below (h1_role_compare 'FR = PR ratio')
                row('weap', FO + 'focus rifle', 'Heat Generated Per Round', 0.0175, 0.0229, 'Heat', block='Triggers'),
                # the one loss: 0.3 (the H1 PR's = the overheated loss) x 0.23/0.35; recovery 0.25 x 0.1/0.1
                row('weap', FO + 'focus rifle', 'Heat Loss Per Second', 0.197, 0.29, 'Heat'),
                row('weap', FO + 'focus rifle', 'Heat Recovery Threshold', 0.25, 0.1, 'Heat'),
                # battery by time: H1 PR 20 s x 20.7 / Reach PR 44.4 = 9.3 s -> 280 rounds at 30/s
                row('weap', FO + 'focus rifle', 'Age Generated Per Round', 1 / 280.0, 0.0016125, 'Battery', block='Triggers'),
                # aim: 5 x 2/5 (no row), 25 x 10/12; 12 x 4/9, 25 x 10/18
                row('weap', FO + 'focus rifle', 'Autoaim Range', 20.83, 10.0, 'Autoaim'),
                row('weap', FO + 'focus rifle', 'Magnetism Angle', 5.33, 4.0, 'Magnetism'),
                row('weap', FO + 'focus rifle', 'Magnetism Range', 13.89, 10.0, 'Magnetism'),
                # NO velocity row: the ratio's 50 x 4000/25 = 8000 wu/s crosses the 120 wu range in one
                # tick (the Spartan Laser: no overpenetration at that speed) -- both versions keep the
                # Sentinel beam's 1200; range: the H1 plasma rifle bolt has none (Reach's 120 kept)
            ]},
    },

    # step 4b (port_field_audit.py --port focus_rifle): the source pair (Reach focus rifle vs the
    # yardstick, Reach's plasma rifle) against the target pair (the H1 port vs its template = the
    # yardstick, the H1 plasma rifle)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\focus_rifle.weapon', r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon'),
                   'projectile': (RW + r'\projectiles\focus_rifle_beam.projectile',
                                  r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (RW + r'\projectiles\focus_rifle_beam.damage_effect',
                                     r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.damage_effect')},
        'target': {'weapon': (FO + 'focus rifle.weapon', PR + 'plasma rifle.weapon'),
                   'projectile': (FO + 'beam.projectile', PR + 'bolt.projectile'),
                   'damage_effect': (FO + 'beam.damage_effect', PR + 'bolt.damage_effect')}},

    # the dry test: b30 (the parallel pair's level for B7), a battery weapon spawns charged
    'test': {'level': 'b30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})

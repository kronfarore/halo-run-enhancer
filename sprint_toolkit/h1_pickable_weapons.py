r"""Make Halo 1's enemy-only Energy Sword and Fuel Rod pickable (HCEEK kit tags).

Halo 1 SHIPS both weapons -- the Elites' `weapons\energy sword\energy sword` and the
Grunts' `weapons\fuel rod gun\fuel rod` -- but as enemy-only items: each carries the weapon
flag `detonates_when_dropped` (the sword disperses, the fuel rod blows up 1.75-3 s after
landing), and neither has a first-person model, first-person animations or (the fuel rod)
a HUD. The user's call (2026-10-05): pick up the ORIGINAL weapons, behaviour unchanged --
the fuel rod keeps its 4-round magazine, 1.25 s charge and rod projectile.

What this writes, all idempotent, every stock tag backed up once as <tag>.before_pickable:

  weapon tag     detonates_when_dropped cleared; first-person model + animations named
                 (h1_fp_retarget.py builds those from Halo 3's FP animations); the fuel rod
                 gets its own HUD and its own melee damage (Halo 1: every weapon owns one)
  FP animations  melee key frames (Halo 3's primary_keyframe) and the stock Halo 1 sounds
                 that fit: the Elite's sword swing, the fuel rod's own melee, the PC fuel
                 rod's ready sound. Reload stays silent until the port's own sounds (step 10).
  fuel rod HUD   the PC fuel rod's (`weapons\plasma_cannon`: its crosshair and pickup icon)
                 with the Assault Rifle's magazine readout -- child `ui\hud\master rounds`
                 and a 4-tick meter from ammo_meter.py -- instead of its heat display
  player biped   `characters\cyborg\cyborg` is taught the two labels: `fr` from the PC fuel
                 rod's `pc` (plasmacannon class), `fb` from the oddball's `b` (pistol class).
                 Without the label the third-person pose has no animations (enemy AI in
                 the same case fell back to its default weapon, halo1-enemy-weapon-teaching).

The sword gets no HUD and no trigger -- exactly the oddball's setup (`weapons\ball\ball`:
no HUD interface, no triggers, own melee). Its FP model is its own world model; the
retarget poses that directly (h1_fp_retarget.py, 'same_space').

Maps must be REBUILT afterwards (h1_rebuild_all.py): every change here is a kit tag.

    python h1_pickable_weapons.py            # show what it would do
    python h1_pickable_weapons.py --write
"""
import argparse
import math
import copy
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.hek.defs.wphi import wphi_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.actv import actv_def  # noqa: E402
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402
from reclaimer.hek.defs.ustr import ustr_def  # noqa: E402
import ports_h1  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
BACKUP = '.before_pickable'
CYBORG = r'characters\cyborg\cyborg'

# per weapon: ports_h1/<weapon>.py, section 'pickable' (the energy sword, fuel rod and
# Sentinel Beam carry the full record of what each key does and why). RESERVED holds each
# port's reservations (pickup message pair, icon / reticle sequence, label): a new port
# writes at ITS reserved index, so sessions never collide.
WEAPONS = ports_h1.section('pickable')
RESERVED = {k: p.get('reservations', {}) for k, p in ports_h1.all_ports()}
MESSAGES = r'ui\hud\hud_item_messages'
STOCK_MESSAGES = 47       # entries 0..46 ship with the game; ports append (the SAW is 47/48)
ICONS = r'ui\hud\bitmaps\combined\hud_msg_icons'


def path(rel, ext):
    return os.path.join(TAGS, rel + ext)


def backup(p):
    if os.path.exists(p) and not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)


def save(tag, p, write):
    if write:
        backup(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tag.serialize(filepath=p, temp=False, backup=False)


def icon_sequence(name):
    """hud_msg_icons sequence index of a pickup icon added by add_msg_icon.py."""
    d = bitm_def.build(filepath=path(ICONS, '.bitmap')).data.tagdata
    names = [q.sequence_name for q in d.sequences.STEPTREE]
    if name not in names:
        raise SystemExit('no %r icon in hud_msg_icons -- run add_msg_icon.py first' % name)
    return names.index(name)


def message_index(lines, write, reserved=None):
    """Index of an appended pickup-message PAIR (Halo 1 reads index and index + 1),
    appending it once. Appending never moves an entry (h1_port_messages.py).

    `reserved` (the port's reservation, H1_PORT_PLAN.md): the pair goes at exactly that
    index -- the list is padded with EMPTY lines up to it, and a slot holding other text is
    refused -- so ports written in any order keep their numbers."""
    t = ustr_def.build(filepath=path(MESSAGES, '.unicode_string_list'))
    strs = t.data.tagdata.strings.STEPTREE
    texts = [s.data for s in strs]
    if reserved is not None:
        if reserved < STOCK_MESSAGES:
            raise SystemExit('message %d is a stock line' % reserved)
        have = texts[reserved:reserved + 2]
        if have == list(lines):
            return reserved
        if any(x for x in have):
            raise SystemExit('messages %d/%d hold %r, not %r -- another port\'s reservation?'
                             % (reserved, reserved + 1, have, lines))
        while len(strs) < reserved + 2:
            strs.append()
            strs[-1].data = ''
        for k, line in enumerate(lines):
            strs[reserved + k].data = line
        save(t, path(MESSAGES, '.unicode_string_list'), write)
        return reserved
    for i in range(STOCK_MESSAGES, len(texts) - 1):     # never a stock line: MCC overrides those
        if texts[i] == lines[0] and texts[i + 1] == lines[1]:
            return i
    i = len(strs)
    for line in lines:
        strs.append()
        strs[-1].data = line
    save(t, path(MESSAGES, '.unicode_string_list'), write)
    return i


def make_hud(w, key, write):
    """The weapon's own HUD interface, from the donor named in its 'hud' entry."""
    h = w['hud']
    t = wphi_def.build(filepath=path(h['donor'], '.weapon_hud_interface'))
    d = t.data.tagdata
    if 'meter' in h:                     # fuel rod: magazine readout in the RL's frame
        import ammo_meter
        import h1_rocket_meter
        mag = 4
        ro = wphi_def.build(filepath=path(h['readout'], '.weapon_hud_interface')).data.tagdata
        d.child_hud.filepath = ro.child_hud.filepath              # master plasma -> rounds
        for name, field, suffix in (('static_elements', 'interface_bitmap', '_alphas'),
                                    ('meter_elements', 'meter_bitmap', '_meters')):
            dst = getattr(d, name).STEPTREE
            dst[:] = []
            for e in getattr(ro, name).STEPTREE:
                if e.state_attached_to.enum_name != 'loaded_ammo':
                    continue
                e = copy.deepcopy(e)
                getattr(e, field).filepath = h['meter'] + suffix
                e.sequence_index = h1_rocket_meter.SEQ
                if name == 'meter_elements':             # ammo_meter.plan: see saw_weapon
                    e.alpha_multiplier = ammo_meter.plan(mag)[3]
                    e.alpha_bias = 1
                    e.value_scale = 0
                dst.append(e)
        fc = d.flash_cutoffs
        fc.heat_cutoff = 0
        fc.loaded_ammo_cutoff = 1
        fc.total_ammo_cutoff = 4
        if write:
            h1_rocket_meter.build(mag, h['meter'], h.get('art', 'rockets'))
    if 'ammo_meter' in h:                # a MAGAZINE gun's tick readout (the SAW's recipe)
        # ammo_meter.py draws one sheet sequence per magazine size: sequence 0 = the
        # weapon's own (default) magazine, the next = its balanced one (balance rows select
        # it, as the SAW's). The AR's two loaded-ammo elements point at sequence 0.
        import ammo_meter
        sizes, base = h['ammo_meter']['sizes'], h['ammo_meter']['base']
        for name, field, suffix in (('static_elements', 'interface_bitmap', '_alphas'),
                                    ('meter_elements', 'meter_bitmap', '_meters')):
            for e in getattr(d, name).STEPTREE:
                if e.state_attached_to.enum_name != 'loaded_ammo':
                    continue
                getattr(e, field).filepath = base + suffix
                e.sequence_index = 0
                if name == 'meter_elements':
                    e.alpha_multiplier = ammo_meter.step(sizes[0])
                    e.alpha_bias = 1             # the comparison is strict (saw_weapon.py)
                    e.value_scale = 0
        fc = d.flash_cutoffs                  # low-ammo flash: the donor's (AR: 10 of 60)
        fc.loaded_ammo_cutoff = round(fc.loaded_ammo_cutoff * sizes[0] / float(h.get('flash_base', 60)))
        if write:
            ammo_meter.main(*([str(n) for n in sizes] + [base]))
    if 'reticle' in h:                   # a Halo 3 reticle, into Halo 1's sheet
        import h1_add_reticle
        seq = (h1_add_reticle.add(*h['reticle'], index=RESERVED.get(key, {}).get('reticle'),
                                  thicken=h.get('reticle_thicken', 0))
               if write else -1)
        for c in d.crosshairs.STEPTREE:
            if c.crosshair_type.enum_name == 'aim':
                for o in c.crosshair_overlays.STEPTREE:
                    o.sequence_index = seq
    if 'scope' in h:                     # Halo 3's ZOOMED scope (h1_h3_scope.py): the BR, 2026-10-07
        # the whole zoom HUD replaced (user: the standard procedure): the screen-effect
        # mask = Halo 3's scope widgets baked, no blur, the donor's zoom crosshairs dropped
        import h1_h3_scope
        S = h['scope']
        if not d.screen_effect.STEPTREE and h.get('screen_effect_from'):
            # a donor HUD with NO zoom screen effect (the Beam Rifle: the plasma pistol's
            # heat + battery HUD) takes another HUD's (the sniper's: mask, convolution,
            # night vision) -- the mask itself is replaced below
            src = wphi_def.build(filepath=path(h['screen_effect_from'], '.weapon_hud_interface')).data.tagdata
            for se in src.screen_effect.STEPTREE:
                d.screen_effect.STEPTREE.append(copy.deepcopy(se))
        if write:
            dark, blur, used = h1_h3_scope.bake_maps(S['chud'], size=S.get('size', 512), span=S.get('span', 640.0),
                                                     aspect=S.get('aspect', 1.0), per_widget=S.get('per_widget'))
            h1_h3_scope.write(dark, S['out'], alpha=S.get('alpha', 255), blur=blur)
            print('   scope: ' + '; '.join(used))
        se = d.screen_effect.STEPTREE[0]
        se.mask.flags.only_when_zoomed = True
        se.mask.fullscreen_mask.filepath = S['out']
        se.mask.splitscreen_mask.filepath = S['out']
        for k in h.get('screen_effect_clear', ()):
            # a borrowed screen effect's extras switched off (the Beam Rifle took the sniper's:
            # its night vision and green desaturation; Halo 3's beam rifle has neither)
            blk = getattr(se, k)
            for f in blk.flags.NAME_MAP:
                setattr(blk.flags, f, False)
            blk.intensity = 0.0
        # the convolution stays the DONOR's: radius 0 smeared the zoomed view (BR tests 2-3)
        if 'blur_radius' in S:
            se.convolution.radius_out_bounds[0], se.convolution.radius_out_bounds[1] = S['blur_radius']
        xs = d.crosshairs.STEPTREE
        for i in range(len(xs) - 1, -1, -1):
            if xs[i].crosshair_type.enum_name == 'zoom':
                xs.pop(i)
    seq = icon_sequence(w['icon'])
    want = RESERVED.get(key, {}).get('icon')
    if want is not None and seq != want:
        raise SystemExit('%s: icon %r is hud_msg_icons #%d, reserved #%d' % (key, w['icon'], seq, want))
    d.messaging_information.sequence_index = seq
    save(t, path(h['out'], '.weapon_hud_interface'), write)
    return h['out']


def make_lunge(w, a, write):
    """The sword's fire button: a magazine and trigger in the plasma pistol's shape, firing
    an invisible short strike with the sword's own melee damage, and shoving the wielder."""
    L = w['lunge']
    tmpl = weap_def.build(filepath=path(L['template'], '.weapon')).data.tagdata.weap_attrs
    # the strike: the AR bullet with everything visible or audible taken off
    pt = proj_def.build(filepath=path(L['strike_from'], '.projectile'))
    pd = pt.data.tagdata
    pd.obje_attrs.attachments.STEPTREE[:] = []
    ph = pd.proj_attrs.physics
    ph.initial_velocity = ph.final_velocity = L['velocity']
    ph.air_gravity_scale = 0.0
    ph.flyby_sound.filepath = ''
    if write:
        shutil.copy2(path(a.melee.player_damage.filepath, '.damage_effect'),
                     path(L['strike_damage'], '.damage_effect'))
    ph.impact_damage.filepath = L['strike_damage']                # = the melee's values
    pd.proj_attrs.detonation.maximum_range = L['range']
    hit = ''
    if L.get('hit_effect') and w.get('hit_sound'):
        from reclaimer.hek.defs.effe import effe_def
        src, hit = L['hit_effect']
        et = effe_def.build(filepath=path(src, '.effect'))
        parts = et.data.tagdata.events.STEPTREE[0].parts.STEPTREE
        for i in reversed(range(len(parts))):
            if parts[i].type.tag_class.enum_name != 'sound':
                parts.pop(i)
        if len(parts) != 1:
            raise SystemExit('%s: want exactly one sound part' % src)
        parts[0].type.filepath = w['hit_sound']
        save(et, path(hit, '.effect'), write)
    for m in pd.proj_attrs.material_responses.STEPTREE:     # no bullet holes; the sword's hit
        m.effect.filepath = hit
        m.potential_response.effect.filepath = ''
        m.detonation_effect.filepath = ''
    save(pt, path(L['strike'], '.projectile'), write)
    # the shove: a zero-damage firing effect whose instantaneous acceleration is the lunge
    jt = jpt__def.build(filepath=path(L['push_from'], '.damage_effect'))
    dm = jt.data.tagdata.damage
    dm.instantaneous_acceleration = L['acceleration']
    dm.damage_lower_bound = L['push_damage']
    dm.damage_upper_bound[0] = dm.damage_upper_bound[1] = L['push_damage']
    mods = jt.data.tagdata.damage_modifiers
    for k in mods.desc['NAME_MAP']:
        setattr(mods, k, 1.0)
    save(jt, path(L['push'], '.damage_effect'), write)
    mags = a.magazines.STEPTREE
    mags[:] = []
    mags.append(copy.deepcopy(tmpl.magazines.STEPTREE[0]))        # all zero: no ammo
    trs = a.triggers.STEPTREE
    trs[:] = []
    trs.append(copy.deepcopy(tmpl.triggers.STEPTREE[0]))
    tr = trs[0]
    tr.flags.data = 0
    tr.flags.does_not_repeat_automatically = True
    tr.firing.rounds_per_second.__setitem__(0, L['rate'])
    tr.firing.rounds_per_second.__setitem__(1, L['rate'])
    tr.firing.error.__setitem__(0, 0.0)
    tr.firing.error.__setitem__(1, 0.0)
    tr.charging.charging_time = 0.0
    tr.charging.charge_hold_time = 0.0
    tr.charging.overcharged_action.set_to('none')
    tr.charging.charged_illumination = 0.0
    # a sword swing is not a gunshot: the plasma pistol template fires `loud`, which every
    # AI in earshot reacts to
    tr.firing.firing_noise.set_to('silent')
    tr.projectile.projectile.filepath = L['strike']
    tr.projectile.error_angle.__setitem__(1, 0.0)
    tr.misc.heat_generated_per_round = 0.0
    tr.misc.age_generated_per_round = L['energy']
    tr.misc.illumination_recovery_time = 0.0
    for fe in tr.firing_effects.STEPTREE:
        fe.firing_effect.filepath = ''
        fe.misfire_effect.filepath = ''
        fe.empty_effect.filepath = ''
        fe.firing_damage.filepath = L['push']
        fe.misfire_damage.filepath = ''
        fe.empty_damage.filepath = ''
    a.flags.cannot_fire_at_maximum_age = True
    a.age.misfire_start = 0.0
    a.age.misfire_chance = 0.0


def own_projectile(a, o, write):
    """Clone projectile -> detonation effect -> damage effect and repoint the chain, so the
    weapon fires tags nothing else names (verify the BUILT map: port_refs_audit idea)."""
    from reclaimer.hek.defs.effe import effe_def
    (p_src, p_own), (e_src, e_own), (j_src, j_own) = o['projectile'], o['effect'], o['damage']
    if write:
        shutil.copy2(path(j_src, '.damage_effect'), path(j_own, '.damage_effect'))
    et = effe_def.build(filepath=path(e_src, '.effect'))
    n = 0
    for ev in et.data.tagdata.events.STEPTREE:
        for part in ev.parts.STEPTREE:
            if part.type.filepath.lower() == j_src.lower():
                part.type.filepath = j_own
                n += 1
    if n != 1:
        raise SystemExit('%s: %d parts name %s' % (e_src, n, j_src))
    save(et, path(e_own, '.effect'), write)
    pt = proj_def.build(filepath=path(p_src, '.projectile'))
    det = pt.data.tagdata.proj_attrs.detonation
    if det.effect.filepath.lower() != e_src.lower():
        raise SystemExit('%s detonates %s, not %s' % (p_src, det.effect.filepath, e_src))
    det.effect.filepath = e_own
    save(pt, path(p_own, '.projectile'), write)
    for tr in a.triggers.STEPTREE:
        if tr.projectile.projectile.filepath.lower() == p_src.lower():
            tr.projectile.projectile.filepath = p_own


def own_beam(a, b, write):
    """The weapon's own projectile (a copy of `projectile[0]`, range set) and its own
    impact damage (a copy of `damage[0]`, damage + instantaneous acceleration set).
    The same for a BULLET (`bullet` key, the SMG): `velocity` sets initial = final speed
    (Reclaimer: world units per SECOND), and a value left out keeps the template's."""
    (p_src, p_own), (j_src, j_own) = b['projectile'], b['damage']
    jt = jpt__def.build(filepath=path(j_src, '.damage_effect'))
    dm = jt.data.tagdata.damage
    dm.damage_lower_bound = b['dmg']
    dm.damage_upper_bound[0] = dm.damage_upper_bound[1] = b['dmg']
    if 'acceleration' in b:
        dm.instantaneous_acceleration = b['acceleration']
    for dotted, v in b.get('fields', {}).items():  # step 4b on the damage effect (the BR)
        *head, last = dotted.split('.')
        node = jt.data.tagdata
        for part in head:
            node = getattr(node, part)
        if isinstance(v, str) and hasattr(getattr(node, last), 'set_to'):
            getattr(node, last).set_to(v)
        else:
            setattr(node, last, v)
    save(jt, path(j_own, '.damage_effect'), write)
    pt = proj_def.build(filepath=path(p_src, '.projectile'))
    pd = pt.data.tagdata.proj_attrs
    pd.physics.impact_damage.filepath = j_own
    if 'range' in b:
        pd.detonation.maximum_range = b['range']
    for dotted, v in b.get('proj_fields', {}).items():   # step 4b on the projectile (the Beam Rifle)
        *head, last = dotted.split('.')
        node = pt.data.tagdata
        for part in head:
            node = getattr(node, part)
        if isinstance(v, str) and hasattr(getattr(node, last), 'set_to'):
            getattr(node, last).set_to(v)        # an enum by name (the Spike Rifle's timer start)
        elif isinstance(v, tuple):               # a bounds pair (the Spike Rifle's damage range)
            for i, x in enumerate(v):
                getattr(node, last)[i] = x
        else:
            setattr(node, last, v)
    if 'velocity' in b:
        if isinstance(b['velocity'], tuple):  # (initial, final): the Spike Rifle's slowing spike
            pd.physics.initial_velocity, pd.physics.final_velocity = b['velocity']
        else:
            pd.physics.initial_velocity = pd.physics.final_velocity = b['velocity']
    for resp, mats in b.get('default_responses', {}).items():
        # per Halo 1 material index, the DEFAULT response by name (the Spike Rifle's stuck
        # spike: 'attach', the needle's way; Halo 3's fizzles -> 'disappear')
        for i in mats:
            pd.material_responses.STEPTREE[i].response.set_to(resp)
    if 'model' in b:                         # a visible projectile (the stuck spike's gbxmodel)
        pt.data.tagdata.obje_attrs.model.filepath = b['model']
    if 'impact_thin' in b:
        # the impact effect ON THE PLAYER, thinned (the Spike Rifle's Armed test: 'an impact
        # effect played on the player' at a high rate -- a hit plays the projectile's response
        # effect for the player's material, the AR's `impact cyborg shield` = 25 shield sparks
        # + a flash): per Halo 1 material index, an OWN copy of the response effect under
        # `out` keeping every n-th particle whose path holds a key of `thin` {substring: n}
        from reclaimer.hek.defs.effe import effe_def
        import h1_hit_effect_load as HL
        I = dict(b['impact_thin'])
        for i in I['materials']:
            x = pd.material_responses.STEPTREE[i]
            src_e = x.effect.filepath
            if I.get('budget'):
                # THE HIT-EFFECT RULE (user, 2026-10-08): at most the stock pistol's load per
                # second on the player -- size scale = sqrt(budget / (rate x load per hit))
                I['scale'] = HL.rule_scale(src_e, I['rate'], I.get('per_shot', 1), I['budget'])
                print('   hit-effect rule: %s at %.1f/s -> size x%.3f' % (src_e, I['rate'], I['scale']))
            et = effe_def.build(filepath=path(src_e, '.effect'))
            kept = total = 0
            for ev in et.data.tagdata.events.STEPTREE:
                pts = ev.particles.STEPTREE
                seen = {}
                for k in range(len(pts) - 1, -1, -1):
                    key = next((s for s in I['thin'] if s in pts[k].particle_type.filepath), None)
                    if key is None:
                        continue
                    total += 1
                    seen[key] = seen.get(key, -1) + 1
                    if seen[key] % I['thin'][key]:
                        pts.pop(k)
                    else:
                        kept += 1
                for q in pts:                     # `scale`: every remaining particle's radius
                    q.radius[0], q.radius[1] = q.radius[0] * I.get('scale', 1.0), q.radius[1] * I.get('scale', 1.0)
            own = I['out'] + src_e.rsplit('\\', 1)[-1]
            save(et, path(own, '.effect'), write)
            x.effect.filepath = own
            print('   impact on material %d: %s -> %s (%d of %d thinned particles kept)' % (i, src_e, own, kept, total))
    if 'detonation_effect' in b:
        # an OWN detonation effect copied from another projectile's (the Spike Rifle, test 2:
        # 'detonate like the needles, no damage' -- the needle's burst): particles whose path
        # holds one of `drop_particles` removed, the rest whose path holds one of `tint_match`
        # recoloured `tint` (RGB, not HSV); parts whose tag path is in `drop_parts` removed
        from reclaimer.hek.defs.effe import effe_def
        D = b['detonation_effect']
        et = effe_def.build(filepath=path(D['from'], '.effect'))
        for ev in et.data.tagdata.events.STEPTREE:
            pts = ev.particles.STEPTREE
            for i in range(len(pts) - 1, -1, -1):
                q = pts[i]
                if any(s in q.particle_type.filepath for s in D.get('drop_particles', ())):
                    pts.pop(i)
                else:
                    if D.get('tint') and any(s in q.particle_type.filepath for s in D.get('tint_match', ())):
                        q.flags.tint_as_hsv = False
                        for bound in (q.tint_lower_bound, q.tint_upper_bound):
                            bound.r, bound.g, bound.b = D['tint']
                    if D.get('scale'):           # every particle's radius (the spike's smaller burst)
                        q.radius[0], q.radius[1] = q.radius[0] * D['scale'], q.radius[1] * D['scale']
            prts = ev.parts.STEPTREE
            for i in range(len(prts) - 1, -1, -1):
                if prts[i].type.filepath in D.get('drop_parts', ()):
                    prts.pop(i)
        save(et, path(D['out'], '.effect'), write)
        pd.detonation.effect.filepath = D['out']
    if 'reflect' in b:
        # a RICOCHET as the potential response (the Spike Rifle: Halo 3's spike bounces off
        # hard metal / rock / forerunner shields at 0-60 deg, chance 1): per Halo 1 material
        # index, potential response 'reflect', skip fraction 0 (Halo 1 SKIPS that fraction;
        # Halo 3 has a chance), impact angle (deg), optional impact velocity window, the
        # response's frictions and angular noise. The default response stays the template's
        R = b['reflect']
        mr = pd.material_responses.STEPTREE
        for i in R['materials']:
            x = mr[i]
            pr = x.potential_response
            pr.response.set_to('reflect')
            pr.skip_fraction = R.get('skip', 0.0)
            pr.impact_angle[0], pr.impact_angle[1] = (math.radians(a) for a in R['angle_deg'])
            pr.impact_velocity[0], pr.impact_velocity[1] = R.get('velocity', (0.0, 0.0))
            if R.get('effect_from_default', True):   # the template's impact effect on the bounce
                pr.effect.filepath = x.effect.filepath
            x.parallel_refriction = R.get('parallel_friction', x.parallel_refriction)
            x.perpendicular_friction = R.get('perpendicular_friction', x.perpendicular_friction)
            x.angular_noise = math.radians(R.get('noise_deg', 0.0))
    if 'attachments_from' in b:          # e.g. a TRACER contrail (the BR takes the AR bullet's)
        src = proj_def.build(filepath=path(b['attachments_from'], '.projectile')).data.tagdata
        att = pt.data.tagdata.obje_attrs.attachments.STEPTREE
        att[:] = []
        for x in src.obje_attrs.attachments.STEPTREE:
            att.append(copy.deepcopy(x))
    if 'contrail' in b:                  # an OWN recoloured copy of the trail (the Beam Rifle)
        from reclaimer.hek.defs.cont import cont_def
        C = b['contrail']
        ct = cont_def.build(filepath=path(C['from'], '.contrail'))
        for ps in ct.data.tagdata.point_states.STEPTREE:
            for bound in (ps.color_lower_bound, ps.color_upper_bound):
                bound.r, bound.g, bound.b = C['rgb']
            if 'width' in C:
                ps.width *= C['width']
            if C.get('no_physics'):          # a BEAM, not a vapour trail: the sniper's points
                ps.physics.filepath = ''     # ride smoke point physics and drift with the wind
        save(ct, path(C['out'], '.contrail'), write)
        n = 0
        for x in pt.data.tagdata.obje_attrs.attachments.STEPTREE:
            if x.type.filepath.lower() == C['from'].lower():
                x.type.filepath = C['out']
                n += 1
        if n != 1:
            raise SystemExit('%s: %d attachments name %s' % (p_own, n, C['from']))
    if 'material_responses_from' in b:   # the impact effects per material (the Carbine: plasma)
        src = proj_def.build(filepath=path(b['material_responses_from'], '.projectile')).data.tagdata
        mr = pd.material_responses.STEPTREE
        mr[:] = []
        for x in src.proj_attrs.material_responses.STEPTREE:
            mr.append(copy.deepcopy(x))
    if 'material_effects_from' in b:
        # only the EFFECTS of another projectile's responses (the Beam Rifle close-out: Halo
        # 3's beam overpenetrates the same 11 materials as its sniper, but the plasma pistol
        # bolt's whole responses -- material_responses_from -- made them 'disappear'): the
        # template's response types stay, each material's effect / potential effect /
        # detonation effect come from `from` (same material index in Halo 1's fixed list)
        src = proj_def.build(filepath=path(b['material_effects_from'], '.projectile')).data.tagdata
        for x, y in zip(pd.material_responses.STEPTREE, src.proj_attrs.material_responses.STEPTREE):
            x.effect.filepath = y.effect.filepath
            x.potential_response.effect.filepath = y.potential_response.effect.filepath
            x.detonation_effect.filepath = y.detonation_effect.filepath
    if 'change_color' in b:
        # the projectile's CHANGE COLOUR A (the Beam Rifle, test 4: the impacts stayed
        # un-pink): `c generic` particles take their colour from the CREATING object's change
        # colour, here the projectile -- the plasma pistol bolt's runs magenta -> GREEN; the
        # sniper bullet has none. A copy of `from`'s block, both bounds `rgb`, RGB blend
        C = b['change_color']
        src = proj_def.build(filepath=path(C['from'], '.projectile')).data.tagdata
        ccs = pt.data.tagdata.obje_attrs.change_colors.STEPTREE
        ccs[:] = []
        cc = copy.deepcopy(src.obje_attrs.change_colors.STEPTREE[0])
        cc.flags.blend_in_hsv = False
        for bound in (cc.color_lower_bound, cc.color_upper_bound):
            bound.r, bound.g, bound.b = C['rgb']
        ccs.append(cc)
    if 'impact_tint' in b:
        # the impacts RECOLOURED (the Beam Rifle, test 3: 'green plasma on the ground, blue
        # smoke'): every response effect with a matching particle (path holds one of `match`)
        # or a `decals` swap gets an own copy under `out`, those particles tinted `rgb` (RGB,
        # not HSV: the stock tints blend in hue space), the decals swapped
        from reclaimer.hek.defs.effe import effe_def
        T = b['impact_tint']
        done = {}
        for x in pd.material_responses.STEPTREE:
            for k in x.desc['NAME_MAP']:
                ref = getattr(x, k)
                if not (hasattr(ref, 'filepath') and ref.filepath) or ref.tag_class.enum_name != 'effect':
                    continue
                src_e = ref.filepath
                if src_e not in done:
                    et = effe_def.build(filepath=path(src_e, '.effect'))
                    n = 0
                    for ev in et.data.tagdata.events.STEPTREE:
                        for q in ev.particles.STEPTREE:
                            if any(m in q.particle_type.filepath for m in T['match']):
                                q.flags.tint_as_hsv = False
                                for bound in (q.tint_lower_bound, q.tint_upper_bound):
                                    bound.r, bound.g, bound.b = T['rgb']
                                n += 1
                        for part in ev.parts.STEPTREE:
                            new = T.get('decals', {}).get(part.type.filepath)
                            if new:
                                part.type.filepath = new
                                n += 1
                    if n:
                        own = T['out'] + src_e.rsplit('\\', 1)[-1]
                        save(et, path(own, '.effect'), write)
                        done[src_e] = own
                    else:
                        done[src_e] = src_e
                ref.filepath = done[src_e]
        print('   impacts: %d effect(s) recoloured' % sum(1 for k, v in done.items() if k != v))
    save(pt, path(p_own, '.projectile'), write)
    for tr in a.triggers.STEPTREE:
        tr.projectile.projectile.filepath = p_own


def add_hum(d, h, write):
    """An always-on looping sound on the weapon: a sound_looping cloned from `like`,
    its loop track naming our sound, attached unscaled at `marker`."""
    from reclaimer.hek.defs.lsnd import lsnd_def
    lt = lsnd_def.build(filepath=path(h['like'], '.sound_looping'))
    ld = lt.data.tagdata
    tr = ld.tracks.STEPTREE[0]
    tr.start.filepath = ''
    tr.loop.filepath = h['loop']
    tr.end.filepath = ''
    while len(ld.tracks.STEPTREE) > 1:
        ld.tracks.STEPTREE.pop()
    save(lt, path(h['tag'], '.sound_looping'), write)
    atts = d.obje_attrs.attachments.STEPTREE
    if any(x.type.filepath == h['tag'] for x in atts):
        return
    atts.append(copy.deepcopy(atts[0]))
    x = atts[len(atts) - 1]
    x.type.tag_class.set_to('sound_looping')
    x.type.filepath = h['tag']
    x.marker = h['marker']
    x.primary_scale.set_to('none')
    x.secondary_scale.set_to('none')
    x.change_color.set_to('none')


def rewire(d, r):
    """Re-lay a template's export inputs and object functions: `inputs` A..D, functions
    {new index: (source, scale by, usage)} -- source a template function index, or
    (weapon tag, index) to copy another weapon's -- and attachment scales renamed."""
    o = d.obje_attrs
    old = [copy.deepcopy(f) for f in o.functions.STEPTREE]
    for slot, inp in zip('ABCD', r['inputs']):
        getattr(d.weap_attrs, slot + '_in').set_to(inp)
    for i, (src, by, usage, *extra) in r['functions'].items():
        if isinstance(src, tuple):
            other = weap_def.build(filepath=path(src[0], '.weapon')).data.tagdata
            fn = copy.deepcopy(other.obje_attrs.functions.STEPTREE[src[1]])
        else:
            fn = copy.deepcopy(old[src])
        fn.scale_function_by.set_to(by)
        fn.usage = usage
        for k, v in (extra[0] if extra else {}).items():
            if k == 'turn_off_with':
                fn.turn_off_with = v
            else:
                setattr(fn.flags, k, v)
        o.functions.STEPTREE[i] = fn
    atts = o.attachments.STEPTREE
    for i in range(len(atts) - 1, -1, -1):
        sc = atts[i].primary_scale.enum_name
        if sc in r.get('drop_attachments_on', ()):
            atts.pop(i)
        elif sc in r.get('attach_scale', {}):
            atts[i].primary_scale.set_to(r['attach_scale'][sc])


def add_fire_loop(d, f, write):
    """A start/loop/end sound_looping (cloned from `like`) at `marker`, its primary scale
    the weapon's existing object function output `scale` (it plays while that is up)."""
    from reclaimer.hek.defs.lsnd import lsnd_def
    lt = lsnd_def.build(filepath=path(f['like'], '.sound_looping'))
    ld = lt.data.tagdata
    tr = ld.tracks.STEPTREE[0]
    tr.start.filepath, tr.loop.filepath, tr.end.filepath = f['start'], f['loop'], f['end']
    tr.gain = 1.0                 # the flamethrower's fire_ft says 0.0; the charging loop
                                  # that played in tests 2-3 says 1.0
    while len(ld.tracks.STEPTREE) > 1:
        ld.tracks.STEPTREE.pop()
    save(lt, path(f['tag'], '.sound_looping'), write)
    atts = d.obje_attrs.attachments.STEPTREE
    atts.append(copy.deepcopy(atts[0]))
    x = atts[len(atts) - 1]
    x.type.tag_class.set_to('sound_looping')
    x.type.filepath = f['tag']
    x.marker = f['marker']
    x.primary_scale.set_to(f['scale'])
    x.secondary_scale.set_to('none')
    x.change_color.set_to('none')


def add_charge_loop(d, c):
    """A looping sound attachment whose scale follows the weapon's charge."""
    o = d.obje_attrs
    funcs, atts = o.functions.STEPTREE, o.attachments.STEPTREE
    if any(a.type.filepath == c['sound'] for a in atts):
        return
    if len(funcs) >= 4:
        raise SystemExit('no free object function for the charge loop')
    tmpl = weap_def.build(filepath=path(r'weapons\plasma pistol\plasma pistol', '.weapon'))
    td = tmpl.data.tagdata.obje_attrs
    funcs.append(copy.deepcopy(td.functions.STEPTREE[3]))      # 'one' scaled by an input
    f = funcs[len(funcs) - 1]
    f.scale_function_by.set_to(c['input'])
    out = 'ABCD'[len(funcs) - 1] + '_out'
    loop = [a for a in td.attachments.STEPTREE if a.type.filepath == c['sound']][0]
    for ref in [c['sound']] + c.get('glow', []):
        atts.append(copy.deepcopy(loop))
        a = atts[len(atts) - 1]
        if ref != c['sound']:
            ext = 'light_volume' if os.path.exists(path(ref, '.light_volume')) else 'light'
            a.type.tag_class.set_to(ext)
        a.type.filepath = ref
        a.marker = c['marker']
        a.primary_scale.set_to(out)


def edit_weapon(key, write):
    w = WEAPONS[key]
    p = path(w['weapon'], '.weapon')
    if w.get('template'):                    # a NEW weapon: always rebuilt from its template
        src = path(w['template'], '.weapon')
    else:
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = weap_def.build(filepath=src)
    d = t.data.tagdata
    a = d.weap_attrs
    print('%s: flags before %s' % (key, [f for f in a.flags.NAME_MAP if a.flags.get(f)]))
    a.flags.detonates_when_dropped = False
    a.interface.first_person_model.filepath = w['fp_model']
    a.interface.first_person_animations.filepath = w['fp_anims']
    if 'melee' in w:
        donor, own = w['melee']
        if write:
            backup(path(own, '.damage_effect'))
            shutil.copy2(path(donor, '.damage_effect'), path(own, '.damage_effect'))
        if 'melee_dmg' in w:
            # the copy's damage MEAN set, its lower / upper spread kept (the Spike Rifle's blade:
            # Halo 3 cut_melee 72 against the H1 AR's 50..60): both upper bounds x mean / old
            jt = jpt__def.build(filepath=path(donor, '.damage_effect'))
            dm = jt.data.tagdata.damage
            k = w['melee_dmg'] / ((dm.damage_upper_bound[0] + dm.damage_upper_bound[1]) / 2.0)
            dm.damage_lower_bound *= k
            dm.damage_upper_bound[0], dm.damage_upper_bound[1] = (dm.damage_upper_bound[0] * k,
                                                                  dm.damage_upper_bound[1] * k)
            save(jt, path(own, '.damage_effect'), write)
            print('   melee %s: x%.3f -> %.1f..%.1f' % (own, k, dm.damage_upper_bound[0], dm.damage_upper_bound[1]))
        a.melee.player_damage.filepath = own
        a.melee.player_response.filepath = w['melee_response']
    if 'messages' in w:
        res = (RESERVED.get(key, {}).get('messages') or (None,))[0]
        d.item_attrs.message_index = message_index(w['messages'], write, res)
    if 'hud' in w:
        a.interface.hud_interface.filepath = make_hud(w, key, write)
    if 'lunge' in w:
        make_lunge(w, a, write)
    if 'own_projectile' in w:
        own_projectile(a, w['own_projectile'], write)
    if w.get('world_model'):
        d.obje_attrs.model.filepath = w['world_model']
    if w.get('label'):
        a.label = w['label']
    if 'keep_triggers' in w:
        # the template's EXTRA triggers dropped (the Beam Rifle on the plasma pistol: its
        # charged-shot trigger 1); the secondary trigger mode back to normal
        trs = a.triggers.STEPTREE
        while len(trs) > w['keep_triggers']:
            trs.pop()
    if 'beam' in w:
        own_beam(a, w['beam'], write)
    if 'bullet' in w:
        own_beam(a, w['bullet'], write)
    if 'magazine' in w:                      # magazine 0's fields (rounds, reload time s)
        m = a.magazines.STEPTREE[0]
        for k, v in w['magazine'].items():
            setattr(m, k, v)
    for k, v in w.get('error_deg', {}).items():     # Halo 1 stores angles in RADIANS
        for tr in a.triggers.STEPTREE:
            if k == 'error_angle':
                tr.projectile.error_angle[0], tr.projectile.error_angle[1] = (
                    math.radians(v[0]), math.radians(v[1]))
            else:
                setattr(tr.projectile, k, math.radians(v))
    for field, (src, out, swaps, *opt) in w.get('sound_effects', {}).items():
        # an OWN copy of a shared effect (the AR's `fire bullet` / `empty`) with its sound
        # parts renamed: the SAW's own-sounds recipe, as data (h1_saw_sounds.py)
        from reclaimer.hek.defs.effe import effe_def
        fl = opt[0] if opt else {}
        # `copy_from`: the copy starts from ANOTHER effect (the Carbine: the plasma pistol's
        # green `fire bolt`, no casing) -- `src` still names the template field repointed
        et = effe_def.build(filepath=path(fl.get('copy_from', src), '.effect'))
        # the MUZZLE FLASH of the copy (SMG test 1, 2026-10-07: the AR's flash is sized for
        # the AR's muzzle): particles whose tag path holds `match` -- off-axis ones (|y| or
        # |z| over `drop_off_axis` wu: the AR's muzzle-brake rings) removed, the rest
        # `scale`d (radius) and `shift`ed (wu, marker space: forward, left, up)
        for ev in (et.data.tagdata.events.STEPTREE if fl.get('match') else ()):
            pts = ev.particles.STEPTREE
            for i in range(len(pts) - 1, -1, -1):
                x = pts[i]
                if fl['match'] not in x.particle_type.filepath:
                    continue
                o = x.relative_offset
                if fl.get('drop_off_axis') is not None and max(abs(o.j), abs(o.k)) > fl['drop_off_axis']:
                    pts.pop(i)
                    continue
                x.radius[0], x.radius[1] = x.radius[0] * fl.get('scale', 1.0), x.radius[1] * fl.get('scale', 1.0)
                dx, dy, dz = fl.get('shift', (0.0, 0.0, 0.0))
                o.i, o.j, o.k = o.i + dx, o.j + dy, o.k + dz
        # `tint` (ARGB): every particle of the copy recoloured, RGB not HSV (the plasma
        # pistol's green flash IS a tint on a white sprite -- the Sentinel Beam's finding)
        for ev in (et.data.tagdata.events.STEPTREE if fl.get('tint') else ()):
            for x in ev.particles.STEPTREE:
                x.flags.tint_as_hsv = False
                for b in (x.tint_lower_bound, x.tint_upper_bound):
                    b.a, b.r, b.g, b.b = fl['tint']
        # `drop_particles` (path substrings) / `drop_parts` (tag paths): what the source weapon
        # does not have (the Spike Rifle: no casing, so the AR's casing particle and the
        # pistol's eject sound go -- otherwise a BORROW in port_sound_refs)
        for ev in et.data.tagdata.events.STEPTREE:
            pts = ev.particles.STEPTREE
            for i in range(len(pts) - 1, -1, -1):
                if any(s in pts[i].particle_type.filepath for s in fl.get('drop_particles', ())):
                    pts.pop(i)
            prts = ev.parts.STEPTREE
            for i in range(len(prts) - 1, -1, -1):
                if prts[i].type.filepath in fl.get('drop_parts', ()):
                    prts.pop(i)
        n = 0
        for ev in et.data.tagdata.events.STEPTREE:
            for part in ev.parts.STEPTREE:
                new = swaps.get(part.type.filepath)
                if new:
                    part.type.filepath = new
                    n += 1
        if n != len(swaps):
            raise SystemExit('%s: %d of %d sound parts found' % (src, n, len(swaps)))
        save(et, path(out, '.effect'), write)
        for tr in a.triggers.STEPTREE:
            for fe in tr.firing_effects.STEPTREE:
                if getattr(fe, field).filepath.lower() == src.lower():
                    setattr(getattr(fe, field), 'filepath', out)
    for k, v in w.get('trigger', {}).items():
        for tr in a.triggers.STEPTREE:
            if k == 'rounds_per_second':
                lo, hi = v if isinstance(v, tuple) else (v, v)
                tr.firing.rounds_per_second[0], tr.firing.rounds_per_second[1] = lo, hi
            elif k == 'error_angle':
                tr.projectile.error_angle[0], tr.projectile.error_angle[1] = v
            elif k == 'first_person_offset':
                o = tr.projectile.first_person_offset
                o.x, o.y, o.z = v
            else:                            # whichever trigger struct holds the field
                sub = [s for s in tr if hasattr(s, 'NAME_MAP') and k in s.NAME_MAP]
                if not sub:
                    raise SystemExit('trigger field %s not found' % k)
                if isinstance(v, str):       # an enum by name (the BR's overcharged_action)
                    getattr(sub[0], k).set_to(v)
                else:
                    setattr(sub[0], k, v)
    for k, v in w.get('heat', {}).items():
        setattr(a.heat, k, v)
    if 'overheated_effect' in w:
        from reclaimer.hek.defs.effe import effe_def
        O = w['overheated_effect']
        et = effe_def.build(filepath=path(O['from'], '.effect'))
        for loc in et.data.tagdata.locations.STEPTREE:
            loc.marker_name = O['locations'].get(loc.marker_name, loc.marker_name)
        save(et, path(O['out'], '.effect'), write)
        a.heat.overheated.filepath = O['out']
    if 'misfire_effect' in w:                 # same marker fix for the misfire burst
        from reclaimer.hek.defs.effe import effe_def
        M = w['misfire_effect']
        et = effe_def.build(filepath=path(M['from'], '.effect'))
        for loc in et.data.tagdata.locations.STEPTREE:
            loc.marker_name = M['locations'].get(loc.marker_name, loc.marker_name)
        # `sounds`: its sound parts renamed (the Sentinel Beam's own overheat, 2026-10-08)
        n = 0
        for ev in et.data.tagdata.events.STEPTREE:
            for part in ev.parts.STEPTREE:
                new = M.get('sounds', {}).get(part.type.filepath)
                if new:
                    part.type.filepath = new
                    n += 1
        if M.get('sounds') and not n:
            raise SystemExit('%s: none of the sound parts %s found' % (M['from'], list(M['sounds'])))
        save(et, path(M['out'], '.effect'), write)
        for tr in a.triggers.STEPTREE:
            for fe in tr.firing_effects.STEPTREE:
                if fe.misfire_effect.filepath == M['from']:
                    fe.misfire_effect.filepath = M['out']
    if 'rewire' in w:
        rewire(d, w['rewire'])
    if 'change_color_a' in w:
        cc = d.obje_attrs.change_colors.STEPTREE[0]
        cc.flags.blend_in_hsv = False
        for b, rgb in zip((cc.color_lower_bound, cc.color_upper_bound), w['change_color_a']):
            b.r, b.g, b.b = rgb
    if 'own_light' in w:
        from reclaimer.hek.defs.ligh import ligh_def
        L = w['own_light']
        lt = ligh_def.build(filepath=path(L['shape'], '.light'))
        look = ligh_def.build(filepath=path(L['look'], '.light')).data.tagdata
        lt.data.tagdata.color = look.color
        lt.data.tagdata.lens_flare.filepath = look.lens_flare.filepath
        if 'radius' in L:
            lt.data.tagdata.shape.radius = L['radius']
        for bound in (lt.data.tagdata.color.color_lower_bound,
                      lt.data.tagdata.color.color_upper_bound):
            if 'argb' in L:
                bound.a, bound.r, bound.g, bound.b = L['argb']
        if 'duration' in L:
            lt.data.tagdata.effect_parameters.duration = L['duration']
        if L.get('no_flare'):
            lt.data.tagdata.lens_flare.filepath = ''
        if 'flare' in L:
            from reclaimer.hek.defs.lens import lens_def
            fl = L['flare']
            ft = lens_def.build(filepath=path(fl['from'], '.lens_flare'))
            for r in ft.data.tagdata.reflections.STEPTREE:
                r.radius[0] = r.radius[1] = fl['radius']
                r.brightness_scaled_by.set_to('none')
            save(ft, path(fl['out'], '.lens_flare'), write)
            lt.data.tagdata.lens_flare.filepath = fl['out']
        save(lt, path(L['out'], '.light'), write)
    if 'fire_effect' in w:
        from reclaimer.hek.defs.effe import effe_def
        F = w['fire_effect']
        et = effe_def.build(filepath=path(F['from'], '.effect'))
        evs = et.data.tagdata.events.STEPTREE
        while len(evs) > 1:                       # one event
            evs.pop()
        ev = evs[0]
        keep = F.get('keep_particles')            # particle tags whose path holds this
        pts = ev.particles.STEPTREE
        for i in range(len(pts) - 1, -1, -1):
            if not keep or not pts[i].particle_type.filepath.endswith(keep):
                pts.pop(i)
        for x in pts:
            if 'tint' in F:
                x.flags.tint_as_hsv = False
                for b in (x.tint_lower_bound, x.tint_upper_bound):
                    b.a, b.r, b.g, b.b = F['tint']
            if 'particle_offset' in F:
                o = x.relative_offset
                o.i, o.j, o.k = F['particle_offset']
        parts = ev.parts.STEPTREE
        if F['sound']:
            parts[0].type.filepath = F['sound']
            parts.append(copy.deepcopy(parts[0]))
        lp = parts[len(parts) - 1]
        lp.type.tag_class.set_to('light')
        lp.type.filepath = F['light']
        save(et, path(F['out'], '.effect'), write)
        for tr in a.triggers.STEPTREE:
            for fe in tr.firing_effects.STEPTREE:
                fe.firing_effect.filepath = F['out']
    if 'charge_loop' in w:
        add_charge_loop(d, w['charge_loop'])
    if 'hum' in w:
        add_hum(d, w['hum'], write)
    if 'fire_loop' in w:
        add_fire_loop(d, w['fire_loop'], write)
    if 'obje_functions' in w:
        # the object FUNCTIONS (out N = function N, scaled by an export 'in'), rebuilt from
        # another weapon's (the BR, test 6: the on-gun counter reads A out, and the pistol
        # template's ONE function put the muzzle-flash LIGHT on A too -- a constant glow
        # once A carried the ammo; the AR keeps them apart: A out = ammo, B out = flash)
        fs = d.obje_attrs.functions.STEPTREE
        new = []
        for spec in w['obje_functions']:
            src = weap_def.build(filepath=path(spec['from'], '.weapon')).data.tagdata
            f = copy.deepcopy(src.obje_attrs.functions.STEPTREE[spec['index']])
            for k, v in spec.get('set', {}).items():
                getattr(f, k).set_to(v)
            new.append(f)
        fs[:] = []
        for f in new:
            fs.append(f)
    for i, spec in w.get('attachments_set', {}).items():
        # an attachment of the TEMPLATE re-pointed in place (type, marker, scales): editing
        # an existing element; tool rejected FRESH elements appended with Reclaimer (Beam
        # Rifle gem-flare test: 'tag reference name length mismatch')
        x = d.obje_attrs.attachments.STEPTREE[i]
        if 'type' in spec:
            x.type.tag_class.set_to(spec.get('class', 'light'))
            x.type.filepath = spec['type']
        if 'marker' in spec:
            x.marker = spec['marker']
        if 'scale' in spec:
            x.primary_scale.set_to(spec['scale'])
    if 'drop_attachments' in w:
        # template attachments that do not apply (the Beam Rifle on the plasma pistol: the
        # charged shot's flare and charging sound); indices in the TEMPLATE's order
        att = d.obje_attrs.attachments.STEPTREE
        for i in sorted(w['drop_attachments'], reverse=True):
            att.pop(i)
    for i, (p_scale, s_scale) in w.get('attachment_scales', {}).items():
        x = d.obje_attrs.attachments.STEPTREE[i]
        x.primary_scale.set_to(p_scale)
        x.secondary_scale.set_to(s_scale)
    for x in d.obje_attrs.attachments.STEPTREE:
        x.marker = w.get('attach_markers', {}).get(x.marker, x.marker)
        x.type.filepath = w.get('attach_swap', {}).get(x.type.filepath, x.type.filepath)
    if 'hit_sound' in w:
        jp = path(a.melee.player_damage.filepath, '.damage_effect')
        jt = jpt__def.build(filepath=jp + BACKUP if os.path.exists(jp + BACKUP) else jp)
        jt.data.tagdata.sound.filepath = w['hit_sound']
        save(jt, jp, write)
    if 'rounds_per_shot' in w:
        for tr in a.triggers.STEPTREE:
            tr.firing.rounds_per_shot = w['rounds_per_shot']
    for k, v in w.get('aiming', {}).items():
        if isinstance(v, tuple):             # a bounds pair (the Beam Rifle's zoom_ranges)
            for i, x in enumerate(v):
                getattr(a.aiming, k)[i] = x
        else:
            setattr(a.aiming, k, math.radians(v) if k.endswith('_angle') else v)
    # step 4b (port_field_audit.py --port <key>): fields NO card covers, by dotted path
    # from the tag data ('obje_attrs.bounding_radius'; a number indexes a block's elements:
    # 'weap_attrs.magazines.0.magazine_items.0.rounds'); values in Reclaimer units
    for dotted, v in w.get('fields', {}).items():
        *head, last = dotted.split('.')
        node = d
        for part in head:
            node = node.STEPTREE[int(part)] if part.isdigit() else getattr(node, part)
        if not hasattr(node, last):
            raise SystemExit('%s: no field %s' % (key, dotted))
        if isinstance(v, str) and hasattr(getattr(node, last), 'set_to'):
            getattr(node, last).set_to(v)        # an enum by name (the BR's B_in)
        elif isinstance(v, tuple):               # a bounds pair (the Beam Rifle's firing error)
            for i, x in enumerate(v):
                getattr(node, last)[i] = x
        else:
            setattr(node, last, v)
    print('   -> flags %s | fp %s | anims %s | hud %s | melee %s | message %d | triggers %d'
          % ([f for f in a.flags.NAME_MAP if a.flags.get(f)],
             a.interface.first_person_model.filepath,
             a.interface.first_person_animations.filepath,
             a.interface.hud_interface.filepath, a.melee.player_damage.filepath,
             d.item_attrs.message_index, len(a.triggers.STEPTREE)))
    t.filepath = p
    save(t, p, write)


def edit_palettes(key, write):
    """The weapon appended to each `palette_levels` scenario's weapons palette."""
    from reclaimer.hek.defs.scnr import scnr_def
    w = WEAPONS[key]
    for lvl in w.get('palette_levels', []):
        p = path('levels\\%s\\%s' % (lvl, lvl), '.scenario')
        t = scnr_def.build(filepath=p)
        pal = t.data.tagdata.weapons_palette.STEPTREE
        names = [e.name.filepath.lower() for e in pal]
        if w['weapon'].lower() in names:
            idx = names.index(w['weapon'].lower())
        else:
            pal.append()
            pal[-1].name.filepath = w['weapon']
            idx = len(pal) - 1
        # a palette entry ALONE is not built in (a10 test, 2026-10-06): tool keeps only
        # what a placement uses. Like the SAW: ONE placement, `not placed: automatically`
        # (never spawns, only makes the tag resident for the enhancer's own placements),
        # a copy of the SAW's
        places = t.data.tagdata.weapons.STEPTREE
        if any(x.type == idx for x in places):
            print('   %s: palette #%d + placement already there' % (lvl, idx))
            continue
        saw = names.index(r'weapons\saw\saw')
        src = [x for x in places if x.type == saw and x.not_placed.automatically]
        if not src:
            raise SystemExit('%s: no resident-only SAW placement to copy' % lvl)
        places.append(copy.deepcopy(src[0]))
        x = places[len(places) - 1]
        x.type = idx
        x.rounds_left = x.rounds_loaded = 0
        print('   %s: palette #%d + resident-only placement (the SAW\'s, at %s)'
              % (lvl, idx, tuple(round(c, 1) for c in x.position)))
        t.filepath = p
        save(t, p, write)


def edit_death_drop(key, write):
    """The weapon as a part of event 0 of each `death_drop` effect (an enemy that has no
    weapon to drop leaves one when it dies). The part copies the event's first part
    (location, velocity, cone), its type the weapon."""
    from reclaimer.hek.defs.effe import effe_def
    w = WEAPONS[key]
    for rel in w.get('death_drop', []):
        p = path(rel, '.effect')
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
        t = effe_def.build(filepath=src)
        parts = t.data.tagdata.events.STEPTREE[0].parts.STEPTREE
        parts.append(copy.deepcopy(parts[0]))
        x = parts[len(parts) - 1]
        x.type.tag_class.set_to('weapon')
        x.type.filepath = w['weapon']
        x.angular_velocity_bounds[0] = x.angular_velocity_bounds[1] = 0.0
        print('   %s: + weapon part %s (%d parts)' % (rel, w['weapon'], len(parts)))
        t.filepath = p
        save(t, p, write)


def edit_drops(key, write):
    """What the enemies that carry it drop: (loaded fraction range, reserve rounds range)."""
    for rel, ((l0, l1), (a0, a1)) in WEAPONS[key].get('drops', {}).items():
        p = path(rel, '.actor_variant')
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
        t = actv_def.build(filepath=src)
        it = t.data.tagdata.items
        print('   %s: drop loaded %s..%s ammo %s..%s -> %s..%s / %s..%s'
              % (rel, it.drop_weapon_loaded[0], it.drop_weapon_loaded[1],
                 it.drop_weapon_ammo[0], it.drop_weapon_ammo[1], l0, l1, a0, a1))
        it.drop_weapon_loaded[0], it.drop_weapon_loaded[1] = l0, l1
        it.drop_weapon_ammo[0], it.drop_weapon_ammo[1] = a0, a1
        t.filepath = p
        save(t, p, write)


def edit_fp_anims(key, write):
    """Melee key frames and sounds on the compiled FP animation tag. Recompiling it with
    `tool animations` resets both, so run this after every h1_fp_retarget --write."""
    w = WEAPONS[key]
    p = path(w['fp_anims'], '.model_animations')
    t = antr_def.build(filepath=p)
    d = t.data.tagdata
    refs = d.sound_references.STEPTREE
    have = [r.sound.filepath for r in refs]
    # UNUSED references the patcher swaps in after a balanced retime (catalog
    # anim_sounds; port_sounds.retimed_anim_sound): the SAW's saw_reload_balanced recipe
    for snd in w.get('extra_sounds', ()):
        if snd not in have:
            refs.append()
            refs[-1].sound.filepath = snd
            have.append(snd)
    for a in d.animations.STEPTREE:
        if a.name in w['keys']:
            a.key_frame_index = w['keys'][a.name]
        snd = w['sounds'].get(a.name)
        if snd:
            if snd not in have:
                refs.append()
                refs[-1].sound.filepath = snd
                have.append(snd)
            a.sound = have.index(snd)
            a.sound_frame_index = w.get('sound_frames', {}).get(a.name, 0)
        print('   %-30s key %2d sound %s' % (a.name, a.key_frame_index,
                                              have[a.sound] if a.sound >= 0 else '-'))
    save(t, p, write)


def teach_cyborg(write):
    """Append `fr` (from `pc`) and `fb` (from `b`) wherever the donor label exists."""
    p = path(CYBORG, '.model_animations')
    src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = antr_def.build(filepath=src)
    added = []
    for u in t.data.tagdata.units.STEPTREE:
        for wc in u.weapons.STEPTREE:
            wt = wc.weapon_types.STEPTREE
            labels = [x.label for x in wt]
            for w in WEAPONS.values():
                new, donor = w['teach']
                if donor in labels and new not in labels:
                    e = copy.deepcopy(wt[labels.index(donor)])
                    e.label = new
                    wt.append(e)
                    labels.append(new)
                    added.append('%s/%s %s<-%s' % (u.label, wc.name, new, donor))
    print('cyborg: %d label(s) taught: %s' % (len(added), ', '.join(added)))
    t.filepath = p
    save(t, p, write)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    # one port's own tags only (a weapon session): the shared cyborg labels are still
    # taught for every port (idempotent), the other ports' weapon tags are not rewritten
    ap.add_argument('--only', choices=sorted(WEAPONS))
    a = ap.parse_args()
    for key in ([a.only] if a.only else WEAPONS):
        edit_weapon(key, a.write)
        edit_drops(key, a.write)
        edit_death_drop(key, a.write)
        edit_palettes(key, a.write)
        if os.path.exists(path(WEAPONS[key]['fp_anims'], '.model_animations')):
            edit_fp_anims(key, a.write)
        else:
            print('   (no FP animation tag yet: python h1_fp_retarget.py %s --write, then '
                  'tool animations)' % key)
    teach_cyborg(a.write)
    if not a.write:
        print('\n(dry run -- --write to save)')


if __name__ == '__main__':
    main()

r"""Time-to-kill on LEGENDARY: the shared core of the Halo 3 and Halo 3: ODST collectors
(ttk_halo3.py, ttk_odst.py), on ttk_common's method.

READ-ONLY. Every tag is read from the H3EK / H3ODSTEK kit through ttk_common.flatten
(tool export-tag-to-xml into a PRIVATE temp file, deleted after). Nothing is written but
the game's reports/ttk/*.json (ttk_common.write).

What Halo 3 / ODST read where (tags + the kit's own field help strings in tool.exe):
  * enemy pools: the CHARACTER's 'vitality properties' legendary body / shield vitality
    (walked up the parent characters) -- they replace the model's 'new damage info'
    maxima (Elite model 30/70 -> 45/105, Brute model 60/1 -> 70/70). matg Difficulty
    'imposs. enemy vitality / shield' (help: "enemy maximum body / shield vitality scale
    on impossible difficulty") multiply on top.
  * the player pool: the player biped's model 'new damage info' body maximum vitality and
    shield maximum shield vitality; shield 'stun time' = the recharge delay.
  * damage per hit: jpt 'damage upper bound' (mean of its pair) x every matg damage-table
    [0] row for (jpt general_damage, specific_damage) x (material general armor, specific
    armor), each inherited up the matg Materials parent chain; ALL rows found multiply, a
    missing row = 1 (confirmed in game for Halo 3). Table [1] is the native Tilt table and
    is never read.
  * AI fire: the character's 'firing pattern properties' entry for the weapon (own block
    first, then the parents -> ai\generic). Its two 'firing patterns' are the two ends of
    the ACCURACY ramp (kit help: "At zero, the parameters of the first firing-pattern
    block is used. At 1, the parameters in the second block ... linearly interpolated");
    'weapons properties' gives 'legendary accuracy bounds' + 'legendary accuracy time'.
    'rate of fire' = "how many times per second we pull the trigger (zero = continuously
    held down)"; 'burst duration' / 'burst separation' (seconds); 'weapon damage modifier'
    ("zero = no modifier"). matg 'imposs. rate of fire' / 'imposs. burst separation' scale
    them, 'imposs. enemy damage' scales the damage.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc  # noqa: E402

MATG = r'globals\globals.globals'
TICK = 30.0          # jmad animations play at 30 frames per second


def r3(x):
    return None if x is None else round(x, 3)


class Tag(object):
    """One kit tag, read through ttk_common.flatten; every value read is logged."""

    def __init__(self, kit, path, log=None):
        self.kit = kit
        self.path = path
        self.v = tc.flatten(kit, path)
        self.log = log if log is not None else {}

    def raw(self, field):
        x = self.v.get(field)
        if x is None:
            x = self.v.get('@' + field)          # ODST's export prefixes a few blocks
        return None if x is None else x[1]

    def s(self, field, record=True):
        x = self.raw(field)
        x = '' if x is None else x
        if record:
            self.log['%s :: %s' % (self.path, field)] = x
        return x

    def ref(self, field, record=True):
        """A tag reference without its ',group' suffix ('' when empty)."""
        x = self.s(field, record)
        x = x.split(',')[0]
        return x if x and '�' not in x else ''

    def f(self, field, record=True):
        x = self.raw(field)
        val = tc.num(x) if x is not None else 0.0
        if record:
            self.log['%s :: %s' % (self.path, field)] = val
        return val

    def pair(self, field, record=True):
        x = self.raw(field) or '0,0'
        p = [float(a) for a in str(x).split(',')[:2]]
        if len(p) == 1:
            p.append(p[0])
        if record:
            self.log['%s :: %s' % (self.path, field)] = p
        return p

    def count(self, block):
        x = self.raw(block + '/#count')
        return int(tc.num(x)) if x is not None else 0


# ----------------------------------------------------------------------------- matg
DIALS = ('enemy damage', 'enemy vitality', 'enemy shield', 'enemy recharge', 'rate of fire',
         'burst separation', 'projectile error')


class Globals(object):
    def __init__(self, kit, log):
        self.t = Tag(kit, MATG, log)
        self.n_difficulty = self.t.count('difficulty')
        self.dial = self.dials(0)
        self.table = {}                              # group -> (index, {armour: mult})
        g0 = 'damage table/[0]/damage groups'
        for g in range(self.t.count(g0)):
            gname = self.t.s('%s/[%d]/name' % (g0, g), record=False)
            rows = {}
            am = '%s/[%d]/armor modifiers' % (g0, g)
            for a in range(self.t.count(am)):
                rows[self.t.s('%s/[%d]/name' % (am, a), record=False)] = \
                    self.t.f('%s/[%d]/damage multiplier' % (am, a), record=False)
            self.table[gname] = (g, rows)
        self.mats = {}                               # name -> (index, parent, gen, spec)
        for i in range(self.t.count('materials')):
            p = 'materials/[%d]/' % i
            self.mats[self.t.s(p + 'name', False)] = (
                i, self.t.s(p + 'parent name', False), self.t.s(p + 'general armor', False),
                self.t.s(p + 'specific armor', False))

    def dials(self, element, record=True):
        d = 'difficulty/[%d]/imposs. ' % element
        return {k: self.t.f(d + k, record) for k in DIALS}

    def armour(self, material):
        """(general armour, specific armour, chain): each the nearest non-blank value up
        the material's parent chain."""
        gen = spec = ''
        chain, name = [], material
        while name and name in self.mats and len(chain) < 20:
            i, parent, g, s = self.mats[name]
            chain.append('materials/[%d] %s (general %r, specific %r, parent %r)'
                         % (i, name, g, s, parent))
            gen = gen or g
            spec = spec or s
            name = parent
        return gen, spec, chain

    def multiplier(self, groups, material):
        """Product of every damage-table [0] row matching (group x armour), with detail."""
        gen, spec, chain = self.armour(material)
        out, detail = 1.0, {'material': material, 'material chain': chain,
                            'general armor': gen, 'specific armor': spec, 'rows': {}}
        for grp in [g for g in groups if g]:
            if grp not in self.table:
                detail['rows']['%s (no such damage group)' % grp] = 1.0
                continue
            gi, rows = self.table[grp]
            for arm in [a for a in (gen, spec) if a]:
                key = 'damage table/[0]/damage groups/[%d] %s x %s' % (gi, grp, arm)
                if arm in rows:
                    out *= rows[arm]
                    detail['rows'][key] = rows[arm]
                else:
                    detail['rows'][key + ' (no row = 1)'] = 1.0
        detail['product'] = out
        return out, detail


# ----------------------------------------------------------------------------- weapons
def anim_frames(kit, jmad, names, log):
    """{animation name: frame count} of a model_animation_graph."""
    a = Tag(kit, jmad + '.model_animation_graph', log)
    out = {}
    for i in range(a.count('definitions/animations')):
        nm = a.s('definitions/animations/[%d]/name' % i, False)
        if nm in names:
            out[nm] = a.f('definitions/animations/[%d]/frame count' % i)
    return out


def read_weapon(kit, path, log):
    w = Tag(kit, path + '.weapon', log)
    trig = 'new triggers/[0]/'
    bi = int(str(w.s(trig + 'primary barrel')).split(',')[-1] or 0)
    b = 'barrels/[%d]/' % max(bi, 0)
    m = 'magazines/[0]/'
    has_mag = w.count('magazines') and w.f(m + 'rounds loaded maximum') > 0
    d = {
        'tag': w.path,
        'trigger behavior': w.s(trig + 'behavior'),
        'barrel': b.rstrip('/'),
        'rps': w.pair(b + 'firing/rounds per second'),
        'accel': w.f(b + 'firing/acceleration time'),
        'decel': w.f(b + 'firing/deceleration time'),
        'shots per fire': w.pair(b + 'firing/shots per fire'),
        'fire recovery': w.f(b + 'firing/fire recovery time'),
        'projectiles per shot': w.f(b + 'projectiles per shot') or 1.0,
        'rounds per shot': w.f(b + 'rounds per shot'),
        'heat per round': w.f(b + 'heat generated per round'),
        'overheated threshold': w.f('overheated threshold'),
        'heat recovery threshold': w.f('heat recovery threshold'),
        'heat loss': w.f('heat loss per second'),
        'overheated heat loss': w.f('overheated heat loss per second'),
        'mag': int(w.f(m + 'rounds loaded maximum')) if has_mag else 0,
        'reload tag': w.f(m + 'reload time') if has_mag else 0.0,
        'projectile': w.ref(b + 'projectile'),
        'fp animations': w.ref('player interface/first person/[0]/first person animations'),
    }
    d['reload'] = d['reload tag']
    d['reload source'] = '%s :: %s' % (w.path, m + 'reload time')
    if d['fp animations']:
        fr = anim_frames(kit, d['fp animations'],
                         ('first_person:reload_empty', 'first_person:reload_full',
                          'first_person:fire_1', 'first_person:fire_1:var1'), log)
        d['fp animation frames'] = fr
        if 'first_person:reload_empty' in fr:
            fc = fr['first_person:reload_empty']
            d['reload animation'] = {'tag': d['fp animations'] + '.model_animation_graph',
                                     'animation': 'first_person:reload_empty',
                                     'frames': fc, 'seconds @30Hz': r3(fc / TICK)}
            if d['mag'] and not d['reload tag']:
                d['reload'] = fc / TICK
                d['reload source'] = '%s first_person:reload_empty %d frames / 30' % (
                    d['fp animations'], fc)
    p = Tag(kit, d['projectile'] + '.projectile', log)
    d['impact damage'] = p.ref('impact damage')
    d['air damage range'] = p.pair('air damage range')
    j = Tag(kit, d['impact damage'] + '.damage_effect', log)
    up = j.pair('damage upper bound')
    d['damage lower bound'] = j.f('damage lower bound')
    d['damage upper bound'] = up
    d['upper'] = sum(up) / 2.0
    d['general_damage'] = j.s('general_damage')
    d['specific_damage'] = j.s('specific_damage')
    return d


def sim_player(n, w, cool_while_firing=True):
    """Seconds until the n-th shot (first at 0), trigger held; events. Continuous time:
      * rate ramps from rounds per second [lo] to [hi] over 'acceleration time' of
        continuous fire, from each (re)start (after an overheat or a reload);
      * 'shots per fire' > 1 = a burst at the barrel rate, then 'fire recovery time' from
        the burst's last round to the next burst; a single-shot weapon with 0 rounds per
        second fires every 'fire recovery time';
      * heat + per round; 'heat loss per second' runs between shots when
        cool_while_firing (else never while the trigger is held -- the kit help: "heat lost
        each second when the weapon is not being fired"); reaching the overheated threshold
        stops the gun until heat falls to the recovery threshold at the 'overheated heat
        loss per second';
      * an empty magazine costs the reload time before the next shot."""
    if n is None:
        return None, {}
    lo, hi = w['rps']
    burst = int(w['shots per fire'][1]) if w['shots per fire'][1] > 1 else 1
    t, start, heat, inmag, in_burst = 0.0, 0.0, 0.0, w['mag'], 0
    ev = {'overheats': 0, 'reloads': 0, 'bursts started': 1 if n else 0, 'first overheat at shot': None}
    for k in range(1, n + 1):
        if k == n:
            return t, ev
        heat += w['heat per round']
        in_burst += 1
        held = t - start
        if hi > 0:
            rate = hi if not w['accel'] else lo + (hi - lo) * min(1.0, held / w['accel'])
            dt = 1.0 / rate
        else:
            dt = w['fire recovery']                   # semi-auto, recovery-limited
        if burst > 1:
            if in_burst >= burst:
                dt = max(dt, w['fire recovery'])
                in_burst = 0
                ev['bursts started'] += 1
        elif w['fire recovery']:
            dt = max(dt, w['fire recovery'])
        restart = False
        if w['heat per round'] and heat >= w['overheated threshold'] - 1e-9:
            pause = (heat - w['heat recovery threshold']) / w['overheated heat loss']
            dt = max(dt, pause)
            heat = w['heat recovery threshold']
            ev['overheats'] += 1
            if ev['first overheat at shot'] is None:
                ev['first overheat at shot'] = k
            ev['overheat pause s'] = r3(pause)
            restart = True
        elif cool_while_firing:
            heat = max(0.0, heat - w['heat loss'] * dt)
        if w['mag']:
            inmag -= 1
            if inmag <= 0:
                dt = max(dt, w['reload'])
                inmag = w['mag']
                ev['reloads'] += 1
                in_burst = 0
                restart = True
        ev['longest gap s'] = r3(max(ev.get('longest gap s') or 0.0, dt))
        t += dt
        if restart:
            start = t
    return None, ev


# ----------------------------------------------------------------------------- AI + models
def char_chain(kit, path, log):
    out, seen = [], set()
    path = path.replace('.character', '')
    while path and path not in seen and len(out) < 8:
        seen.add(path)
        t = Tag(kit, path + '.character', log)
        out.append(t)
        path = t.ref('parent character')
    return out


def char_entry(chain, block, weapon):
    """(tag, prefix) of the first block element whose 'weapon' is `weapon`, own first."""
    for t in chain:
        for i in range(t.count(block)):
            if t.ref('%s/[%d]/weapon' % (block, i), False) == weapon:
                t.s('%s/[%d]/weapon' % (block, i))
                return t, '%s/[%d]/' % (block, i)
    return None, None


def char_vitality(chain):
    for t in chain:
        if t.count('vitality properties'):
            return t, 'vitality properties/[0]/'
    return None, None


def model_damage_info(kit, path, log, body_material):
    m = Tag(kit, path, log)
    p = 'new damage info/[0]/'
    d = {'tag': path,
         'maximum vitality': m.f(p + 'body/maximum vitality'),
         'maximum shield vitality': m.f(p + 'shield/maximum shield vitality'),
         'global shield material name': m.s(p + 'shield/global shield material name'),
         'shield stun time (recharge delay)': m.f(p + 'shield/stun time'),
         'shield recharge time': m.f(p + 'shield/recharge time'),
         'body stun time': m.f(p + 'body/stun time'),
         'body recharge time': m.f(p + 'body/recharge time'),
         'body recharge fraction': m.f(p + 'body/recharge fraction'),
         'global indirect material name': m.s(p + 'global indirect material name')}
    d['body material'] = None
    for i in range(m.count('materials')):
        if m.s('materials/[%d]/material name' % i, False) == body_material:
            d['body material'] = m.s('materials/[%d]/global material name' % i)
            d['body material slot'] = 'materials/[%d] %s' % (i, body_material)
    return d


def biped_model(kit, biped, log):
    b = Tag(kit, biped + '.biped', log)
    return b.ref('unit/object/model') + '.model'


# ----------------------------------------------------------------------------- the run
def run(kit, game, player, enemies, player_weapons, extra_notes=()):
    """player: dict(label, biped, body_material, explain)
    enemies: [(label, character, body material name, AI weapon path, AI weapon label,
               weapon note[, ai_only])] -- ai_only: measure only this enemy -> player
    player_weapons: [(label, weapon path)]"""
    rows = []
    glog = {}
    g = Globals(kit, glog)
    dial = g.dial
    alt = g.dials(1, record=True) if g.n_difficulty > 1 else None

    plog = {}
    p_model = biped_model(kit, player['biped'], plog)
    pm = model_damage_info(kit, p_model, plog, player['body_material'])
    p_sh, p_body = pm['maximum shield vitality'], pm['maximum vitality']
    p_delay = pm['shield stun time (recharge delay)']
    plabel = player['label']

    weapons = {}
    for label, wpath in player_weapons:
        wl = {}
        weapons[label] = (read_weapon(kit, wpath, wl), wl)

    for entry in enemies:
        elabel, cpath, body_mat_name, eweap, eweap_label, eweap_note = entry[:6]
        ai_only = len(entry) > 6 and entry[6]          # a second AI weapon: enemy->player only
        clog = {}
        chain = char_chain(kit, cpath, clog)
        ch = chain[0]
        vt, vp = char_vitality(chain)
        leg_body = vt.f(vp + 'legendary body vitality')
        leg_sh = vt.f(vp + 'legendary shield vitality')
        vt.f(vp + 'normal body vitality')
        vt.f(vp + 'normal shield vitality')
        sh_delay_raw = vt.f(vp + 'shield recharge delay time')
        body_delay = vt.f(vp + 'body recharge delay time')
        body_frac = vt.f(vp + 'body recharge fraction')
        unit = ch.ref('unit') or next((t.ref('unit') for t in chain if t.ref('unit')), '')
        em = model_damage_info(kit, biped_model(kit, unit, clog), clog, body_mat_name)
        e_body = leg_body * dial['enemy vitality']
        e_sh = leg_sh * dial['enemy shield']
        sh_delay = sh_delay_raw * dial['enemy recharge']
        target_in = {
            'character': ch.path, 'vitality from': vt.path, 'unit': unit,
            'legendary body vitality': leg_body, 'legendary shield vitality': leg_sh,
            'model new damage info (replaced by the character)': {
                k: em[k] for k in ('tag', 'maximum vitality', 'maximum shield vitality')},
            'shield material': em['global shield material name'],
            'body material': '%s -> %s' % (em.get('body material slot'), em['body material']),
            'matg imposs. enemy vitality': dial['enemy vitality'],
            'matg imposs. enemy shield': dial['enemy shield'],
            'shield pool': r3(e_sh), 'body pool': r3(e_body),
            'character shield recharge delay time': sh_delay_raw,
            'matg imposs. enemy recharge': dial['enemy recharge'],
            'shield recharge delay used (delay x enemy recharge, ASSUMED)': r3(sh_delay),
            'body recharge delay time / fraction': [body_delay, body_frac],
            'fields read': clog}

        # ---------- player -> enemy
        for label, _wp in ([] if ai_only else player_weapons):
            w, wl = weapons[label]
            groups = (w['general_damage'], w['specific_damage'])
            m_sh, d_sh = g.multiplier(groups, em['global shield material name'])
            m_bo, d_bo = g.multiplier(groups, em['body material'])
            sh = w['upper'] * w['projectiles per shot'] * m_sh
            bo = w['upper'] * w['projectiles per shot'] * m_bo
            n, _ = tc.shots_to_kill(e_sh, e_body, sh, bo)
            t, ev = sim_player(n, w)
            flags = []
            if e_sh > 0 and t is not None and t > sh_delay:
                flags.append('fight (%.2f s) outlasts the shield recharge delay %.2f s '
                             '(character %.0f s x matg enemy recharge %.2f, assumed to scale '
                             'the delay) -- recharge not modelled' % (t, sh_delay, sh_delay_raw,
                                                                      dial['enemy recharge']))
                if t <= sh_delay_raw:
                    flags.append('(inside the raw %.0f s delay if the dial does not scale it)'
                                 % sh_delay_raw)
            gap = ev.get('longest gap s') or 0.0
            if e_sh > 0 and gap >= sh_delay:
                flags.append('a single pause in fire (%.2f s, overheat/reload) is itself >= the '
                             'shield recharge delay %.2f s: in game the shield would start '
                             'recharging mid-fight' % (gap, sh_delay))
            if body_frac and t is not None and t > body_delay:
                flags.append('fight (%.2f s) outlasts the body recharge delay %.1f s '
                             '(recharges %.0f%% of body) -- not modelled'
                             % (t, body_delay, body_frac * 100))
            if w['rps'][0] != w['rps'][1]:
                flags.append('rate ramps %.0f -> %.0f rounds/s over %.2f s held (re-ramps after '
                             'each overheat / reload)' % (w['rps'][0], w['rps'][1], w['accel']))
            alt_cool = None
            if w['heat per round']:
                alt_cool = sim_player(n, w, cool_while_firing=False)
                if ev.get('overheats'):
                    flags.append('%d overheat(s) during the kill: shot %s overheats the gun '
                                 '(heat loss assumed to run between shots, like the H2 '
                                 'collector), the cool-down to the recovery threshold costs '
                                 '%.2f s' % (ev['overheats'], ev['first overheat at shot'],
                                             ev.get('overheat pause s') or 0))
                flags.append('if heat only falls while NOT firing (kit help text; user-confirmed '
                             'for Halo 4\'s Focus Rifle): %s s, %d overheat(s), first at shot %s'
                             % (r3(alt_cool[0]), alt_cool[1].get('overheats', 0),
                                alt_cool[1].get('first overheat at shot')))
            if ev.get('reloads'):
                flags.append('%d reload(s) during the kill (%.2f s each, %s)'
                             % (ev['reloads'], w['reload'], w['reload source']))
            if int(w['shots per fire'][1]) > 1:
                flags.append('%d-round bursts at %.0f/s, %.2f s fire recovery from a burst\'s '
                             'last round to the next burst (assumed timing); %d bursts'
                             % (int(w['shots per fire'][1]), w['rps'][1], w['fire recovery'],
                                ev.get('bursts started', 0)))
            alt_anim = None
            if w['rps'][1] <= 0:
                fr = w.get('fp animation frames', {})
                ff = fr.get('first_person:fire_1:var1') or fr.get('first_person:fire_1')
                if ff:
                    alt_anim = sim_player(n, dict(w, **{'fire recovery': ff / TICK}))[0]
                flags.append('rounds per second 0: a semi-automatic trigger; the gun cycles every '
                             'fire recovery time %.3f s (%.1f shots/s) -- the engine limit, '
                             'faster than a human trigger finger%s'
                             % (w['fire recovery'], 1 / w['fire recovery'],
                                '; at one shot per %d-frame fire_1 animation (%.1f/s, NOT a '
                                'confirmed limit): %.2f s' % (ff, TICK / ff, alt_anim)
                                if alt_anim is not None else ''))
            if w.get('reload animation') and w['reload tag'] and w['mag'] and ev.get('reloads'):
                ra = w['reload animation']
                flags.append('reload uses the magazine reload time %.2f s; the first-person '
                             'reload_empty animation is %d frames = %.2f s'
                             % (w['reload tag'], ra['frames'], ra['seconds @30Hz']))
            lo_d, rng = w['damage lower bound'], w['air damage range']
            flags.append('point-blank damage: the jpt upper bound; the lower bound %.2f applies '
                         'toward the end of the projectile air damage range %.0f-%.0f wu '
                         '(not modelled)' % (lo_d, rng[0], rng[1]))
            cross = None
            if w['rps'][0] == w['rps'][1] and w['rps'][1] > 0 and not w['heat per round'] and \
                    int(w['shots per fire'][1]) <= 1 and w['fire recovery'] <= 1.0 / w['rps'][1]:
                cross = tc.player_time(n, 1.0 / w['rps'][1], w['mag'], w['reload'])
                assert abs(cross - t) < 1e-6, (label, cross, t)
            inputs = {
                'weapon': dict(w),
                'damage multipliers': {'shield': d_sh, 'body': d_bo},
                'shield hit': r3(sh), 'body hit': r3(bo),
                'target': target_in,
                'events in the kill': ev,
                'ttk_common.player_time cross-check (constant-rate weapons)': r3(cross),
                'fields read (weapon)': wl,
                'fields read (matg)': glog}
            if alt is not None:
                n_alt, _ = tc.shots_to_kill(leg_sh * alt['enemy shield'],
                                            leg_body * alt['enemy vitality'], sh, bo)
                inputs['IF matg difficulty [1] were used (vitality %.2f, shield %.2f)'
                       % (alt['enemy vitality'], alt['enemy shield'])] = {
                    'shots': n_alt, 'seconds': r3(sim_player(n_alt, w)[0])}
            rows.append({'direction': 'player->enemy', 'attacker': plabel,
                         'target': elabel, 'weapon': label, 'shots': n, 'seconds': r3(t),
                         'inputs': inputs, 'flags': flags})

        # ---------- enemy -> player
        wl = {}
        w = read_weapon(kit, eweap, wl)
        fpt, fpp = char_entry(chain, 'firing pattern properties', eweap)
        wpt, wpp = char_entry(chain, 'weapons properties', eweap)
        acc_lo, acc_hi = wpt.pair(wpp + 'legendary accuracy bounds')
        acc_time = wpt.f(wpp + 'legendary accuracy time')
        first_burst = wpt.pair(wpp + 'first burst delay time')
        pats = []
        for i in range(fpt.count(fpp + 'firing patterns')):
            q = fpp + 'firing patterns/[%d]/' % i
            pats.append({'rate of fire': fpt.f(q + 'rate of fire'),
                         'burst duration': fpt.pair(q + 'burst duration'),
                         'burst separation': fpt.pair(q + 'burst separation'),
                         'weapon damage modifier': fpt.f(q + 'weapon damage modifier')})

        def at_acc(a, key):
            vals = [sum(p[key]) / 2.0 if isinstance(p[key], list) else p[key] for p in pats]
            if len(vals) == 1:
                return vals[0]
            return vals[0] + (vals[1] - vals[0]) * a

        def pulls(a):
            rs = [p['rate of fire'] or w['rps'][1] for p in pats]
            return rs[0] + (rs[-1] - rs[0]) * a

        def wdm_at(a):
            vals = [p['weapon damage modifier'] or 1.0 for p in pats]   # 0 = no modifier
            return vals[0] + (vals[-1] - vals[0]) * a

        a = acc_hi
        wdm = wdm_at(a)
        burst_w = int(w['shots per fire'][1]) if w['shots per fire'][1] > 1 else 1

        def ai_case(dials, a):
            mul = dials['enemy damage'] * wdm_at(a) * w['projectiles per shot']
            groups = (w['general_damage'], w['specific_damage'])
            m_sh, d_sh = g.multiplier(groups, pm['global shield material name'])
            m_bo, d_bo = g.multiplier(groups, pm['body material'])
            sh, bo = w['upper'] * m_sh * mul, w['upper'] * m_bo * mul
            n, _ = tc.shots_to_kill(p_sh, p_body, sh, bo)
            ai_pulls = pulls(a) * dials['rate of fire']
            w_max = w['rps'][1] if w['rps'][1] > 0 else 1.0 / max(w['fire recovery'], 1e-6)
            rate = min(ai_pulls, w_max)
            bd = at_acc(a, 'burst duration')
            bs = at_acc(a, 'burst separation') * dials['burst separation']
            held, paced = tc.ai_times(n, rate, bd, bs)
            return dict(n=n, sh=sh, bo=bo, d_sh=d_sh, d_bo=d_bo, pulls=ai_pulls, rate=rate,
                        w_max=w_max, bd=bd, bs=bs, held=held, paced=paced,
                        uncapped=tc.ai_times(n, ai_pulls, bd, bs))

        c = ai_case(dial, a)
        c0 = ai_case(dial, acc_lo)
        flags = [
            'AI weapon %s: %s' % (eweap.split('\\')[-1], eweap_note),
            'AI rate = firing-pattern rate of fire (trigger pulls/s; 0 = held = weapon rounds per '
            'second) x matg imposs. rate of fire %.2f = %.2f/s, CAPPED at the weapon\'s %.2f/s '
            '(uncapped: held %.2f s, paced %.2f s)'
            % (dial['rate of fire'], c['pulls'], c['w_max'], c['uncapped'][0] or 0,
               c['uncapped'][1] or 0),
            'firing pattern at legendary accuracy %.2f (end of the %.2f -> %.2f ramp over %.1f s); '
            'at the ramp start (%.2f): %d hits, held %.2f s, paced %.2f s'
            % (a, acc_lo, acc_hi, acc_time, acc_lo, c0['n'], c0['held'] or 0, c0['paced'] or 0),
            'burst duration / separation are ranges: means used; separation x matg imposs. '
            'burst separation %.2f' % dial['burst separation'],
            'not counted: first burst delay %s s, misses, AI weapon heat / overheat%s'
            % (first_burst, ' (this weapon overheats: heat %.2f per round)' % w['heat per round']
               if w['heat per round'] else '')]
        if burst_w > 1:
            flags.append('the weapon fires %d-round bursts per trigger pull: shots counted as '
                         'rounds, pacing per round (not modelled per burst)' % burst_w)
        if c['paced'] is not None and c['paced'] > p_delay:
            flags.append('paced time (%.2f s) outlasts the player shield recharge delay %.1f s '
                         '(model shield stun time) -- recharge not modelled' % (c['paced'], p_delay))
        if c['bs'] >= p_delay:
            flags.append('one burst separation (%.2f s) alone is >= the player shield recharge '
                         'delay %.1f s' % (c['bs'], p_delay))
        inputs = {
            'attacker character chain': [t.path for t in chain],
            'firing pattern from': '%s :: %s' % (fpt.path, fpp),
            'weapons properties from': '%s :: %s' % (wpt.path, wpp),
            'firing patterns': pats,
            'legendary accuracy bounds / time': [acc_lo, acc_hi, acc_time],
            'weapon': w,
            'damage multipliers': {'shield': c['d_sh'], 'body': c['d_bo'],
                                   'matg imposs. enemy damage': dial['enemy damage'],
                                   'firing pattern weapon damage modifier (0 = none)': wdm},
            'shield hit': r3(c['sh']), 'body hit': r3(c['bo']),
            'target': {'biped': player['biped'], 'model': pm['tag'], 'shield pool': p_sh,
                       'body pool': p_body,
                       'shield material': pm['global shield material name'],
                       'body material': '%s -> %s' % (pm.get('body material slot'),
                                                      pm['body material']),
                       'shield recharge delay (model shield stun time)': p_delay,
                       'shield recharge time': pm['shield recharge time'],
                       'body recharge time / fraction': [pm['body recharge time'],
                                                         pm['body recharge fraction']],
                       'what the pools are': player.get('explain', ''),
                       'fields read': plog},
            'matg imposs. rate of fire': dial['rate of fire'],
            'AI trigger pulls per second (pattern x dial)': r3(c['pulls']),
            'shots per second used (capped)': r3(c['rate']),
            'burst duration used (mean)': r3(c['bd']),
            'burst separation used (mean x dial)': r3(c['bs']),
            'ramp start (accuracy %.2f)' % acc_lo: {'hits': c0['n'], 'held': r3(c0['held']),
                                                    'paced': r3(c0['paced']),
                                                    'rate': r3(c0['rate'])},
            'fields read': dict(clog, **wl),
            'fields read (matg)': glog}
        if alt is not None:
            ca = ai_case(alt, a)
            inputs['IF matg difficulty [1] were used (enemy damage %.2f)' % alt['enemy damage']] = {
                'hits': ca['n'], 'held': r3(ca['held']), 'paced': r3(ca['paced'])}
        rows.append({'direction': 'enemy->player', 'attacker': elabel,
                     'target': plabel, 'weapon': eweap_label,
                     'shots': c['n'], 'seconds': r3(c['held']), 'seconds_paced': r3(c['paced']),
                     'inputs': inputs, 'flags': flags})

    notes = [
        'Source: %s tags (%s), read with ttk_common.flatten (private temp export); nothing in '
        'the kit was written.' % (kit, os.path.join(tc.STEAM, kit, 'tags')),
        'Legendary = matg Difficulty [0] "imposs." column: enemy damage %.2f, enemy vitality '
        '%.2f, enemy shield %.2f, enemy recharge %.2f, rate of fire %.2f, burst separation %.2f.'
        % (dial['enemy damage'], dial['enemy vitality'], dial['enemy shield'],
           dial['enemy recharge'], dial['rate of fire'], dial['burst separation']),
        'Enemy pools = the character\'s "legendary body / shield vitality" (they replace the '
        'model maxima); the matg vitality / shield dials multiply on top.',
        'Damage per hit = jpt damage upper bound (mean of the pair) x every matg damage-table '
        '[0] row for (jpt general_damage, specific_damage) x (material general armor, specific '
        'armor), materials resolved up the parent chain; missing row = 1. Player shields (and in '
        'Halo 3 the Chief / Elite armour) carry the specific armours energy_shield_thin_player / '
        'hard_metal_thin_player, but table [0] has rows for them only in no_damage, so they '
        'multiply by 1 here; every row looked up is listed per row under inputs.',
        'Player times: continuous-time trigger simulation (ttk_h3family.sim_player): ramp lo->hi '
        'over acceleration time, bursts + fire recovery, heat with heat loss between shots and '
        'the overheated cool-down to the recovery threshold, reloads (magazine reload time; '
        'when it is 0 the reload is animation-driven: first-person reload_empty frames / 30). '
        'Constant-rate weapons are asserted equal to ttk_common.player_time.',
        'Enemy shield recharge: character delay x matg "enemy recharge" (help: "enemy shield '
        'recharge scale") %.2f -- ASSUMED to scale the delay (it falls with difficulty: 1.4 '
        'easy -> 0.3 legendary, so it cannot be a recharge speed). Flags use the scaled delay.'
        % dial['enemy recharge'],
        'AI fire: the character\'s firing pattern for the weapon (from ai\\generic; the minor '
        'characters define none of their own); the steady state of the legendary accuracy ramp '
        'is used (second firing pattern), the ramp start is in the flags. AI rate capped at the '
        'weapon\'s own rate. Paced = ttk_common.ai_times with the mean burst duration and '
        'separation.',
        'Not modelled: headshots, melee, grenades, misses, AI weapon heat, damage falloff with '
        'range, the first-burst delay, damage-section (region) pools, Brute armour pieces.',
    ]
    if alt is not None:
        notes.append('This globals has %d Difficulty elements; [0] is used. [1] reads enemy '
                     'damage %.2f, vitality %.2f, shield %.2f, recharge %.2f (probably Firefight / '
                     'a second mode -- unconfirmed); rows carry an "IF matg difficulty [1]" input.'
                     % (g.n_difficulty, alt['enemy damage'], alt['enemy vitality'],
                        alt['enemy shield'], alt['enemy recharge']))
    notes += list(extra_notes)
    path = tc.write(game, rows, notes)
    for row in rows:
        print('%-14s %-34s -> %-22s hits %-4s %7s s%s' % (
            row['direction'], row['attacker'] + ' / ' + row['weapon'], row['target'],
            row['shots'], row['seconds'],
            ('  paced %s s' % row['seconds_paced']) if 'seconds_paced' in row else ''))
        print('    shield hit %s body hit %s | %s' % (
            row['inputs']['shield hit'], row['inputs']['body hit'], ' | '.join(row['flags'])))
    print(path)
    return rows

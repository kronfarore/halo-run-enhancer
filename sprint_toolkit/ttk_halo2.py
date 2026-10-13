r"""Time-to-kill on LEGENDARY: the Halo 2 (MCC) collector (ttk_common's method).

READ-ONLY. Every tag is read from the H2EK kit through ttk_common.flatten (tool
export-tag-to-xml into a PRIVATE temp file, deleted after). Nothing is written but
reports/ttk/ttk_halo_2.json.

What Halo 2 reads where (found in the tags and the kit's own field help strings):
  * enemy pools: the CHARACTER's 'vitality properties' -- 'legendary body / shield
    vitality' ("maximum body vitality of our unit (on legendary)") -- override the model's
    'new damage info' maxima. The matg Difficulty 'imposs. enemy vitality / shield' dials
    multiply on top (both 1.0 in the shipped globals).
  * the player pool: masterchief.model 'new damage info' maximum vitality / shield.
  * damage per hit: jpt 'damage upper bound' (mean of its pair) x the matg damage table
    rows: jpt general_damage / specific_damage groups x the hit material's general /
    specific armour (resolved up the matg Materials parent chain); every row found
    multiplies, a missing row = 1. AI damage also x matg 'imposs. enemy damage' and the
    firing pattern's 'weapon damage modifier' (zero = no modifier).
  * AI fire: the character's 'firing pattern properties' entry for the weapon (own block
    first, then the parent character ai\generic). Its two 'firing patterns' are the two
    ends of the ACCURACY ramp (kit help: "At zero, the parameters of the first
    firing-pattern block is used. At 1, the parameters in the second"); the
    'weapons properties' entry gives the legendary accuracy bounds + time. 'rate of fire'
    is trigger pulls per second ("zero = continuously held down" -> the weapon's own
    rounds per second). matg 'imposs. rate of fire' scales the rate, 'imposs. burst
    separation' scales the separation.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc  # noqa: E402

KIT = 'H2EK'
GAME = 'Halo 2'
MATG = r'globals\globals.globals'
PLAYER_MODEL = r'objects\characters\masterchief\masterchief.model'
PLAYER_BODY_MATERIAL = 'body'          # model material name hit by a body shot

ENEMIES = [
    # label, character, body material name on the model, default weapon (ASSUMED, see notes)
    ('Elite minor', r'objects\characters\elite\ai\elite.character', 'armored_torso',
     r'objects\weapons\rifle\plasma_rifle\plasma_rifle', 'Plasma Rifle (AI)'),
    ('Brute minor', r'objects\characters\brute\ai\brute.character', 'body',
     r'objects\weapons\rifle\brute_plasma_rifle\brute_plasma_rifle', 'Brute Plasma Rifle (AI)'),
]
PLAYER_WEAPONS = [
    ('SMG', r'objects\weapons\rifle\smg\smg'),
    ('Plasma Rifle', r'objects\weapons\rifle\plasma_rifle\plasma_rifle'),
    ('Battle Rifle', r'objects\weapons\rifle\battle_rifle\battle_rifle'),
]
# reload ANIMATION used when the magazine's 'reload time' is 0 (the reload is then
# animation-driven): first-person graph, animation, frames at 30 Hz
RELOAD_ANIM = {
    r'objects\weapons\rifle\battle_rifle\battle_rifle':
        (r'objects\characters\masterchief\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle'
         r'.model_animation_graph', 'first_person:reload_empty'),
    r'objects\weapons\rifle\smg\smg':
        (r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg.model_animation_graph',
         'first_person:reload_empty'),
}
TICK = 30.0


def r3(x):
    return None if x is None else round(x, 3)


class Tag(object):
    """One kit tag, read through ttk_common.flatten; every value read is logged."""

    def __init__(self, path, log=None):
        self.path = path
        self.v = tc.flatten(KIT, path)
        self.log = log if log is not None else {}

    def raw(self, field):
        return self.v.get(field, (None, None))[1]

    def s(self, field, record=True):
        x = self.raw(field)
        x = '' if x is None else x
        if record:
            self.log['%s :: %s' % (self.path, field)] = x
        return x

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
        return int(tc.num(self.v.get(block + '/#count', ('count', '0'))))


# ----------------------------------------------------------------------------- matg
class Globals(object):
    def __init__(self, log):
        self.t = Tag(MATG, log)
        d = 'difficulty/[0]/imposs. '
        self.dial = {k: self.t.f(d + k) for k in (
            'enemy damage', 'enemy vitality', 'enemy shield', 'enemy recharge',
            'rate of fire', 'burst separation', 'projectile error')}
        # damage table: {group: {armour: multiplier}}
        self.table = {}
        g0 = 'damage table/[0]/damage groups'
        for g in range(self.t.count(g0)):
            gname = self.t.s('%s/[%d]/name' % (g0, g), record=False)
            rows = {}
            am = '%s/[%d]/armor modifiers' % (g0, g)
            for a in range(self.t.count(am)):
                rows[self.t.s('%s/[%d]/name' % (am, a), record=False)] = \
                    self.t.f('%s/[%d]/damage multiplier' % (am, a), record=False)
            self.table[gname] = (g, rows)
        # materials: name -> (index, parent, general, specific)
        self.mats = {}
        for i in range(self.t.count('materials')):
            p = 'materials/[%d]/' % i
            self.mats[self.t.s(p + 'name', False)] = (
                i, self.t.s(p + 'parent name', False), self.t.s(p + 'general armor', False),
                self.t.s(p + 'specific armor', False))

    def armour(self, material):
        """(general armour, specific armour, chain) of a global material, each inherited up
        the parent chain when blank."""
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
        """Product of every damage-table row matching (group x armour); detail dict."""
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
def read_weapon(path, log):
    w = Tag(path + '.weapon', log)
    b = 'barrels/[0]/'
    m = 'magazines/[0]/'
    d = {
        'tag': w.path,
        'trigger behavior': w.s('new triggers/[0]/behavior'),
        'rps': w.pair(b + 'rounds per second'),
        'accel': w.f(b + 'acceleration time'),
        'shots per fire': w.pair(b + 'shots per fire'),
        'fire recovery': w.f(b + 'fire recovery time'),
        'projectiles per shot': w.f(b + 'projectiles per shot') or 1.0,
        'heat per round': w.f(b + 'heat generated per round'),
        'overheated threshold': w.f('overheated threshold'),
        'heat recovery threshold': w.f('heat recovery threshold'),
        'heat loss': w.f('heat loss per second'),
        'overheated heat loss': w.f('overheated heat loss per second'),
        'mag': int(w.f(m + 'rounds loaded maximum')) if w.count('magazines') else 0,
        'reload tag': w.f(m + 'reload time') if w.count('magazines') else 0.0,
        'projectile': w.s(b + 'projectile'),
    }
    d['reload'] = d['reload tag']
    d['reload source'] = '%s :: %s' % (w.path, m + 'reload time')
    if path in RELOAD_ANIM:
        jmad, name = RELOAD_ANIM[path]
        a = Tag(jmad, log)
        for i in range(a.count('animations')):
            if a.s('animations/[%d]/name' % i, False) == name:
                fc = a.f('animations/[%d]/frame count' % i)
                d['reload animation'] = {'tag': jmad, 'animation': name, 'frames': fc,
                                         'seconds @30Hz': r3(fc / TICK)}
                if d['mag'] and not d['reload tag']:
                    d['reload'] = fc / TICK
                    d['reload source'] = '%s %s frame count / 30' % (jmad, name)
                break
    p = Tag(d['projectile'] + '.projectile', log)
    d['impact damage'] = p.s('impact damage')
    d['air damage range'] = p.pair('air damage range')
    j = Tag(d['impact damage'] + '.damage_effect', log)
    up = j.pair('damage upper bound')
    d['damage lower bound'] = j.f('damage lower bound')
    d['damage upper bound'] = up
    d['upper'] = sum(up) / 2.0
    d['general_damage'] = j.s('general_damage')
    d['specific_damage'] = j.s('specific_damage')
    return d


def sim_player(n, w):
    """Seconds until the n-th shot (first at 0), trigger held. Continuous time:
      * rate ramps from rounds per second [lo] to [hi] over 'acceleration time' from the
        moment the trigger (re)starts (after an overheat or reload);
      * 'shots per fire' > 1 = a burst at the barrel rate, then 'fire recovery time' from
        the burst's last shot to the next burst;
      * heat + per round, - 'heat loss per second' continuously; reaching the overheated
        threshold stops the gun until heat falls to the recovery threshold at the
        'overheated heat loss per second';
      * an empty magazine costs the reload time before the next shot."""
    if n is None:
        return None, {}
    lo, hi = w['rps']
    burst = int(w['shots per fire'][1]) if w['shots per fire'][1] > 1 else 1
    t, start, heat, inmag, in_burst = 0.0, 0.0, 0.0, w['mag'], 0
    ev = {'overheats': 0, 'reloads': 0, 'bursts': 0}
    for k in range(1, n + 1):
        if k == n:
            return t, ev
        # the k-th shot leaves at t
        heat += w['heat per round']
        in_burst += 1
        held = t - start
        rate = hi if not w['accel'] else lo + (hi - lo) * min(1.0, held / w['accel'])
        dt = 1.0 / rate
        if burst > 1:
            if in_burst >= burst:
                dt = max(dt, w['fire recovery'])
                in_burst = 0
                ev['bursts'] += 1
        elif w['fire recovery']:
            dt = max(dt, w['fire recovery'])
        restart = False
        if w['heat per round'] and heat >= w['overheated threshold'] - 1e-9:
            pause = (heat - w['heat recovery threshold']) / w['overheated heat loss']
            dt = max(dt, pause)
            heat = w['heat recovery threshold']
            ev['overheats'] += 1
            restart = True
        else:
            heat = max(0.0, heat - w['heat loss'] * dt)
        if w['mag']:
            inmag -= 1
            if inmag <= 0:
                dt = max(dt, w['reload'])
                inmag = w['mag']
                ev['reloads'] += 1
                in_burst = 0
                restart = True
        t += dt
        if restart:
            start = t
    return None, ev


def tick_rate(rate):
    """Shots per second a 30 Hz accumulator that resets on each shot gives (the H1
    collector's measured trigger; NOT measured for Halo 2 -- cross-check only)."""
    if rate <= 0:
        return 0.0
    n, s = 0, 0.0
    while s < 1.0 - 1e-9:
        s += rate / TICK
        n += 1
    return TICK / n


# ----------------------------------------------------------------------------- AI
def char_chain(path, log):
    out, seen = [], set()
    while path and path not in seen and len(out) < 8:
        seen.add(path)
        t = Tag(path + ('' if path.endswith('.character') else '.character'), log)
        out.append(t)
        path = t.s('parent character')
    return out


def char_entry(chain, block, weapon):
    """(tag, prefix) of the first block element whose 'weapon' is `weapon`, own first."""
    for t in chain:
        for i in range(t.count(block)):
            if t.s('%s/[%d]/weapon' % (block, i), False) == weapon:
                t.s('%s/[%d]/weapon' % (block, i))
                return t, '%s/[%d]/' % (block, i)
    return None, None


def char_vitality(chain):
    """First character in the chain with a vitality properties element."""
    for t in chain:
        if t.count('vitality properties'):
            return t, 'vitality properties/[0]/'
    return None, None


def model_damage_info(path, log, body_material):
    m = Tag(path, log)
    p = 'new damage info/[0]/'
    d = {'tag': path,
         'maximum vitality': m.f(p + 'maximum vitality'),
         'maximum shield vitality': m.f(p + 'maximum shield vitality'),
         'global shield material name': m.s(p + 'global shield material name'),
         'shield stun time (recharge delay)': m.f(p + "stun time'"),
         'shield recharge time': m.f(p + "recharge time'"),
         'body stun time': m.f(p + 'stun time'),
         'body recharge fraction': m.f(p + 'recharge fraction')}
    d['body material'] = None
    for i in range(m.count('materials')):
        if m.s('materials/[%d]/material name' % i, False) == body_material:
            d['body material'] = m.s('materials/[%d]/global material name' % i)
            d['body material slot'] = 'materials/[%d] %s' % (i, body_material)
    return d


# ----------------------------------------------------------------------------- main
def main():
    rows, notes = [], []
    glog = {}
    g = Globals(glog)
    dial = g.dial

    # ---------------- player
    plog = {}
    pm = model_damage_info(PLAYER_MODEL, plog, PLAYER_BODY_MATERIAL)
    p_sh, p_body = pm['maximum shield vitality'], pm['maximum vitality']
    p_delay = pm['shield stun time (recharge delay)']

    weapons = {}
    for label, wpath in PLAYER_WEAPONS:
        wl = {}
        weapons[label] = (read_weapon(wpath, wl), wl)

    for elabel, cpath, body_mat_name, eweap, eweap_label in ENEMIES:
        clog = {}
        chain = char_chain(cpath.replace('.character', ''), clog)
        ch = chain[0]
        vt, vp = char_vitality(chain)
        leg_body = vt.f(vp + 'legendary body vitality')
        leg_sh = vt.f(vp + 'legendary shield vitality')
        vt.f(vp + 'normal body vitality')
        vt.f(vp + 'normal shield vitality')
        sh_delay_raw = vt.f(vp + 'shield recharge delay time')
        body_delay = vt.f(vp + 'body recharge delay time')
        body_frac = vt.f(vp + 'body recharge fraction')
        unit = ch.s('unit')
        bipd = Tag(unit + '.biped', clog)
        model_path = bipd.s('model') + '.model'
        em = model_damage_info(model_path, clog, body_mat_name)
        e_body = leg_body * dial['enemy vitality']
        e_sh = leg_sh * dial['enemy shield']
        sh_delay = sh_delay_raw * dial['enemy recharge']
        target_in = {
            'character': ch.path, 'vitality from': vt.path,
            'legendary body vitality': leg_body, 'legendary shield vitality': leg_sh,
            'model new damage info (overridden by the character)': {
                k: em[k] for k in ('maximum vitality', 'maximum shield vitality')},
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
        for label, _wp in PLAYER_WEAPONS:
            w, wl = weapons[label]
            groups = (w['general_damage'], w['specific_damage'])
            m_sh, d_sh = g.multiplier(groups, em['global shield material name']) \
                if e_sh > 0 else (0.0, {})
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
            if e_sh > 0 and t is not None and sh_delay < t <= sh_delay_raw:
                flags.append('(inside the raw %.0f s delay if the dial does not scale it)'
                             % sh_delay_raw)
            if body_frac and t is not None and t > body_delay:
                flags.append('fight (%.2f s) outlasts the body recharge delay %.1f s '
                             '(recharges %.0f%% of body) -- not modelled'
                             % (t, body_delay, body_frac * 100))
            if w['rps'][0] != w['rps'][1]:
                flags.append('rate ramps %.0f -> %.0f rounds/s over %.2f s held (re-ramps after '
                             'each overheat)' % (w['rps'][0], w['rps'][1], w['accel']))
            if ev.get('overheats'):
                cool = dict(w, **{'heat per round': 0.0})
                k = next(k for k in range(2, n + 1) if sim_player(k, w)[1]['overheats'])
                flags.append('%d overheat(s) during the kill: the %d-th bolt overheats the gun '
                             '(heat loss assumed to run while firing), the cool-down to the '
                             'recovery threshold costs %.2f s; without overheat pauses: %.2f s'
                             % (ev['overheats'], k - 1,
                                (w['overheated threshold'] - w['heat recovery threshold'])
                                / w['overheated heat loss'], sim_player(n, cool)[0]))
            if ev.get('reloads'):
                flags.append('%d reload(s) during the kill (%.2f s each, %s)'
                             % (ev['reloads'], w['reload'], w['reload source']))
            if int(w['shots per fire'][1]) > 1:
                flags.append('%d-round bursts at %.0f/s, %.2f s fire recovery from a burst\'s '
                             'last round to the next burst (assumed timing)'
                             % (int(w['shots per fire'][1]), w['rps'][1], w['fire recovery']))
            lo_d = w['damage lower bound']
            rng = w['air damage range']
            flags.append('point-blank damage: the jpt upper bound falls toward the lower bound '
                         '(%.2f) across the projectile air damage range %.0f-%.0f wu (at 5 wu: '
                         'x%.3f, ASSUMED linear)' % (lo_d, rng[0], rng[1],
                                                       (w['upper'] - (w['upper'] - lo_d) *
                                                        (5 - rng[0]) / (rng[1] - rng[0]))
                                                       / w['upper'] if rng[1] > rng[0] else 1))
            cross = None
            if w['rps'][0] == w['rps'][1] and not w['heat per round'] and \
                    int(w['shots per fire'][1]) <= 1:
                cross = tc.player_time(n, 1.0 / w['rps'][1], w['mag'], w['reload'])
                assert abs(cross - t) < 1e-6, (label, cross, t)
            inputs = {
                'weapon': {k: v for k, v in w.items()},
                'damage multipliers': {'shield': d_sh, 'body': d_bo},
                'shield hit': r3(sh), 'body hit': r3(bo),
                'target': target_in,
                'events in the kill': ev,
                'ttk_common.player_time cross-check (constant-rate weapons)': r3(cross),
                '30 Hz quantised rate (H1 trigger model, cross-check only)':
                    [r3(tick_rate(x)) for x in w['rps']],
                'fields read (weapon)': wl,
                'fields read (matg)': glog}
            rows.append({'direction': 'player->enemy', 'attacker': 'Player (Master Chief)',
                         'target': elabel, 'weapon': label, 'shots': n, 'seconds': r3(t),
                         'inputs': inputs, 'flags': flags})

        # ---------- enemy -> player
        wl = {}
        w = read_weapon(eweap, wl)
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

        def at_acc(a, key, mean=True):
            vals = [(sum(p[key]) / 2.0 if mean else p[key]) if isinstance(p[key], list)
                    else p[key] for p in pats]
            if len(vals) == 1:
                return vals[0]
            return vals[0] + (vals[1] - vals[0]) * a

        def pulls(a):
            # rate 0 = held: the weapon's own (top) rounds per second
            rs = [p['rate of fire'] or w['rps'][1] for p in pats]
            return rs[0] + (rs[-1] - rs[0]) * a

        a = acc_hi                                   # steady state, reached after acc_time
        wdm = at_acc(a, 'weapon damage modifier') or 1.0
        mul = dial['enemy damage'] * wdm * w['projectiles per shot']
        groups = (w['general_damage'], w['specific_damage'])
        m_sh, d_sh = g.multiplier(groups, pm['global shield material name'])
        m_bo, d_bo = g.multiplier(groups, pm['body material'])
        sh = w['upper'] * m_sh * mul
        bo = w['upper'] * m_bo * mul
        n, _ = tc.shots_to_kill(p_sh, p_body, sh, bo)
        ai_pulls = pulls(a) * dial['rate of fire']
        w_max = w['rps'][1]
        rate = min(ai_pulls, w_max)
        bd = at_acc(a, 'burst duration')
        bs_raw = at_acc(a, 'burst separation')
        bs = bs_raw * dial['burst separation']
        held, paced = tc.ai_times(n, rate, bd, bs)
        held_u, paced_u = tc.ai_times(n, ai_pulls, bd, bs)
        # the start of the accuracy ramp (first-pattern end), for reference
        a0 = acc_lo
        r0 = min(pulls(a0) * dial['rate of fire'], w_max)
        held0, paced0 = tc.ai_times(n, r0, at_acc(a0, 'burst duration'),
                                    at_acc(a0, 'burst separation') * dial['burst separation'])
        flags = [
            'AI default weapon %s is an ASSUMPTION: Halo 2 gives AI their weapon from the '
            'scenario squad / starting location, not the character' % eweap.split('\\')[-1],
            'AI rate = firing-pattern rate of fire (0 = held: weapon rounds per second max %.0f) '
            'x matg imposs. rate of fire %.2f = %.2f/s, CAPPED at the weapon\'s %.0f/s (as the '
            'H1 collector; uncapped: held %.2f s, paced %.2f s)'
            % (w_max, dial['rate of fire'], ai_pulls, w_max, held_u or 0, paced_u or 0),
            'firing pattern at legendary accuracy %.2f (end of the %.2f -> %.2f ramp over %.1f s); '
            'at the ramp start (%.2f): held %.2f s, paced %.2f s'
            % (a, acc_lo, acc_hi, acc_time, a0, held0 or 0, paced0 or 0),
            'burst duration / separation are ranges: means used; separation x matg imposs. '
            'burst separation %.2f' % dial['burst separation'],
            'AI weapon heat / overheat not modelled; first burst delay %s s not counted'
            % first_burst]
        if paced is not None and paced > p_delay:
            flags.append('paced time (%.2f s) outlasts the player shield recharge delay %.1f s '
                         '(model shield stun time) -- recharge not modelled' % (paced, p_delay))
        inputs = {
            'attacker character chain': [t.path for t in chain],
            'firing pattern from': '%s :: %s' % (fpt.path, fpp),
            'weapons properties from': '%s :: %s' % (wpt.path, wpp),
            'firing patterns': pats,
            'legendary accuracy bounds / time': [acc_lo, acc_hi, acc_time],
            'weapon': w,
            'damage multipliers': {'shield': d_sh, 'body': d_bo,
                                   'matg imposs. enemy damage': dial['enemy damage'],
                                   'firing pattern weapon damage modifier (0 = none)': wdm},
            'shield hit': r3(sh), 'body hit': r3(bo),
            'target': {'model': pm['tag'], 'shield pool': p_sh, 'body pool': p_body,
                       'shield material': pm['global shield material name'],
                       'body material': '%s -> %s' % (pm.get('body material slot'),
                                                      pm['body material']),
                       'shield recharge delay (model shield stun time)': p_delay,
                       'shield recharge time': pm['shield recharge time'],
                       'fields read': plog},
            'matg imposs. rate of fire': dial['rate of fire'],
            'AI trigger pulls per second (pattern x dial)': r3(ai_pulls),
            'shots per second used (capped)': r3(rate),
            'burst duration used (mean)': r3(bd),
            'burst separation (mean, before dial)': r3(bs_raw),
            'burst separation used': r3(bs),
            '30 Hz quantised rate (H1 trigger model, cross-check only)': r3(tick_rate(rate)),
            'fields read': dict(clog, **wl),
            'fields read (matg)': glog}
        rows.append({'direction': 'enemy->player', 'attacker': elabel,
                     'target': 'Player (Master Chief)', 'weapon': eweap_label,
                     'shots': n, 'seconds': r3(held), 'seconds_paced': r3(paced),
                     'inputs': inputs, 'flags': flags})

    notes += [
        'Source: H2EK tags (%s), read with ttk_common.flatten (private temp export); '
        'nothing in the kit was written.' % os.path.join(tc.STEAM, KIT, 'tags'),
        'Legendary = matg Difficulty "imposs." column: enemy damage %.2f, enemy vitality %.2f, '
        'enemy shield %.2f, enemy recharge %.2f, rate of fire %.2f, burst separation %.2f.'
        % (dial['enemy damage'], dial['enemy vitality'], dial['enemy shield'],
           dial['enemy recharge'], dial['rate of fire'], dial['burst separation']),
        'Enemy pools = character "legendary body / shield vitality" (the kit help: "maximum '
        'body vitality of our unit (on legendary)"), which replace the model maxima (Elite '
        'model 30/70 -> 45/105 on Legendary; Brute model 150 -> 250). The matg vitality/'
        'shield dials (1.0) multiply on top.',
        'Damage per hit = jpt damage upper bound (mean of the pair) x every matg damage-table '
        'row for (jpt general_damage, specific_damage) x (material general armor, specific '
        'armor), materials resolved up the parent chain; missing row = 1. None of these '
        'damage effects has a specific_damage and none of these materials a specific armor, '
        'so each multiplier is a single row. Body shot = Elite "armored_torso" '
        '(hard_metal_thin_cov_elite; the skinned parts resolve to the same hard_metal_thin '
        'armour), Brute "body" (tough_organic_flesh_brute -> tough_organic), Chief "body".',
        'Player times: continuous-time trigger simulation (sim_player): ramp lo->hi over '
        'acceleration time, bursts + fire recovery, heat with continuous heat loss and the '
        'overheated cool-down to the recovery threshold, reloads. Constant-rate weapons are '
        'asserted equal to ttk_common.player_time. Battle Rifle reload = its fp reload_empty '
        'animation (magazine reload time is 0 = animation-driven); SMG uses its tag reload '
        'time 2.0 s (its fp reload animation is 50 frames = 1.67 s).',
        'Enemy shield recharge: the character delay (Elite 15 s) x matg "enemy recharge" (kit '
        'help: "enemy shield recharge scale") 0.3 -- ASSUMED to scale the delay (it falls with '
        'difficulty, so it cannot be a rate). Flags use 4.5 s.',
        'Not modelled: headshots, melee, grenades, misses, AI weapon heat, damage falloff '
        'with range (projectile air damage range 0-40 wu: the jpt lower bound is reached '
        'at 40 wu), the first-burst delay, the AI accuracy ramp (steady state used).',
    ]
    path = tc.write(GAME, rows, notes)
    for row in rows:
        print('%-14s %-34s -> %-22s hits %-4s %7s s%s' % (
            row['direction'], row['attacker'] + ' / ' + row['weapon'], row['target'],
            row['shots'], row['seconds'],
            ('  paced %s s' % row['seconds_paced']) if 'seconds_paced' in row else ''))
        print('    shield hit %s body hit %s | %s' % (
            row['inputs']['shield hit'], row['inputs']['body hit'], ' | '.join(row['flags'])))
    print(path)


if __name__ == '__main__':
    main()

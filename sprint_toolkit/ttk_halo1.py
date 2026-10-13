r"""Time-to-kill on LEGENDARY: the Halo 1 (MCC) collector (ttk_common's method).

READ-ONLY. Halo 1 is read from the patcher's BASELINE map (E:\HaloBaselines\halo1\maps),
never the HCEEK kit (port sessions hold its kit lock), and the Assembly plugins from the
loose E: copy (same files as the kit's, so the kit folder is not touched at all). The map
is opened, read into memory and never saved.

    python ttk_halo1.py [--map a10] [--plugins DIR]

Writes reports/ttk/ttk_halo_1.json via ttk_common.write('Halo 1', rows, notes).

Halo 1 specifics (what the shared method leaves to each game):
  * damage of one hit = jpt! Damage Upper Bound (mean of its min/max pair) x the jpt!'s
    own per-material modifier (shield material from coll Shield Material Type, body
    material from the coll material named 'body') x coll material Shield / Body Damage
    Multiplier of that 'body' material.
  * enemy pool = actv Body / Shield Vitality (the actor variant's override; coll max when
    0) x matg Difficulty Impossible Enemy Vitality / Enemy Shield.
  * AI damage = jpt x matg Impossible Enemy Damage x actv Weapon Damage Modifier.
  * the 30 Hz trigger (measured live for the Plasma Repeater port, h1_weapon_state_probe):
    rate/30 is added each tick, a shot when the sum reaches 1, then the sum resets -> a
    weapon fires every ceil(30/rate) ticks. Plasma heat cools while firing. The player
    times come from a tick simulation of exactly that (ramp, heat, reload); for a weapon
    with a flat rate and no heat it equals ttk_common.player_time at the quantised rate
    (asserted below).
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import ttk_common as tc  # noqa: E402
import halo_map as hm  # noqa: E402

BASELINE = r'E:\HaloBaselines\halo1\maps'
PLUGINS = r'E:\Assembly-1-2023-11-29-1702446457\Plugins'   # loose copy, NOT the HCEEK one
TICK = 30.0
TIER = 'Impossible'   # Halo 1's name for Legendary in matg Difficulty

PLAYER_WEAPONS = [('Assault Rifle', 'weapons\\assault rifle\\assault rifle'),
                  ('Plasma Rifle', 'weapons\\plasma rifle\\plasma rifle'),
                  ('Pistol', 'weapons\\pistol\\pistol')]
ELITE_ACTV = 'characters\\elite\\elite minor\\elite minor plasma rifle'
PLAYER_BIPD = 'characters\\cyborg\\cyborg'

# jpt! Damage Modifiers (+0x200, one float per H1 material type, coll enum order)
MATERIALS = ['Dirt', 'Sand', 'Stone', 'Snow', 'Wood', 'Metal (Hollow)', 'Metal (Thin)',
             'Metal (Thick)', 'Rubber', 'Glass', 'Force Field', 'Grunt', 'Hunter Armor',
             'Hunter Skin', 'Elite', 'Jackal', 'Jackal Energy Shield', 'Engineer Skin',
             'Engineer Force Field', 'Flood Combat Form', 'Flood Carrier Form', 'Cyborg Armor',
             'Cyborg Energy Shield', 'Human Armor', 'Human Skin', 'Sentinel', 'Monitor',
             'Plastic', 'Water', 'Leaves', 'Elite Energy Shield', 'Ice', 'Hunter Shield']


class Reader:
    def __init__(self, path):
        self.path = path
        self.m = hm.HaloMap(path)          # reads the file into memory; never saved
        self.plugin = {}

    def f(self, o):
        return struct.unpack_from('<f', self.m.data, o)[0]

    def h(self, o):
        return struct.unpack_from('<h', self.m.data, o)[0]

    def H(self, o):
        return struct.unpack_from('<H', self.m.data, o)[0]

    def meta(self, cls, path):
        off = self.m.tags.get((cls, path))
        if off is None:
            raise SystemExit('%s %s not in %s' % (cls, path, self.path))
        return off

    def ref(self, o):
        """H1 tagref at o: group fourcc, name ptr, 0, datum id -> (group, path) or None."""
        tid = self.m.u32(o + 0xC)
        if tid == 0xFFFFFFFF:
            return None
        return bytes(self.m.data[o:o + 4][::-1]).decode('latin1'), self.m.tag_name_by_id(tid)

    def block(self, meta, off, size):
        """[element offsets] of the reflexive at meta+off."""
        n = self.m.i32(meta + off)
        if n <= 0:
            return []
        base = (self.m.u32(meta + off + 4) - self.m.magic) & 0xFFFFFFFF
        return [base + i * size for i in range(n)]

    def cstr(self, o, n=32):
        return bytes(self.m.data[o:o + n]).split(b'\0')[0].decode('latin1')

    def fields(self, cls, path, names, sub='Halo1MCC'):
        """{name: value} of root-level plugin fields (checks the plugin's offsets)."""
        key = cls
        if key not in self.plugin:
            p = os.path.join(PLUGINS, sub, cls + '.xml')
            if not os.path.isfile(p):
                p = os.path.join(PLUGINS, 'Halo1', cls + '.xml')
            self.plugin[key] = hm.Plugin(p)
        pl = self.plugin[key]
        out = {}
        for nm in names:
            v = self.m.read(cls, path, nm, pl)
            if v is None:
                raise SystemExit('field %s not found in %s plugin' % (nm, cls))
            out[nm] = v
        return out


# ----------------------------------------------------------------------------- reading
def read_matg(r):
    meta = r.meta('matg', 'globals\\globals')
    names = ['%s %s' % (TIER, k) for k in ('Enemy Damage', 'Enemy Vitality', 'Enemy Shield',
                                            'Enemy Recharge', 'Rate Of Fire', 'Burst Separation',
                                            'Projectile Error', 'Burst Error')]
    v = r.fields('matg', 'globals\\globals', names, sub='Halo1')
    del meta
    return {k.replace(TIER + ' ', ''): float(x) for k, x in v.items()}


def read_coll(r, path):
    meta = r.meta('coll', path)
    d = {'tag': 'coll ' + path,
         'Maximum Body Vitality (+0x8)': r.f(meta + 0x8),
         'Maximum Shield Vitality (+0xCC)': r.f(meta + 0xCC),
         'Shield Material Type (+0xD2)': MATERIALS[r.H(meta + 0xD2)],
         'Stun Time (+0x10C)': r.f(meta + 0x10C),
         'Recharge Time (+0x110)': r.f(meta + 0x110),
         'Shield Recharge Rate (+0x1C0, runtime per tick)': r.f(meta + 0x1C0)}
    mats = []
    for b in r.block(meta, 0x234, 0x48):
        mats.append({'name': r.cstr(b), 'head flag': bool(r.m.u32(b + 0x20) & 1),
                     'type': MATERIALS[r.H(b + 0x24)],
                     'shield_mul': r.f(b + 0x2C), 'body_mul': r.f(b + 0x3C)})
    d['materials'] = mats
    body = [x for x in mats if x['name'] == 'body']
    if not body:
        raise SystemExit('no "body" material in coll ' + path)
    d['body material'] = body[0]
    return d


def read_jpt(r, path):
    meta = r.meta('jpt!', path)
    lo, up0, up1 = r.f(meta + 0x1D0), r.f(meta + 0x1D4), r.f(meta + 0x1D8)
    return {'tag': 'jpt! ' + path,
            'Damage Lower Bound (+0x1D0)': lo,
            'Damage Upper Bound (+0x1D4 / +0x1D8)': [up0, up1],
            'upper': (up0 + up1) / 2.0,
            'Stun Time (+0x1EC)': r.f(meta + 0x1EC),
            'modifiers': {n: r.f(meta + 0x200 + 4 * i) for i, n in enumerate(MATERIALS)}}


def read_weapon(r, path):
    meta = r.meta('weap', path)
    trig = r.block(meta, 0x4FC, 0x114)[0]
    mags = r.block(meta, 0x4F0, 0x70)
    proj = r.ref(trig + 0x94)
    pmeta = r.meta('proj', proj[1])
    dmg = r.ref(pmeta + 0x224)              # proj Impact Damage
    if dmg is None:
        raise SystemExit('projectile %s has no Impact Damage' % proj[1])
    w = {'tag': 'weap ' + path,
         'Triggers[0] Rounds Per Second (+0x4)': r.f(trig + 0x4),
         'Triggers[0] Rounds Per Second Max (+0x8)': r.f(trig + 0x8),
         'Triggers[0] Acceleration Time (+0xC)': r.f(trig + 0xC),
         'Triggers[0] Rate Of Fire Acceleration Rate (+0xF8, runtime per tick)': r.f(trig + 0xF8),
         'Triggers[0] Projectiles Per Shot (+0x6E)': r.h(trig + 0x6E),
         'Triggers[0] Rounds Per Shot (+0x22)': r.h(trig + 0x22),
         'Triggers[0] Heat Generated Per Round (+0xB8)': r.f(trig + 0xB8),
         'Triggers[0] Projectile (+0x94)': 'proj ' + proj[1],
         'proj Impact Damage (+0x224)': 'jpt! ' + dmg[1],
         'Overheated Threshold (+0x350)': r.f(meta + 0x350),
         'Heat Recovery Threshold (+0x34C)': r.f(meta + 0x34C),
         'Heat Loss Per Second (+0x35C)': r.f(meta + 0x35C)}
    if mags:
        w['Magazines[0] Rounds Loaded Maximum (+0xA)'] = r.h(mags[0] + 0xA)
        w['Magazines[0] Reload Time (+0x14)'] = r.f(mags[0] + 0x14)
    return w, read_jpt(r, dmg[1])


def read_actv(r, path):
    meta = r.meta('actv', path)
    unit = r.ref(meta + 0x14)
    weap = r.ref(meta + 0x64)
    a = {'tag': 'actv ' + path,
         'Unit (+0x14)': '%s %s' % unit,
         'Weapon (+0x64)': '%s %s' % weap,
         'Rate Of Fire (+0x78)': r.f(meta + 0x78),
         'Weapon Damage Modifier (+0xC4)': r.f(meta + 0xC4),
         'Damage Per Second (+0xC8)': r.f(meta + 0xC8),
         'Burst Duration (+0xE0 / +0xE4)': [r.f(meta + 0xE0), r.f(meta + 0xE4)],
         'Burst Separation (+0xE8 / +0xEC)': [r.f(meta + 0xE8), r.f(meta + 0xEC)],
         'First Burst Delay Time (+0x80 / +0x84)': [r.f(meta + 0x80), r.f(meta + 0x84)],
         'Body Vitality (+0x200)': r.f(meta + 0x200),
         'Shield Vitality (+0x204)': r.f(meta + 0x204)}
    bmeta = r.meta(unit[0], unit[1])
    coll = r.ref(bmeta + 0x70)
    a['%s Collision Model (+0x70)' % unit[0]] = 'coll ' + coll[1]
    return a, unit, weap, coll


# ----------------------------------------------------------------------------- simulation
def tick_rate(rate):
    """Shots per second the 30 Hz accumulator gives for a constant rate (float32 as the
    engine adds it)."""
    if rate <= 0:
        return 0.0
    step = struct.unpack('<f', struct.pack('<f', rate / TICK))[0]
    s, n = 0.0, 0
    while s < 1.0:
        s = struct.unpack('<f', struct.pack('<f', s + step))[0]
        n += 1
    return TICK / n


def player_ticks(n, w):
    """Seconds until the n-th shot (first at t=0) with the H1 trigger held: rate ramps
    from Rounds Per Second to Max by the runtime acceleration rate each tick, the
    accumulator fires at 1, heat +per round and -loss/30 per tick, overheat pauses until
    heat < recovery threshold, magazine reloads take Reload Time."""
    if n is None:
        return None, {}
    r0 = w['Triggers[0] Rounds Per Second (+0x4)']
    r1 = w['Triggers[0] Rounds Per Second Max (+0x8)']
    acc = w['Triggers[0] Rate Of Fire Acceleration Rate (+0xF8, runtime per tick)']
    heat_pr = w['Triggers[0] Heat Generated Per Round (+0xB8)']
    over = w['Overheated Threshold (+0x350)']
    recov = w['Heat Recovery Threshold (+0x34C)']
    loss = w['Heat Loss Per Second (+0x35C)'] / TICK
    mag = w.get('Magazines[0] Rounds Loaded Maximum (+0xA)', 0)
    reload_t = w.get('Magazines[0] Reload Time (+0x14)', 0.0)
    frac, s, heat, inmag = 0.0, 1.0, 0.0, mag   # s starts at 1: the first shot leaves at t=0
    overheated, busy_until = False, 0
    shots, tick, events = 0, 0, {'overheats': 0, 'reloads': 0}
    while True:
        # trigger held: the rate ramps every tick it is held and allowed to fire
        rate = r0 + (r1 - r0) * frac
        if not overheated and tick >= busy_until:
            if s >= 1.0 - 1e-6:
                shots += 1
                s = 0.0
                if shots == n:
                    return tick / TICK, events
                if heat_pr:
                    heat += heat_pr
                    if heat >= over - 1e-9:
                        overheated = True
                        events['overheats'] += 1
                        frac = 0.0
                if mag:
                    inmag -= 1
                    if inmag <= 0:
                        busy_until = tick + int(math.ceil(reload_t * TICK - 1e-9))
                        inmag = mag
                        events['reloads'] += 1
                        frac = 0.0
                        s = 1.0          # as ttk_common: the next shot leaves when the reload ends
            s += rate / TICK
            frac = min(1.0, frac + acc) if acc else 1.0
        heat = max(0.0, heat - loss)
        if overheated and heat < recov:
            overheated = False
            s = 1.0                      # trigger still held: fires on the next allowed tick
        tick += 1
        if tick > 600 * TICK:
            return None, events


def damage(jpt, coll, mul=1.0):
    """(shield hit, body hit) of one projectile on a target."""
    sh_mat = coll['Shield Material Type (+0xD2)']
    bm = coll['body material']
    sh = jpt['upper'] * jpt['modifiers'][sh_mat] * bm['shield_mul'] * mul
    bo = jpt['upper'] * jpt['modifiers'][bm['type']] * bm['body_mul'] * mul
    return sh, bo, {'jpt shield modifier [%s]' % sh_mat: jpt['modifiers'][sh_mat],
                    'jpt body modifier [%s]' % bm['type']: jpt['modifiers'][bm['type']],
                    'coll material "body" Shield Damage Multiplier (+0x2C)': bm['shield_mul'],
                    'coll material "body" Body Damage Multiplier (+0x3C)': bm['body_mul']}


def r3(x):
    return None if x is None else round(x, 3)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--map', default='a10', help='baseline level (default a10, the first '
                    'level holding all three player weapons and the Elite minor)')
    args = ap.parse_args()
    path = os.path.join(BASELINE, args.map + '.map')
    r = Reader(path)
    g = read_matg(r)
    rows, notes = [], []

    actv, unit, eweap, ecoll_ref = read_actv(r, ELITE_ACTV)
    ecoll = read_coll(r, ecoll_ref[1])
    pb = r.meta('bipd', PLAYER_BIPD)
    pcoll_ref = r.ref(pb + 0x70)
    pcoll = read_coll(r, pcoll_ref[1])

    dial_src = 'matg globals\\globals Difficulty %s' % TIER
    # ---------------- player -> Elite minor
    e_body0 = actv['Body Vitality (+0x200)'] or ecoll['Maximum Body Vitality (+0x8)']
    e_sh0 = actv['Shield Vitality (+0x204)'] or ecoll['Maximum Shield Vitality (+0xCC)']
    e_body = e_body0 * g['Enemy Vitality']
    e_sh = e_sh0 * g['Enemy Shield']
    stun = ecoll['Stun Time (+0x10C)']
    for label, wpath in PLAYER_WEAPONS:
        w, jpt = read_weapon(r, wpath)
        pps = w['Triggers[0] Projectiles Per Shot (+0x6E)'] or 1
        sh, bo, dmods = damage(jpt, ecoll, pps)
        n, _ = tc.shots_to_kill(e_sh, e_body, sh, bo)
        t, ev = player_ticks(n, w)
        r0 = w['Triggers[0] Rounds Per Second (+0x4)']
        r1 = w['Triggers[0] Rounds Per Second Max (+0x8)']
        q0, q1 = tick_rate(r0), tick_rate(r1)
        heat_pr = w['Triggers[0] Heat Generated Per Round (+0xB8)']
        loss = w['Heat Loss Per Second (+0x35C)']
        pause = ((w['Overheated Threshold (+0x350)'] - w['Heat Recovery Threshold (+0x34C)'])
                 / loss) if heat_pr and loss else 0.0
        common = {}
        for q in (q0, q1):
            common['ttk_common.player_time at %.3f/s' % q] = r3(tc.player_time(
                n, 1.0 / q, w.get('Magazines[0] Rounds Loaded Maximum (+0xA)', 0),
                w.get('Magazines[0] Reload Time (+0x14)', 0.0), heat_pr,
                w['Overheated Threshold (+0x350)'] or 1.0, pause))
        if r0 == r1 and not heat_pr:
            pt = tc.player_time(n, 1.0 / q0, w.get('Magazines[0] Rounds Loaded Maximum (+0xA)', 0),
                                w.get('Magazines[0] Reload Time (+0x14)', 0.0))
            assert abs(pt - t) < 1.5 / TICK, (label, pt, t)
        flags = []
        if t is not None and t > stun:
            flags.append('fight (%.2f s) outlasts the Elite shield Stun Time %.2f s (coll +0x10C)'
                         % (t, stun))
        if r0 != r1:
            flags.append('rate ramps %.1f -> %.1f rounds/s (quantised %.2f -> %.2f/s at 30 Hz) '
                         'over %.2f s held; time from the tick simulation of the ramp'
                         % (r0, r1, q0, q1, w['Triggers[0] Acceleration Time (+0xC)']))
        if ev.get('overheats'):
            flags.append('%d overheat(s) during the kill' % ev['overheats'])
        if ev.get('reloads'):
            flags.append('%d reload(s) during the kill' % ev['reloads'])
        inputs = {'weapon': w, 'damage effect': {k: v for k, v in jpt.items() if k != 'modifiers'},
                  'damage multipliers': dmods,
                  'shield hit': r3(sh), 'body hit': r3(bo),
                  'target': {'actv': actv['tag'], 'coll': ecoll['tag'],
                             'actv Body Vitality (+0x200)': actv['Body Vitality (+0x200)'],
                             'actv Shield Vitality (+0x204)': actv['Shield Vitality (+0x204)'],
                             'coll Maximum Body Vitality (+0x8)': ecoll['Maximum Body Vitality (+0x8)'],
                             'coll Maximum Shield Vitality (+0xCC)': ecoll['Maximum Shield Vitality (+0xCC)'],
                             'coll Shield Material Type (+0xD2)': ecoll['Shield Material Type (+0xD2)'],
                             'coll body material': ecoll['body material'],
                             'coll Stun Time (+0x10C)': stun,
                             'coll Recharge Time (+0x110)': ecoll['Recharge Time (+0x110)'],
                             '%s Enemy Vitality' % dial_src: g['Enemy Vitality'],
                             '%s Enemy Shield' % dial_src: g['Enemy Shield'],
                             '%s Enemy Recharge' % dial_src: g['Enemy Recharge'],
                             'shield pool': r3(e_sh), 'body pool': r3(e_body)},
                  'rate used (30 Hz quantised)': [r3(q0), r3(q1)],
                  'overheat pause (s) = (Overheated - Recovery threshold) / Heat Loss': r3(pause),
                  'events in the kill': ev,
                  'cross-check (fixed-rate shared helper)': common}
        rows.append({'direction': 'player->enemy', 'attacker': 'Player (Master Chief)',
                     'target': 'Elite minor', 'weapon': label, 'shots': n, 'seconds': r3(t),
                     'inputs': inputs, 'flags': flags})

    # ---------------- Elite minor -> player
    w, jpt = read_weapon(r, eweap[1])
    pps = w['Triggers[0] Projectiles Per Shot (+0x6E)'] or 1
    wdm = actv['Weapon Damage Modifier (+0xC4)'] or 1.0
    mul = g['Enemy Damage'] * wdm * pps
    sh, bo, dmods = damage(jpt, pcoll, mul)
    p_sh = pcoll['Maximum Shield Vitality (+0xCC)']
    p_body = pcoll['Maximum Body Vitality (+0x8)']
    n, _ = tc.shots_to_kill(p_sh, p_body, sh, bo)
    ai_rate = actv['Rate Of Fire (+0x78)'] * g['Rate Of Fire']
    w_max = w['Triggers[0] Rounds Per Second Max (+0x8)']
    rate = min(ai_rate, w_max) if ai_rate > 0 else w_max
    q = tick_rate(rate)
    bd = sum(actv['Burst Duration (+0xE0 / +0xE4)']) / 2.0
    bs_raw = sum(actv['Burst Separation (+0xE8 / +0xEC)']) / 2.0
    bs = bs_raw * g['Burst Separation']
    held, paced = tc.ai_times(n, q, bd, bs)
    held_unq, paced_unq = tc.ai_times(n, ai_rate, bd, bs)
    flags = ['AI rate = actv Rate Of Fire x matg %s Rate Of Fire (ASSUMED multiplicative; '
             'not measured in game), capped at the weapon Rounds Per Second Max, quantised '
             'to the 30 Hz trigger' % TIER,
             'actv Burst Duration and Burst Separation are RANGES: the means are used; '
             'separation also x matg %s Burst Separation %.2f (assumed to scale it)'
             % (TIER, g['Burst Separation'])]
    if actv['Damage Per Second (+0xC8)']:
        flags.append('actv Damage Per Second is non-zero (%.2f): a damage-rate cap may apply'
                     % actv['Damage Per Second (+0xC8)'])
    if held is not None and held > pcoll['Stun Time (+0x10C)']:
        flags.append('held time outlasts the player shield Stun Time %.2f s'
                     % pcoll['Stun Time (+0x10C)'])
    if paced is not None and paced > pcoll['Stun Time (+0x10C)']:
        flags.append('paced time (%.2f s) outlasts the player shield Stun Time %.2f s (coll '
                     '+0x10C) -- recharge not modelled' % (paced, pcoll['Stun Time (+0x10C)']))
    inputs = {'attacker': actv, 'weapon': w,
              'damage effect': {k: v for k, v in jpt.items() if k != 'modifiers'},
              'damage multipliers': dict(dmods, **{
                  '%s Enemy Damage' % dial_src: g['Enemy Damage'],
                  'actv Weapon Damage Modifier (+0xC4)': actv['Weapon Damage Modifier (+0xC4)']}),
              'shield hit': r3(sh), 'body hit': r3(bo),
              'target': {'bipd': 'bipd ' + PLAYER_BIPD, 'coll': pcoll['tag'],
                         'coll Maximum Body Vitality (+0x8)': p_body,
                         'coll Maximum Shield Vitality (+0xCC)': p_sh,
                         'coll Shield Material Type (+0xD2)': pcoll['Shield Material Type (+0xD2)'],
                         'coll body material': pcoll['body material'],
                         'coll Stun Time (+0x10C)': pcoll['Stun Time (+0x10C)'],
                         'coll Recharge Time (+0x110)': pcoll['Recharge Time (+0x110)']},
              '%s Rate Of Fire' % dial_src: g['Rate Of Fire'],
              'AI trigger pulls per second (actv RoF x dial)': r3(ai_rate),
              'shots per second used (capped, 30 Hz quantised)': r3(q),
              'burst duration used (mean)': r3(bd),
              'burst separation (actv mean, before dial)': r3(bs_raw),
              'burst separation used (x %s Burst Separation)' % TIER: r3(bs),
              'unquantised (held, paced)': [r3(held_unq), r3(paced_unq)]}
    rows.append({'direction': 'enemy->player', 'attacker': 'Elite minor',
                 'target': 'Player (Master Chief)', 'weapon': 'Plasma Rifle (AI)',
                 'shots': n, 'seconds': r3(held), 'seconds_paced': r3(paced),
                 'inputs': inputs, 'flags': flags})

    notes += [
        'Source: %s (patcher baseline, read-only); plugins %s (loose copy of the Assembly '
        'Halo1MCC/Halo1 set; the HCEEK kit was not touched).' % (path, PLUGINS),
        'Legendary = matg Difficulty "%s" column throughout.' % TIER,
        'Damage per hit = jpt! Damage Upper Bound mean x jpt! per-material modifier (shield '
        'material = coll Shield Material Type; body = the coll material named "body") x that '
        'coll material\'s Shield/Body Damage Multiplier. No headshots, no melee, no AOE.',
        'Elite pool = actv Body/Shield Vitality (+0x200/+0x204, the actor-variant override; '
        'equal to the coll maxima for the minor) x matg Enemy Vitality / Enemy Shield.',
        'Player times: 30 Hz tick simulation of the measured H1 trigger (rate/30 per tick, '
        'shot at sum >= 1, sum resets; rate ramp by the runtime Rate Of Fire Acceleration '
        'Rate per tick; plasma heat cools while firing). Halo 1 has no fire-recovery-time '
        'field: the rate is the only limit. Flat-rate weapons match ttk_common.player_time '
        '(asserted).',
        'Shield recharge: coll Stun Time (+0x10C) is reported as the recharge delay. Its '
        'unit is NOT verified in game for H1 (the Elite\'s 12 vs the cyborg\'s 6; matg %s '
        'Enemy Recharge %.1f is assumed to scale the recharge RATE, not the delay).'
        % (TIER, g['Enemy Recharge']),
        'AI damage = jpt x matg Enemy Damage x actv Weapon Damage Modifier (+0xC4). The '
        'player is NOT scaled by any vitality dial (matg Friend dials apply to allies).',
        'AI "held" = the AI firing continuously at its trigger-pull rate; "paced" = in its '
        'own bursts. Both count every shot as a hit; first-burst delay, aim error and '
        'leading are ignored.',
        'Halo 1 has no Brutes.',
    ]
    out = tc.write('Halo 1', rows, notes)
    for row in rows:
        print('%-14s %-22s -> %-22s shots %-4s %8s s%s  %s' % (
            row['direction'], row['attacker'] + ' / ' + row['weapon'], row['target'],
            row['shots'], row['seconds'],
            ('  paced %s s' % row['seconds_paced']) if 'seconds_paced' in row else '',
            ' | '.join(row['flags'])))
        print('    hits: shield %s body %s' % (row['inputs']['shield hit'], row['inputs']['body hit']))
    print('wrote', out)


if __name__ == '__main__':
    main()

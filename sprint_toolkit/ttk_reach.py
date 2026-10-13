r"""Time-to-kill on LEGENDARY: HALO REACH collector (ttk_common's method, user 2026-10-13).

READ-ONLY. Every tag is read from HREK through ttk_common.flatten (a private export file);
nothing is written but reports/ttk/ttk_halo_reach.json.

WHERE REACH KEEPS THE NUMBERS (found 2026-10-13, see 'inputs' of every row):
  * enemy pool -- the CHARACTER's 'vitality properties' (legendary body / shield vitality,
    shield recharge delay); they replace the model's own numbers (elite_ai.model 50 / 79). The
    matg 'difficulty' enemy vitality / shield dials are all 1.
  * materials -- unit (biped) -> model: 'model materials' (the one named 'body') and the shield
    material ('new damage info' shield, or, for the old-style Brute model, the 'damage info'
    section named 'shield'). Armour names come up the globals material PARENT chain (the first
    non-empty general armor / specific armor) -- the leaf usually leaves them empty.
  * multiplier -- globals 'damage table' [0]: EVERY row found multiplies (jpt general and
    specific damage group, each vs the material's general and specific armor; missing = 1).
    Reach has no '_player' armour rows, so the Spartan / Elite specific armours count 1.
  * difficulty -- globals 'difficulty' imposs.(= Legendary) enemy damage 1.6, rate of fire 1,
    burst separation 0.5 (everything the AI deals to the player is x1.6).
  * AI fire -- the firing pattern of the AI's weapon: the character's 'firing pattern
    properties', else its parent's (ai\generic carries the plasma rifle and the spiker).
    Four patterns per weapon: inaccurate / really accurate / marksman / trigger happy; the
    character's 'legendary accuracy bounds' 0.3 -> 1 over 'legendary accuracy time' 3 s move
    the AI from the first to the second, so the REALLY ACCURATE pattern is used (rate of fire,
    burst duration and separation as the mean of their bounds).
  * default AI weapon -- not on the character in Reach: the campaign squad templates
    (ai\squad_templates\sq_camp_elite_minor_1 / sq_camp_brute_1 'initial weapon').
  * reload -- animation-driven in Reach (the magazine has no time): the first-person
    'reload_empty' animation's 'allow interruption' frame / 30.
  * Plasma Repeater heat -- in its weapon FUNCTIONS, whose curves the XML export does not
    carry; the evaluated values come from the B3 port research (ports_h1/plasma_repeater.py):
    0.03 heat a tick firing, rate 15 + (3 - 15) x heat^1.5, never overheats.

    python ttk_reach.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc                                             # noqa: E402

KIT = 'HREK'
GAME = 'Halo Reach'
GLOBALS = r'globals\globals.globals'
TICK = 1.0 / 30.0
W = r'objects\weapons\rifle'
FP = r'objects\characters\spartans\fp\weapons\rifle'

PLAYER = {'name': 'Spartan (player)', 'biped': r'objects\characters\spartans\spartans.biped',
          'model': r'objects\characters\spartans\spartans.model'}
ENEMIES = [
    {'name': 'Elite minor', 'char': r'objects\characters\elite\ai\elite.character',
     'biped': r'objects\characters\elite_ai\elite_ai.biped',
     'model': r'objects\characters\elite_ai\elite_ai.model',
     'squad': r'ai\squad_templates\sq_camp_elite_minor_1.squad_template'},
    {'name': 'Brute minor', 'char': r'objects\characters\brute\ai\brute.character',
     'biped': r'objects\characters\brute\brute.biped',
     'model': r'objects\characters\brute\brute.model',
     'squad': r'ai\squad_templates\sq_camp_brute_1.squad_template'},
]
PLAYER_WEAPONS = [
    {'name': 'Assault Rifle', 'weapon': W + r'\assault_rifle\assault_rifle.weapon',
     'projectile': W + r'\assault_rifle\projectiles\assault_rifle_bullet.projectile',
     'jpt': W + r'\assault_rifle\projectiles\assault_rifle_bullet.damage_effect',
     'fp': FP + r'\fp_assault_rifle\fp_assault_rifle.model_animation_graph'},
    {'name': 'Plasma Repeater', 'weapon': W + r'\plasma_repeater\plasma_repeater.weapon',
     'projectile': W + r'\plasma_repeater\projectiles\plasma_repeater_bolt.projectile',
     'jpt': W + r'\plasma_repeater\projectiles\plasma_repeater_bolt.damage_effect', 'fp': None},
    {'name': 'DMR', 'weapon': W + r'\dmr\dmr.weapon',
     'projectile': W + r'\dmr\projectiles\dmr_bullet.projectile',
     'jpt': W + r'\dmr\projectiles\dmr_bullet.damage_effect',
     'fp': FP + r'\fp_dmr\fp_dmr.model_animation_graph'},
]
AI_WEAPONS = {
    'plasma_rifle': {'name': 'Plasma Rifle', 'weapon': W + r'\plasma_rifle\plasma_rifle.weapon',
                     'projectile': W + r'\plasma_rifle\projectiles\plasma_rifle_bolt.projectile',
                     'jpt': W + r'\plasma_rifle\projectiles\plasma_rifle_bolt.damage_effect'},
    'spike_rifle': {'name': 'Spike Rifle', 'weapon': W + r'\spike_rifle\spike_rifle.weapon',
                    'projectile': W + r'\spike_rifle\projectiles\spike_rifle_shard.projectile',
                    'jpt': W + r'\spike_rifle\projectiles\spike_rifle_shard.damage_effect'},
}
#: Plasma Repeater heat functions, evaluated in the B3 port research (not in the XML export)
REPEATER = {'heat_per_tick': 0.03, 'rate_exponent': 1.5,
            'src': 'plasma_repeater.weapon item/object/functions heat->heat_generated_per_round / '
                   'heat->heat_driven_rate_of_fire (curves not exported; values from '
                   'ports_h1/plasma_repeater.py, ManagedBlam Evaluate 2026-10-11)'}


# ----------------------------------------------------------------------------- reading
class Inputs(dict):
    def put(self, key, value, src):
        self[key] = {'value': value, 'src': src}
        return value


def read(tag):
    return tc.flatten(KIT, tag)


def val(tag, field, default=None):
    v = read(tag).get(field)
    return default if v is None else v[1]


def number(tag, field, inp, key, mean=False):
    """A real from a tag (mean of a bounds pair when asked), recorded in inp."""
    raw = val(tag, field)
    if raw is None:
        raise SystemExit('%s: no field %r' % (tag, field))
    parts = [float(x) for x in str(raw).split(',')]
    v = sum(parts) / len(parts) if mean else parts[0]
    return inp.put(key, v, '%s : %s = %s' % (tag, field, raw))


def check_ref(tag, field, expect):
    """Reach exports a tag reference as its NAME only: confirm it names the file used."""
    got = (val(tag, field) or '').split(',')[0]
    want = os.path.splitext(os.path.basename(expect))[0]
    if got != want:
        raise SystemExit('%s : %s = %r, expected %r (%s)' % (tag, field, got, want, expect))


def globals_tables():
    g = read(GLOBALS)
    table, mats = {}, {}
    for k, (_t, v) in g.items():
        p = k.split('/')
        if (len(p) == 7 and p[:3] == ['damage table', '[0]', 'damage groups']
                and p[4] == 'armor modifiers' and p[6] == 'damage multiplier'):
            grp = g['/'.join(p[:4]) + '/name'][1]
            arm = g['/'.join(p[:6]) + '/name'][1]
            table.setdefault(grp, {})[arm] = float(v)
        if len(p) == 3 and p[0] == 'materials' and p[2] == 'name':
            base = '/'.join(p[:2])
            mats.setdefault(v, {'index': p[1], 'parent': g.get(base + '/parent name', ('', ''))[1],
                                'general': g.get(base + '/general armor', ('', ''))[1],
                                'specific': g.get(base + '/specific armor', ('', ''))[1]})
    return table, mats


def armor_of(material, mats):
    """(general armor, specific armor, chain): the first non-empty of each up the parents."""
    gen = spec = ''
    chain, m = [], material
    while m and m in mats and m not in chain:
        chain.append(m)
        gen = gen or mats[m]['general']
        spec = spec or mats[m]['specific']
        m = mats[m]['parent']
    return gen, spec, chain


def multiplier(groups, material, table, mats):
    """Product of every damage-table row found (group x armour); missing rows = 1."""
    gen, spec, chain = armor_of(material, mats)
    m, rows = 1.0, []
    for grp in [x for i, x in enumerate(groups) if x and x not in groups[:i]]:
        for arm in [x for i, x in enumerate((gen, spec)) if x and x not in (gen, spec)[:i]]:
            if arm in table.get(grp, {}):
                m *= table[grp][arm]
                rows.append('%s x %s = %g' % (grp, arm, table[grp][arm]))
            else:
                rows.append('%s x %s: no row (1)' % (grp, arm))
    return m, '%s [%s] -> %s' % (material, ' > '.join(chain), '; '.join(rows) or 'no rows')


def difficulty(inp):
    t = GLOBALS
    d = {}
    for key, field in (('enemy_damage', 'imposs. enemy damage'),
                       ('enemy_vitality', 'imposs. enemy vitality'),
                       ('enemy_shield', 'imposs. enemy shield'),
                       ('rate_of_fire', 'imposs. rate of fire'),
                       ('burst_separation', 'imposs. burst separation')):
        d[key] = number(t, 'difficulty/[0]/' + field, inp, 'legendary ' + key.replace('_', ' '))
    return d


def damage_effect(wdef, inp, prefix):
    """(hit, [general, specific]) of a weapon's projectile impact damage effect."""
    w, p, j = wdef['weapon'], wdef['projectile'], wdef['jpt']
    check_ref(w, 'barrels/[0]/projectile', p)
    check_ref(p, 'impact damage', j)
    hit = number(j, 'damage upper bound', inp, prefix + 'damage per hit (upper bound, mean)', mean=True)
    pps = number(w, 'barrels/[0]/projectiles per shot', inp, prefix + 'projectiles per shot') or 1.0
    groups = [inp.put(prefix + 'general damage', val(j, 'general_damage', ''), j + ' : general_damage'),
              inp.put(prefix + 'specific damage', val(j, 'specific_damage', ''), j + ' : specific_damage')]
    return hit * pps, groups


def reload_time(fp, inp, prefix):
    """The first-person reload_empty animation: 'allow interruption' frame (else its length)."""
    g = read(fp)
    idx = next((k.split('/')[2] for k, (_t, v) in g.items()
                if k.startswith('definitions/animations/[') and k.endswith('/name')
                and v.endswith(':reload_empty')), None)
    if idx is None:
        raise SystemExit('%s: no reload_empty animation' % fp)
    base = 'definitions/animations/%s/shared animation data/[0]/' % idx
    frames = float(g[base + 'frame count'][1])
    use, how = frames, 'frame count'
    i = 0
    while base + 'frame events/[%d]/type' % i in g:
        if g[base + 'frame events/[%d]/type' % i][1] == 'allow interruption':
            use, how = float(g[base + 'frame events/[%d]/frame' % i][1]), 'allow interruption frame'
        i += 1
    return inp.put(prefix + 'reload s', use / 30.0,
                   '%s : animations %s first_person:reload_empty %s %g (of %g frames) / 30'
                   % (fp, idx, how, use, frames))


# ----------------------------------------------------------------------------- targets
def player_pool(inp):
    check_ref(PLAYER['biped'], 'unit/object/model', PLAYER['model'])
    m = PLAYER['model']
    body = number(m, 'new damage info/[0]/body/maximum vitality', inp, 'player body vitality')
    shield = number(m, 'new damage info/[0]/shield/maximum shield vitality', inp, 'player shield vitality')
    delay = number(m, 'new damage info/[0]/shield/stun time', inp, 'player shield recharge delay s')
    smat = inp.put('player shield material', val(m, 'new damage info/[0]/shield/global shield material name'),
                   m + ' : new damage info/[0]/shield/global shield material name')
    bmat = inp.put('player body material', body_material(m), m + " : model materials ['body'] global material name")
    return {'body': body, 'shield': shield, 'delay': delay, 'shield_mat': smat, 'body_mat': bmat}


def body_material(model):
    h = read(model)
    for k, (_t, v) in h.items():
        if k.startswith('model materials/') and k.endswith('/material name') and v == 'body':
            return h[k.rsplit('/', 1)[0] + '/global material name'][1]
    return h.get('new damage info/[0]/global indirect material name', ('', ''))[1]


def enemy_pool(e, diff, inp):
    c, m = e['char'], e['model']
    check_ref(c, 'unit', e['biped'])
    check_ref(e['biped'], 'unit/object/model', m)
    if int(val(c, 'vitality properties/#count', '0')) < 1:
        raise SystemExit('%s: no vitality properties' % c)
    v = 'vitality properties/[0]/'
    body = number(c, v + 'legendary body vitality', inp, 'target legendary body vitality') * diff['enemy_vitality']
    shield = number(c, v + 'legendary shield vitality', inp, 'target legendary shield vitality') * diff['enemy_shield']
    delay = number(c, v + 'shield recharge delay time', inp, 'target shield recharge delay s')
    body_delay = number(c, v + 'body recharge delay time', inp, 'target body recharge delay s')
    body_frac = number(c, v + 'body recharge fraction', inp, 'target body recharge fraction')
    h = read(m)
    if int(h.get('new damage info/#count', ('', '0'))[1] or 0):
        smat = inp.put('target shield material', h['new damage info/[0]/shield/global shield material name'][1],
                       m + ' : new damage info/[0]/shield/global shield material name')
    else:                                   # old-style damage info (the Reach Brute)
        smat, i = '', 0
        while 'damage info/damage sections/[%d]/name' % i in h:
            if h['damage info/damage sections/[%d]/name' % i][1] == 'shield':
                smat = h['damage info/damage sections/[%d]/shield material name' % i][1]
                inp.put('target shield material', smat,
                        m + " : damage info/damage sections/[%d] 'shield' shield material name" % i)
            i += 1
    bmat = inp.put('target body material', body_material(m), m + " : model materials ['body'] global material name")
    return {'body': body, 'shield': shield, 'delay': delay, 'body_delay': body_delay,
            'body_frac': body_frac, 'shield_mat': smat, 'body_mat': bmat}


# ----------------------------------------------------------------------------- weapons
def repeater_time(n):
    """Seconds to the n-th Plasma Repeater shot, trigger held from cold: heat 0.9/s while
    firing (0.03 a tick), rate 15 -> 3 by heat^1.5, never overheats."""
    if n is None:
        return None
    hi, lo = 15.0, 3.0
    t = 0.0
    for _ in range(1, n):
        heat = min(1.0, REPEATER['heat_per_tick'] * 30.0 * t)
        t += 1.0 / (hi + (lo - hi) * heat ** REPEATER['rate_exponent'])
    return t


def player_weapon(wdef, inp):
    w = wdef['weapon']
    pre = 'weapon '
    hit, groups = damage_effect(wdef, inp, pre)
    rps = number(w, 'barrels/[0]/firing/rounds per second', inp, pre + 'rounds per second (first of pair)')
    rec = number(w, 'barrels/[0]/firing/fire recovery time', inp, pre + 'fire recovery time')
    mag = int(number(w, 'magazines/[0]/rounds loaded maximum', inp, pre + 'magazine'))
    age = number(w, 'barrels/[0]/campaign age generated per round', inp, pre + 'campaign age per round (battery)')
    heat = number(w, 'barrels/[0]/heat generated per round', inp, pre + 'heat per round (field)')
    hfun = inp.put(pre + 'heat per round function', val(w, 'barrels/[0]/heat generated per round function', ''),
                   w + ' : barrels/[0]/heat generated per round function')
    spec = {'hit': hit, 'groups': groups, 'mag': mag, 'reload': 0.0, 'heat': heat}
    if hfun:                                            # Plasma Repeater: heat in functions
        rate = val(w, 'barrels/[0]/firing/rounds per second')
        inp.put(pre + 'rate by heat', '15 -> 3 (rounds per second %s) by heat^%g' % (rate, REPEATER['rate_exponent']),
                REPEATER['src'])
        inp.put(pre + 'heat per tick firing', REPEATER['heat_per_tick'], REPEATER['src'])
        inp.put(pre + 'never overheats', 'never overheats' in val(w, 'secondary flags', ''),
                w + ' : secondary flags')
        spec['time'] = repeater_time
        spec['battery'] = int(round(1.0 / age)) if age else 0
        return spec
    interval = max(1.0 / rps, rec)
    inp.put(pre + 'interval s', interval, 'max(1 / rounds per second, fire recovery time)')
    if mag and wdef.get('fp'):
        spec['reload'] = reload_time(wdef['fp'], inp, pre)
    over = tc.num(read(w).get('overheated threshold'), 1.0) or 1.0
    spec['time'] = lambda n: tc.player_time(n, interval, mag=mag, reload=spec['reload'],
                                            heat_per_shot=heat, overheat_at=over)
    return spec


def ai_weapon(e, inp):
    """(weapon key, its def, firing numbers) for an enemy's default campaign weapon."""
    sq = e['squad']
    wname = (val(sq, 'cell templates/[0]/initial weapon/[0]/weapon type') or '').split(',')[0]
    inp.put('enemy default weapon', wname, sq + ' : cell templates/[0]/initial weapon/[0]/weapon type')
    if wname not in AI_WEAPONS:
        raise SystemExit('%s: no weapon definition for %s' % (e['name'], wname))
    # the firing pattern: the character's own entry for the weapon, else its parent's
    path, seen = e['char'], set()
    while path and path not in seen:
        seen.add(path)
        c = read(path)
        i = 0
        while 'firing pattern properties/[%d]/weapon' % i in c:
            if c['firing pattern properties/[%d]/weapon' % i][1].split(',')[0] == wname:
                return wname, path, i
            i += 1
        parent = (c.get('parent character', ('', ''))[1] or '').split(',')[0]
        path = {'generic': r'ai\generic.character'}.get(parent) if parent else None
    raise SystemExit('%s: no firing pattern for %s' % (e['name'], wname))


# ----------------------------------------------------------------------------- rows
def main():
    table, mats = globals_tables()
    rows, notes = [], []
    gi = Inputs()
    diff = difficulty(gi)
    pinp = Inputs()
    player = player_pool(pinp)

    for e in ENEMIES:
        einp = Inputs()
        tgt = enemy_pool(e, diff, einp)
        for wdef in PLAYER_WEAPONS:
            inp = Inputs(einp)
            inp.update(gi)
            spec = player_weapon(wdef, inp)
            ms, why_s = multiplier(spec['groups'], tgt['shield_mat'], table, mats)
            mb, why_b = multiplier(spec['groups'], tgt['body_mat'], table, mats)
            inp.put('shield multiplier', ms, GLOBALS + ' damage table [0] / materials: ' + why_s)
            inp.put('body multiplier', mb, GLOBALS + ' damage table [0] / materials: ' + why_b)
            hs, hb = spec['hit'] * ms, spec['hit'] * mb
            inp.put('hit vs shield', hs, 'damage per hit x shield multiplier')
            inp.put('hit vs body', hb, 'damage per hit x body multiplier')
            n, _ = tc.shots_to_kill(tgt['shield'], tgt['body'], hs, hb)
            secs = spec['time'](n)
            flags = []
            if n and spec['mag'] and n > spec['mag']:
                flags.append('needs %d reload(s) (magazine %d, reload %.2f s)'
                             % ((n - 1) // spec['mag'], spec['mag'], spec['reload']))
            if n and spec.get('battery') and n > spec['battery']:
                flags.append('more shots than one battery (%d)' % spec['battery'])
            if secs is not None and tgt['delay'] > 0 and secs > tgt['delay']:
                flags.append('fight (%.2f s) outlasts shield recharge delay (%g s)' % (secs, tgt['delay']))
            if tgt['delay'] <= 0 and tgt['shield'] > 0:
                flags.append('shield never recharges (character shield recharge delay/time 0)')
            if tgt['body_frac'] > 0 and secs is not None and secs > tgt['body_delay']:
                flags.append('fight (%.2f s) outlasts body recharge delay (%g s, %g of body)'
                             % (secs, tgt['body_delay'], tgt['body_frac']))
            if spec.get('battery'):
                flags.append('rate falls with heat (15 -> 3/s); the manual vent (2.5 s) is not used')
            rows.append({'direction': 'player->enemy', 'attacker': PLAYER['name'], 'target': e['name'],
                         'weapon': wdef['name'], 'shots': n,
                         'seconds': None if secs is None else round(secs, 3),
                         'inputs': inp, 'flags': flags})

        # enemy -> player
        inp = Inputs(pinp)
        inp.update(gi)
        wkey, fpath, fi = ai_weapon(e, inp)
        wdef = AI_WEAPONS[wkey]
        hit, groups = damage_effect(wdef, inp, 'weapon ')
        fp = 'firing pattern properties/[%d]/firing patterns/[1]/' % fi       # really accurate
        c = read(fpath)
        label = 'firing pattern %s [%d] really accurate ' % (wkey, fi)
        rof = number(fpath, fp + 'rate of fire', inp, label + 'rate of fire')
        bd = number(fpath, fp + 'burst duration', inp, label + 'burst duration (mean)', mean=True)
        bs = number(fpath, fp + 'burst separation', inp, label + 'burst separation (mean)', mean=True)
        wdm = number(fpath, fp + 'weapon damage modifier', inp, label + 'weapon damage modifier')
        number(fpath, 'firing pattern properties/[%d]/firing patterns/[0]/rate of fire' % fi, inp,
               'firing pattern %s inaccurate rate of fire (Legendary starts at accuracy 0.3)' % wkey)
        acc = None
        i = 0
        while 'weapons properties/[%d]/weapon' % i in c:
            if c['weapons properties/[%d]/weapon' % i][1].split(',')[0] == wkey:
                acc = number(fpath, 'weapons properties/[%d]/legendary accuracy bounds' % i, inp,
                             'legendary accuracy bounds (first)')
                number(fpath, 'weapons properties/[%d]/legendary accuracy time' % i, inp,
                       'legendary accuracy time s')
            i += 1
        wrps = number(wdef['weapon'], 'barrels/[0]/firing/rounds per second', inp,
                      'weapon rounds per second (first of pair)')
        wrps_max = float(str(val(wdef['weapon'], 'barrels/[0]/firing/rounds per second')).split(',')[-1])
        rate = (rof or max(wrps, wrps_max)) * diff['rate_of_fire']
        rate = min(rate, max(wrps, wrps_max))
        inp.put('ai shots per second', rate, 'pattern rate of fire (0 = weapon rate) x legendary '
                'rate of fire, capped by the weapon rounds per second')
        sep = bs * diff['burst_separation']
        inp.put('ai burst separation s', sep, 'pattern burst separation x legendary burst separation')
        mod = wdm if wdm > 0 else 1.0
        inp.put('ai weapon damage modifier used', mod, 'pattern weapon damage modifier (0 = unset -> 1)')
        ms, why_s = multiplier(groups, player['shield_mat'], table, mats)
        mb, why_b = multiplier(groups, player['body_mat'], table, mats)
        inp.put('shield multiplier', ms, GLOBALS + ' damage table [0] / materials: ' + why_s)
        inp.put('body multiplier', mb, GLOBALS + ' damage table [0] / materials: ' + why_b)
        scale = diff['enemy_damage'] * mod
        hs, hb = hit * ms * scale, hit * mb * scale
        inp.put('hit vs shield', hs, 'damage x shield multiplier x legendary enemy damage x modifier')
        inp.put('hit vs body', hb, 'damage x body multiplier x legendary enemy damage x modifier')
        n, _ = tc.shots_to_kill(player['shield'], player['body'], hs, hb)
        held, paced = tc.ai_times(n, rate, bd, sep)
        flags = []
        if paced is not None and paced > player['delay']:
            flags.append('fight (%.2f s paced) outlasts player shield recharge delay (%g s)'
                         % (paced, player['delay']))
        heat = tc.num(read(wdef['weapon']).get('barrels/[0]/heat generated per round'))
        over = tc.num(read(wdef['weapon']).get('overheated threshold'), 1.0) or 1.0
        rec = tc.num(read(wdef['weapon']).get('heat recovery threshold'))
        if heat > 0 and rec < over and n and n * heat >= over:
            k = int(over / heat + 0.999)
            flags.append('AI weapon overheat not modelled: %d rounds overheat it if heat does not '
                         'cool while firing (heat %.3g/round, threshold %g)' % (k, heat, over))
        if acc is not None and acc < 1:
            flags.append('first %g s of a fight the AI fires between the inaccurate and really '
                         'accurate patterns (accuracy %g -> 1)'
                         % (tc.num(inp['legendary accuracy time s']['value']), acc))
        rows.append({'direction': 'enemy->player', 'attacker': e['name'], 'target': PLAYER['name'],
                     'weapon': wdef['name'], 'shots': n,
                     'seconds': None if held is None else round(held, 3),
                     'seconds_paced': None if paced is None else round(paced, 3),
                     'inputs': inp, 'flags': flags})

    notes += [
        'Legendary = the globals difficulty "imposs." column: enemy damage 1.6, enemy vitality / '
        'shield 1 (the characters carry their own legendary pools), rate of fire 1, burst '
        'separation 0.5.',
        'Enemy pools are the character vitality properties (legendary body / shield); they '
        'replace the model numbers (elite_ai.model 50 / 79, brute.model damage info 60).',
        'Every damage-table row found multiplies (general and specific damage group x general and '
        'specific armour, missing = 1); armours come up the globals material parent chain. Reach '
        'has no *_player rows, so the Spartan / Elite specific armours add nothing.',
        'The Reach Brute body is soft_organic_flesh (model materials "body"); its armour is the '
        'damage section "shield" with energy_shield_thin. tough_organic_flesh_brute is only the '
        'biped physics / indirect (area) material, not used for direct body shots.',
        'The Brute armour does not recharge (character shield recharge delay and time 0); its '
        'BODY recharges 35% after 8 s, flagged where a fight outlasts it.',
        'AI fire = the "really accurate" firing pattern (Legendary accuracy reaches 1 within 3 s); '
        'burst duration / separation = the mean of their bounds; co-op modifiers not applied (solo).',
        'Default AI weapons come from the campaign squad templates (Elite minor: plasma rifle; '
        'Brute: spike rifle); the character tags only list weapon handling.',
        'Reload times are the first-person reload_empty "allow interruption" frame / 30 '
        '(Reach reloads are animation-driven).',
        'Plasma Repeater heat curves are not in the XML export; the B3 research values are used '
        '(0.03 heat a tick firing, rate 15 + (3-15) x heat^1.5, never overheats). Holding the '
        'trigger is modelled; a manual vent (2.5 s) is not.',
        'Bloom / spread ignored (every shot hits), body shots only.',
    ]
    path = tc.write(GAME, rows, notes)
    print(path)
    print('%-14s %-16s %-16s %-16s %6s %8s %8s  flags' % ('direction', 'attacker', 'target', 'weapon',
                                                          'shots', 'held s', 'paced s'))
    for r in rows:
        print('%-14s %-16s %-16s %-16s %6s %8s %8s  %s' % (
            r['direction'], r['attacker'], r['target'], r['weapon'], r['shots'], r['seconds'],
            r.get('seconds_paced', ''), ' | '.join(r['flags'])))


if __name__ == '__main__':
    main()

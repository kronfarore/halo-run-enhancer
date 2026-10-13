r"""Time-to-kill on LEGENDARY, HALO 4 (MCC) -- the collector (user, 2026-10-13).

Method: ttk_common (signed off). READ-ONLY: every tag comes from H4EK through
ttk_common.flatten (private export file); nothing is written but reports/ttk/ttk_halo_4.json.

Where Halo 4 keeps what this needs (all verified on the H4EK tags, 2026-10-13):
  * ENEMY POOL     character `vitality properties` (legendary body / shield vitality,
                   shield recharge delay), walked up `parent character`; x matg Difficulty
                   `imposs. enemy vitality` / `imposs. enemy shield` (both 1.0 in Halo 4).
                   The character's `player damage_scale` (0 = 1, tool.exe's own doc) scales
                   what the player deals.
  * PLAYER POOL    storm_masterchief hlmt. Two spellings, same numbers: legacy `new damage
                   info` body 45 / shield 70 and the root `damage info` 70 x body section
                   0.642857 = 45, shield section 1.0 x 70 = 70. No player difficulty dial.
  * MATERIALS      the hlmt ROOT `damage info` (Halo 4's own layout): shield = the `shield`
                   section's shield material, body = the model material named *body*, else
                   the indirect material. Disagreement with the legacy block is flagged (the
                   Knight's legacy block is a stale Elite copy).
  * MULTIPLIER     matg `damage table` [0] (= "default"; [1] is the native Tilt table):
                   EVERY row found multiplies -- jpt general_damage and specific_damage, each
                   against the material's general armor and specific armor (each inherited
                   up `parent name`); a missing row = 1.
  * PLAYER WEAPON  weapon barrel[0]: rounds per second (mean of the pair), fire recovery
                   time, shots per fire (the BR's burst), heat / overheat, magazine;
                   projectile `impact damage` -> jpt `damage upper bound` (mean of the pair).
                   RELOAD has no weapon field in Halo 4: it is the first-person animation
                   `first_person:reload_empty` frame count / 30.
  * AI FIRE        the character's `firing pattern properties` entry for its weapon (none on
                   the Elite / Knight: inherited from ai\generic). tool.exe documents the
                   block: element [0] 'inaccurate' / [1] 'really accurate', interpolated by
                   the AI's ACCURACY, which runs from `legendary accuracy bounds` lo to hi
                   over `legendary accuracy time` of continuous fire (weapons properties);
                   elements [2]+ are AI-trait-weapon overrides, not difficulty tiers.
                   `rate of fire` = trigger pulls per second (0 = held -> the weapon's own
                   rate); `weapon damage modifier` (0 = none) scales the damage. matg
                   Difficulty `imposs. rate of fire` / `burst separation` / `enemy damage`.

    python ttk_halo4.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc                                             # noqa: E402

KIT = 'H4EK'
GAME = 'Halo 4'
GLOBALS = r'globals\globals.globals'
GENERIC = r'ai\generic.character'
PLAYER_BIPED = r'objects\characters\storm_masterchief\storm_masterchief.biped'
FPS = 30.0
W = r'objects\weapons\rifle'
FP = r'objects\characters\storm_fp\weapons\rifle'
PLAYER_WEAPONS = [
    ('Assault Rifle', W + r'\storm_assault_rifle\storm_assault_rifle.weapon',
     FP + r'\fp_assault_rifle\storm_fp_assault_rifle.model_animation_graph'),
    ('Storm Rifle', W + r'\storm_assault_carbine\storm_assault_carbine.weapon', None),
    ('Battle Rifle', W + r'\storm_br\storm_br.weapon',
     FP + r'\fp_br\storm_fp_br.model_animation_graph'),
]
C = r'objects\characters'
ENEMIES = [
    ('Elite (minor)', C + r'\storm_elite\ai\storm_elite.character'),
    ('Knight', C + r'\storm_knight\ai\storm_knight.character'),
]
LEG = 'imposs.'                    # matg Difficulty's Legendary column


def ref(v):
    """tag path of a flattened tag reference ('path,grp' -> 'path.<ext>' left to caller)."""
    return (v[1] if isinstance(v, tuple) else v or '').split(',')[0].strip()


def g(vals, key, default=None):
    v = vals.get(key)
    return default if v is None else v[1]


# ----------------------------------------------------------------------------- globals
class Globals:
    def __init__(self):
        m = self.m = tc.flatten(KIT, GLOBALS)
        self.table = {}
        for k, (_t, v) in m.items():
            p = k.split('/')
            if p[:2] == ['damage table', '[0]'] and len(p) == 7 and p[2] == 'damage groups' \
                    and p[4] == 'armor modifiers' and p[6] == 'damage multiplier':
                grp = m['/'.join(p[:4]) + '/name'][1]
                arm = m['/'.join(p[:6]) + '/name'][1]
                self.table.setdefault(grp, {})[arm] = (float(v), k)
        self.mats = {}
        for k, (_t, v) in m.items():
            p = k.split('/')
            if p[0] == 'materials' and len(p) == 3 and p[2] == 'name':
                b = '/'.join(p[:2])
                self.mats.setdefault(v, {'index': p[1], 'parent': g(m, b + '/parent name', ''),
                                         'general': g(m, b + '/general armor', ''),
                                         'specific': g(m, b + '/specific armor', '')})

    def diff(self, field):
        key = 'difficulty/[0]/%s %s' % (LEG, field)
        return tc.num(self.m[key]), 'globals\\globals.globals: ' + key

    def armors(self, material):
        """(general armor, specific armor, chain): each the first non-empty up the parents."""
        gen = spec = ''
        chain, seen, x = [], set(), material
        while x and x not in seen and x in self.mats:
            seen.add(x)
            e = self.mats[x]
            chain.append('%s %s' % (e['index'], x))
            gen = gen or e['general']
            spec = spec or e['specific']
            x = e['parent']
        return gen, spec, chain

    def multiplier(self, groups, material):
        """Product of EVERY damage-table row found: each damage group x each armor."""
        gen, spec, chain = self.armors(material)
        total, rows = 1.0, []
        for grp in dict.fromkeys(x for x in groups if x):
            for arm in dict.fromkeys(x for x in (gen, spec) if x):
                hit = self.table.get(grp, {}).get(arm)
                if hit:
                    total *= hit[0]
                    rows.append('%s x %s = %g (%s)' % (grp, arm, hit[0], hit[1]))
                else:
                    rows.append('%s x %s: no row (1)' % (grp, arm))
        return total, {'material': material, 'materials chain': ' -> '.join(chain),
                       'general armor': gen, 'specific armor': spec, 'rows': rows,
                       'multiplier': total}


# ----------------------------------------------------------------------------- bodies
def hlmt_of_biped(biped):
    b = tc.flatten(KIT, biped)
    return ref(b['unit/object/model']) + '.model'


def model_damage(model):
    """Pools and materials from the hlmt. Root `damage info` (Halo 4) is used; the legacy
    `new damage info` block is read for comparison."""
    h = tc.flatten(KIT, model)
    root_max = tc.num(h.get('damage info/maximum vitality'))
    body_pct = shield_pct = None
    shield_mat = shield_stun = None
    n = int(tc.num(h.get('damage info/damage sections/#count')))
    for i in range(n):
        b = 'damage info/damage sections/[%d]/' % i
        name = g(h, b + 'name', '')
        if name == 'body':
            body_pct = tc.num(h[b + 'vitality percentage'])
        if name == 'shield':
            shield_pct = tc.num(h[b + 'vitality percentage'])
            shield_mat = g(h, b + 'shield material name', '')
            shield_stun = tc.num(h[b + 'stun time'])
    body_mat = ''
    for k, (_t, x) in h.items():
        if k.startswith('model materials/') and k.endswith('/material name') \
                and 'body' in x.lower():
            body_mat = h[k.rsplit('/', 1)[0] + '/global material name'][1]
            break
    indirect = g(h, 'damage info/indirect material name', '')
    legacy = {'body vitality': tc.num(h.get('new damage info/[0]/body/maximum vitality')),
              'shield vitality': tc.num(h.get('new damage info/[0]/shield/maximum shield vitality')),
              'shield material': g(h, 'new damage info/[0]/shield/global shield material name', ''),
              'indirect material': g(h, 'new damage info/[0]/global indirect material name', ''),
              'shield stun time': tc.num(h.get('new damage info/[0]/shield/stun time'))}
    return {'tag': model, 'root maximum vitality': root_max, 'body section %': body_pct,
            'shield section %': shield_pct,
            'body': root_max * (body_pct or 0), 'shield': root_max * (shield_pct or 0),
            'shield material': shield_mat, 'body material': body_mat or indirect,
            'body material source': 'model materials (*body*)' if body_mat else 'indirect material',
            'indirect material': indirect, 'shield stun time (root)': shield_stun,
            'legacy new damage info': legacy}


def character(path):
    """vitality (legendary) + unit + initial weapon + firing data, up the parent chain."""
    out, seen, p, chain = {}, set(), path, []
    while p and p not in seen:
        seen.add(p)
        chain.append(p)
        c = tc.flatten(KIT, p)
        if 'vitality' not in out and int(tc.num(c.get('vitality properties/#count'))):
            v = 'vitality properties/[0]/'
            out['vitality'] = {
                'body': tc.num(c[v + 'legendary body vitality']),
                'shield': tc.num(c[v + 'legendary shield vitality']),
                'normal body': tc.num(c[v + 'normal body vitality']),
                'normal shield': tc.num(c[v + 'normal shield vitality']),
                'shield recharge delay': tc.num(c[v + 'shield recharge delay time']),
                'shield recharge time': tc.num(c[v + 'shield recharge time']),
                'body recharge fraction': tc.num(c[v + 'body recharge fraction']),
                'player damage_scale': tc.num(c[v + 'player damage_scale']),
                'source': p + ': vitality properties/[0]/legendary body|shield vitality'}
        if 'unit' not in out and ref(c.get('unit')):
            out['unit'] = ref(c['unit']) + '.biped'
        w = ref(c.get('general properties/[0]/initial primary weapon '))
        if 'weapon' not in out and w:
            out['weapon'] = w + '.weapon'
            out['weapon source'] = p + ': general properties/[0]/initial primary weapon'
        p = ref(c.get('parent character'))
        p = p + '.character' if p else None
    out['chain'] = chain
    return out


def firing_data(chain, weapon):
    """(weapons properties, firing patterns, source) for a weapon: the first character
    up the chain whose block is non-empty -- a non-empty block REPLACES the parent's."""
    stem = weapon[:-len('.weapon')]
    res = {}
    for blk in ('weapons properties', 'firing pattern properties'):
        for p in chain:
            c = tc.flatten(KIT, p)
            n = int(tc.num(c.get(blk + '/#count')))
            if not n:
                continue
            for i in range(n):
                if ref(c.get('%s/[%d]/weapon' % (blk, i))) == stem:
                    res[blk] = (p, i, c)
                    break
            break
    return res


def lerp(a, b, t):
    return a + (b - a) * t


def mean_pair(v):
    xs = [float(x) for x in str(v).split(',') if x.strip()]
    return sum(xs) / len(xs) if xs else 0.0


def ai_fire(chain, weapon, wpn_vals, glob):
    """AI firing numbers at Legendary, at the START (accuracy lo) and the END (accuracy hi)
    of a burst series."""
    fd = firing_data(chain, weapon)
    inputs, flags = {}, []
    wp_char, wi, wc = fd['weapons properties']
    wb = 'weapons properties/[%d]/' % wi
    acc = [float(x) for x in g(wc, wb + 'legendary accuracy bounds').split(',')]
    acc_t = tc.num(wc[wb + 'legendary accuracy time'])
    inputs['legendary accuracy bounds'] = (acc, '%s: %slegendary accuracy bounds' % (wp_char, wb))
    inputs['legendary accuracy time'] = (acc_t, '%s: %slegendary accuracy time' % (wp_char, wb))
    fp_char, fi, fc = fd['firing pattern properties']
    fb = 'firing pattern properties/[%d]/firing patterns/' % fi
    npat = int(tc.num(fc[fb + '#count']))
    pats = []
    for j in range(min(2, npat)):
        b = fb + '[%d]/' % j
        pats.append({'rate of fire': tc.num(fc[b + 'rate of fire']),
                     'burst duration': mean_pair(g(fc, b + 'burst duration')),
                     'burst separation': mean_pair(g(fc, b + 'burst separation')),
                     'weapon damage modifier': tc.num(fc[b + 'weapon damage modifier'])})
    inputs['firing patterns [0] inaccurate / [1] really accurate'] = (
        pats, '%s: %s[0..1] (burst duration / separation = mean of the bounds)' % (fp_char, fb))
    if npat > 2:
        flags.append('firing patterns [2..%d] exist (AI-trait-weapon overrides per tool.exe: '
                     '"VALID_INDEX(block_index-2, k_num_ai_trait_weapon-2)"); not used'
                     % (npat - 1))
    rps_w = mean_pair(g(wpn_vals, 'barrels/[0]/firing/rounds per second'))
    rec_w = tc.num(wpn_vals['barrels/[0]/firing/fire recovery time'])
    rof_scale, rof_src = glob.diff('rate of fire')
    sep_scale, sep_src = glob.diff('burst separation')
    inputs['difficulty rate of fire'] = (rof_scale, rof_src)
    inputs['difficulty burst separation'] = (sep_scale, sep_src)
    out = {}
    for label, a in (('start', acc[0]), ('end', acc[-1])):
        p0, p1 = pats[0], pats[-1]
        # 0 = 'continuously held down' -> the weapon's own held rate; otherwise trigger
        # pulls per second, one round per pull once the barrel has recovered (tap cap
        # 1 / fire recovery time)
        r0, r1 = (pt['rate of fire'] for pt in (p0, p1))
        if r0 <= 0 and r1 <= 0:
            rof = 0.0
            sps = rps_w
        else:
            rof = lerp(r0 if r0 > 0 else rps_w, r1 if r1 > 0 else rps_w, a)
            sps = min(rof, 1.0 / rec_w) if rec_w else rof
        wdm = lerp(p0['weapon damage modifier'], p1['weapon damage modifier'], a) or 1.0
        out[label] = {'accuracy': a, 'shots per second': sps * rof_scale,
                      'burst duration': lerp(p0['burst duration'], p1['burst duration'], a),
                      'burst separation': lerp(p0['burst separation'], p1['burst separation'], a)
                      * sep_scale,
                      'weapon damage modifier': wdm, 'pattern rate of fire': rof}
    inputs['weapon rounds per second'] = (rps_w, weapon + ': barrels/[0]/firing/rounds per second')
    inputs['weapon fire recovery time'] = (rec_w, weapon + ': barrels/[0]/firing/fire recovery time')
    return out, inputs, flags


# ----------------------------------------------------------------------------- weapons
def weapon_shot(weapon):
    """damage per projectile hit, groups, projectile path."""
    w = tc.flatten(KIT, weapon)
    proj = ref(w['barrels/[0]/projectile']) + '.projectile'
    p = tc.flatten(KIT, proj)
    jpt = ref(p['impact damage']) + '.damage_effect'
    d = tc.flatten(KIT, jpt)
    dmg = mean_pair(g(d, 'damage upper bound'))
    groups = [g(d, 'general_damage', ''), g(d, 'specific_damage', '')]
    info = {'projectile': proj, 'damage effect': jpt, 'damage upper bound': dmg,
            'damage lower bound': tc.num(d.get('damage lower bound')),
            'air damage range': g(p, 'air damage range'),
            'general_damage': groups[0], 'specific_damage': groups[1],
            'projectiles per shot': tc.num(w.get('barrels/[0]/projectiles per shot'), 1) or 1}
    return w, info, groups


def reload_seconds(graph):
    if not graph:
        return None, None
    a = tc.flatten(KIT, graph)
    for k, (_t, v) in a.items():
        if k.startswith('definitions/animations/') and k.endswith('/name') \
                and v == 'first_person:reload_empty':
            b = k.rsplit('/', 1)[0]
            fc = tc.num(a[b + '/shared animation data/[0]/frame count'])
            return fc / FPS, '%s: %s/shared animation data/[0]/frame count = %d (/30 fps)' % (
                graph, b, fc)
    return None, None


def player_weapon(label, weapon, graph):
    w, shot, groups = weapon_shot(weapon)
    B = 'barrels/[0]/'
    rps = mean_pair(g(w, B + 'firing/rounds per second'))
    rec = tc.num(w[B + 'firing/fire recovery time'])
    spf = int(mean_pair(g(w, B + 'firing/shots per fire')) or 0)
    heat = tc.num(w.get(B + 'heat generated per round'))
    over = tc.num(w.get('overheated threshold')) or 1.0
    rthr = tc.num(w.get('heat recovery threshold'))
    oloss = tc.num(w.get('overheated heat loss per second'))
    mag = int(tc.num(w.get('magazines/[0]/rounds loaded maximum')))
    rps_shot = int(tc.num(w.get(B + 'rounds per shot'), 1))
    reload_s, reload_src = reload_seconds(graph) if mag and rps_shot else (None, None)
    pause = (over - rthr) / oloss if heat and oloss else 0.0
    m = {'label': label, 'weapon': weapon, 'shot': shot, 'groups': groups,
         'rounds per second': rps, 'fire recovery time': rec, 'shots per fire': spf,
         'interval': 1.0 / rps if rps else rec, 'heat per round': heat,
         'overheated threshold': over, 'heat recovery threshold': rthr,
         'overheated heat loss per second': oloss, 'overheat pause': pause,
         'magazine': mag if rps_shot else 0, 'reload': reload_s or 0.0,
         'reload source': reload_src}
    if not spf:
        # automatic: held trigger fires at the rate of fire; a single fire's recovery
        # (tap cap) only matters when it is longer
        m['interval'] = max(1.0 / rps if rps else 0.0, rec)
    return m


def burst_time(n, m):
    """BR: `shots per fire` rounds at 1/rps, then `fire recovery time` from the burst's last
    round to the next burst's first, magazine reloads in between."""
    if n is None:
        return None
    spf, dt, rec = m['shots per fire'], m['interval'], m['fire recovery time']
    t, inmag = 0.0, m['magazine']
    for i in range(1, n):
        step = dt if i % spf else max(dt, rec)
        if m['magazine']:
            inmag -= 1
            if inmag <= 0:
                step = max(step, m['reload'])
                inmag = m['magazine']
        t += step
    return t


# ----------------------------------------------------------------------------- main
def main():
    G = Globals()
    rows, notes = [], []
    vit_s, vit_src = G.diff('enemy vitality')
    sh_s, sh_src = G.diff('enemy shield')
    dmg_s, dmg_src = G.diff('enemy damage')

    # player
    p_model = hlmt_of_biped(PLAYER_BIPED)
    P = model_damage(p_model)
    P_body, P_shield = P['body'], P['shield']
    p_flags = []
    lg = P['legacy new damage info']
    if abs(lg['body vitality'] - P_body) > 0.01 or abs(lg['shield vitality'] - P_shield) > 0.01:
        p_flags.append('player pool: root %g/%g vs legacy block %g/%g'
                       % (P_body, P_shield, lg['body vitality'], lg['shield vitality']))
    p_delay = min(x for x in (P['shield stun time (root)'], lg['shield stun time']) if x)
    if P['shield stun time (root)'] != lg['shield stun time']:
        p_flags.append('player shield recharge delay: root shield-section stun time %g s vs '
                       'legacy block %g s; flagging against the shorter (%g s)'
                       % (P['shield stun time (root)'], lg['shield stun time'], p_delay))
    player_inputs = {
        'player hlmt': p_model + ' (from ' + PLAYER_BIPED + ': unit/object/model)',
        'player body': (P_body, '%s: damage info/maximum vitality %g x body section vitality '
                        'percentage %g' % (p_model, P['root maximum vitality'], P['body section %'])),
        'player shield': (P_shield, '%s: damage info/maximum vitality %g x shield section %g'
                          % (p_model, P['root maximum vitality'], P['shield section %'])),
        'player shield recharge delay': (p_delay, 'shield section stun time (root %g / legacy %g)'
                                         % (P['shield stun time (root)'], lg['shield stun time'])),
        'player shield material': P['shield material'],
        'player body material': '%s (%s)' % (P['body material'], P['body material source'])}

    weapons = [player_weapon(*x) for x in PLAYER_WEAPONS]

    for ename, cpath in ENEMIES:
        ch = character(cpath)
        vit = ch['vitality']
        e_model = hlmt_of_biped(ch['unit'])
        E = model_damage(e_model)
        e_body = vit['body'] * vit_s
        e_shield = vit['shield'] * sh_s
        pds = vit['player damage_scale'] or 1.0
        e_flags = []
        lgE = E['legacy new damage info']
        if lgE['shield material'] != E['shield material'] or \
                lgE['indirect material'] != E['indirect material']:
            e_flags.append('%s hlmt: root damage info (used) shield %s / indirect %s, legacy '
                           '`new damage info` says shield %s / indirect %s' % (
                               ename, E['shield material'], E['indirect material'],
                               lgE['shield material'], lgE['indirect material']))
        enemy_inputs = {
            'character chain': ' -> '.join(ch['chain']),
            'enemy body (legendary)': (vit['body'], vit['source']),
            'enemy shield (legendary)': (vit['shield'], vit['source']),
            'normal body/shield (not used)': (vit['normal body'], vit['normal shield']),
            'difficulty enemy vitality': (vit_s, vit_src),
            'difficulty enemy shield': (sh_s, sh_src),
            'enemy shield recharge delay': (vit['shield recharge delay'],
                                            cpath + ': vitality properties/[0]/shield recharge delay time'),
            'player damage_scale': (vit['player damage_scale'], '0 = 1 (tool.exe doc)'),
            'enemy hlmt': e_model + ' (from ' + ch['unit'] + ')',
            'enemy hlmt pools (overridden by the character)': (E['body'], E['shield']),
            'enemy shield material': E['shield material'],
            'enemy body material': '%s (%s)' % (E['body material'], E['body material source'])}

        # ---- player -> enemy
        for m in weapons:
            ms, why_s = G.multiplier(m['groups'], E['shield material'])
            mb, why_b = G.multiplier(m['groups'], E['body material'])
            hit = m['shot']['damage upper bound'] * m['shot']['projectiles per shot'] * pds
            n, _ = tc.shots_to_kill(e_shield, e_body, hit * ms, hit * mb)
            if m['shots per fire']:
                secs = burst_time(n, m)
            else:
                secs = tc.player_time(n, m['interval'], m['magazine'], m['reload'],
                                      m['heat per round'], m['overheated threshold'],
                                      m['overheat pause'])
            flags = list(e_flags)
            if secs is not None and secs > vit['shield recharge delay']:
                flags.append('fight outlasts the target\'s shield recharge delay (%g s)'
                             % vit['shield recharge delay'])
            pauses = []
            if m['magazine'] and n and n > m['magazine']:
                pauses.append('reload(s) %.2f s' % m['reload'])
            if m['heat per round'] and n and n * m['heat per round'] >= m['overheated threshold']:
                pauses.append('overheat %.2f s' % m['overheat pause'])
                if m['overheat pause'] >= vit['shield recharge delay']:
                    flags.append('an overheat pause is as long as the shield recharge delay')
            if pauses:
                flags.append('includes ' + ', '.join(pauses))
            if m['shot']['damage lower bound'] < m['shot']['damage upper bound']:
                flags.append('damage lower bound %g < upper %g with air damage range %s: '
                             'damage falls off with distance; upper bound used (point blank)'
                             % (m['shot']['damage lower bound'], m['shot']['damage upper bound'],
                                m['shot']['air damage range']))
            if m['shots per fire']:
                flags.append('burst weapon: %d rounds at 1/%g s, next burst %g s (fire recovery '
                             'time) after the last round; soft recovery (queueing) ignored'
                             % (m['shots per fire'], m['rounds per second'], m['fire recovery time']))
            if not m['magazine'] and not m['heat per round']:
                pass
            inputs = dict(enemy_inputs)
            inputs.update({
                'weapon': m['weapon'],
                'rounds per second': (m['rounds per second'], m['weapon'] + ': barrels/[0]/firing/rounds per second'),
                'fire recovery time': (m['fire recovery time'], m['weapon'] + ': barrels/[0]/firing/fire recovery time'),
                'shots per fire': (m['shots per fire'], m['weapon'] + ': barrels/[0]/firing/shots per fire'),
                'interval used': m['interval'],
                'magazine': (m['magazine'], m['weapon'] + ': magazines/[0]/rounds loaded maximum'),
                'reload': (m['reload'], m['reload source']),
                'heat per round / overheat at / recovery threshold / overheated loss per s': (
                    m['heat per round'], m['overheated threshold'], m['heat recovery threshold'],
                    m['overheated heat loss per second']),
                'overheat pause': (m['overheat pause'], '(overheated threshold - heat recovery '
                                   'threshold) / overheated heat loss per second'),
                'damage per hit': (m['shot']['damage upper bound'],
                                   m['shot']['damage effect'] + ': damage upper bound (mean of pair)'),
                'projectile': m['shot']['projectile'] + ': impact damage',
                'damage groups (general / specific)': m['groups'],
                'shield multiplier': why_s, 'body multiplier': why_b,
                'hit on shield': hit * ms, 'hit on body': hit * mb})
            rows.append({'direction': 'player->enemy', 'attacker': 'Player', 'target': ename,
                         'weapon': m['label'], 'shots': n,
                         'seconds': None if secs is None else round(secs, 3),
                         'inputs': inputs, 'flags': flags})

        # ---- enemy -> player
        wpn = ch['weapon']
        wv = tc.flatten(KIT, wpn)
        _w, shot, groups = weapon_shot(wpn)
        fire, f_inputs, f_flags = ai_fire(ch['chain'], wpn, wv, G)
        ms, why_s = G.multiplier(groups, P['shield material'])
        mb, why_b = G.multiplier(groups, P['body material'])
        res = {}
        for label in ('end', 'start'):
            f = fire[label]
            hit = shot['damage upper bound'] * shot['projectiles per shot'] * \
                f['weapon damage modifier'] * dmg_s
            n, _ = tc.shots_to_kill(P_shield, P_body, hit * ms, hit * mb)
            held, paced = tc.ai_times(n, f['shots per second'], f['burst duration'],
                                      f['burst separation'])
            res[label] = (n, held, paced, hit)
        n, held, paced, hit = res['end']
        flags = list(p_flags) + list(f_flags)
        if paced is not None and paced > p_delay:
            flags.append('paced fight outlasts the player\'s shield recharge delay (%g s)' % p_delay)
        n0, held0, paced0, _h0 = res['start']
        flags.append('AI accuracy runs %g -> %g over %g s (Legendary); main numbers use the END '
                     'pattern (accuracy %g); at the START (accuracy %g): %s shots, held %.2f s, '
                     'paced %.2f s' % (fire['start']['accuracy'], fire['end']['accuracy'],
                                       f_inputs['legendary accuracy time'][0],
                                       fire['end']['accuracy'], fire['start']['accuracy'],
                                       n0, held0, paced0))
        if shot['damage lower bound'] < shot['damage upper bound']:
            flags.append('damage lower bound %g < upper %g, air damage range %s: damage falls '
                         'off with distance; upper bound used (point blank)'
                         % (shot['damage lower bound'], shot['damage upper bound'],
                            shot['air damage range']))
        if tc.num(wv.get('barrels/[0]/heat generated per round')):
            flags.append('the AI weapon generates heat (%g per round); AI overheating is not '
                         'modelled' % tc.num(wv['barrels/[0]/heat generated per round']))
        mag = int(tc.num(wv.get('magazines/[0]/rounds loaded maximum')))
        if mag and n and n > mag:
            flags.append('kill needs more than one magazine (%d); AI reload not modelled' % mag)
        inputs = {'weapon': wpn + ' (' + ch['weapon source'] + ')',
                  'damage per hit': (shot['damage upper bound'],
                                     shot['damage effect'] + ': damage upper bound (mean of pair)'),
                  'projectile': shot['projectile'],
                  'damage groups (general / specific)': groups,
                  'difficulty enemy damage': (dmg_s, dmg_src),
                  'weapon damage modifier (end pattern; 0 = none)': fire['end']['weapon damage modifier'],
                  'shots per second (end pattern)': fire['end']['shots per second'],
                  'pattern rate of fire (end; 0 = held -> weapon rate)': fire['end']['pattern rate of fire'],
                  'burst duration (end)': fire['end']['burst duration'],
                  'burst separation (end, x difficulty)': fire['end']['burst separation'],
                  'start-of-series pattern': fire['start'],
                  'shield multiplier': why_s, 'body multiplier': why_b,
                  'hit on shield': hit * ms, 'hit on body': hit * mb}
        inputs.update(f_inputs)
        inputs.update(player_inputs)
        rows.append({'direction': 'enemy->player', 'attacker': ename, 'target': 'Player',
                     'weapon': os.path.basename(wpn)[:-len('.weapon')], 'shots': n,
                     'seconds': None if held is None else round(held, 3),
                     'seconds_paced': None if paced is None else round(paced, 3),
                     'inputs': inputs, 'flags': flags})

    notes += [
        'Halo 4 Legendary = matg Difficulty "imposs." column: enemy damage %g, enemy vitality %g, '
        'enemy shield %g, rate of fire %g, burst separation %g. Enemy toughness on Legendary comes '
        'from the CHARACTER: vitality properties carry separate normal / legendary body and shield '
        '(Heroic presumably uses normal; not checked in game).'
        % (dmg_s, vit_s, sh_s, G.diff('rate of fire')[0], G.diff('burst separation')[0]),
        'Damage multiplier: matg damage table [0] ("default"; [1] is the native Tilt-skull table), '
        'every row found multiplied (jpt general/specific x material general/specific armor, '
        'inherited up the parent chain; missing = 1). The Spartan, Elite materials carry the '
        'specific armors hard_metal_thin_player / energy_shield_thin_player, which have NO rows.',
        'The Battle Rifle in Halo 4 fires a 3-ROUND burst (barrel shots per fire 3,3), not 4: '
        'modelled as 3 rounds at 1/30 s, then the 0.3 s fire recovery from the last round. If the '
        'engine counts recovery after the last round\'s own 1/30 s slot, each burst cycle is '
        '0.033 s longer.',
        'Reload: Halo 4 weapons carry no reload time; the first-person reload_empty animation '
        'frame count / 30 is used (reload ends when the animation ends; animation-cancel tricks '
        'not modelled).',
        'AI fire (tool.exe field docs): firing pattern [0] "inaccurate" and [1] "really accurate" '
        'are interpolated by accuracy, which goes from the legendary accuracy bounds low to high '
        'over legendary accuracy time of firing at the target. Rate of fire = trigger pulls per '
        'second (0 = held -> weapon rounds per second); a pull fires once the barrel recovered '
        '(cap 1 / fire recovery time). Weapon damage modifier 0 = none. Misses, AI reloads and '
        'AI overheat are not counted.',
        'Knight mechanics NOT modelled: teleport/blink away when hurt (breaks the fight and lets the '
        'shield recharge after its 4 s delay), Watcher shielding / resurrection of Knights, the '
        'face-plate pop exposing the skull section, Knight Commanders / Battlewagons (tougher '
        'variants), alternative Knight weapons (incineration cannon, scattershot, binary rifle, '
        'light rifle) -- this table is the default storm_knight with its Suppressor (forerunner '
        'SMG npc).',
        'Elite mechanics NOT modelled: evasion rolls / cover breaks, plasma grenades, stimuli '
        'overrides (aggressive / berserk characters), the hlmt armor-lock and engineer-shield '
        'sections (Reach leftovers on storm_elite_ai).',
        'Every multiplier in these rows is 1.0: the Storm Rifle and the Suppressor are plasma_FAST '
        '(1.0 vs energy_shield_thin); only plasma_SLOW carries the Halo-style 1.6 vs shields / 0.4 '
        'vs hard_metal_thin in Halo 4. So the Storm Rifle is no shield-stripper on paper.',
        'Storm Rifle held trigger: overheats on the 12th bolt (0.09 heat per bolt, threshold 1), '
        'then (1 - 0.1 recovery threshold) / 0.3 per s = 3.0 s locked (the real heat is 1.08, '
        'so ~3.27 s). A feathering player (heat loss 0.55/s while not firing) avoids the lockout; '
        'the held-trigger number is a worst case, not how people use it.',
        'Headshots are excluded by method; Halo 4 jpt headshot damage multiplier reads 0 on all '
        'three player weapons (engine default applies to BR shots via its headshot flag).',
    ]
    path = tc.write(GAME, rows, notes)

    # ---- compact print
    print('HALO 4 LEGENDARY time to kill (body shots, full pools, no recharge)')
    print('player pool: body %g shield %g   enemy damage x%g' % (P_body, P_shield, dmg_s))
    for r in rows:
        extra = '' if r['direction'] == 'player->enemy' else '  paced %.2f s' % r['seconds_paced']
        print('%-14s -> %-14s %-22s %4s shots  %6.2f s%s   %s' % (
            r['attacker'], r['target'], r['weapon'], r['shots'], r['seconds'] or -1, extra,
            ' | '.join(f for f in r['flags'] if not f.startswith('AI accuracy') and 'hlmt:' not in f)[:160]))
    print(path)


if __name__ == '__main__':
    main()

r"""TIME TO KILL: a port against the weapons of its role, on the game's real enemies
(2026-10-05; first for the Halo 4 Focus Rifle, port_role_compare.py set focus_rifle).

Raw damage per second says little on its own: what an enemy takes depends on the damage
type against its shield and its body. Halo 4 (Reach's model) keeps it all in tags:

  * enemy VITALITY  -- the character's `vitality properties` (normal / legendary body and
    shield, shield recharge delay), walked up the parent characters; the globals'
    difficulty multipliers for enemy vitality and shields are all 1 in Halo 4
  * enemy MATERIALS -- the character's unit (biped) -> model: the shield's global material
    (new damage info / shield) and the body's (model materials 'body', else the indirect)
  * MULTIPLIER      -- globals 'damage table' [default]: damage GROUP (the damage
    effect's specific_damage, else its general_damage) x ARMOR (the material's specific
    armor, else its general armor up the material's parent chain). The first pair found
    wins; none = 1. Every lookup is printed (`--why`) so it can be checked.

SIMULATION: body shots from cold; shots at the weapon's interval; after the shots that
overheat it, a pause of its overheat recovery (heat cools ONLY while not firing --
confirmed by the user); shield damage that overflows carries into the body at the body
multiplier. A pause as long as the enemy's shield recharge delay is flagged '!'.
Headshots are NOT counted (the Beam Rifle and Sniper would do better on bare heads).

    python port_ttk.py focus_rifle [--why]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_field_audit as fa                                       # noqa: E402
import port_role_compare as rc                                      # noqa: E402

KIT = 'H4EK'
GLOBALS = r'globals\globals.globals'
C = r'objects\characters'
ENEMIES = [
    ('Grunt', C + r'\storm_grunt\ai\storm_grunt.character'),
    ('Grunt Ultra', C + r'\storm_grunt\ai\storm_grunt_ultra.character'),
    ('Jackal', C + r'\storm_jackal\ai\storm_jackal.character'),
    ('Elite', C + r'\storm_elite\ai\storm_elite.character'),
    ('Elite Officer', C + r'\storm_elite\ai\storm_elite_officer.character'),
    ('Elite Zealot', C + r'\storm_elite\ai\storm_elite_zealot.character'),
    ('Elite General', C + r'\storm_elite\ai\storm_elite_general.character'),
    ('Crawler', C + r'\storm_pawn\ai\storm_pawn.character'),
    ('Watcher', C + r'\storm_bishop\ai\storm_bishop.character'),
    ('Knight', C + r'\storm_knight\ai\storm_knight.character'),
    ('Knight Commander', C + r'\storm_knight\ai\storm_knight_commander.character'),
]
#: which weapons of a port_role_compare set are measured (Halo 4 ones)
WEAPONS = {'focus_rifle': ['H4 Focus (port)', 'H4 Beam Rifle', 'H4 Sentinel Beam', 'H4 Sniper (bridge)']}


def damage_tables():
    g = fa.flatten(KIT, GLOBALS)
    table, mats = {}, {}
    for k, (_t, v) in g.items():
        p = k.split('/')
        if p[:2] == ['damage table', '[0]'] and len(p) == 7 and p[2] == 'damage groups' \
                and p[4] == 'armor modifiers' and p[6] == 'damage multiplier':
            grp = g['/'.join(p[:4]) + '/name'][1]
            arm = g['/'.join(p[:6]) + '/name'][1]
            table.setdefault(grp, {})[arm] = float(v)
        if p[0] == 'materials' and len(p) == 3 and p[2] == 'name':
            base = '/'.join(p[:2])
            mats.setdefault(v, (g.get(base + '/parent name', ('', ''))[1],
                                g.get(base + '/general armor', ('', ''))[1],
                                g.get(base + '/specific armor', ('', ''))[1]))
    return table, mats


def armors(material, mats):
    """(specific armor, general armor) of a global material, up its parent chain."""
    spec = gen = ''
    seen = set()
    m = material
    while m and m not in seen and m in mats:
        seen.add(m)
        parent, g, s = mats[m]
        spec = spec or s
        gen = gen or g
        if gen:
            break
        m = parent
    return spec, gen


def multiplier(groups, material, table, mats):
    spec_a, gen_a = armors(material, mats)
    for grp in groups:
        for arm in (spec_a, gen_a):
            if grp and arm and arm in table.get(grp, {}):
                return table[grp][arm], '%s x %s' % (grp, arm)
    return 1.0, 'no entry for %s x %s/%s' % ('/'.join(x for x in groups if x), spec_a, gen_a)


def enemy(char_path):
    """vitality (normal/legendary, body/shield), recharge delay, shield + body material."""
    vit = unit = None
    path, seen = char_path, set()
    while path and path not in seen:
        seen.add(path)
        c = fa.flatten(KIT, path)
        if vit is None and int(c.get('vitality properties/#count', ('', '0'))[1] or 0):
            v = lambda n: float(c.get('vitality properties/[0]/' + n, ('', '0'))[1] or 0)
            vit = {'normal': (v('normal body vitality'), v('normal shield vitality')),
                   'legendary': (v('legendary body vitality'), v('legendary shield vitality')),
                   'delay': v('shield recharge delay time')}
        u = c.get('unit', ('', ''))[1].split(',')[0]
        if unit is None and u.strip():
            unit = u
        parent = c.get('parent character', ('', ''))[1].split(',')[0]
        path = parent + '.character' if parent else None
    b = fa.flatten(KIT, unit + '.biped')
    model = next(x for k, (_t, x) in b.items() if k.split('/')[-1] == 'model').split(',')[0]
    h = fa.flatten(KIT, model + '.model')
    shield = h.get('new damage info/[0]/shield/global shield material name', ('', ''))[1]
    body = ''
    for k, (_t, x) in h.items():
        if k.startswith('model materials/') and k.endswith('/material name') and x == 'body':
            body = h[k.rsplit('/', 1)[0] + '/global material name'][1]
            break
    body = body or h.get('new damage info/[0]/global indirect material name', ('', ''))[1]
    return vit, shield, body


def simulate(m, hp, sh, ms, mb, delay):
    """(seconds, shots, flag) to kill with body shots, or (None, shots, why)."""
    if hp <= 0:
        return 0.0, 0, ''
    d, interval = m['hit'], m['interval']
    burst = m.get('burst shots') or 10 ** 9
    pause = m.get('recover s', 0.0)
    t, shots, flag = 0.0, 0, ''
    for _ in range(5000):
        if sh > 0:
            if ms <= 0:
                return None, shots, 'shield immune'
            dmg = d * ms
            if dmg >= sh:
                over = (dmg - sh) / ms
                sh = 0.0
                hp -= over * mb
            else:
                sh -= dmg
        else:
            hp -= d * mb
        shots += 1
        if hp <= 1e-9:
            return t, shots, flag
        if shots % burst == 0:
            t += pause
            if pause >= delay and delay > 0:
                flag = '!'                    # the shield would start recharging
        t += interval
    return None, shots, 'no kill'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('set', choices=sorted(WEAPONS))
    ap.add_argument('--why', action='store_true', help='print every multiplier lookup')
    a = ap.parse_args()
    table, mats = damage_tables()
    S = rc.SETS[a.set]
    weapons = []
    for label, kit, w, stem in S['weapons']:
        if label in WEAPONS[a.set]:
            d = fa.flatten(kit, stem + '.damage_effect')
            groups = [d.get('specific_damage', ('', ''))[1], d.get('general_damage', ('', ''))[1]]
            weapons.append((label, rc.metrics(kit, w, stem), groups))
    width = 20
    print('TIME TO KILL, body shots, seconds (shots) -- normal / legendary')
    print('%-18s' % '' + ''.join('%-*s' % (width * 2, l[:width * 2 - 1]) for l, _m, _g in weapons))
    whys = []
    for name, char in ENEMIES:
        try:
            vit, shield_mat, body_mat = enemy(char)
        except Exception as e:
            print('%-18s could not read: %s' % (name, e))
            continue
        cells = []
        for label, m, groups in weapons:
            ms, why_s = multiplier(groups, shield_mat, table, mats)
            mb, why_b = multiplier(groups, body_mat, table, mats)
            whys.append('%-16s %-18s shield %-28s %.3g (%s)   body %-28s %.3g (%s)'
                        % (name, label, shield_mat, ms, why_s, body_mat, mb, why_b))
            out = []
            for diff in ('normal', 'legendary'):
                hp, sh = vit[diff]
                secs, shots, flag = simulate(m, hp, sh, ms, mb, vit['delay'])
                out.append('%s' % flag if secs is None else '%.2f(%d)%s' % (secs, shots, flag))
            cells.append(' / '.join(out))
        print('%-18s' % name + ''.join('%-*s' % (width * 2, c[:width * 2 - 1]) for c in cells))
    print('\n! = an overheat pause as long as the enemy\'s shield recharge delay')
    if a.why:
        print()
        for w in whys:
            print(w)


if __name__ == '__main__':
    main()

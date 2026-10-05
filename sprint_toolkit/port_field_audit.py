r"""Which tag fields of a port still carry the DONOR's value where the source weapon differs?

A port is built by cloning the target game's donor (Halo 3: the Assault Rifle's weapon,
projectile and damage effect) and then writing the fields the balance table covers --
only fields some enhancer CARD targets (balance_port.py). Every other field is the
donor's. Some of those are the source weapon's identity (the Halo 4 SAW differs from the
Halo 4 AR there) and should have been ported too. (User, 2026-10-05.)

The rule, per field, comparing the SOURCE pair (Halo 4 SAW vs Halo 4 AR):
  1  same in the source pair     -> not the weapon's identity; the target donor's value
                                    is the target game's convention. Keep. (counted only)
  2  differs, same field in the  -> a WEAPON difference: port it as the balance rows do,
     target, numeric                ported_source * donor_target / donor_source (the ratio
                                    carries the game scale and keeps the SAW's offset)
  3  differs, but does not carry -> an ENGINE / GAME difference to decide by hand: no
     over                           such field in the target, flags / enums / names, a
                                    zero on one side (no ratio), or a block of another size
Tag references and string ids are counted, not listed: the port's own tags, sounds and
text are steps 3, 8 and 10.

READ-ONLY. Values come from the kits' `export-tag-to-xml` (fields named; structs nest by
indentation only, so paths are built from it).

    python port_field_audit.py --game h3 [--json out.json] [--all]
"""
import argparse
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
STEAM = r'F:\SteamLibrary\steamapps\common'
B = '\\'
CLASS = {'weapon': 'weap', 'projectile': 'proj', 'damage_effect': 'jpt!'}

#: the source weapon and the donor it is measured against, per tag kind (Halo 4)
SOURCE = dict(kit='H4EK', tags={
    'weapon': (r'objects\weapons\rifle\storm_lmg\storm_lmg.weapon',
               r'objects\weapons\rifle\storm_assault_rifle\storm_assault_rifle.weapon'),
    'projectile': (r'objects\weapons\rifle\storm_lmg\projectiles\storm_lmg_bullet.projectile',
                   r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.projectile'),
    'damage_effect': (r'objects\weapons\rifle\storm_lmg\projectiles\storm_lmg_bullet.damage_effect',
                      r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.damage_effect')})
#: per target game: the kit, the port's tags and the donor's, the balance table
GAMES = {
    'h3': dict(kit='H3EK', game='Halo 3', table='balance_SAW_Halo4_to_Halo3.json', tags={
        'weapon': (r'objects\weapons\rifle\saw\saw.weapon',
                   r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
        'projectile': (r'objects\weapons\rifle\saw\projectiles\saw_bullet_h4_original_numbers.projectile',
                       r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
        'damage_effect': (r'objects\weapons\rifle\saw\damage_effects\saw_bullet_h4_original_numbers.damage_effect',
                          r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect')}),
}
SKIP_TYPES = ('pad', 'skip', 'explanation', 'struct', 'unknown', 'data')
REF_TYPES = ('tag reference', 'string id', 'old string id', 'long string', 'string')
NUMERIC = ('real', 'real fraction', 'angle', 'short integer', 'long integer', 'char integer',
           'real bounds', 'angle bounds', 'short integer bounds', 'real point 3d',
           'real vector 3d', 'real vector 2d', 'real point 2d', 'real euler angles 2d',
           'fraction bounds', 'real fraction bounds')


def flatten(kit, tag):
    """{path: (type, value)} of every leaf field; block sizes as '<block>/#count'."""
    ek = os.path.join(STEAM, kit)
    out = os.path.join(ek, 'temp', '_field_audit.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml', os.path.join(ek, 'tags', tag), out],
                   cwd=ek, capture_output=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise SystemExit('could not export %s from %s' % (tag, kit))
    stack, vals = [], {}                       # stack: (indent, name)
    for line in open(out, encoding='utf-8', errors='replace'):
        s = line.lstrip(' ')
        ind = len(line) - len(s)
        if s.startswith('</'):
            continue
        while stack and stack[-1][0] >= ind:
            stack.pop()
        here = '/'.join(n for _i, n in stack)
        # H3/ODST: value="<block type>,<count>"; H4: count="<count>"
        m = re.match(r'<block name="([^"]*)" (?:value="[^"]*,|count=")(\d+)"', s)
        if m:
            vals[(here + '/' if here else '') + m.group(1).lower() + '/#count'] = ('count', m.group(2))
            stack.append((ind, m.group(1).lower()))
            continue
        m = re.match(r'<element index="(\d+)"', s)
        if m:
            stack.append((ind, '[%s]' % m.group(1)))
            continue
        m = re.match(r'<field name="([^"]*)" value="([^"]*)" type="([^"]*)"', s)
        if not m:
            continue
        name, val, typ = m.group(1).lower(), m.group(2), m.group(3)
        if typ == 'struct':
            stack.append((ind, name))
            continue
        if typ in SKIP_TYPES or not name:
            continue
        key = (here + '/' if here else '') + name
        while key in vals:                    # same leaf twice in one struct (rare)
            key += "'"
        vals[key] = (typ, val)
    return vals


def nums(v):
    try:
        return [float(x) for x in v.split(',')]
    except ValueError:
        return None


def covered_fields(table):
    """{class: set(lower field names)} the balance table already writes."""
    p = os.path.join(HERE, table)
    out = {}
    if os.path.exists(p):
        for r in json.load(open(p, encoding='utf-8'))['rows']:
            for f in (r.get('dst_field'), r.get('field')):
                if f and r.get('dst_class'):
                    out.setdefault(r['dst_class'], set()).add(f.lower())
    return out


def leaf(path):
    return path.rsplit('/', 1)[-1].rstrip("'")


def match(path, target):
    """The target path for a source path: exact, else a UNIQUE same-leaf field in the
    same top-level block / struct (schemas move fields between games)."""
    if path in target:
        return path, 'exact'
    top, lf = path.split('/', 1)[0], leaf(path)
    hits = [k for k in target if leaf(k) == lf and k.split('/', 1)[0] == top]
    if len(hits) == 1:
        return hits[0], 'by name'
    hits = [k for k in target if leaf(k) == lf]
    if len(hits) == 1:
        return hits[0], 'by name (moved)'
    return None, 'ambiguous' if hits else 'none'


def audit(game, show_all=False):
    G = GAMES[game]
    covered = covered_fields(G['table'])
    report = {'game': G['game'], 'kinds': {}}
    for kind in ('weapon', 'projectile', 'damage_effect'):
        s_port, s_donor = (flatten(SOURCE['kit'], t) for t in SOURCE['tags'][kind])
        t_port, t_donor = (flatten(G['kit'], t) for t in G['tags'][kind])
        cov = covered.get(CLASS[kind], set())
        rows = {'same': 0, 'refs': 0, 'port': [], 'decide': [], 'covered': []}
        for path, (typ, sv) in s_port.items():
            dv = s_donor.get(path, (None, None))[1]
            if dv == sv:
                rows['same'] += 1
                continue
            if typ in REF_TYPES:
                rows['refs'] += 1
                continue
            tp, how = match(path, t_donor)
            row = {'field': path, 'type': typ, 'h4_port': sv, 'h4_donor': dv, 'match': how}
            if tp is None:
                rows['decide'].append(dict(row, why='no such field in %s' % G['game']))
                continue
            ttyp, tv = t_donor[tp]
            row.update(target_field=tp, target_donor=tv, target_port=t_port.get(tp, (None, None))[1])
            if leaf(tp) in cov or leaf(path) in cov:
                rows['covered'].append(row)
                continue
            a, b, c = nums(sv), nums(dv) if dv is not None else None, nums(tv)
            if typ == 'count' or ttyp == 'count':
                rows['decide'].append(dict(row, why='block size differs'))
            elif typ not in NUMERIC or ttyp not in NUMERIC or None in (a, b, c) \
                    or not (len(a) == len(b) == len(c)):
                rows['decide'].append(dict(row, why='%s (not a number to scale)' % typ))
            else:
                sug, zero = [], False
                for x, y, z in zip(a, b, c):
                    if x == y:
                        sug.append(z)                   # this element is the donor's
                    elif y == 0 or z == 0:
                        sug.append(x)
                        zero = True
                    else:
                        sug.append(x * z / y)
                row['suggested'] = ','.join('%g' % v for v in sug)
                if zero:
                    rows['decide'].append(dict(row, why='a zero on one side: no ratio, '
                                               'suggested = the source value'))
                else:
                    rows['port'].append(row)
        report['kinds'][kind] = rows
    return report


def show(report, show_all=False):
    print('PORT FIELD AUDIT -- %s (source Halo 4: SAW vs Assault Rifle)' % report['game'])
    for kind, r in report['kinds'].items():
        print('\n== %s: %d same in the source pair (kept), %d reference/name differences '
              '(steps 3/8/10), %d already ported by the balance table'
              % (kind, r['same'], r['refs'], len(r['covered'])))
        print('-- 2. WEAPON differences to port (%d)' % len(r['port']))
        for x in r['port']:
            flag = '' if x['target_port'] == x['target_donor'] else '   (port already %s)' % x['target_port']
            print('   %-58s H4 SAW %-16s AR %-16s | H3 AR %-16s -> %s%s%s' % (
                x['target_field'][-58:], x['h4_port'][:16], (x['h4_donor'] or '-')[:16],
                x['target_donor'][:16], x['suggested'], '' if x['match'] == 'exact' else '  [%s]' % x['match'], flag))
        print('-- 3. decide by hand (%d)' % len(r['decide']))
        for x in r['decide']:
            print('   %-58s H4 SAW %-16s AR %-16s | H3 AR %-16s  %s' % (
                (x.get('target_field') or x['field'])[-58:], x['h4_port'][:16], (x['h4_donor'] or '-')[:16],
                (x.get('target_donor') or '-')[:16], x['why']))
        if show_all:
            print('-- covered by the balance table (%d)' % len(r['covered']))
            for x in r['covered']:
                print('   %-58s H4 SAW %-16s -> port %s' % (x['target_field'][-58:], x['h4_port'][:16], x['target_port']))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', choices=sorted(GAMES), default='h3')
    ap.add_argument('--json')
    ap.add_argument('--all', action='store_true', help='also list the fields the balance table covers')
    a = ap.parse_args()
    rep = audit(a.game)
    show(rep, a.all)
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), indent=1)
        print('\nwrote %s' % a.json)


if __name__ == '__main__':
    main()

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

    python port_field_audit.py --game h3|odst|reach|h2|h1 [--json out.json] [--all]
"""
import argparse
import json
import os
import re
import subprocess
import sys

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
    'h3': dict(kit='H3EK', game='Halo 3', tags={
        'weapon': (r'objects\weapons\rifle\saw\saw.weapon',
                   r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
        'projectile': (r'objects\weapons\rifle\saw\projectiles\saw_bullet_h4_original_numbers.projectile',
                       r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
        'damage_effect': (r'objects\weapons\rifle\saw\damage_effects\saw_bullet_h4_original_numbers.damage_effect',
                          r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect')}),
    'odst': dict(kit='H3ODSTEK', game='Halo 3: ODST', tags={
        'weapon': (r'objects\weapons\rifle\saw\saw.weapon',
                   r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
        'projectile': (r'objects\weapons\rifle\saw\projectiles\saw_bullet_h4_original_numbers.projectile',
                       r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
        'damage_effect': (r'objects\weapons\rifle\saw\damage_effects\saw_bullet_h4_original_numbers.damage_effect',
                          r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect')}),
    # Reach keeps the damage effect BESIDE the projectile
    'reach': dict(kit='HREK', game='Halo Reach', tags={
        'weapon': (r'objects\weapons\rifle\saw\saw.weapon',
                   r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
        'projectile': (r'objects\weapons\rifle\saw\projectiles\saw_bullet_h4_original_numbers.projectile',
                       r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
        'damage_effect': (r'objects\weapons\rifle\saw\projectiles\saw_bullet_h4_original_numbers.damage_effect',
                          r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.damage_effect')}),
    # Halo 2 has no Assault Rifle: the donor is the SMG, and the scale walks through
    # Halo 3 as balance_port.py's does -- H4 AR > H3 AR, then H3 SMG > H2 SMG
    'h2': dict(kit='H2EK', game='Halo 2', tags={
        'weapon': (r'objects\weapons\rifle\saw\saw.weapon', r'objects\weapons\rifle\smg\smg.weapon'),
        'projectile': (r'objects\weapons\rifle\saw\projectiles\saw_bullet.projectile',
                       r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile'),
        'damage_effect': (r'objects\weapons\rifle\saw\damage_effects\saw_bullet.damage_effect',
                          r'objects\weapons\rifle\smg\damage_effects\smg_bullet.damage_effect')},
        hops=[('H4EK', {'weapon': r'objects\weapons\rifle\storm_assault_rifle\storm_assault_rifle.weapon',
                        'projectile': r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.projectile',
                        'damage_effect': r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.damage_effect'},
               'H3EK', {'weapon': r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon',
                        'projectile': r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile',
                        'damage_effect': r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect'}),
              ('H3EK', {'weapon': r'objects\weapons\rifle\smg\smg.weapon',
                        'projectile': r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile',
                        'damage_effect': r'objects\weapons\rifle\smg\damage_effects\smg_bullet.damage_effect'},
               'H2EK', {'weapon': r'objects\weapons\rifle\smg\smg.weapon',
                        'projectile': r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile',
                        'damage_effect': r'objects\weapons\rifle\smg\damage_effects\smg_bullet.damage_effect'})]),
    # Halo 1: the Assault Rifle in both games, one hop; read through Reclaimer
    'h1': dict(kit='HCEEK', game='Halo 1', tags={
        'weapon': (r'weapons\saw\saw.weapon', r'weapons\assault rifle\assault rifle.weapon'),
        'projectile': (r'weapons\saw\bullet.projectile', r'weapons\assault rifle\bullet.projectile'),
        'damage_effect': (r'weapons\saw\bullet.damage_effect', r'weapons\assault rifle\bullet.damage_effect')}),
}
KIT_GAME = {'H4EK': 'Halo 4', 'H3EK': 'Halo 3', 'H3ODSTEK': 'Halo 3: ODST', 'HREK': 'Halo Reach',
            'H2EK': 'Halo 2', 'HCEEK': 'Halo 1'}
SKIP_TYPES = ('pad', 'skip', 'explanation', 'struct', 'unknown', 'data')
REF_TYPES = ('tag reference', 'string id', 'old string id', 'long string', 'string')
NUMERIC = ('real', 'real fraction', 'angle', 'short integer', 'long integer', 'char integer',
           'real bounds', 'angle bounds', 'short integer bounds', 'real point 3d',
           'real vector 3d', 'real vector 2d', 'real point 2d', 'real euler angles 2d',
           'fraction bounds', 'real fraction bounds')


_CACHE = {}


def flatten(kit, tag):
    """{path: (type, value)} of every leaf field; block sizes as '<block>/#count'. One
    reader per kit family: H3EK / H3ODSTEK / HREK / H4EK export XML (two dialects),
    H2EK exports real XML, HCEEK has no export at all (Reclaimer)."""
    key = (kit, tag)
    if key not in _CACHE:
        _CACHE[key] = (flatten_h1(tag) if kit == 'HCEEK' else
                       flatten_h2(tag) if kit == 'H2EK' else flatten_xml(kit, tag))
    return _CACHE[key]


def flatten_h2(tag):
    """Halo 2's export is well-formed XML: <block name> / <element index> / <field name
    type>value</field> / <tag_reference name type>path</tag_reference>; no structs."""
    import xml.etree.ElementTree as ET
    ek = os.path.join(STEAM, 'H2EK')
    out = os.path.join(ek, 'temp', '_field_audit.xml')        # ABSOLUTE both: H2EK's rule
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml', os.path.join(ek, 'tags', tag), out],
                   cwd=ek, capture_output=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise SystemExit('could not export %s from H2EK' % tag)
    vals = {}

    def walk(node, path):
        for c in node:
            name = (c.get('name') or '').lower()
            p = (path + '/' if path else '') + name
            if c.tag == 'block':
                vals[p + '/#count'] = ('count', str(len([e for e in c if e.tag == 'element'])))
                for e in c:
                    if e.tag == 'element':
                        walk(e, '%s/[%s]' % (p, e.get('index')))
            elif c.tag == 'tag_reference':
                vals[p] = ('tag reference', (c.text or '').strip())
            elif c.tag == 'field':
                typ = c.get('type') or ''
                if typ in SKIP_TYPES or not name or name.startswith('runtime'):
                    continue
                v = ' '.join((c.text or '').split())
                if 'enum' in typ:
                    v = re.sub(r'^-?\d+,', '', v)            # '0,small' -> 'small'
                while p in vals:
                    p += "'"
                vals[p] = (typ, v.replace(', ', ','))
            elif len(c):
                walk(c, p)
    walk(ET.parse(out).getroot(), '')
    return vals


def flatten_h1(tag):
    """Halo 1 through Reclaimer (pylibs): snake_case names -> spaces, angles to DEGREES
    (the field's UNIT_SCALE; the other kits' exports print degrees), the top-level
    *_attrs structs flattened away so paths look like the other games'."""
    import importlib
    sys.path.insert(0, os.path.join(HERE, 'pylibs'))
    import env  # noqa: F401
    ext = tag.rsplit('.', 1)[-1]
    mod = {'weapon': 'weap', 'projectile': 'proj', 'damage_effect': 'jpt_'}[ext]
    d = getattr(importlib.import_module('reclaimer.hek.defs.' + mod), mod + '_def')
    t = d.build(filepath=os.path.join(STEAM, 'HCEEK', 'tags', tag))
    vals = {}

    def walk(node, path, top=False):
        for i in range(len(node)):
            if i not in node.desc:
                continue
            dsc, c = node.desc[i], node[i]
            name = dsc['NAME'].replace('_', ' ').lower().strip()
            tn = dsc['TYPE'].name
            if name.startswith('pad') or name.startswith('runtime'):
                continue
            p = path if (top and name.endswith(' attrs')) else (path + '/' if path else '') + name
            if tn in ('TagRef', 'TagIndexRef'):
                vals[p] = ('tag reference', getattr(c, 'filepath', ''))
            elif tn == 'Reflexive':
                vals[p + '/#count'] = ('count', str(len(c.STEPTREE)))
                for k, e in enumerate(c.STEPTREE):
                    walk(e, '%s/[%d]' % (p, k))
            elif hasattr(c, 'enum_name'):
                vals[p] = ('enum', c.enum_name)
            elif tn.startswith('Bool'):
                vals[p] = ('flags', str(c.data))
            elif hasattr(c, 'desc'):
                kids = [c[k] for k in range(len(c))]
                if kids and all(isinstance(k, (int, float)) for k in kids) and len(kids) <= 3:
                    sc = dsc.get('UNIT_SCALE')
                    sc = sc if isinstance(sc, (int, float)) else 1
                    vals[p] = ('real bounds', ','.join('%g' % (k * sc) for k in kids))
                else:
                    walk(c, p, top and name.endswith(' attrs'))
            elif isinstance(c, (int, float)):
                sc = dsc.get('UNIT_SCALE')
                v = c * sc if isinstance(sc, (int, float)) else c
                vals[p] = ('real' if isinstance(c, float) else 'short integer', '%g' % v)
            elif isinstance(c, str):
                vals[p] = ('string', c)
    walk(t.data.tagdata, '', top=True)
    return vals


def flatten_xml(kit, tag):
    ek = os.path.join(STEAM, kit)
    out = os.path.join(ek, 'temp', '_field_audit.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml', os.path.join(ek, 'tags', tag), out],
                   cwd=ek, capture_output=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise SystemExit('could not export %s from %s' % (tag, kit))
    stack, vals = [], {}                       # stack: (indent, name)
    reach_block = {}                           # Reach: indent -> the block field just seen
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
            # Reach writes a block as a self-closing FIELD and its elements as SIBLINGS at
            # the same indent; Halo 3 / Halo 4 nest them inside <block>
            owner = reach_block.get(ind)
            stack.append((ind, '%s/[%s]' % (owner, m.group(1)) if owner else '[%s]' % m.group(1)))
            continue
        m = re.match(r'<field name="([^"]*)" value="([^"]*)" type="([^"]*)"', s)
        if not m:
            continue
        name, val, typ = m.group(1).lower(), m.group(2), m.group(3)
        if typ == 'struct':
            stack.append((ind, name))
            continue
        if typ == 'block':                        # Reach
            vals[(here + '/' if here else '') + name + '/#count'] = ('count', val)
            reach_block[ind] = name
            continue
        if typ in SKIP_TYPES or not name or name.startswith('runtime'):
            continue                          # runtime fields: the compiler fills them
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


def covered_fields(game, weapon='SAW'):
    """{class: {lower field name: catalog value}} the patcher's balance writes -- read from
    weapon_ports_catalog.json, NOT a balance table: the catalog adds derived and measured
    rows (Halo 3: Rounds Total Maximum = inventory + loaded) a table does not have."""
    cat = json.load(open(os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json'),
                         encoding='utf-8')).get(game) or []
    out = {}
    for e in (cat if isinstance(cat, list) else [cat]):
        if e.get('weapon') == weapon:
            for r in e.get('balance') or ():
                out.setdefault(r['class'], {})[r['field'].lower()] = r.get('value')
    return out


def leaf(path):
    """The field's own name; a block count is named by its BLOCK ('attachments/#count'),
    or every count in the tag would look like the same field."""
    parts = path.rstrip("'").split('/')
    if parts[-1] == '#count' and len(parts) > 1:
        return parts[-2] + '/#count'
    return parts[-1].rstrip("'")


def _segments(path):
    return set(s for s in path.split('/') if s and not s.startswith('['))


#: per target game: source path -> target path where names alone cannot decide. Halo 2's
#: export prints no struct names, so a barrel holds 'acceleration time' / 'deceleration
#: time' FOUR times; the second pair is the firing error (it precedes 'damage error')
#: Halo 1 names them 'error acceleration/deceleration time' inside the trigger's firing
#: struct -- its plain 'deceleration time' there is the RATE OF FIRE spin-down
ALIASES = {'H2EK': {'barrels/[0]/firing error/acceleration time': "barrels/[0]/acceleration time'",
                    'barrels/[0]/firing error/deceleration time': "barrels/[0]/deceleration time'"},
           'HCEEK': {'barrels/[0]/firing error/acceleration time': 'triggers/[0]/firing/error acceleration time',
                     'barrels/[0]/firing error/deceleration time': 'triggers/[0]/firing/error deceleration time'}}


def match(path, target, kit=None):
    """The target path for a source path: an alias, exact, else the same-leaf field whose
    path shares the MOST named segments, if that best one is unique."""
    alias = ALIASES.get(kit, {}).get(path)
    if alias and alias in target:
        return alias, 'alias'
    if path in target:
        return path, 'exact'
    lf, segs = leaf(path), _segments(path)
    hits = [k for k in target if leaf(k) == lf]
    if not hits:
        return None, 'none'
    if len(hits) == 1:
        return hits[0], 'by name'
    score = {k: len(segs & _segments(k)) for k in hits}
    best = max(score.values())
    top = [k for k in hits if score[k] == best]
    if len(top) == 1:
        return top[0], 'by name (closest path)'
    return None, 'ambiguous'


def audit(game, show_all=False):
    G = GAMES[game]
    covered = covered_fields(G['game'])
    report = {'game': G['game'], 'kinds': {}}
    hops = G.get('hops') or [(SOURCE['kit'], {k: v[1] for k, v in SOURCE['tags'].items()},
                              G['kit'], {k: v[1] for k, v in G['tags'].items()})]
    for kind in ('weapon', 'projectile', 'damage_effect'):
        s_port, s_donor = (flatten(SOURCE['kit'], t) for t in SOURCE['tags'][kind])
        t_port, t_donor = (flatten(G['kit'], t) for t in G['tags'][kind])
        cov = covered.get(CLASS[kind], {})
        rows = {'same': 0, 'refs': 0, 'port': [], 'done': [], 'decide': [], 'covered': [],
                'clone': [], 'extra': []}
        seen = set()                           # target fields some source field spoke to
        for path, (typ, sv) in s_port.items():
            dv = s_donor.get(path, (None, None))[1]
            tp0, _h0 = match(path, t_donor, G['kit'])
            if tp0:
                seen.add(tp0)
            if dv == sv:
                rows['same'] += 1
                # the source pair agrees, so the port should read like the target's
                # yardstick donor -- unless it was CLONED from another weapon (Halo 2:
                # the GPMG + the Warthog turret's bullet) and still holds that one's value
                if typ not in REF_TYPES and typ != 'count':
                    tp = tp0
                    if (tp and leaf(tp) not in cov and tp in t_port
                            and t_port[tp][1] != t_donor[tp][1] and t_port[tp][0] not in REF_TYPES):
                        rows['clone'].append({'field': path, 'target_field': tp, 'h4': sv,
                                              'target_donor': t_donor[tp][1],
                                              'target_port': t_port[tp][1]})
                continue
            if typ in REF_TYPES:
                rows['refs'] += 1
                continue
            # walk the donor chain: each hop is the SAME weapon in two games (Halo 2: the
            # AR into Halo 3, then the SMG into Halo 2), matched by field name per hop
            cur, how, pairs, missing = path, 'exact', [], None
            for k, (fk, ftags, tk, ttags) in enumerate(hops):
                fmap = s_donor if k == 0 else flatten(fk, ftags[kind])
                if k:
                    cur, h = match(cur, fmap, fk)
                    if cur is None:
                        missing = fk
                        break
                tmap = flatten(tk, ttags[kind])
                tp, h = match(cur, tmap, tk)
                if tp is None:
                    missing = tk
                    break
                how = h if h != 'exact' else how
                pairs.append((fmap.get(cur, (None, None))[1], tmap[tp][1], tmap[tp][0]))
                cur = tp
            row = {'field': path, 'type': typ, 'h4_port': sv, 'h4_donor': dv, 'match': how}
            if missing:
                rows['decide'].append(dict(row, why='no such field in %s' % KIT_GAME.get(missing, missing)))
                continue
            tp = cur
            ttyp, tv = t_donor[tp]
            row.update(target_field=tp, target_donor=tv, target_port=t_port.get(tp, (None, None))[1])
            if leaf(tp) in cov or leaf(path) in cov:
                rows['covered'].append(dict(row, balanced=cov.get(leaf(tp), cov.get(leaf(path)))))
                continue
            a = nums(sv)
            hp = [(nums(f) if f is not None else None, nums(t)) for f, t, _ty in pairs]
            if len(pairs) > 1:
                row['bridge'] = ' > '.join('%s->%s' % (f, t) for f, t, _ty in pairs)
            if typ == 'count' or ttyp == 'count':
                rows['decide'].append(dict(row, why='block size differs'))
            elif typ not in NUMERIC or ttyp not in NUMERIC or a is None or any(
                    f is None or t is None or len(f) != len(a) or len(t) != len(a) for f, t in hp):
                rows['decide'].append(dict(row, why='%s (not a number to scale)' % typ))
            else:
                sug, zero = [], False
                for e, x in enumerate(a):
                    if x == hp[0][0][e]:
                        sug.append(hp[-1][1][e])        # this element is the donor's
                    elif any(f[e] == 0 or t[e] == 0 for f, t in hp):
                        sug.append(x)
                        zero = True
                    else:
                        r = x
                        for f, t in hp:
                            r *= t[e] / f[e]
                        sug.append(r)
                row['suggested'] = ','.join('%g' % v for v in sug)
                if zero:
                    rows['decide'].append(dict(row, why='a zero on one side: no ratio, '
                                               'suggested = the source value'))
                else:
                    have = nums(row['target_port'] or '')
                    done = have is not None and len(have) == len(sug) and all(
                        abs(h - g) < 1e-4 for h, g in zip(have, sug))
                    rows['done' if done else 'port'].append(row)
        # 5. what NO source field speaks to: the port differs from the yardstick donor in a
        # field Halo 4 has no counterpart for (Halo 2's bullet is the turret's: it never
        # ricochets or overpenetrates, where the SMG's does)
        for tp, (ttyp, tv) in t_port.items():
            if tp in seen or ttyp in REF_TYPES or leaf(tp) in cov or tp not in t_donor:
                continue
            if t_donor[tp][1] != tv:
                rows['extra'].append({'target_field': tp, 'target_donor': t_donor[tp][1],
                                      'target_port': tv})
        for tp in t_donor:                    # blocks/fields the port lacks entirely
            if tp not in t_port and tp not in seen and t_donor[tp][0] not in REF_TYPES:
                rows['extra'].append({'target_field': tp, 'target_donor': t_donor[tp][1],
                                      'target_port': '(missing)'})
        report['kinds'][kind] = rows
    return report


def show(report, show_all=False):
    print('PORT FIELD AUDIT -- %s (source Halo 4: SAW vs Assault Rifle)' % report['game'])
    tgt = 'the target donor'
    for kind, r in report['kinds'].items():
        print('\n== %s: %d same in the source pair (kept), %d reference/name differences '
              '(steps 3/8/10), %d already ported by the balance table'
              % (kind, r['same'], r['refs'], len(r['covered'])))
        print('-- 2. WEAPON differences to port (%d; %d already written: %s)' % (
            len(r['port']), len(r['done']), ', '.join(leaf(x['target_field']) for x in r['done']) or '-'))
        for x in r['port']:
            flag = '' if x['target_port'] == x['target_donor'] else '   (port already %s)' % x['target_port']
            print('   %-58s H4 SAW %-16s AR %-16s | tgt AR %-16s -> %s%s%s' % (
                x['target_field'][-58:], x['h4_port'][:16], (x['h4_donor'] or '-')[:16],
                x['target_donor'][:16], x['suggested'], '' if x['match'] == 'exact' else '  [%s]' % x['match'], flag))
        if r.get('clone'):
            print('-- 4. source pair AGREES, but the port holds another value than %s -- its '
                  "clone donor's, or a deliberate setting (%d)" % (tgt, len(r['clone'])))
            for x in r['clone']:
                print('   %-58s H4 both %-12s | %s %-16s port %s' % (
                    x['target_field'][-58:], x['h4'][:12], tgt, x['target_donor'][:16], x['target_port'][:24]))
        if r.get('extra'):
            print('-- 5. no Halo 4 counterpart, and the port differs from %s (%d)'
                  % (tgt, len(r['extra'])))
            for x in r['extra']:
                print('   %-58s %s %-24s port %s' % (x['target_field'][-58:], tgt,
                                                    x['target_donor'][:24], x['target_port'][:24]))
        print('-- 3. decide by hand (%d)' % len(r['decide']))
        for x in r['decide']:
            print('   %-58s H4 SAW %-16s AR %-16s | tgt AR %-16s  %s' % (
                (x.get('target_field') or x['field'])[-58:], x['h4_port'][:16], (x['h4_donor'] or '-')[:16],
                (x.get('target_donor') or '-')[:16], x['why']))
        if show_all:
            print('-- covered by the balance table (%d)' % len(r['covered']))
            for x in r['covered']:
                print('   %-58s H4 SAW %-16s tags %-16s balanced %s' % (
                    x['target_field'][-58:], x['h4_port'][:16], x['target_port'], x.get('balanced')))


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

r"""Step 4a's Halo 3 side: the values the ratio rule compares, for any H3EK weapons, side by side.

Exports each weapon, its trigger projectile and the projectile's impact damage effect with
`tool export-tag-to-xml` (cached in out\h3_export), plus the first-person animation lengths
of its FP graph, and prints one row per value:

  rate (rounds/s bounds, rate ramp, fire recovery), magazine (loaded / initial / maximum /
  reload time / rounds reloaded), spread (minimum error, error angle bounds, bloom ramp,
  angle change per shot = barrel climb), heat / age per round, aim assist, melee damage
  tags, projectile velocity / range / gravity, damage (bounds, damage group, acceleration),
  and FP ready / put-away / reload / melee frames (30 fps).

Written for the SMG pilot (2026-10-07, PORTING.md); the numbers in ports_h1/smg.py's
yardstick came from it. The Halo 1 side is h1_role_compare.py.

    python h3_weapon_values.py rifle\smg\smg rifle\assault_rifle\assault_rifle pistol\magnum\magnum
    (paths under objects\weapons, no extension; --json out.json writes the table)
"""
import argparse
import io
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
H3EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
CACHE = os.path.join(HERE, 'out', 'h3_export')
W = 'objects\\weapons\\'
FP = 'objects\\characters\\masterchief\\fp\\weapons\\'


def export(rel):
    """XML text of a kit tag (rel with extension), cached by mtime; None if absent."""
    src = os.path.join(H3EK, 'tags', rel)
    if not os.path.exists(src):
        return None
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, os.path.basename(rel) + '.xml')
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run([os.path.join(H3EK, 'tool.exe'), 'export-tag-to-xml', src, out],
                       cwd=H3EK, capture_output=True, timeout=600)
    return io.open(out, encoding='utf-8', errors='replace').read() if os.path.exists(out) else None


def field(s, name, after=None):
    if s is None:
        return None
    if after and after in s:
        s = s[s.find(after):]
    m = re.search(r'<field name="%s" value="([^"]*)"' % re.escape(name), s)
    return m.group(1) if m else None


def ref(s, name):
    v = field(s, name)
    return v.split(',')[0] if v and ',' in v and v.split(',')[0] else None


def values(weapon, graph=None):
    """The table column of one weapon; `graph` = its FP graph under masterchief\\fp\\weapons
    (Halo 3 weapons do not name it), for the FP frame rows."""
    s = export(W + weapon + '.weapon')
    if s is None:
        raise SystemExit('no %s%s.weapon in H3EK' % (W, weapon))
    bar = s[s.find('<block name="barrels"'):]
    mag = s[s.find('<block name="magazines"'):]
    proj = ref(bar, 'projectile')
    ps = export(proj + '.projectile') if proj else None
    dmg = ref(ps, 'impact damage')
    ds = export(dmg + '.damage_effect') if dmg else None
    after = 'distribution function'          # the single-wield error, after the dual set
    v = {
        'rounds per second': field(bar, 'rounds per second'),
        'rate ramp (acc, dec)': '%s, %s' % (field(bar, 'acceleration time'), field(bar, 'deceleration time')),
        'fire recovery time': field(bar, 'fire recovery time'),
        'magazine loaded': field(mag, 'rounds loaded maximum'),
        'ammo initial': field(mag, 'rounds total initial'),
        'ammo maximum': field(mag, 'rounds total maximum'),
        'reload time (tag)': field(mag, 'reload time'),
        'rounds reloaded': field(mag, 'rounds reloaded'),
        'minimum error': field(bar, 'minimum error', after),
        'error angle': field(bar, 'error angle', after),
        'bloom ramp (acc, dec)': '%s, %s' % (field(bar, 'acceleration time', 'firing error'),
                                            field(bar, 'deceleration time', 'firing error')),
        'barrel climb / shot': field(bar, 'angle change per shot'),
        'heat per round': field(bar, 'heat generated per round'),
        'age per round': field(bar, 'age generated per round'),
        'autoaim angle / range': '%s / %s' % (field(s, 'autoaim angle'), field(s, 'autoaim range')),
        'magnetism angle / range': '%s / %s' % (field(s, 'magnetism angle'), field(s, 'magnetism range')),
        'melee 1st / 3rd hit': '%s / %s' % ((ref(s, '1st hit melee damage') or '-').rsplit('\\', 1)[-1],
                                           (ref(s, '3rd hit melee damage') or '-').rsplit('\\', 1)[-1]),
        'velocity (init, final)': '%s, %s' % (field(ps, 'initial velocity'), field(ps, 'final velocity')),
        'maximum range': field(ps, 'maximum range'),
        'air gravity scale': field(ps, 'air gravity scale'),
        'damage (lower; upper)': '%s; %s' % (field(ds, 'damage lower bound'), field(ds, 'damage upper bound')),
        'damage group': field(ds, 'general_damage'),
        'instantaneous accel': field(ds, 'instantaneous acceleration'),
    }
    if graph:
        gs = export(FP + graph + '.model_animation_graph')
        fr = {}
        for m in re.finditer(r'<field name="name" value="(first_person:[^"]*)" type="string id"/>'
                             r'(.*?)<field name="frame count" value="(\d+)"', gs or '', re.S):
            if ':dual:' not in m.group(1):
                fr.setdefault(m.group(1).split(':')[1], int(m.group(3)))
        for k in ('ready', 'put_away', 'reload_empty', 'reload_full', 'melee_strike_1', 'fire_1'):
            if k in fr:
                v['FP %s frames' % k] = str(fr[k])
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('weapons', nargs='+', help=r'under objects\weapons, e.g. rifle\smg\smg; '
                    r'add =<fp graph under masterchief\fp\weapons> for FP frames, e.g. '
                    r'rifle\smg\smg=rifle\fp_smg\fp_smg')
    ap.add_argument('--json')
    a = ap.parse_args()
    cols = []
    for w in a.weapons:
        name, _, graph = w.partition('=')
        cols.append((name.rsplit('\\', 1)[-1], values(name, graph or None)))
    keys = list(cols[0][1])
    for _n, v in cols[1:]:
        keys += [k for k in v if k not in keys]
    print('%-26s' % '' + ''.join('%-24s' % n[:23] for n, _v in cols))
    for k in keys:
        print('%-26s' % k + ''.join('%-24s' % str(v.get(k, '-'))[:23] for _n, v in cols))
    if a.json:
        json.dump({n: v for n, v in cols}, open(a.json, 'w', encoding='utf-8'), indent=1)
        print('wrote', a.json)


if __name__ == '__main__':
    main()

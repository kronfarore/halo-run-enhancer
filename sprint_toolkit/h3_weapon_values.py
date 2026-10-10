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

HALO REACH (`--kit reach`, the DMR pilot, 2026-10-10): the same rows from HREK. Reach's
export writes a tag reference as its BASENAME only (`dmr_bullet`), so a reference is found
by name + extension, nearest the referencing tag's folder first; FP graphs sit under
spartans\fp\weapons; the melee is ONE `melee damage` field (shown as 1st / 3rd); a Reach
magazine has no reload time (the animation sets it).

    python h3_weapon_values.py --kit reach rifle\dmr\dmr=rifle\fp_dmr\fp_dmr pistol\magnum\magnum
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
#: per kit: (kit root, export cache, FP graph folder); 'h3' is the original behaviour
KITS = {'h3': (H3EK, CACHE, FP),
        'reach': (os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HREK'),
                  os.path.join(HERE, 'out', 'reach_export'),
                  'objects\\characters\\spartans\\fp\\weapons\\')}
KIT = 'h3'


def use_kit(kit):
    """Point export / ref / values at another kit (module globals)."""
    global H3EK, CACHE, FP, KIT
    H3EK, CACHE, FP = KITS[kit]
    KIT = kit


def export(rel):
    """XML text of a kit tag (rel with extension), cached by mtime; None if absent."""
    src = os.path.join(H3EK, 'tags', rel)
    if not os.path.exists(src):
        return None
    os.makedirs(CACHE, exist_ok=True)
    # keyed by the kit PATH, not the basename: generic names collide (the Spike Rifle's
    # fx\projectile.effect read the Carbine's cached one, 2026-10-08)
    out = os.path.join(CACHE, rel.replace('\\', '~').replace('/', '~') + '.xml')
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


def ref(s, name, ext=None, near=None):
    v = field(s, name)
    if KIT != 'h3':
        return find_tag(v, ext, near) if v else None
    return v.split(',')[0] if v and ',' in v and v.split(',')[0] else None


_INDEX = {}


def find_tag(base, ext, near=None):
    """Reach: a basename reference -> the kit-relative path (no extension) of <base>.<ext>,
    the one sharing the longest folder prefix with `near` (the referencing tag) first."""
    if '\\' in base:
        return base
    root = os.path.join(H3EK, 'tags')
    if not _INDEX:
        for d, _ds, fs in os.walk(root):
            for f in fs:
                b, e = os.path.splitext(f)
                _INDEX.setdefault((b.lower(), e[1:].lower()), []).append(
                    os.path.relpath(os.path.join(d, b), root))
    hits = _INDEX.get((base.lower(), (ext or '').lower()), [])
    if not hits:
        return None
    nb = (near or '').lower().split('\\')[:-1]

    def shared(h):
        a, n = h.lower().split('\\')[:-1], 0
        while n < min(len(a), len(nb)) and a[n] == nb[n]:
            n += 1
        return -n
    return sorted(hits, key=shared)[0]


def values(weapon, graph=None):
    """The table column of one weapon; `graph` = its FP graph under masterchief\\fp\\weapons
    (Halo 3 weapons do not name it), for the FP frame rows."""
    s = export(W + weapon + '.weapon')
    if s is None:
        raise SystemExit('no %s%s.weapon in H3EK' % (W, weapon))
    # Halo 3 writes <block name=..>; Reach a <field name=.. type="block"/> before the elements
    blk = '<block name="%s"' if KIT == 'h3' else '<field name="%s" value='
    bar = s[s.find(blk % 'barrels'):]
    mag = s[s.find(blk % 'magazines'):]
    proj = ref(bar, 'projectile', 'projectile', W + weapon)
    ps = export(proj + '.projectile') if proj else None
    dmg = ref(ps, 'impact damage', 'damage_effect', proj)
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
        # Halo 3 has a campaign-only battery cost beside the multiplayer one (beam rifle 0.05
        # vs 0.1: 20 shots a battery in campaign, 10 in multiplayer; found by the Beam Rifle)
        'CAMPAIGN age per round': field(bar, 'CAMPAIGN age generated per round'),
        'heat loss / s (normal; overheated)': '%s; %s' % (field(s, 'heat loss per second'),
                                                          field(s, 'overheated heat loss per second')),
        'heat recovery / overheated threshold': '%s / %s' % (field(s, 'heat recovery threshold'),
                                                             field(s, 'overheated threshold')),
        'zoom levels (range)': '%s (%s)' % (field(s, 'magnification levels'),
                                           field(s, 'magnification range')),
        'autoaim angle / range': '%s / %s' % (field(s, 'autoaim angle'), field(s, 'autoaim range')),
        'magnetism angle / range': '%s / %s' % (field(s, 'magnetism angle'), field(s, 'magnetism range')),
        'melee 1st / 3rd hit': '%s / %s' % ((ref(s, '1st hit melee damage') or ref(s, 'melee damage', 'damage_effect') or '-').rsplit('\\', 1)[-1],
                                           (ref(s, '3rd hit melee damage') or ref(s, 'melee damage', 'damage_effect') or '-').rsplit('\\', 1)[-1]),
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
    ap.add_argument('--kit', choices=sorted(KITS), default='h3')
    a = ap.parse_args()
    use_kit(a.kit)
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

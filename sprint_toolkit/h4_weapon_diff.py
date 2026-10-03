r"""Diff Halo 4 weapon tags field by field -- the check that found the Focus Rifle port's
leftovers from its donor (2026-10-03): the Sentinel Beam's AI aim assist (20 deg deviation
= the reticle drift), acceleration scales of 0, and the missing "strict deviation angle"
and "hide FP weapon when in iron sights" flags.

A port built on another weapon's tag inherits EVERYTHING the build steps do not set.
Diff the port against a player weapon of the same family (and against its donor) before
the first boot; every difference is either intended or a leftover.

    python h4_weapon_diff.py <port.weapon> <reference.weapon> [<reference2.weapon>]
                             [--filter aim,flags,...] [--all]

Paths are relative to H4EK\tags. Uses `tool export-tag-to-xml` (no Blender); top-level
weapon flag words are also printed by NAME, from the Assembly plugin.
"""
import argparse
import os
import re
import subprocess
import sys

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: blocks whose values are expected to differ between any two weapons -- skipped unless --all
NOISE = ('heat', 'age', 'battery', 'ammo', 'damage', 'sound', 'projectile', 'rounds',
         'magazine', 'overheat', 'charging', 'message', 'msg', 'name', 'reference')


def flatten(tag):
    """{path: value} of every leaf field, block elements indexed."""
    out = os.path.join(os.environ.get('TEMP', '.'), '_h4_weapon_diff.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(H4EK, 'tags', tag), out], cwd=H4EK, capture_output=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise SystemExit('could not export %s' % tag)
    path, idx, vals = [], [], {}
    for line in open(out, encoding='utf-8', errors='replace'):
        m = re.search(r'<block name="([^"]*)"', line)
        if m:
            path.append(m.group(1))
            idx.append(None)
            continue
        m = re.search(r'<element index="(\d+)"', line)
        if m and path:
            idx[-1] = m.group(1)
            continue
        if '</block>' in line and path:
            path.pop()
            idx.pop()
            continue
        m = re.search(r'<field name="([^"]*)" value="([^"]*)" type="([^"]*)"', line)
        if m and m.group(3) not in ('pad', 'skip', 'explanation', 'struct', 'block'):
            key = '/'.join('%s[%s]' % (p, i) if i is not None else p for p, i in zip(path, idx))
            vals[(key + '/' if key else '') + m.group(1)] = m.group(2)
    return vals


def flag_names():
    """{bit: name} for the weapon's top-level Flags and Secondary Flags (plugin)."""
    try:
        sys.path.insert(0, TOOL)
        import assembly_plugins
        p = os.path.join(assembly_plugins.plugins_dir(), 'Halo4MCC', 'weap.xml')
        s = open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        return {}
    out = {}
    for name, off in (('flags', '0x2A0'), ('secondary flags', '0x2A4')):
        m = re.search(r'<flags32 name="[^"]*" offset="%s"[^>]*>(.*?)</flags32>' % off, s, re.S)
        if m:
            out[name] = {int(i): n for n, i in re.findall(r'<bit name="([^"]*)" index="(\d+)"', m.group(1))}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tags', nargs='+')
    ap.add_argument('--filter', help='comma list: only paths containing one of these')
    ap.add_argument('--all', action='store_true', help='include the usual per-weapon differences')
    a = ap.parse_args()
    v = [flatten(t) for t in a.tags]
    labels = [os.path.basename(t).rsplit('.', 1)[0][:18] for t in a.tags]
    keys = list(dict.fromkeys(k for d in v for k in d))
    want = [w.strip().lower() for w in a.filter.split(',')] if a.filter else None
    n = 0
    for k in keys:
        vals = [d.get(k) for d in v]
        if len(set(vals)) == 1:
            continue
        low = k.lower()
        if want and not any(w in low for w in want):
            continue
        if not a.all and not want and any(w in low for w in NOISE):
            continue
        n += 1
        print('%-70s %s' % (k[-70:], ' | '.join('%s=%s' % (l, (x if x is not None else '-')[:24])
                                                for l, x in zip(labels, vals))))
    names = flag_names()
    for f in ('flags', 'secondary flags'):
        bits = names.get(f)
        if not bits:
            continue
        for l, d in zip(labels, v):
            try:
                val = int(d.get(f, '0'))
            except ValueError:
                continue
            print('%-16s %-18s %s' % (f, l, ', '.join(b for i, b in sorted(bits.items()) if val >> i & 1) or '-'))
    print('%d differing field(s)%s' % (n, '' if a.all or want else ' (usual per-weapon differences hidden; --all)'))


if __name__ == '__main__':
    main()

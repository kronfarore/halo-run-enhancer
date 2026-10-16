r"""Halo 4 FLAGS BY NAME (read-only) -- step 4b decides every flags line by NAME, and H4EK's
`tool export-tag-to-xml` writes a flags field as a NUMBER; the Halo 3 bit order gives nonsense
(the Binary Rifle, C6 2026-10-16: barrel bit 9 read as 'use error when unzoomed' is
"don't clear fire bit after recovering"). ManagedBlam (in Blender, Foundry: h4_weapon_refs.py's
setup) gives each flags field's FlagIndex / FlagName; the value comes from the export.

    python h4_flag_names.py <tag> <field> [<field> ...] [-- <tag> <field> ...]

`tag` under H4EK\tags WITH its extension; `field` as h4_weapon_refs.resolve_any reads it: '/flags' =
the TOP-LEVEL field, 'barrels[0]/flags' = a block element's. Prints the set flags' names per field.
(Git Bash turns '/flags' into a path: set MSYS_NO_PATHCONV=1.)
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'


def groups(argv):
    out, cur = [], []
    for a in argv:
        if a == '--':
            out.append(cur)
            cur = []
        else:
            cur.append(a)
    out.append(cur)
    return [g for g in out if g]


def in_blender(argv):
    """Inside Blender: every field's flag table -> JSON on stdout (one 'FLAGTABLE' line)."""
    import importlib
    sys.path.insert(0, HERE)
    import h4_weapon_refs as R
    mb = importlib.import_module(R.KEY + '.managed_blam')
    u = importlib.import_module(R.KEY + '.utils')
    kit = os.path.dirname(R.H4EK_TAGS)
    have = u.read_projects_list() or []
    if kit.lower() not in [h.rstrip('\\/').lower() for h in have]:
        u.write_projects_list(have + [kit])
        u.setup_projects_list()
    if not mb.mb_active:
        mb.mb_init(os.path.join(R.H4EK_TAGS, 'globals', 'globals.globals'))

    class T(mb.Tag):
        pass

    table = {}
    for g in groups(argv):
        rel, paths = g[0], g[1:]
        with T(path=os.path.join(R.H4EK_TAGS, rel)) as t:
            for p in paths:
                f = R.resolve_any(t.tag, p)
                table['%s|%s' % (rel, p)] = {int(it.FlagIndex): str(it.FlagName) for it in f.Items}
    print('FLAGTABLE ' + json.dumps(table))


def xml_value(rel, path):
    """The flags field's number from the H4EK export (h4_tags): '/name' top level, 'block[i]/name'."""
    sys.path.insert(0, HERE)
    import h4_tags
    s = io.open(h4_tags.export_xml('h4:' + rel), encoding='utf-8', errors='replace').read()
    if path.startswith('/'):
        m = re.search(r'(?m)^    <field name="%s" value="(-?\d+)"' % re.escape(path[1:]), s)
    else:
        *blocks, name = path.split('/')
        at = 0
        for b in blocks:
            bm = re.match(r'(.+)\[(\d+)\]$', b)
            bname, idx = (bm.group(1), int(bm.group(2))) if bm else (b, 0)
            at = s.index('<block name="%s"' % bname, at)
            at = s.index('<element index="%d"' % idx, at)
        m = re.compile(r'<field name="%s" value="(-?\d+)"' % re.escape(name)).search(s, at)
    return int(m.group(1)) & 0xFFFFFFFF if m else None


def main(argv):
    env = dict(os.environ, MSYS_NO_PATHCONV='1')
    r = subprocess.run([BLENDER, '--background', '--python', os.path.abspath(__file__), '--'] + argv,
                       capture_output=True, text=True, errors='replace', env=env)
    line = next((l for l in r.stdout.splitlines() if l.startswith('FLAGTABLE ')), None)
    if line is None:
        raise SystemExit('ManagedBlam gave no table:\n' + (r.stdout + r.stderr)[-2000:])
    table = json.loads(line[len('FLAGTABLE '):])
    for key, names in table.items():
        rel, p = key.split('|', 1)
        v = xml_value(rel, p)
        on = [names.get(str(b), 'bit %d' % b) for b in range(32) if v is not None and v >> b & 1]
        print('%-55s %-22s %s  %s' % (rel.split('\\')[-1], p, v, on))


if __name__ == '__main__':
    if 'bpy' in sys.modules or os.path.basename(sys.executable).lower().startswith('blender'):
        in_blender(sys.argv[sys.argv.index('--') + 1:])
    else:
        main(sys.argv[1:])

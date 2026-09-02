# -*- coding: utf-8 -*-
r"""fear_census.py -- the fear/scariness family: which games declare it on the character tag, who sets it.

Halo 1 keeps characters in `actv` (and `actr`), every later game in `char`, so the
question "in how many games is this defined" needs all three classes asked.
"""
import io, os, sys, collections
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\tool")
sys.path.insert(0, TOOL); sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_enhancer as he, halo_patch                             # noqa: E402
import coverage_audit as ca                                        # noqa: E402
he.load_settings()
P = he.CONFIG['assembly_plugins_dir']
S = chr(92)
ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection")
CASES = [('Halo 1', ['Halo1MCC', 'Halo1'], ('halo1', 'maps'), ('actv', 'actr')),
         ('Halo 2', ['Halo2MCC', 'Halo2'], ('halo2', 'h2_maps_win64_dx11'), ('char',)),
         ('Halo 3', ['Halo3MCC', 'Halo3'], ('halo3', 'maps'), ('char',)),
         ('Halo 3: ODST', ['ODSTMCC', 'ODST'], ('halo3odst', 'maps'), ('char',)),
         ('Halo Reach', ['ReachMCC', 'Reach'], ('haloreach', 'maps'), ('char',))]
KEYS = ('scary', 'scariness', 'fear', 'panic', 'cower', 'flee', 'berserk')

for game, subs, folder, classes in CASES:
    paths = ca.game_maps(os.path.join(ROOT, *folder))
    print('\n=== %s ===' % game)
    if not paths:
        print('   no maps')
        continue
    for cls in classes:
        plug = halo_patch.PluginRegistry(P, subs).get(cls)
        if plug is None:
            print('   %s: no plugin' % cls)
            continue
        fields = sorted({f['name'] for f in plug.fields
                         if any(k in f['name'].lower() for k in KEYS)})
        print('   %s declares %d fear/scary field(s)' % (cls, len(fields)))
        if not fields:
            continue
        # who sets them, over every level
        setters = collections.defaultdict(dict)
        seen = set()
        for mp in paths:
            try:
                m = halo_patch.open_map(mp, game)
            except Exception:
                continue
            for tp, base in m.find_tags(cls, '*'):
                if tp in seen:
                    continue
                seen.add(tp)
                for f in fields:
                    fl = plug.find(f)
                    b = fl['block_chain'][-1] if fl and fl['block_chain'] else None
                    try:
                        v = m.read_tag_field(base, f, plug, b, 'all', 0)
                    except Exception:
                        v = None
                    if v:
                        setters[f][tp.rsplit(S, 1)[-1]] = (round(v, 3)
                                                           if isinstance(v, float)
                                                           else v)
        for f in fields:
            got = setters.get(f) or {}
            top = sorted(got.items(), key=lambda kv: -abs(kv[1]))[:4]
            print('      %-40s set on %3d/%3d tag(s)  %s'
                  % (f, len(got), len(seen), top if top else ''))

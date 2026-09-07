"""Third leg: actually WRITE every Halo 4 equipment target onto map copies.

Reading proves the plugin path resolves. It does not prove the write lands, and the
shared-block trap (two tag paths resolving to ONE block, so an operator applies twice)
only shows up on a real apply. This multiplies every target by 2 on a copy and checks
each result the patcher reports.
"""
import io
import json
import os
import shutil
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
MAPS = ['m10_crash', 'm30_cryptum', 'm40_invasion', 'm80_delta']
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
reg = hp.PluginRegistry(W.PLUGINS, W.SUBDIRS)

ops = []
for entry, cards in doc['Equipment'].items():
    for cname, c in cards.items():
        if not isinstance(c, dict):
            continue
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or [])
        if 'Halo 4' in (c.get('skip_games') or []) or (gl and 'Halo 4' not in gl):
            continue
        tag = W.resolve(c.get('tag'), 'Halo 4', order)
        for t in W.resolve(c.get('targets'), 'Halo 4', order) or []:
            if not isinstance(t, dict):
                continue
            gs = t.get('games')
            if gs and 'Halo 4' not in gs:
                continue
            f = W.resolve(t.get('field'), 'Halo 4', order)
            if isinstance(f, str):
                ops.append((entry, cname, tag, f, t.get('block'), t.get('index')))

print('%d Halo 4 equipment targets to write\n' % len(ops))
tot_ok = tot_none = 0
for mid in MAPS:
    src = os.path.join(hc.MAPS, mid + '.map')
    dst = os.path.join(SCRATCH, mid + '.patchtest.map')
    shutil.copyfile(src, dst)
    m = hp.open_map(dst, 'Halo 4')
    hits = fails = skipped = 0
    for entry, cname, tag, f, block, index in ops:
        cls, _, rest = tag.partition(' ')
        pl = reg.get(cls)
        for path in [p.strip() for p in rest.split('&')]:
            res = m.apply_field(cls, path, f, 'mul', 2.0, pl, block,
                                0 if index is None else index)
            for r in (res or []):
                # Two benign outcomes, neither a fault:
                #   'not present in this map' -- an ability this mission does not
                #       carry, which the mission lists already gate on.
                #   skip=True -- the shared-block dedup. Halo 4's stock and _pve
                #       variants of an ability share ONE `IWHBYDaddy` block (though
                #       NOT their `Abilities` elements), and patching both would
                #       apply the operator twice to the same struct.
                if r.get('skip'):
                    skipped += 1
                    continue
                if r.get('ok'):
                    hits += 1
                    if r.get('old') != r.get('new'):
                        continue
                    if r.get('old') in (0, 0.0):
                        continue        # nothing to multiply
                    print('   !! %s / %s / %s wrote nothing (%s)'
                          % (entry, cname, f, r.get('old')))
                    fails += 1
                elif r.get('reason') not in ('tag not found', 'not present in this map',
                                             None):
                    fails += 1
                    print('   !! %s / %s / %s -> %s'
                          % (entry, cname, f, r.get('reason')))
    m.save()
    tot_ok += hits
    tot_none += fails
    print('%-14s %4d field writes ok, %d shared-block skip(s), %d problem(s)'
          % (mid, hits, skipped, fails))
    os.remove(dst)

print('\n%d successful writes across %d maps, %d problem(s)'
      % (tot_ok, len(MAPS), tot_none))

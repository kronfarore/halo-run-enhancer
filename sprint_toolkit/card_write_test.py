"""Write-test every card touched this round.

One map copy per (game, map), reused for every target -- the previous shape copied a
map per target, which on Halo 4's maps is minutes of pure I/O.
"""
import collections
import io
import json
import os
import shutil
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import halo_enhancer as he
import h4_census as hc
import h4_wire_weapons as W

SEP = chr(92)
S = os.path.dirname(os.path.abspath(__file__))
P = r'F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins'
ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
doc = json.load(io.open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
order = list(doc['Missions'])
GAMES = collections.OrderedDict([
    ('Halo 1', (['Halo1MCC', 'Halo1'], os.path.join(ROOT, 'halo1', 'maps'),
                ['b30', 'c10'])),
    ('Halo 2', (['Halo2MCC', 'Halo2'],
                os.path.join(ROOT, 'halo2', 'h2_maps_win64_dx11'),
                ['03a_oldmombasa'])),
    ('Halo 3', (['Halo3MCC', 'Halo3'], os.path.join(ROOT, 'halo3', 'maps'),
                ['010_jungle', '030_outskirts'])),
    ('Halo 3: ODST', (['ODSTMCC', 'ODST'], os.path.join(ROOT, 'halo3odst', 'maps'),
                      ['l200'])),
    ('Halo Reach', (['ReachMCC', 'Reach'], os.path.join(ROOT, 'haloreach', 'maps'),
                    ['m30', 'm20'])),
    ('Halo 4', (['Halo4MCC', 'Halo4'], hc.MAPS,
                ['m40_invasion', 'm30_cryptum', 'm10_crash'])),
])
CHECK = [
    ('Needler', 'Needle Timer'), ('Needle Rifle', 'Needle Timer'),
    ('Plasma Launcher', 'Plasma Timer'),
    ('Frag Grenade', 'Fuse Timer'), ('Plasma Grenade', 'Fuse Timer'),
    ('Pulse Grenade', 'Fuse Timer'), ('Claymore Grenade', 'Fuse Timer'),
    ('Firebomb Grenade', 'Fuse Timer'), ('Flamethrower', 'Fuse Timer'),
    ('Scattershot', 'Super Detonation Damage'),
    ('Scattershot', 'Super Detonation Radius'), ('Scattershot', 'Bullet Damage'),
    ('Sticky Detonator', 'Explosion Damage'), ('Sticky Detonator', 'Radius'),
    ('Watcher', 'Shield'), ('Watcher', 'Grenade Catch'),
    ('Watcher', 'Turret Damage'), ('Watcher', 'Turret Vitality'),
    ('Watcher', 'Turret Rate of Fire'),
    ('Needler', 'Projectile'), ('Sniper Rifle', 'Projectile'),
    ('Assault Rifle', 'Projectile'), ('Plasma Pistol', 'Homing'),
]
found = {}


def walk(n, p):
    if isinstance(n, dict):
        if 'tag' in n and 'targets' in n:
            if len(p) >= 2:
                found[(p[-2], p[-1])] = n
            return
        for k, v in n.items():
            walk(v, p + [k])


walk(doc, [])
results = collections.defaultdict(list)     # (weapon, card, game) -> [(field, ok)]
for game, (subs, mapdir, maps) in GAMES.items():
    reg = hp.PluginRegistry(P, subs)
    jobs = []
    for key in CHECK:
        c = found.get(key)
        if c is None:
            continue
        g = c.get('game')
        gl = [g] if isinstance(g, str) else list(g or list(GAMES))
        if game not in gl or c.get('ignore'):
            continue
        tag = W.resolve(c.get('tag'), game, order)
        if not isinstance(tag, str) or ' ' not in tag:
            continue
        for t in W.resolve(c.get('targets'), game, order) or []:
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            f = W.resolve(t.get('field'), game, order)
            if isinstance(f, str):
                jobs.append((key, tag, f, t))
    if not jobs:
        continue
    hit = set()
    for mid in maps:
        fp = os.path.join(mapdir, mid + '.map')
        if not os.path.exists(fp):
            print('   !! missing %s' % fp)
            continue
        d = os.path.join(S, mid + '.vb.map')
        shutil.copyfile(fp, d)
        m = hp.open_map(d, game)
        for key, tag, f, t in jobs:
            if (key, f) in hit:
                continue
            cls, _, rest = tag.partition(' ')
            pl = reg.get(cls)
            for path in [x.strip() for x in rest.split('&')]:
                for r in (m.apply_field(cls, path, f, 'mul', 2.0, pl, t.get('block'),
                                        t.get('index', 0) if t.get('index') is not None
                                        else 0, nth=t.get('nth', 0) or 0) or []):
                    if r.get('ok') and not r.get('skip'):
                        hit.add((key, f))
        del m
        os.remove(d)
    for key, tag, f, t in jobs:
        results[(key[0], key[1], game)].append((f, (key, f) in hit))

tot = ok = 0
for (w, cn, game), rows in sorted(results.items()):
    bad = [f for f, good in rows if not good]
    tot += len(rows)
    ok += len(rows) - len(bad)
    flag = '' if not bad else '   !! no write: ' + ', '.join(bad)
    print('   %-18s %-24s %-12s %d/%d%s' % (w, cn, game, len(rows) - len(bad),
                                            len(rows), flag))
print('\n%d/%d targets wrote' % (ok, tot))

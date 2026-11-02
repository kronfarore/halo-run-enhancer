r"""READ-ONLY third pass: every declared weap reference of char / bipd tags; jmad sort order. Never saves."""
import os, struct, sys, collections
TOOL = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool'
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP
import assembly_plugins, tagrefs
GAME = 'Halo Reach'
S = chr(92)
leaf = lambda n: n.rsplit(S, 1)[-1] if n else n
name = sys.argv[1]
m = HP.open_map(r'E:\HaloBaselines\haloreach\maps\%s.map' % name, GAME)
by = {t['ident']: t for t in m.tags if t.get('ident') is not None}
pd = assembly_plugins.plugins_dir()
specs = {}
def spec(c):
    if c not in specs:
        specs[c] = tagrefs._spec(pd, 'ReachMCC', c) or tagrefs._spec(pd, 'Reach', c)
    return specs[c]
for t in m.tags:
    c = t.get('class')
    if c not in ('char', 'bipd') or not t.get('base'):
        continue
    if 'stimuli' in t['name']:
        continue
    hit = []
    for path, d in tagrefs.refs_of(m, t['base'], spec(c)):
        x = by.get(d)
        if x and x['class'] in ('weap', 'eqip') and 'eapons Properties' not in str(path) and 'Firing Pattern' not in str(path):
            hit.append((str(path), leaf(x['name'])))
    if hit:
        print(c, leaf(t['name']), hit)

# sort order of Modes / classes in one graph
for t in m.tags:
    if t.get('class') == 'jmad' and t['name'].endswith(S + 'grunt'):
        b = t['base']
        mods = m.follow_all(b, [0x104], [0x30], 'all')
        sids = [m.u32(x) for x in mods]
        print('jmad', t['name'], 'modes', len(sids), 'raw sorted', sids == sorted(sids), 'low16 sorted',
              [s & 0xFFFF for s in sids] == sorted(s & 0xFFFF for s in sids), [hex(s) for s in sids[:12]])
        for x in mods:
            lab = m.resolve_stringid(m.u32(x))
            if lab == 'combat':
                cl = m.follow_all(x, [0xC], [0x38], 'all')
                print(' combat classes', [(hex(m.u32(c)), m.resolve_stringid(m.u32(c)), m.i32(c + 8)) for c in cl])
                for c in cl:
                    ty = m.follow_all(c, [8], [0x14], 'all')
                    print('   ', m.resolve_stringid(m.u32(c)), [(hex(m.u32(y)), m.resolve_stringid(m.u32(y))) for y in ty])
                pts = [hex(m.u32(c + 8 + 4)) for c in cl]
                print(' type block ptrs', pts)
        wl = m.follow_all(b, [0x140], [8], 'all')
        print(' wlist', len(wl))
# sizes for a teach
for g in ('grunt', 'jackal', 'brute', 'bugger', 'engineer'):
    for t in m.tags:
        if t.get('class') == 'jmad' and t['name'].endswith(S + g):
            n = sum(m.i32(x + 0xC) for x in m.follow_all(t['base'], [0x104], [0x30], 'all'))
            print('jmad', g, 'modes', m.i32(t['base'] + 0x104), 'class elements', n, 'bytes', n * 0x38)

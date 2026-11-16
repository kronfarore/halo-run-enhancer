# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Read-only: every grenade-ish eqip on every campaign map, its item Flags bit 1 and
its detonation references. Prefers the pristine baseline on E:, falls back to live."""
import json, os, sys, collections
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
import halo_enhancer as he
import halo_patch as hp

C = dict(he.CONFIG); C.update(json.load(open('settings.json', encoding='utf-8')))
MCC = C['mcc_root']
db = json.load(open('halo.json', encoding='utf-8'))
games = sys.argv[1:] or list(db['Missions'])
REFS = ('Detonation Damage Effect', 'Detonating Effect', 'Detonation Effect')


def ref_name(m, game, base, fld):
    off = base + fld['offset']
    rid = m.u32(off + (4 if game == 'Halo 2' else 0xC))
    if rid in (0xFFFFFFFF, 0):
        return None
    try:
        if hasattr(m, 'tag'):
            t = m.tag(rid & 0xFFFF)
            return t['name'] if t else '?%08x' % rid
        return m.tag_name_by_id(rid)
    except Exception as e:
        return '?%08x' % rid


import re
def xml_refs(g, _c={}):
    if g in _c: return _c[g]
    for sd in C['plugin_subdirs_by_game'][g]:
        f = os.path.join(C['assembly_plugins_dir'], sd, 'eqip.xml')
        if os.path.isfile(f):
            txt = open(f, encoding='utf-8', errors='replace').read()
            r = {}
            for mm in re.finditer(r'<tag[Rr]ef name="([^"]+)" offset="(0x[0-9A-Fa-f]+)"', txt):
                if mm.group(1) in REFS and mm.group(1) not in r:
                    r[mm.group(1)] = int(mm.group(2), 16)
            _c[g] = r; return r
    _c[g] = {}; return {}

out = collections.OrderedDict()
for g in games:
    reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game'][g])
    pl = reg.get('eqip')
    ff = pl.find('Flags', None)
    # the ITEM flags: the first 'Flags' whose bits include 'always maintains z up'
    cands = [f for f in pl.fields if f['name'].lower() == 'flags'
             and 'always maintains z up' in (f.get('bits') or {})]
    ff = cands[0]
    print('##', g, 'item Flags @0x%x' % ff['offset'], 'bits', ff.get('bits'), 'chain', ff['block_chain'])
    sub = C['map_game_folder'][g]
    for mid in db['Missions'][g]:
        live = hp.default_map_path(MCC, sub, mid)
        bl = hp.baseline_path(live, C.get('baseline_root'), sub)
        path = bl if os.path.isfile(bl) else live
        if not os.path.isfile(path):
            print('  ', mid, 'NO MAP'); continue
        try:
            m = hp.open_map(path, g)
        except Exception as e:
            print('  ', mid, 'open failed', e); continue
        for tpath, tb in m.find_tags('eqip', '*grenade*'):
            allf = [f for f in pl.fields if f['name'].lower() == 'flags']
            v = m.read_tag_field(tb, 'Flags', pl, None, 0, allf.index(ff))
            refs = {}
            for rn, ro in xml_refs(g).items():
                refs[rn] = ref_name(m, g, tb, {'offset': ro})
            dl = pl.find('Detonation Delay')
            key = (g, tpath)
            e = out.setdefault(key, {'levels': [], 'flags': set(), 'refs': set()})
            e['levels'].append(mid)
            e['flags'].add(int(v) if v is not None else None)
            e['refs'].add(json.dumps(refs, sort_keys=True))
        print('  ', mid, os.path.basename(os.path.dirname(path)), 'ok', flush=True)

for (g, t), e in out.items():
    print('%-13s %-70s flags=%s bit1=%s levels=%s' % (
        g, t, sorted(e['flags'], key=str),
        sorted({(f >> 1) & 1 for f in e['flags'] if f is not None}), ','.join(e['levels'])))
    for r in e['refs']:
        print('      refs', r)

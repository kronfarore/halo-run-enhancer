# Stable Grenades research tool (2026-11-05..16), kept from the card's survey
# work; read-only. See memory halo-stable-grenades-card.
"""Read-only: the model (hlmt / H1 mod2+coll) behind each grenade pickup and its damage
fields, one map per game."""
import json, os, sys, re
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL); os.chdir(TOOL)
import halo_enhancer as he, halo_patch as hp
C = dict(he.CONFIG); C.update(json.load(open('settings.json', encoding='utf-8')))
ONE = {'Halo 1': 'a30', 'Halo 2': '03a', 'Halo 3': '010', 'Halo 3: ODST': 'sc100',
       'Halo Reach': 'm30', 'Halo 4': 'm40_invasion'}
games = sys.argv[1:] or list(ONE)
PAT = re.compile(r'vital|damage|indestruct|flags|explo|shield|immune|area|aoe', re.I)


def ref_at(m, g, off):
    rid = m.u32(off + (4 if g == 'Halo 2' else 0xC))
    if rid in (0, 0xFFFFFFFF):
        return None
    return (m.tag(rid & 0xFFFF) or {}).get('name') if hasattr(m, 'tag') else m.tag_name_by_id(rid)


def xml_ref(g, cls, name):
    for sd in C['plugin_subdirs_by_game'][g]:
        f = os.path.join(C['assembly_plugins_dir'], sd, cls + '.xml')
        if os.path.isfile(f):
            mm = re.search(r'<tag[Rr]ef name="%s" offset="(0x[0-9A-Fa-f]+)"' % re.escape(name),
                           open(f, encoding='utf-8', errors='replace').read())
            return int(mm.group(1), 16) if mm else None


def dump(m, g, reg, cls, path, base):
    pl = reg.get(cls)
    print('   [%s %s]' % (cls, path))
    for f in pl.fields:
        if not PAT.search(f['name']) and not any(PAT.search(b) for b in f['block_chain']):
            continue
        blk = '/'.join(f['block_chain']) or None
        try:
            v = m.read_tag_field(base, f['name'], pl, blk)
        except Exception as e:
            v = 'ERR'
        if v not in (None, 0, 0.0):
            print('      %-55s %-40s %s' % (f['name'], blk or '', v))


for g in games:
    reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game'][g])
    sub = C['map_game_folder'][g]
    live = hp.default_map_path(C['mcc_root'], sub, ONE[g])
    bl = hp.baseline_path(live, C.get('baseline_root'), sub)
    m = hp.open_map(bl if os.path.isfile(bl) else live, g)
    print('##', g, ONE[g])
    for tp, tb in m.find_tags('eqip', '*grenade*'):
        mo = xml_ref(g, 'eqip', 'Model')
        mdl = ref_at(m, g, tb + mo) if mo is not None else None
        print(' eqip', tp, '-> model', mdl)
        if g == 'Halo 1':
            co = xml_ref(g, 'eqip', 'Collision Model')
            coll = ref_at(m, g, tb + co) if co is not None else None
            print('    coll', coll)
            for cp, cb in (m.find_tags('coll', coll) if coll else []):
                dump(m, g, reg, 'coll', cp, cb)
            continue
        for hp_, hb in (m.find_tags('hlmt', mdl) if mdl else []):
            dump(m, g, reg, 'hlmt', hp_, hb)

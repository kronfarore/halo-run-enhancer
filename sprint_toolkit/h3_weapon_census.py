"""Which weapon tags a Halo 3 map carries, and which of them it never uses.

An unused weapon tag is a free seat: it is already in the map, already resident, already
has its own projectile and damage tags, so it can host a ported weapon without adding a
single tag-table entry. What makes it usable is that NOTHING in the level reaches for it
-- no placement, no palette slot, no character equipment -- so rewriting it costs the
level nothing.

    python h3_weapon_census.py [mission]
"""
import contextlib, io, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 3'


def main(mission='010_jungle'):
    he.load_settings()
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    weaps = sorted(p for p, _o in m.find_tags('weap', '*'))
    print('%s: %d weapon tag(s)' % (mission, len(weaps)))

    # 1. the level's weapon palette + placements
    lay = hp._MAP_WEAPONS.get(GAME)
    scnr = hp._scnr_base(m)
    placed, palette = {}, {}
    if lay and scnr is not None:
        poff, pes = lay['palette']
        pbase = hp._block_base(m, scnr + poff)
        n_pal = m.i32(scnr + poff)
        for i in range(n_pal):
            nm = hp._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
            palette[i] = nm
        woff, wes = lay['weapons']
        wbase = hp._block_base(m, scnr + woff)
        n_w = m.i32(scnr + woff)
        for i in range(n_w):
            pi = struct.unpack_from('<h', m.data, wbase + i * wes)[0]
            nm = palette.get(pi)
            if nm:
                placed[nm] = placed.get(nm, 0) + 1
        print('   palette %d, placements %d' % (n_pal, n_w))

    # 2. anything else in the map that REFERENCES a weapon tag: characters carry
    #    weapons through their char/unit tags, so a tag with no placement can still be
    #    handed out by the AI.
    referenced = set()
    idents = {}
    for t in m.tags:
        if t.get('class') == 'weap' and t.get('name'):
            idents[t['ident']] = t['name']
    hits = {}
    data = m.data
    for ident, name in idents.items():
        needle = struct.pack('<I', ident)
        n = data.count(needle)
        hits[name] = n
        if n > 1:                      # its own index entry always matches once
            referenced.add(name)

    print('\n%-58s %-6s %-9s %s' % ('weapon tag', 'placed', 'refs', 'verdict'))
    free = []
    for w in weaps:
        p = placed.get(w, 0)
        r = hits.get(w, 0)
        verdict = 'IN USE' if (p or r > 1) else 'unused -- free seat'
        if not p and r <= 1:
            free.append(w)
        print('%-58s %-6d %-9d %s' % (w.replace('objects' + B + 'weapons' + B, ''), p, r, verdict))
    print('\n%d free seat(s)' % len(free))
    for w in free:
        print('   ', w)


if __name__ == '__main__':
    main(*(sys.argv[1:2] or ['010_jungle']))

r"""Name the ported SAW's region and permutation the way every stock model does.

The dropped / ally-held SAW rendered nothing while the first-person model was fine, and a
bisect proved the fault was the world model. Its regions block turned out to be identical
to the Assault Rifle's in every field -- mesh index, mesh count, instance masks, LOD group
indices, checksum -- EXCEPT the two names: 'default' where the Assault Rifle says
'standard'. tool.exe will not be told otherwise; the JMS declares the region as `standard`
and the permutation file is standard.jms, and the render still comes out 'default'.

In a TAG the name is a length-prefixed `tgsi` chunk, so 'default' -> 'standard' would grow
the file by a byte and every enclosing chunk with it. In the built MAP the same name is a
4-byte string id, so it is a straight copy from the Assault Rifle's render model. That is
what this does, and it has to be redone after every build -- like the numbers and the
residency.

    python h3_saw_fix_region.py [--map 010_jungle] [--dry-run]
"""
import argparse, contextlib, io, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 3'
REGIONS_AT, REGION_ES = 0xC, 0x10       # mode: Regions tagblock, element size
PERMS_AT, PERM_ES = 0x4, 0x18           # within a region: Permutations
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
SAW = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw_world_model_h4_port'])


def names_of(m, tag):
    """(region name sid, permutation name sid, where they live)."""
    hits = m.find_tags('mode', tag)
    if not hits:
        return None
    meta = hits[0][1]
    n = m.i32(meta + REGIONS_AT)
    if n <= 0:
        return None
    rbase = hp._block_base(m, meta + REGIONS_AT)
    region_at = rbase
    pn = m.i32(rbase + PERMS_AT)
    perm_at = hp._block_base(m, rbase + PERMS_AT) if pn > 0 else None
    return (m.u32(region_at), m.u32(perm_at) if perm_at else None, region_at, perm_at)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    he.load_settings()
    live = os.path.join(he.mcc_root(), 'halo3', 'maps', a.map + '.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, GAME)

    src = names_of(m, AR)
    dst = names_of(m, SAW)
    if not src or not dst:
        raise SystemExit('render model missing from the map (AR %s, SAW %s)'
                         % (bool(src), bool(dst)))
    print('assault rifle  region %#010x  permutation %#010x' % (src[0], src[1]))
    print('saw            region %#010x  permutation %#010x' % (dst[0], dst[1]))
    if src[0] == dst[0] and src[1] == dst[1]:
        print('\nalready matching -- nothing to do')
        return
    if not a.dry_run:
        struct.pack_into('<I', m.data, dst[2], src[0])
        if dst[3] is not None and src[1] is not None:
            struct.pack_into('<I', m.data, dst[3], src[1])
        m.save(live)
        after = names_of(m, SAW)
        print('\nsaw now        region %#010x  permutation %#010x' % (after[0], after[1]))
        print('saved %s' % live)
    else:
        print('\n(dry run)')


if __name__ == '__main__':
    main()

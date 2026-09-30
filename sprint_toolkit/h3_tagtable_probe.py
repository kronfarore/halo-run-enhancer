"""Is there room to add a tag to a built Halo 3 map?

Three tables decide it: the tag table (8 bytes per tag), the tag-name table, and wherever
a new tag's meta would live. Each one either has slack after it -- padding we can write
into and bump a count -- or it is packed tight against the next structure, in which case
the whole table has to move and every pointer to it with it.

    python h3_tagtable_probe.py [mission]
"""
import contextlib, io, os, struct, sys

TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402


def run(bs, off, limit=4096):
    """How many zero bytes follow `off`."""
    n = 0
    while off + n < len(bs) and n < limit and bs[off + n] == 0:
        n += 1
    return n


def main(mission='010_jungle'):
    he.load_settings()
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), 'Halo 3')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, 'Halo 3')
    print('%s  (%d bytes, %d tags)' % (mission, len(m.data), m.n_tags))
    io_ = m.index_header_off
    print('index header @ %#x' % io_)
    for name, cnt_at, addr_at, esize in (('tag groups', 0x0, 0x8, 0x10),
                                         ('tag table', 0x10, 0x18, 0x8)):
        n = m.i32(io_ + cnt_at)
        va = m.u64(io_ + addr_at)
        off = m.va2off(va)
        end = off + n * esize
        print('%-11s n=%-6d va=%#x off=%#x .. %#x   zeros after: %d'
              % (name, n, va, off, end, run(m.data, end)))
        print('            next 32 bytes: %s'
              % ' '.join('%02x' % b for b in m.data[end:end + 32]))
    # where the tag NAMES live
    for attr in ('names_off', 'name_table_off', '_names_off'):
        if hasattr(m, attr):
            print('names at %s = %#x' % (attr, getattr(m, attr)))
    # the assault rifle's meta, as the thing a clone would copy
    B = os.sep
    ar = 'objects' + B + 'weapons' + B + 'rifle' + B + 'assault_rifle' + B + 'assault_rifle'
    for t in m.tags:
        if t.get('name') == ar and t.get('class') == 'weap':
            print('\nassault_rifle weap: index %d salt %#x ident %#x memaddr %#x off %#x'
                  % (t['index'], t['salt'], t['ident'], t['memaddr'], t['base']))
            break
    # is there slack at the very end of the file (somewhere to put new meta)?
    tail = m.data[-0x4000:]
    z = 0
    for b in reversed(tail):
        if b:
            break
        z += 1
    print('trailing zero bytes at EOF: %d' % z)


if __name__ == '__main__':
    main(*(sys.argv[1:2] or ['010_jungle']))

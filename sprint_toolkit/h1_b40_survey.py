r"""What a Halo 1 level gives us to aim at when Sapien will not draw it.

b40 does not render in Sapien and its player start hangs in mid-air, so markers have to
go in by coordinate. The two turrets at the start are the landmark the player can
actually see, so they are what everything else is measured from.

Halo 1's scenario keeps each placement block immediately followed by its palette, 24
bytes apart, and halo_patch already knows two of the pairs (equipment 0x258/0x264,
weapons 0x270/0x27C). The rest of the ladder follows from that spacing; every count and
position printed here is sanity-checked rather than trusted.

Placement element: palette index i16 @0, name index i16 @2, flags @4, position @8,
rotation @0x14.

    python h1_b40_survey.py [mission]
"""
import contextlib, io, math, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
GAME = 'Halo 1'
# name -> (placement reflexive, element size, palette reflexive)
BLOCKS = [('scenery', 0x210, 0x48, 0x21C),
          ('bipeds', 0x228, 0x78, 0x234),
          ('vehicles', 0x240, 0x78, 0x24C),
          ('equipment', 0x258, 0x28, 0x264),
          ('weapons', 0x270, 0x5C, 0x27C),
          ('machines', 0x294, 0x40, 0x2A0)]
PAL_ES, PAL_ID = 0x30, 0xC
START_BLOCK, START_ES = 0x354, 0x34


def read_block(m, scnr, off, esize, paloff):
    n = m.i32(scnr + off)
    if n <= 0:
        return 0, None, {}
    base = hp._block_base(m, scnr + off)
    names = {}
    if paloff is not None:
        pn = m.i32(scnr + paloff)
        if pn > 0:
            pbase = hp._block_base(m, scnr + paloff)
            for i in range(pn):
                names[i] = hp._tag_name_by_id(m, m.u32(pbase + i * PAL_ES + PAL_ID))
    return n, base, names


def main(mission='b40'):
    he.load_settings()
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo1', mission), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    scnr = hp._scnr_base(m)
    print('%s  (scenario @%#x)\n' % (mission, scnr))

    n = m.i32(scnr + START_BLOCK)
    if 0 < n < 64:
        base = hp._block_base(m, scnr + START_BLOCK)
        print('player starting locations: %d' % n)
        for i in range(n):
            x, y, z, yaw = struct.unpack_from('<4f', m.data, base + i * START_ES)
            print('   [%d]  %9.3f %9.3f %9.3f   facing %7.2f deg'
                  % (i, x, y, z, math.degrees(yaw)))

    for label, off, esize, paloff in BLOCKS:
        n, base, names = read_block(m, scnr, off, esize, paloff)
        if not n:
            continue
        print('\n%s: %d placement(s), %d palette entr(ies)' % (label, n, len(names)))
        show = label in ('vehicles', 'machines', 'weapons')
        for i in range(n if show else 0):
            pi = struct.unpack_from('<h', m.data, base + i * esize)[0]
            x, y, z = struct.unpack_from('<3f', m.data, base + i * esize + 8)
            nm = (names.get(pi) or '?').rsplit(B, 1)[-1]
            if label == 'weapons' and i >= 12:
                if i == 12:
                    print('   ... %d more' % (n - 12))
                break
            print('   [%2d] %-26s %9.3f %9.3f %9.3f' % (i, nm, x, y, z))
        if label == 'weapons':
            kinds = {}
            for i in range(n):
                pi = struct.unpack_from('<h', m.data, base + i * esize)[0]
                kinds[(names.get(pi) or '?').rsplit(B, 1)[-1]] = \
                    kinds.get((names.get(pi) or '?').rsplit(B, 1)[-1], 0) + 1
            print('   kinds: %s' % kinds)


if __name__ == '__main__':
    main(*(sys.argv[1:2] or ['b40']))

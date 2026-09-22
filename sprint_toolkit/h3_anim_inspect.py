r"""What a Halo 3 animation actually stores, so it can be resampled rather than relabelled.

`halo3_reload.scale_reload` only rewrites the Frame Count field. That is fine for making
an animation FASTER -- the engine reads fewer frames than are there -- but it cannot make
one longer: past the stored data it reads whatever follows. A port needs longer. The SAW
holds the Assault Rifle's 58-frame reload and wants 109, so the frames themselves have to
be rebuilt.

This is the reconnaissance for that: what the animation block says about itself, where its
data lives (Halo 3 keeps it in a tag RESOURCE group, not in the tag block) and how big
that data is against the frame and node counts -- which is what tells us the per-frame
stride, and therefore whether a resample is arithmetic or a codec problem.

    python h3_anim_inspect.py [--map 010_jungle] [--match reload]
"""
import argparse, contextlib, io, os, struct, sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402
import halo3_reload as hr       # noqa: E402

B = os.sep
GAME = 'Halo 3'
AR_FP = B.join(['objects', 'characters', '*', 'fp', 'weapons', 'rifle',
                'fp_assault_rifle', 'fp_assault_rifle'])
# Animations block element fields we care about, from the jmad plugin
F = dict(weight=0x4, loop=0x8, desired=0xd, current=0xe, nodes=0xf, frames=0x10,
         atype=0x12, finfo=0x13, importer=0x20, compressor=0x22,
         res_group=0x28, res_member=0x2a)
COMPRESSION = {0: 'none', 1: 'best score', 2: 'best compression', 3: 'best accuracy',
               4: 'best fullframe', 5: 'best small'}
ANIM_TYPE = {0: 'base', 1: 'overlay', 2: 'replacement'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--match', default='reload')
    a = ap.parse_args()
    he.load_settings()

    src = he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', a.map), GAME)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, GAME)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))
    plugin = reg.get('jmad')
    L = hr.LAYOUTS[GAME]

    tags = m.find_tags('jmad', AR_FP)
    print('%d graph(s) match %s\n' % (len(tags), AR_FP))
    for path, base in tags:
        pack = struct.unpack_from('<h', m.data, base + 0x12)[0]
        print('== %s   (Animation Codec Pack %d)' % (path.rsplit(B, 1)[-1], pack))
        idxs = hr._reload_anim_indices(m, base, L, (a.match,))
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        print('   %d animation(s) in the graph, %d driven by %r'
              % (len(anims), len(idxs), a.match))
        for ai in idxs:
            el = anims[ai]
            g = lambda k, fmt='<h': struct.unpack_from(fmt, m.data, el + F[k])[0]
            name = None
            try:
                name = m.resolve_stringid(struct.unpack_from('<I', m.data, el)[0])
            except Exception:
                pass
            print('   [%d] %-28s frames=%-4d nodes=%-3d type=%-11s frame-info=%d'
                  % (ai, name or '?', g('frames'), g('nodes', '<B'),
                     ANIM_TYPE.get(g('atype', '<B'), g('atype', '<B')), g('finfo', '<B')))
            print('        compression: current %s, desired %s   compressor v%d'
                  % (COMPRESSION.get(g('current', '<B'), g('current', '<B')),
                     COMPRESSION.get(g('desired', '<B'), g('desired', '<B')),
                     g('compressor')))
            print('        resource group %d, member %d   loop frame %d'
                  % (g('res_group'), g('res_member'), g('loop')))
            for blk, label in ((0x2C, 'frame events'), (0x38, 'sound events'),
                               (0x44, 'effect events'), (0x50, 'dialogue events')):
                n = struct.unpack_from('<I', m.data, el + blk)[0]
                if n:
                    print('        %-15s %d' % (label, n))


if __name__ == '__main__':
    main()

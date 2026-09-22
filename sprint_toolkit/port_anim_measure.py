r"""How much longer (or shorter) is the ported weapon's animation than the donor's?

A port built by cloning a donor keeps the DONOR's animation graph, so it reloads and
swaps at the donor's speed no matter what its own weapon looked like. The fix is a
multiplier on the cloned graph, and this is where the multiplier comes from: the ported
weapon's frame count in its HOME game over the donor's frame count in the TARGET game.

Frames, not seconds, because both are 30fps -- the units cancel the same way the balance
ratios do.

    python port_anim_measure.py                 # the SAW, Halo 4 -> Halo 3
    python port_anim_measure.py --target "Halo 1"
"""
import argparse, contextlib, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402
import halo3_reload as hr       # noqa: E402

B = os.sep
GROUPS = (('reload', ('reload',)), ('swap', ('ready', 'put_away')))

# Where each side's first-person animations live, and a mission that carries them.
SOURCE = {
    'Halo 4': dict(folder='halo4', mission='m10_crash',
                   ported=B.join(['objects', 'characters', 'storm_fp', 'weapons',
                                  'rifle', 'fp_lmg', 'storm_fp_lmg']),
                   donor=B.join(['objects', 'characters', 'storm_fp', 'weapons', 'rifle',
                                 'fp_assault_rifle', 'storm_fp_assault_rifle'])),
}
TARGET = {
    'Halo 3': dict(folder='halo3', mission='010_jungle',
                   donor=B.join(['objects', 'characters', '*', 'fp', 'weapons', 'rifle',
                                 'fp_assault_rifle', 'fp_assault_rifle'])),
    'Halo 1': dict(folder='halo1', mission='b30',
                   donor=B.join(['weapons', 'assault rifle', 'fp', 'fp'])),
}


def frames(m, pattern, game, match):
    """Total frames across every graph that matches, and the per-graph detail."""
    got = hr.reload_frames(m, pattern, game=game, match=match)
    return got


def open_mission(game, spec):
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), spec['folder'],
                                                 spec['mission']), game)
    if not os.path.exists(src):
        return None
    with contextlib.redirect_stdout(io.StringIO()):
        return hp.open_map(src, game)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='Halo 4')
    ap.add_argument('--target', default='Halo 3')
    a = ap.parse_args()
    he.load_settings()

    s_spec, t_spec = SOURCE[a.source], TARGET[a.target]
    ms, mt = open_mission(a.source, s_spec), open_mission(a.target, t_spec)
    if ms is None or mt is None:
        print('missing map for %s or %s' % (a.source, a.target))
        return

    print('%s -> %s\n' % (a.source, a.target))
    out = {}
    for group, match in GROUPS:
        ported = frames(ms, s_spec['ported'], a.source, match)
        src_donor = frames(ms, s_spec['donor'], a.source, match)
        dst_donor = frames(mt, t_spec['donor'], a.target, match)
        print('%s:' % group)
        for label, got in (('ported (%s)' % a.source, ported),
                           ('donor  (%s)' % a.source, src_donor),
                           ('donor  (%s)' % a.target, dst_donor)):
            for who, fcs in got:
                print('   %-22s %-14s %s  (total %d)'
                      % (label, who, fcs, sum(fcs)))
            if not got:
                print('   %-22s -- nothing matched' % label)

        # One number per side: the longest graph, because a weapon's reload is one
        # animation played once -- summing would count the Chief's and the Arbiter's
        # copies of the same reload twice.
        def longest(got):
            return max((sum(f) for _who, f in got), default=0)

        p, d = longest(ported), longest(dst_donor)
        if p and d:
            out[group] = p / float(d)
            print('   -> %d / %d = x%.6f\n' % (p, d, out[group]))
        else:
            print('   -> cannot measure (ported %s, donor %s)\n' % (p, d))

    print('anims: %s' % ({k: round(v, 6) for k, v in out.items()},))


if __name__ == '__main__':
    main()

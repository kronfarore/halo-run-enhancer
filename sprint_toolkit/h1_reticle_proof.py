r"""h1_add_reticle.py: a git revision's version vs the working copy, on EVERY port's reticle --
dry (the art + the MCC simulation PNGs, out\reticle_<name>[_sim].png), hashed side by side.
Nothing is written into the kit. The fast proof for a reticle-tool change (the Needle Rifle's
per-layer xform, 2026-10-10: 12 reticles identical); port_tool_proof.py is the full one.

    python h1_reticle_proof.py [--rev HEAD] [--skip needle_rifle]
"""
import argparse
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import ports_h1  # noqa: E402


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rev', default='HEAD')
    ap.add_argument('--skip', nargs='*', default=[])
    a = ap.parse_args()
    src = subprocess.run(['git', 'show', a.rev + ':sprint_toolkit/h1_add_reticle.py'], capture_output=True).stdout
    if not src:
        raise SystemExit('h1_add_reticle.py not in ' + a.rev)
    tmp = os.path.join(tempfile.mkdtemp(), 'h1_add_reticle_old.py')
    open(tmp, 'wb').write(src)
    old = load(tmp, 'ret_old')
    new = load(os.path.join(HERE, 'h1_add_reticle.py'), 'ret_new')
    old.HERE = new.HERE                       # outputs land in sprint_toolkit\out either way
    bad = n = 0
    for key in sorted(ports_h1.section('pickable')):
        if key in a.skip:
            continue
        h = ports_h1.load(key)['pickable'].get('hud', {})
        if 'reticle' not in h:
            continue
        kw = dict(thicken=h.get('reticle_thicken', 0), layers=h.get('reticle_layers', ()),
                  prefilter=h.get('reticle_prefilter', 0), scale=h.get('reticle_scale', 1.0),
                  pixel=h.get('reticle_pixel', 0), centre=h.get('reticle_centre', old.CENTRE),
                  hard=h.get('reticle_hard', 0), min_width=h.get('reticle_min_width', 0),
                  split=h.get('reticle_split', 0), dry=True)
        if h.get('reticle_xform'):
            kw['xform'] = h['reticle_xform']
        name = h['reticle'][2]
        outs = [os.path.join(HERE, 'out', 'reticle_%s%s.png' % (name.replace(' ', '_'), s)) for s in ('', '_sim')]
        digs = []
        for mod in (old, new):
            try:
                mod.add(*h['reticle'], **kw)
            except TypeError as e:             # an option the old version does not know
                digs.append(str(e))
                continue
            digs.append([hashlib.sha1(open(o, 'rb').read()).hexdigest() for o in outs])
        n += 1
        same = digs[0] == digs[1]
        bad += not same
        print('%-18s %-22s %s' % (key, name, 'IDENTICAL' if same else 'DIFFERENT'))
    print('%d reticles, %d different' % (n, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

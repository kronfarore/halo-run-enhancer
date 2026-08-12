r"""Find the player's ACTUAL world position in a running MCC, read-only.

Why: a level's Player Starting Locations say where the game intends to put you, not
where you end up. Kikowani Station's spawn sits 225 units from the nearest vanilla
weapon or equipment, which is nothing like the 8-42 units every working level shows,
so it is worth knowing whether the player really starts there before assuming the
scenario data is the problem.

No debugger needed. A position is three consecutive float32s that change together
when you move and hold still when you do not, which is exactly the changed/unchanged
narrowing the score hunt used -- and it is read-only, so it cannot disturb the game.

    python odst_poswatch.py scan                 # candidates anywhere plausible
    python odst_poswatch.py scan --near -91 225 4.5 --radius 30
    python odst_poswatch.py moved                # run after MOVING
    python odst_poswatch.py still                # run after standing STILL
    python odst_poswatch.py list
    python odst_poswatch.py watch 0x1234ABCD

Alternate scan / moved / still a few times and the survivors collapse to the player.
Compare the answer with the scenario spawn (odst_survey / the spawn dumps) to see
whether the level starts you where it says it does.
"""
import argparse
import json
import math
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2_memscan as M                                          # noqa: E402

STATE = os.path.join(os.environ.get('TEMP', '.'), 'odst_poswatch.json')
# Halo world units: a campaign level spans a few hundred. Anything beyond this is
# not a position, which throws out most of the float soup before narrowing starts.
LIMIT = 2000.0


def attach():
    pid = M.find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed -- run elevated')
    return h


def _plausible(t):
    for v in t:
        if v != v or abs(v) > LIMIT:         # NaN or out of world
            return False
    # all-zero and tiny triples are everywhere and are never a player position
    return any(abs(v) > 0.01 for v in t)


def _save(addrs, vals):
    with open(STATE, 'w') as f:
        json.dump({'addrs': addrs, 'vals': {str(k): v for k, v in vals.items()}}, f)


def _load():
    if not os.path.exists(STATE):
        raise SystemExit('no saved scan -- run `scan` first')
    with open(STATE) as f:
        d = json.load(f)
    return d['addrs'], {int(k): tuple(v) for k, v in d['vals'].items()}


def _read(h, a):
    b = M.read(h, a, 12)
    return struct.unpack('<fff', b) if b and len(b) >= 12 else None


def cmd_scan(args):
    """Vectorised with numpy: a Python loop over every 4-byte offset in ~2 GB is
    half a billion iterations and takes minutes, which makes the move/stand-still
    rhythm this depends on unusable."""
    import numpy as np
    h = attach()
    near = np.array(args.near, dtype=np.float32) if args.near else None
    regions = M.all_regions(h)
    print('%d regions, %.0f MB' % (len(regions), sum(r[1] for r in regions) / 1048576))
    found, vals = [], {}
    for base, size in regions:
        blob = M.read(h, base, size)
        if not blob or len(blob) < 16:
            continue
        n = (len(blob) // 4) - 2
        f = np.frombuffer(blob, dtype='<f4', count=n + 2)
        x, y, z = f[0:n], f[1:n + 1], f[2:n + 2]
        ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        for c in (x, y, z):
            ok &= np.abs(c) <= LIMIT
        ok &= (np.abs(x) > 0.01) | (np.abs(y) > 0.01) | (np.abs(z) > 0.01)
        if near is not None:
            # in float64 and with errors muted: the distance is evaluated over every
            # 4-byte window including the garbage the mask above is there to reject,
            # so overflow and NaN are expected here and mean nothing
            with np.errstate(all='ignore'):
                d2 = ((x.astype(np.float64) - near[0]) ** 2
                      + (y.astype(np.float64) - near[1]) ** 2
                      + (z.astype(np.float64) - near[2]) ** 2)
            ok &= np.nan_to_num(d2, nan=np.inf, posinf=np.inf) <= args.radius ** 2
        idx = np.flatnonzero(ok)
        for i in idx:
            a = base + int(i) * 4
            found.append(a)
            vals[a] = (float(x[i]), float(y[i]), float(z[i]))
            if len(found) > args.cap:
                break
        if len(found) > args.cap:
            print('hit the %d candidate cap — narrow with --near/--radius' % args.cap)
            break
    _save(found, vals)
    where = '' if near is None else ' near (%.1f, %.1f, %.1f)' % tuple(near)
    print('%d candidate position(s)%s' % (len(found), where))
    if len(found) < 30:
        cmd_list(args)
    else:
        print('move, then run:  moved      (or stand still and run:  still)')


def _narrow(args, want_change):
    addrs, old = _load()
    h = attach()
    keep, vals = [], {}
    for a in addrs:
        t = _read(h, a)
        if t is None or not _plausible(t):
            continue
        moved = a in old and math.dist(t, old[a]) > args.eps
        if moved == want_change:
            keep.append(a)
            vals[a] = t
    print('%s: %d -> %d candidate(s)'
          % ('moved' if want_change else 'still', len(addrs), len(keep)))
    _save(keep, vals)
    if keep and len(keep) < 30:
        cmd_list(args)


def cmd_list(args):
    addrs, vals = _load()
    h = attach()
    print('\n%d candidate(s):' % len(addrs))
    for a in sorted(addrs)[:40]:
        t = _read(h, a)
        print('  0x%012X  (%.2f, %.2f, %.2f)' % ((a,) + (t or (0, 0, 0))))


def cmd_watch(args):
    h = attach()
    a = int(args.addr, 0)
    print('watching 0x%X   Ctrl-C to stop' % a)
    last = None
    try:
        while True:
            t = _read(h, a)
            if t and (last is None or math.dist(t, last) > 0.05):
                print('  %s  (%.2f, %.2f, %.2f)' % ((time.strftime('%H:%M:%S'),) + t))
                last = t
            time.sleep(0.15)
    except KeyboardInterrupt:
        print('stopped')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan')
    s.add_argument('--near', nargs=3, type=float)
    s.add_argument('--radius', type=float, default=25.0)
    s.add_argument('--cap', type=int, default=200000)
    s.set_defaults(func=cmd_scan)
    for name, want in (('moved', True), ('still', False)):
        p = sub.add_parser(name)
        p.add_argument('--eps', type=float, default=0.05)
        p.set_defaults(func=lambda a, w=want: _narrow(a, w))
    sub.add_parser('list').set_defaults(func=cmd_list, eps=0.05)
    w = sub.add_parser('watch')
    w.add_argument('addr')
    w.set_defaults(func=cmd_watch)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main() or 0)

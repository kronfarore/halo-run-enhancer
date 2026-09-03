r"""Read the player's LIVE world coordinates out of the running game.

WHY THIS EXISTS
---------------
Reach's scenario Player Starting Locations are not where the player is put down. m20's
sits 70+ units from the nearest placement, and equipment dropped there does not spawn
even with a Can Attach To BSP mask of 0xFFFF -- so it is not merely far away, it is
somewhere the engine does not consider part of the playable world. Six of Reach's ten
maps have a starting location like that, and no amount of reading the map file says
where the mission actually begins. The running game does.

HOW IT WORKS
------------
There is no need to guess at object-table layouts. The player's position is three
contiguous float32s, and we already know real coordinates in the level from the
scenario -- every weapon and equipment placement is one. So:

    1. stand ON a landmark whose coordinates the map file gives us, and scan every
       private page for a float triple near it
    2. walk to a SECOND landmark and rescan the survivors -- anything that did not
       move with the player is discarded, which throws out the level geometry, the
       placement records themselves, and any stale copy
    3. read the survivors live, and walk anywhere: the mission start included

Step 2 is what makes it reliable. A single scan finds hundreds of matches, most of
them the scenario data itself sitting in memory.

USAGE
-----
    # 1. stand on the target locator on m20 (its coordinates come from the map)
    python player_pos.py find -57.3 34.7 13.1

    # 2. walk to the armor lock spot and narrow to what actually moved
    python player_pos.py refine -60.0 37.4 13.1

    # 3. walk to where the mission started you, and read it
    python player_pos.py watch
    python player_pos.py read --note "m20 mission start"

`read` appends to reports/player_pos_log.jsonl, because a measurement nobody wrote
down has to be taken again.

Reading only; the game is never written to.
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skull_diff as SD                                          # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
STATE = os.path.join(OUT, 'player_pos_candidates.json')
LOG = os.path.join(OUT, 'player_pos_log.jsonl')
# A coordinate this far from the landmark is not the player standing on it. Generous
# because "stand on it" is eyeballed, and the player origin is at the feet while a
# placement's is wherever the artist put it.
DEFAULT_TOL = 4.0
# Anything outside this is not a Reach world coordinate; it filters out the huge
# float noise that a raw scan otherwise returns.
WORLD = 4000.0


def attach():
    pid = SD.find_pid()
    if not pid:
        raise SystemExit('MCC is not running')
    h = SD.k32.OpenProcess(SD.PROCESS_QUERY_INFORMATION | SD.PROCESS_VM_READ,
                           False, pid)
    if not h:
        raise SystemExit('OpenProcess failed (%d); try an elevated shell'
                         % ctypes.get_last_error())
    return h


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def scan(h, want, tol):
    """Every address holding three contiguous float32 near `want`."""
    hits = []
    for base, size in SD.regions(h):
        if size > (1 << 28):
            continue
        data = SD.read(h, base, size)
        if not data:
            continue
        # step 4: a float triple is 4-byte aligned in every layout worth finding
        for off in range(0, len(data) - 12, 4):
            x = struct.unpack_from('<f', data, off)[0]
            if not (-WORLD < x < WORLD) or abs(x - want[0]) > tol:
                continue
            y, z = struct.unpack_from('<ff', data, off + 4)
            if near((x, y, z), want, tol):
                hits.append(base + off)
    return hits


def read_triple(h, addr):
    d = SD.read(h, addr, 12)
    if not d or len(d) < 12:
        return None
    v = struct.unpack('<fff', d)
    if any(x != x or abs(x) > WORLD for x in v):
        return None
    return v


def save(cands):
    os.makedirs(OUT, exist_ok=True)
    with open(STATE, 'w', encoding='utf-8') as f:
        json.dump({'addrs': cands, 'when': time.strftime('%Y-%m-%d %H:%M:%S')}, f)


def load():
    if not os.path.isfile(STATE):
        raise SystemExit('no candidates yet -- run `find` first')
    return json.load(open(STATE, encoding='utf-8'))['addrs']


def cmd_find(a):
    h = attach()
    want = (a.x, a.y, a.z)
    print('scanning for a float triple within %.1f of (%.1f, %.1f, %.1f)...'
          % (a.tol, *want))
    hits = scan(h, want, a.tol)
    save(hits)
    print('%d candidate(s) saved.' % len(hits))
    print('Now WALK to a different landmark and run:  player_pos.py refine X Y Z')
    return 0


def cmd_refine(a):
    h = attach()
    want = (a.x, a.y, a.z)
    keep = []
    for addr in load():
        v = read_triple(h, addr)
        if v and near(v, want, a.tol):
            keep.append(addr)
    save(keep)
    print('%d candidate(s) still match after the move.' % len(keep))
    if len(keep) > 6:
        print('Still broad -- walk somewhere else and refine again.')
    elif keep:
        print('Good. Walk to the spot you want and run:  player_pos.py watch')
    else:
        print('None survived. The first landmark may have been off, or the address '
              'moved (a level reload relocates it) -- run `find` again.')
    return 0


def cmd_watch(a):
    h = attach()
    addrs = load()
    print('%d candidate(s). Ctrl+C to stop.' % len(addrs))
    try:
        while True:
            vals = [(addr, read_triple(h, addr)) for addr in addrs]
            live = ['(%8.2f, %8.2f, %8.2f)' % v for _addr, v in vals if v]
            print('  ' + '   '.join(live[:4]) + (' ...' if len(live) > 4 else ''),
                  end='\r', flush=True)
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print()
    return 0


def cmd_read(a):
    h = attach()
    vals = [v for v in (read_triple(h, addr) for addr in load()) if v]
    if not vals:
        raise SystemExit('no candidate reads back a sane coordinate')
    for v in vals:
        print('   (%.2f, %.2f, %.2f)' % v)
    os.makedirs(OUT, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'when': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'note': a.note, 'positions': vals}) + '\n')
    print('logged to %s' % LOG)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('find', help='scan for a triple near a known landmark')
    f.add_argument('x', type=float); f.add_argument('y', type=float)
    f.add_argument('z', type=float)
    f.add_argument('--tol', type=float, default=DEFAULT_TOL)
    f.set_defaults(fn=cmd_find)
    r = sub.add_parser('refine', help='keep only what moved with you')
    r.add_argument('x', type=float); r.add_argument('y', type=float)
    r.add_argument('z', type=float)
    r.add_argument('--tol', type=float, default=DEFAULT_TOL)
    r.set_defaults(fn=cmd_refine)
    w = sub.add_parser('watch', help='print the live position continuously')
    w.add_argument('--interval', type=float, default=0.25)
    w.set_defaults(fn=cmd_watch)
    d = sub.add_parser('read', help='read once and log it')
    d.add_argument('--note', default='')
    d.set_defaults(fn=cmd_read)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())

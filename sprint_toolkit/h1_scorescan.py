r"""Find the live Halo 1 metagame SCORE in MCC's memory, by narrowing on its value.

Why this and not x64dbg: the score is the one thing about the metagame we can observe
directly. Static scanning of halo1.dll found no value table and no schema (see
h1_metagame_scan.py), so the way in is the other direction -- pin the score variable
first, then find the code that writes it. That second step is static too
(h1_xref.py), so no debugger is needed at any point.

READ-ONLY. It opens the process with QUERY_INFORMATION|VM_READ only and never writes.
Needs elevation, like the rest of the memscan tools. Campaign / offline only.

Workflow -- run one command per kill, with the game paused or not, it does not matter:

    python h1_scorescan.py scan 10        # score currently reads 10 on the HUD
    python h1_scorescan.py narrow 20      # killed another grunt, now 20
    python h1_scorescan.py narrow 35      # killed a jackal, now 35
    python h1_scorescan.py list           # survivors, with module attribution

Three or four narrows normally leaves a handful of addresses. `list` marks which ones
sit inside halo1.dll's image -- those are statics, and a static is what h1_xref.py can
chase. Heap addresses are still useful but move between runs.

    python h1_scorescan.py watch 0x1234ABCD    # confirm one address tracks the score
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2_memscan as M                                          # noqa: E402

STATE = os.path.join(os.environ.get('TEMP', '.'), 'h1_scorescan.json')
MODULES = ('halo1.dll', 'MCC-Win64-Shipping.exe', 'groundhog.dll')

# The score need not be a 32-bit int. If an int32 hunt keeps converging on junk, the
# storage is the assumption to question before the method is.
WIDTHS = {'i32': ('<i', 4), 'i64': ('<q', 8), 'i16': ('<h', 2), 'f32': ('<f', 4)}


def _pack(width, value):
    fmt, size = WIDTHS[width]
    return struct.pack(fmt, float(value) if width == 'f32' else int(value))


def _unpack(width, blob):
    fmt, size = WIDTHS[width]
    if not blob or len(blob) < size:
        return None
    v = struct.unpack(fmt, blob[:size])[0]
    return round(v, 3) if width == 'f32' else v


def _read_val(h, addr, width):
    return _unpack(width, M.read(h, addr, WIDTHS[width][1]))


def attach():
    pid = M.find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed -- run elevated')
    return pid, h


def module_map(pid):
    out = {}
    for name in MODULES:
        base, size = M.module_base(pid, name)
        if base:
            out[name] = (base, size)
    return out


def where(mods, addr):
    for name, (base, size) in mods.items():
        if base <= addr < base + size:
            return '%s+%X' % (name, addr - base)
    return None


def _save(cands, value, width='i32'):
    with open(STATE, 'w') as f:
        json.dump({'value': value, 'addrs': cands, 'width': width}, f)


def _load():
    if not os.path.exists(STATE):
        raise SystemExit('no saved scan -- run `scan <value>` first')
    with open(STATE) as f:
        d = json.load(f)
    return d['addrs'], d['value'], d.get('width', 'i32')


def cmd_scan(args):
    pid, h = attach()
    width = args.width
    value = args.value if width == 'f32' else int(args.value)
    needle = _pack(width, value)
    size_of = WIDTHS[width][1]
    regions = M.all_regions(h)
    total = sum(r[1] for r in regions)
    print('%d committed RW regions, %.0f MB -- scanning for %s %s'
          % (len(regions), total / 1048576, width, value))
    found = []
    for base, size in regions:
        blob = M.read(h, base, size)
        if not blob:
            continue
        i = blob.find(needle)
        while i != -1:
            if i % size_of == 0:                # a counter is aligned
                found.append(base + i)
            i = blob.find(needle, i + 1)
    _save(found, value, width)
    _save_values({})
    print('%d aligned candidate(s) hold %s' % (len(found), value))
    if len(found) < 40:
        cmd_list(args)
    else:
        print('kill something and run:  narrow <new score>')


def cmd_narrow(args):
    cands, prev, width = _load()
    pid, h = attach()
    value = args.value if width == 'f32' else int(args.value)
    keep = [a for a in cands if _read_val(h, a, width) == value]
    print('%d -> %d candidate(s) still equal %s (was %s)'
          % (len(cands), len(keep), value, prev))
    _save(keep, value, width)
    if not keep:
        print('nothing survived -- the score may not be a plain int32, or the earlier\n'
              'reading was stale. Re-run `scan` with the CURRENT score.')
    elif len(keep) < 40:
        cmd_list(args)


def cmd_list(args):
    cands, value, width = _load()
    pid, h = attach()
    mods = module_map(pid)
    print('\n%d candidate(s), last known value %s (%s):' % (len(cands), value, width))
    statics = 0
    for a in sorted(cands):
        now = _read_val(h, a, width)
        tag = where(mods, a)
        if tag:
            statics += 1
        print('  0x%012X  now=%-8s %s' % (a, now, tag or '(heap)'))
    if statics:
        print('\n%d of these are STATIC (inside a module image). Feed one to:\n'
              '  python h1_xref.py <module+offset>' % statics)
    else:
        print('\nAll heap. Still usable: h1_xref.py can chase the code that writes a\n'
              'heap address only via the static pointer that reaches it, so prefer a\n'
              'static hit if one appears after another narrow.')


def cmd_ptr(args):
    """Find what POINTS AT a heap score address -- the route to a static anchor.

    Why this exists: `list` showed every surviving candidate on the heap, and heap
    addresses cannot be cross-referenced statically (h1_xref only follows
    RIP-relative code references, which reach statics). But the heap object is
    reached by the game through SOME pointer, and if any link in that chain lives
    inside halo1.dll's image, that link IS a static -- and h1_xref can chase it.

    A pointer usually aims at the START of the containing object, not at the score
    field inside it, so this looks for any qword in [addr-back, addr] and reports the
    implied field offset. A pointer found inside a module image is the prize.
    """
    pid, h = attach()
    addr = int(args.addr, 0)
    mods = module_map(pid)
    lo = addr - args.back
    print('scanning for qwords in [0x%X, 0x%X]  (object base + field offset)'
          % (lo, addr))
    regions = M.all_regions(h)
    print('%d regions, %.0f MB' % (len(regions), sum(r[1] for r in regions) / 1048576))
    hits = []
    for base, size in regions:
        blob = M.read(h, base, size)
        if not blob:
            continue
        for off in range(0, len(blob) - 8, 8):
            v = int.from_bytes(blob[off:off + 8], 'little')
            if lo <= v <= addr:
                hits.append((base + off, v))
    statics = [(p, v) for p, v in hits if where(mods, p)]
    log = args.log or os.path.join(os.environ.get('TEMP', '.'),
                                   'h1_ptr_%X.txt' % addr)
    with open(log, 'w') as f:
        f.write('# pointers into [0x%X, 0x%X]  (target 0x%X)\n' % (lo, addr, addr))
        for p, v in sorted(hits, key=lambda t: (addr - t[1], t[0])):
            f.write('%s\t0x%012X\t0x%012X\t+0x%X\n'
                    % ('STATIC' if where(mods, p) else 'heap', p, v, addr - v))
    print('\n%d pointer(s), %d of them STATIC   -- all of them logged to:\n  %s'
          % (len(hits), len(statics), log))

    # Which object base do they agree on? A real structure shows up as one field
    # offset shared by many pointers; scattered one-off offsets are coincidence.
    from collections import Counter
    common = Counter(addr - v for _, v in hits).most_common(args.limit)
    print('\nmost common field offsets (offset -> how many pointers agree):')
    for off, n in common:
        print('  +0x%-6X %d' % (off, n))

    for p, v in statics[:args.limit]:
        print('  STATIC  %-28s -> 0x%X   (+0x%X to the score)'
              % (where(mods, p), v, addr - v))
    if statics:
        print('\nTake a STATIC one and run:\n'
              '  python h1_xref.py <module+offset>   (from the label above)')
    else:
        print('\nNo static pointer at depth 1 -- expected, deep game state usually\n'
              'sits several hops out. Pick the object base the offsets agree on and\n'
              're-run `ptr` against THAT, rather than against a random pointer: one\n'
              'hop from the real base beats a hundred from a coincidence.')


def _snapshot(h, cands, width):
    out = {}
    for a in cands:
        v = _read_val(h, a, width)
        if v is not None:
            out[a] = v
    return out


def cmd_rel(args):
    """Narrow WITHOUT knowing the score: keep only what moved the right way.

    This exists because exact-value narrowing failed badly. The first hunt pinned
    0x020D77AD4B40, which turned out to be the LENGTH FIELD of a UI string that
    happened to hold 21 (`mov [rbx+0x20], esi` at MCC+5D0B69, esi = 13 =
    len("mCategoryText")). Small integers collide with string lengths, refcounts and
    enum fields all over a 2 GB process, so "== 21" is nearly no evidence at all.

    A relative filter is far more selective and needs no HUD reading:
      `inc`  the score went UP   -- run it after kills
      `same` the score did NOT change -- run it while standing still, which is the
             killer filter, because unrelated counters keep moving
    Alternate inc / same a few times and the survivors collapse fast.
    """
    cands, prev, width = _load()
    pid, h = attach()
    old = _prev_values()
    now = _snapshot(h, cands, width)
    keep = []
    for a in cands:
        if a not in now or a not in old:
            continue
        if args.mode == 'inc' and now[a] > old[a]:
            keep.append(a)
        elif args.mode == 'same' and now[a] == old[a]:
            keep.append(a)
    print('%s: %d -> %d candidate(s)' % (args.mode, len(cands), len(keep)))
    _save(keep, prev, width)
    _save_values({a: now[a] for a in keep})
    if not keep:
        print('nothing survived -- if you ran `inc` without actually scoring, or\n'
              '`same` while the score was ticking, just re-run `scan`.')
    elif len(keep) < 40:
        cmd_list(args)


VALS = os.path.join(os.environ.get('TEMP', '.'), 'h1_scorescan_vals.json')


def _save_values(d):
    with open(VALS, 'w') as f:
        json.dump({str(k): v for k, v in d.items()}, f)


def _prev_values():
    if not os.path.exists(VALS):
        return {}
    with open(VALS) as f:
        return {int(k): v for k, v in json.load(f).items()}


def cmd_snap(args):
    """Record the current value of every candidate, so `inc`/`same` have a baseline."""
    cands, prev, width = _load()
    pid, h = attach()
    vals = _snapshot(h, cands, width)
    _save_values(vals)
    print('baseline recorded for %d candidate(s)' % len(vals))


def cmd_watch(args):
    pid, h = attach()
    addr = int(args.addr, 0)
    mods = module_map(pid)
    try:
        width = _load()[2]
    except SystemExit:
        width = 'i32'
    print('watching 0x%X (%s)  %s   Ctrl-C to stop'
          % (addr, width, where(mods, addr) or '(heap)'))
    last = None
    try:
        while True:
            v = _read_val(h, addr, width)
            if v != last:
                print('  %s  ->  %s' % (time.strftime('%H:%M:%S'), v))
                last = v
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('stopped')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan')
    s.add_argument('value', type=float)
    s.add_argument('--width', choices=sorted(WIDTHS), default='i32',
                   help='how the score is stored (default i32)')
    s.set_defaults(func=cmd_scan)
    n = sub.add_parser('narrow'); n.add_argument('value', type=float)
    n.set_defaults(func=cmd_narrow)
    l = sub.add_parser('list'); l.set_defaults(func=cmd_list)
    p = sub.add_parser('ptr')
    p.add_argument('addr')
    p.add_argument('--back', type=lambda s: int(s, 0), default=0x1000,
                   help='how far before the address an object base may start')
    p.add_argument('--limit', type=int, default=25)
    p.add_argument('--log', help='where to write every hit (default: TEMP)')
    p.set_defaults(func=cmd_ptr)
    sub.add_parser('snap').set_defaults(func=cmd_snap)
    i = sub.add_parser('inc'); i.set_defaults(func=cmd_rel, mode='inc')
    sm = sub.add_parser('same'); sm.set_defaults(func=cmd_rel, mode='same')
    w = sub.add_parser('watch'); w.add_argument('addr'); w.set_defaults(func=cmd_watch)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main() or 0)

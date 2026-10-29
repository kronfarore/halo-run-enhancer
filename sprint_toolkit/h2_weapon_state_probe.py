r"""Halo 2 live probe: TIME a held weapon's charge and heat (the Spartan Laser, A2 boot 2: 'charge time
needs to be measured in game, same with venting').

READ-ONLY (h2_memscan's attach, elevated). The object table is walked the way h2_memscan.resolve_unit
resolves the player's unit (halo2.dll+18B7398 entries of 12 bytes, offset at +8, objects at
((*(halo2.dll+18B7360) + 0x57) & ~0xF) + offset).

    find   after ONE shot, every object holding the float `--value` (default 0.1999995: the laser's
           battery age per round, a value no stock object carries) -- prints the candidates
    log    polls that object's first `--size` bytes every ~2 ms and writes every 4-byte word that
           changed (time, offset, old, new as float) to reports/h2_weapon_state_probe.jsonl, with the
           `--note`; Ctrl-C ends it
    times  from the last log run: per word, each RAMP 0 -> 1 (a charge) and each DECAY from >= 0.99
           down to `--floor` (the heat recovery threshold, default 0.1: the vent) with their durations

    python sprint_toolkit\h2_weapon_state_probe.py find
    python sprint_toolkit\h2_weapon_state_probe.py log --object 0x1A2B3C4D --note "laser: 3 charged shots"
    python sprint_toolkit\h2_weapon_state_probe.py times
"""
import argparse
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_memscan as M  # noqa: E402

LOG = os.path.join(HERE, 'reports', 'h2_weapon_state_probe.jsonl')


def attach():
    pid = M.find_pid()
    if not pid:
        raise SystemExit('MCC-Win64-Shipping.exe is not running')
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    base, _ = M.module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')
    return h, base


def q(h, a):
    b = M.read(h, a, 8)
    return struct.unpack('<Q', b)[0] if b else 0


def objects(h, base, limit=4096):
    """(index, address) of every live object table entry."""
    tbl = q(h, base + 0x18B7398)
    heap = (q(h, base + 0x18B7360) + 0x57) & ~0xF
    first = tbl + q(h, tbl + 0x48)
    raw = M.read(h, first, limit * 12) or b''
    out = []
    for i in range(len(raw) // 12):
        salt, = struct.unpack_from('<H', raw, i * 12)
        off, = struct.unpack_from('<i', raw, i * 12 + 8)
        if salt and off > 0:
            out.append((i, heap + off))
    return out


def find(value, size):
    h, base = attach()
    want = struct.pack('<f', value)
    hits = []
    for i, addr in objects(h, base):
        d = M.read(h, addr, size) or b''
        at = [k for k in range(0, len(d) - 3, 4) if d[k:k + 4] == want]
        if at:
            hits.append((i, addr, at))
    for i, addr, at in hits:
        print('object #%d at 0x%X: %g at +%s' % (i, addr, value, ', '.join('0x%X' % k for k in at)))
    if not hits:
        print('no object holds %r -- fire ONE shot first (the battery age per round)' % value)
    M.k32.CloseHandle(h)


def log(addr, size, note):
    h, _base = attach()
    prev = M.read(h, addr, size)
    if not prev:
        raise SystemExit('cannot read 0x%X' % addr)
    run = int(time.time())
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    print('logging 0x%X (+0..0x%X) -- charge, fire, let it vent; Ctrl-C to stop' % (addr, size))
    t0 = time.perf_counter()
    n = 0
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'run': run, 'start': time.strftime('%Y-%m-%d %H:%M:%S'), 'object': '0x%X' % addr,
                             'note': note, 'condition': 'Halo 2 MCC, live object words (h2_weapon_state_probe)'}) + '\n')
        try:
            while True:
                cur = M.read(h, addr, size)
                if cur and cur != prev:
                    t = time.perf_counter() - t0
                    for k in range(0, size - 3, 4):
                        if cur[k:k + 4] != prev[k:k + 4]:
                            a, = struct.unpack_from('<f', prev, k)
                            b, = struct.unpack_from('<f', cur, k)
                            fh.write(json.dumps({'run': run, 't': round(t, 4), 'off': k, 'old': a, 'new': b}) + '\n')
                            n += 1
                    prev = cur
                time.sleep(0.002)
        except KeyboardInterrupt:
            pass
    print('%d changes logged to %s' % (n, LOG))
    M.k32.CloseHandle(h)


def times(floor):
    rows = [json.loads(x) for x in open(LOG, encoding='utf-8') if x.strip()]
    run = max(r['run'] for r in rows)
    head = next(r for r in rows if r['run'] == run and 'note' in r)
    print('run %s (%s): %s' % (run, head['start'], head['note']))
    series = {}
    for r in rows:
        if r['run'] == run and 'off' in r:
            series.setdefault(r['off'], []).append((r['t'], r['old'], r['new']))
    for off, s in sorted(series.items()):
        vals = [(t, b) for t, _a, b in s if b == b and -0.01 <= b <= 1.01]
        if len(vals) < 5:
            continue
        ramps, decays = [], []
        start = None
        for (t, v), (t2, v2) in zip(vals, vals[1:]):
            if start is None and v <= 0.02 and v2 > v:
                start = t
            if start is not None and v2 >= 0.99:
                ramps.append(round(t2 - start, 3))
                start = None
            if start is not None and v2 < v - 0.2:
                start = None
        top = None
        for t, v in vals:
            if v >= 0.99:
                top = t
            elif top is not None and v <= floor:
                decays.append(round(t - top, 3))
                top = None
        if ramps or decays:
            print('   +0x%03X  ramps 0 -> 1: %s   decays 1 -> %.2f: %s' % (off, ramps or '-', floor, decays or '-'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=('find', 'log', 'times'))
    ap.add_argument('--value', type=float, default=0.1999995)
    ap.add_argument('--object')
    ap.add_argument('--size', type=lambda s: int(s, 0), default=0x400)
    ap.add_argument('--note', default='')
    ap.add_argument('--floor', type=float, default=0.1)
    a = ap.parse_args(argv)
    if a.mode == 'find':
        find(a.value, a.size)
    elif a.mode == 'log':
        if not a.object:
            raise SystemExit('--object 0x... (from `find`)')
        log(int(a.object, 0), a.size, a.note)
    else:
        times(a.floor)


if __name__ == '__main__':
    main()

r"""Halo 1 live probe: the FIRST-PERSON animation the game plays, beside the held weapon's MAGAZINE -- read-only.

Written for the Scattershot (C5, 2026-10-15): three shell-reload theories built from the user's shell
COUNTS each failed in game; this measurement settled it in one boot (PORTING 'Halo 1: the Scattershot',
memory h1-shell-reload-mechanism). The weapon object does not hold the first-person state, so:
  1. wait for a mission, read the held weapon's object handle (h1_weapon_state_probe.held);
  2. FIND every 4-aligned copy of that handle in MCC's writable memory -- one of them sits in the
     first-person record (MCC halo1, 2026-10-15: +0x10 = animation index into the weapon's FP
     model_animations (u16), +0x12 = its frame (u16));
  3. WATCH 0x100 bytes around every hit plus the weapon's magazine (weapon object +0x280: state u16,
     ticks u16; +0x284: cycle length u16, reserve u16; +0x288: -, rounds loaded u16), every ~10 ms,
     logging the words that change -> out/fp_state_probe.jsonl.
`--analyse --port <key>` picks the record whose +0x10 low half stays a small index while its high half
counts frames, names the indices from the port's compiled FP animations, and prints per reload: the
magazine cycles (length, rounds loaded) and the first-person sequence (enter / reload-empty / ...).
    python sprint_toolkit/h1_fp_state_probe.py --seconds 240 --note "scattershot reloads 1..5 missing"
    python sprint_toolkit/h1_fp_state_probe.py --analyse --port scattershot
(Run elevated if OpenProcess fails. A level restart gives the weapon a new handle: restart the probe.)
Promoted 2026-10-16 from the two scratch scripts the measurement ran (find + watch, verified on boots 4-5);
`--analyse` re-tested on boot 5's log (enter -> reload-empty -> reload-full -> exit-full / exit-empty);
the combined logging half (magazine + hits in one file) has not run live yet.
"""
import argparse
import ctypes
import ctypes.wintypes as W
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import death_penalty as dp  # noqa: E402
import h1_melee_fire_probe as mp  # noqa: E402
import h1_weapon_state_probe as ws  # noqa: E402

OUT = os.path.join(HERE, 'out', 'fp_state_probe.jsonl')
MAG = 0x280                     # the weapon object's magazine 0 (state/ticks, cycle/reserve, -/loaded)
FP_WORD = 0x10                  # in the first-person record: anim index (lo) | frame (hi)


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', W.DWORD), ('PartitionId', W.WORD), ('RegionSize', ctypes.c_size_t),
                ('State', W.DWORD), ('Protect', W.DWORD), ('Type', W.DWORD)]


def find(h, value):
    """Every 4-aligned address in committed read/write memory holding the u32 `value`."""
    k32 = ctypes.windll.kernel32
    k32.VirtualQueryEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    needle, hits, addr, m = struct.pack('<I', value), [], 0, MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(m), ctypes.sizeof(m)):
        if m.State == 0x1000 and m.Protect in (0x04, 0x40) and m.RegionSize < 1 << 30:
            try:
                blob = dp.read(h, m.BaseAddress, m.RegionSize)
            except Exception:
                blob = None
            i = blob.find(needle) if blob else -1
            while i >= 0:
                if (m.BaseAddress + i) % 4 == 0:
                    hits.append(m.BaseAddress + i)
                i = blob.find(needle, i + 1)
        addr = (m.BaseAddress or 0) + m.RegionSize
        if addr >= 0x7FFFFFFFFFFF:
            break
    return hits


def run(a):
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running')
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    base = dp.module_base(pid, b'halo1.dll')
    if not base:
        raise SystemExit('halo1.dll not loaded')
    print('waiting for a mission ...')
    while True:
        try:
            wh, _c, _u = ws.held(h, base)
        except (TypeError, struct.error):
            wh = None
        if wh not in (None, 0xFFFFFFFF):
            break
        time.sleep(0.5)
    hits = find(h, wh)
    print('weapon %08x: %d copies of its handle; logging %d s -- reload with 1, 2, 3 ... rounds missing'
          % (wh, len(hits), a.seconds))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prev, t0, rows = {}, time.perf_counter(), 0
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'start': time.strftime('%Y-%m-%d %H:%M:%S'), 'note': a.note,
                            'weapon': '%08x' % wh, 'hits': ['%x' % x for x in hits]}) + '\n')
        while time.perf_counter() - t0 < a.seconds:
            row = {'ms': round((time.perf_counter() - t0) * 1000, 1), 'ch': {}}
            w = mp.obj(h, base, wh)
            areas = [('mag', w + MAG, 0x10)] if w else []
            areas += [('%x' % x, x - 0x80, 0x100) for x in hits]
            for name, lo, n in areas:
                b = dp.read(h, lo, n)
                if not b or len(b) < n:
                    continue
                cur = ws.words(b)
                p = prev.get(name)
                if p is not None:
                    for k, (x, y) in enumerate(zip(p, cur)):
                        if x != y:
                            off = k * 4 - (0x80 if name != 'mag' else 0)
                            row['ch']['%s%+x' % (name, off)] = [x, y]
                else:
                    row['ch'].update({'%s%+x' % (name, k * 4 - (0x80 if name != 'mag' else 0)): [None, y]
                                      for k, y in enumerate(cur)})
                prev[name] = cur
            if row['ch']:
                f.write(json.dumps(row) + '\n')
                rows += 1
            time.sleep(0.008)
    print('%d row(s) -> %s' % (rows, OUT))


def fp_names(port):
    """The port's compiled FP animation names, in tag order (= the record's index)."""
    import port_env  # noqa: F401
    import ports_h1
    from reclaimer.hek.defs.antr import antr_def
    rel = ports_h1.load(port)['pickable']['fp_anims'] if hasattr(ports_h1, 'load') else None
    if rel is None:
        import importlib
        rel = importlib.import_module('ports_h1.' + port).PORT['pickable']['fp_anims']
    p = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags', rel + '.model_animations')
    t = antr_def.build(filepath=p).data.tagdata
    return [a.name.replace('first-person ', '') for a in t.animations.STEPTREE]


def analyse(a):
    rows = []
    for line in open(OUT, encoding='utf-8'):
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    starts = [i for i, r in enumerate(rows) if 'start' in r]
    if not starts:
        raise SystemExit('no run in %s' % OUT)
    run_rows = rows[starts[a.run] + 1:(starts[a.run + 1] if a.run + 1 < len(starts) and a.run != -1 else None)]
    print(rows[starts[a.run]].get('note'))
    # the FP record: the hit whose +0x10 word keeps a small low half and a counting high half
    series = {}
    for r in run_rows:
        for k, (_x, y) in r['ch'].items():
            if k.endswith('+10') and not k.startswith('mag'):
                series.setdefault(k, []).append((r['ms'], y))
    best, score = None, 0
    for k, v in series.items():
        lo = {y & 0xFFFF for _t, y in v}
        steps = sum(1 for (_a, x), (_b, y) in zip(v, v[1:]) if (y >> 16) == (x >> 16) + 1)
        if max(lo) < 64 and steps > score:
            best, score = k, steps
    if not best:
        raise SystemExit('no first-person record found among the hits')
    names = fp_names(a.port) if a.port else None
    print('first-person record: %s (anim index at +0x10, frame at +0x12)' % best[:-3])
    name = lambda i: names[i] if names and i < len(names) else i
    # 1) the first-person stages, one line a reload: from an `enter` to the next `idle`
    seq, prev = None, None
    for t, y in series[best]:
        i = y & 0xFFFF
        if i == prev:
            continue
        n = name(i)
        if n == 'enter':
            seq = [t, ['enter']]
        elif seq is not None:
            seq[1].append(str(n))
            if n == 'idle':
                print('%7.1f s  first person: %s' % (seq[0] / 1000, ' -> '.join(seq[1])))
                seq = None
        prev = i
    # 2) the magazine, one line a reload: every cycle's length (ticks) and the rounds loaded after it
    mag, cur = {}, None
    for r in run_rows:
        for k, (_x, y) in r['ch'].items():
            if k.startswith('mag'):
                mag[k] = y
        state, cyc, loaded = mag.get('mag+0', 0) & 0xFFFF, mag.get('mag+4', 0) & 0xFFFF, mag.get('mag+8', 0) >> 16
        if state == 1:
            if cur is None:
                cur = [r['ms'], loaded, []]
            if not cur[2] or cur[2][-1] != (cyc, loaded):
                cur[2].append((cyc, loaded))
        elif cur is not None and state in (0, 2, 3):
            print('%7.1f s  magazine: from %d loaded, cycles %s -> %d' % (
                cur[0] / 1000, cur[1], ' '.join('%d' % c for c, _l in cur[2]), loaded))
            cur = None
    print("(cycle 1 = the enter's length; one round a cycle; repeated loops show once in the FP line)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds', type=float, default=240.0)
    ap.add_argument('--note', default='')
    ap.add_argument('--analyse', action='store_true')
    ap.add_argument('--port', help='--analyse: a ports_h1 key, to name the FP animation indices')
    ap.add_argument('--run', type=int, default=-1, help='--analyse: which run (default the last)')
    a = ap.parse_args(argv)
    analyse(a) if a.analyse else run(a)


if __name__ == '__main__':
    main()

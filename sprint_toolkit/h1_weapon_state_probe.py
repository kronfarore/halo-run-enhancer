r"""Halo 1 live probe: the HELD weapon object's state while firing, and the same object after a DROP.

Written for the Plasma Repeater (wave B3, boot 2, 2026-10-11): three things the tags did not settle --
the heat never reached the overheat threshold (Halo 1 cools while firing; does the rate ramp from 15
DOWN to 3 at all?), the on-gun lights driven by a change colour stayed black, and a dropped gun
rests nose-first in the ground. Instead of guessing a fourth time: measure.

Every change (polled far faster than the 30 Hz tick) is appended to out/weapon_state_probe.jsonl:
  held    the weapon object's first 0x2A0 bytes as 4-byte words -- only the words that CHANGED since
          the last row (offset: [old, new] as float and hex), plus the unit's control flags (+0x1D8,
          0x800 = fire) so the rows can be read against the trigger
  dropped once the player no longer holds that weapon, the same object keeps being logged (its
          header: position +0x5C, velocity +0x68, forward +0x74, up +0x80, angular velocity +0x8C)
          until it has been still for 3 s
The words that matter are found AFTERWARDS (h1_weapon_state_probe.py --analyse): which offset rises
by a fixed step per shot (heat), which counts shots, which ticks (rate), which change colours.

    python sprint_toolkit/h1_weapon_state_probe.py --seconds 90 --note "repeater: hold fire, drop"
    python sprint_toolkit/h1_weapon_state_probe.py --analyse
"""
import argparse
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
import h1_melee_fire_probe as mp  # noqa: E402  (player unit -> object resolution)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'weapon_state_probe.jsonl')
SIZE = 0x2A0


def words(b):
    return struct.unpack('<%dI' % (len(b) // 4), b[:len(b) // 4 * 4])


def f32(u):
    return round(struct.unpack('<f', struct.pack('<I', u))[0], 5)


def held(h, base):
    pc = mp.u64(h, base + mp.PLAYER_CONTROL_PTR)
    if not pc:
        return None, None, None
    unit_h = struct.unpack('<I', dp.read(h, pc + 0x10, 4))[0]
    u = mp.obj(h, base, unit_h)
    if not u:
        return None, None, None
    ub = dp.read(h, u, 0x2E0)
    idx = struct.unpack_from('<b', ub, 0x2D3)[0]
    wh = struct.unpack_from('<I', ub, 0x2D8 + 4 * idx)[0] if 0 <= idx < 4 else 0xFFFFFFFF
    return wh, struct.unpack_from('<I', ub, 0x1D8)[0], u


def run(a):
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running')
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    base = dp.module_base(pid, b'halo1.dll')
    if not base:
        raise SystemExit('halo1.dll not loaded')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print('waiting for a mission ...')
    while True:
        try:
            wh, _c, _u = held(h, base)
        except (TypeError, struct.error):
            wh = None
        if wh not in (None, 0xFFFFFFFF):
            break
        time.sleep(0.5)
    print('logging %d s -- fire in bursts and held, let it overheat, then DROP it and wait' % a.seconds)
    t0 = time.perf_counter()
    track = None                      # the weapon handle being followed (held, then dropped)
    last = {}
    still_since = None
    rows = 0
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'start': time.strftime('%Y-%m-%d %H:%M:%S'), 'note': a.note}) + '\n')
        while time.perf_counter() - t0 < a.seconds:
            try:
                wh, ctrl, _u = held(h, base)
                if track is None and wh not in (None, 0xFFFFFFFF):
                    track = wh               # the weapon held at the start, followed after a drop
                if track is None:
                    continue
                w = mp.obj(h, base, track)
                b = dp.read(h, w, SIZE) if w else None
            except (TypeError, struct.error):
                continue
            if not b:
                continue
            ws = words(b)
            ch = {('%03x' % (i * 4)): [f32(last[i]) if i in last else None, f32(v), '%08x' % v]
                  for i, v in enumerate(ws) if last.get(i) != v}
            if not ch:
                if wh != track:
                    still_since = still_since or time.perf_counter()
                    if time.perf_counter() - still_since > 3.0:
                        print('dropped weapon at rest for 3 s -- done')
                        break
                continue
            dropped = wh != track
            if dropped:
                moving = any(k in ch for k in ('05c', '060', '064', '074', '078', '07c', '080', '084', '088'))
                still_since = None if moving else (still_since or time.perf_counter())
                pose = {k: [f32(ws[int(k, 16) // 4 + j]) for j in range(3)] for k in ('05c', '068', '074', '080', '08c')}
            row = {'ms': round((time.perf_counter() - t0) * 1000, 1), 'weapon': '%08x' % track,
                   'held': not dropped, 'fire': bool((ctrl or 0) & 0x800), 'ch': ch}
            if dropped:
                row['pose'] = pose
            for i, v in enumerate(ws):
                last[i] = v
            f.write(json.dumps(row) + '\n')
            rows += 1
    print('%d row(s) -> %s' % (rows, OUT))


def analyse(a):
    """Per offset of the held weapon: how often it changed while firing, and its range -- the
    candidates for heat (steps per shot, falls between), a shot counter, timers."""
    runs, cur = [], None
    for line in open(OUT, encoding='utf-8'):
        r = json.loads(line)
        if 'start' in r:
            cur = {'note': r.get('note'), 'rows': []}
            runs.append(cur)
        elif cur is not None:
            cur['rows'].append(r)
    run_ = runs[a.run]
    print('run %d of %d: %s, %d rows' % (a.run % len(runs), len(runs), run_['note'], len(run_['rows'])))
    stats = {}
    for r in run_['rows']:
        if not r['held']:
            continue
        for k, (old, new, _hx) in r['ch'].items():
            s = stats.setdefault(k, {'n': 0, 'fire': 0, 'lo': new, 'hi': new})
            s['n'] += 1
            s['fire'] += r['fire']
            if new is not None:
                s["lo"], s["hi"] = min(s["lo"], new), max(s["hi"], new)
    for k in sorted(stats):
        s = stats[k]
        if s['n'] >= a.min:
            print('  +0x%s  changes %4d (%4d firing)  range %s .. %s' % (k, s['n'], s['fire'], s['lo'], s['hi']))
    drops = [r for r in run_['rows'] if not r['held']]
    if drops:
        print('dropped: %d rows; first pose %s' % (len(drops), drops[0]['pose']))
        print('         last pose %s' % drops[-1]['pose'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds', type=float, default=90.0)
    ap.add_argument('--note', default='')
    ap.add_argument('--analyse', action='store_true')
    ap.add_argument('--run', type=int, default=-1, help='--analyse: which run (default the last)')
    ap.add_argument('--min', type=int, default=3, help='--analyse: offsets changing at least this often')
    a = ap.parse_args(argv)
    (analyse if a.analyse else run)(a)


if __name__ == '__main__':
    main()

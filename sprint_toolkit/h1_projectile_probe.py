r"""Halo 1 live probe: every PROJECTILE object's state from creation to detonation -- read-only.

Written for the Grenade Launcher (wave B4, boot 1, 2026-10-12): its grenade (Halo 1's frag grenade
projectile, fired at 12.5 -> 7.5 wu/s, fuse 0.5 s 'on first bounce') bounced erratically and burst
~9 s later instead of 0.5 s after its first bounce -- about its 100 wu maximum range. Two questions
the tags do not settle: does a projectile with a velocity stay PROPELLED after a bounce (its speed
forced along initial -> final), and when does the detonation timer run? Measure, do not guess.

Polls the object table far faster than the 30 Hz tick; for each object whose tag is a `proj`:
  new     its tag name, handle, the first 0x300 bytes as words
  ch      only the words that CHANGED since the last row (offset: [old, new] as float and hex),
          plus its position (+0x18) and speed (|+0x24|, wu per tick x 30 = wu/s) every row
  gone    the poll it disappeared (detonated / removed), with its last position
Rows -> out/projectile_probe.jsonl. `--analyse` prints per projectile: life, distance, speed over
time, and the words that ran DOWN monotonically (a fuse) or flipped once (a 'bounced' flag).

    python sprint_toolkit/h1_projectile_probe.py --seconds 120 --note "GL tap at the ground"
    python sprint_toolkit/h1_projectile_probe.py --analyse [--last]
"""
import argparse
import json
import math
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
import h1_melee_fire_probe as mp  # noqa: E402  (object / tag resolution, pointers)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'projectile_probe.jsonl')
SIZE = 0x300
POS, VEL = 0x18, 0x24          # object header: position, translational velocity (wu per tick)


def words(b):
    return struct.unpack('<%dI' % (len(b) // 4), b[:len(b) // 4 * 4])


def f32(u):
    return round(struct.unpack('<f', struct.pack('<I', u))[0], 5)


def tag_info(h, base, tid):
    """(class, name) of a tag index (the tag instance table: class fourcc at +0, name at +0x10)."""
    inst = mp.u64(h, base + mp.TAG_TABLE_PTR)
    e = dp.read(h, inst + (tid & 0xFFFF) * 32, 32)
    if not e or len(e) < 32:
        return None, None
    cls = e[:4][::-1].decode('latin1', 'replace')
    p = struct.unpack_from('<i', e, 0x10)[0]
    raw = dp.read(h, p - mp.u64(h, base + mp.TAG_ADDR_BASE) + mp.u64(h, base + mp.TAG_DATA_BASE), 160) or b''
    return cls, raw.split(b'\0')[0].decode('latin1', 'replace')


def objects(h, base):
    """[(handle, address)] of every live object (the data array: entries of 12 bytes from +0x34's
    offset -- salt u16 at +0, data offset at +8; the count as a short at +0x2E, tried first)."""
    table = mp.u64(h, base + mp.OBJ_TABLE_PTR)
    if not table:
        return []
    hdr = dp.read(h, table, 0x38)
    if not hdr or len(hdr) < 0x38:              # no mission loaded
        return []
    first = struct.unpack_from('<i', hdr, 0x34)[0]
    n = max(struct.unpack_from('<h', hdr, 0x2E)[0], struct.unpack_from('<h', hdr, 0x20)[0])
    n = max(0, min(n, 4096))
    raw = dp.read(h, table + first, 12 * n) or b''
    data = mp.u64(h, base + mp.OBJ_DATA_PTR)
    out = []
    for i in range(len(raw) // 12):
        salt, = struct.unpack_from('<H', raw, i * 12)
        off, = struct.unpack_from('<i', raw, i * 12 + 8)
        if salt and off != -1:
            out.append(((salt << 16) | i, data + 0x34 + off))
    return out


def run(a):
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running')
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    base = dp.module_base(pid, b'halo1.dll')
    if not base:
        raise SystemExit('halo1.dll not loaded')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    names = {}                                   # tag index -> (class, name)
    live = {}                                    # handle -> {'last': words, 'tag': name}
    t0 = time.perf_counter()
    rows = 0
    print('logging %d s -- fire the projectiles to measure' % a.seconds)
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'start': time.strftime('%Y-%m-%d %H:%M:%S'), 'note': a.note}) + '\n')
        while time.perf_counter() - t0 < a.seconds:
            try:
                objs = objects(h, base)
            except (TypeError, struct.error):
                time.sleep(0.2)
                continue
            now = round((time.perf_counter() - t0) * 1000, 1)
            seen = set()
            for hd, addr in objs:
                try:
                    b_ = dp.read(h, addr, SIZE)
                except (TypeError, struct.error):
                    b_ = None
                if not b_ or len(b_) < SIZE:
                    continue
                ws = words(b_)
                tid = ws[0]
                if tid not in names:
                    try:
                        names[tid] = tag_info(h, base, tid)
                    except (TypeError, struct.error):
                        names[tid] = (None, None)
                cls, name = names[tid]
                if cls != 'proj' or (a.match and a.match not in (name or '')):
                    continue
                seen.add(hd)
                pos = [f32(ws[POS // 4 + j]) for j in range(3)]
                vel = [f32(ws[VEL // 4 + j]) for j in range(3)]
                speed = round(math.sqrt(sum(v * v for v in vel)) * 30.0, 3)
                F = live.get(hd)
                if F is None:
                    live[hd] = {'last': ws, 'tag': name}
                    f.write(json.dumps({'ms': now, 'new': '%08x' % hd, 'tag': name, 'pos': pos,
                                        'speed': speed, 'words': ['%08x' % w for w in ws]}) + '\n')
                    rows += 1
                    continue
                ch = {('%03x' % (i * 4)): [f32(F['last'][i]), f32(v), '%08x' % v]
                      for i, v in enumerate(ws) if F['last'][i] != v}
                if ch:
                    f.write(json.dumps({'ms': now, 'p': '%08x' % hd, 'pos': pos, 'speed': speed,
                                        'ch': ch}) + '\n')
                    rows += 1
                F['last'] = ws
            for hd in [x for x in live if x not in seen]:
                F = live.pop(hd)
                f.write(json.dumps({'ms': now, 'gone': '%08x' % hd, 'tag': F['tag'],
                                    'pos': [f32(F['last'][POS // 4 + j]) for j in range(3)]}) + '\n')
                rows += 1
    print('%d row(s) -> %s' % (rows, OUT))


def analyse(a):
    runs, cur = [], None
    for line in open(OUT, encoding='utf-8'):
        r = json.loads(line)
        if 'start' in r:
            cur = {'note': r['note'], 'rows': []}
            runs.append(cur)
        elif cur is not None:
            cur['rows'].append(r)
    for run_ in (runs[-1:] if a.last else runs):
        print('== %s' % run_['note'])
        P = {}
        for r in run_['rows']:
            hd = r.get('new') or r.get('p') or r.get('gone')
            P.setdefault(hd, []).append(r)
        for hd, rs in P.items():
            t_new = rs[0]['ms']
            tag = rs[0].get('tag')
            end = rs[-1]
            life = (end['ms'] - t_new) / 1000.0
            path = 0.0
            pts = [x['pos'] for x in rs if 'pos' in x]
            for p, q in zip(pts, pts[1:]):
                path += math.dist(p, q)
            print('  %s %s: life %.2f s, path %.1f wu, %s' % (hd, tag, life, path,
                                                            'GONE' if 'gone' in end else 'alive'))
            sp = [(round((x['ms'] - t_new) / 1000.0, 2), x['speed']) for x in rs if 'speed' in x]
            step = max(1, len(sp) // 24)
            print('    speed (s, wu/s): %s' % sp[::step])
            # words that ran down steadily (a fuse) or changed exactly once (a flag)
            hist = {}
            for x in rs:
                for k, (_o, n, _h) in x.get('ch', {}).items():
                    hist.setdefault(k, []).append(((x['ms'] - t_new) / 1000.0, n))
            for k, v in sorted(hist.items()):
                if k in ('018', '01c', '020', '024', '028', '02c'):
                    continue
                vals = [n for _t, n in v]
                if len(v) == 1:
                    print('    %s changed once at %.2f s -> %s' % (k, v[0][0], v[0][1]))
                elif all(b <= c for b, c in zip(vals[1:], vals)) and vals[0] != vals[-1] and len(v) >= 4:
                    print('    %s ran DOWN %s -> %s over %.2f..%.2f s (%d steps)'
                          % (k, vals[0], vals[-1], v[0][0], v[-1][0], len(v)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=int, default=120)
    ap.add_argument('--note', default='')
    ap.add_argument('--match', default='', help='only projectiles whose tag path holds this')
    ap.add_argument('--analyse', action='store_true')
    ap.add_argument('--last', action='store_true')
    a = ap.parse_args(argv)
    (analyse if a.analyse else run)(a)


if __name__ == '__main__':
    main()

r"""Halo 2 live probe, READ-ONLY: what is stuck in the PLAYER's unit (the player-supercombine hunt,
h2_supercombine_players.py; the Needle Rifle B2, 2026-11-17: the patch is on and still no combine).

Polls the player's unit (h2_memscan.resolve_unit's chain) and walks its children the way the
attach count (+0x9040C0) does: first child at object +0x10, next sibling at +0xC, the tag datum at
+0x0. For every child it prints the tag datum and the projectile flags dword at +0x130:
    0x08 attached (set by +0x9040C0 itself)    0x40 already counted / detonating
    0x80 marked for the supercombine (set by +0x9040C0 when the count passes the tag's field)
Every change of the child list is printed and appended to reports/h2_stuck_needle_probe.jsonl
with the `--note` (memory halo-log-measured-values).

    python sprint_toolkit\h2_stuck_needle_probe.py --seconds 120 --note "05a, patch on, Needler Grunts"
    python sprint_toolkit\h2_stuck_needle_probe.py --all ...   EVERY object with stuck needles (an enemy's
           working combine, for comparison); a child counts as a needle when flags & 0x818 == 0x818
           [--tags F9C4184E,FD3B1BC5: only those projectile tag datums -- read them off a player run]
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

OUT = os.path.join(HERE, 'reports', 'h2_stuck_needle_probe.jsonl')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds', type=float, default=120)
    ap.add_argument('--note', default='')
    ap.add_argument('--all', action='store_true', help='every object carrying stuck needles, not only the player')
    ap.add_argument('--tags', default='', help='--all: only children of these tag datums (hex, comma-separated)')
    a = ap.parse_args(argv)
    pid = M.find_pid()
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    base, _ = M.module_base(pid, 'halo2.dll')
    if not (h and base):
        raise SystemExit('attach failed -- run elevated, with a level loaded')

    def rd(addr, n):
        return M.read(h, addr, n) or b''

    def q(addr):
        b = rd(addr, 8)
        return struct.unpack('<Q', b)[0] if len(b) == 8 else 0

    def u32(addr):
        b = rd(addr, 4)
        return struct.unpack('<I', b)[0] if len(b) == 4 else 0xFFFFFFFF

    def obj(datum):
        if datum == 0xFFFFFFFF:
            return 0
        tbl = q(base + 0x18B7398)
        off = struct.unpack('<i', rd(tbl + q(tbl + 0x48) + (datum & 0xFFFF) * 12 + 8, 4) or b'\0\0\0\0')[0]
        return ((q(base + 0x18B7360) + 0x57) & ~0xF) + off if off > 0 else 0

    def children(o):
        out, c, guard = [], u32(o + 0x10), 0
        while c != 0xFFFFFFFF and guard < 64:
            k = obj(c)
            if not k:
                break
            out.append((c, u32(k), u32(k + 0x130)))
            c, guard = u32(k + 0xC), guard + 1
        return out

    def all_objects(limit=4096):
        tbl = q(base + 0x18B7398)
        heap = (q(base + 0x18B7360) + 0x57) & ~0xF
        raw = rd(tbl + q(tbl + 0x48), limit * 12)
        for i in range(len(raw) // 12):
            salt, = struct.unpack_from('<H', raw, i * 12)
            off, = struct.unpack_from('<i', raw, i * 12 + 8)
            if salt and off > 0:
                yield (salt << 16) | i, heap + off

    def player_unit():
        players = q(base + 0xE80A28)
        if not players:
            return 0xFFFFFFFF
        return u32(players + q(players + 0x48) + 0x2C)

    last, t0, seen_max = None, time.time(), 0
    print('watching the player unit for %.0f s (stuck children every 20 ms) ...' % a.seconds, flush=True)
    if a.all:
        tags = {int(x, 16) for x in a.tags.split(',') if x.strip()}
        lastall = {}
        while time.time() - t0 < a.seconds:
            now = {}
            for d, o in all_objects():
                ks = [k for k in children(o) if k[2] != 0xFFFFFFFF and k[2] & 0x818 == 0x818
                      and (not tags or k[1] in tags)]
                if ks:
                    now[d] = tuple(ks)
            t = round(time.time() - t0, 2)
            for d in sorted(set(now) | set(lastall)):
                if now.get(d) != lastall.get(d):
                    ks = now.get(d, ())
                    print('%7.2f s  object %08X (tag %08X)  %d needles: %s' % (
                        t, d, u32(obj(d)) if obj(d) else 0, len(ks),
                        '  '.join('%08X fl %08X' % (k[0], k[2]) for k in ks)), flush=True)
                    with open(OUT, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({'t': t, 'object': '%08X' % d, 'mode': 'all', 'note': a.note,
                                            'needles': [{'datum': '%08X' % k[0], 'tag': '%08X' % k[1],
                                                         'flags130': '%08X' % k[2]} for k in ks]}) + '\n')
            lastall = now
            time.sleep(0.02)
        return
    while time.time() - t0 < a.seconds:
        ud = player_unit()
        u = obj(ud)
        kids = children(u) if u else []
        state = tuple(kids)
        if state != last:
            t = round(time.time() - t0, 2)
            row = {'t': t, 'unit': '%08X' % ud, 'unit_player_index': '%08X' % u32(u + 0xD4) if u else None,
                   'children': [{'datum': '%08X' % d, 'tag': '%08X' % tg, 'flags130': '%08X' % f}
                                for d, tg, f in kids]}
            print('%7.2f s  unit %08X  %d children: %s' % (
                t, ud, len(kids), '  '.join('%08X tag %08X fl %08X' % k for k in kids)), flush=True)
            last = state
            if len(kids) != seen_max or True:
                row.update(note=a.note, condition='live halo2.dll, player supercombine patch state per h2_supercombine_players show')
                with open(OUT, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(row) + '\n')
            seen_max = max(seen_max, len(kids))
        time.sleep(0.02)
    print('done; most children at once: %d (log %s)' % (seen_max, OUT))


if __name__ == '__main__':
    main()

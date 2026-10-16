r"""A CHARGE trigger's timeline from an h1_weapon_state_probe run, read-only (the Railgun + the halo1.dll charge
latch, C7 2026-10-16): fire presses / releases, trigger 0's STATE byte (+0x229: 0 idle, 2 charging, 3 charged,
4 recovering, 7 wait until let go), its FLAGS (+0x22C: bit 0 'up since the last shot', bit 7 the latch v2's 'just
discharged' marker; a shot clears bit 0), and the charge word +0xE4 (start / reset = the shot). Offsets from
h1_charge_latch.py's static reading; the slug fires where bit 0 clears.

    python h1_trigger_trace.py                 the last run in out/weapon_state_probe.jsonl
    python h1_trigger_trace.py --rows 1343     the last N rows (when the run's start is ambiguous)
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'out', 'weapon_state_probe.jsonl')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rows', type=int)
    ap.add_argument('--log', default=LOG)
    a = ap.parse_args()
    rows = []
    for l in open(a.log, encoding='utf-8'):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if 'ms' in r:
            rows.append(r)
    start = len(rows) - a.rows if a.rows else max(i for i, r in enumerate(rows) if r['ms'] < 1.0)
    rows = rows[start:]
    print('%d row(s)' % len(rows))
    fire, charge, state, flags = False, None, None, None
    for r in rows:
        t, ev = r['ms'] / 1000.0, []
        if bool(r.get('fire')) != fire:
            fire = bool(r.get('fire'))
            ev.append('PRESS' if fire else 'RELEASE')
        ch = r.get('ch', {})
        if '0e4' in ch:
            new = ch['0e4'][1]
            if charge is not None and charge > 0.9 and new < 0.5:
                ev.append('charge reset %.2f -> %.2f' % (charge, new))
            if (charge is None or charge < 0.05) and new >= 0.05:
                ev.append('charge starts')
            charge = new
        if '228' in ch:
            s = (int(ch['228'][2], 16) >> 8) & 0xFF
            if s != state:
                ev.append('state %s -> %d' % (state, s))
                state = s
        if '22c' in ch:
            f = int(ch['22c'][2], 16)
            if f != flags:
                ev.append('flags %s -> 0x%x%s' % (None if flags is None else hex(flags), f,
                                                  '  (SHOT: bit 0 cleared)' if flags is not None and flags & 1
                                                  and not f & 1 and fire else ''))
                flags = f
        for e in ev:
            print('%7.2f  %s' % (t, e))


if __name__ == '__main__':
    main()

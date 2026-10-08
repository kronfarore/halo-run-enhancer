r"""LIVE Halo 1 player shield + health, logged: how fast enemies actually hurt you.

WHY (2026-10-08, the Covenant Carbine's Armed test): a tag estimate of AI damage per
second needs a HIT FRACTION nobody can compute well (aim error, spread, projectile
speed against a strafing player). The user: measure in game first. Run A = stock Elites,
run B = the same Elites carrying a port (h1_port_test_map --armed elite --mortal); the
logged damage per second under fire gives the ratio a Weapon Damage Modifier rule needs.

HOW (one command, it walks you through it; reading only, the game is never written to):
  1. stand still at the level start -> every float triple near the scenario's starting
     location is a position candidate (player_pos.py's method)
  2. walk away a few metres -> keep only what MOVED with you (repeat until few are left)
  3. the Halo 1 object layout: position at +0x5C, health at +0xE0, shield at +0xE4 (both
     0..1, 1 = full; overshield above 1) -> read relative to each survivor; checked by
  4. taking one hit -> the shield must have dropped below 1
  5. sample at 20 Hz until Ctrl+C; every sample and a summary go to
     reports/h1_vitality_log.jsonl (memory halo-log-measured-values)

Summary: damage taken under fire (shield + health, in vitality points: the cyborg has 75
+ 75), seconds under fire (a sample is 'under fire' if a drop happened in the last 1 s),
damage per second under fire, shield breaks with their full -> 0 time, deaths.

    python h1_vitality_live.py --note "a30 run A, stock elite minors, legendary"
    python h1_vitality_live.py --start 31.65 -103.46 58.71     (another level's start)
"""
import argparse
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skull_diff as SD                                          # noqa: E402
import player_pos as PP                                          # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
LOG = os.path.join(OUT, 'h1_vitality_log.jsonl')
A30_START = (31.65, -103.46, 58.71)
POS, HEALTH, SHIELD = 0x5C, 0xE0, 0xE4        # Halo 1 object datum (CE layout, ASSUMED for MCC)
MAX_HEALTH = MAX_SHIELD = 75.0                # characters\cyborg collision model


def f32(h, addr):
    d = SD.read(h, addr, 4)
    return struct.unpack('<f', d)[0] if d and len(d) == 4 else None


def ask(msg):
    input('\n>>> ' + msg + '  [Enter] ')


def find_player(h, start):
    ask('Stand STILL near the level start (in game, with control)')
    cands = PP.scan(h, start, 20.0)
    print('   %d position candidate(s)' % len(cands))
    first = {a: PP.read_triple(h, a) for a in cands}
    while True:
        ask('WALK a few metres away and stand still')
        keep = {}
        for a, before in first.items():
            now = PP.read_triple(h, a)
            if now and before and max(abs(x - y) for x, y in zip(now, before)) > 1.5:
                keep[a] = now
        print('   %d candidate(s) moved with you' % len(keep))
        if not keep:
            raise SystemExit('nothing moved with you -- reload the level and start again')
        first = keep
        # the object datum: health + shield readable as 0..1 at their offsets
        objs = []
        for a in keep:
            hp, sh = f32(h, a - POS + HEALTH), f32(h, a - POS + SHIELD)
            if hp is not None and sh is not None and 0.0 <= hp <= 1.0 and 0.0 <= sh <= 3.0:
                objs.append((a - POS, hp, sh))
        print('   %d of them read a health/shield pair: %s'
              % (len(objs), ', '.join('0x%X (%.2f, %.2f)' % o for o in objs[:6])))
        if objs and len(objs) <= 6:
            return [o[0] for o in objs]
        print('   still too many -- walk somewhere else')


def confirm(h, objs):
    ask('Take ONE hit (any enemy) so the shield drops, then wait a moment')
    hit = [o for o in objs if (lambda v: v is not None and v < 0.999)(f32(h, o + SHIELD))]
    for o in objs:
        print('   object 0x%X  health %.3f  shield %.3f%s' % (o, f32(h, o + HEALTH), f32(h, o + SHIELD),
                                                          '  <- dropped' if o in hit else ''))
    if not hit:
        raise SystemExit('no candidate shield dropped -- the layout guess is wrong for MCC; '
                         'rerun, or extend this tool with a value scan')
    return hit[0]


def log(rec):
    os.makedirs(OUT, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')


def record(h, obj, note, hz):
    print('\nLOGGING at %d Hz -- fight now. Ctrl+C to stop.' % hz)
    run = time.strftime('%Y-%m-%d %H:%M:%S')
    samples, t0 = [], time.time()
    try:
        while True:
            t = time.time() - t0
            hp, sh = f32(h, obj + HEALTH), f32(h, obj + SHIELD)
            if hp is None or sh is None:
                print('\n   the object went away (death / level reload?)')
                break
            samples.append((round(t, 3), round(hp, 4), round(sh, 4)))
            print('   t %6.1f s  health %5.1f  shield %5.1f' % (t, hp * MAX_HEALTH, sh * MAX_SHIELD),
                  end='\r', flush=True)
            time.sleep(1.0 / hz)
    except KeyboardInterrupt:
        print()
    s = summary(samples)
    log({'when': run, 'kind': 'run', 'note': note, 'object': '0x%X' % obj, 'hz': hz,
         'summary': s, 'samples': samples})
    print('\nSUMMARY  %s' % note)
    for k, v in s.items():
        print('   %-26s %s' % (k, v))
    print('logged to %s' % LOG)


def summary(samples):
    lost, under, last_drop = 0.0, 0.0, None
    breaks, deaths, full_at = [], 0, None
    for (t0, h0, s0), (t1, h1, s1) in zip(samples, samples[1:]):
        d = max(0.0, s0 - s1) * MAX_SHIELD + max(0.0, h0 - h1) * MAX_HEALTH
        if h1 > h0 + 0.5:                    # respawn / reload: health jumped back
            deaths += 1
        if d > 0:
            lost += d
            last_drop = t1
        if last_drop is not None and t1 - last_drop <= 1.0:
            under += t1 - t0
        if s0 >= 0.999 and s1 < 0.999:
            full_at = t0
        if s0 > 0 and s1 <= 0 and full_at is not None:
            breaks.append(round(t1 - full_at, 2))
            full_at = None
    dur = samples[-1][0] if samples else 0
    return {'duration s': round(dur, 1), 'damage taken': round(lost, 1),
            'seconds under fire': round(under, 1),
            'damage / s under fire': round(lost / under, 2) if under else None,
            'shield breaks (full->0, s)': breaks, 'deaths': deaths}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--note', required=True, help='the CONDITION: level, run, enemies, difficulty')
    ap.add_argument('--start', type=float, nargs=3, default=A30_START, metavar=('X', 'Y', 'Z'))
    ap.add_argument('--hz', type=int, default=20)
    a = ap.parse_args()
    h = PP.attach()
    objs = find_player(h, tuple(a.start))
    obj = confirm(h, objs)
    log({'when': time.strftime('%Y-%m-%d %H:%M:%S'), 'kind': 'found', 'note': a.note,
         'object': '0x%X' % obj, 'layout': {'pos': POS, 'health': HEALTH, 'shield': SHIELD}})
    record(h, obj, a.note, a.hz)


if __name__ == '__main__':
    main()

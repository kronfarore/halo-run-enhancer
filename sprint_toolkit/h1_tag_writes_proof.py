r"""CLOSING CHECK 6 for a Halo 1 port (PORTING "What ported actually means"): every tag write proven.
Halo 1 has no XML export (kit_tag_diff), so this flattens tags with port_field_audit.flatten: snap
every tag the port's writers produce or touch, re-run the writers, diff -- a writer that reproduces its
own output changes nothing (the bitmaps' `base address` is tool's garbage pointer: reported apart).
Read-only itself (the writers are yours to re-run between snap and diff).

Tags: everything under the port's weapon folder (`.before_pickable` copies left out), the shared tags
h1_pickable_weapons writes (cyborg animations, hud_item_messages, hud_reticles / hud_msg_icons + _r), the
ten scenarios. Another session writing a shared tag in between shows as a change in ITS entries.

    python h1_tag_writes_proof.py suppressor snap
    python h1_h3_weapon_model.py suppressor & python h1_pickable_weapons.py --only suppressor --write
    python h1_tag_writes_proof.py suppressor diff
Written for the C2 Suppressor (2026-10-15: 54 tags, 1,036,348 fields, 4 changed = base addresses).
"""
import argparse
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_field_audit as A  # noqa: E402
import ports_h1  # noqa: E402

T = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
SHARED = [r'characters\cyborg\cyborg.model_animations', r'ui\hud\hud_item_messages.unicode_string_list',
          r'ui\hud\bitmaps\combined\hud_reticles.bitmap', r'ui\hud\bitmaps\combined\hud_reticles_r.bitmap',
          r'ui\hud\bitmaps\combined\hud_msg_icons.bitmap', r'ui\hud\bitmaps\combined\hud_msg_icons_r.bitmap']
NOISE = ('base address',)


def tags_of(key):
    P = dict(ports_h1.all_ports())[key]
    folder = (P.get('reservations') or {}).get('weapon_dir') or os.path.dirname(P['pickable']['weapon'])
    out = [os.path.relpath(p, T) for p in glob.glob(os.path.join(T, folder, '**', '*.*'), recursive=True)
           if not p.endswith(('.before_pickable', '.bisect'))]
    out += SHARED + [r'levels\%s\%s.scenario' % (lv, lv) for lv in LEVELS]
    return [t for t in out if os.path.exists(os.path.join(T, t))]


def flat(tags):
    out = {}
    for t in tags:
        try:
            out[t] = {k: repr(v) for k, v in A.flatten('HCEEK', t).items()}
        except Exception as e:       # a class flatten cannot read: its bytes instead
            out[t] = {'__sha1__': hashlib.sha1(open(os.path.join(T, t), 'rb').read()).hexdigest(),
                      '__why__': type(e).__name__}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('mode', choices=('snap', 'diff'))
    ap.add_argument('--file', help='snapshot file (default out\\tagproof_<port>.json)')
    a = ap.parse_args()
    path = a.file or os.path.join(HERE, 'out', 'tagproof_%s.json' % a.port)
    now = flat(tags_of(a.port))
    if a.mode == 'snap':
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(now, open(path, 'w'))
        print('snap: %d tags, %d fields -> %s' % (len(now), sum(len(v) for v in now.values()), path))
        return
    old = json.load(open(path))
    n = changed = noise = 0
    for t, f in now.items():
        o = old.get(t)
        if o is None:
            print('NEW TAG', t)
            continue
        for k in sorted(set(f) | set(o)):
            n += 1
            if f.get(k) == o.get(k):
                continue
            if any(x in k for x in NOISE):
                noise += 1
                continue
            changed += 1
            if changed <= 60:
                print('CHANGED %s :: %s  %s -> %s' % (t, k, str(o.get(k))[:60], str(f.get(k))[:60]))
    for t in old:
        if t not in now:
            print('GONE', t)
    print('diff: %d tags, %d fields, %d changed (+%d bitmap base addresses: tool noise)'
          % (len(now), n, changed, noise))


if __name__ == '__main__':
    main()

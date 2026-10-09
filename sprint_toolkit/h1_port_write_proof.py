r"""Closing check 6 for a HALO 1 port: every tag write is PROVEN.

Halo 1 has no XML export (kit_tag_diff), so the port's tags are flattened with
port_field_audit.flatten_h1: every tag under the port's weapon folder, the shared pickup
messages, the player biped's animations and the ten level scenarios (where the writer puts
the palette entry). `snap` saves that, the writer is re-run, `diff` compares -- 0 changed
means every value the config asks for is in the tags and the writer is idempotent.

Written for the Mauler (2026-10-09: 39 tags, 693,643 fields, 0 changed); the Spike Rifle did
the same by hand.

    python h1_port_write_proof.py brute_mauler snap out\proof_brute_mauler.json
    python h1_pickable_weapons.py --only brute_mauler --write
    python h1_port_write_proof.py brute_mauler diff out\proof_brute_mauler.json
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_field_audit as A  # noqa: E402
import ports_h1  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
LEVELS = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')


def tags_of(key):
    p = ports_h1.load(key)
    wdir = p['reservations']['weapon_dir']
    out = sorted(os.path.relpath(f, TAGS) for f in glob.glob(os.path.join(TAGS, wdir, '**', '*.*'), recursive=True)
                 if f.rsplit('.', 1)[-1] in A.H1_DEFS)
    out += [r'ui\hud\hud_item_messages.unicode_string_list', r'characters\cyborg\cyborg.model_animations']
    out += [r'levels\%s\%s.scenario' % (lv, lv) for lv in LEVELS]
    return out


def flatten(key):
    return {t: {k: str(v) for k, v in A.flatten_h1(t).items()} for t in tags_of(key)}


def main(key, mode, out):
    snap = flatten(key)
    if mode == 'snap':
        json.dump(snap, open(out, 'w', encoding='utf-8'), indent=0)
        print('%d tags, %d fields' % (len(snap), sum(len(v) for v in snap.values())))
        return
    old = json.load(open(out, encoding='utf-8'))
    n = changed = 0
    for t, fields in snap.items():
        for k, v in fields.items():
            n += 1
            if old.get(t, {}).get(k) != v:
                changed += 1
                if changed <= 20:
                    print('CHANGED %s  %s  %s -> %s' % (t, k, old.get(t, {}).get(k), v))
    print('%d tags, %d fields compared, %d changed' % (len(snap), n, changed))


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[2] not in ('snap', 'diff'):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])

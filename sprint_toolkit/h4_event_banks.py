r"""Which Halo 4 Wwise sound bank(s) hold each named EVENT (the Incineration Cannon, C9 2026-10-16: its projectile
bank is `proj_forerunner_incinerator`, a name no tag path suggests). Read-only.

Events are matched by FNV id in every bank of the live package (h4_wwise.BANKS); bank ids are named by trying
every bank string the H4EK .sound tags carry (an unnamed bank prints as its hex id).

    python h4_event_banks.py <event name> [<event name> ...]
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h4_wwise as W  # noqa: E402

H4_SOUND = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H4EK', 'tags', 'sound')


def main(events):
    ids = {W.fnv(e): e for e in events}
    p = W.read_pck(W.BANKS)
    names = set()
    for f in glob.glob(os.path.join(H4_SOUND, '**', '*.sound'), recursive=True):
        for x in re.findall(rb'([a-z0-9_]{4,})lbgt', open(f, 'rb').read()):
            names.add(x.decode())
    byid = {W.fnv(n): n for n in names}
    found = set()
    for bid, ent in p['banks'].items():
        try:
            objs = W.hirc(W.bank_bytes(W.BANKS, ent))
        except Exception:
            continue
        for t, oid, _d in objs:
            if t == 4 and oid in ids:            # 4 = an event
                print(ids[oid], '->', byid.get(bid, hex(bid)))
                found.add(oid)
    for oid, e in ids.items():
        if oid not in found:
            print(e, '-> in NO bank')


if __name__ == '__main__':
    main(sys.argv[1:])

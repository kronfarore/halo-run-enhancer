r"""Halo 4 SOUND RESEARCH for a port's step 10 -- read-only (the LightRifle, C4 2026-10-15; the Suppressor
found its drop event the same way, by hand). Three questions h4_wwise's extract does not answer:

  cues  <FP graph frame_event_list tag>     every animation's sound cues: frame offset, the .sound tag and
                                            its PLAYER event name (+ the event / fallback names) -- what a
                                            port's `sounds` entries and `offsets` come from
  event <event> [<event> ...]               which banks of sfxbank.pck hold each event (bank names by the
                                            FNV of H4EK's soundbank tag names) -- an event outside the
                                            weapon's player bank is `event@bank` in a port config
  tree  <bank> <hex object id> [...]        a HIRC container's children down to the sounds, depth-first by
                                            each node's PARENT link (the first container id in its body), with
                                            the source id and whether the bank / sfxstream holds its media --
                                            a fire event whose sounds sit behind a SWITCH (the LightRifle):
                                            pick the containers for h1_port_sounds `obj_<id>` specs

    python h4_sound_research.py cues "objects\characters\storm_fp\weapons\rifle\fp_forerunner_rifle\storm_fp_forerunner_rifle"
    python h4_sound_research.py event play_wea_drop_rifle_shotgun_nonplayer
    python h4_sound_research.py tree homing_rifle_player 2d68b28b

An event's own actions: `python h4_wwise.py --bank <bank> --event <event>` (targets named None live in
no bank of this package).
"""
import argparse
import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402
import h4_wwise as W  # noqa: E402

TYPES = {2: 'sound', 5: 'random/sequence', 6: 'switch', 7: 'actor-mixer', 9: 'blend'}


def bank_names():
    out = {}
    for f in glob.glob(os.path.join(h4_tags.H4EK, 'tags', 'sound', 'soundbanks', '**', '*.soundbank'),
                       recursive=True):
        n = os.path.splitext(os.path.basename(f))[0]
        out[W.fnv(n)] = n
    return out


def cues(rel):
    t = open(h4_tags.export_xml(rel + '.frame_event_list'), encoding='utf-8', errors='replace').read()
    refs = t[t.index('<block name="sound references"'):t.index('<block name="frame events"')]
    snds = re.findall(r'name="sound" value="([^"]*),snd!"', refs)
    events = {}
    for path in snds:
        try:
            st = open(h4_tags.export_xml(path + '.sound'), encoding='utf-8', errors='replace').read()
            ev = dict(re.findall(r'name="((?:Player |Fallback )?Event Name)" value="([^"]*)"', st))
            events[path] = ev.get('Player Event Name') or ev.get('Event Name') or '-'
        except SystemExit:
            events[path] = '(no H4EK .sound tag)'
    frames = t[t.index('<block name="frame events"'):]
    for anim in re.split(r'(?=<element index="\d+" name="[^"]*\(\d+ frames\)">)', frames)[1:]:
        name = re.search(r'name="animation name" value="([^"]*)"', anim).group(1)
        sb = re.search(r'<block name="sound events" count="(\d+)">(.*?)</block>', anim, re.S)
        if not sb or sb.group(1) == '0':
            continue
        for el in re.findall(r'<element index="\d+" name="\d+\. animation_sound_event_block_extended">(.*?)</element>',
                             sb.group(2), re.S):
            idx = int(re.search(r'name="sound" value=",(-?\d+)"', el).group(1))
            off = re.search(r'name="frame offset" value="(-?\d+)"', el)
            path = snds[idx] if 0 <= idx < len(snds) else '-'
            print('%-34s @%3s  %-70s %s' % (name, off.group(1) if off else '0', path.rsplit('\\', 1)[-1],
                                           events.get(path, '-')))


def event(names):
    bn = bank_names()
    want = {W.fnv(e): e for e in names}
    pck = W.read_pck(W.BANKS)
    found = set()
    for bid, ent in pck['banks'].items():
        for t, oid, _d in W.hirc(W.bank_bytes(W.BANKS, ent)):
            if t == 4 and oid in want:
                print('%-60s @ %s' % (want[oid], bn.get(bid, hex(bid))))
                found.add(oid)
    for oid, e in want.items():
        if oid not in found:
            print('%-60s   in NO bank of sfxbank.pck' % e)


def tree(bank, ids):
    pck, st = W.read_pck(W.BANKS), W.read_pck(W.STREAMS)
    b = W.bank_bytes(W.BANKS, pck['banks'][W.fnv(bank)])
    objs = W.hirc(b)
    byid = {o: (t, d) for t, o, d in objs}
    c = W.chunks(b)
    didx = set()
    if 'DIDX' in c:
        at, n = c['DIDX']
        didx = {struct.unpack_from('<I', b, at + i * 12)[0] for i in range(n // 12)}
    containers = {o for t, o, _d in objs if t in (5, 6, 7, 9)}
    kids = {}
    for t, o, d in objs:
        if t in (2, 5, 6, 9):
            for i in range(len(d) - 3):
                v = struct.unpack_from('<I', d, i)[0]
                if v in containers and v != o:
                    kids.setdefault(v, []).append(o)
                    break

    def show(o, depth):
        t, d = byid[o]
        extra = ''
        if t == 2:
            src = struct.unpack_from('<I', d, 8)[0]
            where = 'bank' if src in didx else 'stream' if src in st['streams'] else 'MISSING'
            extra = '  src %#x (%s)' % (src, where)
        print('%s%#x %s%s' % ('  ' * depth, o, TYPES.get(t, t), extra))
        for k in kids.get(o, ()):
            show(k, depth + 1)
    for x in ids:
        o = int(x, 16)
        if o not in byid:
            print('%#x: not in %s' % (o, bank))
            continue
        show(o, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('cues', 'event', 'tree'))
    ap.add_argument('args', nargs='+')
    a = ap.parse_args()
    if a.verb == 'cues':
        cues(a.args[0])
    elif a.verb == 'event':
        event(a.args)
    else:
        tree(a.args[0], a.args[1:])


if __name__ == '__main__':
    main()

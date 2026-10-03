r"""Read Halo 4's Wwise sound data (MCC: halo4\sound\pc\sfxbank.pck / sfxstream.pck).

RESEARCH TOOL for porting a weapon's sounds INTO Halo 4 (step: firing sound). Halo 4's
sound tags hold no audio: a .sound tag names a Wwise EVENT and a .soundbank tag naming a
BANK; the game hashes both names (Wwise FNV-1, lower case) and finds the bank in the AKPK
package by that id.

    python h4_wwise.py --bank sentinel                 bank entry + HIRC summary
    python h4_wwise.py --event play_wea_sentinel_friendly_beam_fire_in --bank sentinel
"""
import argparse
import os
import struct
import sys

MCC = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
BANKS = os.path.join(MCC, 'halo4', 'sound', 'pc', 'sfxbank.pck')
STREAMS = os.path.join(MCC, 'halo4', 'sound', 'pc', 'sfxstream.pck')
HIRC_TYPES = {1: 'settings', 2: 'sound', 3: 'action', 4: 'event', 5: 'random/sequence',
              6: 'switch', 7: 'actor-mixer', 8: 'bus', 9: 'blend', 10: 'music segment',
              11: 'music track', 12: 'music switch', 13: 'music playlist', 14: 'attenuation',
              15: 'dialogue event', 16: 'motion bus', 17: 'motion fx', 18: 'effect',
              19: 'unknown19', 20: 'aux bus'}


def fnv(name):
    """Wwise short id: FNV-1 32 over the lower-case name."""
    h = 2166136261
    for c in name.lower().encode():
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= c
    return h


def read_pck(path):
    """{'langs': {id: name}, 'banks': {id: (block, size, start, lang)}, 'streams': {...}}"""
    with open(path, 'rb') as f:
        hd = f.read(0x1C)
        magic, hsz, ver, lsz, bsz, ssz, xsz = struct.unpack('<4sIIIIII', hd)
        if magic != b'AKPK':
            raise SystemExit('%s is not an AKPK package' % path)
        body = f.read(hsz + 8 - 0x1C)
    lang = body[:lsz]
    langs = {}
    for i in range(struct.unpack_from('<I', lang, 0)[0]):
        off, lid = struct.unpack_from('<II', lang, 4 + i * 8)
        e = off
        while lang[e:e + 2] != b'\0\0':
            e += 2
        langs[lid] = lang[off:e].decode('utf-16-le')

    def lut(blob):
        out = {}
        if len(blob) < 4:
            return out
        for i in range(struct.unpack_from('<I', blob, 0)[0]):
            bid, blk, size, start, lg = struct.unpack_from('<IIIII', blob, 4 + i * 20)
            out[bid] = (blk, size, start, lg)
        return out
    return {'version': ver, 'header': hsz + 8, 'langs': langs,
            'banks': lut(body[lsz:lsz + bsz]), 'streams': lut(body[lsz + bsz:lsz + bsz + ssz])}


def bank_bytes(path, entry):
    blk, size, start, _lg = entry
    with open(path, 'rb') as f:
        f.seek(start * blk)
        return f.read(size)


def chunks(bank):
    out, i = {}, 0
    while i + 8 <= len(bank):
        tag, n = bank[i:i + 4].decode('latin-1'), struct.unpack_from('<I', bank, i + 4)[0]
        out[tag] = (i + 8, n)
        i += 8 + n
    return out


def hirc(bank):
    c = chunks(bank)
    if 'HIRC' not in c:
        return []
    at, _n = c['HIRC']
    count = struct.unpack_from('<I', bank, at)[0]
    i, objs = at + 4, []
    for _ in range(count):
        t = bank[i]
        size, oid = struct.unpack_from('<II', bank, i + 1)
        objs.append((t, oid, bank[i + 9:i + 5 + size]))
        i += 5 + size
    return objs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bank')
    ap.add_argument('--event')
    a = ap.parse_args()
    p = read_pck(BANKS)
    s = read_pck(STREAMS)
    print('sfxbank.pck: version %d, %d banks, languages %s; sfxstream.pck: %d banks, %d streams'
          % (p['version'], len(p['banks']), p['langs'], len(s['banks']), len(s['streams'])))
    if not a.bank:
        return
    bid = fnv(a.bank)
    ent = p['banks'].get(bid)
    print('bank %r id %#010x -> %s' % (a.bank, bid, ent))
    if not ent:
        return
    b = bank_bytes(BANKS, ent)
    c = chunks(b)
    bkhd = struct.unpack_from('<II', b, c['BKHD'][0])
    print('chunks', {k: v[1] for k, v in c.items()}, 'BKHD version %d id %#x' % bkhd)
    objs = hirc(b)
    from collections import Counter
    print('HIRC', len(objs), dict(Counter(HIRC_TYPES.get(t, t) for t, _i, _d in objs)))
    if a.event:
        eid = fnv(a.event)
        byid = {oid: (t, d) for t, oid, d in objs}
        print('event %r id %#010x in bank: %s' % (a.event, eid, eid in byid))
        if eid in byid:
            _t, d = byid[eid]
            n = struct.unpack_from('<I', d, 0)[0]
            acts = struct.unpack_from('<%dI' % n, d, 4)
            for aid in acts:
                at, ad = byid.get(aid, (None, b''))
                atype = struct.unpack_from('<H', ad, 0)[0] if ad else None
                target = struct.unpack_from('<I', ad, 2)[0] if ad else None
                tt = byid.get(target, (None,))[0]
                print('  action %#x type %#06x -> target %#x (%s)' % (aid, atype or 0, target or 0,
                                                                     HIRC_TYPES.get(tt, tt)))


VGM = r'F:\Tools\vgmstream\vgmstream-cli.exe'


def event_sounds(bank, objs, event_id):
    """[(action type, sound id, play|stop)] an event reaches: its actions' targets, and a
    container's child sounds (ids found in the container body -- v88 packs its fields)."""
    byid = {oid: (t, d) for t, oid, d in objs}
    sounds = {oid for t, oid, _d in objs if t == 2}
    out = []
    if event_id not in byid:
        return out
    d = byid[event_id][1]
    n = struct.unpack_from('<I', d, 0)[0]
    for aid in struct.unpack_from('<%dI' % n, d, 4):
        _at, ad = byid.get(aid, (None, b''))
        if not ad:
            continue
        kind, tgt = struct.unpack_from('<HI', ad, 0)
        verb = 'play' if kind == 0x0403 else 'stop' if kind >> 8 == 0x01 else '%#06x' % kind
        if tgt in sounds:
            out.append((verb, tgt))
        elif tgt in byid:
            body = byid[tgt][1]
            kids = [v for v in (struct.unpack_from('<I', body, i)[0] for i in range(len(body) - 3))
                    if v in sounds]
            out += [(verb, k) for k in dict.fromkeys(kids)]
    return out


def media_of(bank, objs, sound_id, streams):
    """(bytes of the sound's media, stream type) -- embedded in DATA or in sfxstream.pck."""
    d = {oid: dd for t, oid, dd in objs}[sound_id]
    plug, stype, src, fid = struct.unpack_from('<IIII', d, 0)
    if stype == 0:
        off, size = struct.unpack_from('<II', d, 16)
        return bank[off:off + size], stype, plug
    ent = streams['streams'].get(src)
    if not ent:
        return None, stype, plug
    blk, size, start, _lg = ent
    with open(STREAMS, 'rb') as f:
        f.seek(start * blk)
        return f.read(size), stype, plug


def extract(bank_name, events, out_dir):
    """Decode every sound the named events PLAY to WAV: <out>/<event>/<n>_<sound id>.wav"""
    import subprocess
    p, s = read_pck(BANKS), read_pck(STREAMS)
    b = bank_bytes(BANKS, p['banks'][fnv(bank_name)])
    objs = hirc(b)
    done = 0
    for ev in events:
        hits = [(v, sid) for v, sid in event_sounds(b, objs, fnv(ev)) if v == 'play']
        if not hits:
            print('   %-48s (not in %s or plays nothing)' % (ev, bank_name))
            continue
        os.makedirs(os.path.join(out_dir, ev), exist_ok=True)
        for k, (_v, sid) in enumerate(hits):
            blob, stype, plug = media_of(b, objs, sid, s)
            if not blob:
                print('   %-48s sound %#x: media not found' % (ev, sid))
                continue
            wem = os.path.join(out_dir, ev, '%d_%08x.wem' % (k, sid))
            open(wem, 'wb').write(blob)
            wav = wem[:-4] + '.wav'
            subprocess.run([VGM, '-o', wav, wem], capture_output=True)
            os.remove(wem)
            done += os.path.exists(wav)
        print('   %-48s %d sound(s)' % (ev, len(hits)))
    return done


if __name__ == '__main__':
    if '--extract' in sys.argv:
        # python h4_wwise.py --extract <bank> <out dir> <event> [<event> ...]
        i = sys.argv.index('--extract')
        bank_name, out = sys.argv[i + 1], sys.argv[i + 2]
        n = extract(bank_name, sys.argv[i + 3:], out)
        print('%d wav(s) -> %s' % (n, out))
    else:
        main()

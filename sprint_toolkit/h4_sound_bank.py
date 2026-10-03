r"""Halo 4 port, sound: the Focus Rifle's OWN Wwise bank, built from the Sentinel bank.

Test 1 (h4_sound_test.py, boot 30) proved the chain in game: Reach's audio as PCM WEM in
a rebuilt v88 bank, read from sfxbank.pck, played by a looping sound attached to the
weapon. That test lived INSIDE the Sentinel's bank. This builds the port's own:

  * a full copy of the sentinel bank (43 HIRC objects, 15 media) with EVERY internal id
    renamed -- objects, media and the bank id -- so it never collides with the real
    sentinel bank when both are loaded. The two events the port uses get readable names:
        play_wea_port_focus_rifle_fire_in   start one-shot + loop   (was ..._sentinel_friendly_beam_fire_in)
        stop_wea_port_focus_rifle_fire      stop loop + tail        (was stop_wea_sentinel_friendly_beam_fire)
    every other id becomes fnv('port_focus_rifle/<old id>'). Ids from OUTSIDE the bank
    (buses, the mixer's parent, RTPCs) are left alone.
    Renaming is a byte replacement over the object bodies: v88 packs its fields, so ids
    sit at odd offsets; measured on the sentinel bank, every hit is a real reference.
  * the three media the events play replaced by Reach's 3p firing set (in / loop / out,
    sfx.fsb 10952-10954) as PCM, those sound objects switched to PCM.
Bank name `port_focus_rifle` (id 0xb4d927ce, free in sfxbank.pck).

Output: tool\port_sounds\halo4\port_focus_rifle.bnk -- installed into the live
sfxbank.pck by tool\port_sounds.py (patch time / by hand), the way port_glyphs.py
handles the icon fonts.

    python h4_sound_bank.py           build + verify, write the .bnk
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_sound_test as t                                          # noqa: E402
import h4_wwise as w                                               # noqa: E402

SOURCE_BANK = 'sentinel'
BANK = 'port_focus_rifle'
EVENTS = {'play_wea_sentinel_friendly_beam_fire_in': 'play_wea_port_focus_rifle_fire_in',
          'stop_wea_sentinel_friendly_beam_fire': 'stop_wea_port_focus_rifle_fire'}
#: OLD sentinel sound object -> Reach wav (as in test 1)
REPLACE = {0x090ac918: '10952_in.wav', 0x392e4cf5: '10953_loop.wav', 0x290e3e3c: '10954_out.wav'}
OUT_DIR = os.path.join(os.path.dirname(HERE), 'port_sounds', 'halo4')
#: the stock package, so a build never starts from an installed port bank
STOCK_PCK = r'F:\HaloPortBackups\h4_sound_stock\sfxbank.pck'


def renaming(bank):
    """old id -> new id for every id the bank OWNS."""
    objs = t.objects(bank)
    c = w.chunks(bank)
    di, dn = c['DIDX']
    old = [oid for _t, oid, _a, _e in objs]
    old += [struct.unpack_from('<I', bank, di + k * 12)[0] for k in range(dn // 12)]
    m = {w.fnv(SOURCE_BANK): w.fnv(BANK)}
    named = {w.fnv(a): w.fnv(b) for a, b in EVENTS.items()}
    for o in old:
        m[o] = named.get(o, w.fnv('%s/%08x' % (BANK, o)))
    if len(set(m.values())) != len(m):
        raise SystemExit('renaming collides with itself')
    return m


def rename(bank, m):
    """The bank with every owned id replaced: BKHD bank id, DIDX media ids, HIRC object
    ids (headers) and every reference inside the object bodies."""
    out = bytearray(bank)
    c = w.chunks(bank)
    bk = c['BKHD'][0]
    struct.pack_into('<I', out, bk + 4, m[struct.unpack_from('<I', bank, bk + 4)[0]])
    di, dn = c['DIDX']
    for k in range(dn // 12):
        at = di + k * 12
        struct.pack_into('<I', out, at, m[struct.unpack_from('<I', bank, at)[0]])
    hits = 0
    for _ty, oid, a, e in t.objects(bank):
        struct.pack_into('<I', out, a - 4, m[oid])            # the header id
        i = a
        while i + 4 <= e:
            v = struct.unpack_from('<I', bank, i)[0]
            if v in m:
                struct.pack_into('<I', out, i, m[v])
                hits += 1
                i += 4
            else:
                i += 1
    return bytes(out), hits


def check_events(bank):
    """Each named event must reach PCM sound objects whose media sit in this bank."""
    objs = {oid: (ty, a, e) for ty, oid, a, e in t.objects(bank)}
    c = w.chunks(bank)
    di, dn = c['DIDX']
    media = {struct.unpack_from('<I', bank, di + k * 12)[0] for k in range(dn // 12)}
    ok = True
    for name in EVENTS.values():
        eid = w.fnv(name)
        if eid not in objs:
            print('   MISSING event %s' % name)
            ok = False
            continue
        _ty, a, _e = objs[eid]
        n = struct.unpack_from('<I', bank, a)[0]
        for aid in struct.unpack_from('<%dI' % n, bank, a + 4):
            _aty, aa, _ae = objs[aid]
            kind, tgt = struct.unpack_from('<HI', bank, aa)
            ty, ta, _te = objs.get(tgt, (None, 0, 0))
            desc = w.HIRC_TYPES.get(ty, ty)
            if ty == 2:
                plug, _st, src = struct.unpack_from('<III', bank, ta)
                desc += ' %s media %s' % ('PCM' if plug == t.PCM else hex(plug),
                                          'in bank' if src in media else 'MISSING')
                ok &= src in media
            print('   %-36s action %#06x -> %#010x %s' % (name, kind, tgt, desc))
    return ok


def main():
    stock = w.bank_bytes(STOCK_PCK, w.read_pck(STOCK_PCK)['banks'][w.fnv(SOURCE_BANK)])
    m = renaming(stock)
    renamed, hits = rename(stock, m)
    print('renamed %d ids (%d references in object bodies); bank %#x -> %#x'
          % (len(m), hits, w.fnv(SOURCE_BANK), w.fnv(BANK)))
    # the media swap of test 1, on the renamed sound objects
    t.REPLACE = {m[k]: v for k, v in REPLACE.items()}
    bank, report = t.build(renamed)
    for oid, wav, was, now in report:
        print('   sound %#010x: %d bytes Vorbis -> %d bytes PCM (%s)' % (oid, was, now, wav))
    if not t.verify(bank):
        raise SystemExit('media verification failed')
    if not check_events(bank):
        raise SystemExit('event check failed')
    # nothing of the sentinel's own ids may survive in the new bank's HIRC/DIDX headers
    left = [o for o in m if any(struct.pack('<I', o) in bank[a - 4:e]
                                for _t, _o, a, e in t.objects(bank))]
    if left:
        raise SystemExit('old ids still referenced: %s' % [hex(x) for x in left[:8]])
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, BANK + '.bnk')
    open(path, 'wb').write(bank)
    json.dump({'bank': BANK, 'bank_id': w.fnv(BANK), 'events': list(EVENTS.values()),
               'source': 'Reach focus_rifle 3p firing set (sfx.fsb 10952-10954) as PCM, in a '
                         'renamed copy of the Halo 4 sentinel bank',
               'bytes': len(bank)},
              open(os.path.join(OUT_DIR, BANK + '.json'), 'w'), indent=1)
    print('wrote %s (%d bytes)' % (path, len(bank)))


if __name__ == '__main__':
    main()

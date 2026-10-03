r"""Halo 4 sound, TEST 1: Reach's Focus Rifle firing audio inside the SENTINEL bank.

The port fires the Sentinel friendly-beam effect, whose sound is the sentinel bank's
    play_wea_sentinel_friendly_beam_fire_in  -> start one-shot (random container) + LOOP
    stop_wea_sentinel_friendly_beam_fire     -> stop the loop + TAIL
This rebuilds that bank with the three media replaced by Reach's 3p firing set
(sfx.fsb subsongs 10952 in / 10953 loop / 10954 out, decoded with vgmstream) written as
PCM WEM -- the codec 641 shipped Halo 4 sounds use, and the only one writable without
Wwise -- and the three sound objects switched from Vorbis to PCM. The bank is APPENDED
to sfxbank.pck and its LUT entry (20 bytes in the header) repointed; nothing else in the
400 MB package changes. Every other sound in the bank is untouched.

Side effect while installed: friendly Sentinels' beams sound like the Focus Rifle too.

    python h4_sound_test.py              build + verify offline (no game file touched)
    python h4_sound_test.py --install    append + repoint (backs up the entry first)
    python h4_sound_test.py --restore    put the entry back, truncate the package

Stock package backup: F:\HaloPortBackups\h4_sound_stock\sfxbank.pck (sha1 c63d37be...).
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_wwise as w                                               # noqa: E402

SOUNDS = r'F:\SteamLibrary\steamapps\common\H4EK\temp\focus_rifle_sounds'
VGM = r'F:\Tools\vgmstream\vgmstream-cli.exe'
OUT = r'F:\SteamLibrary\steamapps\common\H4EK\temp\focus_rifle_bank'
RESTORE = r'F:\HaloPortBackups\h4_sound_stock\sound_test_restore.json'
BANK = 'sentinel'
PCM = 0x00010001
#: sound object id -> Reach wav: (Sentinel role)
REPLACE = {
    0x090ac918: '10952_in.wav',      # start one-shot (fire_in's random container)
    0x392e4cf5: '10953_loop.wav',    # the loop (stopped by stop_..._fire)
    0x290e3e3c: '10954_out.wav',     # the tail
}


def wem_pcm(wav_path):
    """A Wwise PCM WEM from a 16-bit WAV, laid out like the shipped ones: RIFF/WAVE,
    fmt (0xFFFE, 24 bytes: ..., cbSize 6, u16 0, u32 channel mask), JUNK 4, data."""
    with wave.open(wav_path, 'rb') as r:
        ch, sw, rate, n = r.getnchannels(), r.getsampwidth(), r.getframerate(), r.getnframes()
        pcm = r.readframes(n)
    if sw != 2:
        raise SystemExit('%s: not 16-bit' % wav_path)
    mask = {1: 0x4, 2: 0x3}[ch]
    fmt = struct.pack('<HHIIHHHHI', 0xFFFE, ch, rate, rate * ch * 2, ch * 2, 16, 6, 0, mask)
    body = (b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt +
            b'JUNK' + struct.pack('<I', 4) + b'\0' * 4 +
            b'data' + struct.pack('<I', len(pcm)) + pcm)
    return b'RIFF' + struct.pack('<I', len(body)) + body


def objects(bank):
    """[(type, id, data offset, data end)] of the HIRC, as absolute offsets."""
    at, _n = w.chunks(bank)['HIRC']
    count = struct.unpack_from('<I', bank, at)[0]
    i, out = at + 4, []
    for _ in range(count):
        t = bank[i]
        size, oid = struct.unpack_from('<II', bank, i + 1)
        out.append((t, oid, i + 9, i + 5 + size))
        i += 5 + size
    return out


def build(stock):
    """The sentinel bank with REPLACE's media swapped. Returns (bytes, media report)."""
    c = w.chunks(stock)
    order = ('BKHD', 'DIDX', 'DATA', 'HIRC')
    if list(c) != list(order):
        raise SystemExit('unexpected chunk order %s' % list(c))
    da, _dn = c['DATA']
    di, dn = c['DIDX']
    media = []
    for k in range(dn // 12):
        mid, off, size = struct.unpack_from('<III', stock, di + k * 12)
        media.append([mid, stock[da + off:da + off + size]])
    objs = objects(stock)
    src_of = {}
    for t, oid, a, _e in objs:
        if t == 2 and oid in REPLACE:
            src_of[oid] = struct.unpack_from('<I', stock, a + 8)[0]
    if set(src_of) != set(REPLACE):
        raise SystemExit('the bank lacks sound objects %s' % [hex(x) for x in set(REPLACE) - set(src_of)])
    report = []
    for oid, wav in REPLACE.items():
        new = wem_pcm(os.path.join(SOUNDS, wav))
        for m in media:
            if m[0] == src_of[oid]:
                report.append((oid, wav, len(m[1]), len(new)))
                m[1] = new
    # DATA: media back to back, each start 16-aligned (as shipped)
    data, didx, pos = bytearray(), bytearray(), 0
    for mid, blob in media:
        pos += -pos % 16
        data += b'\0' * (pos - len(data))
        didx += struct.pack('<III', mid, pos, len(blob))
        data += blob
        pos = len(data)
    bkhd = stock[c['BKHD'][0] - 8:c['BKHD'][0] + c['BKHD'][1]]
    hirc = bytearray(stock[c['HIRC'][0] - 8:c['HIRC'][0] + c['HIRC'][1]])
    head = len(bkhd) + 8 + len(didx) + 8            # where DATA's payload starts
    where = {mid: (off, size) for mid, off, size in struct.iter_unpack('<III', bytes(didx))}
    base = c['HIRC'][0] - 8
    for t, oid, a, _e in objs:
        if t != 2:
            continue
        a -= base
        plug, stype, src = struct.unpack_from('<III', hirc, a)
        if stype != 0 or src not in where:
            continue
        off, size = where[src]
        if oid in REPLACE:
            struct.pack_into('<I', hirc, a, PCM)
        struct.pack_into('<II', hirc, a + 16, head + off, size)
    out = bkhd + b'DIDX' + struct.pack('<I', len(didx)) + bytes(didx) + \
        b'DATA' + struct.pack('<I', len(data)) + bytes(data) + bytes(hirc)
    return out, report


def verify(bank):
    """Every replaced medium must decode (vgmstream) to the source length; the HIRC must
    still parse with every embedded sound pointing inside DATA."""
    os.makedirs(OUT, exist_ok=True)
    c = w.chunks(bank)
    da, dn = c['DATA']
    di, didn = c['DIDX']
    where = {}
    for k in range(didn // 12):
        mid, off, size = struct.unpack_from('<III', bank, di + k * 12)
        where[mid] = (off, size)
    ok = True
    for t, oid, a, _e in objects(bank):
        if t != 2:
            continue
        plug, stype, src, _fid, off, size = struct.unpack_from('<IIIIII', bank, a)
        if stype == 0 and (off != da + where[src][0] or size != where[src][1]):
            print('   BAD sound %#x points at %d+%d, media at %d' % (oid, off, size, da + where[src][0]))
            ok = False
        if oid in REPLACE:
            f = os.path.join(OUT, '%08x.wem' % oid)
            open(f, 'wb').write(bank[off:off + size])
            r = subprocess.run([VGM, '-m', f], capture_output=True, text=True).stdout
            got = [l for l in r.splitlines() if 'play duration' in l or 'encoding' in l]
            with wave.open(os.path.join(SOUNDS, REPLACE[oid])) as src_w:
                want = src_w.getnframes()
            good = ('%d samples' % want) in r and 'PCM' in r
            ok &= good
            print('   sound %#x %s codec %s: %s' % (oid, REPLACE[oid], 'PCM' if plug == PCM else hex(plug),
                                                   '; '.join(x.strip() for x in got)))
    return ok


def lut_entry_offset(path, bank_id):
    """Byte offset of a bank's 20-byte entry in the package header."""
    with open(path, 'rb') as f:
        hd = f.read(0x1C)
        _m, _h, _v, lsz, bsz, _s, _x = struct.unpack('<4sIIIIII', hd)
        lut = (f.seek(0x1C + lsz), f.read(bsz))[1]
    for k in range(struct.unpack_from('<I', lut, 0)[0]):
        if struct.unpack_from('<I', lut, 4 + k * 20)[0] == bank_id:
            return 0x1C + lsz + 4 + k * 20
    raise SystemExit('bank %#x not in the package' % bank_id)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    bid = w.fnv(BANK)
    if a.restore:
        r = json.load(open(RESTORE))
        with open(w.BANKS, 'r+b') as f:
            f.seek(r['entry_at'])
            f.write(bytes.fromhex(r['entry']))
            f.truncate(r['size'])
        print('restored the %s entry and truncated to %d bytes' % (BANK, r['size']))
        return
    pck = w.read_pck(w.BANKS)
    stock = w.bank_bytes(w.BANKS, pck['banks'][bid])
    bank, report = build(stock)
    for oid, wav, was, now in report:
        print('   sound %#x: %d bytes Vorbis -> %d bytes PCM (%s)' % (oid, was, now, wav))
    print('bank %d -> %d bytes' % (len(stock), len(bank)))
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'sentinel_test.bnk'), 'wb').write(bank)
    if not verify(bank):
        raise SystemExit('verification failed; nothing installed')
    print('verified offline')
    if not a.install:
        print('(dry run -- pass --install)')
        return
    if os.path.exists(RESTORE):
        raise SystemExit('a test is already installed (%s); --restore first' % RESTORE)
    at = lut_entry_offset(w.BANKS, bid)
    size = os.path.getsize(w.BANKS)
    with open(w.BANKS, 'r+b') as f:
        f.seek(at)
        entry = f.read(20)
        json.dump({'entry_at': at, 'entry': entry.hex(), 'size': size}, open(RESTORE, 'w'))
        f.seek(size)
        f.write(bank)
        blk = struct.unpack_from('<I', entry, 4)[0]
        if blk != 1:
            raise SystemExit('block size %d, expected 1' % blk)
        f.seek(at)
        f.write(struct.pack('<IIIII', bid, 1, len(bank), size, struct.unpack_from('<I', entry, 16)[0]))
    check = w.read_pck(w.BANKS)['banks'][bid]
    back = w.bank_bytes(w.BANKS, check)
    print('installed: entry %s -> %s; reads back %s' % (struct.unpack('<IIIII', entry)[1:],
                                                        check, 'identical' if back == bank else 'DIFFERENT'))


if __name__ == '__main__':
    main()

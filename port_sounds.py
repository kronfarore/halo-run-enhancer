r"""Put the weapon ports' own Wwise sound banks into Halo 4's live sound package -- on any
machine. The sound counterpart of port_glyphs.py.

WHY: Halo 4 reads every sound bank from ONE package, `halo4\sound\pc\sfxbank.pck` (AKPK:
a header with a bank table sorted by bank id -- id, block size 1, size, byte offset,
language -- then the banks). A map rebuild never touches it; a Steam update or "verify"
restores the stock file; a co-op partner's install never had the port's bank.

WHAT IT CARRIES: `port_sounds\<game>\*.bnk`, finished banks built by the port tools
(sprint_toolkit\h4_sound_bank.py). Standard library only.

HOW: a missing bank gets a NEW table entry, inserted in id order; the header grows by 20
bytes per entry, so every existing bank's offset moves by that much; the banks follow
unchanged and the new ones are appended at the end. A bank already present with the same
bytes is left alone; one present with OTHER bytes is replaced (its old bytes are dropped
when they are the file's tail, else left unreferenced). The package is written to a temp
file and swapped in, then read back. Proven in game (2026-10-03, boot 30): a bank
APPENDED to the package and named by its table entry plays.

HALO 1 TOO (2026-10-04): MCC plays Halo 1 sounds from the classic FMOD bank
sounds_adpcm.fsb, by tag path -- see h1_ensure(); port_sounds\halo1 carries the audio.

FOR THE ENHANCER (patch time, Halo 4 and Halo 1):
    import port_sounds
    rows = port_sounds.ensure('halo4', mcc_root())       # patcher-style rows
    rows = port_sounds.ensure('halo4', mcc_root(), volume={'Focus Rifle': -3.0})
                                   # per-port volume knob, dB relative to the bank as built
                                   # (port_volume.bank_volume: the root mixer's Volume)
    problems = port_sounds.problems(mcc_root())           # validator messages
A frozen build needs datas += [('port_sounds', 'port_sounds')] in halo_enhancer.spec.

COMMAND LINE (cmd.exe):
    python port_sounds.py              report
    python port_sounds.py --write      install missing banks
    python port_sounds.py --check      validator: exit 1 if a bank is missing
"""
import argparse
import glob
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = 'port_sounds'
PACKAGES = {'halo4': os.path.join('halo4', 'sound', 'pc', 'sfxbank.pck'),
            'halo1': os.path.join('halo1', 'sound', 'pc', 'sounds_adpcm.fsb')}
CHUNK = 1 << 24


def _data_dir():
    for d in (HERE, getattr(sys, '_MEIPASS', '')):
        p = os.path.join(d, DATA)
        if d and os.path.isdir(p):
            return p
    return os.path.join(HERE, DATA)


def banks(game, volume=None):
    """[(bank id, bytes, file name)] the ports carry for `game`; `volume` {port: dB}
    shifts a port's bank (port_volume.PORT_BANKS names which file is whose)."""
    out = []
    shift = {}
    if volume:
        import port_volume
        shift = {f.lower(): volume[w] for w, (g, f) in port_volume.PORT_BANKS.items()
                 if g == game and volume.get(w)}
    for p in sorted(glob.glob(os.path.join(_data_dir(), game, '*.bnk'))):
        b = open(p, 'rb').read()
        if b[:4] != b'BKHD':
            continue
        if shift.get(os.path.basename(p).lower()):
            import port_volume
            b = port_volume.bank_volume(b, shift[os.path.basename(p).lower()])[0]
        out.append((struct.unpack_from('<I', b, 12)[0], b, os.path.basename(p)))
    return out


def read_header(f):
    """(header bytes, fields, bank table {id: (blk, size, start, lang)} in file order)"""
    f.seek(0)
    hd = f.read(0x1C)
    magic, hsz, ver, lsz, bsz, ssz, xsz = struct.unpack('<4sIIIIII', hd)
    if magic != b'AKPK':
        raise ValueError('not an AKPK package')
    rest = f.read(hsz + 8 - 0x1C)
    lut = rest[lsz:lsz + bsz]
    n = struct.unpack_from('<I', lut, 0)[0]
    table = [struct.unpack_from('<IIIII', lut, 4 + i * 20) for i in range(n)]
    return hd + rest, (hsz, ver, lsz, bsz, ssz, xsz), table


def _bank_at(f, entry):
    _id, blk, size, start, _lg = entry
    f.seek(start * blk)
    return f.read(size)


def plan(path, want):
    """What has to change: ([(id, bytes, name)] to add, [(id, name)] present)."""
    with open(path, 'rb') as f:
        _h, _fields, table = read_header(f)
        have = {e[0]: e for e in table}
        add, present = [], []
        for bid, b, name in want:
            if bid in have and have[bid][2] == len(b) and _bank_at(f, have[bid]) == b:
                present.append((bid, name))
            else:
                add.append((bid, b, name))
    return add, present


def install(path, add):
    """Rewrite the package with `add` banks in it (new or replaced)."""
    with open(path, 'rb') as f:
        head, (hsz, ver, lsz, bsz, ssz, xsz), table = read_header(f)
        size = os.fstat(f.fileno()).st_size
        old_end = len(head)
        ids = {b for b, _x, _n in add}
        keep = [e for e in table if e[0] not in ids]
        # a replaced bank whose bytes are the tail of the file is cut off
        tail = size
        for e in table:
            if e[0] in ids and e[3] * e[1] + e[2] == tail:
                tail = e[3] * e[1]
        new_entries = len(keep) + len(add) - len(table)
        delta = 20 * new_entries
        rows = [(e[0], e[1], e[2], e[3] * e[1] + delta, e[4]) for e in keep]
        pos = tail + delta
        for bid, b, _n in add:
            rows.append((bid, 1, len(b), pos, 0))
            pos += len(b)
        rows.sort()
        lut = struct.pack('<I', len(rows)) + b''.join(struct.pack('<IIIII', *r) for r in rows)
        lang = head[0x1C:0x1C + lsz]
        after = head[0x1C + lsz + bsz:]                    # stream + externals tables
        new_head = struct.pack('<4sIIIIII', b'AKPK', hsz + delta, ver, lsz, len(lut), ssz,
                               xsz) + lang + lut + after
        if len(new_head) != old_end + delta:
            raise ValueError('header arithmetic is off')
        tmp = path + '.port_sounds_tmp'
        with open(tmp, 'wb') as o:
            o.write(new_head)
            f.seek(old_end)
            left = tail - old_end
            while left > 0:
                c = f.read(min(CHUNK, left))
                o.write(c)
                left -= len(c)
            for _bid, b, _n in add:
                o.write(b)
    os.replace(tmp, path)


def ensure(game, mcc_root, write=True, backup_dir=None, volume=None):
    """Make `game`'s live sound package carry every port bank. Patcher-style rows; never
    raises for a bad package -- it reports and leaves the file alone. `volume` {port: dB}:
    the knob (a bank at another volume is simply replaced)."""
    if game == 'halo1':
        return h1_ensure(mcc_root, write=write, backup_dir=backup_dir, volume=volume)
    try:
        want = banks(game, volume)
    except ValueError as e:
        return [{'effect': 'port sound bank', 'field': '%s volume' % game, 'ok': False,
                 'reason': str(e)}]
    if game not in PACKAGES or not want:
        return []
    path = os.path.join(mcc_root, PACKAGES[game])
    row = {'effect': 'port sound bank', 'field': '%s sfxbank.pck' % game}
    if not os.path.exists(path):
        return [dict(row, ok=True, skip=True, reason='package not installed')]
    try:
        add, present = plan(path, want)
    except Exception as e:
        return [dict(row, ok=False, reason='unreadable package: %s' % e)]
    rows = [dict(row, field='%s %s' % (game, n), ok=True, skip=True, reason='bank present')
            for _b, n in present]
    if not add:
        return rows
    names = ', '.join(n for _b, _x, n in add)
    if not write:
        return rows + [dict(row, ok=True, old='without %s' % names, new='%s added (dry run)' % names)]
    try:
        if backup_dir:
            keep = os.path.join(backup_dir, game, 'sfxbank.pck')
            if not os.path.exists(keep):
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copyfile(path, keep)
        install(path, add)
        still, _p = plan(path, want)
        if still:
            return rows + [dict(row, ok=False, reason='written, but %s do not read back'
                                % ', '.join(n for _b, _x, n in still))]
    except Exception as e:
        return rows + [dict(row, ok=False, reason='could not write: %s' % e)]
    return rows + [dict(row, ok=True, old='without %s' % names, new='%s added' % names)]


# ---- Halo 1: the classic FMOD bank (h1_fsb.py) --------------------------------------
# MCC's Halo 1 plays its sounds from halo1\sound\pc\sounds_adpcm.fsb (classic view),
# found by the sound TAG'S PATH through lst\sounds_adpcm.lst.bin -- not from the map. A
# port's own sound tags are silent until their audio is in that bank under their paths.
# port_sounds\halo1\*.json (made by sprint_toolkit\h1_saw_sounds.py) lists each sound's
# index paths and its permutation WAVs (22 kHz mono); they are encoded to XBOX IMA ADPCM
# here and APPENDED as subsongs named port_*, always the bank's tail, so a reinstall (or
# another volume) drops the old tail and appends again; the stock part is never touched.
H1_FSB = os.path.join('halo1', 'sound', 'pc', 'sounds_adpcm.fsb')
H1_LST = os.path.join('halo1', 'sound', 'pc', 'lst', 'sounds_adpcm.lst.bin')
H1_PREFIX = 'port_'
H1_MAX_UP_DB = 6.0


def h1_wanted(volume=None):
    """[(subsong name, rate, adpcm bytes, sample count)] and [(index path, i0, count)]
    (i0 relative to the first port subsong) from the halo1 manifests."""
    import json
    import wave
    import numpy as np
    import h1_fsb
    samples, index = [], []
    for man in sorted(glob.glob(os.path.join(_data_dir(), 'halo1', '*.json'))):
        m = json.load(open(man, encoding='utf-8'))
        db = min((volume or {}).get(m.get('weapon'), 0.0) or 0.0, H1_MAX_UP_DB)
        for snd in m['sounds']:
            i0 = len(samples)
            base = snd.get('name') or snd['tag'].replace('\\', '/').rsplit('/', 1)[-1]
            for k, f in enumerate(snd['perms']):
                with wave.open(os.path.join(os.path.dirname(man), f), 'rb') as r:
                    if r.getnchannels() != 1 or r.getsampwidth() != 2:
                        raise ValueError('%s: want 16-bit mono' % f)
                    rate = r.getframerate()
                    x = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16) / 32768.0
                if db:
                    x = x * 10 ** (db / 20.0)
                    if db > 0:
                        x = 0.95 * np.tanh(x / 0.95)        # louder, peaks soft-limited
                blob, ns = h1_fsb.encode_xbox_ima(np.round(x * 32767).astype(np.int32))
                samples.append(('%s%s_%d' % (H1_PREFIX, base, k), rate, blob, ns))
            for alias in snd['aliases']:
                index.append((alias, i0, len(snd['perms'])))
    return samples, index


def h1_ensure(mcc_root, write=True, backup_dir=None, volume=None):
    import h1_fsb
    row = {'effect': 'port sound bank', 'field': 'halo1 sounds_adpcm.fsb'}
    fsb, lst = os.path.join(mcc_root, H1_FSB), os.path.join(mcc_root, H1_LST)
    if not (os.path.exists(fsb) and os.path.exists(lst)):
        return [dict(row, ok=True, skip=True, reason='bank not installed')]
    try:
        samples, index = h1_wanted(volume)
        if not samples:
            return []
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
    except Exception as e:
        return [dict(row, ok=False, reason='unreadable: %s' % e)]
    p0 = next((i for i, n in enumerate(names) if n.startswith(H1_PREFIX)), info['n'])
    if any(not n.startswith(H1_PREFIX) for n in names[p0:]):
        return [dict(row, ok=False, reason='port subsongs are not the bank tail -- left alone')]
    want_index = {(a, p0 + i, c) for a, i, c in index}

    def present():
        if names[p0:] != [s[0] for s in samples]:
            return False
        with open(fsb, 'rb') as f:
            for k, (_n, _r, blob, _ns) in enumerate(samples):
                f.seek(data_at + ((sh[p0 + k] >> 6) & 0x0FFFFFFF) * 16)
                if f.read(len(blob)) != blob:
                    return False
        return want_index <= set(entries)
    if present():
        return [dict(row, ok=True, skip=True, reason='port sounds present')]
    what = ', '.join(sorted({s[0].rsplit('_', 1)[0] for s in samples}))
    if not write:
        return [dict(row, ok=True, old='without %s' % what, new='%s added (dry run)' % what)]
    try:
        if backup_dir:
            for p, rel in ((fsb, H1_FSB), (lst, H1_LST)):
                keep = os.path.join(backup_dir, rel)
                if not os.path.exists(keep):
                    os.makedirs(os.path.dirname(keep), exist_ok=True)
                    shutil.copyfile(p, keep)
        first = h1_fsb.append_fsb(fsb, fsb, samples, keep=p0)
        ours = {a for a, _i, _c in index}
        kept = [e for e in entries if e[1] < p0 and e[0] not in ours]
        h1_fsb.write_lst(lst, ver, kept + [(a, first + i, c) for a, i, c in index])
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
        if not present():
            return [dict(row, ok=False, reason='written, but the port sounds do not read back')]
    except Exception as e:
        return [dict(row, ok=False, reason='could not write: %s' % e)]
    return [dict(row, ok=True, old='without %s' % what,
                 new='%s added (%d subsongs from %d)' % (what, len(samples), first))]


def problems(mcc_root, volume=None):
    """Validator: a port bank missing from (or stale in) a live package. Pass the same
    `volume` the patch used, or a turned bank reads as stale."""
    out = []
    for game in PACKAGES:
        for r in ensure(game, mcc_root, write=False, volume=volume):
            if not r.get('ok'):
                out.append('sound %s: %s' % (r['field'], r.get('reason')))
            elif not r.get('skip'):
                out.append('sound %s: missing %s -- run `python port_sounds.py --write` (or patch)'
                           % (r['field'], r['old'].replace('without ', '')))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mcc', default=os.path.dirname(HERE))
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--backup-dir')
    a = ap.parse_args()
    if a.check:
        found = problems(a.mcc)
        for p in found:
            print(' ', p)
        print('%d sound problem(s)' % len(found))
        sys.exit(1 if found else 0)
    for game in PACKAGES:
        for r in ensure(game, a.mcc, write=a.write, backup_dir=a.backup_dir):
            state = 'skip' if r.get('skip') else ('ok' if r['ok'] else 'FAIL')
            print('%-5s %-34s %s' % (state, r['field'], r.get('reason') or
                                     '%s -> %s' % (r.get('old'), r.get('new'))))
    if not a.write:
        print('(report only -- pass --write)')


if __name__ == '__main__':
    main()

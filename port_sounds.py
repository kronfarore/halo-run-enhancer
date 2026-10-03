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

FOR THE ENHANCER (patch time, Halo 4):
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
PACKAGES = {'halo4': os.path.join('halo4', 'sound', 'pc', 'sfxbank.pck')}
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

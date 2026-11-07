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

HALO 3 / ODST / REACH (2026-10-05): a port's own FMOD bank FILE beside sfx.fsb, copied
into <game>\fmod\pc when missing or different -- see fmod_ensure().

HALO 1 TOO (2026-10-04): MCC plays Halo 1 sounds from the classic FMOD bank
sounds_adpcm.fsb, by tag path -- see h1_ensure(); port_sounds\halo1 carries the audio.

FOR THE ENHANCER (patch time, Halo 4 and Halo 1):
    import port_sounds
    rows = port_sounds.ensure('halo4', mcc_root())       # patcher-style rows
    rows = port_sounds.ensure('halo4', mcc_root(), volume={'Focus Rifle': -3.0})
                                   # per-port volume knob, dB relative to the bank as built
                                   # (port_volume.bank_volume: the root mixer's Volume)
    problems = port_sounds.problems(mcc_root())           # validator messages
    row = port_sounds.retimed_anim_sound(m, game, port, 'reload', mult)
                                   # after the balance retime: Halo 1's stretched reload sound
A frozen build needs datas += [('port_sounds', 'port_sounds')] in halo_enhancer.spec.

COMMAND LINE (cmd.exe):
    python port_sounds.py              report
    python port_sounds.py --write      install missing banks
    python port_sounds.py --check      validator: exit 1 if a bank is missing
    python port_sounds.py --backup-dir D:\keep   (with --write) copy each STOCK bank there first
    python port_sounds.py --restore [--check]  take the ports' data OUT of the live banks (restore();
                                       --check = the inventory only). 'Revert engine patches' runs it.
All three read the per-port volume knob from settings.json (weapon_port_volume, as the
enhancer passes it: volume_knobs), so a bank turned on purpose is not 'stale' and --write
does not put the as-built bank back (review U4 B2). --backup-dir is a hand tool: the copy is
taken only while the live bank is STOCK (no port bank in it yet -- a bank that already
carries ports is reported and not copied, review U4 C2), nothing restores from it by itself,
and a Steam verify remains the supported way back to stock; the enhancer never passes it.
"""
import argparse
import contextlib
import glob
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = 'port_sounds'
PACKAGES = {'halo4': os.path.join('halo4', 'sound', 'pc', 'sfxbank.pck'),
            'halo1': os.path.join('halo1', 'sound', 'pc', 'sounds_adpcm.fsb')}
CHUNK = 1 << 24
#: every row's tag: a write into THIS machine's MCC files, not into the map -- the patch
#: signature leaves such rows out of the co-op code (halo_patch.is_machine_row, review U4 F3)
MACHINE_TAG = 'MCC files'


def _data_dir():
    for d in (HERE, getattr(sys, '_MEIPASS', '')):
        p = os.path.join(d, DATA)
        if d and os.path.isdir(p):
            return p
    return os.path.join(HERE, DATA)


KNOB_GAMES = (('Halo 1', 'halo1'), ('Halo 4', 'halo4'))     # the bank-route games


def volume_knobs(settings_path=None):
    """{game folder: {port weapon: dB}} from settings.json's weapon_port_volume for the
    bank-route games -- the knob the enhancer passes to ensure() per game (0 and missing
    values left out). Per GAME: the Focus Rifle is a port in Halo 1 and in Halo 4, so one
    flat dict would let one game's knob shadow the other's. {} when there is no settings
    file or no knob."""
    path = settings_path or os.path.join(HERE, 'settings.json')
    try:
        with open(path, encoding='utf-8') as f:
            knobs = json.load(f).get('weapon_port_volume') or {}
    except Exception:
        return {}
    out = {}
    for game, folder in KNOB_GAMES:
        v = {}
        for w, x in (knobs.get(game) or {}).items():
            try:
                if float(x):
                    v[w] = float(x)
            except (TypeError, ValueError):
                pass
        if v:
            out[folder] = v
    return out


def _game_volume(volume, game):
    """`volume` as ensure() wants it for `game`: a per-game dict {folder: {weapon: dB}}
    (volume_knobs) gives that game's knobs; a flat {weapon: dB} is one game's, as the
    enhancer passes it."""
    if not volume:
        return None
    if all(k in ALL_GAMES for k in volume):
        return volume.get(game) or None
    return volume


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


def _pck_is_stock(path, want):
    """No port bank id in the package's table at all (a replaced bank at other bytes is a
    port bank too): what --backup-dir may call a stock copy (review U4 C2)."""
    ids = {bid for bid, _b, _n in want}
    with open(path, 'rb') as f:
        _h, _f, table = read_header(f)
    return not any(e[0] in ids for e in table)


def install(path, add):
    """Rewrite the package with `add` banks in it (new or replaced)."""
    with open(path, 'rb') as f:
        head, (hsz, ver, lsz, bsz, ssz, xsz), table = read_header(f)
        size = os.fstat(f.fileno()).st_size
        old_end = len(head)
        ids = {b for b, _x, _n in add}
        keep = [e for e in table if e[0] not in ids]
        if any(e[1] != 1 for e in table):
            # kept offsets are rewritten as start * blk + delta with blk 1 assumed (the shipped
            # package has 1 throughout); another block size would corrupt every stock offset (N18)
            raise ValueError('a bank table entry has block size %d, not 1 -- unknown package layout'
                             % next(e[1] for e in table if e[1] != 1))
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
        try:
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
                o.flush()
                os.fsync(o.fileno())       # the replace below must find the bytes on disk
        except BaseException:
            with contextlib.suppress(OSError):
                os.remove(tmp)             # a failed install leaves no 400 MB temp behind (N10)
            raise
    try:
        os.replace(tmp, path)              # once the source handle is closed: Windows refuses otherwise
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def remove(path, ids):
    """Rewrite the package WITHOUT the banks `ids` -- install() backwards (review U4 F1). The
    banks a port install appended sit at the file's tail, so the common case is a cut: the
    header shrinks by 20 bytes per dropped entry, every kept offset moves back by that much
    and the file ends where the first dropped bank began -- on a package install() made from
    stock, that is the stock bytes again. A dropped bank that is NOT at the tail (a volume
    change replaced it and its old bytes were left unreferenced mid-file) takes the general
    route: the kept banks are copied in file order, contiguously, behind the new header.
    Returns the number of entries dropped (0 = nothing to do, nothing written)."""
    with open(path, 'rb') as f:
        head, (hsz, ver, lsz, bsz, ssz, xsz), table = read_header(f)
        size = os.fstat(f.fileno()).st_size
        old_end = len(head)
        drop = [e for e in table if e[0] in ids]
        if not drop:
            return 0
        keep = [e for e in table if e[0] not in ids]
        delta = -20 * len(drop)
        cut = min(e[3] * e[1] for e in drop)
        tail_cut = all(e[3] * e[1] + e[2] <= cut for e in keep)
        if tail_cut:
            rows = [(e[0], e[1], e[2], e[3] * e[1] + delta, e[4]) for e in keep]
        else:
            rows, pos = [], old_end + delta
            for e in sorted(keep, key=lambda e: e[3] * e[1]):
                rows.append((e[0], 1, e[2], pos, e[4]))
                pos += e[2]
        rows.sort()
        lut = struct.pack('<I', len(rows)) + b''.join(struct.pack('<IIIII', *r) for r in rows)
        lang = head[0x1C:0x1C + lsz]
        after = head[0x1C + lsz + bsz:]
        new_head = struct.pack('<4sIIIIII', b'AKPK', hsz + delta, ver, lsz, len(lut), ssz,
                               xsz) + lang + lut + after
        if len(new_head) != old_end + delta:
            raise ValueError('header arithmetic is off')
        tmp = path + '.port_sounds_tmp'
        with open(tmp, 'wb') as o:
            o.write(new_head)
            if tail_cut:
                f.seek(old_end)
                left = cut - old_end
                while left > 0:
                    c = f.read(min(CHUNK, left))
                    o.write(c)
                    left -= len(c)
            else:
                for e in sorted(keep, key=lambda e: e[3] * e[1]):
                    o.write(_bank_at(f, e))
            o.flush()
            os.fsync(o.fileno())
    os.replace(tmp, path)
    return len(drop)


def restore(game, mcc_root, write=True):
    """Take the ports' sound data OUT of `game`'s live files, undoing ensure() (review U4 F1):
    Halo 3 / ODST / Reach -- the added sfx.<port>.fsb (+ .info) beside the stock banks are
    deleted (pure additions); Halo 4 -- the package is rewritten without the port banks
    (remove()); Halo 1 -- the port_ tail is dropped from the bank and both indexes lose the
    port entries (h1_restore). Rows like ensure()'s; `write=False` is the inventory. The
    next patch puts everything back. Never raises for a bad file."""
    if game == 'halo1':
        return h1_restore(mcc_root, write=write)
    if game in FMOD_GAMES:
        rows = []
        pc = os.path.join(mcc_root, game, 'fmod', 'pc')
        for fsb in sorted(glob.glob(os.path.join(_data_dir(), game, 'sfx.*.fsb'))):
            name = os.path.basename(fsb)
            row = {'effect': 'port sound bank', 'field': '%s %s' % (game, name), 'tag': MACHINE_TAG}
            targets = [p for p in (os.path.join(pc, name), os.path.join(pc, name + '.info'))
                       if os.path.exists(p)]
            if not targets:
                rows.append(dict(row, ok=True, skip=True, reason='already stock (bank absent)'))
                continue
            if write:
                try:
                    for p in targets:
                        os.remove(p)
                except PermissionError:
                    rows.append(dict(row, ok=False, reason='%s is in use -- MCC holds it while a %s '
                                     'map is loaded; leave the map and press again' % (name, game)))
                    continue
                except Exception as e:
                    rows.append(dict(row, ok=False, reason='could not remove: %s' % e))
                    continue
            rows.append(dict(row, ok=True, old='with %s' % name,
                             new='stock (%d file(s) removed)%s' % (len(targets), '' if write else ' (dry run)')))
        return rows
    if game not in PACKAGES:
        return []
    row = {'effect': 'port sound bank', 'field': '%s sfxbank.pck' % game, 'tag': MACHINE_TAG}
    path = os.path.join(mcc_root, PACKAGES[game])
    if not os.path.exists(path):
        return [dict(row, ok=True, skip=True, reason='package not installed')]
    try:
        ids = {struct.unpack_from('<I', open(p, 'rb').read(16), 12)[0]
               for p in glob.glob(os.path.join(_data_dir(), game, '*.bnk'))}
        with open(path, 'rb') as f:
            _h, _f, table = read_header(f)
    except Exception as e:
        return [dict(row, ok=False, reason='unreadable package: %s' % e)]
    present = [e for e in table if e[0] in ids]
    if not present:
        return [dict(row, ok=True, skip=True, reason='already stock (no port bank)')]
    if not write:
        return [dict(row, ok=True, old='with %d port bank(s)' % len(present), new='stock (dry run)')]
    try:
        n = remove(path, ids)
        with open(path, 'rb') as f:
            _h, _f, table = read_header(f)
        if any(e[0] in ids for e in table):
            return [dict(row, ok=False, reason='written, but a port bank still reads back')]
    except PermissionError:
        return [dict(row, ok=False, reason='sfxbank.pck is in use -- MCC holds it while a Halo 4 map '
                                           'is loaded; leave the map and press again')]
    except Exception as e:
        return [dict(row, ok=False, reason='could not write: %s' % e)]
    return [dict(row, ok=True, old='with %d port bank(s)' % n, new='stock (%d entries)' % len(table))]


def ensure(game, mcc_root, write=True, backup_dir=None, volume=None):
    """Make `game`'s live sound package carry every port bank. Patcher-style rows; never
    raises for a bad package -- it reports and leaves the file alone. `volume` {port: dB}:
    the knob (a bank at another volume is simply replaced)."""
    if game == 'halo1':
        return h1_ensure(mcc_root, write=write, backup_dir=backup_dir, volume=volume)
    if game in FMOD_GAMES:
        return fmod_ensure(game, mcc_root, write=write)
    try:
        want = banks(game, volume)
    except ValueError as e:
        return [{'effect': 'port sound bank', 'field': '%s volume' % game, 'ok': False,
                 'reason': str(e), 'tag': MACHINE_TAG}]
    if game not in PACKAGES or not want:
        return []
    path = os.path.join(mcc_root, PACKAGES[game])
    row = {'effect': 'port sound bank', 'field': '%s sfxbank.pck' % game, 'tag': MACHINE_TAG}
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
            if os.path.exists(keep):
                pass
            elif not _pck_is_stock(path, want):
                rows.append(dict(row, ok=True, skip=True, field='%s backup' % game,
                                 reason='live bank already carries ports, no stock copy taken'))
            else:
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copyfile(path, keep)
        install(path, add)
        still, _p = plan(path, want)
        if still:
            return rows + [dict(row, ok=False, reason='written, but %s do not read back'
                                % ', '.join(n for _b, _x, n in still))]
    except PermissionError:
        return rows + [dict(row, ok=False, reason='sfxbank.pck is in use -- MCC holds it while a '
                            'Halo 4 map is loaded; leave the map and patch again')]
    except Exception as e:
        return rows + [dict(row, ok=False, reason='could not write: %s' % e)]
    return rows + [dict(row, ok=True, old='without %s' % names, new='%s added' % names)]


# ---- Halo 3 / ODST / Reach: a port's OWN FMOD bank FILE (2026-10-05) -----------------
# These games play their sounds from <game>\fmod\pc\sfx.<suffix>.fsb + .info, one bank per
# suffix; a port's sound tags carry their own suffix (the SAW: 'saw'), so its bank is a
# SEPARATE file beside the stock sfx.fsb -- nothing stock is touched. Built by the kit
# (sprint_toolkit\saw_port_sounds.py, which also copies it to port_sounds\<game>\); here
# it is only copied into place when missing or different. MCC holds a game's bank open
# while one of that game's maps is loaded, so a locked file is reported, not forced.
# The volume knob is in the MAP for these games (port_volume.py), not in the bank.
FMOD_GAMES = ('halo3', 'halo3odst', 'haloreach')


def _same(a, b):
    if not os.path.exists(b) or os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, 'rb') as f, open(b, 'rb') as g:
        while True:
            x, y = f.read(CHUNK), g.read(CHUNK)
            if x != y:
                return False
            if not x:
                return True


def fmod_ensure(game, mcc_root, write=True):
    rows = []
    pc = os.path.join(mcc_root, game, 'fmod', 'pc')
    for fsb in sorted(glob.glob(os.path.join(_data_dir(), game, 'sfx.*.fsb'))):
        name = os.path.basename(fsb)
        row = {'effect': 'port sound bank', 'field': '%s %s' % (game, name), 'tag': MACHINE_TAG}
        if not os.path.exists(fsb + '.info'):
            rows.append(dict(row, ok=False, reason='%s.info missing from port_sounds' % name))
            continue
        if not os.path.isdir(pc):
            rows.append(dict(row, ok=True, skip=True, reason='game not installed'))
            continue
        pairs = [(fsb, os.path.join(pc, name)), (fsb + '.info', os.path.join(pc, name + '.info'))]
        stale = [(s, d) for s, d in pairs if not _same(s, d)]
        if not stale:
            rows.append(dict(row, ok=True, skip=True, reason='bank present'))
            continue
        old = 'without %s' % name if not os.path.exists(pairs[0][1]) else 'a different %s' % name
        if not write:
            rows.append(dict(row, ok=True, old=old, new='%s installed (dry run)' % name))
            continue
        try:
            for s, d in stale:                    # temp + replace: never a half-written bank
                shutil.copyfile(s, d + '.tmp')
                os.replace(d + '.tmp', d)
        except PermissionError:
            rows.append(dict(row, ok=False, reason='%s is in use -- MCC holds it while a %s map '
                             'is loaded; leave the map and patch again' % (name, game)))
            continue
        except Exception as e:
            rows.append(dict(row, ok=False, reason='could not write: %s' % e))
            continue
        bad = [d for s, d in pairs if not _same(s, d)]
        rows.append(dict(row, ok=not bad, old=old, new='%s installed' % name,
                         reason=('written, but %s does not read back' % bad) if bad else None))
    return rows


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
# THE ANNIVERSARY INDEX TOO (2026-10-04): a sound tag under sound\sfx needs an entry in
# sounds_debug.lst.bin as well -- with only the classic one the game crashed the moment
# the port became active (halo1.dll+0xB3605D, a garbage tag pointer). That bank is CELT
# (not writable here) and the user plays classic only, so the port's entry BORROWS a stock
# Anniversary sound's subsongs (manifest `remastered_from`). The index is SORTED; entries
# are inserted in order, the stock ones keep theirs.
H1_DEBUG_LST = os.path.join('halo1', 'sound', 'pc', 'lst', 'sounds_debug.lst.bin')


def h1_wanted(volume=None):
    """[(subsong name, rate, adpcm bytes, sample count)], [(classic index path, i0, count)]
    (i0 relative to the first port subsong) and [(tag path, stock Anniversary path,
    count)] from the halo1 manifests."""
    import json
    import wave
    import numpy as np
    import h1_fsb
    samples, index, remastered = [], [], []
    for man in sorted(glob.glob(os.path.join(_data_dir(), 'halo1', '*.json'))):
        m = json.load(open(man, encoding='utf-8'))
        db = min((volume or {}).get(m.get('weapon'), 0.0) or 0.0, H1_MAX_UP_DB)
        # Path order, for a stable layout. (The 2026-10-04 theory that the classic index
        # must stay SORTED was disproven the same day -- halo1.dll sorts the entries itself;
        # the silent SAW fire was the FSB5 sample-header layout, see h1_fsb.py -- and the
        # live install's appended tail is unsorted across manifests and plays. Review U4 N1.)
        for snd in sorted(m['sounds'], key=lambda s: s['aliases'][0].lower()):
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
            if snd.get('remastered_from'):
                remastered.append((snd['tag'], snd['remastered_from'], len(snd['perms'])))
    return samples, index, remastered


def h1_ensure(mcc_root, write=True, backup_dir=None, volume=None):
    import h1_fsb
    row = {'effect': 'port sound bank', 'field': 'halo1 sounds_adpcm.fsb', 'tag': MACHINE_TAG}
    fsb, lst = os.path.join(mcc_root, H1_FSB), os.path.join(mcc_root, H1_LST)
    dlst = os.path.join(mcc_root, H1_DEBUG_LST)
    if not (os.path.exists(fsb) and os.path.exists(lst) and os.path.exists(dlst)):
        return [dict(row, ok=True, skip=True, reason='bank not installed')]
    try:
        samples, index, remastered = h1_wanted(volume)
        if not samples:
            return []
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
        dver, dentries = h1_fsb.read_lst(dlst)
        dmap = {e[0].lower(): e for e in dentries}
        want_debug = set()
        for tag, src, count in remastered:
            s = dmap.get(src.lower())
            if s is None:
                raise ValueError('no Anniversary entry %s to borrow' % src)
            want_debug.add((tag, s[1], min(count, s[2])))
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
                if h1_fsb.sample_channels(sh[p0 + k]) != 1:
                    return False                  # a mis-encoded header (old 16-byte layout)
                f.seek(data_at + h1_fsb.sample_offset(sh[p0 + k]))
                if f.read(len(blob)) != blob:
                    return False
        # EXACTLY ours: an entry left over from an earlier manifest (pointing into the
        # port range) is stale and makes the install not present
        ours_now = {e for e in entries if e[1] >= p0}
        return ours_now == want_index and want_debug <= set(dentries)
    if present():
        return [dict(row, ok=True, skip=True, reason='port sounds present')]
    what = ', '.join(sorted({s[0].rsplit('_', 1)[0] for s in samples}))
    if not write:
        return [dict(row, ok=True, old='without %s' % what, new='%s added (dry run)' % what)]
    extra = []
    try:
        if backup_dir:
            if p0 < info['n']:                    # a port_ tail: not a stock bank any more
                extra.append(dict(row, ok=True, skip=True, field='halo1 backup',
                                  reason='live bank already carries ports, no stock copy taken'))
            else:
                for p, rel in ((fsb, H1_FSB), (lst, H1_LST), (dlst, H1_DEBUG_LST)):
                    keep = os.path.join(backup_dir, rel)
                    if not os.path.exists(keep):
                        os.makedirs(os.path.dirname(keep), exist_ok=True)
                        shutil.copyfile(p, keep)
        first = h1_fsb.append_fsb(fsb, fsb, samples, keep=p0)
        ours = {a for a, _i, _c in index}
        kept = [e for e in entries if e[1] < p0 and e[0] not in ours]
        new = [(a, first + i, c) for a, i, c in index]
        # (no sort-order guard: the engine sorts the index itself, see h1_wanted; review U4 N1)
        h1_fsb.write_lst(lst, ver, kept + new)
        # the Anniversary index: drop our old entries, insert ours in its sort order
        dours = {t.lower() for t, _f, _c in want_debug}
        dkept = [e for e in dentries if e[0].lower() not in dours]
        h1_fsb.write_lst(dlst, dver, sorted(dkept + sorted(want_debug), key=lambda e: e[0].lower()))
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
        dver, dentries = h1_fsb.read_lst(dlst)
        if not present():
            return extra + [dict(row, ok=False, reason='written, but the port sounds do not read back')]
    except PermissionError:
        return extra + [dict(row, ok=False, reason='the bank is in use -- MCC holds it while a Halo 1 '
                             'map is loaded; leave the map and patch again')]
    except Exception as e:
        return extra + [dict(row, ok=False, reason='could not write: %s' % e)]
    return extra + [dict(row, ok=True, old='without %s' % what,
                         new='%s added (%d subsongs from %d)' % (what, len(samples), first))]


def h1_port_paths():
    """(index paths, Anniversary tag paths) the manifests give the ports -- no WAV is read."""
    import json
    aliases, tags = set(), set()
    for man in sorted(glob.glob(os.path.join(_data_dir(), 'halo1', '*.json'))):
        m = json.load(open(man, encoding='utf-8'))
        for snd in m['sounds']:
            aliases.update(a.lower() for a in snd['aliases'])
            if snd.get('remastered_from'):
                tags.add(snd['tag'].lower())
    return aliases, tags


def h1_restore(mcc_root, write=True):
    """Drop the port_ tail from sounds_adpcm.fsb and the port entries from both indexes
    (review U4 F1) -- what h1_ensure does before it re-appends, without the re-append."""
    import h1_fsb
    row = {'effect': 'port sound bank', 'field': 'halo1 sounds_adpcm.fsb', 'tag': MACHINE_TAG}
    fsb, lst = os.path.join(mcc_root, H1_FSB), os.path.join(mcc_root, H1_LST)
    dlst = os.path.join(mcc_root, H1_DEBUG_LST)
    if not (os.path.exists(fsb) and os.path.exists(lst) and os.path.exists(dlst)):
        return [dict(row, ok=True, skip=True, reason='bank not installed')]
    try:
        aliases, tags = h1_port_paths()
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
        dver, dentries = h1_fsb.read_lst(dlst)
    except Exception as e:
        return [dict(row, ok=False, reason='unreadable: %s' % e)]
    p0 = next((i for i, n in enumerate(names) if n.startswith(H1_PREFIX)), info['n'])
    if any(not n.startswith(H1_PREFIX) for n in names[p0:]):
        return [dict(row, ok=False, reason='port subsongs are not the bank tail -- left alone')]
    ours = [e for e in entries if e[1] >= p0 or e[0].lower() in aliases]
    dours = [e for e in dentries if e[0].lower() in tags]
    if p0 == info['n'] and not ours and not dours:
        return [dict(row, ok=True, skip=True, reason='already stock (no port subsong, no port entry)')]
    what = '%d subsongs, %d + %d index entries' % (info['n'] - p0, len(ours), len(dours))
    if not write:
        return [dict(row, ok=True, old='with %s' % what, new='stock (dry run)')]
    try:
        if p0 < info['n']:
            h1_fsb.append_fsb(fsb, fsb, [], keep=p0)
        h1_fsb.write_lst(lst, ver, [e for e in entries if e not in ours])
        h1_fsb.write_lst(dlst, dver, [e for e in dentries if e not in dours])
        info, sh, names, data_at = h1_fsb.read_fsb(fsb)
        ver, entries = h1_fsb.read_lst(lst)
        dver, dentries = h1_fsb.read_lst(dlst)
        if (any(n.startswith(H1_PREFIX) for n in names) or any(e[1] >= info['n'] or e[0].lower() in aliases for e in entries)
                or any(e[0].lower() in tags for e in dentries)):
            return [dict(row, ok=False, reason='written, but port data still reads back')]
    except PermissionError:
        return [dict(row, ok=False, reason='the bank is in use -- MCC holds it while a Halo 1 map '
                                           'is loaded; leave the map and press again')]
    except Exception as e:
        return [dict(row, ok=False, reason='could not write: %s' % e)]
    return [dict(row, ok=True, old='with %s' % what, new='stock (%d subsongs)' % info['n'])]


# --- Halo 1: an animation sound that follows the balance retime ---
# A Halo 1 animation plays ONE sound (index into its antr's Sound References, cued at its
# sound frame). The patcher's balance retimes the SAW's first-person reload x1.28125 in the
# map (halo3_reload.scale_reload), which the 128-frame reload mix does not follow: its
# later clicks land up to 1.2 s early. So the map also carries a mix stretched for that
# retime -- an UNUSED sound reference of the same antr (sprint_toolkit\saw_anims.py) -- and
# the catalog names the swap: port['anim_sounds'][group] = {'mult', 'from', 'to'}.
H1_ANTR_SOUNDS, H1_SOUND_EL = 0x54, 0x14      # Sound References: tagref (id @+0xC) + pad
H1_ANIM_BLK, H1_ANIM_EL, H1_ANIM_SOUND = 0x74, 0xB4, 0x3C   # animation: Sound i16 @0x3C


def retimed_anim_sound(m, game, port, group, mult):
    """After the patcher retimes `group` of `port` by `mult`: point the animations that
    play the port's `from` sound at its `to` sound (stretched for exactly that mult).
    Returns a patcher-style row, or None when the port names no such swap.
    `anim_sounds[group]` may be a LIST of swaps (the H1 Battle Rifle: reload-empty and
    reload-full play different sounds); they are applied in turn and reported as one row."""
    spec = (port.get('anim_sounds') or {}).get(group)
    if not spec or str(game).strip() != 'Halo 1' or not port.get('fp_animations'):
        return None
    if isinstance(spec, list):
        rows = [_retimed_one(m, port, s, group, mult) for s in spec]
        bad = [r for r in rows if not r['ok']]
        done = [r for r in rows if not r.get('skip')]
        out = dict(rows[0], old=', '.join(r['old'] for r in rows))
        if bad:
            return dict(out, ok=False, reason='; '.join(r['reason'] for r in bad))
        if not done:
            return dict(out, skip=True, reason='; '.join(r['reason'] for r in rows))
        return dict(out, ok=True, skip=False, new=', '.join(r['new'] for r in done))
    return _retimed_one(m, port, spec, group, mult)


def _retimed_one(m, port, spec, group, mult):
    """One {'mult', 'from', 'to'} swap of retimed_anim_sound."""
    fp = port['fp_animations']
    row = {'effect': '%s (ported)' % (port.get('weapon') or 'port'),
           'tag': fp.rsplit('\\', 1)[-1], 'field': '%s sound' % group,
           'old': spec['from'].rsplit('\\', 1)[-1], 'new': spec['to'].rsplit('\\', 1)[-1]}
    if abs(float(mult) - float(spec['mult'])) > 1e-3:
        return dict(row, ok=True, skip=True,
                    reason='the stretched sound fits x%.4f, not x%.4f' % (spec['mult'], mult))
    changed = 0
    for _p, base in m.find_tags('antr', fp):
        refs = m.follow_all(base, [H1_ANTR_SOUNDS], [H1_SOUND_EL], 'all')
        names = [(m.tag_name_by_id(m.u32(el + 0xC)) or '').lower() for el in refs]
        if spec['from'].lower() not in names or spec['to'].lower() not in names:
            return dict(row, ok=False, reason='%s does not carry both sounds (map built '
                        'before 2026-10-04?)' % fp)
        old, new = names.index(spec['from'].lower()), names.index(spec['to'].lower())
        for el in m.follow_all(base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all'):
            if struct.unpack_from('<h', m.data, el + H1_ANIM_SOUND)[0] == old:
                struct.pack_into('<h', m.data, el + H1_ANIM_SOUND, new)
                changed += 1
    if not changed:
        return dict(row, ok=True, skip=True, reason='no animation plays %s' % spec['from'])
    return dict(row, ok=True, new='%s (%d animation(s))' % (row['new'], changed))


ALL_GAMES = tuple(PACKAGES) + FMOD_GAMES


def problems(mcc_root, volume=None):
    """Validator: a port bank missing from (or stale in) a live package. Pass the same
    `volume` the patch used -- volume_knobs(), per game -- or a turned bank reads as
    stale."""
    out = []
    for game in ALL_GAMES:
        for r in ensure(game, mcc_root, write=False, volume=_game_volume(volume, game)):
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
    ap.add_argument('--backup-dir', help='with --write: copy each STOCK bank here before its '
                                         'first install (a copy to put back by hand)')
    ap.add_argument('--restore', action='store_true', help="take the ports' data out of the live "
                                                           "banks (with --check: the inventory only)")
    a = ap.parse_args()
    if a.restore:
        for game in ALL_GAMES:
            for r in restore(game, a.mcc, write=not a.check):
                state = 'skip' if r.get('skip') else ('ok' if r['ok'] else 'FAIL')
                print('%-5s %-34s %s' % (state, r['field'], r.get('reason') or
                                         '%s -> %s' % (r.get('old'), r.get('new'))))
        if a.check:
            print('(inventory only -- drop --check to restore)')
        return
    knobs = volume_knobs()          # the enhancer's per-port volume, per game (settings.json)
    if knobs:
        print('volume knobs: %s' % ', '.join('%s %s %+g dB' % (g, w, v) for g in sorted(knobs)
                                              for w, v in sorted(knobs[g].items())))
    if a.check:
        found = problems(a.mcc, volume=knobs)
        for p in found:
            print(' ', p)
        print('%d sound problem(s)' % len(found))
        sys.exit(1 if found else 0)
    for game in ALL_GAMES:
        for r in ensure(game, a.mcc, write=a.write, backup_dir=a.backup_dir,
                        volume=_game_volume(knobs, game)):
            state = 'skip' if r.get('skip') else ('ok' if r['ok'] else 'FAIL')
            print('%-5s %-34s %s' % (state, r['field'], r.get('reason') or
                                     '%s -> %s' % (r.get('old'), r.get('new'))))
    if not a.write:
        print('(report only -- pass --write)')


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit'))
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('port_sounds'):
        main()

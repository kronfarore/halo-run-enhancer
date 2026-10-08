r"""Halo 1: an overheat drops the zoom, as in Halo 2-4 -- a 6-byte halo1.dll patch.

No stock Halo 1 weapon both zooms and overheats, so the engine never unzooms on an
overheat; the Beam Rifle port (and any battery weapon a run gives zoom to) stayed
scoped through the vent. The patch is ENGINE-WIDE: it is keyed on the overheat event,
not on a weapon, so every heat weapon a local player holds is covered -- stock, ported
or given zoom levels by a card. Stock heat weapons never zoom, so for them it writes
"unzoomed" over "unzoomed". Research: PORTING.md, "the Beam Rifle, wave A4 -- leaving
the zoom on overheat".

The site (rva, image base 0x180000000; MCC halo1.dll of 2026-06-22): the first-person
weapon event handler +0xB2A3F0 unzooms the player for events 9/10/0x12/0x13 (the
reloads). The overheat (heat >= the tag's overheated threshold) sends event 0xF (0x10
for one variant), which fell through. Widened in place so 0xF..0x13 unzoom (0x11 has
its own `je` before it, so it is untouched):

    +0xB2A462  8D 42 EE   lea eax,[rdx-0x12]   ->  8D 42 F1   lea eax,[rdx-0x0F]
    +0xB2A465  41 3B C7   cmp eax,r15d (=1)    ->  83 F8 04   cmp eax,4

Both halves, whatever state MCC is in -- `sync(on)`:
  LIVE  MCC running with halo1.dll loaded: the bytes are written into the process
        (death_penalty's attach/read/write). Takes effect at once, until MCC exits.
  FILE  halo1.dll on disk, so every later MCC start has it. MCC closed: written in
        place. MCC running: the loaded dll cannot be opened for writing, but it CAN be
        renamed -- the patched copy is put in its place and the loaded original is
        renamed to halo1.dll.inuse-<time>, deleted by the next sync once MCC has let go.
Context bytes around the site are verified before every write (live and file); a dll
that does not hold them (an MCC update) is refused, never guessed at. A Steam update
or verify restores the stock dll -- the next patch with the option on puts it back.
The first file write keeps halo1.dll.prepatch.bak. In co-op BOTH machines need it
(the option travels with the run's options snapshot).

    python sprint_toolkit/h1_overheat_unzoom.py --show
    python sprint_toolkit/h1_overheat_unzoom.py --on
    python sprint_toolkit/h1_overheat_unzoom.py --off
    python sprint_toolkit/h1_overheat_unzoom.py --show --dll <copy of halo1.dll>
"""
import argparse
import glob
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402  (attach/read/write helpers)

H = bytes.fromhex

DLL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', 'halo1', 'halo1.dll'))
RVA = 0xB2A462            # the patched 6 bytes, in memory
FILE_OFF = 0xB29862       # the same bytes in the file (.text: rva - 0xC00)
PRE = H('83fa11' '7440')  # cmp edx,0x11 / je  -- must precede the site
POST = H('775d')          # ja (skip the unzoom) -- must follow it
STOCK = H('8d42ee' '413bc7')
PATCHED = H('8d42f1' '83f804')
NAME = 'Overheat drops the zoom'


def _classify(window):
    """window = PRE + 6 site bytes + POST -> 'off' / 'on' / 'unknown'."""
    if len(window) != len(PRE) + 6 + len(POST):
        return 'unknown'
    if window[:len(PRE)] != PRE or window[-len(POST):] != POST:
        return 'unknown'
    site = window[len(PRE):len(PRE) + 6]
    return 'on' if site == PATCHED else 'off' if site == STOCK else 'unknown'


def _window_at(buf_read, site):
    return buf_read(site - len(PRE), len(PRE) + 6 + len(POST))


# ---- file ----------------------------------------------------------------------------

def file_state(path=DLL):
    if not os.path.exists(path):
        return 'missing'
    with open(path, 'rb') as f:
        def rd(off, n):
            f.seek(off)
            return f.read(n)
        return _classify(_window_at(rd, FILE_OFF))


def _cleanup_inuse(path=DLL):
    """Delete originals a running MCC held at the last swap, once it has let go."""
    for old in glob.glob(glob.escape(path) + '.inuse-*'):
        try:
            os.remove(old)
        except OSError:
            pass                                # still mapped by MCC: next time


def file_set(on, path=DLL):
    """(ok, message). Writes in place, or swaps the file when MCC holds it."""
    _cleanup_inuse(path)
    st = file_state(path)
    want = 'on' if on else 'off'
    if st == want:
        return True, 'already ' + want
    if st == 'missing':
        return False, '%s not found' % path
    if st == 'unknown':
        return False, ('halo1.dll does not hold the expected bytes at +0x%X -- this MCC '
                       'build differs, refusing to write' % RVA)
    blob = PATCHED if on else STOCK
    bak = path + '.prepatch.bak'
    if on and not os.path.exists(bak):
        shutil.copyfile(path, bak)
    try:
        with open(path, 'r+b') as f:
            f.seek(FILE_OFF)
            f.write(blob)
        return True, 'written in place'
    except PermissionError:
        pass                                    # loaded by MCC: swap instead
    new = path + '.new'
    shutil.copyfile(path, new)
    with open(new, 'r+b') as f:
        f.seek(FILE_OFF)
        f.write(blob)
    if file_state(new) != want:
        os.remove(new)
        return False, 'the patched copy did not verify'
    held = '%s.inuse-%d' % (path, int(time.time()))
    try:
        os.rename(path, held)
    except OSError as e:
        os.remove(new)
        return False, 'MCC holds halo1.dll and it could not be renamed: %s' % e
    try:
        os.rename(new, path)
    except OSError as e:
        os.rename(held, path)                   # put the original back
        return False, 'could not put the patched halo1.dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


# ---- live ----------------------------------------------------------------------------

def live_state(h, base):
    return _classify(_window_at(lambda a, n: dp.read(h, a, n) or b'', base + RVA))


def live_set(h, base, on):
    st = live_state(h, base)
    want = 'on' if on else 'off'
    if st == want:
        return True, 'already ' + want
    if st == 'unknown':
        return False, ('the running halo1.dll does not hold the expected bytes at '
                       '+0x%X -- this MCC build differs, refusing to write' % RVA)
    return dp.write(h, base + RVA, PATCHED if on else STOCK)


# ---- both ----------------------------------------------------------------------------

def sync(on, path=DLL, quiet=True):
    """One call for the GUI: the patch on (or back to stock) in the running MCC AND in
    halo1.dll on disk. Result rows; never raises. quiet: no rows for halves that were
    already as wanted, so a patch with nothing to change stays out of the summary."""
    row = {'tag': 'halo1.dll', 'effect': NAME}
    want = 'on' if on else 'off'
    out = []

    def add(field, ok, old, msg):
        if quiet and ok and old == want:
            return
        out.append({**row, 'field': field, 'ok': ok, 'old': old,
                    'new': want if ok else None, 'reason': None if ok else msg,
                    **({'note': msg} if ok else {})})

    pid = dp.find_pid()
    if pid:
        h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
        if not h:
            add('running MCC', False, None, 'OpenProcess failed -- run elevated')
        else:
            try:
                base = dp.module_base(pid, b'halo1.dll')
                if base:
                    old = live_state(h, base)
                    ok, err = live_set(h, base, on)
                    add('running MCC', ok, old, err)
            finally:
                dp.k32.CloseHandle(h)
    try:
        old = file_state(path)
        ok, msg = file_set(on, path)
        add('halo1.dll file', ok, old, msg)
    except Exception as e:                      # never fatal to a map patch
        add('halo1.dll file', False, None, str(e))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    g.add_argument('--show', action='store_true')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    a = ap.parse_args(argv)
    if a.on or a.off:
        rows = sync(a.on, a.dll, quiet=False)
        for r in rows:
            print('%-16s %s %s' % (r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                   r.get('note') or r.get('reason') or r.get('new')))
        return
    print('file %-8s %s' % (file_state(a.dll), a.dll))
    pid = dp.find_pid()
    if not pid:
        print('live  MCC is not running')
        return
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    try:
        base = dp.module_base(pid, b'halo1.dll')
        print('live  %s' % (live_state(h, base) if base else 'halo1.dll not loaded'))
    finally:
        dp.k32.CloseHandle(h)


if __name__ == '__main__':
    main()

r"""Shared engine for VALUE patches of a game dll: a number (seconds, a count) written into
fixed sites, in the running MCC (live) AND in the dll file, verify-before-write.

h1_overheat_unzoom.py and its siblings switch a patch on or off. These carry a VALUE, so a
site is (rva, context before, stock bytes, context after) and a Tunable turns a value into
the bytes of each site (encode) and back (decode). Every write checks the context first;
a dll whose bytes differ (another MCC build) is refused, never corrupted. None = stock.

File: rva -> file offset through the PE section table (sites live in .text AND .rdata).
In place, or -- while MCC maps the dll -- the swap by rename that h1_melee_blocks_fire.py
uses (the patched copy is verified, the held original is renamed to .inuse-<time> and
removed at a later call). A first write keeps <dll>.prepatch.bak if there is none yet.
Live: dp.write (the page made writable for the write, the protection put back).
"""
import glob
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402

H = bytes.fromhex


def find_dll(game_dir, name):
    """MCC's <game_dir>/<name>: HALO_MCC_ROOT (the enhancer's MCC folder), the tool-relative
    folder, the default Steam folder -- the order h1_overheat_unzoom._find_dll uses."""
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [os.environ.get('HALO_MCC_ROOT'), os.path.join(here, '..', '..'),
             r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection']
    cands = [os.path.normpath(os.path.join(r, game_dir, name)) for r in roots if r]
    return next((c for c in cands if os.path.isfile(c)), cands[0])


def f32(x):
    return struct.pack('<f', x)


def unf32(b):
    return struct.unpack('<f', b)[0]


class Tunable:
    """sites: [(rva, pre, stock, post)], written in this order when leaving stock and in
    reverse when going back (a cave / slot first, the instruction that uses it last).
    encode(value) -> [bytes per site]; decode([bytes per site]) -> value (None = unknown)."""

    def __init__(self, key, label, unit, stock, sites, encode, decode):
        self.key, self.label, self.unit, self.stock = key, label, unit, stock
        self.sites, self._encode, self._decode = sites, encode, decode

    def blobs(self, value):
        return [st for _r, _p, st, _po in self.sites] if value is None else self._encode(value)

    def read(self, read):
        """read(rva, n) -> bytes. ('stock'|'set'|'unknown', value)."""
        cur = []
        for rva, pre, stock, post in self.sites:
            w = read(rva - len(pre), len(pre) + len(stock) + len(post)) or b''
            if (len(w) != len(pre) + len(stock) + len(post) or w[:len(pre)] != pre
                    or w[len(w) - len(post):] != post):
                return 'unknown', None
            cur.append(w[len(pre):len(pre) + len(stock)])
        if cur == self.blobs(None):
            return 'stock', self.stock
        v = self._decode(cur)
        return ('set', v) if v is not None else ('unknown', None)

    def writes(self, read, value):
        """[(rva, bytes)] that take the sites from what they hold to `value`."""
        state, _v = self.read(read)
        if state == 'unknown':
            raise ValueError('%s: the dll does not hold the expected bytes -- this MCC '
                             'build differs, refusing to write' % self.label)
        want = self.blobs(value)
        order = range(len(self.sites)) if value is not None else reversed(range(len(self.sites)))
        out = []
        for i in order:
            rva, _p, stock, _po = self.sites[i]
            if read(rva, len(stock)) != want[i]:
                out.append((rva, want[i]))
        return out


# ---- file ------------------------------------------------------------------------------

def _sections(data):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    n = struct.unpack_from('<H', data, pe + 6)[0]
    opt = struct.unpack_from('<H', data, pe + 20)[0]
    out = []
    for i in range(n):
        o = pe + 24 + opt + 40 * i
        _vs, va, rawsize, raw = struct.unpack_from('<IIII', data, o + 8)
        out.append((va, rawsize, raw))
    return out


def _off(secs, rva):
    for va, rawsize, raw in secs:
        if va <= rva < va + rawsize:
            return raw + rva - va
    raise ValueError('rva +0x%X is not file-backed' % rva)


def file_reader(path):
    with open(path, 'rb') as f:
        data = f.read()
    secs = _sections(data)

    def read(rva, n):
        try:
            o = _off(secs, rva)
        except ValueError:
            return b''
        return data[o:o + n]
    return read


def _write_file(path, writes):
    with open(path, 'rb') as f:
        secs = _sections(f.read(0x1000))
    with open(path, 'r+b') as f:
        for rva, blob in writes:
            f.seek(_off(secs, rva))
            f.write(blob)


def _cleanup_inuse(path):
    for old in glob.glob(glob.escape(path) + '.inuse-*'):
        try:
            os.remove(old)
        except OSError:
            pass                                # still mapped by MCC: next time


def file_set(path, tun, value):
    """(ok, message): the dll file to `value` (None = stock)."""
    if not os.path.exists(path):
        return False, '%s not found' % path
    _cleanup_inuse(path)
    try:
        writes = tun.writes(file_reader(path), value)
    except ValueError as e:
        return False, str(e)
    if not writes:
        return True, 'already as wanted'
    bak = path + '.prepatch.bak'
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    try:
        _write_file(path, writes)
        return True, 'written in place'
    except PermissionError:
        pass                                    # mapped by MCC: swap instead
    new = path + '.new'
    shutil.copyfile(path, new)
    _write_file(new, writes)
    if tun.blobs(value) != [file_reader(new)(r, len(st)) for r, _p, st, _po in tun.sites]:
        os.remove(new)
        return False, 'the patched copy did not verify'
    held = '%s.inuse-%d' % (path, int(time.time()))
    try:
        os.rename(path, held)
    except OSError as e:
        os.remove(new)
        return False, 'MCC holds %s and it could not be renamed: %s' % (os.path.basename(path), e)
    try:
        os.rename(new, path)
    except OSError as e:
        os.rename(held, path)
        return False, 'could not put the patched dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


# ---- live ------------------------------------------------------------------------------

def live(module, fn):
    """fn(h, base) on the running MCC; None when MCC / the module is not there."""
    pid = dp.find_pid()
    if not pid:
        return None
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        return False, 'OpenProcess failed -- run elevated'
    try:
        base = dp.module_base(pid, module.encode())
        return fn(h, base) if base else None
    finally:
        dp.k32.CloseHandle(h)


def live_reader(h, base):
    return lambda rva, n: dp.read(h, base + rva, n)


def live_set(h, base, tun, value):
    try:
        writes = tun.writes(live_reader(h, base), value)
    except ValueError as e:
        return False, str(e)
    for rva, blob in writes:
        ok, err = dp.write(h, base + rva, blob)
        if not ok:
            return False, '+0x%X: %s' % (rva, err)
    return True, None


# ---- one call for the GUI -------------------------------------------------------------

def sync(tunables, module, values, path, mcc_path, quiet=True, live_only=False):
    """values {key: value or None (= stock)}; keys left out are not touched. The running
    MCC (only when `path` is MCC's own dll, `mcc_path`) and the file. Result rows; never
    raises."""
    out = []

    def add(tun, field, ok, old, new, msg):
        if quiet and ok and old == new:
            return
        out.append({'tag': module, 'effect': tun.label, 'field': field, 'ok': ok,
                    'old': old, 'new': new if ok else None,
                    'reason': None if ok else msg, **({'note': msg} if ok and msg else {})})

    todo = [(t, values[t.key]) for t in tunables if t.key in values]
    own = os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(mcc_path))

    def do_live(h, base):
        for tun, v in todo:
            old = tun.read(live_reader(h, base))[1]
            ok, err = live_set(h, base, tun, v)
            add(tun, 'running MCC', ok, old, tun.stock if v is None else v, err)
    try:
        r = live(module, do_live) if own else None
        if isinstance(r, tuple):
            for tun, _v in todo:
                add(tun, 'running MCC', False, None, None, r[1])
    except Exception as e:                      # never fatal to a map patch
        for tun, _v in todo:
            add(tun, 'running MCC', False, None, None, str(e))
    if not live_only:
        for tun, v in todo:
            try:
                old = tun.read(file_reader(path))[1] if os.path.exists(path) else None
                ok, msg = file_set(path, tun, v)
                add(tun, '%s file' % module, ok, old, tun.stock if v is None else v, msg)
            except Exception as e:
                add(tun, '%s file' % module, False, None, None, str(e))
    return out


def show(tunables, module, path):
    rd = file_reader(path) if os.path.exists(path) else None
    lv = live(module, lambda h, base: {t.key: t.read(live_reader(h, base)) for t in tunables})
    for t in tunables:
        f = t.read(rd) if rd else ('missing', None)
        l = lv.get(t.key) if isinstance(lv, dict) else None
        print('%-34s file %-7s %-10s live %s' % (
            t.label, f[0], _fmt(f[1], t.unit),
            '%s %s' % (l[0], _fmt(l[1], t.unit)) if l else 'MCC / %s not running' % module))


def _fmt(v, unit):
    if v is None:
        return '-'
    if v == 0:
        return 'unlimited'
    return ('%g %s' % (round(v, 2), unit)).strip()

r"""The MCC data files this tool rewrites outside the maps -- `Data\UI\scoredb.xml`,
`data\careerdb\careerdb.xml` and their side files -- read and written so that the live file
is never half-written and the shipped bytes come back exactly.

    text = read_text(path)                 # utf-8, line endings kept as they are (newline='')
    write_text_atomic(path, text)          # temp file beside the target, flush + fsync, os.replace
    copy_atomic(src, dst)                  # the same for a byte-for-byte copy (a restore)

MCC parses both files once at startup, so a truncated file is what it would run with for a
whole session: an in-place `open(path, 'w')` truncates first and writes second, and a kill, a
crash or a full disk between the two leaves exactly that. The temp file sits BESIDE the target
(os.replace is atomic within one volume only), is flushed and fsynced before the replace, and is
removed again on any failure, so the live file is either the old bytes or the new ones (review
U4 B9). Line endings are kept as read -- the shipped files are CRLF -- so a scale of 1 or a
restore puts the shipped BYTES back and an 'is the live file stock' test may compare bytes
(note N7). Standard library only: scoredb_patch and careerdb_patch import this and must stay
importable without the GUI.

THE STOCK COPY IS NOT TRUSTED FOREVER (review U4 C1). Beside each `<file>.bak` sits
`<file>.bak.meta`: the sha256 of the .bak and of the bytes this tool last wrote into the live
file. `guard()` runs at the start of every write and restore: a live file equal to the .bak is
stock, one equal to the last write (or, before the record existed, one that differs from the
.bak in values only -- `skeleton`) is ours; anything else was replaced from outside -- an MCC
update that shipped a new file, a Steam verify followed by an edit -- and is taken as the NEW
stock file: the .bak is refreshed from it (only when it passes the caller's `pristine` test,
where one exists) and the caller says so in its row. Without this, every patch and the Revert
button kept rewriting a post-update file from the pre-update copy, reported as a success.

    state = guard(live, bak, skeleton, pristine, 'scoredb.xml', notes)   # 'stock' | 'ours' | 'refreshed'
    record_bak(bak)                     # after seeding the .bak
    record_write(live, bak)             # after every write into the live file
"""
import hashlib
import json
import os
import shutil
import time


class StockError(RuntimeError):
    """The live file is neither the stock copy nor this tool's own write, and fails the pristine
    test too, so it cannot be taken as a new stock file. Nothing is written."""


def read_text(path):
    """The file as text, utf-8, with its line endings untouched."""
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write_text_atomic(path, text, newline=''):
    """Write `text` so that no reader ever sees half a file and no failure leaves one.
    `newline=''` writes the text's own line endings (what read_text returned)."""
    path = str(path)
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def copy_atomic(src, dst):
    """`dst` = the bytes of `src` (a .bak put back), through a temp file beside `dst`."""
    dst = str(dst)
    tmp = dst + '.tmp'
    try:
        with open(src, 'rb') as f, open(tmp, 'wb') as o:
            shutil.copyfileobj(f, o)
            o.flush()
            os.fsync(o.fileno())
        os.replace(tmp, dst)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---- the stock copy and what was written over it -----------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def meta_path(bak):
    return str(bak) + '.meta'


def read_meta(bak):
    try:
        with open(meta_path(bak), encoding='utf-8') as f:
            m = json.load(f)
        return m if isinstance(m, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_meta(bak, meta):
    write_text_atomic(meta_path(bak), json.dumps(meta, indent=1, sort_keys=True))


def record_bak(bak):
    """Called once the .bak was seeded: remember which bytes the stock copy has."""
    meta = read_meta(bak)
    meta['bak_sha256'] = sha256(bak)
    meta.setdefault('taken', time.strftime('%Y-%m-%d'))
    _write_meta(bak, meta)


def record_write(live, bak):
    """Called after every write into the live file: remember what this tool put there."""
    meta = read_meta(bak)
    meta['written_sha256'] = sha256(live)
    if not meta.get('bak_sha256'):
        meta['bak_sha256'] = sha256(bak)
    _write_meta(bak, meta)


def guard(live, bak, skeleton, pristine=None, label='the file', notes=None):
    """What the live file is, against its .bak: 'stock' (the .bak's bytes), 'ours' (this tool's
    last write -- or, with no record yet, a file that differs from the .bak in values only, as
    `skeleton(text)` sees it) or 'refreshed': another file underneath the stock copy, taken as
    the new stock file -- the .bak is replaced by it, the meta reset, and a line appended to
    `notes`. A replaced file that fails `pristine(text)` raises StockError instead: the
    caller must not write over something it cannot name."""
    live_h, bak_h = sha256(live), sha256(bak)
    if live_h == bak_h:
        return 'stock'
    meta = read_meta(bak)
    if meta.get('written_sha256') == live_h:
        return 'ours'
    live_t, bak_t = read_text(live), read_text(bak)
    if skeleton(live_t) == skeleton(bak_t):
        return 'ours'                     # the same rows, other values: an edit of ours
    if pristine is not None and not pristine(live_t):
        raise StockError('%s matches neither its stock copy nor this tool\'s last write, and '
                         'is not a stock file either -- left alone; Steam verify, then patch '
                         'again' % label)
    taken = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(bak)))
    shutil.copy2(live, bak)
    _write_meta(bak, {'bak_sha256': live_h, 'written_sha256': None,
                      'taken': time.strftime('%Y-%m-%d'), 'replaced_copy_of': taken})
    if notes is not None:
        notes.append('%s was replaced underneath the stock copy of %s (an MCC update?): the '
                     'live file is the new stock copy' % (label, taken))
    return 'refreshed'

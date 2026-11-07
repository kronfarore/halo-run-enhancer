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
"""
import os
import shutil


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

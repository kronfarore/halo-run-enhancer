# read-only helpers: opens BASELINE maps, never saves
import os, struct, sys, json, collections, time
TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as hp
import enemy_count as ec
GAME = 'Halo 4'
BASE = r'E:\HaloBaselines\halo4\maps'
OUT = os.path.dirname(os.path.abspath(__file__))
LEVELS = [('m10_crash', 'Dawn'), ('m020', 'Requiem'), ('m30_cryptum', 'Forerunner'),
          ('m60_rescue', 'Infinity'), ('m40_invasion', 'Reclaimer'), ('m70_liftoff', 'Shutdown'),
          ('m80_delta', 'Composer'), ('m90_sacrifice', 'Midnight')]
S = chr(92)


def op(mid):
    return hp.open_map(os.path.join(BASE, mid + '.map'), GAME)


def leaf(n):
    return str(n).rsplit(S, 1)[-1] if n else None


def i16(m, o):
    return struct.unpack_from('<h', m.data, o)[0]


def palette(m, scnr, off, es, idat):
    b, n = hp._block_base(m, scnr + off), max(0, m.i32(scnr + off))
    return [hp._tag_name_by_id(m, m.u32(b + i * es + idat)) for i in range(n)] if b else []


def block(m, at, es):
    n = m.i32(at)
    b = hp._block_base(m, at) if n > 0 else None
    return [b + i * es for i in range(n)] if b else []


def sid_tools(m):
    rows = hp._h4_string_rows(m)
    name_at = {i: s for s, i in rows.items()}
    return rows, name_at


def sid_name(m, name_at, sid):
    if sid == 0:
        return ''
    r = None
    try:
        r = m.resolve_stringid(sid)
    except Exception:
        pass
    return r or hex(sid)


def ref(m, at):
    """(class, name) of a tagRef field (16 bytes; id at +0xC)"""
    i = m.u32(at + 0xC)
    return hp._tag_name_by_id(m, i) if i != 0xFFFFFFFF else None

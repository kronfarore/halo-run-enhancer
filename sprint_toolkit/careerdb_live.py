"""Mirror careerdb.xml's par times into the RUNNING MCC -- careerdb's twin of score_live.

MCC reads <mcc_root>\\data\\careerdb\\careerdb.xml once, at startup (CareerDB::init),
so a par-time patch otherwise waits for a restart. The parsed chapter records live on
MCC's heap; this finds them and writes the file's numbers straight in.

Record layout (MCC-Win64-Shipping.exe, chapter parser at +0x20CEA0):
    +0x18  map info (-> "m10_crash" on Halo 4)
    +0x20  mission_segment_count      i32
    +0x24  par_time / +0x28 average_time / +0x2C max_time     f32 seconds
    +0x48  -> the chapter's title string, "$H1_Chapter_1-1_Title"
The TITLE is the key: it is careerdb's own `title` attribute, one per chapter.

Finding them: every par-time triplet MCC can possibly hold is known -- the pristine
file, the current file, and every state careerdb_patch has ever written
(careerdb_patch.known_triplets) -- so candidates are those 12-byte patterns in
private heap memory, confirmed by the title behind +0x48. Found addresses are cached
per MCC process like score_live's, so only the first push of a launch scans.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import careerdb_patch as CP                                       # noqa: E402
import score_live as SL                                           # noqa: E402

OFF_TIMES, OFF_TITLE = 0x24, 0x48
CACHE = os.path.join(HERE, 'out', 'careerdb_live_addrs.json')


def _title_at(h, rec):
    p = SL.read(h, rec + OFF_TITLE, 8)
    if not p or len(p) < 8:
        return None
    q = struct.unpack('<Q', p)[0]
    if not 0x10000 < q < (1 << 47):
        return None
    s = SL.read(h, q, 96)
    if not s:
        return None
    try:
        return s.split(b'\0')[0].decode('ascii')
    except UnicodeDecodeError:
        return None


def find_records(h, triplets):
    """{title: {record address}} for every chapter record in the process."""
    pats = {}
    for title, trips in triplets.items():
        for t in trips:
            pats.setdefault(struct.pack('<3f', *t), set()).add(title)
    found = {}
    for base, size in SL.regions(h):
        if size > 0x40000000:
            continue
        data = SL.read(h, base, size)
        if not data:
            continue
        for pat, titles in pats.items():
            i = data.find(pat)
            while i >= 0:
                rec = base + i - OFF_TIMES
                t = _title_at(h, rec)
                if t in titles:
                    found.setdefault(t, set()).add(rec)
                i = data.find(pat, i + 1)
    return found


def _cached(h, pid):
    try:
        with open(CACHE, encoding='utf-8') as f:
            blob = json.load(f)
    except Exception:
        return None
    if blob.get('pid') != pid or not blob.get('records'):
        return None
    out = {}
    for rec, title in blob['records']:
        if _title_at(h, rec) != title:
            return None                   # the heap moved or the pid was recycled
        out.setdefault(title, set()).add(rec)
    return out


def _save(pid, found):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump({'pid': pid, 'records': [[r, t] for t, rs in found.items()
                                           for r in sorted(rs)]}, f)


def push_from_xml(path):
    """Write every chapter's par/average/max from careerdb.xml into the running MCC.

    Returns a report dict; ok=False with a reason when there is nothing to write to,
    which includes the ordinary case of MCC not running."""
    with open(path, encoding='utf-8') as f:
        want = CP.chapter_times(f.read())
    if not want:
        return {'ok': False, 'reason': 'no chapters with par times in careerdb.xml'}
    pid = SL.find_pid()
    if not pid:
        return {'ok': False, 'reason': 'MCC is not running'}
    h = SL.k32.OpenProcess(SL.PROCESS_QUERY_INFORMATION | SL.PROCESS_VM_READ
                           | SL.PROCESS_VM_WRITE | SL.PROCESS_VM_OPERATION, False, pid)
    if not h:
        return {'ok': False, 'reason': 'could not open MCC for writing'}
    try:
        found = _cached(h, pid)
        cached = found is not None
        if not cached:
            found = find_records(h, CP.known_triplets(path))
            if not found:
                return {'ok': False, 'reason': 'no chapter records found in MCC'}
            _save(pid, found)
        done = failed = 0
        for title, recs in found.items():
            if title not in want:
                continue
            for rec in recs:
                if SL.write(h, rec + OFF_TIMES, struct.pack('<3f', *want[title])):
                    done += 1
                else:
                    failed += 1
        return {'ok': done > 0 and failed == 0, 'written': done, 'chapters': len(found),
                'expected': len(want), 'cached': cached,
                'reason': ('%d write(s) failed' % failed) if failed else None}
    finally:
        SL.k32.CloseHandle(h)


def read_back(title):
    """(par, avg, max) the running MCC holds for one chapter title, or None."""
    pid = SL.find_pid()
    if not pid:
        return None
    h = SL.k32.OpenProcess(SL.PROCESS_QUERY_INFORMATION | SL.PROCESS_VM_READ, False, pid)
    try:
        found = _cached(h, pid) or {}
        for rec in found.get(title, ()):
            return struct.unpack('<3f', SL.read(h, rec + OFF_TIMES, 12))
        return None
    finally:
        SL.k32.CloseHandle(h)

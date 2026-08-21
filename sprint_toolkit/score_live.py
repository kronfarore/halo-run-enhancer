r"""Read -- and optionally rewrite -- MCC's metagame score table in the RUNNING game.

WHY
---
`scoredb_patch.py` edits `<MCC>\Data\UI\scoredb.xml`, which MCC parses exactly once at
startup. That means every score change costs a full MCC restart, and since the enhancer
rescales scores on every patch, that is a restart per patch. This is the way around it:
the parsed table is ordinary heap memory, so it can be rewritten in place while the game
runs.

WHAT THE TABLE LOOKS LIKE (from MCC-Win64-Shipping.exe)
-------------------------------------------------------
The parser at +4469C0 walks the XML and stores each `<Enemy>` / vehicle row into an
MSVC `std::map` hanging off the score-info object:

    +4469F1  lea rdx, ["HaloScoreInfo"]        ; the document root
    +446A45  lea r15, [r13 + 0x40]             ; <- the map
    +446AE1..+446B0D                           ; the usual _Tree lookup, key at node+0x1C
    +446B44  movss dword ptr [rbx + 0x20], xmm6 ; score
    +446B49  movss dword ptr [rbx + 0x24], xmm7 ; score_skull

and the scoring path at +446E54 reads it back with a key built as `(type << 16) | class`
from two u16 bucket enums. So each record is a plain `_Tree_node`:

    +0x00 _Left   +0x08 _Parent   +0x10 _Right
    +0x18 _Color  +0x19 _Isnil
    +0x1C key u32   (TYPE in the low half, CLASS in the high half -- the parser does
                     `mov word [rsp+0x30], ax` with ax = the type enum and
                     `mov word [rsp+0x32], bx` with bx = the class enum, so the halves
                     are the other way round from how the lookup's argument order
                     reads)
    +0x20 score f32     +0x24 score_skull f32

Names are NOT kept -- searching the process for "Combat Form (unarmed)" finds nothing --
so the values are all there is to match on, and matching has to be structural.

HOW THIS FINDS IT
-----------------
Scan committed memory for anything shaped like that node, then group the candidates by
walking `_Parent` to the tree head: nodes of one `std::map` all reach the same head, so
this partitions candidates into actual maps rather than guessing by address proximity.
A group is THE table when its score multiset matches a section of scoredb.xml.

    python score_live.py                  # locate and report
    python score_live.py --dump           # every record in the tables it found
    python score_live.py --set-all 9999   # THE VIABILITY TEST (see below)
    python score_live.py --restore        # put the saved values back

THE VIABILITY TEST
------------------
Knowing WHICH node is which enemy needs the bucket enums, which are hashed
(CRC-32/BZIP2 over the uppercased name -- confirmed 8/8 against the class helper's
constants at +207C7B0) and then binary-searched, so the type names cost real work to
recover. None of that is needed to answer the only question that matters first: does
the game read this table, or a copy of it?

`--set-all` writes ONE distinctive score to every node in the table. If the table is
live, every kill in a scored campaign level then awards that number, whatever it is you
killed -- an unmissable, unambiguous answer from a single test, with no mapping needed.
`--restore` puts back exactly what was there, from a snapshot written next to this file.

Writing needs PROCESS_VM_WRITE, so run this elevated.
"""
import argparse
import collections
import ctypes
import ctypes.wintypes as w
import os
import re
import struct
import sys

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
TH32CS_SNAPPROCESS = 0x00000002
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_READABLE = (0x02, 0x04, 0x20, 0x40)

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

MCC_ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Halo The Master Chief Collection")
SCOREDB = os.path.join(MCC_ROOT, 'Data', 'UI', 'scoredb.xml')

# node layout, from the parser disassembly quoted above
N_COLOR, N_ISNIL, N_KEY, N_SCORE, N_SKULL = 0x18, 0x19, 0x1C, 0x20, 0x24
NODE_MIN = 0x28
# The plausible-score window the candidate filter uses. It has to stay WIDER than
# anything this tool itself writes: capped at 5000 it stopped finding the table the
# moment `--set-all 9999` had run, which also meant `--restore` could not find it back.
SCORE_MAX = 1e6


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ProcessID', w.DWORD),
                ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', w.DWORD), ('cntThreads', w.DWORD),
                ('th32ParentProcessID', w.DWORD), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', w.DWORD), ('szExeFile', ctypes.c_char * 260)]


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_ulonglong), ('AllocationBase', ctypes.c_ulonglong),
                ('AllocationProtect', w.DWORD), ('__alignment1', w.DWORD),
                ('RegionSize', ctypes.c_ulonglong), ('State', w.DWORD),
                ('Protect', w.DWORD), ('Type', w.DWORD), ('__alignment2', w.DWORD)]


def find_pid(name=b'MCC-Win64-Shipping.exe'):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32First(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == name.lower():
            return e.th32ProcessID
        ok = k32.Process32Next(snap, ctypes.byref(e))
    return None


def regions(h):
    mbi = MEMORY_BASIC_INFORMATION64()
    addr = 0
    while addr < (1 << 47):
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        if (mbi.State == MEM_COMMIT and mbi.Protect in PAGE_READABLE
                and mbi.Type == MEM_PRIVATE):
            # MEM_PRIVATE only: the table is heap-allocated, so image and file-mapped
            # regions cannot hold it and scanning them is pure cost -- they are most of
            # the process. Nothing else about the search changes.
            yield mbi.BaseAddress, mbi.RegionSize
        if mbi.RegionSize == 0:
            break
        addr = mbi.BaseAddress + mbi.RegionSize


def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf,
                                 ctypes.c_size_t(size), ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


# --- the bucket enums ---------------------------------------------------------
#
# Neither name is stored: the parser hashes each one and binary-searches a compare tree
# (`+207C7B0` for class, `+207C868` for type). The hash is **CRC-32/BZIP2 -- poly
# 0x04C11DB7, init 0xFFFFFFFF, no reflection, no xorout -- over the UPPERCASED name**,
# confirmed against all eight class constants.
#
# The values below were recovered by EMULATING those two functions with each name's
# hash and following the real control flow to the `mov eax, <enum>` it lands on. Reading
# the tree structurally instead was tried first and produced nonsense (two names sharing
# one value); emulation resolves 8/8 classes and 40/40 types with no duplicates.
CLASS_ENUM = {
    'infantry': 0, 'leader': 1, 'hero': 2, 'specialist': 3,
    'light_vehicle': 4, 'heavy_vehicle': 5, 'giant_vehicle': 6, 'standard_vehicle': 7,
}
TYPE_ENUM = {
    'brute': 0, 'grunt': 1, 'jackel': 2, 'skirmisher': 3, 'marine': 4, 'spartan': 5,
    'bugger': 6, 'hunter': 7, 'flood_carrier': 9, 'flood_combat': 10, 'flood_pure': 11,
    'sentinel': 12, 'elite': 13, 'engineer': 14, 'mule': 15, 'turret': 16,
    'mongoose': 17, 'warthog': 18, 'scorpion': 19, 'hornet': 20, 'pelican': 21,
    'revenant': 22, 'seraph': 23, 'shade': 24, 'ghost': 26, 'chopper': 27,
    'mauler': 28, 'wraith': 29, 'banshee': 30, 'phantom': 31, 'scarab': 32,
    'guntower': 33, 'tuning_fork': 34, 'lich': 37, 'bishop': 41, 'knight': 42,
    'pawn': 43, 'sabre': 46, 'space_banshee': 47, 'falcon': 48,
}
CLASS_PREFIX = '_campaign_metagame_bucket_class_'
TYPE_PREFIX = '_campaign_metagame_bucket_type_'


def xml_records(path=None):
    """{(class enum, type enum): (score, score_skull)} straight from scoredb.xml.

    Later rows win, which is what the game does too: the parser writes into the map by
    key, so a duplicate (class, type) overwrites the earlier one.
    """
    text = open(path or SCOREDB, encoding='utf-8').read()
    out = {}
    for row in re.finditer(r'<Enemy\b([^>]*)/?>', text):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', row.group(1)))
        c = CLASS_ENUM.get(str(attrs.get('class', '')).replace(CLASS_PREFIX, ''))
        t = TYPE_ENUM.get(str(attrs.get('type', '')).replace(TYPE_PREFIX, ''))
        if c is None or t is None or 'score' not in attrs:
            continue
        score = float(attrs['score'])
        skull = float(attrs.get('score_skull', score))
        out[(c << 16) | t] = (score, skull)
    return out


def push_from_xml(path=None, pid=None):
    """Mirror scoredb.xml into the RUNNING game's parsed table.

    This is the whole point of the module: MCC reads that file once at startup, so a
    fresh patch otherwise costs a full restart (and on this install, a Microsoft account
    login with it). Writing the same numbers straight into the parsed records makes the
    patch take effect where the game actually reads it.

    Keyed by (class, type), so it does not care what MCC loaded at startup or how far
    the file has drifted since -- afterwards, memory says exactly what the file says.

    Returns a report dict; `ok=False` with a reason when there is nothing to write to,
    which includes the ordinary case of MCC not running.
    """
    want = xml_records(path)
    if not want:
        return {'ok': False, 'reason': 'no usable rows in scoredb.xml'}
    pid = pid or find_pid()
    if not pid:
        return {'ok': False, 'reason': 'MCC is not running'}
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
                        | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)
    if not h:
        return {'ok': False, 'reason': 'OpenProcess failed (%d)'
                % ctypes.get_last_error()}
    rows = cached_rows(h, pid)
    cached = rows is not None
    if not cached:
        rows = find_table(h)
        if not rows:
            return {'ok': False,
                    'reason': 'score table not found in the running process'}
        save_addrs(pid, rows)
    save_snapshot(rows)
    done = missing = failed = 0
    for addr, key, _sc, _sk in rows:
        if key not in want:
            missing += 1
            continue
        sc, sk = want[key]
        if write(h, addr + N_SCORE, struct.pack('<ff', sc, sk)):
            done += 1
        else:
            failed += 1
    return {'ok': failed == 0 and done > 0, 'written': done, 'records': len(rows),
            'unmatched': missing, 'failed': failed, 'cached': cached,
            'reason': ('%d write(s) failed' % failed) if failed else None}


def find_table(h):
    """The score table's records, as [(addr, key, score, skull)].

    Picked as the biggest tree, not the best value match: once the scores have been
    rewritten they no longer resemble the file, and matching on values would lose the
    table exactly when it is needed. The size gap is not subtle -- 89 nodes against 1.
    """
    cache, trees = {}, collections.defaultdict(list)
    for addr, key, sc, sk in candidates(h):
        head = tree_head(h, addr, cache)
        if head:
            trees[head].append((addr, key, sc, sk))
    if not trees:
        return []
    best = max(trees.values(), key=len)
    return best if len(best) >= 20 else []


def write(h, addr, blob):
    got = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(addr), blob,
                                ctypes.c_size_t(len(blob)), ctypes.byref(got))
    return bool(ok) and got.value == len(blob)


SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'out', 'score_live_snapshot.json')


def _cache_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'out', 'score_live_addrs.json')


def save_addrs(pid, rows):
    """Remember this launch's node addresses so the next push can skip the scan."""
    import json
    os.makedirs(os.path.dirname(_cache_path()), exist_ok=True)
    with open(_cache_path(), 'w', encoding='utf-8') as f:
        json.dump({'pid': pid, 'nodes': [[a, k] for a, k, _s, _k in rows]}, f)


def cached_rows(h, pid):
    """The remembered nodes, re-read and re-verified, or None.

    A full scan reads ~2.5 GB and takes tens of seconds; with the live push wired into
    every patch that is a wait on every patch. The addresses only move when MCC does, so
    they are cached per pid and re-checked rather than re-found: every node must still
    carry the key it had, which is a cheap read and is enough to catch a stale cache
    (the pid guard already catches a restart, and Windows can recycle a pid).
    """
    import json
    p = _cache_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding='utf-8') as f:
            blob = json.load(f)
    except Exception:
        return None
    if blob.get('pid') != pid or not blob.get('nodes'):
        return None
    rows = []
    for addr, key in blob['nodes']:
        node = read(h, addr, NODE_MIN)
        if not node or struct.unpack_from('<I', node, N_KEY)[0] != key:
            return None
        sc, sk = struct.unpack_from('<ff', node, N_SCORE)
        rows.append((addr, key, sc, sk))
    return rows


def save_snapshot(rows):
    """Remember what was there before a write.

    Not a nicety: these values only exist in the running process, and the file on disk
    has usually moved on since MCC loaded it, so a botched write cannot be undone by
    re-reading scoredb.xml. The snapshot is keyed by (class, type) rather than by
    address, so it still applies after the heap has moved.
    """
    import json
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, 'w', encoding='utf-8') as f:
        json.dump([{'key': k, 'score': sc, 'skull': sk} for _a, k, sc, sk in rows],
                  f, indent=1)
    return SNAPSHOT


def load_snapshot():
    import json
    if not os.path.exists(SNAPSHOT):
        return None
    with open(SNAPSHOT, encoding='utf-8') as f:
        return {r['key']: (r['score'], r['skull']) for r in json.load(f)}


def xml_sections():
    """{section label: Counter of score values} from scoredb.xml.

    The file has an Enemies list and a Vehicles list; each becomes its own map in the
    game, so they are counted separately and matched separately.
    """
    text = open(SCOREDB, encoding='utf-8').read()
    out = {}
    for label in ('Enemies', 'Vehicles'):
        m = re.search(r'<%s>(.*?)</%s>' % (label, label), text, re.S)
        if not m:
            continue
        out[label] = collections.Counter(
            float(v) for v in re.findall(r'\bscore="([\d.]+)"', m.group(1)))
    return out


def candidates(h):
    """Every address that looks like one of these tree nodes."""
    out = []
    for base, size in regions(h):
        if size > 64 << 20:
            continue
        data = read(h, base, size)
        if not data:
            continue
        for off in range(0, len(data) - NODE_MIN, 8):
            if data[off + N_COLOR] > 1 or data[off + N_ISNIL] > 1:
                continue
            key = struct.unpack_from('<I', data, off + N_KEY)[0]
            # NOT `key == 0`: infantry is class 0 and brute is type 0, so the Brute
            # Minor record -- one of the most common kills in the game -- has key 0.
            # Rejecting it as noise silently dropped it from every scan.
            if (key & 0xFFFF) > 0x40 or (key >> 16) > 0x40:
                continue
            sc, sk = struct.unpack_from('<ff', data, off + N_SCORE)
            if not (1.0 <= sc <= SCORE_MAX and float(sc).is_integer()):
                continue
            if sk != 0.0 and not (1.0 <= sk <= SCORE_MAX and float(sk).is_integer()):
                continue
            left, parent, right = struct.unpack_from('<QQQ', data, off)
            if not all(0x10000 < p < (1 << 47) for p in (left, parent, right)):
                continue
            out.append((base + off, key, sc, sk))
    return out


def tree_head(h, node, cache, depth=64):
    """Walk `_Parent` to the tree's head node. Every node of one std::map reaches the
    same head, which is what lets candidates be grouped into ACTUAL maps instead of by
    address proximity -- two unrelated allocations can share a page, and two halves of
    one map need not."""
    if node in cache:
        return cache[node]
    seen, cur = [], node
    for _ in range(depth):
        blob = read(h, cur, 0x20)
        if not blob or len(blob) < 0x20:
            return None
        parent = struct.unpack_from('<Q', blob, 0x08)[0]
        isnil = blob[N_ISNIL]
        if isnil == 1:
            break
        if not (0x10000 < parent < (1 << 47)) or parent == cur:
            return None
        seen.append(cur)
        cur = parent
    else:
        return None
    for s in seen:
        cache[s] = cur
    cache[node] = cur
    return cur


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dump', action='store_true', help='print every record found')
    ap.add_argument('--set-all', type=float, metavar='N',
                    help='write N as the score of EVERY record (the viability test)')
    ap.add_argument('--restore', action='store_true',
                    help='write back the values saved by the last --set-all')
    ap.add_argument('--push', action='store_true',
                    help='mirror scoredb.xml into the running game (no restart)')
    a = ap.parse_args(argv)
    writing = a.set_all is not None or a.restore or a.push

    if a.push:
        rep = push_from_xml()
        print('push: %s' % rep)
        return 0 if rep.get('ok') else 1

    want = xml_sections()
    for label, counter in want.items():
        print('scoredb.xml <%s>: %d entries, %d distinct values'
              % (label, sum(counter.values()), len(counter)))

    pid = find_pid()
    if not pid:
        print('\nMCC is not running \u2014 nothing to read.')
        return 1
    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if writing:
        access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
    h = k32.OpenProcess(access, False, pid)
    if not h:
        print('\nOpenProcess failed (%d). Run this elevated.' % ctypes.get_last_error())
        return 1
    print('\nMCC pid %d' % pid)

    cands = candidates(h)
    print('node-shaped candidates: %d' % len(cands))
    cache = {}
    trees = collections.defaultdict(list)
    for addr, key, sc, sk in cands:
        head = tree_head(h, addr, cache)
        if head:
            trees[head].append((addr, key, sc, sk))
    print('distinct trees: %d' % len(trees))

    ranked = []
    for head, lst in trees.items():
        got = collections.Counter(x[2] for x in lst)
        for label, counter in want.items():
            overlap = sum((got & counter).values())
            ranked.append((overlap, len(lst), head, label, lst))
    ranked.sort(reverse=True)
    # Always show the biggest tree, whatever its overlap. Ranking on overlap alone hid
    # the table the moment --set-all had run: 88 nodes reading 9999 match nothing, so a
    # one-node coincidence outranked the thing we came for.
    if ranked:
        biggest = max(ranked, key=lambda r: r[1])
        ranked = [biggest] + [r for r in ranked if r is not biggest]

    for overlap, n, head, label, lst in ranked[:4]:
        print('\n== tree head 0x%X  %d node(s)  \u2014 %d/%d match <%s>'
              % (head, n, overlap, sum(want[label].values()), label))
        if a.dump or overlap:
            for addr, key, sc, sk in sorted(lst, key=lambda t: t[1])[:40]:
                print('   0x%012X  class=%-3d type=%-3d score=%-6g skull=%g'
                      % (addr, key >> 16, key & 0xFFFF, sc, sk))
    if not writing:
        return 0

    rows = max((r[4] for r in ranked), key=len, default=[])
    if len(rows) < 20:
        print('\nRefusing to write: no tree big enough to be the score table.')
        return 1

    if a.restore:
        snap = load_snapshot()
        if not snap:
            print('\nNo snapshot at %s \u2014 nothing to restore.' % SNAPSHOT)
            return 1
        done = miss = 0
        for addr, key, _sc, _sk in rows:
            if key not in snap:
                miss += 1
                continue
            sc, sk = snap[key]
            if write(h, addr + N_SCORE, struct.pack('<ff', sc, sk)):
                done += 1
        print('\nrestored %d record(s)%s'
              % (done, ', %d not in the snapshot' % miss if miss else ''))
        return 0

    path = save_snapshot(rows)
    print('\nsnapshot of the current values: %s' % path)
    val = float(a.set_all)
    done = 0
    for addr, key, _sc, sk in rows:
        # score_skull goes too: the scoring path takes the LARGER of the two, so
        # leaving the skull value alone would mask the test on every enemy that has
        # one (the Brute rows do).
        if write(h, addr + N_SCORE, struct.pack('<ff', val, val)):
            done += 1
    print('wrote %g to %d of %d record(s)' % (val, done, len(rows)))
    if done < len(rows):
        print('  (%d failed \u2014 run elevated)' % (len(rows) - done))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

r"""Which map files does MCC hold open right now, and how? READ-ONLY.

Halo 3 cannot be patched from the post-game summary screen (user, 2026-11-05): the
next map stays locked until it has been started and quit. Halo 1 and 2 patch fine
there. Before anything can release that lock we need to know what holds it:

  * WHICH files are open (the next map? the finished one? shared/campaign?)
  * HOW: the access each handle was granted (read only? write?)
  * whether the open allowed renames (FILE_SHARE_DELETE) or writes (FILE_SHARE_WRITE),
    found by trying to open the file ourselves with that access and closing at once
  * how many handles, and the handle's current file position

Nothing here writes to a map or touches MCC's memory: handles are DUPLICATED into this
process to read their names and closed again; the share tests open with no data
access and close immediately. Each run appends one row per file to
reports/mcc_map_locks.jsonl with the --note you give it (the condition: which screen).

    python mcc_map_locks.py --note "H3 summary screen after 010"
    python mcc_map_locks.py --all          # every file MCC has open, not only maps
"""
import argparse
import ctypes
import ctypes.wintypes as W
import datetime
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'reports', 'mcc_map_locks.jsonl')
MCC_EXE = 'mcc-win64-shipping.exe'

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll')

PROCESS_DUP_HANDLE = 0x0040
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DUPLICATE_SAME_ACCESS = 0x2
SystemExtendedHandleInformation = 64
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
FILE_TYPE_DISK = 1
GENERIC_READ, GENERIC_WRITE, DELETE = 0x80000000, 0x40000000, 0x00010000
FILE_READ_ATTRIBUTES = 0x80
SHARE_ALL = 0x7
OPEN_EXISTING = 3
INVALID = W.HANDLE(-1).value

ACCESS_BITS = [(0x1, 'read_data'), (0x2, 'write_data'), (0x4, 'append'),
               (0x10000, 'delete'), (0x80, 'read_attr'), (0x100, 'write_attr'),
               (0x100000, 'synchronize')]


class HANDLE_ENTRY(ctypes.Structure):
    _fields_ = [('Object', ctypes.c_void_p), ('UniqueProcessId', ctypes.c_size_t),
                ('HandleValue', ctypes.c_size_t), ('GrantedAccess', W.ULONG),
                ('CreatorBackTraceIndex', W.USHORT), ('ObjectTypeIndex', W.USHORT),
                ('HandleAttributes', W.ULONG), ('Reserved', W.ULONG)]


k32.CreateFileW.restype = W.HANDLE
k32.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD,
                            W.DWORD, W.HANDLE]
k32.OpenProcess.restype = W.HANDLE
k32.GetCurrentProcess.restype = W.HANDLE
k32.DuplicateHandle.argtypes = [W.HANDLE, W.HANDLE, W.HANDLE, ctypes.POINTER(W.HANDLE),
                                W.DWORD, W.BOOL, W.DWORD]
k32.GetFileType.argtypes = [W.HANDLE]
k32.CloseHandle.argtypes = [W.HANDLE]
k32.GetFinalPathNameByHandleW.argtypes = [W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD]
k32.SetFilePointerEx.argtypes = [W.HANDLE, ctypes.c_longlong,
                                 ctypes.POINTER(ctypes.c_longlong), W.DWORD]


def mcc_pids():
    import subprocess
    out = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True,
                         text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0].lower() == MCC_EXE:
            pids.append(int(parts[1]))
    return pids


def system_handles():
    size = 1 << 20
    while True:
        buf = ctypes.create_string_buffer(size)
        ret = W.ULONG(0)
        st = ntdll.NtQuerySystemInformation(SystemExtendedHandleInformation, buf, size,
                                            ctypes.byref(ret)) & 0xFFFFFFFF
        if st == STATUS_INFO_LENGTH_MISMATCH:
            size = max(size * 2, ret.value + (1 << 16))
            continue
        if st:
            raise OSError('NtQuerySystemInformation failed: 0x%08X' % st)
        n = ctypes.c_size_t.from_buffer(buf).value
        off = 2 * ctypes.sizeof(ctypes.c_size_t)
        arr = (HANDLE_ENTRY * n).from_buffer(buf, off)
        return list(arr)


def file_type_index():
    """The object type index of a File, read off a handle this process opens itself."""
    h = k32.CreateFileW(os.path.abspath(__file__), FILE_READ_ATTRIBUTES, SHARE_ALL,
                        None, OPEN_EXISTING, 0, None)
    try:
        me = os.getpid()
        for e in system_handles():
            if e.UniqueProcessId == me and e.HandleValue == h:
                return e.ObjectTypeIndex
    finally:
        k32.CloseHandle(h)
    raise OSError('could not find the File object type')


def handle_path(proc, value):
    dup = W.HANDLE()
    if not k32.DuplicateHandle(proc, W.HANDLE(value), k32.GetCurrentProcess(),
                               ctypes.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
        return None, (None, None)
    try:
        if k32.GetFileType(dup) != FILE_TYPE_DISK:     # pipes can hang a name query
            return None, (None, None)
        buf = ctypes.create_unicode_buffer(1024)
        n = k32.GetFinalPathNameByHandleW(dup, buf, 1024, 0)
        path = buf.value[4:] if n and buf.value.startswith('\\\\?\\') else (buf.value or None)
        pos = ctypes.c_longlong(0)
        # a move of 0 from the current position only READS the shared position
        posv = pos.value if k32.SetFilePointerEx(dup, 0, ctypes.byref(pos), 1) else None
        return path, (posv, _file_mode(dup))
    finally:
        k32.CloseHandle(dup)


FILE_MODE_BITS = [(0x2, 'write_through'), (0x4, 'sequential'), (0x8, 'no_buffering'),
                  (0x10, 'sync_alert'), (0x20, 'sync_nonalert'),
                  (0x1000, 'delete_on_close')]


def _file_mode(h):
    """FileModeInformation: no sync_* bit = the handle was opened OVERLAPPED (async)."""
    class IOSB(ctypes.Structure):
        _fields_ = [('Status', ctypes.c_void_p), ('Information', ctypes.c_size_t)]
    io, mode = IOSB(), W.ULONG(0)
    st = ntdll.NtQueryInformationFile(h, ctypes.byref(io), ctypes.byref(mode), 4, 16)
    if st & 0xFFFFFFFF:
        return None
    bits = [n for b, n in FILE_MODE_BITS if mode.value & b]
    return bits or ['overlapped']


def can_open(path, access):
    h = k32.CreateFileW(path, access, SHARE_ALL, None, OPEN_EXISTING, 0, None)
    if h in (None, INVALID):
        return False
    k32.CloseHandle(h)
    return True


def decode(mask):
    return [name for bit, name in ACCESS_BITS if mask & bit] + (
        ['generic:0x%X' % (mask & 0xF0000000)] if mask & 0xF0000000 else [])


CLUSTER = 0x400            # a map's handles this close together = one record

# The engine's precache state, per dll (RVAs). Halo 3: see h3_dll_patch.py. ODST found
# 2026-11-07 by matching halo3odst.dll's chooser (0x12DD10) against Halo 3's (0x10F20C):
# same slot table layout (0x4018 a slot, name at +0x1E8), same request record.
ENGINES = {
    'halo3.dll': dict(label='Halo 3', state_ptr=0xA46A08, req_name=0x2127004,
                      req_prio=0x2127104, slots=0x20BA420, count=0x1B, stride=0x4018,
                      name_at=0x1E8),
    'halo3odst.dll': dict(label='ODST', state_ptr=0xA9C9B8, req_name=0x2164FE4,
                          req_prio=0x21650E4, slots=0x2100430, count=0x19, stride=0x4018,
                          name_at=0x1E8),
    # Reach 2026-11-09: slot lookup 0x41588 walks 0x1C slots of 0xA040 from 0x263F5F0,
    # comparing the name at +0x1E0. Its chooser (0xAA090) hands the request to a call
    # instead of a global record, so there is no pending-request read yet.
    'haloreach.dll': dict(label='Reach', state_ptr=0xC1A230, req_name=None, req_prio=None,
                          slots=0x263F5F0, count=0x1C, stride=0xA040, name_at=0x1E0),
    # Halo 4 2026-11-09 (static only): slot lookup 0x7AAA4 walks 9 slots of 0x1E040 from
    # 0x2940188, comparing the name at +0. Its chooser (0x11E66C) tests the WORD at
    # [0x4967A30]+0xC (0 = the next-level branch may run), so that is the state shown.
    'halo4.dll': dict(label='Halo 4', state_ptr=0x4967A30, state_at=0xC, state_size=2,
                      req_name=None, req_prio=None,
                      slots=0x2940188, count=9, stride=0x1E040, name_at=0),
}
ENGINE_KEYS = {'halo3.dll': 'h3', 'halo3odst.dll': 'odst', 'haloreach.dll': 'reach',
               'halo4.dll': 'h4'}
SLOT = 0x4018              # Halo 3 / ODST slot size (Reach: ENGINES stride)
H3_STATE_PTR = ENGINES['halo3.dll']['state_ptr']   # game state byte: 2 = in game


def engine_state(pid, dll='halo3.dll'):
    """The precache state, read-only: game state, pending request, every named slot
    (1 shared and 2 campaign on Halo 3 / ODST; the levels sit higher up)."""
    sys.path.insert(0, HERE)
    import h2_memscan as M
    e = ENGINES[dll]
    base, _size = M.module_base(pid, dll)
    if not base:
        return None
    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    try:
        raw = M.read(h, base + e['state_ptr'], 8)
        ptr = struct.unpack('<Q', raw)[0] if raw else 0
        n = e.get('state_size', 1)
        sb = M.read(h, ptr + e.get('state_at', 0), n) if ptr else None
        name = prio = None
        if e['req_name']:
            name = (M.read(h, base + e['req_name'], 0x100) or b'').split(bytes(1))[0]
            name = name.decode('latin-1')
            pr = M.read(h, base + e['req_prio'], 4)
            prio = struct.unpack('<i', pr)[0] if pr else None
        slots = {}
        for i in range(e['count']):
            b = M.read(h, base + e['slots'] + i * e['stride'] + e['name_at'], 0x100)
            nm = (b or b'').split(bytes(1))[0]
            if nm and all(32 <= c < 127 for c in nm):
                slots[i] = nm.decode('latin-1')
        return {'engine': e['label'],
                'game_state': int.from_bytes(sb, 'little') if sb else None,
                'request': name, 'request_prio': prio, 'level_slots': slots}
    finally:
        M.k32.CloseHandle(h)


def h3_state(pid):
    return engine_state(pid, 'halo3.dll')


def scan_memory(pid, row):
    """Where MCC keeps this map's handles and its name (READ-ONLY).

    The handle values are searched as u32 and u64 in every committed read/write
    region; a place where two or more of the map's handles sit within CLUSTER bytes is
    the engine's record of the open map. Addresses inside halo3.dll are given as
    module offsets -- a static slot there leads straight to the code that fills it.
    The map's base name is searched too (ASCII and UTF-16)."""
    import numpy as np
    sys.path.insert(0, HERE)
    import h2_memscan as M
    mods = {}
    for dll in ('halo3.dll', 'halo3odst.dll', 'MCC-Win64-Shipping.exe'):
        b, s = M.module_base(pid, dll)
        if b:
            mods[dll] = (b, s)

    def where(addr):
        for dll, (b, s) in mods.items():
            if b <= addr < b + s:
                return '%s+0x%X' % (dll, addr - b)
        return 'heap'

    h = M.k32.OpenProcess(M.PROCESS_QUERY_INFORMATION | M.PROCESS_VM_READ, False, pid)
    if not h:
        return {'error': 'cannot open MCC for reading: %d' % ctypes.get_last_error()}
    values = [int(x['value'], 16) for x in row['handles']]
    name = os.path.splitext(os.path.basename(row['path']))[0].lower().encode()
    needles = [name, name.decode().encode('utf-16-le')]
    regions = list(M.all_regions(h, cap=(1 << 36)))
    for dll, (b, s) in mods.items():     # module data is not always plain RW: add it
        regions.append((b, s))
    clusters, names = [], []
    try:
        for addr, size in regions:
            buf = M.read(h, addr, size)
            if not buf:
                continue
            a4 = np.frombuffer(buf[:len(buf) & ~3], dtype='<u4')
            hits = []
            for v in values:
                for i in np.nonzero(a4 == v)[0]:
                    hits.append((int(i) * 4, v))
            hits.sort()
            for k, (o, v) in enumerate(hits):
                near = {vv for oo, vv in hits if 0 <= oo - o < CLUSTER}
                if len(near) >= 2 and (not clusters or clusters[-1][0] < addr + o - CLUSTER):
                    at = addr + o
                    clusters.append((at, where(at), sorted('0x%X' % x for x in near)))
            low = buf.lower()
            for nd in needles:
                i = low.find(nd)
                while i >= 0 and len(names) < 200:
                    at = addr + i
                    s = buf[max(0, i - 64):i + 64]
                    names.append(('0x%X' % at, where(at), s.replace(b'\0', b'.').decode('latin-1')))
                    i = low.find(nd, i + 1)
    finally:
        M.k32.CloseHandle(h)
    out = {'clusters': [('0x%X' % a, w, v) for a, w, v in clusters[:100]],
           'names': names}
    print('    memory: %d handle record(s), %d name hit(s) for %s'
          % (len(clusters), len(names), row['path']))
    for a, w, v in out['clusters'][:20]:
        print('      record %s  %s  %s' % (a, w, ' '.join(v)))
    for a, w, s in [n for n in names if n[1] != 'heap'][:20]:
        print('      name   %s  %s' % (a, w))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--note', default='', help='the condition, e.g. "H3 summary after 010"')
    ap.add_argument('--all', action='store_true', help='every file, not only .map files')
    ap.add_argument('--no-log', action='store_true')
    ap.add_argument('--scan', action='store_true',
                    help="also find, in MCC's memory (read only), where each map's handles "
                         "and name are stored -- the engine's record of that map")
    a = ap.parse_args(argv)

    pids = mcc_pids()
    if not pids:
        print('MCC is not running.')
        return 1
    ftype = file_type_index()
    handles = system_handles()
    rows, when = {}, datetime.datetime.now().isoformat(timespec='seconds')
    for pid in pids:
        proc = k32.OpenProcess(PROCESS_DUP_HANDLE | PROCESS_QUERY_LIMITED_INFORMATION,
                               False, pid)
        if not proc:
            print('cannot open MCC (pid %d) for handle reading: error %d'
                  % (pid, ctypes.get_last_error()))
            return 2
        try:
            for e in handles:
                if e.UniqueProcessId != pid or e.ObjectTypeIndex != ftype:
                    continue
                path, info = handle_path(proc, e.HandleValue)
                if not path:
                    continue
                pos, mode = info
                if not a.all and not path.lower().endswith('.map'):
                    continue
                r = rows.setdefault(path.lower(), dict(
                    when=when, note=a.note, path=path, handles=[]))
                r['handles'].append(dict(value='0x%X' % e.HandleValue,
                                         access=decode(e.GrantedAccess),
                                         mask='0x%08X' % e.GrantedAccess, pos=pos,
                                         mode=mode))
        finally:
            k32.CloseHandle(proc)

    for r in rows.values():
        # what a second opener (the enhancer) is allowed to do while MCC holds it
        r['we_can_read'] = can_open(r['path'], GENERIC_READ)
        r['we_can_write'] = can_open(r['path'], GENERIC_WRITE)
        r['we_can_rename'] = can_open(r['path'], DELETE)
    out = sorted(rows.values(), key=lambda r: r['path'].lower())
    print('MCC pid %s, %d %s open%s' % (','.join(map(str, pids)), len(out),
                                        'file(s)' if a.all else 'map file(s)',
                                        (' -- ' + a.note) if a.note else ''))
    for r in out:
        print('  %s' % r['path'])
        for h in r['handles']:
            print('      handle %-6s %s  [%s]  pos %s  mode %s'
                  % (h['value'], h['mask'], ', '.join(h['access']), h['pos'],
                     ','.join(h['mode'] or ['?'])))
        print('      we can: read=%s write=%s rename=%s'
              % (r['we_can_read'], r['we_can_write'], r['we_can_rename']))
    for dll in ENGINES:
        st = None
        for pid in pids:
            st = engine_state(pid, dll) or st
        if st is None:
            continue
        print('  %s: game state %s, pending precache %r (priority %s), level slots %s'
              % (st['engine'], st['game_state'], st['request'], st['request_prio'],
                 st['level_slots']))
        for r in out:
            r[ENGINE_KEYS[dll]] = st
    if a.scan and out:
        for pid in pids:
            for r in out:
                r['memory'] = scan_memory(pid, r)
    if not a.no_log and out:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            for r in out:
                f.write(json.dumps(r) + '\n')
        print('logged to', LOG)
    return 0


if __name__ == '__main__':
    sys.exit(main())

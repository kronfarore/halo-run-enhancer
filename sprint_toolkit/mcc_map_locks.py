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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--note', default='', help='the condition, e.g. "H3 summary after 010"')
    ap.add_argument('--all', action='store_true', help='every file, not only .map files')
    ap.add_argument('--no-log', action='store_true')
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
    if not a.no_log and out:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            for r in out:
                f.write(json.dumps(r) + '\n')
        print('logged to', LOG)
    return 0


if __name__ == '__main__':
    sys.exit(main())

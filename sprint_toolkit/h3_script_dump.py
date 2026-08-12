r"""Decompile the HaloScript in a Halo 3 / ODST scenario, straight out of the .map.

The last unexplored explanation for Kikowani's starting-weapon wall is the level's
own scripts (see the odst-kikowani-starting-weapons notes). Nothing in the repo could
read them, so this does: the scnr carries the compiled syntax tree verbatim --
`Scripts` @0x42C, `Globals` @0x438, `Script Expressions` @0x4DC and the string blob
behind the `Script Strings` dataRef @0x418 -- and that is enough to print source-shaped
HaloScript back out.

    python h3_script_dump.py sc150                 # every script, plus globals
    python h3_script_dump.py sc150 --grep weapon   # only scripts mentioning it
    python h3_script_dump.py sc150 --strings buck  # raw string-blob search
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402

MAPS = {
    'Halo 3: ODST': (r"C:\Program Files (x86)\Steam\steamapps\common"
                     r"\Halo The Master Chief Collection\halo3odst\maps"),
    'Halo 3': (r"C:\Program Files (x86)\Steam\steamapps\common"
               r"\Halo The Master Chief Collection\halo3\maps"),
}

SCRIPTS = 0x42C, 0x34
GLOBALS = 0x438, 0x28
EXPRS = 0x4DC, 0x18
STRINGS = 0x418

SCRIPT_TYPE = ['startup', 'dormant', 'continuous', 'static', 'command_script', 'stub']
# Value types we can print as a literal. Everything else falls back to the raw u32.
T_UNPARSED, T_SPECIAL, T_FUNCNAME, T_PASSTHROUGH = 0, 1, 2, 3
T_VOID, T_BOOL, T_REAL, T_SHORT, T_LONG, T_STRING, T_SCRIPT, T_STRINGID = range(4, 12)


def _dataref(m, off):
    """(file offset, size) of a dataRef's blob. A dataRef is 0x14 bytes: size at +0,
    two unused words, the pointer at +0xC, then one more unused word."""
    size = m.i32(off)
    ptr = m.u32(off + 0xC)
    return (m.data2off(ptr) if ptr else None), max(0, size)


class Blob:
    def __init__(self, m, off, size):
        self.raw = bytes(m.data[off:off + size]) if off else b''

    def at(self, o):
        if o is None or o < 0 or o >= len(self.raw):
            return None
        e = self.raw.find(b'\0', o)
        return self.raw[o:e if e >= 0 else len(self.raw)].decode('latin-1')


class Scripts:
    def __init__(self, m):
        self.m = m
        self.scnr = HP._scnr_base(m)
        so, ss = _dataref(m, self.scnr + STRINGS)
        self.strings = Blob(m, so, ss)
        self.n_expr = max(0, m.i32(self.scnr + EXPRS[0]))
        self.expr_base = HP._block_base(m, self.scnr + EXPRS[0])

    def expr(self, index):
        if not self.expr_base or not (0 <= index < self.n_expr):
            return None
        e = self.expr_base + index * EXPRS[1]
        d = self.m.data
        salt, opcode, vtype, flags = struct.unpack_from('<HHHH', d, e)
        nxt, soff = struct.unpack_from('<II', d, e + 8)
        # Little-endian, despite the plugin naming the bytes "Value 03 (MSB)".. "Value 00
        # (LSB)": read big-endian, every `sleep 60` becomes `sleep -1` and every gain of
        # 1.0 becomes a denormal. LE is what produces sane script text throughout.
        val = struct.unpack_from('<I', d, e + 0x10)[0]
        child = val & 0xFFFF                       # a group's first child expression
        return dict(index=index, salt=salt, opcode=opcode, vtype=vtype, flags=flags,
                    next=nxt, string=self.strings.at(soff), value=val, child=child, off=e)

    # --- printing -------------------------------------------------------------
    def literal(self, e):
        t, v = e['vtype'], e['value']
        if t == T_BOOL:
            return 'true' if (v & 0xFF) else 'false'
        if t == T_REAL:
            return '%g' % struct.unpack('<f', struct.pack('<I', v))[0]
        if t in (T_SHORT, T_LONG):
            return str(struct.unpack('<i', struct.pack('<I', v))[0]
                       if t == T_LONG else struct.unpack('<h', struct.pack('<H', v & 0xFFFF))[0])
        if e['string'] is not None:
            return '"%s"' % e['string'] if t == T_STRING else e['string']
        return '<%d:0x%08X>' % (t, v)

    def render(self, index, depth=0, seen=None):
        """One expression as source text. Groups recurse; a runaway tree is cut."""
        seen = seen if seen is not None else set()
        e = self.expr(index)
        if e is None:
            return '<bad expr %d>' % index
        if index in seen or depth > 60:
            return '...'
        seen = seen | {index}
        if e['flags'] & 0x1:                       # primitive: a value, not a call
            return self.literal(e)
        if e['vtype'] in (T_SPECIAL, T_FUNCNAME):  # the head of a call
            return e['string'] or 'op%d' % e['opcode']
        parts, child = [], e['child']              # group: value is the first child
        guard = 0
        while child != 0xFFFF and guard < 4096:
            parts.append(self.render(child, depth + 1, seen))
            nxt = self.expr(child)
            if nxt is None:
                break
            child = nxt['next'] & 0xFFFF
            if (nxt['next'] & 0xFFFF) == 0xFFFF:
                break
            guard += 1
        return '(' + ' '.join(parts) + ')'

    def scripts(self):
        m, out = self.m, []
        n = max(0, m.i32(self.scnr + SCRIPTS[0]))
        base = HP._block_base(m, self.scnr + SCRIPTS[0])
        for i in range(n) if base else []:
            e = base + i * SCRIPTS[1]
            name = m._cstr(e) if hasattr(m, '_cstr') else ''
            st, rt = struct.unpack_from('<HH', m.data, e + 0x20)
            root = m.u32(e + 0x24) & 0xFFFF
            out.append(dict(index=i, name=name, stype=st, rtype=rt, root=root))
        return out

    def globals(self):
        m, out = self.m, []
        n = max(0, m.i32(self.scnr + GLOBALS[0]))
        base = HP._block_base(m, self.scnr + GLOBALS[0])
        for i in range(n) if base else []:
            e = base + i * GLOBALS[1]
            out.append(dict(index=i, name=m._cstr(e),
                            gtype=m.i16(e + 0x20), root=m.u32(e + 0x24) & 0xFFFF))
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('map', help='map basename, e.g. sc150')
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(MAPS))
    ap.add_argument('--grep', help='only print scripts whose text contains this')
    ap.add_argument('--strings', help='search the raw script-string blob instead')
    ap.add_argument('--globals', action='store_true', help='print globals too')
    a = ap.parse_args(argv)

    path = os.path.join(MAPS[a.game], a.map + '.map')
    m = HP.open_map(path, a.game)
    s = Scripts(m)
    print('%s: %d expressions, %d bytes of script strings'
          % (a.map, s.n_expr, len(s.strings.raw)))

    if a.strings:
        raw, needle, hits = s.strings.raw, a.strings.lower().encode('latin-1'), 0
        i = raw.lower().find(needle)
        while i >= 0:
            start = raw.rfind(b'\0', 0, i) + 1
            end = raw.find(b'\0', i)
            print('  @0x%06X  %s' % (start, raw[start:end].decode('latin-1')))
            hits += 1
            i = raw.lower().find(needle, i + 1)
        print('  %d hit(s)' % hits)
        return 0

    if a.globals:
        for g in s.globals():
            print('(global %s = %s)' % (g['name'], s.render(g['root'])))
        print('')

    shown = 0
    for sc in s.scripts():
        body = s.render(sc['root'])
        if a.grep and a.grep.lower() not in body.lower() \
                and a.grep.lower() not in sc['name'].lower():
            continue
        shown += 1
        kind = SCRIPT_TYPE[sc['stype']] if sc['stype'] < len(SCRIPT_TYPE) else str(sc['stype'])
        print('; --- script %d ---' % sc['index'])
        print('(script %s %s\n  %s\n)\n' % (kind, sc['name'], body))
    print('; %d script(s) shown' % shown)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

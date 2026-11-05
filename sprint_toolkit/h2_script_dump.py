r"""Decompile the HaloScript in a Halo 2 scenario, straight out of the .map.

The Halo 2 sibling of h3_script_dump.py. The scnr carries the compiled tree:
`Scripts` @0x1B8 (0x28: name, type +0x20, return type +0x22, root datum +0x24),
`Globals` @0x1C0 (0x28: name, type +0x20, init datum +0x24), `Script Expressions`
@0x238 (0x14: salt, opcode, value type +0x4, flags +0x6, next +0x8, string +0xC,
value +0x10) and the literal blob behind `Script String Data` @0x1B0.

FUNCTION NAMES ARE OPCODES in Halo 2 (the string blob holds literals and script names
only), so a dump needs the engine's opcode table. That table is read out of the H2EK
tool.exe: an array of pointers to hs function definitions, each with its name pointer
at +4. Anchored on `sleep` = 0x13 and checked against the three opcodes the repo had
measured on the maps (hud_cinematic_fade 0x274, cinematic_show_letterbox 0x230,
cinematic_set_title 0x232 -- all three agree). It is cached in h2_opcodes.json.

    python h2_script_dump.py 08b_deltacontrol                    # every script
    python h2_script_dump.py 08b_deltacontrol --grep cannot_die  # scripts mentioning it
    python h2_script_dump.py 08b_deltacontrol --nodes --grep unit_set_maximum_vitality
    python h2_script_dump.py --build-opcodes                     # re-read tool.exe
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch as HP                                          # noqa: E402

MAPS = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo2\h2_maps_win64_dx11")
OPCODES_JSON = os.path.join(HERE, 'h2_opcodes.json')

SCRIPTS, GLOBALS, EXPRS, STRINGS = 0x1B8, 0x1C0, 0x238, 0x1B0
ELEM_SCRIPT, ELEM_GLOBAL, ELEM_EXPR = 0x28, 0x28, 0x14
SCRIPT_TYPE = ['startup', 'dormant', 'continuous', 'static', 'stub', 'command_script']
T_SPECIAL, T_FUNCNAME = 1, 2
T_VOID, T_BOOL, T_REAL, T_SHORT, T_LONG, T_STRING = 4, 5, 6, 7, 8, 9
NONE = 0xFFFFFFFF
# Expression flags (08b, measured): 0x1 primitive (a value, not a group), 0x2 the group
# calls one of the level's own scripts (opcode = script index, head string = its name),
# 0x4 a global reference (value = global index, string = its name), 0x8 set on all.
# A literal's string offset is NOT its name -- numbers carry stray source fragments.
F_PRIMITIVE, F_SCRIPT_CALL, F_GLOBAL_REF = 0x1, 0x2, 0x4
# Opcode anchors the table must reproduce; the first one positions it.
ANCHORS = {'sleep': 0x13, 'hud_cinematic_fade': 0x274,
           'cinematic_show_letterbox': 0x230, 'cinematic_set_title': 0x232}


# --- opcode table ------------------------------------------------------------------
def build_opcodes(tool_exe=None):
    """Read the hs function table out of H2EK tool.exe. Returns [name by opcode]."""
    if tool_exe is None:
        import h2_tagfield
        tool_exe = os.path.join(h2_tagfield.H2EK, 'tool.exe')
    d = open(tool_exe, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    ns = struct.unpack_from('<H', d, pe + 6)[0]
    opt = struct.unpack_from('<H', d, pe + 20)[0]
    if struct.unpack_from('<H', d, pe + 24)[0] != 0x10B:
        raise SystemExit('tool.exe is not the 32-bit H2EK build this reader expects')
    ib = struct.unpack_from('<I', d, pe + 24 + 28)[0]
    secs = [struct.unpack_from('<IIII', d, pe + 24 + opt + i * 40 + 8) for i in range(ns)]

    def va2o(v):
        for vs, va, rs, ro in secs:
            if ib + va <= v < ib + va + rs:
                return ro + v - ib - va
        return None

    def o2va(o):
        for vs, va, rs, ro in secs:
            if ro <= o < ro + rs:
                return ib + va + o - ro
        return None

    def cstr(o):
        return d[o:d.find(b'\0', o)].decode('latin-1')

    # sleep's definition is the one struct whose +4 points at "sleep"; the table entry
    # pointing at that struct is opcode 0x13.
    name_va = o2va(d.find(b'\0sleep\0') + 1)
    defs = []
    i = d.find(struct.pack('<I', name_va))
    while i >= 0:
        defs.append(o2va(i - 4))
        i = d.find(struct.pack('<I', name_va), i + 1)
    table = None
    for dv in defs:
        j = d.find(struct.pack('<I', dv))
        while j >= 0:
            cand = j - ANCHORS['sleep'] * 4
            names = _walk(d, cand, va2o, cstr)
            if all(names[op] == n for n, op in ANCHORS.items() if op < len(names)) \
                    and len(names) > max(ANCHORS.values()):
                table = names
                break
            j = d.find(struct.pack('<I', dv), j + 1)
        if table:
            break
    if not table:
        raise SystemExit('opcode table not found in %s' % tool_exe)
    return table


def _walk(d, base, va2o, cstr):
    names = []
    while True:
        o = va2o(struct.unpack_from('<I', d, base + len(names) * 4)[0])
        if o is None:
            break
        np_ = va2o(struct.unpack_from('<I', d, o + 4)[0])
        if np_ is None:
            break
        n = cstr(np_)
        if not n or not all(c.isalnum() or c in '_<>=+-*/!' for c in n):
            break
        names.append(n)
    return names


def opcodes():
    if not os.path.isfile(OPCODES_JSON):
        names = build_opcodes()
        with open(OPCODES_JSON, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'source': 'H2EK tool.exe hs function table (h2_script_dump.py)',
                       'names': names}, f, indent=0)
    with open(OPCODES_JSON, encoding='utf-8') as f:
        return json.load(f)['names']


def opcode(name):
    return opcodes().index(name)


# --- the tree ----------------------------------------------------------------------
class Scripts:
    def __init__(self, m):
        self.m = m
        self.scnr = HP._scnr_base(m)
        size = max(0, m.i32(self.scnr + STRINGS))
        ptr = m.u32(self.scnr + STRINGS + 4)
        so = m.p2o(ptr) if ptr else None
        self.blob = bytes(m.data[so:so + size]) if so else b''
        self.n_expr = max(0, m.i32(self.scnr + EXPRS))
        self.expr_base = HP._block_base(m, self.scnr + EXPRS)
        self.ops = opcodes()

    def string(self, off):
        if not (0 <= off < len(self.blob)):
            return None
        e = self.blob.find(b'\0', off)
        return self.blob[off:e if e >= 0 else len(self.blob)].decode('latin-1')

    def expr(self, index):
        if not self.expr_base or not (0 <= index < self.n_expr):
            return None
        e = self.expr_base + index * ELEM_EXPR
        salt, op, vtype, flags, nxt, soff, val = struct.unpack_from('<HHHHIII',
                                                                     self.m.data, e)
        return dict(index=index, salt=salt, opcode=op, vtype=vtype, flags=flags,
                    next=nxt, string=self.string(soff), value=val, child=val & 0xFFFF,
                    off=e)

    def name(self, e):
        return self.ops[e['opcode']] if e['opcode'] < len(self.ops) else 'op%d' % e['opcode']

    def literal(self, e):
        t, v = e['vtype'], e['value']
        if t == T_BOOL:
            return 'true' if (v & 0xFF) else 'false'
        if t == T_REAL:
            return '%g' % struct.unpack('<f', struct.pack('<I', v))[0]
        if t == T_SHORT:
            return str(struct.unpack('<h', struct.pack('<H', v & 0xFFFF))[0])
        if t == T_LONG:
            return str(struct.unpack('<i', struct.pack('<I', v))[0])
        if e['string'] is not None:
            return '"%s"' % e['string'] if t == T_STRING else e['string']
        return '<%d:0x%08X>' % (t, v)

    def children(self, index):
        """Indices of a group's members (the function-name node first)."""
        e = self.expr(index)
        out, child, guard = [], e['child'] if e else 0xFFFF, 0
        while child != 0xFFFF and guard < 4096:
            out.append(child)
            c = self.expr(child)
            if c is None or c['next'] == NONE:
                break
            child, guard = c['next'] & 0xFFFF, guard + 1
        return out

    def render(self, index, depth=0, nodes=False):
        e = self.expr(index)
        if e is None:
            return '<bad expr %d>' % index
        tag = ('#%d' % index) if nodes else ''
        if depth > 80:
            return '...'
        if e['flags'] & F_PRIMITIVE:
            if e['vtype'] in (T_SPECIAL, T_FUNCNAME):
                return self.name(e)
            if e['flags'] & F_GLOBAL_REF:          # value = the global's index
                return (e['string'] or 'global%d' % (e['value'] & 0xFFFF)) + tag
            if e['vtype'] == T_VOID:               # an empty else of a compiled cond
                return 'none' + tag
            return self.literal(e) + tag
        kids = self.children(index)
        parts = [self.render(c, depth + 1, nodes) for c in kids]
        if e['flags'] & F_SCRIPT_CALL and kids:    # a call to one of the level's scripts:
            head = self.expr(kids[0])               # opcode = script index, string = name
            parts[0] = head['string'] or 'script%d' % e['opcode']
        return '(' + ' '.join(parts) + ')' + tag

    def scripts(self):
        m, out = self.m, []
        n = max(0, m.i32(self.scnr + SCRIPTS))
        base = HP._block_base(m, self.scnr + SCRIPTS)
        for i in range(n) if base else []:
            e = base + i * ELEM_SCRIPT
            st, rt = struct.unpack_from('<HH', m.data, e + 0x20)
            out.append(dict(index=i, name=m._cstr(e), stype=st, rtype=rt,
                            root=m.u32(e + 0x24) & 0xFFFF))
        return out

    def globals(self):
        m, out = self.m, []
        n = max(0, m.i32(self.scnr + GLOBALS))
        base = HP._block_base(m, self.scnr + GLOBALS)
        for i in range(n) if base else []:
            e = base + i * ELEM_GLOBAL
            out.append(dict(index=i, name=m._cstr(e), gtype=m.u32(e + 0x20) & 0xFFFF,
                            root=m.u32(e + 0x24) & 0xFFFF))
        return out

    def calls(self, fname):
        """Every call group whose head is `fname`: [(group index, [arg indices])]."""
        want, out = opcode(fname), []
        for i in range(self.n_expr):
            e = self.expr(i)
            if e is None or e['flags'] & F_PRIMITIVE or e['child'] == 0xFFFF:
                continue
            head = self.expr(e['child'])
            if head and head['vtype'] == T_FUNCNAME and head['opcode'] == want \
                    and head['flags'] & F_PRIMITIVE:
                out.append((i, self.children(i)[1:]))
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('map', nargs='?', help='map basename, e.g. 08b_deltacontrol')
    ap.add_argument('--path', help='a .map path instead of the deployed one')
    ap.add_argument('--grep', help='only print scripts whose text contains this')
    ap.add_argument('--globals', action='store_true', help='print globals too')
    ap.add_argument('--nodes', action='store_true', help='tag each group/literal #index')
    ap.add_argument('--build-opcodes', action='store_true',
                    help='re-read the opcode table from H2EK tool.exe')
    a = ap.parse_args(argv)

    if a.build_opcodes:
        if os.path.isfile(OPCODES_JSON):
            os.remove(OPCODES_JSON)
        print('%d opcodes -> %s' % (len(opcodes()), OPCODES_JSON))
        if not a.map:
            return 0
    if not a.map and not a.path:
        ap.error('map required')
    path = a.path or os.path.join(MAPS, a.map + '.map')
    m = HP.open_map(path, 'Halo 2')
    s = Scripts(m)
    print('%s: %d expressions, %d bytes of script strings'
          % (os.path.basename(path), s.n_expr, len(s.blob)))
    if a.globals:
        for g in s.globals():
            print('(global %s = %s)' % (g['name'], s.render(g['root'], nodes=a.nodes)))
        print('')
    shown = 0
    for sc in s.scripts():
        body = s.render(sc['root'], nodes=a.nodes)
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

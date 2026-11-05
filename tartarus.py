r"""Tartarus on The Great Journey (Halo 2, 08b_deltacontrol): health multiplier and a
killable option. Patch-time edits of the compiled boss script.

HOW THE STOCK FIGHT WORKS (08b_deltacontrol_boss.hsc, compiled tree read with
sprint_toolkit/h2_script_dump.py)
    boss_setup: (ai_cannot_die boss_tartarus TRUE), then per difficulty
        (unit_set_maximum_vitality (ai_get_unit boss_tartarus) 400|350|300 1000)
        (unit_set_current_vitality (ai_get_unit boss_tartarus) 50 1000)
    tartarus_boss_fight: (unit_set_current_vitality ... 50 1000) once more, then one
    big (sleep_until (cond ...) 1). The shield window opens below 0.9 / 0.95 / 0.975
    of his shield; each time his health is held at the cannot-die floor
    (ai_vitality_pinned) a phase ends -- count_boss_cycle 4 / 3 / 2 -- and the same
    per-difficulty unit_set_maximum_vitality runs again. Only the LAST phase ends the
    loop, by killing him itself. So the vitality cards never matter: the script sets
    his health outright, every phase.

TARTARUS HP x
    Scales the HEALTH argument (the first real) of every unit_set_maximum_vitality /
    unit_set_current_vitality call whose unit is (ai_get_unit boss_tartarus): the three
    setup maxima, the three per-phase maxima, and both 50s. The shield argument (1000)
    is left alone -- his shield is the script's invincibility switch, not a health pool.

TARTARUS: KILLABLE
    Flips (ai_cannot_die boss_tartarus TRUE) in boss_setup to FALSE. He then dies when
    his health runs out instead of being pinned, so there are no phases: the fight is
    one health bar (the 50 above, times HP x).
    THE STOCK LOOP CANNOT END ON HIS DEATH: a dead actor is never pinned, and the
    "Tartarus left the platform" branch would teleport his corpse forever -- the
    mission would hang. sprint_toolkit/h2_tartarus_kit.py adds a first cond clause
    to the kit source, ((<= (ai_living_count boss_tartarus) 0) TRUE), which is inert
    while he cannot die and ends the fight (straight into the stock outro) once he can.
    This option REFUSES to run on a map without that clause (fight_end_branch()).
"""
import struct

EXPRS, ELEM = 0x238, 0x14              # scnr Script Expressions (Halo 2)
SCRIPTS, ELEM_SCRIPT = 0x1B8, 0x28     # scnr Scripts
STRINGS = 0x1B0                        # Script String Data
NONE = 0xFFFFFFFF
F_PRIMITIVE = 0x1
T_FUNCNAME, T_BOOL, T_REAL, T_SHORT, T_AI = 2, 5, 6, 7, 0x13
# Engine opcodes, from the H2EK tool.exe hs function table (sprint_toolkit/h2_opcodes.json;
# the table reproduces the four opcodes measured on the maps before it was read).
OP = {'if': 0x02, '<=': 0x12, 'sleep_until': 0x15, 'unit_set_maximum_vitality': 0xE5,
      'unit_set_current_vitality': 0xE7, 'ai_get_unit': 0x11E, 'ai_cannot_die': 0x126,
      'ai_living_count': 0x148}
BOSS = 'boss_tartarus'
LEVEL_SCRIPTS = ('boss_setup', 'tartarus_boss_fight')
HP_RANGE = (0.1, 20.0)


class _Tree:
    def __init__(self, m, scnr_base, block_base):
        self.m, self.d = m, m.data
        self.n = max(0, m.i32(scnr_base + EXPRS))
        self.base = block_base(m, scnr_base + EXPRS)
        size = max(0, m.i32(scnr_base + STRINGS))
        ptr = m.u32(scnr_base + STRINGS + 4)
        so = m.p2o(ptr) if ptr else None
        self.blob = bytes(m.data[so:so + size]) if so else b''
        ns = max(0, m.i32(scnr_base + SCRIPTS))
        sb = block_base(m, scnr_base + SCRIPTS) if ns else None
        self.scripts = {}
        for i in range(ns if sb else 0):
            e = sb + i * ELEM_SCRIPT
            name = bytes(m.data[e:e + 0x20]).split(b'\0')[0].decode('latin-1')
            self.scripts[name] = m.u32(e + 0x24) & 0xFFFF

    def at(self, i):
        if not self.base or not (0 <= i < self.n):
            return None
        e = self.base + i * ELEM
        salt, op, vt, fl, nxt, so, val = struct.unpack_from('<HHHHIII', self.d, e)
        s = None
        if 0 <= so < len(self.blob):
            s = self.blob[so:self.blob.find(b'\0', so)].decode('latin-1')
        return dict(i=i, op=op, vt=vt, fl=fl, next=nxt, string=s, value=val, off=e)

    def kids(self, i):
        r = self.at(i)
        if r is None or r['fl'] & F_PRIMITIVE:
            return []
        out, c = [], r['value'] & 0xFFFF
        while c != 0xFFFF and len(out) < 4096:
            out.append(c)
            n = self.at(c)
            if n is None or n['next'] == NONE:
                break
            c = n['next'] & 0xFFFF
        return out

    def call(self, i):
        """(function name opcode, [arg indices]) of an engine call group, else None."""
        k = self.kids(i)
        if not k:
            return None
        g, h = self.at(i), self.at(k[0])
        if g['fl'] & 0x2 or h['vt'] != T_FUNCNAME:      # 0x2 = call to a level script
            return None
        return h['op'], k[1:]

    def reach(self, root):
        """Every expression index under `root` (the script's whole body)."""
        seen, stack = set(), [root]
        while stack:
            i = stack.pop()
            if i in seen or self.at(i) is None:
                continue
            seen.add(i)
            stack.extend(self.kids(i))
        return seen

    def is_boss(self, i):
        r = self.at(i)
        return bool(r and r['fl'] & F_PRIMITIVE and r['vt'] == T_AI and r['string'] == BOSS)

    def boss_unit(self, i):
        c = self.call(i)
        return bool(c and c[0] == OP['ai_get_unit'] and len(c[1]) == 1 and self.is_boss(c[1][0]))

    def real(self, i):
        return struct.unpack_from('<f', self.d, self.at(i)['off'] + 0x10)[0]

    def set_real(self, i, v):
        struct.pack_into('<f', self.d, self.at(i)['off'] + 0x10, v)


def _tree(m, scnr_base, block_base):
    t = _Tree(m, scnr_base, block_base)
    if not t.base or not all(s in t.scripts for s in LEVEL_SCRIPTS):
        return None
    return t


def _body(t):
    out = set()
    for s in LEVEL_SCRIPTS:
        out |= t.reach(t.scripts[s])
    return out


def vitality_sites(t):
    """[(call group, health arg index)] for every Tartarus max/current vitality call."""
    out = []
    for i in sorted(_body(t)):
        c = t.call(i)
        if not c or c[0] not in (OP['unit_set_maximum_vitality'],
                                 OP['unit_set_current_vitality']):
            continue
        args = c[1]
        if len(args) == 3 and t.boss_unit(args[0]) and t.at(args[1])['vt'] == T_REAL \
                and t.at(args[1])['fl'] & F_PRIMITIVE:
            out.append((i, args[1]))
    return out


def cannot_die_sites(t):
    """[bool arg index] of every (ai_cannot_die boss_tartarus TRUE) in boss_setup."""
    out = []
    for i in sorted(t.reach(t.scripts['boss_setup'])):
        c = t.call(i)
        if c and c[0] == OP['ai_cannot_die'] and len(c[1]) == 2 and t.is_boss(c[1][0]):
            b = t.at(c[1][1])
            if b['vt'] == T_BOOL and b['fl'] & F_PRIMITIVE and b['value'] & 0xFF:
                out.append(c[1][1])
    return out


def fight_end_branch(t):
    """Is there an `if` in tartarus_boss_fight testing (<= (ai_living_count
    boss_tartarus) 0)? (A cond compiles to nested ifs.) The kit edit's marker."""
    for i in t.reach(t.scripts['tartarus_boss_fight']):
        c = t.call(i)
        if not c or c[0] != OP['if'] or not c[1]:
            continue
        test = t.call(c[1][0])
        if not test or test[0] != OP['<='] or len(test[1]) != 2:
            continue
        lc = t.call(test[1][0])
        zero = t.at(test[1][1])
        if lc and lc[0] == OP['ai_living_count'] and len(lc[1]) == 1 \
                and t.is_boss(lc[1][0]) and zero['fl'] & F_PRIMITIVE \
                and (zero['value'] & 0xFFFF) == 0:
            return True
    return False


def apply(m, scnr_base, block_base, hp_mult=1.0, killable=False):
    """Returns a list of result dicts (empty when there is nothing to do)."""
    hp_mult = float(hp_mult or 1.0)
    if abs(hp_mult - 1.0) < 1e-6 and not killable:
        return []
    t = _tree(m, scnr_base, block_base)
    if t is None:
        return [{'effect': 'Tartarus', 'ok': True, 'skip': True,
                 'reason': 'no Tartarus fight on this level'}]
    out = []
    if abs(hp_mult - 1.0) >= 1e-6:
        mult = min(max(hp_mult, HP_RANGE[0]), HP_RANGE[1])
        sites = vitality_sites(t)
        olds = [t.real(a) for _g, a in sites]
        for (_g, a), v in zip(sites, olds):
            t.set_real(a, v * mult)
        out.append({'effect': 'Tartarus HP', 'ok': len(sites) == 8,
                    'field': 'boss script health',
                    'old': ', '.join('%g' % v for v in olds),
                    'new': ', '.join('%g' % t.real(a) for _g, a in sites),
                    **({} if len(sites) == 8 else
                       {'reason': 'expected 8 health arguments, found %d' % len(sites)})})
    if killable:
        sites = cannot_die_sites(t)
        if not fight_end_branch(t):
            out.append({'effect': 'Tartarus killable', 'ok': False,
                        'reason': "this 08b was built without the 'Tartarus dead ends the "
                                  "fight' branch -- run sprint_toolkit/h2_tartarus_kit.py "
                                  "--apply and h2_rebuild_all.py --maps 08b; left as stock "
                                  "so the mission cannot hang"})
        elif len(sites) != 1:
            out.append({'effect': 'Tartarus killable', 'ok': False,
                        'reason': 'expected one (ai_cannot_die boss_tartarus TRUE), found %d'
                                  % len(sites)})
        else:
            a = t.at(sites[0])
            struct.pack_into('<B', t.d, a['off'] + 0x10, 0)
            out.append({'effect': 'Tartarus killable', 'ok': True,
                        'field': 'ai_cannot_die boss_tartarus', 'old': 'TRUE', 'new': 'FALSE'})
    return out

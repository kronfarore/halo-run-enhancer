r"""player_armour.py -- give the PLAYER its own damage-table armour rows (Halo 2, Halo 3,
ODST, Reach, Halo 4), so later "Effective" cards can change enemy rows without touching
the player.

From Halo 2 on, what a hit does to an object is the matg Damage Table row named by the
object's material's armour (Specific Armor if a row exists, else General Armor), and the
player shares those armour names with enemies: H2/H3 Arbiter = the Elite materials, the
H3/ODST `_player` specific rows exist only in the native Tilt table [1] (and sit on the
Elite materials too), the ODST body is tough_organic_flesh (the Brute row), the Reach/H4
Spartan materials are also worn by AI Spartans, armour lock sections and the Broadsword.

    apply(m, game, registry=None) -> list of result rows

1. PLAYER BIPEDS: every matg Player Representation entry's Third Person Unit plus the
   scenario's Override Player Representations (H3 and later), bipd only; holograms and
   the Forge monitor are skipped.
2. Each biped -> its model (hlmt). Every hlmt field that holds a matg MATERIAL INDEX is
   collected: Materials/Model Materials/Old Materials 'Global Material Index', New/Old
   Damage Info 'Shield' and 'Indirect Global Material Index', Reach/H4 Damage Sections
   'Shield Global Material Index' and the top-level 'Indirect Global Material Index'.
   NOT touched: hlmt material +0x8 / +0xA ('Collision/Damage Global Material Index' in the
   plugins) -- measured on every hlmt of 03a/010/sc100/m10/m10_crash they are model-local
   runtime indices (+0x8 == the element's own index, +0xA == -1 or small model indices),
   not matg indices. The *name* fields are left alone too: the clone keeps the original's
   Name, so resolving by name would land on the original either way, and on every
   baseline hlmt the stored index already equals the index of the stored name (the cache
   carries resolved indices).
3. CLONE each such material: the clone is a byte copy of the element the engine reads --
   matg Materials in H2/H3/ODST, matg RUNTIME Materials in Reach/H4 (the authoring block
   there leaves General Armor unset on 161/201 entries; the runtime block carries the
   resolved General/Specific Armor, the parent index and, in Reach, the wet variants at
   201..391, so material indices in tags are runtime indices). The clone's General Armor
   = the original's own Name stringid (verified unused as an armour name in every damage
   table and on every material; when it is not -- Reach's armour-lock material
   energy_shield_invulnerable is its own armour name -- the wet partner's Name is used,
   else the material stays shared and a failed row says so), Specific Armor = none. In
   Reach a dry material with a wet variant gets a wet clone too (cross-linked wet/dry
   indices; same key when the wet armour equals the dry). Only the player hlmts are
   repointed. COPY-ON-WRITE: where a player hlmt's material array is the same array a
   non-player hlmt uses (H3 dervish / dervish_ai, Reach spartans / AI Spartans, H4
   storm_masterchief), the player hlmt first gets a private copy of that array.
   ARMOUR RESOLUTION: every element the engine reads already carries its armour FLATTENED
   (H2/H3/ODST Materials: General set on all but default_material; Reach/H4 runtime:
   Specific inherited from the parent, e.g. soft_organic_flesh_scarab gets
   soft_organic_flesh_hunter) -- the resolver below still walks the parent index for
   unset values, first set value up the chain, General and Specific independently.
4. ROWS: for every Damage Table element (incl. the native Tilt table [1]) and every Damage
   Group, the value the player gets today = the row of the material's Specific Armor if
   the group has one, else the row of its General Armor; if found, a row (key, value) is
   APPENDED to that group's Armor Modifiers. No row -> none added (engine default 1).
   SORTED ROWS (confirmed in halo3.dll / halo3odst.dll, 2026-10-07): the engine finds a
   damage group and then each armour row by BINARY SEARCH on the stringid, and MULTIPLIES
   every row it finds (jpt! general and specific group x material general and specific
   armour), a missing row counting 1. Every shipped array is sorted ascending; a grown
   one must be written sorted again (_sorted_rows) or rows are silently missed.
   RULE (`rule`, default 'multiply' -- the engine's own, see above). The clone has no Specific,
   so in a group where the old material had BOTH a specific and a general row, the player
   now gets the copied value alone; if the engine instead MULTIPLIES general x specific,
   those groups change. They exist only in H3/ODST (the `_player` rows: no_damage in
   table [0], where both rows are 0, and the H3 Tilt table [1]) and are listed in the
   'both-rows groups' result row. rule='multiply' copies general x specific instead.
   Evidence for multiply: the H3 Tilt `_player` rows cancel their general rows exactly
   (4 x 0.25, 2 x 0.5, 3 x 0.333 = 1; plasma_slow 3 x 0.1167 = 0.35).
5. IDEMPOTENT: an element later in the block with the same Name as a player material is
   our clone; existing clones and key rows are reused, nothing is written twice.

GROWTH. Halo 2: Halo2Map.grow_blocks (relocate to the end of the image, proven) and the
same append for private hlmt copies. Halo 3 and later: armour-row arrays and private hlmt
copies are relocated through halo_patch._h3_reserve (one call). The materials array is far
bigger than any zero run (H3 90 KB, ODST 92 KB, Reach runtime 166 KB, H4 runtime 86 KB;
largest runs measured 41-63 KB), so it is grown IN PLACE (plan_room / commit_room):
  'before': the whole blocks just before the array move into _h3_reserve slack and the
            array shifts down by k elements (H3 010/100, H4 m10_crash: matg's own blocks);
  'after' : the whole blocks just after the array move out and the clones follow it
            (ODST sc100: matg blocks; Reach m10: 58 snd! 'Extra Info' blocks -- the only
            option there, the authoring Materials array sits before the runtime one).
The smaller valid span wins; a span may not contain a tag header. Every pointer into a
moved range is found by scanning every partition for its encoded value and rewritten;
look-alike u32s are rejected unless they sit in a tagblock [count][ptr][0|CDCDCDCD], a
tag-data ref [size][fill][fill][ptr][fill] or the tag table (the scan meets 1-17 of them
per map in shader / render-method / HUD data). Mod-16 alignment of moved blocks is kept.
"""
import struct

import halo_patch as hp

EFFECT = 'Player armour'

#: Per-game offsets, all read from the Assembly MCC plugins (Halo2MCC, Halo3MCC, ODSTMCC,
#: ReachMCC, Halo4MCC) and checked against the baselines.
LAYOUT = {
    'Halo 2': dict(
        ref_id=4, model=0x34,
        prep=(0x138, 0xBC, 0xB0), scnr_prep=None,
        mats=(0x150, 0xB4), gen=0x10, spec=0x14, parent=0x8, wet=None,
        dt=(0xD0, 0x8), dg=0xC,
        hlmt_blocks=[(0x58, 0x14, (0x10,)), (0x60, 0xF8, (0xCC, 0xCE))], hlmt_top=()),
    'Halo 3': dict(
        ref_id=0xC, model=0x34,
        prep=(0x440, 0x5C, 0x28), scnr_prep=(0x720, 0x5C, 0x28),
        mats=(0x464, 0x170), gen=0xC, spec=0x10, parent=0x8, wet=None,
        dt=(0x3EC, 0xC), dg=0x10,
        hlmt_blocks=[(0x7C, 0x14, (0x10,)), (0x88, 0xA4, (0x80, 0x82))], hlmt_top=()),
    'Halo 3: ODST': dict(
        ref_id=0xC, model=0x34,
        prep=(0x450, 0x5C, 0x28), scnr_prep=(0x760, 0x5C, 0x28),
        mats=(0x480, 0x178), gen=0xC, spec=0x10, parent=0x8, wet=None,
        dt=(0x3FC, 0xC), dg=0x10,
        hlmt_blocks=[(0x88, 0x14, (0x10,)), (0x94, 0xA4, (0x80, 0x82))], hlmt_top=()),
    'Halo Reach': dict(
        ref_id=0xC, model=0x64,
        prep=(0x474, 0x6C, 0x34), scnr_prep=(0x794, 0x6C, 0x34),
        mats=(0x658, 0x1A8), gen=0xC, spec=0x10, parent=0x8, wet=(0x18, 0x1C),
        dt=(0x3F0, 0xC), dg=0x10,
        hlmt_blocks=[(0xA8, 0x14, (0x10,)), (0xB4, 0x14, (0x10,)), (0xC0, 0x10C, (0xE4, 0xE6)),
                     (0xE0, 0xC0, (0xBE,))], hlmt_top=(0x104,)),
    'Halo 4': dict(
        ref_id=0xC, model=0x64,
        prep=(0x5F8, 0x80, 0x48), scnr_prep=(0x7D8, 0x80, 0x48),
        mats=(0x8A0, 0x1A8), gen=0xC, spec=0x10, parent=0x8, wet=(0x18, 0x1C),
        dt=(0x580, 0xC), dg=0x10,
        hlmt_blocks=[(0xE8, 0x14, (0x10,)), (0xF4, 0xB8, (0x90, 0x92)), (0x114, 0xB4, (0xB2,))],
        hlmt_top=(0x138,)),
}
#: the plugin field each offset above stands for, re-checked when a registry is passed
_PLUGIN_CHECK = {
    'Halo 2': [('matg', 'General Armor', 'Materials', 0x10), ('matg', 'Specific Armor', 'Materials', 0x14),
               ('hlmt', 'Global Material Index', 'Materials', 0x10),
               ('hlmt', 'Shield Global Material Index', 'New Damage Info', 0xCC)],
    'Halo 3': [('matg', 'General Armor', 'Materials', 0xC), ('hlmt', 'Global Material Index', 'Materials', 0x10),
               ('hlmt', 'Shield Global Material Index', 'New Damage Info', 0x80)],
    'Halo 3: ODST': [('matg', 'General Armor', 'Materials', 0xC),
                     ('hlmt', 'Global Material Index', 'Materials', 0x10),
                     ('hlmt', 'Shield Global Material Index', 'New Damage Info', 0x80)],
    'Halo Reach': [('matg', 'General Armor', 'Runtime Materials', 0xC),
                   ('hlmt', 'Global Material Index', 'Model Materials', 0x10),
                   ('hlmt', 'Shield Global Material Index', 'Damage Sections', 0xBE)],
    'Halo 4': [('matg', 'General Armor', 'Runtime Materials', 0xC),
               ('hlmt', 'Global Material Index', 'Model Materials', 0x10),
               ('hlmt', 'Shield Global Material Index', 'Damage Sections', 0xB2)],
}
SKIP_UNITS = ('hologram', 'monitor')     # H4 hologram decoy; the Forge editor monitor
#: in-place growth: the evicted span must stay below this (it goes into one zero run)
EVICT_MAX = 0xA000


def _row(field, ok, old=None, new=None, reason=None):
    r = {'effect': EFFECT, 'field': field, 'ok': ok}
    if old is not None:
        r['old'] = old
    if new is not None:
        r['new'] = new
    if reason:
        r['reason'] = reason
    return r


# --- names (reporting only) -----------------------------------------------------------
def sid_name(m, game, v):
    """Best-effort stringid -> text for reports. H3/ODST: dynamic ids sit at
    idx + STATIC_TOTAL - (count - strip); Reach/H4: +4747 / +6841 (damage_categories
    reports). Falls back to hex."""
    if not v:
        return '-'
    s = None
    try:
        if game in ('Halo 3', 'Halo 3: ODST'):
            m._locate_stringids()
            tail = m.str_tbl_count - m._sid_strip
            idx = v & 0xFFFF
            if idx >= tail:
                s = m._string_at(idx + (2671 if game == 'Halo 3: ODST' else 2187) - tail)
            else:
                s = m._string_at(m._sid_strip + idx - 1)
        elif game in ('Halo Reach', 'Halo 4'):
            m._locate_stringids()
            if (v >> 17) == 0 and (v & 0x1FFFF) >= 1000:
                s = m._string_at((v & 0x1FFFF) + (4747 if game == 'Halo Reach' else 6841))
            else:
                s = m.resolve_stringid(v)
        else:
            s = m.resolve_stringid(v)
    except Exception:
        s = None
    return s or '0x%x' % v


# --- map access ------------------------------------------------------------------------
class _Ctx:
    def __init__(self, m, game):
        self.m, self.game, self.L = m, game, LAYOUT[game]
        self.h2 = game == 'Halo 2'
        g = m.globals_tag()
        self.matg = g['base'] if g else None
        self.writes = []

    # raw
    def i16(self, o):
        return struct.unpack_from('<h', self.m.data, o)[0]

    def blk(self, off):
        n = self.m.i32(off)
        return (n, hp._block_base(self.m, off)) if n > 0 else (0, None)

    def ref(self, o):
        return self.m.u32(o + self.L['ref_id'])

    def tag_of(self, datum):
        if datum in (0, 0xFFFFFFFF):
            return None
        t = self.m.tag(datum & 0xFFFF)
        if not t or t.get('base') is None:
            return None
        return t

    def write(self, off, b):
        b = bytes(b)
        self.m.data[off:off + len(b)] = b
        self.writes.append((off, off + len(b)))

    # materials
    def mats(self):
        off, es = self.L['mats']
        n, b = self.blk(self.matg + off)
        return n, b, es

    def mat_fields(self, e):
        L = self.L
        return dict(name=self.m.u32(e), gen=self.m.u32(e + L['gen']), spec=self.m.u32(e + L['spec']),
                    parent=self.i16(e + L['parent']),
                    wet=self.i16(e + L['wet'][0]) if L['wet'] else -1,
                    dry=self.i16(e + L['wet'][1]) if L['wet'] else -1)

    def armour(self, idx):
        """(specific, general) of material `idx`: its own values, else the first set value
        up the parent-index chain -- each independently."""
        n, b, es = self.mats()
        spec = gen = 0
        seen = set()
        i = idx
        while 0 <= i < n and i not in seen:
            seen.add(i)
            f = self.mat_fields(b + i * es)
            spec = spec or f['spec']
            gen = gen or f['gen']
            if spec and gen:
                break
            i = f['parent']
        return spec, gen

    # damage table
    def tables(self):
        """[(table index, [(group elem off, group name sid, rows count, rows base,
        [(name, value)])])]"""
        dto, tes = self.L['dt']
        dges = self.L['dg']
        out = []
        tn, tb = self.blk(self.matg + dto)
        for t in range(tn):
            gn, gb = self.blk(tb + t * tes)
            groups = []
            for g in range(gn):
                ge = gb + g * dges
                rn, rb = self.blk(ge + 4)
                rows = [(self.m.u32(rb + r * 8), struct.unpack_from('<f', self.m.data, rb + r * 8 + 4)[0])
                        for r in range(rn)]
                groups.append((ge, self.m.u32(ge), rn, rb, rows))
            out.append((t, groups))
        return out


def _sorted_rows(arr):
    """An Armor Modifiers array (8-byte (name stringid, multiplier) rows) in ascending
    name order. The engine finds rows by BINARY SEARCH (halo3.dll 0x18013eeb4, compare
    *key - *elem), so a row appended out of order is never found -- the first H3 test
    put the Chief's shield key before smaller ids and his shield read x1 everywhere."""
    rows = [arr[i:i + 8] for i in range(0, len(arr), 8)]
    return b''.join(sorted(rows, key=lambda r: struct.unpack_from('<i', r)[0]))


def lookup(rows, spec, gen, rule='multiply'):
    """The multiplier a material with (specific, general) armour gets from one damage
    group's rows: (value, how) or (None, None) when no row applies (engine default 1).
    rule 'specific': the specific row if the group has one, else the general row.
    rule 'multiply': general row x specific row, each 1 when absent."""
    d = {}
    for nm, v in rows:
        d.setdefault(nm, v)
    hs, hg = bool(spec) and spec in d, bool(gen) and gen in d
    if rule == 'multiply' and hs and hg:
        return d[spec] * d[gen], 'both'
    if hs:
        return d[spec], 'specific'
    if hg:
        return d[gen], 'general'
    return None, None


def player_bipeds(c):
    """[(bipd name, bipd tag dict, source)] -- matg Player Representation + scenario
    Override Player Representations, bipd only, holograms / Forge monitor skipped."""
    m, L = c.m, c.L
    out, seen, skipped = [], set(), []
    srcs = [('matg', c.matg, L['prep'])]
    if L['scnr_prep']:
        s = m.scenario_tag()
        if s and s.get('base') is not None:
            srcs.append(('scnr override', s['base'], L['scnr_prep']))
    for src, base, (off, es, uo) in srcs:
        if base is None:
            continue
        n, b = c.blk(base + off)
        for i in range(n):
            t = c.tag_of(c.ref(b + i * es + uo))
            if t is None:
                continue
            nm = t.get('name') or 'tag#%d' % t['index']
            if t.get('class') != 'bipd':
                skipped.append('%s (%s, not a biped)' % (nm, t.get('class')))
                continue
            if any(k in nm.lower() for k in SKIP_UNITS):
                if nm not in skipped:
                    skipped.append(nm)
                continue
            if t['index'] in seen:
                continue
            seen.add(t['index'])
            out.append((nm, t, '%s[%d]' % (src, i)))
    return out, skipped


_OBJECT_CLASSES = {'bipd', 'vehi', 'weap', 'eqip', 'garb', 'proj', 'scen', 'bloc', 'crea', 'mach',
                   'ctrl', 'ssce', 'term', 'gint', 'efsc', 'argd', 'dctr', 'mach'}


def model_users(c):
    """hlmt tag index -> [(class, tag name)] of every object whose Model is that hlmt."""
    users = {}
    for t in c.m.tags:
        if t.get('class') in _OBJECT_CLASSES and t.get('base') is not None:
            try:
                d = c.ref(t['base'] + c.L['model'])
            except struct.error:
                continue
            ht = c.tag_of(d)
            if ht is not None and ht.get('class') == 'hlmt':
                users.setdefault(ht['index'], []).append((t['class'], t.get('name') or '', t['index']))
    return users


def hlmt_index_fields(c, hbase):
    """[(file offset, value, array)] of every matg-material-index field of one hlmt;
    `array` = (block field offset, array offset, count, element size), None for a field of
    the hlmt's own struct."""
    out = []
    for off, es, fields in c.L['hlmt_blocks']:
        n, b = c.blk(hbase + off)
        for i in range(n):
            for f in fields:
                o = b + i * es + f
                out.append((o, c.i16(o), (hbase + off, b, n, es)))
    for f in c.L['hlmt_top']:
        out.append((hbase + f, c.i16(hbase + f), None))
    return out


def hlmt_arrays(c, skip):
    """[(start, end)] of every material-carrying array of every hlmt not in `skip`."""
    out = []
    for t in c.m.tags:
        if t.get('class') != 'hlmt' or t.get('base') is None or t['index'] in skip:
            continue
        for off, es, _f in c.L['hlmt_blocks']:
            n, b = c.blk(t['base'] + off)
            if n and b is not None:
                out.append((b, b + n * es))
    return out


def _h2_append(c, blobs):
    """Halo 2: append byte blobs to the end of the image (16-aligned, the region padded to
    SEGMENT_ALIGN, header sizes grown) -- Halo2Map.grow_blocks' layout, for copies that
    keep their count. Returns their file offsets."""
    m = c.m
    blob, offs, base = bytearray(), [], len(m.data)
    for b in blobs:
        blob += bytearray((-len(blob)) & 15)
        offs.append(base + len(blob))
        blob += b
    delta = (len(blob) + m.SEGMENT_ALIGN - 1) & ~(m.SEGMENT_ALIGN - 1)
    m.data += blob + bytearray(delta - len(blob))
    m.file_size += delta
    m.meta_size += delta
    m.tag_data_size += delta
    struct.pack_into('<I', m.data, 0x8, m.file_size)
    struct.pack_into('<I', m.data, 0x14, m.meta_size)
    struct.pack_into('<I', m.data, 0x2D8, m.tag_data_size)
    c.writes += [(base, len(m.data)), (0x8, 0xC), (0x14, 0x18), (0x2D8, 0x2DC)]
    return offs


# --- pointer scan / in-place growth ------------------------------------------------------
def _scan_refs(m, targets):
    """{target value: [file offsets of u32 words equal to it]} over every partition."""
    found = {}
    if not targets:
        return found
    try:
        import numpy as np
        want = np.array(sorted(targets), dtype=np.uint32)
        for la, sz, fb in m.partitions:
            if not sz or fb is None or fb + sz > len(m.data):
                continue
            arr = np.frombuffer(m.data, dtype='<u4', count=sz // 4, offset=fb)
            for k in np.nonzero(np.isin(arr, want))[0]:
                found.setdefault(int(arr[k]), []).append(fb + int(k) * 4)
    except ImportError:                                           # pure-python fallback
        import array
        tset = set(targets)
        for la, sz, fb in m.partitions:
            if not sz or fb is None or fb + sz > len(m.data):
                continue
            a = array.array('I')
            a.frombytes(bytes(m.data[fb:fb + (sz & ~3)]))
            for k, v in enumerate(a):
                if v in tset:
                    found.setdefault(v, []).append(fb + k * 4)
    return found


def _partition_of_off(m, off):
    for i, (la, sz, fb) in enumerate(m.partitions):
        if fb is not None and sz and fb <= off < fb + sz:
            return i, fb, fb + sz
    return None, None, None


def _tag_table_range(m):
    """File range of the tag index table (8-byte entries, memaddr at +4), if known."""
    try:
        to = m.va2off(m.u64(m.index_header_off + 0x18))
        return to, to + m.n_tags * 8
    except Exception:
        return None


_FILL = (0, 0xCDCDCDCD)        # unused pointer-struct words: 0 (H3/ODST/Reach), 0xCDCDCDCD (H4)


def _plausible(m, r, ttab):
    """A u32 equal to an encoded pointer is a real reference only where a pointer can sit.
    The scan does find look-alikes (shader bytecode, render-method data, HUD data: 12 on
    010_jungle, 13 on m10_crash), so the word must sit in
      * a tag-table entry (memaddr at +4 of an 8-byte entry), or
      * a tagblock  [count 0..0x100000][ptr][0 / 0xCDCDCDCD], or
      * a tag-data reference [size][fill][fill][ptr][fill] (fill 0 or 0xCDCDCDCD; H4's
        are what the plain count test missed)."""
    if ttab and ttab[0] <= r < ttab[1] and (r - ttab[0]) % 8 == 4:
        return True
    u = lambda o: struct.unpack_from('<I', m.data, o)[0]              # noqa: E731
    if u(r + 4) not in _FILL:
        return False
    if u(r - 4) <= 0x100000:
        return True
    return u(r - 4) in _FILL and u(r - 8) in _FILL and 0 < u(r - 12) <= 0x4000000


def _pointers_into(m, lo, hi, ttab):
    """{target offset: [referencing offsets]} for every 4-aligned address in [lo, hi),
    plausible referencers only; plus the count of look-alikes dropped."""
    enc = {}
    for x in range(lo, hi, 4):
        d = m.off2data(x)
        if d is not None and m.data2off(d) == x:
            enc[d] = x
    found = _scan_refs(m, enc.keys())
    out, dropped = {}, 0
    for v, offs in found.items():
        good = [r for r in offs if _plausible(m, r, ttab)]
        dropped += len(offs) - len(good)
        if good:
            out[enc[v]] = good
    return out, dropped


def plan_room(m, b, n, es, k):
    """Plan k more elements for the array [b, b+n*es) without relocating it whole.

    'before': the whole blocks in [A, b) move into slack and the array shifts down by
              k*es (it keeps its end; the clones fill the last k slots).
    'after' : the whole blocks in [end, B) move into slack; the clones follow the array.
    A span may not contain a tag header (bases are tag-table entries, and other code
    holds them) and must end/start on an address something points at. Returns a plan
    dict or a reason string."""
    import bisect
    need = k * es
    end = b + n * es
    pi, pfb, pend = _partition_of_off(m, b)
    if pi is None or _partition_of_off(m, end - 1)[0] != pi:
        return 'the materials array is not inside one partition'
    ttab = _tag_table_range(m)
    bases = sorted(t['base'] for t in m.tags if t.get('base') is not None)
    reasons = []
    cands = []
    # before
    window = 0x2000
    while window <= EVICT_MAX * 2:
        lo = max(pfb, b - window)
        pts, dropped = _pointers_into(m, lo, b, ttab)
        starts = sorted(x for x in pts if x <= b - need)
        if starts:
            A = starts[-1]
            kk = bisect.bisect_left(bases, A)
            if kk < len(bases) and bases[kk] < b:
                reasons.append('before: a tag header sits %#x bytes before the array' % (b - bases[kk]))
            elif b - A > EVICT_MAX:
                reasons.append('before: %#x bytes to move' % (b - A))
            else:
                cands.append(dict(kind='before', span=(A, b), refs={x: r for x, r in pts.items() if x >= A},
                                  dropped=dropped, clone_at=end - need, shift=-need))
            break
        if lo == pfb:
            reasons.append('before: no block boundary')
            break
        window *= 2
    # after
    window = 0x2000
    while window <= EVICT_MAX * 2:
        hi = min(pend, end + window)
        pts, dropped = _pointers_into(m, end, hi, ttab)
        kk = bisect.bisect_left(bases, end)
        tag_starts = [x for x in bases[kk:] if x < hi]
        bounds = sorted([x for x in pts if x >= end + need] + [x for x in tag_starts if x >= end + need])
        early = [x for x in tag_starts if x < end + need]
        if early:
            reasons.append('after: a tag header sits %#x bytes after the array' % (early[0] - end))
            break
        if bounds:
            B = bounds[0]
            if B - end > EVICT_MAX:
                reasons.append('after: %#x bytes to move' % (B - end))
            else:
                cands.append(dict(kind='after', span=(end, B), refs={x: r for x, r in pts.items() if x < B},
                                  dropped=dropped, clone_at=end, shift=0))
            break
        if hi == pend:
            reasons.append('after: no block boundary')
            break
        window *= 2
    if not cands:
        return '; '.join(reasons) or 'no room'
    best = min(cands, key=lambda p: p['span'][1] - p['span'][0])
    best['alternatives'] = [(p['kind'], p['span'][1] - p['span'][0]) for p in cands]
    best['reasons'] = reasons
    if best['shift']:
        # the array itself moves: every pointer to it (normally only matg's block field)
        arr, dropped = _pointers_into(m, b, end, ttab)
        # only the array start (or an element start) can be a real target; anything else
        # is a look-alike (one in a cusc on m10_crash pointed into a tagRef)
        keep = {x: r for x, r in arr.items() if (x - b) % es == 0}
        best['array_refs'] = keep
        best['dropped'] += dropped + sum(len(r) for x, r in arr.items() if x not in keep)
    best['array'] = (b, end)
    return best


def commit_room(c, plan, new_base):
    """Carry out plan_room's plan: the span goes to new_base, the array shifts if the plan
    says so, every pointer into either is rewritten. Returns (relocate(off) function,
    pointers rewritten)."""
    m = c.m
    A, Bnd = plan['span']
    b, end = plan['array']
    shift = plan['shift']
    moves = [(A, Bnd, new_base)]
    if shift:
        moves.append((b, end, b + shift))

    def relocate(o):
        for lo, hi, dst in moves:
            if lo <= o < hi:
                return dst + (o - lo)
        return o

    refs = {}
    for src in (plan['refs'], plan.get('array_refs', {})):
        for x, r in src.items():
            refs.setdefault(x, []).extend(r)
    snaps = [(lo, hi, dst, bytes(m.data[lo:hi])) for lo, hi, dst in moves]
    for lo, hi, dst, _s in snaps:
        c.write(lo, bytes(hi - lo))
    for lo, hi, dst, s in snaps:
        c.write(dst, s)
    nfix = 0
    for x, rs in refs.items():
        nx = relocate(x)
        newp = m.off2data(nx)
        if newp is None or m.data2off(newp) != nx:
            raise RuntimeError('moved address %#x does not map back' % nx)
        for r in rs:
            c.write(relocate(r), struct.pack('<I', newp))
            nfix += 1
    c.moved = dict(kind=plan['kind'], moves=moves, referencers=sorted(r for rs in refs.values() for r in rs))
    return relocate, nfix


def _cow_move(off, arr, cow, dsts):
    """A field offset inside a copied-on-write array -> the same field in the copy."""
    if arr in cow:
        d = dsts[cow.index(arr)]
        return d + (off - arr[1])
    return off


# --- apply -------------------------------------------------------------------------------
def _check_plugins(game, registry):
    if registry is None:
        return None
    for grp, field, block, off in _PLUGIN_CHECK.get(game, []):
        try:
            p = registry.get(grp)
            if p is None:
                continue
            f = p.find(field, block=block)
        except Exception:
            f = None
        if f is not None and f.get('offset') != off:
            return '%s %s/%s is %#x in the plugin, %#x here' % (grp, block, field, f.get('offset'), off)
    return None


def apply(m, game, registry=None, rule='multiply'):
    """See the module docstring. `rule` decides the copied value where a group has BOTH a
    specific and a general row for a player material (H3 Tilt table only): 'specific'
    (default, the specific row) or 'multiply' (general x specific)."""
    game = str(game).strip()
    if game not in LAYOUT:
        return []
    bad = _check_plugins(game, registry)
    if bad:
        return [_row('layout', False, reason='plugin offsets changed: ' + bad)]
    c = _Ctx(m, game)
    if c.matg is None:
        return [_row('matg', False, reason='no globals tag')]
    out = []
    nm = lambda v: sid_name(m, game, v)                               # noqa: E731

    # 1-2. player bipeds -> hlmts -> material index fields
    bipeds, skipped = player_bipeds(c)
    if skipped:
        out.append(_row('player units skipped', True, new=', '.join(skipped)))
    if not bipeds:
        return out + [_row('player bipeds', False, reason='no player biped found')]
    users = model_users(c)
    player_tags = {t['index'] for _n, t, _s in bipeds}
    hlmts = {}
    for bname, t, src in bipeds:
        ht = c.tag_of(c.ref(t['base'] + c.L['model']))
        if ht is None or ht.get('class') != 'hlmt':
            out.append(_row(bname, False, reason='biped has no model'))
            continue
        hlmts.setdefault(ht['index'], [ht, []])[1].append(bname)
    n, mb, es = c.mats()
    names = [m.u32(mb + i * es) for i in range(n)]
    first = {}
    for i, x in enumerate(names):
        first.setdefault(x, i)

    def original_of(i):
        """A clone (later element sharing an earlier element's Name) -> that original."""
        if 0 <= i < n and first.get(names[i], i) != i:
            return first[names[i]]
        return i

    fields = []                   # (hlmt name, offset, value, array)
    originals = []
    for hidx, (ht, owners) in hlmts.items():
        others = [(cl, u) for cl, u, ti in users.get(hidx, []) if ti not in player_tags]
        if others:
            out.append(_row(ht.get('name'), False, reason='model shared with non-player objects (%s); '
                            'not repointed' % ', '.join('%s %s' % o for o in others[:4])))
            continue
        for off, v, arr in hlmt_index_fields(c, ht['base']):
            if 0 <= v < n:
                fields.append((ht.get('name'), off, v, arr))
                o = original_of(v)
                if o not in originals:
                    originals.append(o)
    if not originals:
        return out + [_row('player materials', False, reason='the player models carry no material index')]

    # 3. clone plan
    def clone_of(o):
        for j in range(o + 1, n):
            if names[j] == names[o]:
                return j
        return None

    existing = set()
    for o in range(n):
        if first.get(names[o]) != o:
            existing.add(o)
    tables = c.tables()
    # every armour name in use: worn by a material (our clones aside) or naming a row
    used = set()
    for i in range(n):
        if i not in existing:
            f = c.mat_fields(mb + i * es)
            used.update((f['gen'], f['spec']))
    for t, groups in tables:
        for ge, gname, rn, rb, rows in groups:
            used.update(r[0] for r in rows)
    used.discard(0)
    clone_keys = {c.mat_fields(mb + i * es)['gen'] for i in existing}

    def pick_key(cands):
        """The material's own Name, else (Reach) its wet partner's Name -- an existing
        stringid that no material wears and no row is named after."""
        for k in cands:
            if k and (k not in used or k in clone_keys):
                return k
        return None

    clones = []                   # dicts: orig, key, idx, new, wet (entry) / dry (entry)
    nxt = n
    by_orig = {}
    for o in originals:
        f = c.mat_fields(mb + o * es)
        j = clone_of(o)
        w = f['wet'] if c.L['wet'] and 0 <= f['wet'] < n else None
        if j is not None:
            key = c.mat_fields(mb + j * es)['gen']
        else:
            key = pick_key([f['name']] + ([names[w]] if w is not None else []))
        if key is None:
            out.append(_row('material [%d] %s' % (o, nm(f['name'])), False,
                            reason='kept shared: its Name is already an armour name and no other free '
                                   'key exists (%s)' % nm(f['name'])))
            continue
        e = dict(orig=o, key=key, idx=j if j is not None else nxt, new=j is None, wet=None)
        if j is None:
            nxt += 1
        by_orig[o] = e
        clones.append(e)
        if w is not None:
            jw = clone_of(w)
            if jw is not None:
                wkey = c.mat_fields(mb + jw * es)['gen']
            elif c.armour(w) == c.armour(o):
                wkey = key
            else:
                wkey = pick_key([names[w]])
            if wkey is None:
                out.append(_row('wet material [%d] %s' % (w, nm(names[w])), False,
                                reason='no free key; the wet variant stays shared'))
                continue
            we = dict(orig=w, key=wkey, idx=jw if jw is not None else nxt, new=jw is None, wet=None, dry=e)
            if jw is None:
                nxt += 1
            e['wet'] = we
            clones.append(we)
    if not clones:
        return out + [_row('player materials', False, reason='no material could be given a key')]

    # 4. rows plan
    row_jobs = []                 # (group elem off, rows count, rows base, [(key, value)], label)
    added = []
    multiply_groups = []
    mism = []
    for t, groups in tables:
        for ge, gname, rn, rb, rows in groups:
            have = {r[0]: r[1] for r in rows}
            new_rows = []
            for e in clones:
                spec, gen = c.armour(e['orig'])
                val, via = lookup(rows, spec, gen, rule)
                if spec in have and gen in have and spec and gen:
                    multiply_groups.append('[%d] %s (%s: %s %g x %s %g -> copied %g)' % (
                        t, nm(gname), nm(names[e['orig']]), nm(spec), have[spec], nm(gen), have[gen], val))
                if e['key'] in have:
                    if val is not None and abs(have[e['key']] - val) > 1e-6:
                        mism.append('[%d] %s %s has %g, player value %g' % (t, nm(gname), nm(e['key']),
                                                                           have[e['key']], val))
                    continue
                if val is None or any(k == e['key'] for k, _v in new_rows):
                    continue
                new_rows.append((e['key'], val))
            if new_rows:
                row_jobs.append((ge, rn, bytes(m.data[rb:rb + rn * 8]) if rn else b'', new_rows,
                                 '[%d] %s' % (t, nm(gname))))
                for k, v in new_rows:
                    added.append('[%d] %s: %s %g' % (t, nm(gname), nm(k), v))

    repoint = [(h, off, v, by_orig[original_of(v)]['idx'], arr) for h, off, v, arr in fields
               if original_of(v) in by_orig and v != by_orig[original_of(v)]['idx']]
    new_clones = [e for e in clones if e['new']]
    # COPY-ON-WRITE: a player hlmt's array can be the very array a non-player hlmt points
    # at (H3 dervish / dervish_ai share their material arrays) -- repointing it in place
    # would hand the AI the player's rows. Such an array gets a private copy first.
    others = hlmt_arrays(c, set(hlmts))
    cow = sorted({arr for _h, _o, _v, _ci, arr in repoint
                  if arr is not None and any(a < arr[1] + arr[2] * arr[3] and arr[1] < b for a, b in others)})

    if not new_clones and not row_jobs and not repoint and not cow:
        out.append(_row('player armour', True, old='already applied',
                        new='%d clone(s), key rows present; nothing to do' % len(clones)))
        if mism:
            out.append(_row('key rows', False, reason='; '.join(mism)))
        return out

    # build clone element bytes
    def clone_bytes(e, src=None):
        src = mb + e['orig'] * es if src is None else src
        b = bytearray(m.data[src:src + es])
        struct.pack_into('<I', b, c.L['gen'], e['key'])
        struct.pack_into('<I', b, c.L['spec'], 0)
        if c.L['wet']:
            wo, do = c.L['wet']
            if e.get('wet') is not None:
                struct.pack_into('<h', b, wo, e['wet']['idx'])
            if e.get('dry') is not None:
                struct.pack_into('<h', b, do, e['dry']['idx'])
        return bytes(b)

    new_clones.sort(key=lambda e: e['idx'])
    if new_clones and [e['idx'] for e in new_clones] != list(range(n, n + len(new_clones))):
        return out + [_row('clones', False, reason='partial earlier clone set; restore the map first')]
    cbytes = [clone_bytes(e) for e in new_clones] if c.h2 else None

    # 5. growth + writes
    try:
        if c.h2:
            if cow:
                dsts = _h2_append(c, [bytes(m.data[p:p + k * e]) for _fo, p, k, e in cow])
                for (fo, p, k, e), d in zip(cow, dsts):
                    c.write(fo + 4, struct.pack('<I', (d - m.meta_offset + m.mask) & 0xFFFFFFFF))
                repoint = [(h, _cow_move(off, arr, cow, dsts), v, ci, arr) for h, off, v, ci, arr in repoint]
            jobs = []
            if cbytes:
                jobs.append((c.matg, c.L['mats'][0], es, cbytes))
            for ge, rn, _old, new_rows, _lbl in row_jobs:
                jobs.append((ge, 4, 8, [struct.pack('<If', k, v) for k, v in new_rows]))
            if jobs:
                old_len = len(m.data)
                m.grow_blocks(jobs)
                c.writes += [(old_len, len(m.data)), (0x8, 0xC), (0x14, 0x18), (0x2D8, 0x2DC)]
                c.writes += [(tb + bo, tb + bo + 8) for tb, bo, _es, _el in jobs]
                # grow_blocks APPENDS; the engine binary-searches each Armor Modifiers
                # array (see SORTED ROWS in the docstring), so put every grown one back
                # in ascending stringid order
                for ge, _rn, _old, _new, _lbl in row_jobs:
                    rn2, rb2 = c.blk(ge + 4)
                    c.write(rb2, _sorted_rows(bytes(m.data[rb2:rb2 + rn2 * 8])))
        else:
            room = None
            moved = lambda o: o                                   # noqa: E731
            if new_clones:
                room = plan_room(m, mb, n, es, len(new_clones))
                if isinstance(room, str):
                    return out + [_row('materials block', False,
                                       reason='cannot grow the materials array in place: ' + room)]
            sizes = []
            if room:
                A, Bnd = room['span']
                sizes.append(Bnd - A + 16)
                # keep _h3_reserve out of everything this growth touches
                if getattr(m, '_h3_reserved', None) is None:
                    m._h3_reserved = []
                m._h3_reserved.append((min(A, mb), max(Bnd, mb + n * es)))
            sizes += [(rn + len(nr)) * 8 for _ge, rn, _o, nr, _l in row_jobs]
            sizes += [k * e for _fo, _p, k, e in cow]
            got = hp._h3_reserve(m, sizes) if sizes else []
            if got is None:                                       # one run each
                got = []
                for sz in sizes:
                    g1 = hp._h3_reserve(m, [sz])
                    if g1 is None:
                        return out + [_row('slack', False, reason='no zero run for %d bytes' % sz)]
                    got += g1
            gi = 0
            if room:
                res = got[gi]
                gi += 1
                new_base = res + ((A - res) & 15)                 # keep each block's mod-16 alignment
                moved, nfix = commit_room(c, room, new_base)
                cbytes = [clone_bytes(e, moved(mb + e['orig'] * es)) for e in new_clones]
                c.write(room['clone_at'], b''.join(cbytes))
                c.write(moved(c.matg + c.L['mats'][0]), struct.pack('<i', n + len(cbytes)))
                out.append(_row('materials block', True, old='%d elements' % n,
                                new='%d elements; made room %s the array: %#x bytes of blocks moved to %#x, '
                                    '%d pointer(s) rewritten%s' % (
                                        n + len(cbytes), room['kind'], Bnd - A, new_base, nfix,
                                        (', %d look-alike u32(s) ignored' % room['dropped'])
                                        if room['dropped'] else '')))
            for ge, rn, old, new_rows, lbl in row_jobs:
                dst = got[gi]
                gi += 1
                arr = _sorted_rows(old + b''.join(struct.pack('<If', k, v) for k, v in new_rows))
                c.write(dst, arr)
                ptr = m.off2data(dst)
                if ptr is None or m.data2off(ptr) != dst:
                    raise RuntimeError('reserved region %#x has no pointer' % dst)
                c.write(moved(ge) + 4, struct.pack('<iI', rn + len(new_rows), ptr))
            dsts = []
            for fo, p, k, e in cow:
                dst = got[gi]
                gi += 1
                c.write(dst, bytes(m.data[moved(p):moved(p) + k * e]))
                c.write(moved(fo) + 4, struct.pack('<I', m.off2data(dst)))
                dsts.append(dst)
            repoint = [(h, _cow_move(off, arr, cow, dsts) if arr in cow else moved(off), v, ci, arr)
                       for h, off, v, ci, arr in repoint]
    except Exception as ex:                                       # pragma: no cover
        return out + [_row('player armour', False, reason='write failed: %s' % ex)]

    for h, off, v, ci, _a in repoint:
        c.write(off, struct.pack('<h', ci))
    m._player_armour_writes = getattr(m, '_player_armour_writes', []) + c.writes
    if getattr(c, 'moved', None):
        m._player_armour_moved = c.moved            # for the self-test / diagnostics

    # (key stringid, original material Name stringid) per clone -- zero_rows() and the
    # coming Effective cards find the player's rows by these
    m._player_armour_keys = [(e['key'], names[e['orig']]) for e in clones]
    for e in clones:
        kind = 'wet clone' if e.get('dry') is not None else 'clone'
        out.append(_row('%s [%d] %s' % (kind, e['orig'], nm(names[e['orig']])), True,
                        old='armour %s / %s' % tuple(nm(x) for x in c.armour(e['orig'])),
                        new='[%d] key %s%s' % (e['idx'], nm(e['key']), '' if e['new'] else ' (existing)')))
    summary = {}
    for h, off, v, ci, _a in repoint:
        summary.setdefault((h or '').rsplit(chr(92), 1)[-1], {}).setdefault((v, ci), 0)
        summary[(h or '').rsplit(chr(92), 1)[-1]][(v, ci)] += 1
    for h, d in summary.items():
        out.append(_row('repoint hlmt %s' % h, True, old=', '.join(str(v) for v, ci in d),
                        new=', '.join('%d (x%d)' % (ci, k) for (v, ci), k in d.items())))
    for fo, p, k, e in cow:
        owner = next((h for h, _o, _v, _c, a in repoint if a == (fo, p, k, e)), '?')
        out.append(_row('private copy', True, old='array %#x shared with a non-player model' % p,
                        new='%s gets its own %d-element copy' % ((owner or '?').rsplit(chr(92), 1)[-1], k)))
    out.append(_row('rows', True, new='%d row(s) added' % len(added)))
    for a in added:
        out.append(_row('row', True, new=a))
    if multiply_groups:
        out.append(_row('both-rows groups', True,
                        new='rule %s; specific AND general row present: %s' % (
                            rule, '; '.join(sorted(set(multiply_groups))))))
    if mism:
        out.append(_row('key rows', False, reason='; '.join(mism)))
    return out


def zero_rows(m, game, group_words=('plasma',), material_words=('shield',)):
    """DEBUG TEST (Options -> Patching -> Bugfixes, debug mode): set the player's own rows
    to 0 in every damage group whose name contains one of `group_words`, for the clones
    of materials whose name contains one of `material_words` -- by default: plasma can no
    longer hurt the player's shield, while Elites (same rows before the split) still take
    it. Proves the engine reads the clone. Run right after apply()."""
    game = str(game).strip()
    keys = {k for k, orig in getattr(m, '_player_armour_keys', ())
            if any(w in (sid_name(m, game, orig) or '') for w in material_words)}
    if not keys:
        return [_row('TEST player rows -> 0', False, reason='no player armour keys (apply first)')]
    c = _Ctx(m, game)
    n, groups_hit = 0, set()
    for t, groups in c.tables():
        for _ge, gsid, rn, rb, _rows in groups:
            gname = sid_name(m, game, gsid) or ''
            if not any(w in gname for w in group_words):
                continue
            for r in range(rn):
                if m.u32(rb + r * 8) in keys:
                    struct.pack_into('<f', m.data, rb + r * 8 + 4, 0.0)
                    n += 1
                    groups_hit.add('[%d] %s' % (t, gname))
    if not n:
        return [_row('TEST player rows -> 0', False,
                     reason='no player %s row in a %s group' % ('/'.join(material_words),
                                                                 '/'.join(group_words)))]
    return [_row('TEST player %s vs %s -> 0' % ('/'.join(material_words), '/'.join(group_words)),
                 True, new='%d row(s) in %s' % (n, ', '.join(sorted(groups_hit))))]

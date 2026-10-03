r"""Halo 3 enemy ground speed: read and scale move-animation root motion in a BUILT map (2026-10-03).

Halo 3 keeps an animation's root motion OUTSIDE its codec data, as plain floats, exactly
like Halo 2 -- but in a built map the frames sit in compressed resource pages:

  jmad Animations +0x50 elem 0x88: Name stringId +0x0, Frame Count +0x10, Frame Info
       Type +0x13, Resource Group +0x28, Resource Group Member +0x2A
  jmad Tag Resource Groups +0xF8 elem 0xC: zone resource datum +0x4
  zone Resources +0x64 elem 0x40: control offset +0x14, control size +0x18, segment
       +0x22, Control Fixups +0x28 (elem 8: location, encoded value)
  control buffer = zone +0x148 dataref (Native Resource Control Data); a member is 0x30:
       frame count +0x8, movement type +0xB, data sizes +0xC (u8 static flags, u8
       animated flags, i16 movement, i16 pill, i16 default, i32 uncompressed, i32
       compressed), blob size +0x1C, data pointer = the fixup at member+0x28, value
       0x4000_0000 | offset in the page
  segment -> File Location (page, elem 0x58): codec +0x3 (0 = raw deflate), shared file
       +0x4 (-1 = this map), Block Offset +0x8 (a FILE offset), compressed +0xC,
       uncompressed +0x10, CRC +0x14 = crc32(unc) ^ 0xFFFFFFFF, SHA-1 of the whole
       uncompressed page +0x18, of its first 0x400 bytes +0x2C, of its last 0x400 +0x40
  member blob: [default][compressed][static flags][animated flags][MOVEMENT][pill]

Only pages that live in the map itself (Editing Kit rebuilds) are written; a vanilla map
keeps them in campaign.map / shared.map and is reported, not touched. An edited page is
recompressed (raw deflate, level 9) into its own slot -- the space up to the next page --
and its checksums are recomputed.

Test-only options: --shield-mult (player Maximum Shield Vitality), --paint (enemy_colors
row, load-proof control).

    python h3_move_speed.py --map <map> --show [--jmad "objects\characters\grunt\grunt"]
    python h3_move_speed.py --map <in> --out <out> --mult 2 --jmad ... [--shield-mult 5]
"""
import argparse
import collections
import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import halo_patch as HP  # noqa: E402
import h3_raw_residency as R  # noqa: E402
import h3_zone_pools as Z  # noqa: E402

PER = (0, 8, 12, 16)
FPS = 30.0


class Pages:
    """Resource pages of one open Halo 3 / ODST / Reach map: read, edit, write back."""

    def __init__(self, m, reach=None):
        self.m = m
        # Halo Reach: same zone and pages, but a 0x64-byte member record (below)
        self.reach = (type(m).__name__ == 'ReachMap') if reach is None else reach
        # Halo 4: pages as before, but its own zone layout -- Segments +0x4C (0x18: page
        # offset +0x0, page index +0xC), Tag Resources +0x58 (0x44), control buffer +0x154 --
        # and a 0x68-byte member record
        self.h4 = type(m).__name__ == 'Halo4Map'
        if self.h4:
            zt = next(t for t in m.tags if t.get('class') == 'zone')
            self.zb = zb = zt['base']
            self.tabs = {'owner': 'zone',
                         'page': (HP._block_base(m, zb + 0x34), m.i32(zb + 0x34)),
                         'seg': (HP._block_base(m, zb + 0x4C), m.i32(zb + 0x4C))}
            self.cbase = m.data2off(m.u32(zb + 0x154 + 0xC))
            self.rbase = HP._block_base(m, zb + 0x58)
        else:
            self.zb = Z._zone_tag(m)['base']
            self.tabs = R.resource_tables(m)
            self.cbase = m.data2off(m.u32(self.zb + 0x148 + 0xC))
            self.rbase = HP._block_base(m, self.zb + 0x64)
        pb, pc = self.tabs['page']
        starts = sorted(struct.unpack_from('<I', m.data, pb + i * R.PLAY_PAGE_ELEM + 8)[0]
                        for i in range(pc)
                        if struct.unpack_from('<h', m.data, pb + i * R.PLAY_PAGE_ELEM + 4)[0] < 0)
        self.next = dict(zip(starts, starts[1:]))
        self.cache = {}          # page index -> bytearray (uncompressed)
        self.dirty = set()

    def page_index(self, seg):
        sb, _sc = self.tabs['seg']
        if self.h4:
            return struct.unpack_from('<h', self.m.data, sb + seg * 0x18 + 0xC)[0]
        return struct.unpack_from('<h', self.m.data, sb + seg * R.PLAY_SEG_ELEM)[0]

    def entry(self, pi):
        return self.tabs['page'][0] + pi * R.PLAY_PAGE_ELEM

    def local(self, pi):
        return struct.unpack_from('<h', self.m.data, self.entry(pi) + 4)[0] < 0

    def get(self, pi):
        if pi not in self.cache:
            e = self.entry(pi)
            codec = struct.unpack_from('<b', self.m.data, e + 3)[0]
            off, comp, unc = struct.unpack_from('<III', self.m.data, e + 8)
            raw = bytes(self.m.data[off:off + comp])
            data = raw if codec < 0 else zlib.decompress(raw, -15)
            if len(data) != unc:
                raise ValueError('page %d inflates to %d, not %d' % (pi, len(data), unc))
            self.cache[pi] = bytearray(data)
        return self.cache[pi]

    def members(self, res):
        m = self.m
        if self.h4:
            return self._members_h4(res)
        e = self.rbase + res * 0x40
        coff, csz = m.i32(e + 0x14), m.i32(e + 0x18)
        seg = struct.unpack_from('<h', m.data, e + 0x22)[0]
        # The segment is a Default Location: required page +0x0, offset in that page +0x4.
        # An Editing Kit rebuild starts every resource on its own page (offset 0); a
        # vanilla map packs several resources into one page.
        seg_off = struct.unpack_from('<i', m.data, self.tabs['seg'][0] + seg * R.PLAY_SEG_ELEM + 4)[0]
        fb = HP._block_base(m, e + 0x28)
        fix = {m.u32(fb + k * 8): m.u32(fb + k * 8 + 4) for k in range(max(0, m.i32(e + 0x28)))}
        out = []
        if self.reach:
            # Reach member, 0x64 bytes: frame count +0x8, movement type +0xB, 17 u32 sizes
            # from +0xC in the order [default, compressed, static flags, animated flags,
            # movement, pill, ...], blob size +0x50, page pointer fixup at +0x5C.
            for k in range(csz // 0x64):
                mo = self.cbase + coff + k * 0x64
                ptr = fix.get(k * 0x64 + 0x5C)
                if ptr is None:
                    break
                fc = struct.unpack_from('<h', m.data, mo + 8)[0]
                it = m.data[mo + 0xB]
                sizes = struct.unpack_from('<17I', m.data, mo + 0xC)
                dflt, cmp, sf, af, mv = sizes[:5]
                ok = (ptr >> 28 == 4 and sum(sizes) == m.i32(mo + 0x50)
                      and 0 < it < 4 and mv == PER[it] * fc)
                out.append(dict(fc=fc, it=it, seg=seg, ok=ok,
                                move=seg_off + (ptr & 0x0FFFFFFF) + dflt + cmp + sf + af))
            return out
        for k in range(csz // 0x30):
            mo = self.cbase + coff + k * 0x30
            ptr = fix.get(k * 0x30 + 0x28)
            if ptr is None:
                break
            fc = struct.unpack_from('<h', m.data, mo + 8)[0]
            it = m.data[mo + 0xB]
            sf, af, mv, pill, dflt, unc, cmp = struct.unpack_from('<BBhhhii', m.data, mo + 0xC)
            ok = (ptr >> 28 == 4 and sf + af + mv + pill + dflt + unc + cmp == m.i32(mo + 0x1C)
                  and 0 < it < 4 and mv == PER[it] * fc)
            out.append(dict(fc=fc, it=it, seg=seg, ok=ok,
                            move=seg_off + (ptr & 0x0FFFFFFF) + dflt + cmp + sf + af))
        return out

    def _members_h4(self, res):
        """Halo 4 resource (0x44): control length +0x14, segment +0x1A, fixups +0x20, Fixup
        Information Locations +0x38 (first entry = offset in the control buffer). Member
        0x68: frame count u16 +0x8, movement type +0xB, 18 u32 sizes from +0xC (default,
        compressed, static flags, animated flags, movement, pill, ...), blob size +0x54,
        page pointer fixup at +0x60."""
        m = self.m
        e = self.rbase + res * 0x44
        seg = struct.unpack_from('<h', m.data, e + 0x1A)[0]
        nloc, lb = m.i32(e + 0x38), HP._block_base(m, e + 0x38)
        if seg < 0 or nloc <= 0 or not lb:
            return []
        ctl = self.cbase + m.i32(lb)
        clen = m.i32(e + 0x14)
        seg_off = struct.unpack_from('<i', m.data, self.tabs['seg'][0] + seg * 0x18)[0]
        fb = HP._block_base(m, e + 0x20)
        fix = {m.u32(fb + k * 8): m.u32(fb + k * 8 + 4) for k in range(max(0, m.i32(e + 0x20)))}
        out = []
        for k in range(clen // 0x68):
            mo = ctl + k * 0x68
            ptr = fix.get(k * 0x68 + 0x60)
            if ptr is None:
                break
            fc = struct.unpack_from('<H', m.data, mo + 8)[0]
            it = m.data[mo + 0xB]
            sizes = struct.unpack_from('<18I', m.data, mo + 0xC)
            ok = (ptr >> 28 == 4 and sum(sizes) == m.i32(mo + 0x54)
                  and 0 < it < 4 and sizes[4] == PER[it] * fc)
            out.append(dict(fc=fc, it=it, seg=seg, ok=ok,
                            move=seg_off + (ptr & 0x0FFFFFFF) + sum(sizes[:4])))
        return out

    def write_back(self):
        """Recompress every edited page into its own slot and refresh its checksums."""
        m = self.m
        out = []
        for pi in sorted(self.dirty):
            e = self.entry(pi)
            off, comp = struct.unpack_from('<II', m.data, e + 8)
            data = bytes(self.cache[pi])
            c = zlib.compressobj(9, zlib.DEFLATED, -15)
            new = c.compress(data) + c.flush()
            slot = self.next.get(off, off + comp) - off
            if len(new) > slot:
                raise ValueError('page %d: %d bytes do not fit its %d-byte slot' % (pi, len(new), slot))
            m.data[off:off + len(new)] = new
            if len(new) < comp:
                m.data[off + len(new):off + comp] = bytes(comp - len(new))
            struct.pack_into('<I', m.data, e + 0xC, len(new))
            struct.pack_into('<I', m.data, e + 0x14, (zlib.crc32(data) ^ 0xFFFFFFFF) & 0xFFFFFFFF)
            m.data[e + 0x18:e + 0x2C] = hashlib.sha1(data).digest()
            m.data[e + 0x2C:e + 0x40] = hashlib.sha1(data[:0x400]).digest()
            m.data[e + 0x40:e + 0x54] = hashlib.sha1(data[-0x400:]).digest()
            out.append((pi, comp, len(new), slot))
        return out


def move_anims(m, pages, base):
    """[(name, type, frames, page index, movement offset in page)] -- every animation with
    root motion whose name holds `move_` ('aim_move' overlays carry none). Members whose
    sizes do not add up are left out.

    Reach keeps frame count, frame info type and resource group/member in a nested Shared
    Animation Data block (+0x30, 0xD4) of a 0x3C element at +0x94, its Tag Resource Groups
    at +0x1AC. An animation without that block BORROWS another graph's (Shared Graph
    Reference +0x1C) and is reached through the lender's own pattern."""
    if pages.h4:
        groups = m.follow_all(base, [0x1E4], [0xC], 'all')
    elif pages.reach:
        groups = m.follow_all(base, [0x1AC], [0xC], 'all')
    else:
        groups = m.follow_all(base, [0xF8], [0xC], 'all')
    res_of = [m.u32(g + 4) & 0xFFFF for g in groups]
    memo = {}
    out = []
    if pages.h4:
        # Halo 4: Animations +0x9C (0x40), Shared Animation Data +0x34 (0xDC): frame info
        # type +0x4, resource group/member +0x18/+0x1A
        els = []
        for el in m.follow_all(base, [0x9C], [0x40], 'all'):
            sh = m.follow_all(el, [0x34], [0xDC], 'all')
            if sh:
                els.append((el, sh[0] + 4, sh[0] + 0x18))
    elif pages.reach:
        els = []
        for el in m.follow_all(base, [0x94], [0x3C], 'all'):
            sh = m.follow_all(el, [0x30], [0xD4], 'all')
            if sh:
                els.append((el, sh[0] + 5, sh[0] + 0x20))
    else:
        els = [(el, el + 0x13, el + 0x28) for el in m.follow_all(base, [0x50], [0x88], 'all')]
    for el, fit_at, group_at in els:
        if not m.data[fit_at]:
            continue
        nm = m.resolve_stringid(m.u32(el)) or ''
        # Halo 4 names its locomotion `locomote_run_<direction>` (the walk is
        # `locomote_walk_inplace`, which carries no root motion and drops out above)
        if ('move_' not in nm and 'locomote_' not in nm) or 'aim_' in nm:
            continue
        g, k = struct.unpack_from('<hh', m.data, group_at)
        if not (0 <= g < len(res_of)):
            continue
        res = res_of[g]
        if res not in memo:
            memo[res] = pages.members(res)
        mem = memo[res]
        if not (0 <= k < len(mem)) or not mem[k]['ok']:
            continue
        mb = mem[k]
        out.append((nm, mb['it'], mb['fc'], pages.page_index(mb['seg']), mb['move']))
    return out


def speed(pg, it, fc, off):
    per = PER[it]
    sx = sum(struct.unpack_from('<f', pg, off + i * per)[0] for i in range(fc))
    sy = sum(struct.unpack_from('<f', pg, off + i * per + 4)[0] for i in range(fc))
    return (sx * sx + sy * sy) ** 0.5 / fc * FPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', required=True)
    ap.add_argument('--game', default='Halo 3')
    ap.add_argument('--out')
    ap.add_argument('--jmad', action='append', default=None)
    ap.add_argument('--mult', type=float)
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--shield-mult', type=float)
    ap.add_argument('--paint', action='append', default=[], help='"<enemy_colors row>=RRGGBB"')
    a = ap.parse_args()
    m = HP.open_map(a.map, a.game)
    pages = Pages(m)
    done = set()
    external = collections.Counter()
    for pat in (a.jmad or ['objects\\characters\\*']):
        for name, base in m.find_tags('jmad', pat):
            rows = move_anims(m, pages, base)
            if not rows:
                continue
            print('%s  (%d move animations)' % (name, len(rows)))
            for nm, it, fc, pi, off in rows:
                if not pages.local(pi):
                    external[name] += 1
                    continue
                pg = pages.get(pi)
                if not a.show and a.mult and (pi, off) not in done:
                    per = PER[it]
                    for i in range(fc):
                        dx, dy = struct.unpack_from('<2f', pg, off + i * per)
                        struct.pack_into('<2f', pg, off + i * per, dx * a.mult, dy * a.mult)
                    done.add((pi, off))
                    pages.dirty.add(pi)
                if (nm.startswith(('combat:', 'any:')) and (':move_front' in nm or 'locomote_run_front' in nm)
                        and ':2:' not in nm):
                    print('   %-40s f=%3d type=%d  %5.2f wu/s' % (nm, fc, it, speed(pg, it, fc, off)))
    for name, n in external.items():
        print('NOT WRITTEN: %s -- %d animation(s) on pages outside this map (vanilla map?)' % (name, n))
    if a.show:
        return
    for pi, old, new, slot in pages.write_back():
        print('page %5d: %6d -> %6d bytes (slot %d)' % (pi, old, new, slot))
    if a.shield_mult:
        import halo_map as hm
        import assembly_plugins as apl
        sub, blk, path = {
            'Halo Reach': ('ReachMCC', 'Old Damage Info', 'objects\\characters\\spartans\\spartans'),
            'Halo 4': ('Halo4MCC', 'Old Damage Info',
                       'objects\\characters\\storm_masterchief\\storm_masterchief'),
        }.get(a.game, ('Halo3MCC', 'New Damage Info', 'objects\\characters\\masterchief\\masterchief'))
        if not os.path.exists(os.path.join(apl.plugins_dir(), sub, 'hlmt.xml')):
            sub = sub.replace('MCC', '')
        pl = hm.Plugin(os.path.join(apl.plugins_dir(), sub, 'hlmt.xml'))
        for _p, base in m.find_tags('hlmt', path):
            old = m.read_tag_field(base, 'Maximum Shield Vitality', pl, blk)
            m.write_tag_field(base, 'Maximum Shield Vitality', old * a.shield_mult, pl, blk)
            print('shield %s: %s -> %s' % (path, old, m.read_tag_field(
                base, 'Maximum Shield Vitality', pl, blk)))
    if a.paint:
        import enemy_colors as ec
        ov = {}
        for spec in a.paint:
            row, col = spec.rsplit('=', 1)
            ov[row.strip()] = {'0': col.strip()}
        for r in ec.apply(m, a.game, ov):
            print('paint:', r.get('field'), r.get('new') or r.get('reason'))
    print('scaled %d movement section(s) x%g on %d page(s)' % (len(done), a.mult or 0, len(pages.dirty)))
    if not a.out:
        sys.exit('--out is required to write')
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()

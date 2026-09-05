r"""Make a weapon that has no resources on one map work, by borrowing the segment
records from a map where it does.

The Kikowani question turned out to be "why does the rocket launcher work on other
ODST levels and not this one", and the answer is small and precise:

  * Every ODST map's `zone` tag has a Tag Resources chunk for every rocket_launcher
    tag -- 60 of them on sc110 AND on sc150, with identical fixup counts. sc150's
    records are fully formed.
  * Each chunk names a `[play] Segment Index`. A segment names Primary/Secondary
    Page Index and offsets. On sc110 those point at pages 348, 349 and 1105; on sc150
    every one of them is **-1**. That is the whole difference.
  * Pages 348/349/1105 are `maps\campaign.map` pages, and **sc150 already carries
    those very page records, at the same indices, with identical offsets and sizes**.
    campaign.map is in sc150's external cache list too.

So the bytes were always reachable. The map simply had no segment pointing at them.
Importing is therefore an in-place field copy -- no block growth, no data copy, no
hashes to recompute, nothing appended:

    for each chunk of the weapon, copy the donor's 0x10-byte Segment record into the
    segment slot this map's own chunk already points at.

The `Sizes` block is empty on every ODST map, so the Size Index fields are inert.

    python h3_import_resources.py --to sc150 --from sc110 --weapon rocket_launcher
    python h3_import_resources.py --to sc150 --from sc110 --weapon rocket_launcher --write

Pair with `h3_raw_residency.py sc150 --survey` before and after: the weapon should
go from "no page at all" to resolving.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                         # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_zone_pools as Z                                        # noqa: E402
import h3_raw_residency as R                                     # noqa: E402

SEG_ELEM = R.PLAY_SEG_ELEM          # 0x10
PAGE_ELEM = R.PLAY_PAGE_ELEM        # 0x58


class Cache:
    def __init__(self, name, game='Halo 3: ODST', vanilla=False):
        path = os.path.join(Z.MAPS[game], name + '.map')
        if vanilla:
            # The baseline is wherever the Baselines folder says; a sibling .bak
            # stops existing once that store moves off the game folder.
            path = V.pristine_source(game, path)
        self.name, self.path = name, path
        self.m = HP.open_map(path, game)
        self.zb = Z._zone_tag(self.m)['base']
        self.pb = R._play_tag(self.m)['base']
        self.seg_base = HP._block_base(self.m, self.pb + R.PLAY_SEGMENTS)
        self.seg_count = self.m.i32(self.pb + R.PLAY_SEGMENTS)
        self.page_base = HP._block_base(self.m, self.pb + R.PLAY_RAW_PAGES)
        self.page_count = self.m.i32(self.pb + R.PLAY_RAW_PAGES)
        self.chunks = self._chunks()

    def _chunks(self):
        """{(class, name): [(chunk index, element offset, segment index)]}"""
        n = self.m.i32(self.zb + R.ZONE_TAG_RESOURCES)
        base = HP._block_base(self.m, self.zb + R.ZONE_TAG_RESOURCES)
        names = {t['index']: (t['class'], t['name'] or '') for t in self.m.tags}
        out = {}
        for i in range(max(0, n)) if base else []:
            e = base + i * R.ZTR_ELEM
            row = self.m.u32(e + 0xC) & 0xFFFF
            if row in names:
                seg = struct.unpack_from('<h', self.m.data, e + R.ZTR_SEGMENT)[0]
                out.setdefault(names[row], []).append((i, e, seg))
        return out

    def seg_bytes(self, i):
        if not self.seg_base or not (0 <= i < self.seg_count):
            return None
        o = self.seg_base + i * SEG_ELEM
        return bytes(self.m.data[o:o + SEG_ELEM])

    def page(self, i):
        if not self.page_base or not (0 <= i < self.page_count):
            return None
        e = self.page_base + i * PAGE_ELEM
        shared = struct.unpack_from('<h', self.m.data, e + 4)[0]
        off, comp, unc = struct.unpack_from('<III', self.m.data, e + 8)
        return (shared, off, comp, unc)


BLOCK = 0x1000
# Never place a borrowed page in the first 64 KB: the run of zeroes at 0x1000 is header
# space, not free space, and the header is the last thing worth corrupting.
HEADER_GUARD = 0x10000


def in_map_gaps(cache):
    """0x1000-aligned, verified all-zero runs where a borrowed raw page can live.

    The first version of this looked at the space between the compressed extents of
    consecutive in-map pages and treated it as padding. It is not: sc150 has NO such
    gap that is both aligned and empty, so that write landed on live data and the map
    was rejected -- the level loaded and bounced straight back to the main menu.

    Placing it OUTSIDE the raw region does not work: 170962944 (aligned, verified
    empty, past the last partition) made the engine reject the map -- the level loaded
    and bounced to the main menu, twice. Being inside the region matters more than
    being aligned, so inter-page padding inside the raw region is tried first even
    though every real page starts on a 0x1000 boundary. On sc150 exactly one such gap
    is empty: 2941 bytes at 92050563.

    The aligned-run scan is kept as a fallback, skipping the first 64 KB because the
    zero run at 0x1000 is header space, not free space.
    """
    data = cache.m.data
    spans = sorted((p[1], p[1] + p[2]) for p in
                   (cache.page(i) for i in range(cache.page_count))
                   if p and p[0] < 0 and p[2] > 0)
    inside = []
    for (a_start, a_end), (b_start, _) in zip(spans, spans[1:]):
        if b_start > a_end and not any(data[a_end:b_start]):
            inside.append((a_end, b_start - a_end))
    inside.sort(key=lambda r: -r[1])

    runs, start = [], None
    for off in range(HEADER_GUARD, (len(data) // BLOCK) * BLOCK, BLOCK):
        if any(data[off:off + BLOCK]):
            if start is not None:
                runs.append((start, off - start))
                start = None
        elif start is None:
            start = off
    if start is not None:
        runs.append((start, len(data) - start))
    runs.sort(key=lambda r: -r[1])
    return inside + runs


def orphan_pages(cache):
    """Page records no segment references -- safe to repurpose in place."""
    used = set()
    base = HP._block_base(cache.m, cache.pb + R.PLAY_SEGMENTS)
    for i in range(cache.seg_count):
        p, s = struct.unpack_from('<hh', cache.m.data, base + i * SEG_ELEM)
        used.update(x for x in (p, s) if x >= 0)
    return [i for i in range(cache.page_count) if i not in used]


def import_page(dst, src, page_index, gaps, orphans):
    """Copy one in-map raw page from the donor into padding here, and point a spare
    page record at it. Returns the new page index, or None."""
    sp = src.page(page_index)
    if sp is None or sp[0] >= 0:
        return None
    size = sp[2]
    # Only write where the file is genuinely empty, and keep the page block-aligned:
    # raw pages start on 0x1000 boundaries everywhere in these caches, so an unaligned
    # borrowed page is a plausible way to make the engine reject the map.
    spot, off = None, None
    for g in gaps:
        if g[1] < size:
            continue
        if any(dst.m.data[g[0]:g[0] + size]):
            continue                       # not actually free -- something lives here
        spot, off = g, g[0]
        break
    if spot is None or not orphans:
        return None
    gaps.remove(spot)
    if spot[1] - size > BLOCK:
        gaps.insert(0, (off + size, spot[1] - size))
    dst.m.data[off:off + size] = src.m.data[sp[1]:sp[1] + size]
    new_index = orphans.pop(0)
    # Copy the donor's whole record -- hashes and CRC come along unchanged because the
    # bytes are identical -- then correct only the Block Offset.
    s_e = src.page_base + page_index * PAGE_ELEM
    d_e = dst.page_base + new_index * PAGE_ELEM
    dst.m.data[d_e:d_e + PAGE_ELEM] = src.m.data[s_e:s_e + PAGE_ELEM]
    struct.pack_into('<I', dst.m.data, d_e + 8, off)
    return new_index


def plan(dst, src, want, remap=None):
    """What would be copied, and whether every page it needs already exists here.

    `remap` is {donor page index: this map's page index} for pages imported by
    import_page(); those segment records need their page fields rewritten rather than
    copied verbatim.
    """
    remap = remap or {}
    todo, missing, skipped = [], [], []
    for key, dlist in sorted(dst.chunks.items()):
        cls, nm = key
        if want.lower() not in nm.lower():
            continue
        slist = src.chunks.get(key)
        if not slist:
            skipped.append((nm, 'not in %s' % src.name))
            continue
        if len(slist) != len(dlist):
            skipped.append((nm, 'chunk count %d vs %d' % (len(dlist), len(slist))))
            continue
        for (di, de, dseg), (si, se, sseg) in zip(dlist, slist):
            raw = src.seg_bytes(sseg)
            if raw is None or dseg < 0 or dseg >= dst.seg_count:
                skipped.append((nm, 'segment %d/%d unusable' % (dseg, sseg)))
                continue
            prim, sec = struct.unpack_from('<hh', raw, 0)
            ok, fixed = True, bytearray(raw)
            for slot, pi in ((0, prim), (2, sec)):
                if pi < 0:
                    continue
                if pi in remap:
                    struct.pack_into('<h', fixed, slot, remap[pi])
                    continue
                a, b = dst.page(pi), src.page(pi)
                if a is None or a != b:
                    missing.append((nm, pi, b, a))
                    ok = False
            if ok:
                # report the page indices as WRITTEN, not as the donor numbered them
                fp, fs = struct.unpack_from('<hh', fixed, 0)
                todo.append((cls, nm, dseg, sseg, bytes(fixed), fp, fs))
    return todo, missing, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--to', required=True, help='map to fix, e.g. sc150')
    ap.add_argument('--donor', '--from', dest='donor', required=True,
                    help='map that already has the weapon working, e.g. sc110')
    ap.add_argument('--weapon', required=True, help='basename, e.g. rocket_launcher')
    ap.add_argument('--game', default='Halo 3: ODST', choices=sorted(Z.MAPS))
    ap.add_argument('--write', action='store_true', help='actually patch the map')
    ap.add_argument('--skip-missing', action='store_true',
                    help='import the chunks whose pages this map already has, instead '
                         'of refusing because some other chunk needs a page it lacks')
    ap.add_argument('--no-page-import', action='store_true',
                    help='never copy a donor page into this map\'s file')
    a = ap.parse_args(argv)

    dst = Cache(a.to, a.game)
    src = Cache(a.donor, a.game, vanilla=True)
    print('%s (%d segments) <- %s (%d segments)'
          % (dst.name, dst.seg_count, src.name, src.seg_count))

    # First pass: what is missing? Anything the donor keeps in its OWN raw data has to
    # be carried over, since it is not in a shared cache both maps already reference.
    _, missing0, _ = plan(dst, src, a.weapon)
    remap = {}
    if missing0 and a.no_page_import:
        print('  %d donor page(s) absent here; --no-page-import, so those chunks are '
              'left alone' % len({pi for _, pi, _, _ in missing0}))
    elif missing0:
        need = sorted({pi for _, pi, _, _ in missing0})
        gaps, orphans = in_map_gaps(dst), orphan_pages(dst)
        print('  %d donor page(s) absent here: %s' % (len(need), need))
        print('  %d padding gap(s), largest %d bytes; %d spare page record(s)'
              % (len(gaps), max((g[1] for g in gaps), default=0), len(orphans)))
        for pi in need:
            new = import_page(dst, src, pi, gaps, orphans)
            if new is None:
                print('    !! could not place donor page %d' % pi)
            else:
                sp = src.page(pi)
                remap[pi] = new
                print('    donor page %d (%d bytes) -> this map\'s page record %d'
                      % (pi, sp[2], new))

    todo, missing, skipped = plan(dst, src, a.weapon, remap)
    live = [t for t in todo if t[5] >= 0 or t[6] >= 0]
    print('  %d chunk(s) matched, %d of them carry a real page' % (len(todo), len(live)))
    for cls, nm, dseg, sseg, raw, prim, sec in live:
        print('    %-4s %-40s seg %-5d <- %s seg %-5d  pages %d/%d'
              % (cls, nm.rsplit('\\', 1)[-1][:40], dseg, src.name, sseg, prim, sec))
    for nm, pi, want_pg, got in missing:
        print('    !! %s needs page %d = %s, this map has %s'
              % (nm.rsplit('\\', 1)[-1], pi, want_pg, got))
    for nm, why in skipped[:10]:
        print('    -- skipped %s (%s)' % (nm.rsplit('\\', 1)[-1], why))
    if missing and not a.skip_missing:
        print('  REFUSING: %d chunk(s) need a page that is not present here, so a '
              'segment copy would point at nothing. --skip-missing imports the rest.'
              % len(missing))
        return 1
    if missing:
        print('  skipping %d chunk(s) whose page is absent; importing the other %d'
              % (len(missing), len(todo)))
    if not a.write:
        print('\n  dry run. Re-run with --write to apply.')
        return 0

    for cls, nm, dseg, sseg, raw, prim, sec in todo:
        o = dst.seg_base + dseg * SEG_ELEM
        dst.m.data[o:o + SEG_ELEM] = raw
    dst.m.save(dst.path)
    print('\n  wrote %d segment record(s) into %s' % (len(todo), dst.path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

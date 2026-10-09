r"""Put one sprite into a Halo 1 HUD sprite sheet (HCEEK bitmap tag) AND its `_r` twin.

EVERY Halo 1 HUD sheet the ports touch has a twin: `hud_msg_icons` / `hud_msg_icons_r`,
`hud_reticles` / `hud_reticles_r` (32-bit colour copies of the same stock layout; both are
compiled into every map, and MCC ships both loose in halo1\tags). A weapon HUD names ONE
sequence index, so a port's sprite must sit at the SAME index in each. Found 2026-10-06:
the sword's Halo 3 reticle went into `hud_reticles` only and drew as a BLUE SQUARE in game
-- the `_r` sheet, still at its 17 stock sequences, had nothing at #17.

`put(...)` writes one sheet: a sequence with this name is replaced in place; otherwise the
sprite goes at `index` (default: appended), padding any gap with EMPTY sequences, so that
the twins line up. Pixel formats: a8y8 (luminance = white, alpha = shape) and a8r8g8b8.
"""
import copy
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402

COMBINED = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                        'ui', 'hud', 'bitmaps', 'combined')
BACKUP = '.before_pickable'


def sheet_path(name):
    return os.path.join(COMBINED, name + '.bitmap')


def _pixels(img, fmt, w, h):
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    if fmt == 'a8y8':
        a = np.array(canvas.split()[3])
        lum = np.array(canvas.convert('L'))
        lum = np.where(a > 0, np.maximum(lum, 1), 0).astype(np.uint8)
        return np.stack([lum, a], axis=-1).astype(np.uint8).tobytes()
    if fmt == 'a8r8g8b8':
        return canvas.tobytes('raw', 'BGRA')
    raise SystemExit('sheet format %s not handled' % fmt)


def mip_chain(img, fmt, w, h):
    """Level 0 + every half-size level down to 1 x 1 (BOX filtered), in the sheet's format."""
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    raw, n = bytearray(), 0
    while True:
        raw += _pixels(canvas, fmt, w, h)
        if w == 1 and h == 1:
            return bytes(raw), n
        w, h = max(1, w // 2), max(1, h // 2)
        canvas = canvas.resize((w, h), Image.BOX)
        n += 1


def put(sheet, name, img, template_seq, sheet_size, reg, index=None, mips=False):
    """img: RGBA (white art + alpha) placed at (0, 0) of a new sheet_size bitmap.
    reg: registration point in PIXELS of that bitmap. Returns the sequence index.
    `mips`: the bitmap carries a full MIP CHAIN (the Spartan Laser, test 7: stock HUD sheets
    have none, so Halo 1 minifies a reticle unfiltered -- thin Halo 3 strokes break up at
    every resolution); the replaced bitmap's old pixels are compacted away."""
    p = sheet_path(sheet)
    if not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)
    t = bitm_def.build(filepath=p)
    d = t.data.tagdata
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    pix = bytearray(d.processed_pixel_data.data)
    tseq = seqs[template_seq]
    tb = bms[tseq.sprites.STEPTREE[0].bitmap_index]
    fmt = tb.format.enum_name
    W, H = sheet_size
    raw = _pixels(img, fmt, W, H)
    nmip = 0
    if mips:
        raw, nmip = mip_chain(img, fmt, W, H)
    have = [i for i, q in enumerate(seqs) if q.sequence_name == name[:31]]
    if have:
        si = have[0]
        bi = seqs[si].sprites.STEPTREE[0].bitmap_index
        nb = bms[bi]
        if (nb.width, nb.height) == (W, H) and nb.mipmaps == nmip:
            pix[nb.pixels_offset:nb.pixels_offset + len(raw)] = raw
        else:                         # another size / mip count: a new bitmap, repointed
            bms.append(copy.deepcopy(nb))
            nb = bms[len(bms) - 1]
            nb.width, nb.height = W, H
            nb.mipmaps = nmip
            nb.pixels_offset = len(pix)
            pix += raw
            bi = len(bms) - 1
            seqs[si].first_bitmap_index = bi
    else:
        reuse = index is not None and index < len(seqs)
        if reuse and len(seqs[index].sprites.STEPTREE):
            raise SystemExit('%s: index %d is taken by %r' % (sheet, index, seqs[index].sequence_name))
        bms.append(copy.deepcopy(tb))
        nb = bms[len(bms) - 1]
        nb.width, nb.height = W, H
        nb.mipmaps = nmip
        nb.pixels_offset = len(pix)
        pix += raw
        bi = len(bms) - 1
        while index is not None and len(seqs) < index:           # empty pads keep twins aligned
            seqs.append(copy.deepcopy(tseq))
            pad = seqs[len(seqs) - 1]
            pad.sequence_name = 'pad'
            pad.first_bitmap_index, pad.bitmap_count = -1, 0
            while len(pad.sprites.STEPTREE):
                pad.sprites.STEPTREE.pop()
        if reuse:                     # an EMPTY stock sequence (hud_msg_icons_r #25) is free
            si = index
            seqs[si].sprites.STEPTREE.append(copy.deepcopy(tseq.sprites.STEPTREE[0]))
        else:
            seqs.append(copy.deepcopy(tseq))
            si = len(seqs) - 1
        seqs[si].sequence_name = name[:31]
        seqs[si].first_bitmap_index, seqs[si].bitmap_count = bi, 1
    for sp in seqs[si].sprites.STEPTREE:
        sp.bitmap_index = bi
        sp.left_side, sp.right_side = 0.0, img.width / float(W)
        sp.top_side, sp.bottom_side = 0.0, img.height / float(H)
        sp.registration_point_x = reg[0] / float(W)
        sp.registration_point_y = reg[1] / float(H)
    _compact(d, pix)
    t.filepath = p
    t.serialize(temp=False, backup=False)
    return si


def put_frames(sheet, name, frames, template_seq, index):
    """A MULTI-FRAME sequence (the Spartan Laser's charge indicator): `frames` = [(RGBA
    image, registration px in it)], each its own small bitmap + sprite, at `index` (empty
    pads before it; a sequence of this name at `index` is replaced, its old bitmaps left
    unreferenced). The registration point may lie OUTSIDE the sprite (a small triangle
    orbiting the crosshair). Returns the sequence index."""
    p = sheet_path(sheet)
    if not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)
    t = bitm_def.build(filepath=p)
    d = t.data.tagdata
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    pix = bytearray(d.processed_pixel_data.data)
    tseq = seqs[template_seq]
    tb = bms[tseq.sprites.STEPTREE[0].bitmap_index]
    fmt = tb.format.enum_name
    if index < len(seqs) and len(seqs[index].sprites.STEPTREE) and seqs[index].sequence_name != name[:31]:
        raise SystemExit('%s: index %d is taken by %r' % (sheet, index, seqs[index].sequence_name))
    while len(seqs) <= index:                     # empty pads keep twins aligned
        seqs.append(copy.deepcopy(tseq))
        pad = seqs[len(seqs) - 1]
        pad.sequence_name = 'pad'
        pad.first_bitmap_index, pad.bitmap_count = -1, 0
        while len(pad.sprites.STEPTREE):
            pad.sprites.STEPTREE.pop()
    sq = seqs[index]
    sprite = copy.deepcopy(tseq.sprites.STEPTREE[0])
    while len(sq.sprites.STEPTREE):
        sq.sprites.STEPTREE.pop()
    first = len(bms)
    for img, (rx, ry) in frames:
        W, H = img.size
        bms.append(copy.deepcopy(tb))
        nb = bms[len(bms) - 1]
        nb.width, nb.height, nb.mipmaps = W, H, 0
        nb.pixels_offset = len(pix)
        pix += _pixels(img, fmt, W, H)
        sq.sprites.STEPTREE.append(copy.deepcopy(sprite))
        sp = sq.sprites.STEPTREE[len(sq.sprites.STEPTREE) - 1]
        sp.bitmap_index = len(bms) - 1
        sp.left_side, sp.right_side, sp.top_side, sp.bottom_side = 0.0, 1.0, 0.0, 1.0
        sp.registration_point_x, sp.registration_point_y = rx / float(W), ry / float(H)
    sq.sequence_name = name[:31]
    sq.first_bitmap_index, sq.bitmap_count = first, len(frames)
    _compact(d, pix)
    t.filepath = p
    t.serialize(temp=False, backup=False)
    return index


def _compact(d, pix):
    """Drop the bitmaps no sprite uses any more (a replaced multi-frame sequence's old
    frames) and their pixels; every sprite / sequence index renumbered."""
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    used = sorted({sp.bitmap_index for q in seqs for sp in q.sprites.STEPTREE} |
                  {q.first_bitmap_index for q in seqs if q.first_bitmap_index >= 0})
    offs = sorted(set(b.pixels_offset for b in bms)) + [len(pix)]
    size = {o: offs[offs.index(o) + 1] - o for o in offs[:-1]}
    new_pix, remap, keep = bytearray(), {}, []
    for i in used:
        b = bms[i]
        chunk = pix[b.pixels_offset:b.pixels_offset + size[b.pixels_offset]]
        remap[i] = len(keep)
        b.pixels_offset = len(new_pix)
        new_pix += chunk
        keep.append(b)
    if len(keep) == len(bms):
        d.processed_pixel_data.data = bytes(pix)
        return
    import copy as _c
    kept = [_c.deepcopy(b) for b in keep]
    bms[:] = []
    for b in kept:
        bms.append(b)
    for q in seqs:
        for sp in q.sprites.STEPTREE:
            sp.bitmap_index = remap[sp.bitmap_index]
        if q.first_bitmap_index >= 0:
            q.first_bitmap_index = remap[q.first_bitmap_index]
    d.processed_pixel_data.data = bytes(new_pix)


def put_twins(sheet, name, img, template_seq, sheet_size, reg, index=None, mips=False):
    """The sheet and its `_r` twin, at one index -- the port's RESERVED index when given
    (ports_h1 reservations, H1_PORT_PLAN.md), so ports added in any order keep theirs."""
    i = put(sheet, name, img, template_seq, sheet_size, reg, index=index, mips=mips)
    if index is not None and i != index:
        raise SystemExit('%s: %r already sits at %d, reserved %d' % (sheet, name, i, index))
    j = put(sheet + '_r', name, img, template_seq, sheet_size, reg, index=i, mips=mips)
    if i != j:
        raise SystemExit('%s: %r landed at %d, its _r twin at %d' % (sheet, name, i, j))
    return i

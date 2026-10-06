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


def put(sheet, name, img, template_seq, sheet_size, reg, index=None):
    """img: RGBA (white art + alpha) placed at (0, 0) of a new sheet_size bitmap.
    reg: registration point in PIXELS of that bitmap. Returns the sequence index."""
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
    have = [i for i, q in enumerate(seqs) if q.sequence_name == name[:31]]
    if have:
        si = have[0]
        nb = bms[seqs[si].sprites.STEPTREE[0].bitmap_index]
        if (nb.width, nb.height) != (W, H):
            raise SystemExit('%s %r: bitmap is %dx%d, sprite wants %dx%d'
                             % (sheet, name, nb.width, nb.height, W, H))
        pix[nb.pixels_offset:nb.pixels_offset + len(raw)] = raw
        bi = seqs[si].sprites.STEPTREE[0].bitmap_index
    else:
        reuse = index is not None and index < len(seqs)
        if reuse and len(seqs[index].sprites.STEPTREE):
            raise SystemExit('%s: index %d is taken by %r' % (sheet, index, seqs[index].sequence_name))
        bms.append(copy.deepcopy(tb))
        nb = bms[len(bms) - 1]
        nb.width, nb.height = W, H
        nb.mipmaps = 0
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
    d.processed_pixel_data.data = bytes(pix)
    t.filepath = p
    t.serialize(temp=False, backup=False)
    return si


def put_twins(sheet, name, img, template_seq, sheet_size, reg):
    """The sheet and its `_r` twin, at one index."""
    i = put(sheet, name, img, template_seq, sheet_size, reg)
    j = put(sheet + '_r', name, img, template_seq, sheet_size, reg, index=i)
    if i != j:
        raise SystemExit('%s: %r landed at %d, its _r twin at %d' % (sheet, name, i, j))
    return i

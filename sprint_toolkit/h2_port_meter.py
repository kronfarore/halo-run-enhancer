r"""Step 7 of a Halo 2 port: an ammo meter for the port's magazine, its own HUD (cloned from the
donor's), and the HUD's small stowed-weapon (backpack) icon (generalized from h2_saw_meter.py).

Halo 2 draws the ammo readout as ONE bitmap of tick art revealed as the magazine empties, so the
count is purely a property of the art (battle_rifle_meter 197x34 = 2 rows of 18, smg_meter
198x42 = 3 of 20; the tick is 6 px wide in both). BLUE IS THE THRESHOLD, a property of the CELL:
the threshold field is laid over every pixel first, then the tick art without touching blue
(PORTING "Steps 6 and 7"). The config's `meter` section:

    donor_meter, rel, name        the donor's meter tag, the meters folder, the port's bitmap name
    donor_hud, port_hud, weapon   the HUD cloned donor -> port, the weapon repointed at it
    rounds, rows, canvas, tick_w  the art (keep the donor's canvas so the widget does not move)
    sequences                     [{'rounds', 'tick_w'?}, ...] one meter a magazine size on one
                                  multi-sequence plate (seq 0 = Original; Balanced rows pick another)
    backpack, backpack_port, backpack_size, model_3p   the stowed icon drawn from the port's mesh
    model_skip                    a JMS mesh's materials left out of it (h3_weapon_glyph.mesh)
    preview                       a --show preview file name in %TEMP%

    python h2_port_meter.py <key> [--rounds 72] [--show]
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')


def donor_art(m):
    out = os.path.join(os.environ.get('TEMP', '.'), '_h2meter')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', m['donor_meter'], out],
                   cwd=H2EK, capture_output=True, text=True)
    path = out + os.path.basename(m['donor_meter']) + '_00_00.tga'
    if not os.path.exists(path):
        raise SystemExit('could not export %s' % m['donor_meter'])
    return Image.open(path).convert('RGBA')


def tick_sprite(img, tick_w):
    a = np.asarray(img)
    alpha = a[:, :, 3]
    cols = [i for i in range(a.shape[1]) if alpha[:, i].sum() > 0]
    rows = [i for i in range(a.shape[0]) if alpha[i, :].sum() > 0]
    x0 = cols[0]
    y0, y1 = rows[0], rows[0] + (a.shape[0] // 2) - 2
    return img.crop((x0, y0, x0 + tick_w, y1))


def thresholds(n):
    """254 down to 4 over the magazine, whatever its size (measured on both shipped meters)."""
    return [int(round(254 - i * 250.0 / max(n - 1, 1))) for i in range(n)]


def source_tick(m, sprite, tick_w):
    """`tick_art` {'h3': (chud sheet, sequence), 'h': px} (the Spike Rifle, boot 1: 'the pips
    look different from the original'): the SOURCE game's own round -- the first pip of Halo 3's
    meter sprite, its ALPHA as the shape (Halo 3 keeps the threshold in the colour), scaled to
    tick_w x h, filled with the donor tick's own lit colour (R, G; blue is the threshold)."""
    import h3_hud_art
    sheet, seq = m['tick_art']['h3']
    art, _reg = h3_hud_art.sprite(sheet, seq)
    a = np.asarray(art.convert('RGBA'))[:, :, 3]
    cols = np.nonzero(a.sum(0))[0]
    x0 = x1 = int(cols[0])
    while x1 + 1 < a.shape[1] and a[:, x1 + 1].any():
        x1 += 1
    pip = a[:, x0:x1 + 1]
    rows = np.nonzero(pip.sum(1))[0]
    y0 = y1 = int(rows[0])
    while y1 + 1 < pip.shape[0] and pip[y1 + 1].any():
        y1 += 1
    pip = pip[y0:y1 + 1]
    h = m['tick_art']['h']
    alpha = np.asarray(Image.fromarray(pip, 'L').resize((tick_w, h), Image.LANCZOS))
    lit = np.asarray(sprite)
    ink = lit[lit[:, :, 3] > 128]
    rgb = ink[:, :3].max(0) if len(ink) else np.array([0, 254, 254])
    # Halo 2's lit mask is the COLOUR (the magnum meter: green = the shape, alpha = the shape at the
    # donor's dim level, 136): colour and alpha both carry the pip's shape -- a flat colour lit the
    # whole tick rectangle (the Mauler, boot 2: 'the loaded pips are full rectangles')
    shape = alpha.astype(np.float32) / 255.0
    dim = int(lit[:, :, 3].max()) or 255
    out = np.zeros((h, tick_w, 4), np.uint8)
    for k in range(3):
        out[:, :, k] = np.round(rgb[k] * shape).astype(np.uint8)
    out[:, :, 3] = np.round(dim * shape).astype(np.uint8)
    print('   tick art: %s #%d pip %dx%d -> %dx%d' % (sheet, seq, x1 - x0 + 1, y1 - y0 + 1, tick_w, h))
    return out


def build(m, rounds, rows):
    donor = donor_art(m)
    tick_w = m['tick_w']
    sprite = tick_sprite(donor, tick_w)
    per_row = -(-rounds // rows)
    w, h = m['canvas']
    pitch = w / float(per_row)
    row_pitch = h / float(rows)
    tick_h = int(row_pitch) - 1
    if m.get('tick_art'):
        small = source_tick(m, sprite, tick_w)
        tick_h = small.shape[0]
    else:
        small = np.asarray(sprite.resize((tick_w, tick_h), Image.LANCZOS)).astype(np.uint8)

    sheet = np.zeros((h, w, 4), dtype=np.uint8)
    thr = thresholds(rounds)
    edges = [int(round(c * pitch)) for c in range(per_row)] + [w]
    bands = [int(round(r * row_pitch)) for r in range(rows)] + [h]
    # the threshold field first, over every pixel (blue = the cell's threshold)
    for r in range(rows):
        for c in range(per_row):
            i = min(r * per_row + c, rounds - 1)
            sheet[bands[r]:bands[r + 1], edges[c]:edges[c + 1], 2] = thr[i]
    # then the tick art: red, green and alpha; blue is not touched
    for i in range(rounds):
        r, c = divmod(i, per_row)
        x = edges[c] + max((edges[c + 1] - edges[c] - tick_w) // 2, 0)
        y = bands[r] + max((bands[r + 1] - bands[r] - tick_h) // 2, 0)
        if x + tick_w > w or y + tick_h > h:
            continue
        for k in (0, 1, 3):
            sheet[y:y + tick_h, x:x + tick_w, k] = small[:, :, k]
    print('   %d ticks, %d rows of %d, pitch %.2f x %.2f, tick %dx%d on a %dx%d sheet, '
          'blue %d..%d' % (rounds, rows, per_row, pitch, row_pitch, tick_w, tick_h, w, h,
                           thr[-1], thr[0]))
    return Image.fromarray(sheet, 'RGBA')


def plate(sheets):
    """Several meters as ONE multi-sequence bitmap (the Mauler, boot 3: Original 5 rounds,
    Balanced 10 -- the meter is a FRACTION reveal, so each magazine needs its own art): Bungie's
    colour-plate layout (the dual plates, h2_port_hud_plate) -- pixel (0,0) the BLUE background
    key, (1,0) the MAGENTA sequence divider, a full magenta row opening each sequence, one image a
    sequence ringed by background. Key and divider carry alpha 0 like Bungie's; the art's own
    background is (0, 0, threshold <= 254, 0), never the key."""
    w = max(s.size[0] for s in sheets) + 2
    h = sum(s.size[1] + 3 for s in sheets) + 1
    out = np.zeros((h, w, 4), np.uint8)
    out[:, :, 2] = 255                                   # blue key, alpha 0
    out[0, 1] = (255, 0, 255, 0)
    y = 1
    for s in sheets:
        out[y, :] = (255, 0, 255, 0)                     # the sequence's divider row
        a = np.asarray(s)
        out[y + 2:y + 2 + a.shape[0], 1:1 + a.shape[1]] = a
        y += a.shape[0] + 3
    return Image.fromarray(out, 'RGBA')


def point(tag, cls, old, new):
    have = h2_tagref.references(tag)
    if (cls, new) in have and (cls, old) not in have:
        print('   %-28s already points at the port' % os.path.basename(tag))
        return
    # a dual-wield HUD names its meter TWICE (ammo_meter_right / _left, the SMG's -- the Spike
    # Rifle, 2026-10-21): every copy moves, one at a time (every=True refuses when another
    # record has that path's length, as the AR's FP models)
    move_each(tag, cls, old, new, have.count((cls, old)))


def move_each(tag, cls, old, new, count):
    for _k in range(max(count, 1)):
        h2_tagref.set_reference(tag, cls, old, new, nth=0 if count > 1 else None)


def run_lines(p):
    return ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10)).split(chr(10))


def backpack(m):
    import h3_weapon_glyph as wg
    verts, idx = wg.mesh(m['model_3p'], m.get('model_skip', ()))
    w, h = m['backpack_size']
    cov = wg.close_gaps(wg.silhouette(verts, idx, w, h, margin=0), 3)
    px = wg.stylise(cov)
    im = Image.new('RGBA', (w, h))
    im.putdata([(r * 17, g * 17, b * 17, a * 17) for a, r, g, b in px])
    port = m['backpack_port']
    data = os.path.join(H2EK, 'data', os.path.dirname(port))
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, os.path.basename(port) + '.tif')
    im.save(tif, compression=None)
    print('   %s  %dx%d, %d ink' % (os.path.basename(tif), w, h, sum(1 for q in px if q[0])))
    dest = os.path.join(TAGS, port + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, m['backpack'] + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', os.path.dirname(port)],
                       cwd=H2EK, capture_output=True, text=True)
    for line in run_lines(p):
        line = ' '.join(line.split())
        if os.path.basename(port) in line or 'bitmap created' in line:
            print('   | %s' % line)
    hud = os.path.join(TAGS, m['port_hud'] + '.new_hud_definition')
    point(hud, 'bitm', m['backpack'], port)
    # the port's backpack is ONE image: its widget's sequence indices become 0 (the BR's were
    # 0 already; the SMG's ask for image 1 of the shared sheet -- the Spike Rifle, 2026-10-21)
    import h2_port_scope
    import h2_tagfield
    for idx, _name, ref, seq in h2_port_scope.widgets(hud):
        if ref == port and any(seq):
            for field in ('fullscreen', 'halfscreen', 'quarterscreen'):
                h2_tagfield.set_field(hud, field + ' sequence index', 0, 'bitmap widgets', idx)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    m = ports_h2.get(argv[0], 'meter')
    if '--backpack-only' in argv or m.get('backpack_only'):
        # a port with NO ammo meter (the Spartan Laser, A2: a battery weapon on the beam rifle's HUD,
        # cloned in step 3): only the stowed-weapon icon -- `backpack`, `backpack_port`,
        # `backpack_size`, `model_3p`, `port_hud`
        print('the HUD weapon symbol (no ammo meter):')
        backpack(m)
        return
    rounds = m['rounds']
    if '--rounds' in argv:
        rounds = int(argv[argv.index('--rounds') + 1])
    if m.get('sequences') and '--rounds' not in argv:
        # `sequences` [{'rounds', 'tick_w'?, 'rows'?}, ...]: one meter a magazine size, sequence
        # 0 = the tags' own (Original) magazine; the catalog's Balanced rows pick another by the
        # meter widgets' sequence index
        art = plate([build(dict(m, tick_w=s.get('tick_w', m['tick_w'])), s['rounds'],
                           s.get('rows', m.get('rows', 3))) for s in m['sequences']])
        print('   %d sequences on one %dx%d plate' % (len(m['sequences']), art.size[0], art.size[1]))
    else:
        art = build(m, rounds, m.get('rows', 3))
    # --show leaves the kit's source image alone: its picture goes to TEMP
    data = os.environ.get('TEMP', '.') if '--show' in argv else os.path.join(H2EK, 'data', m['rel'])
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, m['name'] + '.tif')
    art.save(tif, compression=None)
    print('   wrote %s' % tif)
    if '--show' in argv:
        png = os.path.join(os.environ.get('TEMP', '.'), m.get('preview', m['name'] + '_preview.png'))
        art.resize((art.size[0] * 3, art.size[1] * 3), Image.NEAREST).save(png)
        print('   preview %s' % png)
        return
    dest = os.path.join(TAGS, m['rel'], m['name'] + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, m['donor_meter'] + '.bitmap'), dest)
        print('   %s.bitmap seeded from %s' % (m['name'], os.path.basename(m['donor_meter'])))
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', m['rel']],
                       cwd=H2EK, capture_output=True, text=True)
    for line in run_lines(p):
        line = ' '.join(line.split())
        if m['name'] in line or 'bitmap created' in line:
            print('   | %s' % line)
    hud = os.path.join(TAGS, m['port_hud'] + '.new_hud_definition')
    if not os.path.exists(hud):
        shutil.copy(os.path.join(TAGS, m['donor_hud'] + '.new_hud_definition'), hud)
        print('   %s cloned from %s' % (m['port_hud'], m['donor_hud']))
    point(hud, 'bitm', m['donor_meter'], B.join([m['rel'], m['name']]))
    point(os.path.join(TAGS, m['weapon']), 'nhdt', m['donor_hud'], m['port_hud'])
    print('the HUD weapon symbol:')
    backpack(m)


if __name__ == '__main__':
    main()

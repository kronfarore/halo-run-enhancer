"""Halo 1 bullet-tick ammo display for any magazine size N, in the AR's own style.

The AR's solo magazine readout is two HUD elements on loaded ammo (weapon_hud_interface):
  static  ui\\hud\\bitmaps\\combined\\hud_ammo_alphas seq 1  -- 60 tick silhouettes (a8y8)
  meter   ui\\hud\\bitmaps\\combined\\hud_ammo_meters seq 1  -- the same ticks; luminance = the
          tick's threshold 4k (k = 1..60, tick 1 top-left, row by row), alpha = the shape
Layout: 3 rows of 20, pitch 20.74 px, row pitch 34 px, each row 14.5 px further left; the
static art sits (-4, -4) from the meter art. Generalised: threshold of tick k =
step(N) * k, where step = 255 // N is also the element's alpha_multiplier.

Writes two NEW bitmap tags (clones of the AR's, one bitmap / one sequence each) and
returns their paths; the weapon's HUD interface points its two elements at sequence 0.

    python ammo_meter.py <N> <out tag base, e.g. weapons\\saw\\bitmaps\\saw_ammo>
"""
import copy, math, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.bitm import bitm_def

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
COMB = os.path.join(TAGS, 'ui', 'hud', 'bitmaps', 'combined')
W, H = 512, 128
BOX_W, BOX_H = 450, 104          # the AR's ticks occupy x 5..448, y 5..102 of the meter art
PITCH, ROW_PITCH, SLANT = 394 / 19.0, 34.0, 14.5   # AR: row 1 runs x 34..428 over 19 gaps
TICK = None


def ar_tick():
    """The AR's first tick silhouette (alpha), cut from the static art."""
    d = bitm_def.build(filepath=os.path.join(COMB, 'hud_ammo_alphas.bitmap')).data.tagdata
    b = d.bitmaps.STEPTREE[1]
    im = Image.frombytes('LA', (b.width, b.height),
                         bytes(d.processed_pixel_data.data)[b.pixels_offset:
                                                            b.pixels_offset + b.width * b.height * 2])
    a = np.array(im.split()[1])
    return a[1:31, 30:51]          # meter tick 1 is x 34..54, y 5..34; static is (-4, -4)


def plan(n):
    """(rounds_per_tick, ticks, luminance step, alpha_multiplier) for a magazine of n.

    The engine lights a tick while its threshold <= rounds * alpha_multiplier + alpha_bias,
    and luminance is 8-bit -- so n ticks one round apart need n distinct levels, and the
    step 255 // n is also the multiplier (60 rounds -> the AR's stock 4).

    The step must stay >= 2, which is the HEADROOM: with a step of 1 the bias of 1 is a
    whole tick wide and the meter reads one bullet high (in game at 135 rounds, 2026-09-21).
    Past 127 rounds there is no room for one tick per round, so ticks take p rounds each --
    and the multiplier is step // p, which is why the step is rounded down to a multiple
    of p: it has to divide exactly, or the ticks drift out of step with the rounds."""
    n = max(1, int(n))
    for p in range(1, 4):                    # rounds per tick: 1 up to 127, then 2, 3
        ticks = -(-n // p)
        step_ = (255 // ticks) // p * p      # a multiple of p, or the ticks drift
        if step_ >= max(2, p) and step_ * ticks <= 255:
            return p, ticks, step_, step_ // p
    # Past 255 rounds no 8-bit meter can resolve the magazine: the top threshold would
    # have to exceed 255. The bar then fills at 255 rounds and stays full above it.
    ticks = min(85, -(-n // 3))
    return 3, ticks, 3, 1


def step(n):
    """The alpha_multiplier a weapon's HUD element needs for a magazine of n."""
    return plan(n)[3]


def threshold(k, n):
    """Meter luminance of tick k (1..ticks): none at empty, the last at a full magazine."""
    return plan(n)[2] * k


def layout(n):
    """(rows, per_row, scale) that fits n ticks in the AR's box at the largest scale."""
    best = None
    for rows in range(1, 9):
        per = math.ceil(n / rows)
        s = min(1.0, BOX_W / (per * PITCH + (rows - 1) * SLANT), BOX_H / (rows * ROW_PITCH - 4))
        if best is None or s > best[2]:
            best = (rows, per, s)
    return best


def render(n):
    """n is the MAGAZINE, and the sheet holds as many ticks as it takes to show it."""
    rounds_per, n_ticks, _s, _mult = plan(n)
    tick = ar_tick()
    rows, per, s = layout(n_ticks)
    th, tw = tick.shape
    tick_img = Image.fromarray(tick).resize((max(1, round(tw * s)), max(1, round(th * s))), Image.LANCZOS)
    t = np.array(tick_img)
    static_a = np.zeros((H, W), np.uint8)
    meter_l = np.zeros((H, W), np.uint8)
    meter_a = np.zeros((H, W), np.uint8)
    for k in range(1, n_ticks + 1):
        r, c = (k - 1) // per, (k - 1) % per
        x = int(5 + round((rows - 1 - r) * SLANT * s) + c * PITCH * s + 0.5)
        y = int(5 + r * ROW_PITCH * s + 0.5)
        h_, w_ = t.shape
        sl = (slice(y, y + h_), slice(x, x + w_))
        meter_a[sl] = np.maximum(meter_a[sl], t)
        meter_l[sl] = np.where(t > 0, threshold(k, n), meter_l[sl])   # k-th TICK
        ys, xs = slice(y - 4, y - 4 + h_), slice(x - 4, x - 4 + w_)
        static_a[ys, xs] = np.maximum(static_a[ys, xs], t)
    return static_a, meter_l, meter_a, (rows, per, s, n_ticks, rounds_per)


def write_tag(src_name, out_rel, frames, sprite):
    """One tag holding a readout per magazine size: `frames` is [(N, luminance, alpha)],
    written as bitmap/sequence k. The weapon points its element at sequence 0 (the port's
    own magazine); the patcher's balance moves it to a later one when the balance changes
    how much the weapon holds, because a tick sheet only fits the N it was drawn for."""
    t = bitm_def.build(filepath=os.path.join(COMB, src_name + '.bitmap'))
    d = t.data.tagdata
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    keep_b = copy.deepcopy(bms[1])
    keep_s = copy.deepcopy(seqs[1])
    while len(bms):
        bms.pop()
    while len(seqs):
        seqs.pop()
    blob = b''
    for k, (n, l, a) in enumerate(frames):
        bms.append(copy.deepcopy(keep_b))
        seqs.append(copy.deepcopy(keep_s))
        bm = bms[k]
        bm.width, bm.height, bm.mipmaps = W, H, 0
        bm.pixels_offset = len(blob)
        blob += Image.merge('LA', (Image.fromarray(l), Image.fromarray(a))).tobytes()
        s = seqs[k]
        s.first_bitmap_index, s.bitmap_count = k, 1
        s.sequence_name = 'ammo %d' % n
        if sprite and len(s.sprites.STEPTREE):
            sp = s.sprites.STEPTREE[0]
            sp.bitmap_index = k
            sp.left_side, sp.right_side, sp.top_side, sp.bottom_side = 0.0, BOX_W / W, 0.0, (BOX_H + 14) / H
            # the AR sprite registers at 230 px, 32.5 px (0.4492 x 512, 0.1270 x 256): same pixels here
            sp.registration_point_x, sp.registration_point_y = 0.44921875 * 512 / W, 0.126953125 * 256 / H
    d.processed_pixel_data.data = blob
    t.filepath = os.path.join(TAGS, out_rel + '.bitmap')
    os.makedirs(os.path.dirname(t.filepath), exist_ok=True)
    t.serialize(temp=False, backup=False)
    return t.filepath


def main(*sizes_then_base):
    """ammo_meter.py <N> [<N2> ...] <out tag base> -- sequence k is drawn for size k."""
    sizes = [int(x) for x in sizes_then_base[:-1]]
    out_base = sizes_then_base[-1]
    statics, meters = [], []
    for n in sizes:
        static_a, meter_l, meter_a, info = render(n)
        statics.append((n, static_a, static_a))
        meters.append((n, meter_l, meter_a))
        prev = Image.new('RGB', (W, H * 2 + 8), (40, 60, 90))
        prev.paste(Image.fromarray(static_a).convert('RGB'), (0, 0))
        prev.paste(Image.fromarray(meter_l).convert('RGB'), (0, H + 8), Image.fromarray(meter_a))
        prev.save(os.path.join(HERE, 'h1mp', 'ammo_%d.png' % n))
        print('N=%d rows %d x %d scale %.2f -> %d ticks of %d round(s), '
              'sequence %d, multiplier %d, step %d'
              % ((n,) + info[:3] + (info[3], info[4], sizes.index(n), step(n), plan(n)[2])))
    p1 = write_tag('hud_ammo_alphas', out_base + '_alphas', statics, False)
    p2 = write_tag('hud_ammo_meters', out_base + '_meters', meters, True)
    print('wrote %s, %s' % (p1, p2))


if __name__ == '__main__':
    main(*sys.argv[1:])

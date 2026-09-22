r"""The pixel codec inside a Halo 3 font package, decoded both ways.

`maps\fonts\font_package_*.bin` stores every glyph as a 16-byte header and a packed
payload. The payload is a byte-oriented opcode stream over ARGB4444 pixels, emitted row
by row, left to right, and it ends when `width * height` pixels have been produced --
there is no terminator.

    PIXEL   two bytes, byte0 = A << 4 | R, byte1 = G << 4 | B

    0x00        literal: the next TWO bytes are one pixel
    0x01..0x3F  N fully transparent pixels (N = op)
    0x40..0x7F  N copies of the PREVIOUS pixel (N = op & 0x3F)
    0x80..0xBF  one WHITE pixel whose alpha is level (op >> 3) & 7
    0xC0..0xFF  two WHITE pixels, levels (op >> 3) & 7 and op & 7

A payload that stops early is not truncated: the pixels it never reaches are TRANSPARENT.
Most glyphs end on a blank row, so the encoder simply drops the tail. `previous` starts as
opaque white, which is why a glyph that opens with a white run can begin with a bare
0x40|N. The eight alpha levels are not evenly spaced -- LEVELS below --
so the white shorthand is lossy for odd alpha and the encoder falls back to a literal
whenever a pixel is not white.

Verified on every font package the Editing Kit ships: 73895 of 73895 glyphs decode with
the payload consumed to its last byte and not one pixel over -- Latin, Korean, Japanese,
both Chinese sets and all three icon resolutions.

This was not guessed. `tool windows-font-from-settings` + `tool font-package` build a
package from ordinary bitmap tags, so feeding it images whose pixels are known turns the
encoder into a Rosetta stone; every rule above comes from a probe whose output was
predicted first. See `h3_font_probe.py` for the harness.
"""

LEVELS = (0, 2, 4, 6, 8, 10, 12, 15)          # 3-bit alpha -> 4-bit alpha
WHITE = (15, 15, 15, 15)                       # A, R, G, B
CLEAR = (0, 0, 0, 0)


def unpack_pixel(b0, b1):
    return (b0 >> 4, b0 & 15, b1 >> 4, b1 & 15)


def pack_pixel(p):
    a, r, g, b = p
    return ((a << 4) | r, (g << 4) | b)


def decode(payload, width, height):
    """[(A, R, G, B)] of width*height 4-bit pixels, row major.

    Raises if the stream overshoots the glyph or leaves bytes unread: those invariants
    are what prove the opcode table, so they are checked rather than tolerated. Running
    out of bytes early is legal and pads with transparent.
    """
    want = width * height
    out = []
    prev = WHITE
    i = 0
    n = len(payload)
    while len(out) < want and i < n:
        op = payload[i]
        i += 1
        if op == 0x00:
            if i + 2 > n:
                raise ValueError('truncated literal')
            prev = unpack_pixel(payload[i], payload[i + 1])
            i += 2
            out.append(prev)
        elif op < 0x40:
            out.extend([CLEAR] * op)
            prev = CLEAR
        elif op < 0x80:
            out.extend([prev] * (op & 0x3F))
        elif op < 0xC0:
            prev = (LEVELS[(op >> 3) & 7], 15, 15, 15)
            out.append(prev)
        else:
            out.append((LEVELS[(op >> 3) & 7], 15, 15, 15))
            prev = (LEVELS[op & 7], 15, 15, 15)
            out.append(prev)
    if len(out) > want:
        raise ValueError('overshot to %d pixels, wanted %d' % (len(out), want))
    if i != n:
        raise ValueError('%d bytes left unread' % (n - i))
    out.extend([CLEAR] * (want - len(out)))
    return out


def _white_level(p):
    """The alpha level that encodes this pixel exactly, or None if it needs a literal."""
    a, r, g, b = p
    if (r, g, b) != (15, 15, 15):
        return None
    for k, v in enumerate(LEVELS):
        if v == a:
            return k
    return None


def encode(pixels):
    """A payload that decodes back to `pixels` exactly.

    Only lossless choices are made. Bungie's own encoder additionally snaps near-white
    pixels onto the nearest alpha level; doing that here would make a round trip
    disagree with its input, so it is left to the caller.
    """
    out = bytearray()
    prev = WHITE
    i = 0
    n = len(pixels)
    while n and pixels[n - 1] == CLEAR:      # the tail is implicit
        n -= 1
    while i < n:
        p = pixels[i]
        run = 1
        while i + run < n and pixels[i + run] == p and run < 63:
            run += 1
        if p == CLEAR and run > 1:
            out.append(run)                       # transparent run, no pixel needed
            prev = CLEAR
            i += run
            continue
        if p == prev and run > 1:
            out.append(0x40 | run)
            i += run
            continue
        lv = _white_level(p)
        if lv is not None:
            nxt = _white_level(pixels[i + 1]) if i + 1 < n else None
            if nxt is not None:
                out.append(0xC0 | (lv << 3) | nxt)
                prev = pixels[i + 1]
                i += 2
                continue
            out.append(0x80 | (lv << 3))
            prev = p
            i += 1
            continue
        if p == CLEAR:
            out.append(1)
            prev = CLEAR
            i += 1
            continue
        out.append(0x00)
        out.extend(pack_pixel(p))
        prev = p
        i += 1
    return bytes(out)

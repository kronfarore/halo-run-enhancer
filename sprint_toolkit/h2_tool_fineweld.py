r"""Halo 2's `tool render` WELD (found 2026-11-03, the DMR B1 boot 1: 'the glass on the scope is missing, the
display looks wrong'): the render import welds points closer than clamp(the model's largest bounding-box side
x 1/512, 6.1e-5, 0.000977) world units (tool.exe 0x462421, the settings for connected_geometry_point_welder),
and a triangle whose corners weld together is dropped. A weapon is ~0.35 wu long, so the weld is ~0.0007 wu
(0.07 JMS units): Reach's dense DMR lost 16,286 -> 5,717 triangles (the lens glass, the counter display,
small detail), the Needle Rifle 6,811 -> 5,741, the Reach-sourced SAW 13,836 -> 8,361; Bungie-density meshes
(AR 2,139 -> 2,055) barely notice. Measured: 4x the mesh kept 13,876 -- absolute units, the 1/512 rule.

tool_fineweld.exe = tool.exe with the multiply at 0x462478 (mulss xmm1, [0xce89d8] = 1/512) pointed at the
6.1e-5 floor constant 0xce89cc instead: the weld is the floor for every weapon-sized model. The DMR then keeps
16,290 triangles (all of them). Nothing else in tool reads the changed instruction; tool.exe stays untouched.
A config's geometry `fine_weld: True` makes h2_port_geometry --render use it.

    python h2_tool_fineweld.py          build (or check) F:\...\H2EK\tool_fineweld.exe
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_tagref  # noqa: E402

H2EK = h2_tagref.H2EK
EXE = os.path.join(H2EK, 'tool_fineweld.exe')
VA = 0x46247c                                     # the disp32 of mulss xmm1, dword ptr [0xce89d8]
OLD, NEW = struct.pack('<I', 0xce89d8), struct.pack('<I', 0xce89cc)


def file_offset(b, va):
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    opt = struct.unpack_from('<H', b, pe + 20)[0]
    base = struct.unpack_from('<I', b, pe + 24 + 28)[0]
    _vs, sva, _rs, sra = struct.unpack_from('<IIII', b, pe + 24 + opt + 8)      # .text
    return va - base - sva + sra


def build():
    b = bytearray(open(os.path.join(H2EK, 'tool.exe'), 'rb').read())
    o = file_offset(b, VA)
    if bytes(b[o - 4:o]) != b'\xf3\x0f\x59\x0d' or bytes(b[o:o + 4]) != OLD:
        raise SystemExit('tool.exe is not the build this patch was made for (bytes at 0x%x: %s)'
                         % (VA, bytes(b[o - 4:o + 4]).hex()))
    b[o:o + 4] = NEW
    if os.path.exists(EXE) and open(EXE, 'rb').read() == bytes(b):
        print('up to date:', EXE)
        return EXE
    open(EXE, 'wb').write(b)
    print('wrote', EXE)
    return EXE


if __name__ == '__main__':
    build()

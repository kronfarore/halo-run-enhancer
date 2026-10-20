r"""The Halo 2 SAW's step, kept by name: `python h2_saw_glyph.py [args]` == `python h2_port_glyph.py saw [args]`.

The SAW's constants live in ports_h2/saw.py and the code in h2_port_glyph.py since the Halo 2 port
phase 0 (H2_PORT_PLAN.md 0.2, 2026-10-20; proved byte-identical against this script's last full
version, git history before that date). Read that tool's docstring for the step's notes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2_port_glyph  # noqa: E402

if __name__ == '__main__':
    h2_port_glyph.main(['saw'] + sys.argv[1:])

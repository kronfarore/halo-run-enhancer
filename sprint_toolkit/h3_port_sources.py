r"""Where a Halo 3 weapon's port SOURCES live (read-only):

  chud <name>          every bitmap + sequence a Halo 3 chud_definition draws (H3EK export):
                       the RETICLE (`hud_reticles` #n -> the port's `reticle`) and the AMMO
                       icons (`ballistic_meters` #n -> `ammo_meter` art). The Mauler:
                       ui\chud\excavator = hud_reticles 12, ballistic_meters 13 (its pips)
  sounds <text> ...    the folders of Halo 3's FMOD bank (sfx.fsb .info) whose path holds
                       any of the texts, with their permutation counts -- the names
                       h1_port_sounds' configs list (the Mauler: data\sound\weapons\
                       excavator\..., the magnum's ammo / dry fire / drop it reuses)

    python h3_port_sources.py chud excavator
    python h3_port_sources.py sounds excavator magnum\magnum_
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def chud(name):
    import h3_weapon_values as h
    x = h.export('ui\\chud\\%s.chud_definition' % name)
    if x is None:
        raise SystemExit('no ui\\chud\\%s in H3EK' % name)
    seen = {}
    for m in re.finditer(r'<field name="bitmap" value="([^",]+),bitm" type="tag reference"/>\s*'
                         r'<field name="sequence index" value="(\d+)"', x):
        k = (m.group(1), int(m.group(2)))
        seen[k] = seen.get(k, 0) + 1
    for (bm, seq), n in sorted(seen.items()):
        print('%-50s sequence %-3d x%d' % (bm, seq, n))


def sounds(texts):
    import h1_port_sounds
    idx = h1_port_sounds.h3_index()
    base = 'data\\sound\\weapons\\'
    for k in sorted(idx):
        if k.startswith(base) and any(t.lower() in k for t in texts):
            print('%-80s %d' % (k, len(idx[k])))


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('chud', 'sounds'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'chud':
        chud(sys.argv[2])
    else:
        sounds(sys.argv[2:])

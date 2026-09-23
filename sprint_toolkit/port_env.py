r"""Put the Reclaimer stack on sys.path, for the tools that read or write Halo 1 tags.

Halo 1's gbxmodel, bitmap and weapon tags are read and written through Reclaimer
(Mozzarilla's library), which needs no compiler: the packages are pure Python, so the
sdists unpack and import as they are. They are VENDORED under `pylibs/` rather than
pip-installed, for two reasons -- the exact versions matter, and the whole port pipeline
once lived in a session scratchpad and was very nearly lost.

    reclaimer 2.11.2      gbxmodel/bitmap/weapon defs, JMS read+write, extract_model
    supyr_struct 1.5.4    the structure engine underneath it
    arbytmap 1.1.2        bitmap pixel conversion
    binilla 1.3.8         imported by reclaimer's defs (wheel, unpacked)

Import this before anything from `reclaimer`:

    import port_env  # noqa
    from reclaimer.hek.defs.mod2 import mod2_def
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYLIBS = os.path.join(HERE, 'pylibs')
PACKAGES = ('reclaimer-2.11.2', 'supyr_struct-1.5.4', 'arbytmap-1.1.2', 'binilla_whl')

for _d in PACKAGES:
    _p = os.path.join(PYLIBS, _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

missing = [d for d in PACKAGES if not os.path.isdir(os.path.join(PYLIBS, d))]
if missing:
    raise ImportError(
        'the vendored Reclaimer stack is incomplete: %s missing from %s'
        % (', '.join(missing), PYLIBS))

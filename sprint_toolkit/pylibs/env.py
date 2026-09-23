import os, sys
_B = os.path.dirname(os.path.abspath(__file__))
for d in ('reclaimer-2.11.2', 'supyr_struct-1.5.4', 'arbytmap-1.1.2', 'binilla_whl'):
    sys.path.insert(0, os.path.join(_B, d))

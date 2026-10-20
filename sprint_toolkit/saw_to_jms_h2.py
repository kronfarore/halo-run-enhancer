r"""H4 SAW geometry -> Halo 2 JMS, kept by name: `python saw_to_jms_h2.py [dump] [scale]
[--fp-sub=NAME --fp-nudge=x,y,z]` now runs h2_port_geometry.py for the SAW's config (ports_h2/saw.py
holds the dump, the part map, the nudges -- the Dervish model's (0, 0, -0.75) included -- and every
other constant this script had; H2_PORT_PLAN.md 0.2: all three JMS regenerate byte-identical).
A --fp-sub run builds only that model.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h2_port_geometry  # noqa: E402

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    argv = ['saw']
    if args:
        argv.append('--dump=' + args[0])
    if len(args) > 1:
        argv.append(args[1])
    if opts.get('fp-sub'):
        argv.append('--only=' + opts['fp-sub'])
    h2_port_geometry.main(argv)

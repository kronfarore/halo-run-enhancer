r"""Superseded by saw_port_sounds.py (all three Halo 3-family kits); kept so the Reach
commands keep working:  python reach_saw_sounds.py --write  ==  saw_port_sounds.py --game reach --write
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saw_port_sounds                                              # noqa: E402

if __name__ == '__main__':
    if '--game' not in sys.argv:
        sys.argv[1:1] = ['--game', 'reach']
    saw_port_sounds.main()

r"""Print a Reach tag's non-default fields (step 4a / 4b reading of a Reach source; used for the
Grenade Launcher, wave B4): exports the tag with reach_tags.export_xml and lists each field that
is not zero / empty / none, with block elements as [n] headers. Read-only.

    python reach_tag_fields.py objects\weapons\support_low\grenade_launcher\projectiles\grenade.projectile
    python reach_tag_fields.py <tag> <tag> ...          # several, one after another
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach_tags  # noqa: E402

DEFAULTS = (None, '', ' ', '0', '0,0', '0,0,0', 'none', 'NONE')


def dump(rel):
    p = reach_tags.export_xml('reach:' + rel)
    print('=====', rel)
    for line in open(p, encoding='utf-8', errors='replace'):
        m = re.search(r'<(field|element)[^>]*name="([^"]*)"(?: value="([^"]*)")?', line)
        if not m:
            continue
        kind, name, val = m.groups()
        if kind == 'element':
            print('  [%s]' % name)
        elif val not in DEFAULTS:
            print('   ', name, '=', val)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for rel in sys.argv[1:]:
        dump(rel)

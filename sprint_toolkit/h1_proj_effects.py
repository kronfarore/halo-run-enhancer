r"""Every effect / sound a Halo 1 projectile names, and the sound parts inside those effects, read-only (the Railgun,
C7 close-out 2026-10-16; the Grenade Launcher's note: port_sound_refs does not read a projectile's responses --
found by hand). Lists the flyby / detonation-started sounds, the detonation effect, the attached / impact damage,
each material response's effect / detonation effect / potential effect, and the attachments; a sound part not under
the port's own sound folder is a BORROW to decide (own copy, KEEP with the user, or drop).

    python h1_proj_effects.py "weapons\railgun\slug" [--own sound\weapons\railgun_port]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h1_role_compare as R  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.effe import effe_def  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('projectile')
    ap.add_argument('--own', default='', help='the port\'s own sound folder: other sound parts are marked BORROW')
    a = ap.parse_args()
    p = R.load(proj_def, a.projectile, '.projectile')
    pa, refs = p.proj_attrs, {}
    for k in ('detonation_started', 'flyby_sound', 'attached_detonation_damage', 'impact_damage'):
        v = getattr(pa.physics, k, None)
        if v is not None and v.filepath:
            refs.setdefault(v.filepath, set()).add('physics.' + k)
    if pa.detonation.effect.filepath:
        refs.setdefault(pa.detonation.effect.filepath, set()).add('detonation.effect')
    for i, m in enumerate(pa.material_responses.STEPTREE):
        for k in ('effect', 'detonation_effect'):
            v = getattr(m, k, None)
            if v is not None and v.filepath:
                refs.setdefault(v.filepath, set()).add('response ' + k)
        if m.potential_response.effect.filepath:
            refs.setdefault(m.potential_response.effect.filepath, set()).add('response potential')
    for x in p.obje_attrs.attachments.STEPTREE:
        refs.setdefault(x.type.filepath, set()).add('attachment ' + x.type.tag_class.enum_name)
    own = a.own.lower()
    for path, where in sorted(refs.items()):
        print('%-60s %s' % (path, ', '.join(sorted(where))))
        try:
            e = R.load(effe_def, path, '.effect')
        except Exception:
            e = None
        if e is None:
            continue
        for ev in e.events.STEPTREE:
            for part in ev.parts.STEPTREE:
                if part.type.tag_class.enum_name == 'sound':
                    tag = 'OWN   ' if own and part.type.filepath.lower().startswith(own) else 'BORROW' if own else ''
                    print('      %s sound part %s' % (tag, part.type.filepath))


if __name__ == '__main__':
    main()

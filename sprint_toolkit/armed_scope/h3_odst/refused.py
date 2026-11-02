import re
cur = None; f = None
for line in open('gate.txt'):
    if line.startswith('====='):
        f = line.split()[1]; print('\n', f)
    elif line.startswith('# '):
        cur = line.split()[1]
    elif line.startswith('  combat |') or line.startswith('  crouch |') or line.startswith('  flee |') or line.startswith('  patrol |'):
        mo = line.split()[0]
        if not any(w in cur for w in ('brute\\brute', 'grunt', 'jackal', 'bugger', 'elite\\elite', 'marine\\marine', 'floodcombat', 'engineer', 'odst', 'hunter\\')) or 'chieftain' in cur:
            continue
        d = dict(x.rsplit(':', 1) for x in line.split('|', 1)[1].split())
        no = [k for k, v in d.items() if v == '-']
        fb = [k for k, v in d.items() if v == 'f']
        print('  %-52s %-7s refused %2d/%d %s %s' % (cur[19:], mo, len(no), len(d), ' '.join(sorted(no)) if len(no) < 16 else '(most)', ('anyclass:%d' % len(fb)) if fb else ''))

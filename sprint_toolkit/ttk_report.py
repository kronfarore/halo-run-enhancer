r"""Combine the per-game time-to-kill JSONs (ttk_<game>.py -> reports/ttk/*.json) into
reports/ttk_legendary.md: one table per game and a cross-game summary (ttk_common.py has
the method).

    python ttk_report.py
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'reports', 'ttk')
OUT = os.path.join(HERE, 'reports', 'ttk_legendary.md')
ORDER = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
#: readable names for weapon labels a collector left as tag names
NAMES = {'storm_assault_carbine': 'Storm Rifle (AI)',
         'storm_forerunner_smg_npc': 'Suppressor (AI)'}
CAVEATS = [
    'All times assume EVERY shot hits and are therefore lower bounds, the enemy columns '
    'most of all (AI misses are what makes Legendary survivable). "Paced" = the AI fires '
    'in its own bursts with its burst separation between them; "held" = it never stops.',
    "AI fire comes from the parent `ai\\generic` firing patterns (H2+: two patterns blended "
    "by the AI's accuracy, which climbs over the first seconds -- the tables use full "
    "accuracy; ramp-start numbers are in each row). AI trigger rate is capped at the "
    "weapon's own top rate (assumption, all games).",
    "PLASMA HEAT drains WHILE firing in every game (user, 2026-10-13: Halo 3 and Halo 4 "
    "both visibly drain while the trigger is held; the earlier 'cools only when not firing' "
    "Focus Rifle reading was wrong). H1 was measured with the Plasma Repeater port probe; "
    "H2 assumes the same; Reach uses the Plasma Repeater's measured heat curve (rate falls "
    "15 -> 3/s). Halo 4's Storm Rifle first overheats on about the 27th bolt.",
    "Reload pauses come from the tag's reload time, or the first-person reload animation "
    'where the tag has none (H3 AR/BR, Reach, H4). Damage is the point-blank upper bound '
    '(no fall-off with range). Default AI weapons come from scenario squads (census where '
    'possible); H2 assumes Elite = Plasma Rifle, Brute = Brute Plasma Rifle.',
]


def sec(v):
    return '-' if v is None else '%.2f s' % v


def main():
    data = {}
    for p in glob.glob(os.path.join(SRC, 'ttk_*.json')):
        d = json.load(open(p, encoding='utf-8'))
        for r in d['rows']:
            r['weapon'] = NAMES.get(r['weapon'], r['weapon'])
        data[d['game']] = d
    lines = ['# Time to kill on Legendary, all six games', '',
             'Every shot hits, body shots only, full shield and body, no recharge. '
             'Damage multipliers from the game data (H2+: every matching damage-table row '
             'multiplied; H1: the damage effect\'s per-material modifiers) and the '
             'Legendary difficulty dials. Method: `sprint_toolkit/ttk_common.py`.', '']
    lines += ['- ' + c for c in CAVEATS]
    lines += ['', '## Summary', '',
             '| game | you kill an Elite | you kill a Brute / Knight | Elite kills you (paced) '
             '| Brute / Knight kills you (paced) |', '|---|---|---|---|---|']
    for g in ORDER:
        d = data.get(g)
        if not d:
            lines.append('| %s | (not measured) | | | |' % g)
            continue
        rows = d['rows']

        def pk(target):
            hits = [r for r in rows if r['direction'] == 'player->enemy'
                    and target in r['target'] and r.get('seconds') is not None]
            return ', '.join('%s %s' % (r['weapon'], sec(r['seconds'])) for r in hits) or '-'

        def ek(attacker):
            hits = [r for r in rows if r['direction'] == 'enemy->player'
                    and attacker in r['attacker']]
            return ', '.join('%s %s (held %s)' % (r['weapon'], sec(r.get('seconds_paced')),
                                                  sec(r.get('seconds'))) for r in hits) or '-'
        other = 'Knight' if g == 'Halo 4' else 'Brute'
        lines.append('| %s | %s | %s | %s | %s |' % (g, pk('Elite'), pk(other), ek('Elite'),
                                                     ek(other)))
    for g in ORDER:
        d = data.get(g)
        if not d:
            continue
        lines += ['', '## %s' % g, '',
                  '| direction | attacker | target | weapon | hits | time | paced | flags |',
                  '|---|---|---|---|---|---|---|---|']
        for r in d['rows']:
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (
                r['direction'], r['attacker'], r['target'], r['weapon'], r.get('shots', '-'),
                sec(r.get('seconds')), sec(r.get('seconds_paced')) if
                r['direction'] == 'enemy->player' else '', '; '.join(r.get('flags') or [])))
        if d.get('notes'):
            lines += [''] + ['- ' + n for n in d['notes']]
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote %s (%d games)' % (OUT, len(data)))


if __name__ == '__main__':
    main()

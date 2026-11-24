r"""The FIRE-RULE damage correction of a port's Balanced rows (user 2026-11-24: 'Apply them all').

Every game fires by the 30 Hz reset rule (reports/rof_test.jsonl): a shot every ceil(30 / rate)
ticks, a fire recovery rounded UP to ticks pacing only a one-shot-a-fire weapon. The ratio rule
derived a port's Balanced numbers field by field on TAG values, so what its guns really FIRE can
drift from what the rule meant. rof_balance_check.py measures that drift per port as

    k = fired(source) x PRODUCT fired(yardstick, to) / fired(yardstick, from)  /  fired(port)

and the port's config records the correction its Balanced damage takes:

    'fire_rule_damage': {'k': 1.125, 'tags': [<the damage effects its PROJECTILE deals>],
                         'why': 'rof_balance_check 2026-11-24: ...'}

Only the projectile's own damage scales (Damage Lower Bound / Upper Bound / Upper Bound Max of the
named jpt! tags): melee, a supercombine, a charged blast are not paced by the rate. The catalog
builders (make_port_catalog_h1_ports.py, make_port_catalog.py for the Halo 1 SAW,
make_port_catalog_h2.py) call apply() on the rows they build, so a rebuild reproduces it, and
each scaled row carries the reason in its note. rof_balance_check reads FIELD back to report
the port as corrected.

STEP FOR EVERY NEW PORT (PORTING.md "Balance"): after step 4a's Balanced rows exist, run
`python rof_balance_check.py`; a port flagged |k - 1| > 5% gets its k here.
"""

FIELD = 'fire_rule_damage'
DAMAGE_FIELDS = ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')


def apply(rows, spec, digits=4):
    """Scale the Balanced damage rows of `spec['tags']` by `spec['k']` in place; returns the
    number of rows scaled. A row already carrying the note is not scaled twice."""
    if not spec:
        return 0
    k = float(spec['k'])
    tags = {t.lower() for t in spec['tags']}
    tag = 'fire rule x%g' % k
    n = 0
    for r in rows:
        if r.get('class') != 'jpt!' or str(r.get('tag', '')).lower() not in tags:
            continue
        if r.get('field') not in DAMAGE_FIELDS or not isinstance(r.get('value'), (int, float)):
            continue
        if tag in str(r.get('note') or ''):
            continue
        r['value'] = round(float(r['value']) * k, digits)
        why = '%s (%s)' % (tag, spec.get('why') or 'rof_balance_check')
        r['note'] = (r['note'] + '; ' + why) if r.get('note') else why
        n += 1
    if not n:
        raise SystemExit('fire_rule_damage: no damage row of %s in the Balanced rows' % sorted(tags))
    return n

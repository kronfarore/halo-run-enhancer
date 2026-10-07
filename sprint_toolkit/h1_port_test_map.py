r"""A Halo 1 TEST copy of one level with a port in the player's hands from the start,
optionally the enemies swapped, staged into MCC -- generic per weapon (H1_PORT_PLAN.md
phase 0, deliverable 4). Replaces the SAW-only saw_scenario.py for new ports.

  1. KIT, temporarily (the scenario is copied first and ALWAYS put back):
     * the weapon in the level's weapons palette + one resident-only placement (a copy of
       the SAW's, `not placed automatically`) if the level does not carry it yet -- what
       h1_pickable_weapons.edit_palettes does for good;
     * every SPAWN profile's primary weapon = the port (rounds: --rounds, the config's
       test.rounds, else the weapon tag's first magazine full); the secondary is kept.
       Which profiles are spawns is NOT derivable from the tag: a10's bridge0/bridge1 and
       weapon_insert drive mechanisms (saw_scenario.py's finding), every level's
       sprint_profile is the sprint mod's invisible weapon. SKIP below lists them; a level
       whose profiles are not in KNOWN is refused;
     * the enemy actor variants asked for, appended to the Actor Palette when missing.
     Built with `h1_rebuild_all.py --maps <level> --no-ship`, copied to
     HCEEK\maps\port_test\<level>.map, the scenario restored, and (unless --keep-kit-map)
     the normal level rebuilt so HCEEK\maps\<level>.map is the real one again.
  2. MAP COPY: enemies swapped (h1_enemy_test_map.swap_actors: every Grunt / Elite palette
     entry -> the chosen variant), optional --god shield.
  3. --stage: the LIVE halo1\maps\<level>.map is backed up first to
     E:\HaloBackups\h1_port_test\<level>.map (a backup that is itself a staged test copy
     is never taken -- the record in stage.json says what was staged), then the test copy
     goes live. `--restore <level>` puts the backup back.

The defaults come from the weapon's config (ports_h1/<key>.py, section 'test':
{'level', 'rounds', 'grunt', 'elite', 'god'}); flags override them.

    python h1_port_test_map.py sentinel_beam                    # build the copy only
    python h1_port_test_map.py smg --level a30 --elite "characters\elite\elite" --stage
    python h1_port_test_map.py --restore a30
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import port_env  # noqa: E402,F401
import paths  # noqa: E402
import ports_h1  # noqa: E402
import h1_loosetag as L  # noqa: E402
import h1_enemy_test_map as E  # noqa: E402

HCEEK = paths.HCEEK
TAGS = os.path.join(HCEEK, 'tags')
LIVE = os.path.join(paths.MCC, 'halo1', 'maps')
BACKUPS = os.path.join('E:' + os.sep, 'HaloBackups', 'h1_port_test')
RECORD = os.path.join(BACKUPS, 'stage.json')
SAW = r'weapons\saw\saw'

# profiles that are NOT player spawns, per level (every other profile of a KNOWN level is)
SKIP = {'a10': ('bridge0_profile', 'bridge1_profile', 'weapon_insert')}
SKIP_ALL = ('sprint_profile',)
KNOWN = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')


def sha1(p):
    return hashlib.sha1(open(p, 'rb').read()).hexdigest()


def weapon_of(key, p):
    w = (p.get('pickable') or {}).get('weapon')
    if w:
        return w
    d = p['reservations']['weapon_dir']
    return d + '\\' + d.rsplit('\\', 1)[-1]


def full_magazine(weapon):
    from reclaimer.hek.defs.weap import weap_def
    a = weap_def.build(filepath=os.path.join(TAGS, weapon + '.weapon')).data.tagdata.weap_attrs
    mags = a.magazines.STEPTREE
    if not len(mags):
        return 0, 0
    return mags[0].rounds_loaded_maximum, mags[0].rounds_total_maximum


def edit_kit(level, weapon, rounds, actors):
    """The scenario edits of step 1 (the caller restores the file)."""
    from reclaimer.hek.defs.scnr import scnr_def
    sp = E.scenario_path(level)
    t = scnr_def.build(filepath=sp)
    d = t.data.tagdata
    pal = d.weapons_palette.STEPTREE
    names = [e.name.filepath.lower() for e in pal]
    if weapon.lower() in names:
        idx = names.index(weapon.lower())
    else:
        pal.append()
        pal[-1].name.filepath = weapon
        idx = len(pal) - 1
    places = d.weapons.STEPTREE
    if not any(x.type == idx for x in places):
        saw = names.index(SAW)
        src = [x for x in places if x.type == saw and x.not_placed.automatically]
        if not src:
            raise SystemExit('%s: no resident-only SAW placement to copy' % level)
        places.append(copy.deepcopy(src[0]))
        x = places[len(places) - 1]
        x.type = idx
        x.rounds_left = x.rounds_loaded = 0
        print('kit: %s palette #%d + resident-only placement (temporary)' % (weapon, idx))
    else:
        print('kit: %s already resident (palette #%d)' % (weapon, idx))
    skip = SKIP_ALL + SKIP.get(level, ())
    armed = []
    for p in d.player_starting_profiles.STEPTREE:
        if p.name in skip:
            continue
        p.primary_weapon.filepath = weapon
        p.primary_rounds_loaded, p.primary_rounds_total = rounds
        armed.append(p.name or '(unnamed)')
    print('kit: %d spawn profile(s) armed, %d/%d rounds: %s'
          % (len(armed), rounds[0], rounds[1], ', '.join(armed)))
    t.filepath = sp
    t.serialize(temp=False, backup=False)
    if actors:                                   # raw insert, as h1_enemy_test_map does
        data = bytearray(open(sp, 'rb').read())
        have = L.read_block_paths(data, paths.SCNR_XML, E.ACTOR_PALETTE)
        added = [a for a in actors if a not in have]
        for a in added:
            L.insert_block_element(data, paths.SCNR_XML, E.ACTOR_PALETTE, L._tagref(b'actv', a), a)
        open(sp, 'wb').write(data)
        print('kit: actor palette + %s' % (added or 'nothing'))


def build_copy(level, weapon, rounds, actors, keep_kit_map):
    sp = E.scenario_path(level)
    keep = sp + '.before_porttest'
    shutil.copy2(sp, keep)
    try:
        edit_kit(level, weapon, rounds, actors)
        E.build(level)
        out_dir = os.path.join(HCEEK, 'maps', 'port_test')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, level + '.map')
        shutil.copy2(os.path.join(HCEEK, 'maps', level + '.map'), out)
    finally:
        shutil.copy2(keep, sp)
        os.remove(keep)
    print('kit scenario restored')
    if not keep_kit_map:
        print('rebuilding the normal %s (HCEEK\\maps)' % level)
        E.build(level)
    return out


def load_record():
    try:
        return json.load(open(RECORD, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def stage(level, test_map, label):
    live = os.path.join(LIVE, level + '.map')
    os.makedirs(BACKUPS, exist_ok=True)
    rec = load_record()
    bak = os.path.join(BACKUPS, level + '.map')
    staged = rec.get(level, {}).get('staged_sha1')
    if os.path.exists(live) and sha1(live) != staged:
        if os.path.exists(bak):                   # keep the older one too, never lose a live map
            os.replace(bak, bak + '.' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(live, bak)
        print('live %s backed up -> %s' % (live, bak))
    elif os.path.exists(live):
        print('live %s is the previous test copy; backup %s kept' % (live, bak))
    shutil.copy2(test_map, live)
    rec[level] = {'staged_sha1': sha1(live), 'what': label,
                  'when': datetime.datetime.now().isoformat(timespec='seconds'),
                  'backup': bak}
    json.dump(rec, open(RECORD, 'w', encoding='utf-8'), indent=1)
    print('STAGED %s -> %s  (restore: python h1_port_test_map.py --restore %s)' % (label, live, level))


def restore(level):
    bak = os.path.join(BACKUPS, level + '.map')
    if not os.path.exists(bak):
        raise SystemExit('no backup %s' % bak)
    shutil.copy2(bak, os.path.join(LIVE, level + '.map'))
    rec = load_record()
    rec.pop(level, None)
    json.dump(rec, open(RECORD, 'w', encoding='utf-8'), indent=1)
    print('restored %s from %s' % (level, bak))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('weapon', nargs='?', help='port config key (ports_h1/<key>.py)')
    ap.add_argument('--level')
    ap.add_argument('--rounds', help='loaded,total')
    ap.add_argument('--grunt', help='actor variant every Grunt becomes')
    ap.add_argument('--elite', help='actor variant every Elite becomes')
    ap.add_argument('--god', action='store_true', help='unbreakable player shield')
    ap.add_argument('--stage', action='store_true', help='back up the live map, put the copy live')
    ap.add_argument('--keep-kit-map', action='store_true',
                    help='skip the rebuild of the normal level afterwards')
    ap.add_argument('--restore', metavar='LEVEL')
    a = ap.parse_args()
    if a.restore:
        return restore(a.restore)
    if not a.weapon:
        ap.error('a weapon config key, or --restore LEVEL')
    p = ports_h1.load(a.weapon)
    cfg = p.get('test') or {}
    level = a.level or cfg.get('level') or 'a30'
    if level not in KNOWN:
        raise SystemExit('%s: which starting profiles are spawns is not recorded (SKIP/KNOWN)' % level)
    weapon = weapon_of(a.weapon, p)
    if not os.path.exists(os.path.join(TAGS, weapon + '.weapon')):
        raise SystemExit('no weapon tag %s yet' % weapon)
    if a.rounds:
        rounds = tuple(int(x) for x in a.rounds.split(','))
    else:
        rounds = tuple(cfg['rounds']) if cfg.get('rounds') else full_magazine(weapon)
    want = {'grunt': a.grunt or cfg.get('grunt'), 'elite': a.elite or cfg.get('elite')}
    actors = [v for v in want.values() if v]
    out = build_copy(level, weapon, rounds, actors, a.keep_kit_map)
    if actors or a.god or cfg.get('god'):
        import halo_patch
        m = halo_patch.open_map(out, 'Halo 1')
        if actors:
            E.swap_actors(m, want)
        if a.god or cfg.get('god'):
            E.god_shield(m)
        open(out, 'wb').write(bytes(m.data))
    print('wrote %s' % out)
    if a.stage:
        stage(level, out, '%s on %s%s' % (p['name'], level,
                                          ' enemies %s' % actors if actors else ''))


if __name__ == '__main__':
    main()

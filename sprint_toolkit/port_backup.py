"""Back up the weapon-port work to F:, separately from the map baselines on E:.

What a port actually consists of is spread over three places, and losing any one of them
means rebuilding it from scratch:
  * the EK source tags and data the weapon is built from (its own tags, plus the SHARED
    tags a port had to edit -- the HUD message-icon sheet is the dangerous one, because
    tool rewrites it in place and a fresh EK install would silently lose the SAW's icon),
  * the built cache file, which is the only artifact co-op partners can be given, and
  * the build scripts and the catalog the patcher reads.

    python port_backup.py --game h2 [--label saw-h2] [--no-maps]

`--game` picks which port is backed up; `--no-maps` skips the cache files, which are
the slow part and are only worth keeping when a built map exists.
"""
import argparse, datetime, filecmp, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
F = 'F:' + os.sep
HCEEK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
H2EK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
H3EK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
E_BACKUPS = os.path.join('E:' + os.sep, 'HaloBackups')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection')
ROOT = os.path.join(F, 'HaloPortBackups')
B = os.sep

# (source, destination inside the backup, is_dir)
TREES = [
    (os.path.join(HCEEK, 'tags', 'weapons', 'saw'), 'tags/weapons/saw', True),
    (os.path.join(HCEEK, 'data', 'weapons', 'saw'), 'data/weapons/saw', True),
]
# shared tags a port EDITS IN PLACE -- these are the ones a reinstall quietly reverts
SHARED = [
    (os.path.join(HCEEK, 'tags', 'ui', 'hud', 'bitmaps', 'combined', 'hud_msg_icons.bitmap'),
     'shared/hud_msg_icons.bitmap'),
    (os.path.join(HERE, 'hud_msg_icons.bitmap.stock'), 'shared/hud_msg_icons.bitmap.stock'),
]
MAPS = [
    (os.path.join(HCEEK, 'maps', 'a10.map'), 'maps/a10.map'),
]
FILES = [
    (os.path.join(TOOL, 'weapon_ports_catalog.json'), 'catalog/weapon_ports_catalog.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_Halo1.json'), 'catalog/balance_SAW_Halo4_to_Halo1.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_Halo3.json'), 'catalog/balance_SAW_Halo4_to_Halo3.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_Halo3_mgvel.json'), 'catalog/balance_SAW_Halo4_to_Halo3_mgvel.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_Halo2.json'), 'catalog/balance_SAW_Halo4_to_Halo2.json'),
]
SCRIPTS = ('saw_build.py', 'saw_to_jms.py', 'saw_shaders.py', 'saw_weapon.py', 'saw_anims.py',
           'saw_port_values.py', 'saw_scenario.py', 'ammo_meter.py', 'make_icon.py',
           'add_msg_icon.py', 'h4_bitmap.py', 'h4_rm.py', 'balance_compare.py',
           'balance_port.py', 'make_port_catalog.py', 'tagvals.py', 'ammo_pickups_scan.py',
           'port_backup.py', 'port_families.json', 'check_families.py',
           'saw_h3_bench.py', 'h3tag.py', 'h3_make_saw.py',
           'h3_weapon_census.py', 'h3_tagtable_probe.py', 'h3_install_saw.py',
           'h3_apply_saw_numbers.py', 'h3_saw_tag_numbers.py', 'make_port_catalog_h3.py', 'h3_verify_magazine.py', 'saw_to_jms_h3.py', 'h3_saw_wire_model.py', 'h3_saw_textures.py',
           'h3_saw_world_model.py', 'h3_saw_world_revert.py',
           'h1_weapon_ring.py', 'h1_b40_survey.py', 'h3_saw_fix_region.py', 'h3_chunk_check.py', 'jms_add_colour.py')


# --- per game -------------------------------------------------------------------------
# Halo 1's lists are the originals, unchanged. Halo 2's port is spread wider: it owns tags
# under two character folders as well as its own, it creates five HUD bitmaps in Bungie's
# own folders, and it EDITS EIGHT FONTS IN PLACE -- a fresh H2EK would silently take the
# SAW's pickup glyph back out, which is the same trap Halo 1's message-icon sheet is.
SAW2 = os.path.join('objects', 'weapons', 'rifle', 'saw')
FP2 = os.path.join('fp', 'weapons', 'rifle', 'fp_saw')
HUD2 = os.path.join('ui', 'hud', 'bitmaps', 'new_hud')

H2_TREES = [
    (os.path.join(H2EK, 'tags', SAW2), 'tags/objects/weapons/rifle/saw', True),
    (os.path.join(H2EK, 'data', SAW2), 'data/objects/weapons/rifle/saw', True),
    (os.path.join(H2EK, 'tags', 'objects', 'characters', 'masterchief', FP2),
     'tags/objects/characters/masterchief/fp_saw', True),
    (os.path.join(H2EK, 'tags', 'objects', 'characters', 'dervish', FP2),
     'tags/objects/characters/dervish/fp_saw', True),
    (os.path.join(H2EK, 'h2_fonts'), 'shared/h2_fonts', True),
    (os.path.join(E_BACKUPS, 'h2_fonts'), 'shared/h2_fonts.stock', True),
]
H2_SHARED = [
    (os.path.join(H2EK, 'tags', 'ui', 'hud', 'saw.new_hud_definition'),
     'tags/ui/hud/saw.new_hud_definition'),
    (os.path.join(H2EK, 'tags', HUD2, 'meters', 'saw_meter.bitmap'),
     'tags/ui/hud/saw_meter.bitmap'),
    (os.path.join(H2EK, 'tags', HUD2, 'backgrounds', 'saw_bkd.bitmap'),
     'tags/ui/hud/saw_bkd.bitmap'),
    (os.path.join(H2EK, 'tags', HUD2, 'crosshairs', 'saw_reticle.bitmap'),
     'tags/ui/hud/saw_reticle.bitmap'),
    (os.path.join(H2EK, 'tags', HUD2, 'saw_backpack.bitmap'),
     'tags/ui/hud/saw_backpack.bitmap'),
    (os.path.join(H2EK, 'tags', HUD2, 'scope_masks', 'saw_blank.bitmap'),
     'tags/ui/hud/saw_blank.bitmap'),
    (os.path.join(H2EK, 'data', HUD2, 'meters', 'saw_meter.tif'),
     'data/ui/hud/saw_meter.tif'),
    (os.path.join(H2EK, 'data', HUD2, 'backgrounds', 'saw_bkd.tif'),
     'data/ui/hud/saw_bkd.tif'),
    (os.path.join(H2EK, 'data', HUD2, 'crosshairs', 'saw_reticle.tif'),
     'data/ui/hud/saw_reticle.tif'),
    (os.path.join(H2EK, 'data', HUD2, 'saw_backpack.tif'), 'data/ui/hud/saw_backpack.tif'),
    # the H4 render dump the geometry is built from: re-exportable, but it took finding
    # once and it lived in %TEMP% until it nearly did not exist at all
    (os.path.join(H3EK, 'storm_lmg_rm.xml'), 'source/storm_lmg_rm.xml'),
]
H2_FILES = [
    (os.path.join(TOOL, 'weapon_ports_catalog.json'), 'catalog/weapon_ports_catalog.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_Halo2.json'),
     'catalog/balance_SAW_Halo4_to_Halo2.json'),
    (os.path.join(HERE, 'PORTING.md'), 'catalog/PORTING.md'),
]
H2_SCRIPTS = ('saw_to_jms_h2.py', 'h2_jms.py', 'h2_jms_preview.py', 'h2_tagref.py',
              'h2_tagfield.py', 'h2_loosetag.py', 'h2_batch.py',
              'h2_saw_textures.py', 'h2_saw_weapon.py', 'h2_saw_numbers.py',
              'h2_saw_collision.py', 'h2_saw_meter.py', 'h2_saw_hud_plate.py',
              'h2_saw_reticle.py', 'h2_saw_scope.py', 'h2_saw_glyph.py',
              'h2_saw_messages.py', 'h2_saw_animations.py', 'h2_saw_place.py',
              'h2_anim.py', 'h2_anim_retime.py', 'h2_font.py', 'h2_font_add.py',
              'h4_bitmap.py', 'h4_rm.py', 'h3_weapon_glyph.py',
              'make_port_catalog_h2.py', 'port_backup.py', 'PORTING.md')

PROFILES = {
    'h1': {'trees': TREES, 'shared': SHARED, 'files': FILES, 'maps': MAPS,
           'scripts': SCRIPTS, 'label': 'saw-h1'},
    'h2': {'trees': H2_TREES, 'shared': H2_SHARED, 'files': H2_FILES, 'maps': [],
           'scripts': H2_SCRIPTS, 'label': 'saw-h2'},
}


def copy_tree(src, dst):
    n = 0
    for base, _dirs, files in os.walk(src):
        rel = os.path.relpath(base, src)
        out = os.path.join(dst, rel) if rel != '.' else dst
        os.makedirs(out, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(base, f), os.path.join(out, f))
            n += 1
    return n


def copy_one(src, dst):
    if not os.path.exists(src):
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', default='h1', choices=sorted(PROFILES))
    ap.add_argument('--label', default=None)
    ap.add_argument('--no-maps', action='store_true')
    a = ap.parse_args()
    prof = PROFILES[a.game]
    trees, shared, files = prof['trees'], prof['shared'], prof['files']
    maps, scripts = prof['maps'], prof['scripts']
    if a.label is None:
        a.label = prof['label']
    stamp = datetime.datetime.now().strftime('%Y-%m-%d')
    out = os.path.join(ROOT, '%s_%s' % (stamp, a.label))
    os.makedirs(out, exist_ok=True)
    total = 0
    for src, rel, _is_dir in trees:
        if os.path.isdir(src):
            n = copy_tree(src, os.path.join(out, rel.replace('/', B)))
            print('  %-34s %d file(s)' % (rel, n))
            total += n
    for src, rel in shared + files + ([] if a.no_maps else maps):
        n = copy_one(src, os.path.join(out, rel.replace('/', B)))
        print('  %-34s %s' % (rel, 'ok' if n else 'MISSING: ' + src))
        total += n
    n = 0
    for s in scripts:
        n += copy_one(os.path.join(HERE, s), os.path.join(out, 'scripts', s))
    print('  %-34s %d of %d script(s)' % ('scripts/', n, len(scripts)))
    total += n
    size = sum(os.path.getsize(os.path.join(b, f))
               for b, _d, fs in os.walk(out) for f in fs)
    print('\n%d file(s), %.1f MB -> %s' % (total, size / 1e6, out))
    # A cache file is the one artifact that cannot be rebuilt byte-identically, so make
    # sure it really landed rather than trusting the copy.
    for src, rel in ([] if a.no_maps else maps):
        dst = os.path.join(out, rel.replace('/', B))
        if os.path.exists(dst):
            same = filecmp.cmp(src, dst, shallow=False)
            print('verify %-28s %s' % (rel, 'identical' if same else 'MISMATCH'))


if __name__ == '__main__':
    main()

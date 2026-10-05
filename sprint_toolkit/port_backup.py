"""Back up the weapon-port work to F:, separately from the map baselines on E:.

What a port actually consists of is spread over three places, and losing any one of them
means rebuilding it from scratch:
  * the EK source tags and data the weapon is built from (its own tags, plus the SHARED
    tags a port had to edit -- the HUD message-icon sheet is the dangerous one, because
    tool rewrites it in place and a fresh EK install would silently lose the SAW's icon),
  * the built cache file, which is the only artifact co-op partners can be given, and
  * the build scripts and the catalog the patcher reads.

    python port_backup.py --game h1|h2|h3|odst|reach|h4 [--label saw-h2] [--no-maps]

`--game` picks which port is backed up; `--no-maps` skips the cache files, which are
the slow part and are only worth keeping when a built map exists.
"""
import argparse, datetime, filecmp, glob, os, shutil, sys

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
SCRIPTS = ('port_refs_audit.py', 'saw_build.py', 'saw_to_jms.py', 'saw_shaders.py', 'saw_weapon.py', 'saw_anims.py',
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
H2_SCRIPTS = ('port_refs_audit.py', 'saw_to_jms_h2.py', 'h2_jms.py', 'h2_jms_preview.py', 'h2_tagref.py',
              'h2_tagfield.py', 'h2_loosetag.py', 'h2_batch.py',
              'h2_saw_textures.py', 'h2_saw_weapon.py', 'h2_saw_numbers.py',
              'h2_saw_collision.py', 'h2_saw_meter.py', 'h2_saw_hud_plate.py',
              'h2_saw_reticle.py', 'h2_saw_scope.py', 'h2_saw_glyph.py',
              'h2_saw_messages.py', 'h2_saw_animations.py', 'h2_saw_place.py',
              'h2_anim.py', 'h2_anim_retime.py', 'h2_font.py', 'h2_font_add.py',
              'h4_bitmap.py', 'h4_rm.py', 'h3_weapon_glyph.py',
              'make_port_catalog_h2.py', 'port_backup.py', 'PORTING.md')

# Reach, through HREK. The render model and both species' first-person graphs are
# FOUNDRY exports: the .blend files and sidecars under data\ are the source, so the data
# tree is kept whole. The shared tags the port edits in place are the chud, the new meter
# sheet, and hud_messages (tag and its .txt source); the icon lives in the LIVE font
# packages in the game folder, kept next to their pre-port copies from E:.
HREK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'HREK')
SAWR = os.path.join('objects', 'weapons', 'rifle', 'saw')
REACH_TREES = [
    (os.path.join(HREK, 'tags', SAWR), 'tags/objects/weapons/rifle/saw', True),
    (os.path.join(HREK, 'data', SAWR), 'data/objects/weapons/rifle/saw', True),
    (os.path.join(GAME, 'haloreach', 'maps', 'fonts'), 'shared/fonts_live', True),
    (os.path.join(E_BACKUPS, 'reach_live_fonts'), 'shared/fonts.stock', True),
    # the SAW's own sounds (reach_saw_sounds.py): sound tags + source wavs
    (os.path.join(HREK, 'tags', 'sound', 'weapons', 'saw_port'), 'tags/sound/weapons/saw_port', True),
    (os.path.join(HREK, 'data', 'sound', 'weapons', 'saw_port'), 'data/sound/weapons/saw_port', True),
]
REACH_SHARED = [
    # the SAW's FMOD bank, as built by the kit and as installed beside the stock sfx.fsb
    (os.path.join(HREK, 'fmod', 'pc', 'sfx.saw.fsb'), 'fmod/pc/sfx.saw.fsb'),
    (os.path.join(HREK, 'fmod', 'pc', 'sfx.saw.fsb.info'), 'fmod/pc/sfx.saw.fsb.info'),
    (os.path.join(HREK, 'tags', 'ui', 'chud', 'saw.chud_definition'),
     'tags/ui/chud/saw.chud_definition'),
    (os.path.join(HREK, 'tags', 'ui', 'chud', 'bitmaps', 'saw_ballistic_meter.bitmap'),
     'tags/ui/chud/bitmaps/saw_ballistic_meter.bitmap'),
    (os.path.join(HREK, 'tags', 'ui', 'hud', 'hud_messages.multilingual_unicode_string_list'),
     'tags/ui/hud/hud_messages.multilingual_unicode_string_list'),
    (os.path.join(HREK, 'data', 'ui', 'hud', 'hud_messages.txt'), 'data/ui/hud/hud_messages.txt'),
    # the SAW is PLACED in m20 by hand in Sapien -- the only copy of that work
    (os.path.join(HREK, 'tags', 'levels', 'solo', 'm20', 'm20.scenario'),
     'tags/levels/solo/m20/m20.scenario'),
]
REACH_FILES = [
    (os.path.join(TOOL, 'weapon_ports_catalog.json'), 'catalog/weapon_ports_catalog.json'),
    (os.path.join(HERE, 'balance_SAW_Halo4_to_HaloReach.json'),
     'catalog/balance_SAW_Halo4_to_HaloReach.json'),
    (os.path.join(HERE, 'PORTING.md'), 'catalog/PORTING.md'),
]
REACH_MAPS = [
    (os.path.join(GAME, 'haloreach', 'maps', 'm20.map'), 'maps/m20.map'),
]
REACH_SCRIPTS = ('reach_saw_sounds.py', 'saw_port_audio.py', 'port_sound_refs.py', 'h4_wwise.py', 'port_refs_audit.py', 'h3_kit.py', 'h3tag.py', 'h3_make_saw.py', 'saw_to_jms_h3.py',
                 'saw_port_values.py', 'reach_ek_build.py', 'reach_saw_wire_model.py',
                 'reach_saw_textures.py', 'reach_saw_tag_numbers.py',
                 'make_port_catalog_reach.py', 'h3_saw_chud.py', 'reach_meter_art.py',
                 'h3_port_messages.py', 'h3_weapon_glyph.py', 'h3_font_package.py',
                 'h3_font_codec.py', 'h3_font_repack.py', 'h3_saw_animations.py',
                 'foundry_setup.py', 'reach_foundry_saw.py', 'reach_foundry_fp_probe.py',
                 'reach_foundry_fp_retime.py', 'reach_node_names.py', 'reach_donor_mesh.py',
                 'reach_saw_bisect.py', 'port_backup.py', 'PORTING.md')

# Halo 4 as the TARGET (the H4 port kit, first weapon Reach's Focus Rifle): the port's
# tags and its Foundry source live under H4EK; the source textures Foundry extracted sit
# in HREK's data folder.
H4EK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'H4EK')
FOCUS = os.path.join('objects', 'weapons', 'rifle', 'focus_rifle')
H4_TREES = [
    (os.path.join(H4EK, 'tags', FOCUS), 'tags/objects/weapons/rifle/focus_rifle', True),
    (os.path.join(H4EK, 'data', FOCUS), 'data/objects/weapons/rifle/focus_rifle', True),
    (os.path.join(HREK, 'data', FOCUS), 'source/hrek_data_focus_rifle', True),
    (os.path.join(H4EK, 'tags', 'objects', 'characters', 'storm_fp', 'weapons', 'rifle',
                  'fp_focus_rifle'), 'tags/objects/characters/storm_fp/fp_focus_rifle', True),
    (os.path.join(H4EK, 'data', 'objects', 'characters', 'storm_fp', 'weapons', 'rifle',
                  'fp_focus_rifle'), 'data/objects/characters/storm_fp/fp_focus_rifle', True),
    # the port's OWN sound tags (h4_make_port_weapon.make_sound_tags) and soundbank tag
    (os.path.join(H4EK, 'tags', 'sound', 'weapons', 'focus_rifle', 'port'),
     'tags/sound/weapons/focus_rifle/port', True),
    # the built Wwise bank port_sounds.py installs (also committed in the repo)
    (os.path.join(TOOL, 'port_sounds', 'halo4'), 'port_sounds/halo4', True),
    # the port's own HUD screen, Reach scope template and scope bitmaps
    (os.path.join(H4EK, 'tags', 'ui', 'hud', 'weapons', 'covenant', 'focus_rifle'),
     'tags/ui/hud/weapons/covenant/focus_rifle', True),
    (os.path.join(H4EK, 'data', 'ui', 'hud', 'weapons', 'covenant', 'focus_rifle'),
     'data/ui/hud/weapons/covenant/focus_rifle', True),
]
H4_FILES = [
    # tool-root modules the port relies on at patch time (icons, sound bank)
    (os.path.join(TOOL, 'port_glyphs.py'), 'tool/port_glyphs.py'),
    (os.path.join(TOOL, 'port_glyphs.json'), 'tool/port_glyphs.json'),
    (os.path.join(TOOL, 'port_sounds.py'), 'tool/port_sounds.py'),
    (os.path.join(TOOL, 'weapon_ports_catalog.json'), 'catalog/weapon_ports_catalog.json'),
    (os.path.join(HERE, 'balance_Focus_Rifle_HaloReach_to_Halo4.json'),
     'catalog/balance_Focus_Rifle_HaloReach_to_Halo4.json'),
    (os.path.join(HERE, 'PORTING.md'), 'catalog/PORTING.md'),
]
# shared files the H4 port EDITS IN PLACE: the two string lists (fr_* pickup lines,
# focus_rifle_icon) as tags and as source text in every language folder, and the LIVE icon
# font packages carrying the port's glyph U+E1F6 (h4_weapon_glyph.py) -- a Steam update
# or verify restores the stock packages, and an EK reinstall the stock string lists.
H4_SHARED = [
    (os.path.join(H4EK, 'tags', 'ui', 'strings', n + '.multilingual_unicode_string_list'),
     'tags/ui/strings/%s.multilingual_unicode_string_list' % n) for n in ('ingame', 'weapons')
] + [
    (os.path.join(H4EK, d, 'ui', 'strings', n + '.txt'), '%s/ui/strings/%s.txt' % (d, n))
    for d in ['data'] + ['data_' + x for x in ('chs', 'cht', 'de', 'dk', 'fi', 'fr', 'it',
                                               'jpn', 'kor', 'mx', 'nl', 'no', 'pl', 'pt',
                                               'ru', 'sp')]
    for n in ('ingame', 'weapons')
] + [
    (os.path.join(GAME, 'halo4', 'maps', 'fonts', f), 'live_fonts/' + f)
    for f in ('font_package_icon.bin', 'font_package_icon_x2.bin',
              'font_package_icon_x3.bin', 'font_package_icon_x4.bin')
]
H4_SHARED.append((os.path.join(H4EK, 'tags', 'sound', 'soundbanks', 'weapons_covenant',
                               'port_focus_rifle.soundbank'),
                  'tags/sound/soundbanks/weapons_covenant/port_focus_rifle.soundbank'))
H4_MAPS = [
    (os.path.join(GAME, 'halo4', 'maps', 'm30_cryptum.map'), 'maps/m30_cryptum.map'),
]
H4_SCRIPTS = ('port_refs_audit.py', 'h4_weapon_diff.py', 'h4_cusc_dump.py', 'reach_effect_tints.py',
              'h3tag.py', 'foundry_setup.py', 'h4_foundry_port.py', 'h4_port_materials.py',
              'h4_make_port_weapon.py', 'h4_weapon_refs.py', 'h4_tag_numbers.py', 'balance_port.py',
              'h4_map_poke.py', 'h4_fp_jump.py', 'h4_fp_graph.py', 'h4_beam_look.py', 'h4_port_messages.py',
              'h4_mesh_dump.py', 'h4_weapon_glyph.py', 'h4_hud_icon.py', 'h3_font_repack.py', 'h3_font_codec.py',
              'h3_weapon_glyph.py', 'h4_reach_scope_art.py', 'h4_reach_scope.py',
              'h4_muzzle_recolor.py', 'h4_muzzle_tags.py', 'h4_wwise.py', 'h4_sound_test.py',
              'h4_sound_bank.py',
              'make_port_catalog_h4.py', 'port_backup.py', 'PORTING.md')

# --- STEP 10, the SAW's OWN SOUNDS (2026-10-05), in every SAW profile -----------------
# The Halo 4 source audio (h4_wwise.py --extract + saw_port_audio.py) sits in H4EK\temp,
# which nothing else keeps; each kit's sound tags + the wavs/mixes they were imported
# from; and the tool-root modules + Halo 1 bank audio the patcher installs from.
H3ODSTEK = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'H3ODSTEK')
H4EK_TEMP = os.path.join(F, 'SteamLibrary', 'steamapps', 'common', 'H4EK', 'temp')
SND = os.path.join('sound', 'weapons', 'saw_port')
SOUND_SOURCE = [(os.path.join(H4EK_TEMP, 'saw_sounds'), 'source/h4_saw_sounds', True),
                (os.path.join(H4EK_TEMP, 'saw_port_audio'), 'source/h4_saw_port_audio', True)]
SOUND_FILES = [(os.path.join(TOOL, m), 'tool/' + m) for m in ('port_volume.py', 'port_sounds.py', 'h1_fsb.py')]
SOUND_SCRIPTS = ('h4_wwise.py', 'saw_port_audio.py', 'saw_port_foley.py', 'port_sound_levels.py',
                 'graph_sound_events.py', 'port_sound_refs.py', 'h3tag.py')


def sound_trees(ek):
    return [(os.path.join(ek, 'tags', SND), 'tags/sound/weapons/saw_port', True),
            (os.path.join(ek, 'data', SND), 'data/sound/weapons/saw_port', True)]


TREES += sound_trees(HCEEK) + SOUND_SOURCE + [
    (os.path.join(TOOL, 'port_sounds', 'halo1'), 'tool/port_sounds/halo1', True)]
FILES += SOUND_FILES
SCRIPTS += SOUND_SCRIPTS + ('h1_saw_sounds.py', 'h1_saw_tone.py', 'h1_rebuild_all.py')
H2_TREES += sound_trees(H2EK) + SOUND_SOURCE
H2_FILES += SOUND_FILES
H2_SCRIPTS += SOUND_SCRIPTS + ('h2_saw_sounds.py',)
REACH_TREES += SOUND_SOURCE
REACH_FILES += SOUND_FILES
REACH_SCRIPTS += SOUND_SCRIPTS + ('saw_port_sounds.py', 'fsb5_merge.py', 'reach_sound_suffix.py')


# Halo 3 and ODST had NO profile until 2026-10-05: the SAW's own folder (weapon, graphs,
# effects), its sounds + FMOD bank (step 10), and the SHARED files steps 7/8 edit in place
# -- the chud and its bitmap sheets (meter, schematic, sprite boxes), hud_messages (tag +
# its .txt in every language), the live icon font packages and MCC's loose localization
# .bin files (each beside its pre-port copy on E:), and the scenario the SAW is PLACED in
# by hand (Sapien + starting profile).
def h3_family(ek, mcc_folder, maps, loc_game, short, scenario):
    trees = [(os.path.join(ek, 'tags', 'objects', 'weapons', 'rifle', 'saw'),
              'tags/objects/weapons/rifle/saw', True)] + sound_trees(ek) + SOUND_SOURCE + [
        (os.path.join(ek, 'tags', 'ui', 'chud', 'bitmaps'), 'tags/ui/chud/bitmaps', True),
        (os.path.join(GAME, mcc_folder, 'maps', 'fonts'), 'shared/fonts_live', True),
        (os.path.join(E_BACKUPS, '%s_live_fonts' % short), 'shared/fonts.stock', True)]
    shared = [(os.path.join(ek, 'fmod', 'pc', 'sfx.saw.fsb' + x), 'fmod/pc/sfx.saw.fsb' + x)
              for x in ('', '.info')] + [
        (os.path.join(ek, 'tags', 'ui', 'chud', 'saw.chud_definition'),
         'tags/ui/chud/saw.chud_definition'),
        (os.path.join(ek, 'tags', 'ui', 'hud', 'hud_messages.multilingual_unicode_string_list'),
         'tags/ui/hud/hud_messages.multilingual_unicode_string_list'),
        (os.path.join(ek, 'tags', *scenario.split('/')), 'tags/' + scenario)]
    for d in sorted(glob.glob(os.path.join(ek, 'data*'))):           # data + data_<lang>
        p = os.path.join(d, 'ui', 'hud', 'hud_messages.txt')
        if os.path.exists(p):
            shared.append((p, '%s/ui/hud/hud_messages.txt' % os.path.basename(d)))
    loc = os.path.join(GAME, 'data', 'UI', 'Localization')
    for f in sorted(glob.glob(os.path.join(loc, '*_%s.bin' % loc_game))):
        shared.append((f, 'shared/localization/' + os.path.basename(f)))
        shared.append((os.path.join(E_BACKUPS, 'mcc_localization', os.path.basename(f)),
                       'shared/localization.stock/' + os.path.basename(f)))
    files = [(os.path.join(TOOL, 'weapon_ports_catalog.json'), 'catalog/weapon_ports_catalog.json'),
             (os.path.join(HERE, 'PORTING.md'), 'catalog/PORTING.md')] + SOUND_FILES
    return trees, shared, files, [(os.path.join(GAME, mcc_folder, 'maps', m + '.map'),
                                   'maps/%s.map' % m) for m in maps]


H3_SCRIPTS = SOUND_SCRIPTS + ('saw_port_sounds.py', 'fsb5_merge.py', 'h3_build_map.py',
                              'h3_saw_deploy.py', 'h3_chunk_check.py', 'h3_saw_animations.py',
                              'h3_make_saw.py', 'port_backup.py', 'PORTING.md',
                              # steps 7 / 8: the HUD and the pickup text
                              'h3_kit.py', 'h3_saw_chud.py', 'h3_meter_art.py',
                              'h3_chud_sequence.py', 'h3_sprite_box.py', 'h3_weapon_glyph.py',
                              'h3_weapon_schematic.py', 'h3_saw_pickup_icon.py',
                              'h3_mcc_localization.py', 'h3_port_messages.py',
                              'h3_font_package.py', 'h3_font_codec.py', 'h3_font_repack.py')
H3_T, H3_S, H3_F, H3_M = h3_family(H3EK, 'halo3', ['010_jungle'], 'Halo3', 'h3',
                                   'levels/solo/010_jungle/010_jungle.scenario')
ODST_T, ODST_S, ODST_F, ODST_M = h3_family(H3ODSTEK, 'halo3odst', ['sc150'], 'Halo3ODST', 'odst',
                                           'levels/atlas/sc150/sc150.scenario')

# --- STEP 4b, the fields no card covers (port_field_audit.py, 2026-10-05) -------------
# the audit + the before/after proof in every profile; each game's writer beside it
FIELD_SCRIPTS = ('port_field_audit.py', 'kit_tag_diff.py', 'h4_weapon_diff.py',
                 'port_role_compare.py')
SCRIPTS += FIELD_SCRIPTS + ('saw_port_values.py', 'make_port_catalog.py')
H2_SCRIPTS += FIELD_SCRIPTS + ('h2_saw_yardstick.py', 'h2_saw_numbers.py', 'h2_tagfield.py',
                               'h2_tagfield_offsets.json', 'make_port_catalog_h2.py',
                               'h2_saw_weapon.py')
REACH_SCRIPTS += FIELD_SCRIPTS + ('reach_saw_tag_numbers.py',)
H3_SCRIPTS += FIELD_SCRIPTS + ('h3_saw_tag_numbers.py', 'make_port_catalog_h3.py',
                               'make_port_catalog_odst.py', 'balance_port.py')
H4_SCRIPTS += FIELD_SCRIPTS

PROFILES = {
    'h1': {'trees': TREES, 'shared': SHARED, 'files': FILES, 'maps': MAPS,
           'scripts': SCRIPTS, 'label': 'saw-h1'},
    'h2': {'trees': H2_TREES, 'shared': H2_SHARED, 'files': H2_FILES, 'maps': [],
           'scripts': H2_SCRIPTS, 'label': 'saw-h2'},
    'h3': {'trees': H3_T, 'shared': H3_S, 'files': H3_F, 'maps': H3_M,
           'scripts': H3_SCRIPTS, 'label': 'saw-h3'},
    'odst': {'trees': ODST_T, 'shared': ODST_S, 'files': ODST_F, 'maps': ODST_M,
             'scripts': H3_SCRIPTS + ('odst_ek_build.py',), 'label': 'saw-odst'},
    'reach': {'trees': REACH_TREES, 'shared': REACH_SHARED, 'files': REACH_FILES,
              'maps': REACH_MAPS, 'scripts': REACH_SCRIPTS, 'label': 'saw-reach'},
    'h4': {'trees': H4_TREES, 'shared': H4_SHARED, 'files': H4_FILES, 'maps': H4_MAPS,
           'scripts': H4_SCRIPTS, 'label': 'focus-rifle-h4'},
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
    # NAME the ones that are not there. This list is the only record of what a port's
    # tooling consists of, and for a while it quietly ran nine short: the Halo 1 tools
    # were rescued out of a session scratchpad, saw_port_values.py was missed, and the
    # build stayed broken until someone ran it. "31 of 39" reads like a number rather
    # than a loss, so a shortfall now says which files and refuses to be background.
    n, gone = 0, []
    for s in scripts:
        got = copy_one(os.path.join(HERE, s), os.path.join(out, 'scripts', s))
        n += got
        if not got:
            gone.append(s)
    print('  %-34s %d of %d script(s)' % ('scripts/', n, len(scripts)))
    if gone:
        print('  %-34s %s' % ('  NOT IN THE TOOLKIT:', ', '.join(gone)))
        print('  %-34s %s' % ('', 'the manifest names them and they do not exist -- '
                              'either rescue them or drop them from SCRIPTS'))
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

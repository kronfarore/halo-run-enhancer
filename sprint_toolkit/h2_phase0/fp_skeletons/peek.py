import sys
sys.path.insert(0, r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool\sprint_toolkit')
import h1_fp_retarget, reach_tags, h4_rm
for rel in sys.argv[1:]:
    load = reach_tags.load_render_model if reach_tags.is_reach(rel) else h4_rm.load
    rm = load(h1_fp_retarget.export_xml(rel))
    for n in rm['nodes'][:8]:
        print(rel[-30:], n['name'], n['parent'], n['pos'], n['rot'])

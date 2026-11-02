import json,os,sys
LEVELS=[('m10_crash', 'Dawn'), ('m020', 'Requiem'), ('m30_cryptum', 'Forerunner'),('m60_rescue', 'Infinity'), ('m40_invasion', 'Reclaimer'), ('m70_liftoff', 'Shutdown'),('m80_delta', 'Composer'), ('m90_sacrifice', 'Midnight')]
for mid,title in LEVELS:
    p='census_%s.json'%mid
    if not os.path.exists(p): continue
    d=json.load(open(p))
    print('==',mid,title,'squads',d['squads'],'both',d['both_cells'],'ptr=',d['twin_ptr_same'],'bytes=',d['twin_bytes_same'],'zonesets',d['zone_sets'],'dz',d['dz_index'],'dzON',d['dz_zone_sets_on'],'why',d['dz_why'],'slack',d['slack_runs'],d['slack_total'],d['slack_max'],'sqtm',d['sqtm'])
    print('  arrays',d['array_ptrs'],d['array_max_users'])
    print('  per species:')
    for k,v in sorted(d['per'].items(),key=lambda kv:-kv[1].get('spawn',0)-kv[1].get('cell_count',0)):
        print('    %-16s %s'%(k,v))
    print('  ts_units',{k:v for k,v in d['ts_units'].items()})
    print('  gaps',d['gaps'])
    print('  weap_res (<full):',{k:(v.get('card'),v.get('weap_sets'),v.get('full_sets')) for k,v in d['weap_res'].items() if v.get('full_sets')!=d['zone_sets']})
    print('  chars sets',d['char_sets_n'])
    print('  dz items n',len(d['dz_items'] or []),'pal n',len(d['weapons']),'pal not dz',sorted(set(x for x in d['weapons'] if x)-set(d['dz_items'] or [])),'dz not pal',sorted(set(d['dz_items'] or [])-set(x for x in d['weapons'] if x)))

import json
from collections import Counter

rows = [json.loads(l) for l in open('results/predictions_full.jsonl')]
ds = [r for r in rows if r['model'] == 'deepseek-v4.1-flash']
bad = [r for r in ds if r['label'] is None]
print('deepseek nulls:', len(bad), 'of', len(ds))

print('\n== null by codebook/condition ==')
print(Counter((r['codebook'], r['condition']) for r in bad))

print('\n== finish reasons on nulls ==')
print(Counter(r.get('native_finish_reason') for r in bad))
print('was_salvage_retry on nulls:', Counter(r.get('was_salvage_retry') for r in bad))

print('\n== sample raw contents ==')
for r in bad[:6]:
    print('---', r['codebook'], r['condition'],
          '| finish=', r.get('native_finish_reason'),
          '| retry=', r.get('was_salvage_retry'),
          '| ctoks=', (r.get('usage') or {}).get('completion_tokens'))
    print('   raw:', repr(r.get('raw_content'))[:250])

print('\n== unparsed (non-null but not a valid label) by model ==')
LAB_A = {'ja', 'nein'}
LAB_B = {'konfrontation_angriff', 'ablenkung_whataboutism',
         'delegierung_hilflosigkeit', 'vermeidung_rueckzug',
         'reflektierte_rechtfertigung', 'konstruktive_kritik', 'keine_reaktanz'}
for m in sorted({r['model'] for r in rows}):
    sub = [r for r in rows if r['model'] == m]
    ok = {'A': LAB_A, 'B': LAB_B}
    nbad = sum(1 for r in sub if r['label'] not in ok[r['codebook']])
    print(f'  {m:22s} unparsed {nbad}/{len(sub)}')

print('\n== label distribution, codebook A, condition A ==')
for m in sorted({r['model'] for r in rows}):
    sub = [r['label'] for r in rows if r['model'] == m and r['codebook'] == 'A'
           and r['condition'] == 'A' and r['label'] in LAB_A]
    print(f'  {m:22s} {Counter(sub)}')

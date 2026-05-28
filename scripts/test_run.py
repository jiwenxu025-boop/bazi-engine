# -*- coding: utf-8 -*-
from bazi_engine.chart import build_chart
import os

os.environ['BAZI_FUSION_ENGINE'] = '1'
os.environ['BAZI_LLM_REVIEW'] = '0'

c = build_chart('test', '男', 2007, 8, 26, 20, liunian_range=(2023, 2030))

p = c.personality_result
lines = []
lines.append('=== profile ===')
lines.append(p.get('profile', ''))
lines.append('')
lines.append('=== traits ===')
for k, v in p.get('traits', {}).items():
    lines.append('  [%s] %s' % (k, v))
lines.append('')
lines.append('=== day_master_core ===')
lines.append(p.get('day_master_core', '')[:300])
lines.append('')
lines.append('=== bingyao ===')
for b in p.get('bingyao_combos', []):
    lines.append('  %s: %s' % (b['combo'], b['directive'][:200]))
lines.append('')
lines.append('=== weighted_shishen top5 ===')
ws = p.get('weighted_shishen', {}).get('scores', {})
for name, score in sorted(ws.items(), key=lambda x: x[1], reverse=True)[:5]:
    lines.append('  %s: %s' % (name, score))
lines.append('')
lines.append('=== pattern: %s ===' % c.pattern)
lines.append('')
ys = c._yongshen_result or {}
lines.append('=== strength: %s (%s) ===' % (ys.get('strength', '?'), ys.get('score', '?')))
lines.append('fav shishen: %s' % ys.get('favorable', []))
lines.append('harm shishen: %s' % ys.get('harmful', []))

with open('test_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('Done. See test_output.txt')

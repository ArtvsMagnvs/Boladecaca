import re
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'openai_models.html'), encoding='utf-8', errors='replace') as f:
    html = f.read()
prices = re.findall(r'\$([0-9.]+) / (Input|Output) MTok', html)
print('All prices found:')
for p, t in prices:
    print(f'  {t}: ${p}')
print('---')
ctxs = re.findall(r'>([0-9]+[KM])\s*</div>\s*<div[^>]*>[^<]*Context window', html, re.DOTALL)
print('Context windows:', ctxs[:10])
cutoffs = re.findall(r'>([A-Z][a-z]+ [0-9]+, [0-9]+)\s*</div>\s*<div[^>]*>[^<]*Knowledge', html)
print('Cutoffs:', cutoffs[:10])
# Buscar GPT-5.4 nano
print('---')
nano_match = re.search(r'GPT-5\.4 nano.{0,3000}', html, re.DOTALL)
if nano_match:
    snippet = nano_match.group(0)[:2500]
    print('GPT-5.4 nano snippet (primeros 2500 chars):')
    print(snippet)
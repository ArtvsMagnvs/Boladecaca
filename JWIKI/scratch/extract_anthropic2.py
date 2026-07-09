import re
with open(r'C:\tmp\anthropic_models_overview.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'&nbsp;', ' ', text)
text = re.sub(r'&amp;', '&', text)
text = re.sub(r'&lt;', '<', text)
text = re.sub(r'&gt;', '>', text)
text = re.sub(r'&quot;', '"', text)
text = re.sub(r'&#39;', "'", text)
text = re.sub(r'\s+', ' ', text)
# Find pricing
for pat in [r'\$[0-9]+(\.[0-9]+)?\s*/\s*MTok.{0,100}', r'\$[0-9]+(\.[0-9]+)?\s*per MTok.{0,100}', r'200,?000.{0,100}', r'1,?000,?000.{0,80}token', r'cache.{0,200}', r'prompt caching.{0,300}', r'computer use.{0,200}', r'extended thinking.{0,200}', r'effort parameter.{0,200}', r'output tokens.{0,200}', r'input tokens.{0,200}', r'Pricing.{0,500}', r'pricing.{0,500}', r'\[VERIFICAR', r'verificar.{0,150}']:
    print(f"\n=== {pat} ===")
    seen=set()
    for m in re.finditer(pat, text, re.IGNORECASE):
        key=m.group(0)[:80]
        if key in seen: continue
        seen.add(key)
        if len(seen)>=8: break
        print(' ', m.group(0)[:250])
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
print("LENGTH:", len(text))
# Print context around model names
for pat in [r'claude-[a-z]+-4-[0-9](\-[0-9]+)?', r'claude-opus-4-[0-9]\b', r'Claude Opus 4.{0,800}']:
    print(f"\n=== Pattern: {pat} ===")
    seen = set()
    for m in re.finditer(pat, text):
        key = m.group(0)[:60]
        if key in seen: continue
        seen.add(key)
        print('  ', m.group(0)[:200])
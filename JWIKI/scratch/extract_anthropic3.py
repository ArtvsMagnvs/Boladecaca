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
# Print big blocks
i = text.find('Claude is a family')
if i>=0:
    print(text[i:i+8000])
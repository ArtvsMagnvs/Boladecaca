import re
for f, label in [(r'C:\tmp\anthropic_prompt_caching.html', 'CACHE'),
                  (r'C:\tmp\anthropic_computer_use.html', 'COMP'),
                  (r'C:\tmp\anthropic_pricing.html', 'PRICING')]:
    with open(f, 'r', encoding='utf-8', errors='replace') as fh:
        html = fh.read()
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'\s+', ' ', text)
    print(f"\n========== {label} ==========")
    # find prompt caching pricing
    if 'CACHE' in label:
        i = text.find('cache write')
        if i>=0:
            print(text[max(0,i-500):i+2500])
    elif 'COMP' in label:
        i = text.find('computer use')
        if i>=0:
            print(text[max(0,i-200):i+2000])
        # pricing for comp use
        for pat in [r'computer.{0,40}use.{0,40}pricing.{0,300}', r'computer.{0,40}use.{0,40}\$.{0,200}', r'\$.{0,5}/.{0,40}image.{0,200}']:
            print('---',pat)
            for m in re.finditer(pat, text, re.IGNORECASE):
                print('  ', m.group(0)[:300])
    elif 'PRICING' in label:
        i = text.find('cache write')
        if i>=0:
            print(text[max(0,i-300):i+1500])
        i2 = text.find('Cache')
        if i2>=0:
            print(text[max(0,i2-200):i2+2000])
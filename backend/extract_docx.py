import zipfile
import xml.etree.ElementTree as ET
import sys

with zipfile.ZipFile(r'c:\Users\Alejandro\Desktop\Aithera\Actualizacion_V0.2.docx', 'r') as z:
    with z.open('word/document.xml') as f:
        content = f.read().decode('utf-8')

root = ET.fromstring(content)
ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

texts = []
for p in root.iter(f'{ns}p'):
    text = ''
    for t in p.iter(f'{ns}t'):
        text += t.text or ''
    if text.strip():
        texts.append(text)

output = '\n'.join(texts)
with open(r'c:\Users\Alejandro\Desktop\Aithera\Actualizacion_V0.2.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Saved", len(output), "chars to Actualizacion_V0.2.txt")
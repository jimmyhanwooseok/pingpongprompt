with open('.env', 'r', encoding='utf-16') as f:
    content = f.read()
with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)
print('변환 완료!') 
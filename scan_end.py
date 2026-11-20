with open('public/index.html') as f:
    text = f.read()

# Kiểm tra các thẻ <style>
import re
styles = re.findall(r'<style(?:\s+[^>]*)?>(.*?)</style>', text, re.DOTALL)
print(f'Total style tags: {len(styles)}')

# Kiểm tra các lỗi HTML syntax từ dòng 5000 đến hết
lines = text.split('\n')
for i in range(5000, len(lines)):
    l = lines[i]
    # Check for invalid html entities or unclosed tags
    if '<<' in l or '>>' in l:
        print(f'Line {i+1}: double angle bracket: {l}')
    if '& ' in l:
        # unescaped ampersand?
        pass

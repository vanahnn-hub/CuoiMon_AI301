with open('public/index.html') as f:
    lines = f.readlines()

# Kiểm tra dòng 4400 đến dòng 5500
# Tìm các lỗi:
# 1. Unescaped quotes inside template literals
# 2. Syntax errors in JS
# 3. Mismatched parentheses or brackets

for i in range(4400, min(5500, len(lines))):
    line = lines[i]
    # Check for suspicious patterns like missing closing tags, unescaped characters
    # Look for broken backticks
    if '`' in line:
        pass
print(f'Checking range 4400-5500 ({len(lines)} total lines)')

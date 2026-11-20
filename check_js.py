import re

with open('public/index.html') as f:
    text = f.read()

matches = [m for m in re.finditer(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', text, re.DOTALL)]
script = matches[2].group(1)
start_offset = matches[2].start()
start_line = text[:start_offset].count('\n') + 1

stack = []
errors = []
i = 0
n = len(script)
line_no = start_line

while i < n:
    ch = script[i]
    if ch == '\n':
        line_no += 1
        i += 1
        continue
    # Single-line comment
    if ch == '/' and i + 1 < n and script[i+1] == '/':
        i += 2
        while i < n and script[i] != '\n':
            i += 1
        continue
    # Multi-line comment
    if ch == '/' and i + 1 < n and script[i+1] == '*':
        i += 2
        while i + 1 < n and not (script[i] == '*' and script[i+1] == '/'):
            if script[i] == '\n':
                line_no += 1
            i += 1
        i += 2
        continue
    # String literal '
    if ch == "'":
        i += 1
        while i < n and script[i] != "'":
            if script[i] == '\\':
                i += 2
            elif script[i] == '\n':
                errors.append((line_no, "Unclosed single quote '"))
                break
            else:
                i += 1
        i += 1
        continue
    # String literal "
    if ch == '"':
        i += 1
        while i < n and script[i] != '"':
            if script[i] == '\\':
                i += 2
            elif script[i] == '\n':
                errors.append((line_no, 'Unclosed double quote "'))
                break
            else:
                i += 1
        i += 1
        continue
    # Template literal `
    if ch == '`':
        i += 1
        while i < n:
            if script[i] == '\\':
                i += 2
            elif script[i] == '`':
                i += 1
                break
            elif script[i] == '\n':
                line_no += 1
                i += 1
            elif script[i:i+2] == '${':
                # inside template expression
                stack.append(('}', line_no, '${', 'template'))
                i += 2
                break
            else:
                i += 1
        continue
    # Closing brace of template expression ${ ... }
    if ch == '}' and stack and stack[-1][3] == 'template':
        stack.pop()
        i += 1
        # continue parsing template literal until next ` or ${
        while i < n:
            if script[i] == '\\':
                i += 2
            elif script[i] == '`':
                i += 1
                break
            elif script[i] == '\n':
                line_no += 1
                i += 1
            elif script[i:i+2] == '${':
                stack.append(('}', line_no, '${', 'template'))
                i += 2
                break
            else:
                i += 1
        continue
    # Brackets
    if ch in '({[':
        close_ch = ')' if ch == '(' else ('}' if ch == '{' else ']')
        stack.append((close_ch, line_no, ch, 'bracket'))
        i += 1
        continue
    if ch in ')}]':
        if not stack:
            errors.append((line_no, f'Unexpected closing bracket {ch}'))
        else:
            exp, op_line, op_ch, btype = stack.pop()
            if ch != exp:
                errors.append((line_no, f'Mismatched closing bracket {ch}, expected {exp} (opened {op_ch} at line {op_line})'))
        i += 1
        continue
    i += 1

print('Total errors:', len(errors))
for e in errors[:10]:
    print(e)
if stack:
    print('Unclosed stack count:', len(stack))
    for s in stack[-5:]:
        print(s)

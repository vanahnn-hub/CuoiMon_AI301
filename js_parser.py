with open('public/index.html') as f:
    text = f.read()

# Lấy script chính từ dòng 1986 đến 7288
script_start = text.find('<script', 1900)
script_end = text.rfind('</script>')
js_code = text[script_start:script_end]
prefix_lines = text[:script_start].count('\n')

lines = js_code.split('\n')

stack = []
tokens = []

in_string = False
string_char = ''
is_escaped = False
in_regex = False
in_line_comment = False
in_block_comment = False

for line_idx, line in enumerate(lines):
    line_num = prefix_lines + line_idx + 1
    col = 0
    in_line_comment = False
    
    while col < len(line):
        c = line[col]
        
        if is_escaped:
            is_escaped = False
            col += 1
            continue
            
        if c == '\\' and (in_string or in_regex):
            is_escaped = True
            col += 1
            continue
            
        if in_line_comment:
            break
            
        if in_block_comment:
            if c == '*' and col + 1 < len(line) and line[col+1] == '/':
                in_block_comment = False
                col += 2
                continue
            col += 1
            continue
            
        if not in_string and not in_regex:
            if c == '/' and col + 1 < len(line):
                if line[col+1] == '/':
                    in_line_comment = True
                    break
                elif line[col+1] == '*':
                    in_block_comment = True
                    col += 2
                    continue
                    
        if in_string:
            if string_char == '`':
                # check for ${
                if c == '$' and col + 1 < len(line) and line[col+1] == '{':
                    stack.append(('${', line_num, col))
                    col += 2
                    continue
                elif c == '`':
                    in_string = False
                    string_char = ''
            elif c == string_char:
                in_string = False
                string_char = ''
            col += 1
            continue
            
        # Outside string
        if c in ("'", '"', '`'):
            in_string = True
            string_char = c
            col += 1
            continue
            
        if c in '({[':
            stack.append((c, line_num, col))
        elif c in ')}]':
            expected = {'(': ')', '{': '}', '[': ']'}[stack[-1][0]] if stack and stack[-1][0] in '({[' else ('}' if stack and stack[-1][0] == '${' else None)
            if not stack:
                print(f"Error at line {line_num}, col {col}: unexpected closing '{c}'")
            elif c != expected:
                top_sym, top_line, top_col = stack[-1]
                print(f"Error at line {line_num}, col {col}: got '{c}' but expected '{expected}' opened at line {top_line}")
                # Don't pop, just report
            else:
                stack.pop()
        col += 1

print(f"Total unclosed tokens: {len(stack)}")
for sym, l, c in stack[-15:]:
    print(f"  Unclosed '{sym}' opened at line {l}, col {c}")

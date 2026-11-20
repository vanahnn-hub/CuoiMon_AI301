with open('public/index.html') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'id=["\']fileInput["\']|onFileChosen|uploadFile|processUploadedFile', text)]
for m in matches:
    print(text[m-50:m+250])
    print('='*40)

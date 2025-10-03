"""
Script seguro para remover espaços finais, linhas em branco com espaços e garantir newline no fim
Aplica apenas a arquivos .py dentro de backend/controllers/
Executar localmente com o Python do workspace.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
controllers_dir = root / 'backend' / 'controllers'

modified = []
for p in sorted(controllers_dir.glob('*.py')):
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    new_lines = []
    changed = False
    for ln in lines:
        # remove trailing whitespace
        new_ln = ln.rstrip()
        # convert lines that were only whitespace to empty string
        if new_ln == '':
            new_lines.append('')
            if ln != new_ln:
                changed = True
        else:
            new_lines.append(new_ln)
            if new_ln != ln:
                changed = True
    # remove trailing blank lines at EOF
    while new_lines and new_lines[-1] == '':
        new_lines.pop()
        changed = True
    # ensure single newline at EOF
    new_text = '\n'.join(new_lines) + '\n'
    if new_text != text:
        p.write_text(new_text, encoding='utf-8')
        modified.append(str(p.relative_to(root)))

print('Modified files:')
for m in modified:
    print(m)
print(f'Total modified: {len(modified)}')

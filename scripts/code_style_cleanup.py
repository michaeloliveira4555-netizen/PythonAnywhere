"""
Low-risk code style cleanup:
- Remove trailing whitespace
- Convert lines that contain only spaces to empty
- Remove trailing blank lines at EOF and ensure single newline
- Collapse >2 consecutive blank lines to exactly 2
- Ensure 2 blank lines before top-level class/function definitions (except at file start)
Applies to all .py files under `backend/` and `tests/` by default.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = [ROOT / 'backend', ROOT / 'tests']

modified_files = []

for base in TARGET_DIRS:
    if not base.exists():
        continue
    for p in sorted(base.rglob('*.py')):
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        original = text
        # splitlines preserves no trailing newline
        lines = text.splitlines()
        # 1) remove trailing whitespace and normalize blank-only lines
        new_lines = [ln.rstrip() for ln in lines]
        new_lines = [ln if ln != '' else '' for ln in new_lines]
        # 2) collapse >2 blank lines to exactly 2 (global pass)
        collapsed = []
        blank_run = 0
        for ln in new_lines:
            if ln == '':
                blank_run += 1
            else:
                if blank_run > 2:
                    collapsed.extend([''] * 2)
                else:
                    collapsed.extend([''] * blank_run)
                blank_run = 0
                collapsed.append(ln)
        if blank_run:
            # trailing blanks removed later
            if blank_run > 2:
                collapsed.extend([''] * 2)
            else:
                collapsed.extend([''] * blank_run)
        new_lines = collapsed

        # 3) enforce two blank lines before top-level defs (using AST)
        try:
            tree = ast.parse('\n'.join(new_lines) + '\n')
            top_nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            # process in reverse, so line indices remain valid after edits
            for node in reversed(top_nodes):
                lineno = getattr(node, 'lineno', None)
                if lineno is None:
                    continue
                idx = lineno - 1  # 0-based index where def starts
                # if idx is 0 or within first 2 lines, skip (don't add blanks at file start)
                if idx <= 1:
                    continue
                # count existing blank lines immediately before idx
                m = idx - 1
                while m >= 0 and new_lines[m] == '':
                    m -= 1
                # m is last non-blank line before the block (or -1)
                if m < 0:
                    continue
                current_blank_count = idx - 1 - m
                if current_blank_count != 2:
                    # remove the existing blanks between m+1 .. idx-1 and insert exactly 2
                    before = new_lines[: m+1]
                    after = new_lines[idx:]
                    new_lines = before + ['',''] + after
        except Exception:
            # if parsing fails, skip AST-based changes for this file
            pass

        # 4) remove trailing blank lines at EOF, ensure single newline at EOF
        while new_lines and new_lines[-1] == '':
            new_lines.pop()
        new_text = '\n'.join(new_lines) + '\n'

        if new_text != original:
            p.write_text(new_text, encoding='utf-8')
            modified_files.append(str(p.relative_to(ROOT)))

print('Modified files:')
for f in modified_files:
    print(f)
print(f'Total modified: {len(modified_files)}')

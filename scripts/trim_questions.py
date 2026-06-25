"""Trim all grade sections to exactly 10 questions (4 Easy, 4 Medium, 2 Hard)."""
import re

with open('daily/2026-06-25.html', 'r', encoding='utf-8') as f:
    html = f.read()

def trim_section(html, grade, target=10):
    """Keep only the first `target` <li> items in a grade section."""
    pattern = rf'(<div class="grade-section" data-grade="{grade}"[^>]*>.*?<ol class="problems-list">)(.*?)(</ol>)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        print(f"  {grade}: not found")
        return html

    prefix = match.group(1)
    content = match.group(2)
    suffix = match.group(3)

    # Split into individual <li>...</li> items (top-level only)
    # Each question starts with <li> and we need to handle nested <ul><li>
    items = []
    depth = 0
    current = ''
    i = 0
    while i < len(content):
        if content[i:i+4] == '<li>' or content[i:i+3] == '<li':
            if depth == 0:
                if current.strip():
                    items.append(current)
                current = ''
            depth += 1
            # Find end of opening tag
            end = content.find('>', i)
            current += content[i:end+1]
            i = end + 1
        elif content[i:i+5] == '</li>':
            current += '</li>'
            i += 5
            depth -= 1
            if depth == 0:
                items.append(current)
                current = ''
        else:
            current += content[i]
            i += 1

    count = len(items)
    if count <= target:
        print(f"  {grade}: already {count} questions (ok)")
        return html

    # Keep first `target` items
    trimmed = '\n'.join(items[:target])
    new_section = prefix + '\n' + trimmed + '\n' + suffix
    html = html[:match.start()] + new_section + html[match.end():]
    print(f"  {grade}: trimmed from {count} to {target}")
    return html

# Trim G6-G12 to 10
for g in ['G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']:
    html = trim_section(html, g, 10)

# Also verify G1-G5
for g in ['G1', 'G2', 'G3', 'G4', 'G5']:
    html = trim_section(html, g, 10)

with open('daily/2026-06-25.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\nDone!")

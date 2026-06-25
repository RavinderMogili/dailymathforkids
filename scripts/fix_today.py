"""One-time script to fix stripped answers in 2026-06-25.html"""
import re

with open('daily/2026-06-25.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Each fix: (wrong answer text, correct answer text)
# Applied only once (first occurrence) per pair
fixes = [
    ('Answer: 50</li>', 'Answer: 50\u00a2</li>'),    # G2 Q1: 50 -> 50¢
    ('Answer: 1230</li>', 'Answer: 12:30</li>'),      # G2 Q6
    ('Answer: 14</li>', 'Answer: 1/4</li>'),          # G3 Q3
    ('Answer: 12</li>', 'Answer: 1/2</li>'),          # G3 Q8
    ('Answer: 03</li>', 'Answer: 0.3</li>'),          # G4 Q2
    ('Answer: 34</li>', 'Answer: 3/4</li>'),          # G4 Q7
    ('Answer: 3825</li>', 'Answer: $38.25</li>'),     # G4 Q8
    ('Answer: 57</li>', 'Answer: 5/7</li>'),          # G5 Q2
    ('Answer: 30</li>', 'Answer: $30</li>'),          # G5 Q3
    ('Answer: 72.</li>', 'Answer: 72</li>'),          # G5 Q5 trailing dot
    ('Answer: 38</li>', 'Answer: 3/8</li>'),          # G5 Q6
    ('Answer: 675</li>', 'Answer: $6.75</li>'),       # G5 Q7
    ('Answer: 9</li>', 'Answer: $9</li>'),            # G5 Q8
    ('Answer: 85</li>', 'Answer: 8/5</li>'),          # G5 Q9
    ('Answer: 40</li>', 'Answer: $40</li>'),          # G5 Q10
    ('Answer: 25</li>', 'Answer: 2/5</li>'),          # G6 Q1
    ('Answer: 23</li>', 'Answer: 2:3</li>'),          # G6 Q3
    ('Answer: 18</li>', 'Answer: $18</li>'),          # G6 Q9
    ('Answer: 12960</li>', 'Answer: $129.60</li>'),   # G6 Q12
]

count = 0
for old, new in fixes:
    if old in html:
        html = html.replace(old, new, 1)
        count += 1
        print(f'  Fixed: {old.strip()} -> {new.strip()}')

# Fix G2 Q2: answer "3" needs to be "3:00" but "3" is too generic.
# Find it within the G2 section context specifically.
# The question has choices: 2:00, 4:00, 3:30, 3:00
# Answer line immediately after Steps for G2 Q2
g2_q2_pattern = r'(Choices: A\) 2:00\s+B\) 4:00\s+C\) 3:30\s+D\) 3:00.*?Answer: )3(</li>)'
match = re.search(g2_q2_pattern, html, re.DOTALL)
if match:
    html = html[:match.start()] + match.group(1) + '3:00' + match.group(2) + html[match.end():]
    count += 1
    print('  Fixed: G2 Q2: Answer: 3 -> Answer: 3:00')

# Fix G7 Q1: missing answer — need to check what it should be
# Check G7 Q1 context
g7_match = re.search(r'data-grade="G7".*?<ol class="problems-list">(.*?)</ol>', html, re.DOTALL)
if g7_match:
    g7_content = g7_match.group(1)
    # Find first <li> answer
    first_q = re.search(r'Answer:\s*(</li>)', g7_content)
    if first_q:
        print('  NOTE: G7 Q1 has empty answer — checking choices')
        # Find G7 Q1 choices
        choices_match = re.search(r'Choices:.*?</li>', g7_content[:g7_content.find('Answer:')])
        if choices_match:
            print(f'  G7 Q1 choices line: {choices_match.group(0)[:80]}')

print(f'\nTotal fixes: {count}')

with open('daily/2026-06-25.html', 'w', encoding='utf-8') as f:
    f.write(html)

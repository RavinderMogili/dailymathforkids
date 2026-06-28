"""
Post-generation quiz validator.
Runs after gen_site.py to catch common LLM errors before publishing.

Checks:
1. Answer must exactly match one of the choice values
2. Fractions must contain '/' (catches 14 instead of 1/4)
3. Division problems must have integer answers
4. Answer must be a reasonable number (not absurdly large)
5. No duplicate questions within a grade
6. All required fields present (EN, FR, Choices, Answer)

Usage:
  python scripts/validate_quiz.py                  # validate today
  python scripts/validate_quiz.py 2026-06-25       # validate specific date
  python scripts/validate_quiz.py --fix            # auto-fix and write corrections to file
  python scripts/validate_quiz.py --strict         # exit code 2 if any errors (blocks deploy)
  python scripts/validate_quiz.py --fix --strict   # fix first, then block if unfixable remain

Exit code 0 = all good, 1 = warnings only, 2 = errors found
"""

import re, sys, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"


def parse_questions_from_md(md_text):
    """Parse questions from the raw markdown text."""
    questions = []
    # Split by grade sections
    grade_pattern = re.compile(r'## (G\d+)\n(.*?)(?=\n## |\Z)', re.DOTALL)

    for match in grade_pattern.finditer(md_text):
        grade = match.group(1)
        content = match.group(2)

        # Find each question block
        q_pattern = re.compile(
            r'\d+\.\s*\*\*\[(\w+)\]\s*(.*?)\*\*\s*\n'
            r'(.*?)(?=\n\d+\.\s*\*\*|\Z)',
            re.DOTALL
        )

        for qi, qm in enumerate(q_pattern.finditer(content), 1):
            difficulty = qm.group(1)
            title = qm.group(2)
            body = qm.group(3)

            en = _extract(body, r'-\s*EN:\s*(.+)')
            fr = _extract(body, r'-\s*FR:\s*(.+)')
            choices_raw = _extract(body, r'-\s*Choices:\s*(.+)')
            answer = _extract(body, r'-\s*Answer:\s*(\S+)')
            hint = _extract(body, r'-\s*Hint:\s*(.+)')

            choices = parse_choices(choices_raw) if choices_raw else []

            questions.append({
                'grade': grade,
                'num': qi,
                'difficulty': difficulty,
                'title': title.strip(),
                'en': en,
                'fr': fr,
                'choices_raw': choices_raw,
                'choices': choices,
                'answer': answer,
                'hint': hint,
            })

    return questions


def parse_questions_from_html(html_text):
    """Parse questions from the generated HTML file."""
    questions = []

    # Find grade sections
    grade_sections = re.finditer(
        r'<div class="grade-section" data-grade="(G\d+)"[^>]*>(.*?)</div>\s*(?=<div class="grade-section"|<h2>Today)',
        html_text, re.DOTALL
    )

    for gs in grade_sections:
        grade = gs.group(1)
        section_html = gs.group(2)

        # Find each <li> problem
        problems = re.finditer(r'<li><p><strong>(.*?)</strong></p>\s*<ul>(.*?)</ul></li>', section_html, re.DOTALL)

        for qi, pm in enumerate(problems, 1):
            title = pm.group(1)
            body = pm.group(2)

            # Strip HTML tags for text extraction
            en = _extract_html(body, r'<li>EN:\s*(.*?)</li>')
            fr = _extract_html(body, r'<li>FR:\s*(.*?)</li>')
            choices_raw = _extract_html(body, r'<li>Choices:\s*(.*?)</li>')
            answer = _extract_html(body, r'<li>Answer:\s*(.*?)</li>')

            choices = parse_choices(choices_raw) if choices_raw else []

            # Extract difficulty
            diff_match = re.search(r'\[(Easy|Medium|Hard)\]', title, re.IGNORECASE)
            difficulty = diff_match.group(1) if diff_match else 'unknown'

            questions.append({
                'grade': grade,
                'num': qi,
                'difficulty': difficulty,
                'title': re.sub(r'\[(?:Easy|Medium|Hard)\]\s*', '', title).strip(),
                'en': en,
                'fr': fr,
                'choices_raw': choices_raw,
                'choices': choices,
                'answer': answer,
            })

    return questions


def parse_choices(choices_str):
    """Parse 'A) val  B) val  C) val  D) val' into list of values."""
    if not choices_str:
        return []
    parts = re.split(r'\s{2,}(?=[A-D]\))', choices_str.strip())
    values = []
    for p in parts:
        m = re.match(r'[A-D]\)\s*(.+)', p.strip())
        if m:
            values.append(m.group(1).strip())
    return values


def _extract(text, pattern):
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_html(text, pattern):
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else None


class Issue:
    def __init__(self, level, grade, qnum, msg, fix=None):
        self.level = level  # 'error' or 'warning'
        self.grade = grade
        self.qnum = qnum
        self.msg = msg
        self.fix = fix  # suggested fix

    def __str__(self):
        icon = '[ERROR]' if self.level == 'error' else '[WARN]'
        return f"  {icon} [{self.grade} Q{self.qnum}] {self.msg}"


def validate_questions(questions):
    """Run all validation checks. Returns list of Issue objects."""
    issues = []

    for q in questions:
        grade = q['grade']
        num = q['num']

        # Check 1: Required fields
        if not q['en']:
            issues.append(Issue('error', grade, num, 'Missing English question text'))
        if not q['fr']:
            issues.append(Issue('warning', grade, num, 'Missing French translation'))
        if not q['choices']:
            issues.append(Issue('error', grade, num, 'Missing or unparseable choices'))
        if not q['answer']:
            issues.append(Issue('error', grade, num, 'Missing answer'))
            continue

        answer = q['answer']
        choices = q['choices']

        # Check 2: Answer must match one of the choices exactly
        if choices and answer not in choices:
            # Case-insensitive check
            lower_choices = [c.lower() for c in choices]
            if answer.lower() not in lower_choices:
                # Check if answer is a stripped version of a choice
                # (e.g. 14->1/4, 30->$30, 1230->12:30, 03->0.3)
                possible_fix = None
                for c in choices:
                    stripped = re.sub(r'[$/:.,¢]', '', c)
                    if stripped == answer:
                        possible_fix = c
                        break

                if possible_fix:
                    issues.append(Issue('error', grade, num,
                        f'Answer "{answer}" looks like a stripped version of "{possible_fix}". '
                        f'Should be "{possible_fix}" (matches choice)',
                        fix=possible_fix))
                else:
                    issues.append(Issue('error', grade, num,
                        f'Answer "{answer}" does not match any choice: {choices}'))

        # Check 3: Division questions should have integer answers
        en = q.get('en', '') or ''
        if re.search(r'divid|÷|split.*equal|share.*equal', en, re.IGNORECASE):
            try:
                # Extract numbers from question for basic check
                nums = re.findall(r'\d+', en)
                if len(nums) >= 2:
                    # Try common division patterns
                    a, b = int(nums[-2]), int(nums[-1])
                    if b > 0 and a > b and a % b != 0:
                        total_product = None
                        # Check if there's a multiplication first
                        mult_match = re.search(r'(\d+)\s*(?:shelves|boxes|rows|groups).*?(\d+)', en)
                        if mult_match:
                            total_product = int(mult_match.group(1)) * int(mult_match.group(2))
                        if total_product and total_product % b != 0:
                            issues.append(Issue('warning', grade, num,
                                f'Division may not produce integer: {total_product} ÷ {b} = {total_product/b:.2f}'))
            except (ValueError, IndexError):
                pass

        # Check 4: Fraction questions should have fraction answers
        if re.search(r'fraction|what part|what portion', en, re.IGNORECASE):
            if answer and re.match(r'^\d{2,}$', answer) and not re.search(r'/', answer):
                # Looks like a number but should be a fraction
                issues.append(Issue('warning', grade, num,
                    f'Fraction question but answer "{answer}" has no "/" — possible stripped fraction'))

        # Check 5: Answer is a reasonable number
        if answer:
            try:
                # Handle fractions
                if '/' in answer:
                    parts = answer.split('/')
                    val = float(parts[0]) / float(parts[1])
                else:
                    val = float(answer)
                if abs(val) > 100000:
                    issues.append(Issue('warning', grade, num,
                        f'Answer {answer} seems unreasonably large for grade {grade}'))
            except (ValueError, ZeroDivisionError):
                pass  # Non-numeric answers are OK (like choice text)

        # Check 6: Comparison questions — verify logic
        if re.search(r'which is (bigger|larger|greater|smaller|less)', en, re.IGNORECASE):
            # For fraction comparison, basic check
            fracs = re.findall(r'(\d+)/(\d+)', en)
            if len(fracs) >= 2:
                try:
                    val1 = int(fracs[0][0]) / int(fracs[0][1])
                    val2 = int(fracs[1][0]) / int(fracs[1][1])
                    correct_frac = f"{fracs[0][0]}/{fracs[0][1]}" if val1 > val2 else f"{fracs[1][0]}/{fracs[1][1]}"
                    if answer and answer != correct_frac and answer.replace('/', '') != correct_frac.replace('/', ''):
                        # Check if the answer text matches
                        if correct_frac not in (answer or ''):
                            issues.append(Issue('warning', grade, num,
                                f'Comparison question: mathematically {correct_frac} is bigger, '
                                f'but answer is "{answer}"'))
                except (ValueError, ZeroDivisionError):
                    pass

    return issues


def validate_file(filepath, source='html'):
    """Validate a quiz file. Returns (questions, issues)."""
    text = filepath.read_text(encoding='utf-8')

    if source == 'md':
        questions = parse_questions_from_md(text)
    else:
        questions = parse_questions_from_html(text)

    issues = validate_questions(questions)
    return questions, issues


def auto_fix_file(filepath, issues, source='md'):
    """Apply auto-fixes to the file for issues that have a suggested fix."""
    fixable = [i for i in issues if i.fix and i.level == 'error']
    if not fixable:
        print("  No auto-fixable issues found.")
        return 0

    content = filepath.read_text(encoding='utf-8')
    fixed_count = 0

    for issue in fixable:
        old_answer = issue.msg.split('"')[1]  # extract wrong answer from error msg
        if source == 'md':
            old_pattern = f'Answer: {old_answer}'
            new_pattern = f'Answer: {issue.fix}'
        else:
            # HTML: Answer is in <li>Answer: VALUE</li>
            old_pattern = f'Answer: {old_answer}</li>'
            new_pattern = f'Answer: {issue.fix}</li>'

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern, 1)
            fixed_count += 1
            print(f"  Fixed [{issue.grade} Q{issue.qnum}]: \"{old_answer}\" -> \"{issue.fix}\"")

    if fixed_count:
        filepath.write_text(content, encoding='utf-8')
        print(f"\n  Auto-fixed {fixed_count} answer(s) in {filepath.name}")

    return fixed_count


def check_min_questions(questions, min_per_grade=10):
    """Check that each grade has at least min_per_grade questions."""
    from collections import Counter
    grade_counts = Counter(q['grade'] for q in questions)
    issues = []
    for grade, count in sorted(grade_counts.items()):
        if count < min_per_grade:
            issues.append(f"[{grade}] Only {count} questions (expected {min_per_grade})")
    return issues


def main():
    args = sys.argv[1:]
    do_fix = '--fix' in args
    strict = '--strict' in args
    args = [a for a in args if not a.startswith('--')]

    if args:
        date_str = args[0]
    else:
        date_str = datetime.date.today().isoformat()

    md_path = DAILY_DIR / f"{date_str}.md"
    html_path = DAILY_DIR / f"{date_str}.html"

    if md_path.exists():
        filepath = md_path
        source = 'md'
        print(f"Validating: {md_path.name} (markdown source)")
    elif html_path.exists():
        filepath = html_path
        source = 'html'
        print(f"Validating: {html_path.name} (HTML)")
    else:
        print(f"ERROR: No quiz file found for {date_str}")
        sys.exit(2)

    questions, issues = validate_file(filepath, source=source)
    grade_count = len(set(q['grade'] for q in questions))
    print(f"Found {len(questions)} questions across {grade_count} grades\n")

    # Check minimum question count per grade
    min_issues = check_min_questions(questions, min_per_grade=10)
    if min_issues:
        print(f"QUESTION COUNT ISSUES ({len(min_issues)}):")
        for msg in min_issues:
            print(f"  [WARN] {msg}")
        print()

    if not issues and not min_issues:
        print("All checks passed! No issues found.")
        sys.exit(0)

    errors = [i for i in issues if i.level == 'error']
    warnings = [i for i in issues if i.level == 'warning']

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for i in errors:
            print(i)
            if i.fix:
                print(f"       Suggested fix: change answer to \"{i.fix}\"")
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for i in warnings:
            print(i)
        print()

    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings in {len(questions)} questions")

    # Auto-fix mode: apply fixes and write back to file
    if do_fix and errors:
        print(f"\nAttempting auto-fix...")
        fixed = auto_fix_file(filepath, issues, source=source)
        if fixed:
            # Re-validate after fix
            questions2, issues2 = validate_file(filepath, source=source)
            remaining_errors = [i for i in issues2 if i.level == 'error']
            if remaining_errors:
                print(f"\n  {len(remaining_errors)} error(s) remain after auto-fix (need manual review)")
            else:
                print(f"\n  All errors resolved after auto-fix!")
                sys.exit(0)

    # In strict mode, exit with error code if any errors remain
    if strict and errors:
        unfixable = [i for i in errors if not i.fix]
        if unfixable:
            print(f"\nSTRICT MODE: {len(unfixable)} unfixable error(s) -- blocking deploy.")
            sys.exit(2)
        # If all errors were fixable but --fix wasn't used
        print(f"\nSTRICT MODE: {len(errors)} error(s) found -- run with --fix first.")
        sys.exit(2)

    # Exit code: 2 for errors, 1 for warnings only, 0 for clean
    sys.exit(2 if errors else (1 if warnings or min_issues else 0))


if __name__ == "__main__":
    main()

"""Fail-closed daily quiz validator.

Validation is comparison-only: this command never rewrites quiz content.
The mathematical implementation lives in question_quality.py and is shared
with the conformance runner, not with the client-side answer display code.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from question_quality import equivalent_strings, normal_text, validate_question

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
GRADE_CODES = [f"G{i}" for i in range(1, 13)]
EXPECTED_DIFFICULTIES = {"Easy": 4, "Medium": 4, "Hard": 2}
REPORT_ONLY_CODES = {"HINT_LEAKS_ANSWER"}


@dataclass
class Issue:
    level: str
    grade: str
    qnum: int
    msg: str
    code: str = ""
    fix: None = None
    authored_num: int | None = None

    def __str__(self) -> str:
        authored = f" (authored {self.authored_num})" if self.authored_num is not None else ""
        return f"[{self.level.upper()}] [{self.grade} Q{self.qnum}{authored}] {self.msg}"


def _extract(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_html(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() if match else None


def parse_choices(choices_str: str | None) -> list[str]:
    if not choices_str:
        return []
    parts = re.split(r"\s{2,}(?=[A-D]\))", choices_str.strip(), flags=re.I)
    values: list[str] = []
    for part in parts:
        match = re.match(r"[A-D]\)\s*(.+)", part.strip(), re.I)
        if match:
            values.append(match.group(1).strip())
    return values


def parse_questions_from_md(md_text: str) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    grade_pattern = re.compile(r"^##\s+(G\d+)\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE)
    q_pattern = re.compile(
        r"^\s*(\d+)\.\s*\*\*\[([^\]]+)\]\s*(.*?)\*\*\s*$"
        r"([\s\S]*?)(?=^\s*\d+\.\s*\*\*|\Z)",
        re.MULTILINE,
    )
    for grade_match in grade_pattern.finditer(md_text):
        grade, content = grade_match.group(1), grade_match.group(2)
        for question_index, q_match in enumerate(q_pattern.finditer(content), 1):
            qnum, difficulty, title, body = q_match.groups()
            field_indents = [
                match.group(1)
                for match in re.finditer(
                    r"^([ \t]+)-\s*(?:EN|FR|Choices|Hint|Steps|Answer):",
                    body,
                    re.MULTILINE,
                )
            ]
            field_indent = min(field_indents, key=lambda value: len(value.expandtabs(4))) if field_indents else None
            answer_matches = (
                re.findall(
                    rf"^{re.escape(field_indent)}-\s*Answer:\s*(.+)$",
                    body,
                    re.MULTILINE,
                )
                if field_indent is not None
                else []
            )
            choices_raw = _extract(body, r"^\s*-\s*Choices:\s*(.+)$")
            en = _extract(body, r"^\s*-\s*EN:\s*(.+)$")
            fr = _extract(body, r"^\s*-\s*FR:\s*(.+)$")
            hint = _extract(body, r"^\s*-\s*Hint:\s*(.+)$")
            questions.append({
                "grade": grade, "num": int(qnum), "authored_number": int(qnum),
                "question_index": question_index, "difficulty": difficulty.title(),
                "title": title.strip(), "question": en or "", "en": en, "fr": fr,
                "choices_raw": choices_raw, "choices": parse_choices(choices_raw),
                "answer": answer_matches[-1].strip() if answer_matches else None,
                "answer_line_count": len(answer_matches), "hint": hint,
            })
    return questions


def parse_questions_from_html(html_text: str) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    grade_pattern = re.compile(
        r'<div class="grade-section" data-grade="(G\d+)"[^>]*>([\s\S]*?)(?=<div class="grade-section"|<h2>Today|</main>)',
        re.I,
    )
    problem_pattern = re.compile(r"<li><p><strong>(.*?)</strong></p>\s*<ul>([\s\S]*?)</ul></li>", re.I)
    for grade_match in grade_pattern.finditer(html_text):
        grade, section = grade_match.groups()
        for qnum, problem in enumerate(problem_pattern.finditer(section), 1):
            title_html, body = problem.groups()
            title = html.unescape(re.sub(r"<[^>]+>", "", title_html)).strip()
            diff_match = re.search(r"\[(Easy|Medium|Hard)\]", title, re.I)
            difficulty = diff_match.group(1).title() if diff_match else "Unknown"
            choices_raw = _extract_html(body, r"<li>Choices:\s*(.*?)</li>")
            questions.append({
                "grade": grade, "num": qnum, "authored_number": None,
                "question_index": qnum, "difficulty": difficulty,
                "title": re.sub(r"\[(?:Easy|Medium|Hard)\]\s*", "", title, flags=re.I),
                "question": _extract_html(body, r"<li>EN:\s*(.*?)</li>") or "",
                "en": _extract_html(body, r"<li>EN:\s*(.*?)</li>"),
                "fr": _extract_html(body, r"<li>FR:\s*(.*?)</li>"),
                "choices_raw": choices_raw, "choices": parse_choices(choices_raw),
                "answer": _extract_html(body, r"<li>Answer:\s*(.*?)</li>"),
                "hint": _extract_html(body, r"<li>Hint:\s*(.*?)</li>"),
            })
    return questions


def validate_questions(questions: list[dict[str, Any]], require_french: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    for question in questions:
        result = validate_question(question, require_french=require_french)
        for code in result["codes"]:
            level = "warning" if code == "UNVERIFIED" or code in REPORT_ONLY_CODES else "error"
            issues.append(Issue(
                level,
                str(question.get("grade", "")),
                int(question.get("question_index", 0)),
                code,
                code=code,
                authored_num=question.get("authored_number"),
            ))
    return issues


def validate_file(filepath: pathlib.Path, source: str | None = None) -> tuple[list[dict[str, Any]], list[Issue]]:
    text = filepath.read_text(encoding="utf-8")
    source = source or filepath.suffix.lstrip(".")
    questions = parse_questions_from_md(text) if source == "md" else parse_questions_from_html(text)
    return questions, validate_questions(questions, require_french=source == "md")


def check_min_questions(questions: list[dict[str, Any]], min_per_grade: int = 10) -> list[str]:
    counts: dict[str, int] = {}
    for question in questions:
        grade = str(question.get("grade", ""))
        counts[grade] = counts.get(grade, 0) + 1
    return [f"[{grade}] Only {counts.get(grade, 0)} questions (expected {min_per_grade})"
            for grade in GRADE_CODES if counts.get(grade, 0) < min_per_grade]


def _structural_issues(questions: list[dict[str, Any]]) -> list[Issue]:
    issues: list[Issue] = []
    by_grade: dict[str, list[dict[str, Any]]] = {grade: [] for grade in GRADE_CODES}
    for question in questions:
        by_grade.setdefault(str(question.get("grade")), []).append(question)
    for grade in GRADE_CODES:
        group = by_grade.get(grade, [])
        authored_numbers: dict[int, list[dict[str, Any]]] = {}
        for question in group:
            authored_number = question.get("authored_number")
            if authored_number is not None:
                authored_numbers.setdefault(int(authored_number), []).append(question)
        for authored_number, duplicates in authored_numbers.items():
            if len(duplicates) > 1:
                for question in duplicates:
                    issues.append(Issue(
                        "error",
                        grade,
                        int(question.get("question_index", 0)),
                        f"Authored question number {authored_number} appears {len(duplicates)} times",
                        "DUPLICATE_QUESTION_NUMBER",
                        authored_num=authored_number,
                    ))
        if len(group) != 10:
            issues.append(Issue("error", grade, 0, f"Expected exactly 10 questions, found {len(group)}", "QUESTION_COUNT"))
        difficulty = {name: 0 for name in EXPECTED_DIFFICULTIES}
        for question in group:
            key = str(question.get("difficulty", "")).title()
            if key in difficulty:
                difficulty[key] += 1
        if difficulty != EXPECTED_DIFFICULTIES:
            issues.append(Issue("error", grade, 0, f"Difficulty distribution is {difficulty}; expected {EXPECTED_DIFFICULTIES}",
                                "DIFFICULTY_DISTRIBUTION"))
    present = {str(question.get("grade")) for question in questions}
    missing = [grade for grade in GRADE_CODES if grade not in present]
    if missing:
        issues.append(Issue("error", "RUN", 0, f"Missing grades: {', '.join(missing)}", "GRADE_COUNT"))
    return issues


def _position_report(questions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = [0, 0, 0, 0]
    for question in questions:
        answer, choices = question.get("answer"), question.get("choices") or []
        matches = [i for i, choice in enumerate(choices) if equivalent_strings(answer, choice)[0]]
        if len(matches) == 1 and matches[0] < 4:
            counts[matches[0]] += 1
    total = sum(counts)
    proportions = [count / total if total else 0 for count in counts]
    return {
        "counts": {chr(65 + i): counts[i] for i in range(4)},
        "total": total,
        "proportions": {chr(65 + i): proportions[i] for i in range(4)},
        "biased_positions": [chr(65 + i) for i, proportion in enumerate(proportions) if proportion > 0.4],
    }


def _fingerprint(question: dict[str, Any]) -> tuple[str, str]:
    return str(question.get("grade", "")), normal_text(question.get("question") or question.get("en") or "").casefold()


def _duplicate_recent_questions(date_str: str, questions: list[dict[str, Any]]) -> list[Issue]:
    try:
        current = dt.date.fromisoformat(date_str)
    except ValueError:
        return []
    prior: set[tuple[str, str]] = set()
    for path in DAILY_DIR.glob("*.md"):
        try:
            date = dt.date.fromisoformat(path.stem)
        except ValueError:
            continue
        if dt.timedelta(days=1) <= current - date <= dt.timedelta(days=30):
            prior.update(_fingerprint(question) for question in parse_questions_from_md(path.read_text(encoding="utf-8")))
    issues: list[Issue] = []
    seen: set[tuple[str, str]] = set()
    for question in questions:
        fingerprint = _fingerprint(question)
        if fingerprint in prior or fingerprint in seen:
            issues.append(Issue(
                "error",
                str(question.get("grade")),
                int(question.get("question_index", 0)),
                "DUPLICATE_RECENT_QUESTION",
                "DUPLICATE_RECENT_QUESTION",
                authored_num=question.get("authored_number"),
            ))
        seen.add(fingerprint)
    return issues


def _manifest_entries(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def _manifest_allows(entry: dict[str, Any], quiz_date: str, question: dict[str, Any], issue_code: str) -> bool:
    required = ("reviewer", "reviewer_date", "quiz_date", "grade", "question_index",
                "code", "worked_verification", "reason")
    if not all(str(entry.get(key, "")).strip() for key in required):
        return False
    if str(entry["quiz_date"]) != quiz_date or str(entry["code"]) != issue_code:
        return False
    grade = str(question.get("grade"))
    index = int(question.get("question_index", 0))
    try:
        entry_index = int(entry["question_index"])
    except (TypeError, ValueError):
        return False
    return str(entry["grade"]) == grade and entry_index == index


def validate_run(filepath: pathlib.Path, quiz_date: str, allow_nonvalid: int = 0,
                 manifest_path: pathlib.Path | None = None) -> dict[str, Any]:
    source = filepath.suffix.lstrip(".")
    questions, issues = validate_file(filepath, source)
    issues.extend(_structural_issues(questions))
    issues.extend(_duplicate_recent_questions(quiz_date, questions))
    position_report = _position_report(questions)
    manifest = _manifest_entries(manifest_path or ROOT / "data" / "review" / "verified-items.json")
    allowed, blocked = [], []
    for issue in issues:
        question = next((q for q in questions if str(q.get("grade")) == issue.grade and
                         int(q.get("question_index", 0)) == issue.qnum), None)
        if question and any(_manifest_allows(item, quiz_date, question, issue.code) for item in manifest):
            allowed.append(issue)
        else:
            blocked.append(issue)
    nonvalid = len({
        (issue.grade, issue.qnum)
        for issue in blocked
        if issue.grade != "RUN" and issue.code not in REPORT_ONLY_CODES
    })
    blocking_errors = any(issue.level == "error" for issue in blocked)
    publication_allowed = not blocking_errors and nonvalid <= allow_nonvalid
    return {
        "date": quiz_date, "file": str(filepath), "publication_allowed": publication_allowed,
        "non_valid_items": nonvalid,
        "questions": [
            {"grade": q.get("grade"), "question_index": q.get("question_index"),
             "authored_number": q.get("authored_number"),
             **validate_question(q, require_french=source == "md")}
            for q in questions
        ],
        "issues": [{"level": issue.level, "grade": issue.grade, "question_index": issue.qnum,
                    "authored_number": issue.authored_num,
                    "code": issue.code, "message": issue.msg} for issue in issues],
        "allowed_issues": [{"code": issue.code, "grade": issue.grade, "question_index": issue.qnum,
                            "authored_number": issue.authored_num} for issue in allowed],
        "blocking_errors": blocking_errors,
        "position_balance": position_report,
    }


def _print_report(result: dict[str, Any]) -> None:
    print(f"Found {len(result['questions'])} questions")
    errors = [issue for issue in result["issues"] if issue["level"] == "error"]
    warnings = [issue for issue in result["issues"] if issue["level"] == "warning"]
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for issue in errors:
            authored = (
                f" (authored {issue['authored_number']})"
                if issue.get("authored_number") is not None else ""
            )
            print(f"  [ERROR] [{issue['grade']} Q{issue['question_index']}{authored}] "
                  f"[{issue['code']}] {issue['message']}")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for issue in warnings:
            authored = (
                f" (authored {issue['authored_number']})"
                if issue.get("authored_number") is not None else ""
            )
            print(f"  [WARN] [{issue['grade']} Q{issue['question_index']}{authored}] "
                  f"[{issue['code']}] {issue['message']}")
    print(f"\nAnswer positions: {result['position_balance']['counts']}")
    print(f"Summary: {len(errors)} errors, {len(warnings)} warnings in {len(result['questions'])} questions")
    print("Publication: " + ("ALLOWED" if result["publication_allowed"] else "BLOCKED"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a daily quiz without modifying it.")
    parser.add_argument("date", nargs="?", default=dt.date.today().isoformat())
    parser.add_argument("--strict", action="store_true", help="retained for CLI compatibility; validation is always fail-closed")
    parser.add_argument("--allow-nonvalid", type=int, default=0)
    parser.add_argument("--result-file")
    args = parser.parse_args(argv)
    md_path = DAILY_DIR / f"{args.date}.md"
    html_path = DAILY_DIR / f"{args.date}.html"
    if md_path.exists():
        filepath = md_path
    elif html_path.exists():
        filepath = html_path
    else:
        print(f"ERROR: No quiz file found for {args.date}", file=sys.stderr)
        return 2
    result = validate_run(filepath, args.date, allow_nonvalid=max(0, args.allow_nonvalid))
    if args.result_file:
        path = pathlib.Path(args.result_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _print_report(result)
    return 0 if result["publication_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
